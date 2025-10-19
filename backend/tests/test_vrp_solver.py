"""
Test the VRP solver functionality.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vrp_solver import solve_vrp


class TestVRPSolver:
    """Test cases for the VRP solver."""
    
    def setup_method(self):
        """Set up test data."""
        self.sample_matrix = np.array([
            [0.0, 100.0, 200.0, 150.0],
            [100.0, 0.0, 120.0, 80.0],
            [200.0, 120.0, 0.0, 90.0],
            [150.0, 80.0, 90.0, 0.0]
        ])
    
    def test_basic_vrp_solving(self):
        """Test basic VRP solving without constraints."""
        result = solve_vrp(
            distance_matrix=self.sample_matrix,
            vehicle_count=1,
            depot=0
        )
        
        assert isinstance(result, dict)
        assert "routes" in result
        assert "total_distance" in result
        assert "status" in result
        assert len(result["routes"]) == 1
        assert result["routes"][0][0] == 0  # Route starts at depot
        assert result["routes"][0][-1] == 0  # Route ends at depot
    
    def test_multiple_vehicles(self):
        """Test VRP with multiple vehicles."""
        result = solve_vrp(
            distance_matrix=self.sample_matrix,
            vehicle_count=2,
            depot=0
        )
        
        assert len(result["routes"]) == 2
        assert result["vehicle_count"] == 2
        
        # Both routes should start and end at depot
        for route in result["routes"]:
            if len(route) > 1:  # Non-empty route
                assert route[0] == 0
                assert route[-1] == 0
    
    def test_capacity_constraints(self):
        """Test VRP with capacity constraints."""
        demands = [0, 10, 15, 20]  # Depot has 0 demand
        capacities = [25, 25]  # Two vehicles with capacity 25 each
        
        result = solve_vrp(
            distance_matrix=self.sample_matrix,
            vehicle_count=2,
            depot=0,
            demands=demands,
            vehicle_capacities=capacities
        )
        
        assert isinstance(result, dict)
        assert "routes" in result
        # Solution should respect capacity constraints
        for i, route in enumerate(result["routes"]):
            route_demand = sum(demands[node] for node in route)
            assert route_demand <= capacities[i] if i < len(capacities) else True
    
    def test_time_windows(self):
        """Test VRP with time window constraints."""
        time_windows = [(0, 100), (10, 50), (20, 80), (30, 90)]
        
        result = solve_vrp(
            distance_matrix=self.sample_matrix,
            vehicle_count=1,
            depot=0,
            time_windows=time_windows
        )
        
        assert isinstance(result, dict)
        assert "routes" in result
        # Basic validation - should return a valid solution structure
        assert len(result["routes"]) == 1
    
    def test_invalid_depot(self):
        """Test error handling for invalid depot index."""
        with pytest.raises(ValueError, match="Depot index .* out of range"):
            solve_vrp(
                distance_matrix=self.sample_matrix,
                vehicle_count=1,
                depot=10  # Invalid depot index
            )
    
    def test_mismatched_demands(self):
        """Test error handling for mismatched demands length."""
        with pytest.raises(ValueError, match="Demands length .* must match locations"):
            solve_vrp(
                distance_matrix=self.sample_matrix,
                vehicle_count=1,
                depot=0,
                demands=[10, 20]  # Wrong length
            )
    
    def test_mismatched_capacities(self):
        """Test error handling for mismatched capacities length."""
        with pytest.raises(ValueError, match="Vehicle capacities length .* must match vehicle count"):
            solve_vrp(
                distance_matrix=self.sample_matrix,
                vehicle_count=2,
                depot=0,
                vehicle_capacities=[100]  # Wrong length
            )
    
    def test_empty_matrix(self):
        """Test handling of empty distance matrix."""
        empty_matrix = np.array([[]])
        
        # Should handle gracefully or raise appropriate error
        try:
            result = solve_vrp(
                distance_matrix=empty_matrix,
                vehicle_count=1,
                depot=0
            )
            # If it doesn't raise an error, check the result structure
            assert isinstance(result, dict)
        except (ValueError, IndexError):
            # Expected for empty matrix
            pass
    
    def test_single_location(self):
        """Test VRP with only depot (single location)."""
        single_matrix = np.array([[0.0]])
        
        result = solve_vrp(
            distance_matrix=single_matrix,
            vehicle_count=1,
            depot=0
        )
        
        assert isinstance(result, dict)
        assert len(result["routes"]) == 1
        assert result["routes"][0] == [0, 0]  # Start and end at depot
    
    def test_unreachable_nodes(self):
        """Test handling of unreachable nodes (infinite distances)."""
        inf_matrix = np.array([
            [0.0, 100.0, np.inf],
            [100.0, 0.0, 200.0],
            [np.inf, 200.0, 0.0]
        ])
        
        result = solve_vrp(
            distance_matrix=inf_matrix,
            vehicle_count=1,
            depot=0
        )
        
        # Should handle infinite distances gracefully
        assert isinstance(result, dict)
        assert "routes" in result


if __name__ == "__main__":
    pytest.main([__file__])
