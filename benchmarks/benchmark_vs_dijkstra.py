"""
Benchmark BMSSP algorithm against Dijkstra's algorithm.
"""
import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime
from pathlib import Path

# Add backend path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from graph_loader import load_graph
    from distance_matrix import compute_matrix
    import networkx as nx
    import osmnx as ox
except ImportError as e:
    print(f"Import error: {e}")
    print("Please make sure all dependencies are installed")
    sys.exit(1)


class BenchmarkRunner:
    """Class to run benchmarks comparing BMSSP vs Dijkstra."""
    
    def __init__(self, place="Kuala Lumpur, Malaysia"):
        self.place = place
        self.results = {
            "place": place,
            "timestamp": datetime.now().isoformat(),
            "benchmarks": []
        }
        
        print(f"Loading graph for {place}...")
        self.engine, self.id_map, self.rev_map = load_graph(place)
        
        # Load NetworkX graph for Dijkstra comparison
        print("Loading NetworkX graph...")
        G = ox.graph_from_place(place, network_type="drive")
        G = ox.add_edge_lengths(G)
        self.nx_graph = nx.DiGraph(G)
        
        print(f"Graph loaded: {len(self.id_map)} nodes, {len(self.nx_graph.edges())} edges")
    
    def benchmark_single_source(self, num_tests=10, sample_size=100):
        """Benchmark single-source shortest path computation."""
        print(f"\nRunning single-source benchmark ({num_tests} tests, {sample_size} destinations each)...")
        
        # Select random source nodes
        nodes = list(self.id_map.keys())
        test_sources = np.random.choice(nodes, size=num_tests, replace=False)
        
        bmssp_times = []
        dijkstra_times = []
        
        for i, source in enumerate(test_sources):
            print(f"Test {i+1}/{num_tests}: Source {source}")
            
            # Select random destinations
            destinations = np.random.choice(nodes, size=sample_size, replace=False)
            
            # BMSSP benchmark
            start_time = time.time()
            source_id = self.id_map[source]
            self.engine.run(source_id)
            # Access distances for all destinations
            for dest in destinations:
                dest_id = self.id_map[dest]
                _ = self.engine.dist[dest_id]
            bmssp_time = time.time() - start_time
            bmssp_times.append(bmssp_time)
            
            # Dijkstra benchmark
            start_time = time.time()
            try:
                lengths = nx.single_source_dijkstra_path_length(
                    self.nx_graph, source, weight='length'
                )
                # Access distances for destinations
                for dest in destinations:
                    if dest in lengths:
                        _ = lengths[dest]
            except nx.NetworkXNoPath:
                pass
            dijkstra_time = time.time() - start_time
            dijkstra_times.append(dijkstra_time)
        
        # Calculate statistics
        bmssp_mean = np.mean(bmssp_times)
        bmssp_std = np.std(bmssp_times)
        dijkstra_mean = np.mean(dijkstra_times)
        dijkstra_std = np.std(dijkstra_times)
        speedup = dijkstra_mean / bmssp_mean
        
        result = {
            "test_type": "single_source",
            "num_tests": num_tests,
            "sample_size": sample_size,
            "bmssp": {
                "mean_time": bmssp_mean,
                "std_time": bmssp_std,
                "times": bmssp_times
            },
            "dijkstra": {
                "mean_time": dijkstra_mean,
                "std_time": dijkstra_std,
                "times": dijkstra_times
            },
            "speedup": speedup
        }
        
        self.results["benchmarks"].append(result)
        
        print(f"BMSSP: {bmssp_mean:.4f}±{bmssp_std:.4f}s")
        print(f"Dijkstra: {dijkstra_mean:.4f}±{dijkstra_std:.4f}s")
        print(f"Speedup: {speedup:.2f}x")
        
        return result
    
    def benchmark_distance_matrix(self, matrix_sizes=[5, 10, 20, 50]):
        """Benchmark distance matrix computation."""
        print(f"\nRunning distance matrix benchmark (sizes: {matrix_sizes})...")
        
        nodes = list(self.id_map.keys())
        results = []
        
        for size in matrix_sizes:
            print(f"Matrix size: {size}x{size}")
            
            # Select random nodes
            selected_nodes = np.random.choice(nodes, size=size, replace=False).tolist()
            
            # BMSSP benchmark
            start_time = time.time()
            matrix_bmssp = compute_matrix(selected_nodes, self.place)
            bmssp_time = time.time() - start_time
            
            # NetworkX benchmark (using Dijkstra)
            start_time = time.time()
            matrix_nx = np.full((size, size), np.inf)
            for i, source in enumerate(selected_nodes):
                try:
                    lengths = nx.single_source_dijkstra_path_length(
                        self.nx_graph, source, weight='length'
                    )
                    for j, target in enumerate(selected_nodes):
                        if target in lengths:
                            matrix_nx[i][j] = lengths[target]
                        elif source == target:
                            matrix_nx[i][j] = 0.0
                except nx.NetworkXNoPath:
                    pass
            dijkstra_time = time.time() - start_time
            
            speedup = dijkstra_time / bmssp_time
            
            result = {
                "matrix_size": size,
                "bmssp_time": bmssp_time,
                "dijkstra_time": dijkstra_time,
                "speedup": speedup,
                "accuracy": self._compare_matrices(matrix_bmssp, matrix_nx)
            }
            
            results.append(result)
            
            print(f"  BMSSP: {bmssp_time:.4f}s")
            print(f"  Dijkstra: {dijkstra_time:.4f}s")
            print(f"  Speedup: {speedup:.2f}x")
            print(f"  Accuracy: {result['accuracy']:.4f}")
        
        benchmark_result = {
            "test_type": "distance_matrix",
            "matrix_sizes": matrix_sizes,
            "results": results
        }
        
        self.results["benchmarks"].append(benchmark_result)
        return benchmark_result
    
    def _compare_matrices(self, matrix1, matrix2, tolerance=1e-6):
        """Compare two distance matrices and return accuracy score."""
        # Handle infinities
        inf_mask1 = np.isinf(matrix1)
        inf_mask2 = np.isinf(matrix2)
        
        # Count matching infinities
        inf_matches = np.sum(inf_mask1 & inf_mask2)
        
        # Compare finite values
        finite_mask = ~inf_mask1 & ~inf_mask2
        if np.sum(finite_mask) == 0:
            return 1.0 if inf_matches == matrix1.size else 0.0
        
        finite_diff = np.abs(matrix1[finite_mask] - matrix2[finite_mask])
        relative_error = finite_diff / (np.abs(matrix1[finite_mask]) + tolerance)
        
        # Calculate accuracy (percentage of values within tolerance)
        accurate_count = np.sum(relative_error < tolerance) + inf_matches
        total_count = matrix1.size
        
        return accurate_count / total_count
    
    def benchmark_scalability(self, node_counts=[100, 500, 1000]):
        """Benchmark scalability with different node counts."""
        print(f"\nRunning scalability benchmark (node counts: {node_counts})...")
        
        nodes = list(self.id_map.keys())
        max_nodes = min(len(nodes), max(node_counts))
        
        results = []
        
        for count in node_counts:
            if count > len(nodes):
                print(f"Skipping {count} nodes (only {len(nodes)} available)")
                continue
                
            print(f"Testing with {count} nodes...")
            
            # Select random subset of nodes
            selected_nodes = np.random.choice(nodes, size=count, replace=False).tolist()
            
            # BMSSP benchmark - single source to all others
            source = selected_nodes[0]
            start_time = time.time()
            source_id = self.id_map[source]
            self.engine.run(source_id)
            # Access all distances
            for node in selected_nodes:
                node_id = self.id_map[node]
                _ = self.engine.dist[node_id]
            bmssp_time = time.time() - start_time
            
            # NetworkX benchmark
            start_time = time.time()
            try:
                lengths = nx.single_source_dijkstra_path_length(
                    self.nx_graph, source, weight='length'
                )
                for node in selected_nodes:
                    if node in lengths:
                        _ = lengths[node]
            except nx.NetworkXNoPath:
                pass
            dijkstra_time = time.time() - start_time
            
            speedup = dijkstra_time / bmssp_time if bmssp_time > 0 else float('inf')
            
            result = {
                "node_count": count,
                "bmssp_time": bmssp_time,
                "dijkstra_time": dijkstra_time,
                "speedup": speedup
            }
            
            results.append(result)
            
            print(f"  BMSSP: {bmssp_time:.4f}s")
            print(f"  Dijkstra: {dijkstra_time:.4f}s")
            print(f"  Speedup: {speedup:.2f}x")
        
        benchmark_result = {
            "test_type": "scalability",
            "node_counts": node_counts,
            "results": results
        }
        
        self.results["benchmarks"].append(benchmark_result)
        return benchmark_result
    
    def save_results(self, filename=None):
        """Save benchmark results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"
        
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        filepath = results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {filepath}")
        return filepath
    
    def run_all_benchmarks(self):
        """Run all benchmark tests."""
        print("=" * 60)
        print("BMSSP vs Dijkstra Benchmark Suite")
        print("=" * 60)
        
        # Single source benchmark
        self.benchmark_single_source(num_tests=5, sample_size=50)
        
        # Distance matrix benchmark
        self.benchmark_distance_matrix(matrix_sizes=[5, 10, 20])
        
        # Scalability benchmark
        max_nodes = min(len(self.id_map), 1000)
        node_counts = [100, 500, max_nodes] if max_nodes >= 500 else [100, max_nodes]
        self.benchmark_scalability(node_counts=node_counts)
        
        # Save results
        return self.save_results()


def main():
    """Main function to run benchmarks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark BMSSP vs Dijkstra")
    parser.add_argument("--place", default="Kuala Lumpur, Malaysia", 
                        help="Place to load graph for")
    parser.add_argument("--output", help="Output filename")
    
    args = parser.parse_args()
    
    try:
        runner = BenchmarkRunner(args.place)
        results_file = runner.run_all_benchmarks()
        
        print("\n" + "=" * 60)
        print("Benchmark completed successfully!")
        print(f"Results saved to: {results_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error running benchmarks: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
