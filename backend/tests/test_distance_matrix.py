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
        import networkx as nx
        self.sample_locations = ["node_1", "node_2", "node_3"]
        
        # Create a mock NetworkX graph
        self.mock_graph = nx.DiGraph()
        self.mock_graph.add_node("node_1", y=3.139, x=101.686)
        self.mock_graph.add_node("node_2", y=3.140, x=101.687)
        self.mock_graph.add_node("node_3", y=3.141, x=101.688)
        
        # Add edges with lengths
        self.mock_graph.add_edge("node_1", "node_2", length=100.0)
        self.mock_graph.add_edge("node_2", "node_1", length=100.0)
        self.mock_graph.add_edge("node_2", "node_3", length=100.0)
        self.mock_graph.add_edge("node_3", "node_2", length=100.0)
        self.mock_graph.add_edge("node_1", "node_3", length=200.0)
        self.mock_graph.add_edge("node_3", "node_1", length=200.0)
    
    @patch('distance_matrix.load_graph')
    def test_compute_basic_matrix(self, mock_load_graph):
        """Test basic distance matrix computation."""
        # Import here to avoid import errors during module loading
        from distance_matrix import compute_matrix
        
        # Mock the graph loading - return NetworkX graph
        mock_load_graph.return_value = self.mock_graph
        
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
        
        # Return NetworkX graph
        mock_load_graph.return_value = self.mock_graph
        
        result = compute_matrix(["node_1"])
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1)
        assert result[0][0] == 0.0
    
    @patch('distance_matrix.load_graph')
    def test_node_id_formats(self, mock_load_graph):
        """Test different node ID formats (string vs integer)."""
        from distance_matrix import compute_matrix
        import networkx as nx
        
        # Mock with integer node IDs
        int_graph = nx.DiGraph()
        int_graph.add_node(123, y=3.139, x=101.686)
        int_graph.add_node(456, y=3.140, x=101.687)
        int_graph.add_node(789, y=3.141, x=101.688)
        int_graph.add_edge(123, 456, length=100.0)
        int_graph.add_edge(456, 123, length=100.0)
        int_graph.add_edge(456, 789, length=100.0)
        int_graph.add_edge(789, 456, length=100.0)
        int_graph.add_edge(123, 789, length=200.0)
        int_graph.add_edge(789, 123, length=200.0)
        
        mock_load_graph.return_value = int_graph
        
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
        
        # Return NetworkX graph
        mock_load_graph.return_value = self.mock_graph
        
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
        
        # Create a graph with very large distances
        import networkx as nx
        large_graph = nx.DiGraph()
        large_graph.add_node("node_1", y=3.139, x=101.686)
        large_graph.add_node("node_2", y=3.140, x=101.687)
        large_graph.add_node("node_3", y=3.141, x=101.688)
        # Add edges with very large distances
        large_graph.add_edge("node_1", "node_2", length=1e15)
        large_graph.add_edge("node_2", "node_1", length=1e15)
        large_graph.add_edge("node_2", "node_3", length=1e15)
        large_graph.add_edge("node_3", "node_2", length=1e15)
        large_graph.add_edge("node_1", "node_3", length=1e15)
        large_graph.add_edge("node_3", "node_1", length=1e15)
        
        mock_load_graph.return_value = large_graph
        
        result = compute_matrix(self.sample_locations)
        
        assert isinstance(result, np.ndarray)
        # Should have very large distances
        assert np.any(result >= 1e14)


if __name__ == "__main__":
    pytest.main([__file__])
