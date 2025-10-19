from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
import uvicorn
import logging
import time
import traceback
import os
import json
import math
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
    vehicle_count: int = Field(1, ge=1, description="Number of vehicles")
    depot: int = Field(0, ge=0, description="Depot index in locations")
    demands: Optional[List[int]] = Field(None, description="Demand at each location")
    capacities: Optional[List[int]] = Field(None, description="Vehicle capacities")
    time_windows: Optional[List[Tuple[int, int]]] = Field(None, description="Time windows for each location")

class NodeSearchRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    radius: float = Field(1000, ge=100, le=10000, description="Search radius in meters")

app = FastAPI(
    title="BMSSP Routing API",
    description="Production-ready vehicle routing service using BMSSP algorithm",
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

@app.post("/search-nodes")
async def search_nodes(request: NodeSearchRequest):
    """Find nearest nodes to a coordinate within radius."""
    try:
        from graph_loader import find_nearest_nodes
        nodes = find_nearest_nodes(request.lat, request.lon, request.radius)
        return {"nodes": nodes}
    except Exception as e:
        logger.error(f"Error searching nodes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search nodes")

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

@app.post("/distance-matrix")
async def get_distance_matrix(locations: List[str]):
    """Compute distance matrix between locations using BMSSP with production fallbacks."""
    try:
        start_time = time.time()
        mat, meta = compute_matrix_with_fallback(locations, place=None)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing distance matrix: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to compute distance matrix")

@app.post("/vrp")
async def solve_vehicle_routing(request: VRPRequest):
    """Solve Vehicle Routing Problem with capacity and time window constraints."""
    try:
        start_time = time.time()
        
        # Validate inputs
        if request.depot >= len(request.locations):
            raise HTTPException(status_code=400, detail="Depot index out of range")
        
        if request.demands and len(request.demands) != len(request.locations):
            raise HTTPException(status_code=400, detail="Demands length must match locations length")
        
        if request.capacities and len(request.capacities) != request.vehicle_count:
            raise HTTPException(status_code=400, detail="Capacities length must match vehicle count")
        
        if request.time_windows and len(request.time_windows) != len(request.locations):
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
            request.time_windows
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
        
        # Determine status
        status = solution.get("status", "OK")
        if total_distance is None or any(v is None for v in vehicle_distances):
            status = "PARTIAL_OR_UNREACHABLE"
        if (meta.get("fallback_counts", {}).get("symmetric", 0) + meta.get("fallback_counts", {}).get("haversine", 0)) > 0:
            status = "APPROXIMATED"
        
        location_coords = {}
        for loc in request.locations:
            coords = get_node_coordinates(loc)
            if coords:
                location_coords[loc] = {"lat": coords[0], "lon": coords[1]}

        # Build full path geometries for each route
        from graph_loader import get_full_path_coordinates
        route_geometries = []
        for route in solution.get("routes", []):
            route_path = []
            for i in range(len(route) - 1):
                start_idx = route[i]
                end_idx = route[i+1]
                start_id = request.locations[start_idx]
                end_id = request.locations[end_idx]
                segment = get_full_path_coordinates(start_id, end_id)
                if segment:
                    # Avoid duplicating points
                    if route_path and segment[0] == route_path[-1]:
                        route_path.extend(segment[1:])
                    else:
                        route_path.extend(segment)
            route_geometries.append(route_path)

        response = {
            "locations": request.locations,
            "routes": solution.get("routes", []),
            "route_locations": [[request.locations[i] for i in route] for route in solution.get("routes", [])],
            "location_coordinates": location_coords,
            "route_geometries": route_geometries,
            "total_distance": total_distance,
            "vehicle_distances": vehicle_distances,
            "status": status,
            "computation_times": {
                "matrix_computation": matrix_time,
                "vrp_solving": vrp_time,
                "total": total_time
            },
            "metadata": {
                **meta,
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error solving VRP: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to solve VRP")

@app.get("/stats")
async def get_system_stats():
    """Get system statistics and performance metrics."""
    try:
        from graph_loader import get_graph_stats
        stats = get_graph_stats()
        return {
            "graph_stats": stats,
            "api_version": "1.0.0",
            "algorithm": "BMSSP (Bidirectional Multi-Source Shortest Path)"
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