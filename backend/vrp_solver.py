"""Checked mandatory-stop routing. Distance is meters; time is explicitly seconds."""
import math
import numbers
from fractions import Fraction
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import numpy as np
from native_graph import positive_budget, RoutingBudgetExceeded

SAFE = (2**63 - 1) // 8
COST_SCALE = 1000
TIME_SCALE = 1000


def integer(value, label, maximum=SAFE):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral) or not 0 <= value <= maximum:
        raise ValueError(f'{label} must be a nonnegative representable integer')
    return int(value)


def scaled(value, scale, mode='nearest'):
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value) or value < 0:
        raise ValueError('Costs and seconds must be finite nonnegative numbers')
    numerator, denominator = float(value).as_integer_ratio()
    quotient, remainder = divmod(numerator * scale, denominator)
    result = quotient + (int(2*remainder >= denominator) if mode == 'nearest' else
                         int(remainder != 0) if mode == 'ceil' else 0)
    if mode == 'nearest' and value > 0:
        result = max(1, result)
    if result > SAFE:
        raise ValueError('Scaled value exceeds safe signed-64-bit budget')
    return result


def solve_vrp(distance_matrix, vehicle_count=1, depot=0, demands=None,
              vehicle_capacities=None, time_windows=None, max_search_seconds=1,
              duration_matrix=None, service_durations=None,
              vehicle_start_windows=None, vehicle_end_windows=None, max_wait_seconds=86400):
    matrix = np.asarray(distance_matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or not len(matrix):
        raise ValueError('Distance matrix must be nonempty and square')
    n = len(matrix)
    if n > positive_budget('VRP_MAX_LOCATIONS', 32):
        raise RoutingBudgetExceeded('VRP location budget exceeded')
    vehicle_count = integer(vehicle_count, 'Vehicle count')
    if not 1 <= vehicle_count <= positive_budget('VRP_MAX_VEHICLES', 10):
        raise RoutingBudgetExceeded('Vehicle count exceeds VRP budget')
    if isinstance(depot, bool) or not isinstance(depot, numbers.Integral) or not 0 <= depot < n:
        raise ValueError(f'Depot index {depot} out of range for {n} locations')
    max_search_seconds = integer(max_search_seconds, 'Search seconds')
    if not 1 <= max_search_seconds <= positive_budget('VRP_MAX_SEARCH_SECONDS', 10):
        raise RoutingBudgetExceeded('VRP search budget exceeded')
    if np.isnan(matrix).any() or (matrix < 0).any() or not np.all(np.diag(matrix) == 0):
        raise ValueError('Distances require zero diagonal and nonnegative meters or positive infinity')
    if demands is not None and len(demands) != n:
        raise ValueError(f'Demands length {len(demands)} must match locations {n}')
    if vehicle_capacities is not None and len(vehicle_capacities) != vehicle_count:
        raise ValueError(f'Vehicle capacities length {len(vehicle_capacities)} must match vehicle count {vehicle_count}')
    if (demands is None) != (vehicle_capacities is None):
        raise ValueError('Demands and vehicle capacities must be provided together')
    if demands is not None:
        demands = [integer(x, 'Demand') for x in demands]
        vehicle_capacities = [integer(x, 'Capacity') for x in vehicle_capacities]
        if demands[depot] != 0 or sum(demands) > SAFE:
            raise ValueError('Depot demand must be zero; total demand must fit the safe integer budget')
    if time_windows is not None and len(time_windows) != n:
        raise ValueError('Time windows length must match locations')
    if time_windows is not None and duration_matrix is None:
        # Historical low-level callers receive an explicit failed structure, never
        # distance-as-time. API callers convert this status to a validation error.
        return {'routes': [[] for _ in range(vehicle_count)], 'vehicle_distances': [],
                'total_distance': None, 'status': 'INVALID_INPUT', 'route_feasibility': False,
                'reason': 'Time windows require duration_matrix in seconds'}
    if time_windows is None and any(x is not None for x in (duration_matrix, service_durations, vehicle_start_windows, vehicle_end_windows)):
        raise ValueError('Service and vehicle time constraints require time windows')
    costs = [[scaled(x, COST_SCALE) if math.isfinite(x) else None for x in row] for row in matrix]
    max_cost = max(x for row in costs for x in row if x is not None)
    if max_cost * (n - 1 + vehicle_count) > SAFE:
        raise ValueError('Total route objective exceeds safe signed-64-bit budget')
    durations = services = windows = starts = ends = None
    raw_services = None
    horizon = 0
    if time_windows is not None:
        durations_array = np.asarray(duration_matrix, dtype=float)
        if durations_array.shape != matrix.shape or np.isnan(durations_array).any() or (durations_array < 0).any():
            raise ValueError('Duration matrix must match distances, in nonnegative seconds')
        if not np.all(np.diag(durations_array) == 0) or not np.isfinite(durations_array[np.isfinite(matrix)]).all():
            raise ValueError('Every reachable pair requires a finite duration; diagonal must be zero')
        durations = [[scaled(x, TIME_SCALE, 'ceil') if math.isfinite(x) else 0 for x in row] for row in durations_array]
        if service_durations is not None and len(service_durations) != n:
            raise ValueError('Service durations length must match locations')
        raw_services = service_durations if service_durations is not None else [0]*n
        services = [scaled(x, TIME_SCALE, 'ceil') for x in raw_services]
        def window(pair):
            if len(pair) != 2:
                raise ValueError('Time windows require start and end seconds')
            lower, upper = scaled(pair[0], TIME_SCALE, 'ceil'), scaled(pair[1], TIME_SCALE, 'floor')
            if lower > upper or upper > positive_budget('VRP_MAX_TIME_SECONDS', 604800)*TIME_SCALE:
                raise ValueError('Invalid or excessive time window')
            return lower, upper
        windows = [window(pair) for pair in time_windows]
        def vehicle_windows(values):
            if values is None:
                return [windows[depot]] * vehicle_count
            if len(values) != vehicle_count:
                raise ValueError('Vehicle window count must match vehicle count')
            return [(max(window(p)[0], windows[depot][0]), min(window(p)[1], windows[depot][1])) for p in values]
        starts, ends = vehicle_windows(vehicle_start_windows), vehicle_windows(vehicle_end_windows)
        if any(lo > hi for lo, hi in starts+ends):
            raise ValueError('Vehicle and depot windows do not intersect')
        horizon = max(hi for lo, hi in windows+starts+ends)
        if (max(max(row) for row in durations)+max(services))*(n+vehicle_count) > SAFE:
            raise ValueError('Total duration exceeds safe integer budget')
    manager = pywrapcp.RoutingIndexManager(n, vehicle_count, int(depot))
    routing = pywrapcp.RoutingModel(manager)
    callback = routing.RegisterTransitCallback(lambda a,b: costs[manager.IndexToNode(a)][manager.IndexToNode(b)] or 0)
    routing.SetArcCostEvaluatorOfAllVehicles(callback)
    forbidden = 0
    # Include all replicated vehicle starts and ends, not just NodeToIndex(depot).
    for a in range(routing.Size()):
        for b in range(manager.GetNumberOfIndices()):
            if costs[manager.IndexToNode(a)][manager.IndexToNode(b)] is None:
                routing.NextVar(a).RemoveValue(b)
                forbidden += 1
    if demands is not None:
        demand_callback = routing.RegisterUnaryTransitCallback(lambda a: demands[manager.IndexToNode(a)])
        routing.AddDimensionWithVehicleCapacity(demand_callback, 0, vehicle_capacities, True, 'Capacity')
    time_dimension = None
    if durations is not None:
        time_callback = routing.RegisterTransitCallback(lambda a,b: durations[manager.IndexToNode(a)][manager.IndexToNode(b)] + services[manager.IndexToNode(a)])
        wait = scaled(max_wait_seconds, TIME_SCALE, 'floor')
        maximum_wait = Fraction.from_float(float(max_wait_seconds))
        reserve = max(Fraction(durations[a][b]+services[a], TIME_SCALE) - Fraction.from_float(float(durations_array[a,b])) - Fraction.from_float(float(raw_services[a]))
                      for a in range(n) for b in range(n) if math.isfinite(matrix[a,b]))
        if reserve > maximum_wait:
            raise ValueError('Waiting budget is insufficient for conservative millisecond rounding; use exactly representable times or allow rounding reserve')
        slack = int((maximum_wait-reserve)*TIME_SCALE)
        if wait > positive_budget('VRP_MAX_TIME_SECONDS', 604800)*TIME_SCALE:
            raise ValueError('Waiting allowance exceeds time budget')
        routing.AddDimension(time_callback, slack, horizon, False, 'Time')
        time_dimension = routing.GetDimensionOrDie('Time')
        for node in range(n):
            if node != depot:
                time_dimension.CumulVar(manager.NodeToIndex(node)).SetRange(*windows[node])
        for vehicle in range(vehicle_count):
            time_dimension.CumulVar(routing.Start(vehicle)).SetRange(*starts[vehicle])
            time_dimension.CumulVar(routing.End(vehicle)).SetRange(*ends[vehicle])
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(vehicle)))
            routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(vehicle)))
    parameters = pywrapcp.DefaultRoutingSearchParameters()
    parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT
    parameters.time_limit.FromSeconds(max_search_seconds)
    assignment = routing.SolveWithParameters(parameters)
    code = routing.status()
    names = {getattr(pywrapcp.RoutingModel, x): x for x in dir(pywrapcp.RoutingModel) if x.startswith('ROUTING_')}
    status_name = names.get(code, f'UNKNOWN_{code}')
    common = {'solver_status': status_name, 'solver_status_code': code, 'vehicle_count': vehicle_count,
              'cost_scale': COST_SCALE, 'weight_units': 'meters', 'duration_units': 'seconds' if durations is not None else None,
              'forbidden_transition_count': forbidden, 'time_scale': TIME_SCALE if durations is not None else None}
    if assignment is None:
        if code == pywrapcp.RoutingModel.ROUTING_INVALID:
            raise RuntimeError('OR-Tools rejected the routing model')
        status = ('TIMEOUT' if code == pywrapcp.RoutingModel.ROUTING_FAIL_TIMEOUT else
                  'NO_SOLUTION' if code in (pywrapcp.RoutingModel.ROUTING_FAIL, pywrapcp.RoutingModel.ROUTING_INFEASIBLE) else 'FAILED')
        return {**common, 'status': status, 'routes': [], 'total_distance': None, 'vehicle_distances': [],
                'route_feasibility': False, 'reason': 'No assignment established; infeasibility is not claimed unless solver status proves it'}
    routes, vehicle_distances, schedules, loads = [], [], [], []
    visited = []
    for vehicle in range(vehicle_count):
        index = routing.Start(vehicle)
        indices, route = [index], [int(depot)]
        while not routing.IsEnd(index):
            index = assignment.Value(routing.NextVar(index))
            indices.append(index)
            route.append(manager.IndexToNode(index))
            if len(route) > n+2:
                raise RuntimeError('Routing assignment contains a cycle')
        distance = math.fsum(float(matrix[a,b]) for a,b in zip(route, route[1:]))
        if not math.isfinite(distance):
            raise RuntimeError('Solver selected a forbidden directed transition')
        visited.extend(route[1:-1])
        load = sum(demands[x] for x in route[1:-1]) if demands is not None else 0
        if demands is not None and load > vehicle_capacities[vehicle]:
            raise RuntimeError('Solver capacity post-validation failed')
        schedule = []
        if time_dimension is not None:
            times = [assignment.Value(time_dimension.CumulVar(i)) for i in indices]
            for j, (node, arrival) in enumerate(zip(route, times)):
                lo, hi = starts[vehicle] if j == 0 else ends[vehicle] if j == len(route)-1 else windows[node]
                if not lo <= arrival <= hi:
                    raise RuntimeError('Solver time-window post-validation failed')
                waiting = 0
                service = services[node] if j < len(route)-1 else 0
                if j < len(route)-1:
                    waiting = times[j+1]-arrival-service-durations[node][route[j+1]]
                    if waiting < 0 or waiting > slack:
                        raise RuntimeError('Solver travel/service/wait post-validation failed')
                actual_service = float(raw_services[node]) if j < len(route)-1 else 0.0
                actual_wait = Fraction(0)
                if j < len(route)-1:
                    actual_wait = Fraction(times[j+1]-arrival, TIME_SCALE) - Fraction.from_float(actual_service) - Fraction.from_float(float(durations_array[node,route[j+1]]))
                    if actual_wait < 0 or actual_wait > maximum_wait:
                        raise RuntimeError('Original seconds schedule post-validation failed')
                schedule.append({'location_index': node, 'arrival_seconds': arrival/TIME_SCALE,
                                 'service_seconds': actual_service, 'waiting_seconds': float(actual_wait),
                                 'model_service_seconds': service/TIME_SCALE, 'model_waiting_seconds': waiting/TIME_SCALE})
        routes.append(route); vehicle_distances.append(distance); schedules.append(schedule); loads.append(load)
    if sorted(visited) != [x for x in range(n) if x != depot]:
        raise RuntimeError('Mandatory customer coverage post-validation failed')
    objective = sum(costs[a][b] for route in routes for a,b in zip(route,route[1:]) if len(route)>2)
    if objective != assignment.ObjectiveValue():
        raise RuntimeError('Integer objective post-validation failed')
    total = math.fsum(vehicle_distances)
    if not math.isfinite(total):
        raise RuntimeError('Original meter total overflowed')
    return {**common, 'status': 'FEASIBLE', 'route_feasibility': True, 'routes': routes,
            'vehicle_distances': vehicle_distances, 'total_distance': total, 'vehicle_loads': loads,
            'schedules': schedules, 'objective_value': assignment.ObjectiveValue(),
            'objective_units': 'scaled_meter_cost', 'total_locations': len(visited)}
