"""
Test the API endpoints functionality.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Mock the dependencies before importing the API
def mock_load_graph():
    """Mock load_graph function."""
    mock_engine = Mock()
    mock_engine.run = Mock()
    mock_engine.dist = [0.0, 100.0, 200.0]
    
    mock_id_map = {"node_1": 0, "node_2": 1, "node_3": 2}
    mock_rev_map = {0: "node_1", 1: "node_2", 2: "node_3"}
    
    return mock_engine, mock_id_map, mock_rev_map


def mock_compute_matrix(locations):
    """Mock compute_matrix function."""
    import numpy as np
    n = len(locations)
    matrix = np.random.rand(n, n) * 100
    # Make diagonal zero
    for i in range(n):
        matrix[i][i] = 0.0
    return matrix


def mock_solve_vrp(*args, **kwargs):
    """Mock solve_vrp function."""
    return {
        "routes": [[0, 1, 0], [0, 2, 0]],
        "total_distance": 300.0,
        "vehicle_distances": [150.0, 150.0],
        "status": "OPTIMAL",
        "objective_value": 300.0,
        "vehicle_count": 2,
        "total_locations": 2
    }


def mock_get_node_coordinates(node_id):
    """Mock get_node_coordinates function."""
    coords_map = {
        "node_1": (3.139, 101.686),
        "node_2": (3.140, 101.687),
        "node_3": (3.141, 101.688)
    }
    return coords_map.get(node_id)


# Apply mocks
with patch('distance_matrix.load_graph', mock_load_graph), \
     patch('distance_matrix.compute_matrix', mock_compute_matrix), \
     patch('vrp_solver.solve_vrp', mock_solve_vrp), \
     patch('distance_matrix.get_node_coordinates', mock_get_node_coordinates), \
     patch('graph_loader.get_available_cities', return_value=["Kuala Lumpur, Malaysia"]), \
     patch('graph_loader.find_nearest_nodes', return_value=[{"node_id": "node_1", "lat": 3.139, "lon": 101.686, "distance": 50}]), \
     patch('graph_loader.get_graph_stats', return_value={"node_count": 1000, "edge_count": 2000}):
     
    from api import app


class TestAPI:
    """Test cases for the FastAPI application."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_cities_endpoint(self):
        """Test the cities endpoint."""
        response = self.client.get("/cities")
        
        assert response.status_code == 200
        data = response.json()
        assert "cities" in data
        assert isinstance(data["cities"], list)
    
    def test_search_nodes_endpoint(self):
        """Test the search nodes endpoint."""
        request_data = {
            "lat": 3.139,
            "lon": 101.686,
            "radius": 1000
        }
        
        response = self.client.post("/search-nodes", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert isinstance(data["nodes"], list)
    
    def test_search_nodes_invalid_coordinates(self):
        """Test search nodes with invalid coordinates."""
        request_data = {
            "lat": 200,  # Invalid latitude
            "lon": 101.686,
            "radius": 1000
        }
        
        response = self.client.post("/search-nodes", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_node_coordinates_endpoint(self):
        """Test the node coordinates endpoint."""
        response = self.client.get("/node-coordinates/node_1")
        
        assert response.status_code == 200
        data = response.json()
        assert "node_id" in data
        assert "lat" in data
        assert "lon" in data
        assert data["node_id"] == "node_1"
    
    def test_node_coordinates_not_found(self):
        """Test node coordinates for non-existent node."""
        with patch('distance_matrix.get_node_coordinates', return_value=None):
            response = self.client.get("/node-coordinates/nonexistent")
            
            assert response.status_code == 404
    
    def test_distance_matrix_endpoint(self):
        """Test the distance matrix endpoint."""
        locations = ["node_1", "node_2", "node_3"]
        
        response = self.client.post("/distance-matrix", json=locations)
        
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert "matrix" in data
        assert "computation_time" in data
        assert data["locations"] == locations
        assert len(data["matrix"]) == len(locations)
    
    def test_vrp_endpoint_basic(self):
        """Test the basic VRP endpoint."""
        request_data = {
            "locations": ["node_1", "node_2", "node_3"],
            "vehicle_count": 2,
            "depot": 0
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = [
            "locations", "routes", "route_locations", "location_coordinates",
            "total_distance", "vehicle_distances", "computation_times", "metadata"
        ]
        for field in required_fields:
            assert field in data
        
        assert data["locations"] == request_data["locations"]
        assert len(data["routes"]) == request_data["vehicle_count"]
    
    def test_vrp_endpoint_with_constraints(self):
        """Test VRP endpoint with capacity and time window constraints."""
        request_data = {
            "locations": ["node_1", "node_2", "node_3"],
            "vehicle_count": 2,
            "depot": 0,
            "demands": [0, 10, 15],
            "capacities": [20, 20],
            "time_windows": [[0, 100], [10, 50], [20, 80]]
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check metadata reflects constraints
        metadata = data["metadata"]
        assert metadata["has_demands"] is True
        assert metadata["has_capacities"] is True
        assert metadata["has_time_windows"] is True
    
    def test_vrp_invalid_depot(self):
        """Test VRP with invalid depot index."""
        request_data = {
            "locations": ["node_1", "node_2"],
            "vehicle_count": 1,
            "depot": 5  # Invalid depot index
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 400
        assert "depot index out of range" in response.json()["detail"].lower()
    
    def test_vrp_mismatched_demands(self):
        """Test VRP with mismatched demands length."""
        request_data = {
            "locations": ["node_1", "node_2", "node_3"],
            "vehicle_count": 1,
            "depot": 0,
            "demands": [0, 10]  # Wrong length
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 400
        assert "demands length must match locations length" in response.json()["detail"].lower()
    
    def test_vrp_mismatched_capacities(self):
        """Test VRP with mismatched capacities length."""
        request_data = {
            "locations": ["node_1", "node_2"],
            "vehicle_count": 2,
            "depot": 0,
            "capacities": [100]  # Wrong length
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 400
        assert "capacities length must match vehicle count" in response.json()["detail"].lower()
    
    def test_vrp_mismatched_time_windows(self):
        """Test VRP with mismatched time windows length."""
        request_data = {
            "locations": ["node_1", "node_2", "node_3"],
            "vehicle_count": 1,
            "depot": 0,
            "time_windows": [[0, 100]]  # Wrong length
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 400
        assert "time windows length must match locations length" in response.json()["detail"].lower()
    
    def test_stats_endpoint(self):
        """Test the stats endpoint."""
        response = self.client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "graph_stats" in data
        assert "api_version" in data
        assert "algorithm" in data
    
    def test_vrp_validation_vehicle_count(self):
        """Test VRP validation for vehicle count."""
        request_data = {
            "locations": ["node_1", "node_2"],
            "vehicle_count": 0,  # Invalid vehicle count
            "depot": 0
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_vrp_validation_depot_negative(self):
        """Test VRP validation for negative depot index."""
        request_data = {
            "locations": ["node_1", "node_2"],
            "vehicle_count": 1,
            "depot": -1  # Invalid depot index
        }
        
        response = self.client.post("/vrp", json=request_data)
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])
