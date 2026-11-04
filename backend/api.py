from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StrictInt, StrictFloat
from typing import List, Optional, Tuple, Literal
import uvicorn
import logging
import time
import traceback
import os
import json
import math
import threading
from starlette.concurrency import run_in_threadpool
from native_graph import (NativeUnavailable, RoutingBudgetExceeded, RoutingLimits,
                          positive_budget, snapshot_cache, normalize_node_id)
from routing_adapter import compute_native_matrix
import numpy as np
from distance_matrix import compute_matrix, get_node_coordinates, compute_matrix_with_fallback
from vrp_solver import solve_vrp
from graph_loader import load_graph, get_available_cities

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class VRPRequest(BaseModel):
    locations: List[str] = Field(..., description="List of node IDs")
    vehicle_count: StrictInt = Field(1, ge=1, description="Number of vehicles")
    depot: StrictInt = Field(0, ge=0, description="Depot index in locations")
    demands: Optional[List[StrictInt]] = Field(None, description="Demand at each location")
    capacities: Optional[List[StrictInt]] = Field(None, description="Vehicle capacities")
    time_windows: Optional[List[Tuple[StrictFloat, StrictFloat]]] = Field(None, description="Time windows for each location")

    engine: Literal["legacy_networkx", "native_bmssp_2025", "native_reference_dijkstra"] = "legacy_networkx"
    place: Optional[str] = None
    duration_matrix: Optional[List[List[Optional[StrictFloat]]]] = None
    service_durations: Optional[List[StrictFloat]] = None
    vehicle_start_windows: Optional[List[Tuple[StrictFloat, StrictFloat]]] = None
    vehicle_end_windows: Optional[List[Tuple[StrictFloat, StrictFloat]]] = None
    max_wait_seconds: StrictFloat = 86400.0
    max_search_seconds: StrictInt = 1

class NodeSearchRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius: float = Field(1000, ge=100, le=10000, description="Search radius in meters")

app = FastAPI(
    title="BMSSP Routing API",
    description="Directed routing with explicit native BMSSP/Dijkstra and legacy compatibility",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize API - graph will be loaded on first request."""
    logger.info("BMSSP Routing API started successfully")
    logger.info("Graph will be loaded on demand when needed")

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/status")
async def get_status():
    """Get current graph loading status."""
    try:
        from graph_loader import get_graph_stats
        stats = get_graph_stats()
        response = {"timestamp": time.time()}
        if isinstance(stats, dict) and "error" not in stats:
            response.update({
                "graph_loaded": True,
                "current_place": stats.get("place"),
                "node_count": stats.get("node_count"),
                "edge_count": stats.get("edge_count"),
                "cache_file": stats.get("cache_file"),
            })
        else:
            response.update({
                "graph_loaded": False,
                "current_place": None,
                "error": stats.get("error") if isinstance(stats, dict) else "Unknown error",
            })
        # Ensure JSON-safe node_count
        nc = response.get("node_count")
        try:
            if nc is None or not isinstance(nc, (int, float)) or math.isinf(nc) or math.isnan(nc):
                response["node_count"] = -1
        except Exception:
            response["node_count"] = -1
        return response
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return {"graph_loaded": False, "current_place": None, "error": str(e)}

@app.post("/load-graph/{place_name}")
async def load_graph_manually(place_name: str, background_tasks: BackgroundTasks):
    """Manually trigger graph loading for a specific place."""
    try:
        def load_in_background():
            try:
                from graph_loader import load_graph
                load_graph(place_name, force_reload=True)
                logger.info(f"Successfully loaded graph for {place_name}")
            except Exception as e:
                logger.error(f"Failed to load graph for {place_name}: {e}")
        
        background_tasks.add_task(load_in_background)
        return {"message": f"Started loading graph for {place_name}", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/load-graph")
async def load_graph_endpoint(place_name: str = "malaysia-singapore-brunei"):
    """Explicitly load a graph."""
    try:
        pbf_file = "/app/malaysia-singapore-brunei-latest.osm.pbf"
        if os.path.exists(pbf_file):
            from graph_loader import load_graph_from_pbf
            # Corrected signature: use keyword args
            load_graph_from_pbf(pbf_file=pbf_file, place_name=place_name)
            return {"status": "success", "message": f"Graph loaded for {place_name}"}
        else:
            from graph_loader import load_graph
            load_graph(place_name, force_reload=True)
            return {"status": "success", "message": f"Graph loaded for {place_name}"}
    except Exception as e:
        logger.error(f"Error loading graph: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load graph: {str(e)}")

@app.get("/cities")
async def get_cities():
    """Get list of available cities for routing."""
    try:
        cities = get_available_cities()
        return {"cities": cities}
    except Exception as e:
        logger.error(f"Error getting cities: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get available cities")

def _search_native_nodes(request, place):
    if not _native_slots.acquire(blocking=False):
        raise NativeUnavailable("Native routing capacity is busy; retry later")
    try:
        from graph_loader import load_native_graph, haversine_distance
        from road_geometry import coordinate
        from pyproj import CRS
        graph = load_native_graph(place)
        from native_graph import GraphSnapshot
        if isinstance(graph, GraphSnapshot):
            # Prepared fixtures use the same immutable coordinate capture as routing.
            graph, _ = snapshot_cache.get(graph)
            nodes = []
            for node, point in graph.road_data.nodes.items():
                if point is None:
                    continue
                distance = haversine_distance(request.lat, request.lon, *point)
                if distance <= request.radius:
                    nodes.append({"id": str(node), "node_id": str(node), "lat": point[0], "lon": point[1], "distance": distance})
            return sorted(nodes, key=lambda item: item["distance"])
        if len(graph) > RoutingLimits.from_environment().max_nodes:
            raise RoutingBudgetExceeded("Native search node budget exceeded")
        if not CRS.from_user_input(graph.graph.get("crs", "EPSG:4326")).equals(CRS.from_epsg(4326), ignore_axis_order=True):
            raise ValueError("Node search requires WGS84 geographical coordinates")
        nodes = []
        for node, data in graph.nodes(data=True):
            point = coordinate(data.get("x"), data.get("y"))
            if point is not None:
                distance = haversine_distance(request.lat, request.lon, *point)
                if distance <= request.radius:
                    nodes.append({"id": str(node), "node_id": str(node), "lat": point[0], "lon": point[1], "distance": distance})
        return sorted(nodes, key=lambda item: item["distance"])
    finally:
        _native_slots.release()


@app.post("/search-nodes")
async def search_nodes(request: NodeSearchRequest,
    engine: Literal["legacy_networkx", "native_bmssp_2025", "native_reference_dijkstra"] = "legacy_networkx",
    place: Optional[str] = None):
    """Nearest-node discovery only; proximity never establishes road feasibility."""
    try:
        if engine == "legacy_networkx":
            if place and place.startswith("osm-fixture:"):
                raise ValueError("Prepared road fixtures require an explicit native engine")
            from graph_loader import find_nearest_nodes
            nodes = await run_in_threadpool(find_nearest_nodes, request.lat, request.lon, request.radius)
        else:
            nodes = await run_in_threadpool(_search_native_nodes, request, place)
        return {"nodes": [{**node, "id": str(node.get("node_id", node.get("id"))),
                            "node_id": str(node.get("node_id", node.get("id")))} for node in nodes]}
    except RoutingBudgetExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except NativeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Node search failed")
        raise HTTPException(status_code=500, detail="Road-node search failed")

@app.get("/node-coordinates/{node_id}")
async def get_node_coords(node_id: str):
    """Get coordinates for a specific node."""
    try:
        coords = get_node_coordinates(node_id)
        if coords is None:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"node_id": node_id, "lat": coords[0], "lon": coords[1]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node coordinates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get node coordinates")

def _sanitize_for_json(obj):
    """Recursively sanitize objects: convert NaN/Inf floats to None and numpy types to native."""
    try:
        if isinstance(obj, (np.floating,)):
            val = float(obj)
            return None if math.isinf(val) or math.isnan(val) else val
        if isinstance(obj, float):
            return None if math.isinf(obj) or math.isnan(obj) else obj
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (list, tuple)):
            return [ _sanitize_for_json(x) for x in obj ]
        if isinstance(obj, dict):
            return { k: _sanitize_for_json(v) for k, v in obj.items() }
        return obj
    except Exception:
        return None

# Process-wide admission bound; all capture/preprocessing/query work is in a worker.
_native_slots = threading.BoundedSemaphore(positive_budget("NATIVE_MAX_CONCURRENT_REQUESTS", 2))


def _native_matrix_request(locations, engine, place, limits):
    if not _native_slots.acquire(blocking=False):
        raise NativeUnavailable("Native routing capacity is busy; retry later")
    try:
        from graph_loader import load_native_graph
        graph = load_native_graph(place)
        snapshot, snapshot_meta = snapshot_cache.get(graph, limits=limits)
        matrix, metadata = compute_native_matrix(snapshot, locations, engine, limits)
        return matrix, {**metadata, **snapshot_meta}
    finally:
        _native_slots.release()


@app.post("/distance-matrix")
async def get_distance_matrix(
    locations: List[str],
    engine: Literal["legacy_networkx", "native_bmssp_2025", "native_reference_dijkstra"] = "legacy_networkx",
    place: Optional[str] = None,
):
    """Legacy compatibility by default; native exact road routing is explicit."""
    try:
        start_time = time.time()
        if engine == "legacy_networkx":
            mat, meta = await run_in_threadpool(compute_matrix_with_fallback, locations, place)
            meta = {**meta, "selected_engine": engine, "algorithm_version": "networkx-legacy",
                    "exact_routing": False,
                    "approximation_provenance": {"mode": meta.get("fallback_mode"),
                                                  "fallback_counts": meta.get("fallback_counts", {})}}
        else:
            # Validate request cardinality before graph capture or native work.
            limits = RoutingLimits.from_environment()
            if len(locations) > limits.max_locations:
                raise RoutingBudgetExceeded("Native location budget exceeded")
            if not locations:
                raise ValueError("Native routing requires at least one location")
            normalized = [normalize_node_id(loc) for loc in locations]
            if len(set(normalized)) > limits.max_sources:
                raise RoutingBudgetExceeded("Native distinct-source budget exceeded")
            mat, meta = await run_in_threadpool(_native_matrix_request, locations, engine, place, limits)
        computation_time = time.time() - start_time
        
        # Sanitize matrix for JSON (convert inf/NaN to None)
        has_unreachable = False
        sanitized = []
        for row in mat.tolist():
            out_row = []
            for v in row:
                try:
                    fv = float(v)
                    if math.isinf(fv) or math.isnan(fv):
                        out_row.append(None)
                        has_unreachable = True
                    else:
                        out_row.append(fv)
                except Exception:
                    out_row.append(None)
                    has_unreachable = True
            sanitized.append(out_row)
        
        response = {
            "locations": locations,
            "matrix": sanitized,
            "status": "APPROXIMATED" if (meta.get("fallback_counts", {}).get("symmetric", 0) + meta.get("fallback_counts", {}).get("haversine", 0)) > 0 else ("PARTIAL_OR_UNREACHABLE" if has_unreachable else "OK"),
            "computation_time": float(computation_time),
            "metadata": meta,
        }
        return _sanitize_for_json(response)
    except RoutingBudgetExceeded as e:
        raise HTTPException(status_code=413, detail=str(e))
    except NativeUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing distance matrix: {str(e)}")
        raise HTTPException(status_code=500, detail=f"{engine} distance matrix failed: {e}")

def _legacy_vehicle_routing(request: VRPRequest):
    """Solve Vehicle Routing Problem with capacity and time window constraints."""
    try:
        start_time = time.time()
        
        # Validate inputs
        if request.depot >= len(request.locations):
            raise HTTPException(status_code=400, detail="Depot index out of range")
        
        if request.demands is not None and len(request.demands) != len(request.locations):
            raise HTTPException(status_code=400, detail="Demands length must match locations length")
        
        if request.capacities is not None and len(request.capacities) != request.vehicle_count:
            raise HTTPException(status_code=400, detail="Capacities length must match vehicle count")
        
        if request.time_windows is not None and len(request.time_windows) != len(request.locations):
            raise HTTPException(status_code=400, detail="Time windows length must match locations length")
        
        # Compute distance matrix with fallbacks
        matrix_start = time.time()
        distance_matrix, meta = compute_matrix_with_fallback(request.locations, place=None)
        matrix_time = time.time() - matrix_start
        
        # Solve VRP
        vrp_start = time.time()
        solution = solve_vrp(
            distance_matrix, 
            request.vehicle_count, 
            request.depot,
            request.demands, 
            request.capacities, 
            request.time_windows,
            max_search_seconds=request.max_search_seconds,
            duration_matrix=request.duration_matrix,
            service_durations=request.service_durations,
            vehicle_start_windows=request.vehicle_start_windows,
            vehicle_end_windows=request.vehicle_end_windows,
            max_wait_seconds=request.max_wait_seconds,
        )
        vrp_time = time.time() - vrp_start
        total_time = time.time() - start_time
        
        # Sanitize distances for JSON
        def sanitize(val):
            try:
                if val is None or (isinstance(val, float) and (math.isinf(val) or math.isnan(val))):
                    return None
            except Exception:
                return None
            return float(val)
        
        total_distance = sanitize(solution.get("total_distance"))
        vehicle_distances = [sanitize(v) for v in solution.get("vehicle_distances", [])]
        
        # Compatibility is explicit; never mask a genuine failure with approximation.
        status = solution.get("status", "FAILED")
        established = status in ("OPTIMAL", "FEASIBLE") and total_distance is not None
        if established:
            status = "APPROXIMATED" if sum(meta.get("fallback_counts", {}).values()) else "FEASIBLE"

        location_coords = {}
        for loc in request.locations:
            coords = get_node_coordinates(loc)
            if coords:
                location_coords[loc] = {"lat": coords[0], "lon": coords[1]}

        # Build full path geometries for each route
        from graph_loader import get_full_path_coordinates
        route_geometries = []
        geometry_point_count = 0
        for route in solution.get("routes", []):
            route_path = []
            geometry_complete = True
            for i in range(len(route) - 1):
                start_idx = route[i]
                end_idx = route[i+1]
                start_id = request.locations[start_idx]
                end_id = request.locations[end_idx]
                try:
                    segment = get_full_path_coordinates(start_id, end_id)
                except (RuntimeError, ValueError):
                    segment = []  # Explicit legacy geometry-unavailable condition.
                if segment:
                    geometry_point_count += len(segment)
                    if geometry_point_count > positive_budget("VRP_MAX_GEOMETRY_POINTS", 100000):
                        raise RoutingBudgetExceeded("VRP geometry response budget exceeded")
                    # Avoid duplicating points
                    if route_path and segment[0] == route_path[-1]:
                        route_path.extend(segment[1:])
                    else:
                        if route_path:
                            geometry_complete = False
                        route_path.extend(segment)
                else:
                    geometry_complete = False
            route_geometries.append(route_path if geometry_complete else [])

        response = {
            "locations": request.locations,
            "routes": solution.get("routes", []),
            "route_locations": [[request.locations[i] for i in route] for route in solution.get("routes", [])],
            "location_coordinates": location_coords,
            "route_geometries": route_geometries,
            "route_geometry_status": ["LEGACY_UNVERIFIED" if geometry else "UNAVAILABLE" for geometry in route_geometries],
            "total_distance": total_distance,
            "vehicle_distances": vehicle_distances,
            "status": status,
            "selected_engine": "legacy_networkx", "exact_routing": False,
            "route_feasibility": bool(established), "solver_status": solution.get("solver_status", solution.get("status")),
            "weight_units": "meters", "duration_units": solution.get("duration_units"),
            "computation_times": {
                "matrix_computation": matrix_time,
                "vrp_solving": vrp_time,
                "total": total_time
            },
            "metadata": {
                **meta,
                "selected_engine": "legacy_networkx", "exact_routing": False,
                "certification": "Legacy routing is not certified for exact directed-road feasibility",
                "reason": solution.get("reason"),
                "approximation_provenance": meta.get("fallback_counts", {}),
                "vehicle_count": request.vehicle_count,
                "depot": request.depot,
                "has_demands": request.demands is not None,
                "has_capacities": request.capacities is not None,
                "has_time_windows": request.time_windows is not None
            }
        }
        return _sanitize_for_json(response)
    except HTTPException:
        raise
    except RoutingBudgetExceeded as e:
        raise HTTPException(status_code=413, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error solving VRP: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to solve VRP")


def _run_native_vrp(request, selected):
    if not _native_slots.acquire(blocking=False):
        raise NativeUnavailable("Native routing capacity is busy; retry later")
    try:
        from logistics_routing import native_vrp
        response = native_vrp(request, selected)
        clock = time.perf_counter()
        json.dumps(response, allow_nan=False)
        response["computation_times"]["serialization"] = time.perf_counter()-clock
        return JSONResponse(response)
    finally:
        _native_slots.release()


@app.post("/vrp")
async def solve_vehicle_routing(
    request: VRPRequest,
    engine: Optional[Literal["native_bmssp_2025", "native_reference_dijkstra", "legacy_networkx"]] = None,
):
    selected = engine or request.engine
    if engine and request.engine != "legacy_networkx" and request.engine != engine:
        raise HTTPException(status_code=400, detail="Conflicting routing engine selections")
    try:
        if not request.locations:
            raise ValueError("At least one location is required")
        if request.depot >= len(request.locations):
            raise ValueError("Depot index out of range")
        if len(request.locations) > positive_budget("VRP_MAX_LOCATIONS", 32):
            raise RoutingBudgetExceeded("VRP location budget exceeded")
        if not 1 <= request.vehicle_count <= positive_budget("VRP_MAX_VEHICLES", 10):
            raise RoutingBudgetExceeded("VRP vehicle budget exceeded")
        if not 1 <= request.max_search_seconds <= positive_budget("VRP_MAX_SEARCH_SECONDS", 10):
            raise RoutingBudgetExceeded("VRP search budget exceeded")
        if selected == "legacy_networkx":
            if request.place and request.place.startswith("osm-fixture:"):
                raise ValueError("Prepared road fixtures require an explicit native engine")
            return await run_in_threadpool(_legacy_vehicle_routing, request)
        return await run_in_threadpool(_run_native_vrp, request, selected)
    except HTTPException:
        raise
    except RoutingBudgetExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except NativeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Native VRP execution failed")
        raise HTTPException(status_code=500, detail="Routing execution failed; no verified route was returned")


@app.get("/stats")
async def get_system_stats():
    """Get system statistics and performance metrics."""
    try:
        from graph_loader import get_graph_stats
        stats = get_graph_stats()
        return {
            "graph_stats": stats,
            "api_version": "1.0.0",
            "algorithm": "Legacy NetworkX by default; native engines require explicit selection",
            "default_engine": "legacy_networkx",
            "native_engines": ["native_bmssp_2025", "native_reference_dijkstra"]
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system stats")

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        access_log=True
    )