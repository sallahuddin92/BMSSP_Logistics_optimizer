"""Native exact logistics transaction: one snapshot, matrix and retained SSSP set."""
import math
import json
from time import perf_counter
import numpy as np
from native_graph import snapshot_cache, RoutingLimits, RoutingBudgetExceeded, normalize_node_id, positive_budget
from routing_adapter import compute_native_matrix
from vrp_solver import solve_vrp
from road_geometry import assemble_geometry, close


def native_vrp(request, selected):
    from graph_loader import load_native_graph
    start = perf_counter()
    locations = request.locations
    nodes = [normalize_node_id(x) for x in locations]
    if len(set(nodes)) != len(nodes):
        raise ValueError('Duplicate node identities are unsupported for VRP stops; submit each physical stop once')
    if len(nodes) > positive_budget('VRP_MAX_LOCATIONS', 32):
        raise RoutingBudgetExceeded('VRP location budget exceeded')
    limits = RoutingLimits.from_environment()
    graph = load_native_graph(request.place)
    snapshot, capture = snapshot_cache.get(graph, limits=limits)
    matrix_start = perf_counter()
    results = {}
    matrix, metadata = compute_native_matrix(snapshot, locations, selected, limits, source_results=results)
    matrix_time = perf_counter()-matrix_start
    path_time = geometry_time = 0.0
    durations = request.duration_matrix
    duration_provenance = None
    if durations is not None:
        durations = [[math.inf if x is None else x for x in row] for row in durations]
        duration_provenance = 'caller_supplied_seconds_for_submitted_pairs'
    elif request.time_windows is not None:
        durations = np.full(matrix.shape, np.inf)
        for i, source in enumerate(nodes):
            for j, target in enumerate(nodes):
                if math.isfinite(matrix[i,j]):
                    path = results[source].path(target)
                    times = [snapshot.road_data.edges[e].travel_time for e in path['edges']]
                    if any(x is None for x in times):
                        raise ValueError('Time windows require a duration_matrix in seconds or valid travel_time on every selected road edge')
                    durations[i,j] = math.fsum(times)
        duration_provenance = 'sum_of_travel_time_seconds_on_selected_distance_shortest_paths'
    solve_start = perf_counter()
    solution = solve_vrp(matrix, request.vehicle_count, request.depot, request.demands, request.capacities,
                         request.time_windows, request.max_search_seconds, duration_matrix=durations,
                         service_durations=request.service_durations, vehicle_start_windows=request.vehicle_start_windows,
                         vehicle_end_windows=request.vehicle_end_windows, max_wait_seconds=request.max_wait_seconds)
    solve_time = perf_counter()-solve_start
    if solution['status'] == 'NO_SOLUTION' and any(not math.isfinite(matrix[request.depot,i]) or not math.isfinite(matrix[i,request.depot]) for i in range(len(nodes))):
        solution['reason'] = 'A mandatory stop cannot be reached from the depot or cannot return along directed roads'
    if solution['status'] == 'INVALID_INPUT':
        raise ValueError(solution['reason'])
    vehicle_legs, geometries, all_segments = [], [], []
    geometry_points = 0
    path_edges = 0
    for route in solution['routes']:
        legs, segments, continuous = [], [], []
        full_geometry = True
        for a, b in zip(route, route[1:]):
            clock = perf_counter()
            path = snapshot.original_path(results[nodes[a]], nodes[b])
            if not path['reachable'] or path['distance'] != matrix[a,b]:
                raise RuntimeError('Native route-leg matrix/path inconsistency')
            if not path['vertices'] or path['vertices'][0] != nodes[a] or path['vertices'][-1] != nodes[b] or len(path['vertices']) != len(path['edges'])+1:
                raise RuntimeError('Native route-leg endpoint or path-size inconsistency')
            edges = path['edges']
            path_edges += len(edges)
            if path_edges > positive_budget('VRP_MAX_PATH_EDGES', 100000):
                raise RoutingBudgetExceeded('VRP path response budget exceeded')
            total = 0.0
            for edge_id, u, v in zip(edges, path['vertices'], path['vertices'][1:]):
                old_u, old_v, key = snapshot.original_edges[edge_id]
                if normalize_node_id(old_u) != u or normalize_node_id(old_v) != v:
                    raise RuntimeError('Original directed edge mapping mismatch')
                total += snapshot.road_data.edges[edge_id].length
            if total != matrix[a,b]:
                raise RuntimeError('Original selected edge weights disagree with matrix')
            path_time += perf_counter()-clock
            clock = perf_counter()
            points, geometry_status = assemble_geometry(snapshot, edges, path['vertices'])
            geometry_points += len(points)
            if geometry_points > positive_budget('VRP_MAX_GEOMETRY_POINTS', 100000):
                raise RoutingBudgetExceeded('VRP geometry response budget exceeded')
            if not points:
                full_geometry = False
                if continuous:
                    segments.append(continuous); continuous = []
            else:
                if continuous and not close(continuous[-1], points[0]):
                    full_geometry = False
                    segments.append(continuous); continuous = []
                continuous.extend(points[1:] if continuous else points)
            geometry_time += perf_counter()-clock
            legs.append({'from_index': a, 'to_index': b, 'source': locations[a], 'target': locations[b], 'native_source': str(nodes[a]), 'native_target': str(nodes[b]),
                         'distance': float(matrix[a,b]), 'duration_seconds': float(durations[a][b]) if durations is not None else None, 'path_status': 'VERIFIED', 'geometry_status': geometry_status,
                         'vertices': [str(x) for x in path['original_vertices']], 'edge_ids': [str(x) for x in edges],
                         'original_edges': [{'u': str(u), 'v': str(v), 'key': str(k), 'key_type': type(k).__name__} for u,v,k in path['original_edges']],
                         'geometry': points})
        if continuous:
            segments.append(continuous)
        vehicle_legs.append(legs)
        geometries.append(segments[0] if full_geometry and len(segments) == 1 else [])
        all_segments.append(segments)
    for d in metadata['native_execution_diagnostics']['sources']:
        d['source'] = str(d['source'])
    response = {
        'locations': locations, 'routes': solution['routes'],
        'route_locations': [[locations[i] for i in route] for route in solution['routes']],
        'location_coordinates': {location: {'lat': snapshot.road_data.nodes[node][0], 'lon': snapshot.road_data.nodes[node][1]} for location, node in zip(locations, nodes) if snapshot.road_data.nodes[node] is not None},
        'route_geometries': geometries, 'route_geometry_segments': all_segments, 'route_legs': vehicle_legs,
        'total_distance': solution['total_distance'], 'vehicle_distances': solution['vehicle_distances'],
        'status': solution['status'], 'solver_status': solution['solver_status'],
        'route_feasibility': solution['route_feasibility'], 'selected_engine': selected,
        'graph_snapshot': snapshot.snapshot_id, 'exact_routing': True, 'weight_units': 'meters',
        'duration_units': solution['duration_units'], 'schedules': solution.get('schedules', []),
        'vehicle_loads': solution.get('vehicle_loads', []),
        'computation_times': {'matrix_computation': matrix_time, 'vrp_solving': solve_time,
                              'path_reconstruction': path_time, 'geometry_assembly': geometry_time,
                              'total': perf_counter()-start},
        'metadata': {**metadata, **capture, 'road_provenance': json.loads(snapshot.provenance_json) or None, 'duration_provenance': duration_provenance,
                     'objective_value': str(solution['objective_value']) if 'objective_value' in solution else None,
                     'time_scale': solution.get('time_scale'), 'cost_scale': solution.get('cost_scale'),
                     'objective_units': solution.get('objective_units'), 'forbidden_transition_count': solution.get('forbidden_transition_count'),
                     'reason': solution.get('reason'), 'vehicle_count': request.vehicle_count, 'depot': request.depot,
                     'has_demands': request.demands is not None, 'has_capacities': request.capacities is not None,
                     'has_time_windows': request.time_windows is not None},
    }
    return response
