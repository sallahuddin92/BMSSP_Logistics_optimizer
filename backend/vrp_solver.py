from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import numpy as np
import logging
from typing import List, Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def solve_vrp(
    distance_matrix: np.ndarray, 
    vehicle_count: int = 1, 
    depot: int = 0,
    demands: Optional[List[int]] = None, 
    vehicle_capacities: Optional[List[int]] = None, 
    time_windows: Optional[List[Tuple[int, int]]] = None,
    max_search_seconds: int = 30
) -> Dict[str, Any]:
    """
    Solve Vehicle Routing Problem using OR-Tools.
    
    Args:
        distance_matrix: NxN distance matrix
        vehicle_count: Number of vehicles
        depot: Depot node index
        demands: Demand at each location
        vehicle_capacities: Capacity for each vehicle
        time_windows: Time windows for each location
        max_search_seconds: Maximum search time in seconds
        
    Returns:
        Dictionary containing routes and solution metrics
    """
    n = len(distance_matrix)
    
    # Validate inputs
    if depot >= n:
        raise ValueError(f"Depot index {depot} out of range for {n} locations")
    
    if demands and len(demands) != n:
        raise ValueError(f"Demands length {len(demands)} must match locations {n}")
    
    if vehicle_capacities and len(vehicle_capacities) != vehicle_count:
        raise ValueError(f"Vehicle capacities length {len(vehicle_capacities)} must match vehicle count {vehicle_count}")
    
    if time_windows and len(time_windows) != n:
        raise ValueError(f"Time windows length {len(time_windows)} must match locations {n}")
    
    # Create routing model
    manager = pywrapcp.RoutingIndexManager(n, vehicle_count, depot)
    routing = pywrapcp.RoutingModel(manager)
    
    # Distance callback
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        distance = distance_matrix[from_node][to_node]
        # Convert to integer (OR-Tools requirement) and handle infinity
        if np.isinf(distance):
            return 999999999  # Large penalty for unreachable nodes
        return int(distance * 1000)  # Scale up for precision
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Add capacity constraints
    if demands and vehicle_capacities:
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            "Capacity"
        )
        
        logger.info(f"Added capacity constraints: demands={demands}, capacities={vehicle_capacities}")
    
    # Add time window constraints
    if time_windows:
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            distance = distance_matrix[from_node][to_node]
            if np.isinf(distance):
                return 999999
            # Assume travel time equals distance (can be modified for different units)
            return int(distance)
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            30,  # allow waiting time
            300000,  # maximum time per vehicle
            False,  # don't force start cumul to zero
            "Time"
        )
        
        time_dimension = routing.GetDimensionOrDie("Time")
        
        # Add time window constraints for each location
        for location_idx, time_window in enumerate(time_windows):
            if location_idx == depot:
                continue  # Skip depot
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        
        # Add time window constraint for depot (if specified)
        if len(time_windows) > depot:
            depot_index = manager.NodeToIndex(depot)
            time_dimension.CumulVar(depot_index).SetRange(time_windows[depot][0], time_windows[depot][1])
        
        logger.info(f"Added time window constraints: {time_windows}")
    
    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.FromSeconds(max_search_seconds)
    
    logger.info(f"Solving VRP with {n} locations, {vehicle_count} vehicles, depot at {depot}")
    
    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        return _extract_solution(manager, routing, solution, distance_matrix)
    else:
        logger.error("No solution found for VRP")
        # Return empty solution
        return {
            "routes": [[] for _ in range(vehicle_count)],
            "total_distance": float('inf'),
            "vehicle_distances": [float('inf')] * vehicle_count,
            "status": "NO_SOLUTION",
            "objective_value": float('inf')
        }

def _extract_solution(
    manager: pywrapcp.RoutingIndexManager,
    routing: pywrapcp.RoutingModel,
    solution: pywrapcp.Assignment,
    distance_matrix: np.ndarray
) -> Dict[str, Any]:
    """Extract solution from OR-Tools solver. Includes the final leg back to depot."""
    routes = []
    vehicle_distances = []
    total_distance = 0.0
    
    for vehicle_id in range(manager.GetNumberOfVehicles()):
        index = routing.Start(vehicle_id)
        route = []
        route_distance = 0.0
        previous_index = None
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            
            # Add distance for this hop if next is not the end node
            if not routing.IsEnd(index):
                from_node = manager.IndexToNode(previous_index)
                to_node = manager.IndexToNode(index)
                hop_distance = distance_matrix[from_node][to_node]
                route_distance += hop_distance
        
        # index is now the end node; append it (typically the depot)
        final_node = manager.IndexToNode(index)
        route.append(final_node)
        
        # Add the final leg from the last visited node to the depot/end
        if previous_index is not None:
            from_node = manager.IndexToNode(previous_index)
            to_node = final_node
            last_leg = distance_matrix[from_node][to_node]
            route_distance += last_leg
        
        routes.append(route)
        vehicle_distances.append(route_distance)
        total_distance += route_distance
    
    # Get objective value (scaled back)
    objective_value = solution.ObjectiveValue() / 1000.0
    
    logger.info(f"Solution found: total_distance={total_distance:.2f}, routes={len([r for r in routes if len(r) > 2])}")
    
    return {
        "routes": routes,
        "total_distance": total_distance,
        "vehicle_distances": vehicle_distances,
        "status": "OPTIMAL" if solution else "FEASIBLE",
        "objective_value": objective_value,
        "vehicle_count": len(routes),
        "total_locations": sum(len(route) - 1 for route in routes)  # Exclude depot duplicates
    }