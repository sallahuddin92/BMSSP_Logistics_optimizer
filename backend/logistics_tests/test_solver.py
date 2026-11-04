import itertools
import math
import random
import numpy as np
import pytest
from vrp_solver import solve_vrp, scaled, COST_SCALE


def verify(matrix, solution, demands=None, capacities=None):
    assert solution['status'] == 'FEASIBLE'
    visited=[]; totals=[]
    for v, route in enumerate(solution['routes']):
        assert route[0] == route[-1] == 0
        visited += route[1:-1]
        total = math.fsum(matrix[a][b] for a,b in zip(route,route[1:]))
        assert math.isfinite(total)
        assert solution['vehicle_distances'][v] == total
        totals.append(total)
        if demands is not None:
            assert sum(demands[x] for x in route[1:-1]) <= capacities[v]
    assert sorted(visited) == list(range(1,len(matrix)))
    assert solution['total_distance'] == math.fsum(totals)
    assert solution['objective_value'] == sum(scaled(matrix[a][b],COST_SCALE) for r in solution['routes'] for a,b in zip(r,r[1:]))


def test_unreachable_return_and_vehicle_end_domains():
    for count in [1,2,3]:
        result=solve_vrp([[0,1],[math.inf,0]], vehicle_count=count)
        assert result['status']=='NO_SOLUTION'
        assert not result['route_feasibility'] and result['routes']==[]
        assert result['solver_status']=='ROUTING_INFEASIBLE'
        assert result['forbidden_transition_count'] >= count


def test_hard_arcs_with_multiple_routes():
    matrix=[[0,1,1],[1,0,math.inf],[1,math.inf,0]]
    assert solve_vrp(matrix,vehicle_count=1)['status']=='NO_SOLUTION'
    actual=solve_vrp(matrix,vehicle_count=2,demands=[0,1,1],vehicle_capacities=[1,1])
    verify(matrix, actual, [0,1,1], [1,1])


@pytest.mark.parametrize('seed', [2025,17033,45141])
def test_seeded_feasible_and_infeasible_and_independent_tours(seed):
    rng=random.Random(seed)
    matrix=[[0 if i==j else rng.randrange(1,21)/4 for j in range(6)] for i in range(6)]
    solution=solve_vrp(matrix)
    verify(matrix,solution)
    feasible_tours=[(0,)+p+(0,) for p in itertools.permutations(range(1,6))]
    actual=tuple(solution['routes'][0]); assert actual in feasible_tours
    assert solution['total_distance']==math.fsum(matrix[a][b] for a,b in zip(actual,actual[1:]))
    demands=[0,1,1,1,1,1]
    verify(matrix,solve_vrp(matrix,vehicle_count=2,demands=demands,vehicle_capacities=[3,3]),demands,[3,3])
    assert solve_vrp(matrix,vehicle_count=2,demands=demands,vehicle_capacities=[2,2])['status']=='NO_SOLUTION'


def test_zero_constraints_rounding_and_overflow():
    verify([[0,0],[0,0]],solve_vrp([[0,0],[0,0]],demands=[0,0],vehicle_capacities=[0]),[0,0],[0])
    assert scaled(0,1000)==0 and scaled(.00001,1000)==1
    for x in [0,.00001,.0005,.0015,1.125,9.9999]:
        assert abs(scaled(x,1000)/1000-x) < .0011
    with pytest.raises(ValueError):solve_vrp([[0,1e18],[1e18,0]])
    with pytest.raises(ValueError):solve_vrp([[0,1],[1,0]],demands=[0,1])
    with pytest.raises(ValueError):solve_vrp([[0,1],[1,0]],vehicle_capacities=[1])
    for demand in [-1,True,1.5,2**63]:
        with pytest.raises(ValueError):solve_vrp([[0,1],[1,0]],demands=[0,demand],vehicle_capacities=[10])


def test_time_windows_service_wait_and_every_depot_end():
    matrix=[[0,100],[100,0]]
    args=dict(time_windows=[(0,30),(10,20)],duration_matrix=[[0,3],[3,0]],service_durations=[0,2])
    result=solve_vrp(matrix,**args)
    verify(matrix,result)
    times=result['schedules'][0]
    assert times[1]['arrival_seconds']>=10
    for j in range(len(times)-1):
        assert times[j+1]['arrival_seconds']==times[j]['arrival_seconds']+times[j]['waiting_seconds']+times[j]['service_seconds']+3
    assert times[-1]['arrival_seconds']<=30
    for count in [1,2]:
        result=solve_vrp(matrix,vehicle_count=count,time_windows=[(0,5),(0,20)],duration_matrix=[[0,3],[3,0]])
        assert result['status']=='NO_SOLUTION'
    assert solve_vrp(matrix,time_windows=[(0,30),(0,30)],duration_matrix=[[0,3],[3,0]],vehicle_start_windows=[(20,25)],vehicle_end_windows=[(0,15)])['status']=='NO_SOLUTION'
    assert solve_vrp(matrix,time_windows=[(0,30),(0,30)])['status']=='INVALID_INPUT'


@pytest.mark.parametrize('kwargs', [
 {'time_windows':[(0,10),(5,1)],'duration_matrix':[[0,1],[1,0]]},
 {'time_windows':[(0,10),(0,10)],'duration_matrix':[[0,math.inf],[1,0]]},
 {'time_windows':[(0,10),(0,10)],'duration_matrix':[[0,-1],[1,0]]},
 {'service_durations':[0,1]}, {'demands':[0,-1],'vehicle_capacities':[1]},
 {'demands':[0,0],'vehicle_capacities':[-1]}, {'max_search_seconds':0},
 {'vehicle_count':0}, {'time_windows':[(0,10),(0,10)],'duration_matrix':[[0,1],[1,0]],'vehicle_start_windows':[]}
])
def test_invalid_input(kwargs):
    with pytest.raises(ValueError):solve_vrp([[0,1],[1,0]],**kwargs)


def test_fractional_seconds_preserve_physical_wait_and_service():
    result=solve_vrp([[0,10],[10,0]],time_windows=[(0,5),(1,4)],duration_matrix=[[0,.1],[.2,0]],service_durations=[0,.25],max_wait_seconds=2)
    assert result['status']=='FEASIBLE'
    plan=result['schedules'][0]
    assert plan[1]['service_seconds']==.25
    assert all(0<=p['waiting_seconds']<=2 for p in plan)
    assert plan[1]['arrival_seconds']>=1


@pytest.mark.parametrize('code,expected', [(4,'TIMEOUT'),(3,'NO_SOLUTION'),(0,'FAILED')])
def test_injected_solver_status_is_not_relabelled_as_success(monkeypatch,code,expected):
    from ortools.constraint_solver import pywrapcp
    monkeypatch.setattr(pywrapcp.RoutingModel,'SolveWithParameters',lambda *a:None)
    monkeypatch.setattr(pywrapcp.RoutingModel,'status',lambda *a:code)
    result=solve_vrp([[0,1],[1,0]])
    assert result['status']==expected and not result['route_feasibility'] and result['routes']==[]
