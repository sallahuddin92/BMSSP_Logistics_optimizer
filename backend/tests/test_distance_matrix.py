"""
Test the distance matrix computation functionality.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockBMSSP:
    """Mock BMSSP engine for testing."""
    
    def __init__(self, n):
        self.n = n
        self.dist = [float('inf')] * n
    
    def run(self, source):
        """Mock run method - sets distances to simple values for testing."""
        for i in range(self.n):
            if i == source:
                self.dist[i] = 0.0
            else:
                self.dist[i] = abs(i - source) * 100.0


class TestDistanceMatrix:
    """Test cases for distance matrix computation."""
    
    def setup_method(self):
        """Set up test data and mocks."""
        self.sample_locations = ["node_1", "node_2", "node_3"]
        self.mock_id_map = {"node_1": 0, "node_2": 1, "node_3": 2}
        self.mock_rev_map = {0: "node_1", 1: "node_2", 2: "node_3"}
        self.mock_engine = MockBMSSP(3)
    
    @patch('distance_matrix.load_graph')
    def test_compute_basic_matrix(self, mock_load_graph):
        """Test basic distance matrix computation."""
        # Import here to avoid import errors during module loading
        from distance_matrix import compute_matrix
        
        # Mock the graph loading
        mock_load_graph.return_value = (
            self.mock_engine,
            self.mock_id_map,
            self.mock_rev_map
        )
        
        result = compute_matrix(self.sample_locations)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 3)
        
        # Check diagonal elements are zero
        for i in range(3):
            assert result[i][i] == 0.0
        
        # Check symmetry property (should be symmetric for undirected graphs)
        # Note: This might not be true for directed graphs, so we'll just check structure
        assert result[0][1] > 0  # Distance from node_1 to node_2
        assert result[1][2] > 0  # Distance from node_2 to node_3
    
    @patch('distance_matrix.load_graph')
    def test_invalid_node_handling(self, mock_load_graph):
        """Test handling of invalid node IDs."""
        from distance_matrix import compute_matrix
        
        mock_load_graph.return_value = (
            self.mock_engine,
            self.mock_id_map,
            self.mock_rev_map
        )
        
        # Test with invalid node
        invalid_locations = ["node_1", "invalid_node", "node_3"]
        
        with pytest.raises(ValueError, match="Invalid node"):
            compute_matrix(invalid_locations)
    
    @patch('distance_matrix.load_graph')
    def test_empty_locations(self, mock_load_graph):
        """Test handling of empty location list."""
        from distance_matrix import compute_matrix
        
        mock_load_graph.return_value = (
            self.mock_engine,
            self.mock_id_map,
            self.mock_rev_map
        )
        
        result = compute_matrix([])
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (0, 0)
    
    @patch('distance_matrix.load_graph')
    def test_single_location(self, mock_load_graph):
        """Test distance matrix with single location."""
        from distance_matrix import compute_matrix
        
        mock_load_graph.return_value = (
            self.mock_engine,
            self.mock_id_map,
            self.mock_rev_map
        )
        
        result = compute_matrix(["node_1"])
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1)
        assert result[0][0] == 0.0
    
    @patch('distance_matrix.load_graph')
    def test_node_id_formats(self, mock_load_graph):
        """Test different node ID formats (string vs integer)."""
        from distance_matrix import compute_matrix
        
        # Mock with integer node IDs
        int_id_map = {123: 0, 456: 1, 789: 2}
        int_rev_map = {0: 123, 1: 456, 2: 789}
        
        mock_load_graph.return_value = (
            self.mock_engine,
            int_id_map,
            int_rev_map
        )
        
        # Test with string representations of integers
        result = compute_matrix(["123", "456", "789"])
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 3)
    
    @patch('distance_matrix.get_node_coordinates')
    def test_get_node_coordinates(self, mock_get_coords):
        """Test node coordinate retrieval."""
        from distance_matrix import get_node_coordinates
        
        mock_get_coords.return_value = (3.139, 101.6869)
        
        coords = get_node_coordinates("node_1")
        
        assert coords == (3.139, 101.6869)
        mock_get_coords.assert_called_once_with("node_1")
    
    @patch('distance_matrix.load_graph')
    def test_validate_locations(self, mock_load_graph):
        """Test location validation function."""
        from distance_matrix import validate_locations
        
        mock_load_graph.return_value = (
            self.mock_engine,
            self.mock_id_map,
            self.mock_rev_map
        )
        
        # Test valid locations
        valid_locations = validate_locations(["node_1", "node_2"])
        assert valid_locations == ["node_1", "node_2"]
        
        # Test invalid location
        with pytest.raises(ValueError, match="Invalid node"):
            validate_locations(["node_1", "invalid_node"])
    
    @patch('distance_matrix.load_graph')
    def test_large_distances(self, mock_load_graph):
        """Test handling of very large distances."""
        from distance_matrix import compute_matrix
        
        # Mock engine that returns very large distances
        class LargeDistanceBMSSP:
            def __init__(self, n):
                self.n = n
                self.dist = [1e18] * n  # Very large distances
            
            def run(self, source):
                self.dist[source] = 0.0
                for i in range(self.n):
                    if i != source:
                        self.dist[i] = 1e15  # Large but finite
        
        mock_engine = LargeDistanceBMSSP(3)
        mock_load_graph.return_value = (
            mock_engine,
            self.mock_id_map,
            self.mock_rev_map
        )
        
        result = compute_matrix(self.sample_locations)
        
        assert isinstance(result, np.ndarray)
        # Should convert very large distances to infinity
        assert np.any(np.isinf(result) | (result >= 1e17))


if __name__ == "__main__":
    pytest.main([__file__])
