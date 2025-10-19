"""
Load testing script for BMSSP routing API.
Tests API performance under concurrent load.
"""
import asyncio
import aiohttp
import time
import json
import numpy as np
from datetime import datetime
from pathlib import Path
import argparse
import sys
import random


class LoadTester:
    """Async load tester for the routing API."""
    
    def __init__(self, base_url="http://localhost:8000", results_dir="results"):
        self.base_url = base_url
        self.results_dir = Path(__file__).parent / results_dir
        self.results_dir.mkdir(exist_ok=True)
        
        # Test data
        self.sample_locations = [
            "node_123", "node_456", "node_789", "node_999", "node_111",
            "node_222", "node_333", "node_444", "node_555", "node_666"
        ]
        
        self.results = {
            "test_start": datetime.now().isoformat(),
            "base_url": base_url,
            "requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "latencies": [],
            "errors": [],
            "test_duration": 0
        }
    
    async def make_vrp_request(self, session, request_id):
        """Make a single VRP request."""
        # Generate random test data
        num_locations = random.randint(3, 8)
        locations = random.sample(self.sample_locations, num_locations)
        vehicle_count = random.randint(1, 3)
        
        payload = {
            "locations": locations,
            "vehicle_count": vehicle_count,
            "depot": 0,
            "demands": [0] + [random.randint(5, 20) for _ in range(num_locations - 1)],
            "capacities": [random.randint(50, 100) for _ in range(vehicle_count)]
        }
        
        start_time = time.time()
        
        try:
            async with session.post(f"{self.base_url}/vrp", json=payload) as response:
                await response.json()
                latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                return {
                    "request_id": request_id,
                    "status_code": response.status,
                    "latency": latency,
                    "success": response.status == 200
                }
                
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "request_id": request_id,
                "status_code": 0,
                "latency": latency,
                "success": False,
                "error": str(e)
            }
    
    async def run_load_test(self, total_requests=100, concurrent_requests=10, duration=None):
        """Run load test with specified parameters."""
        print(f"Starting load test:")
        print(f"  Target URL: {self.base_url}")
        print(f"  Total requests: {total_requests}")
        print(f"  Concurrent requests: {concurrent_requests}")
        if duration:
            print(f"  Duration: {duration}s")
        print()
        
        start_time = time.time()
        completed_requests = 0
        
        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(limit=concurrent_requests * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            
            if duration:
                # Duration-based testing
                end_time = start_time + duration
                request_id = 0
                
                while time.time() < end_time:
                    # Create batch of concurrent requests
                    batch_size = min(concurrent_requests, total_requests - completed_requests)
                    if batch_size <= 0:
                        break
                    
                    tasks = []
                    for _ in range(batch_size):
                        task = self.make_vrp_request(session, request_id)
                        tasks.append(task)
                        request_id += 1
                    
                    # Execute batch
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for result in results:
                        if isinstance(result, dict):
                            self._process_result(result)
                            completed_requests += 1
                    
                    # Progress update
                    elapsed = time.time() - start_time
                    if completed_requests % 10 == 0:
                        rate = completed_requests / elapsed if elapsed > 0 else 0
                        print(f"Completed: {completed_requests}, Rate: {rate:.1f} req/s, Elapsed: {elapsed:.1f}s")
            
            else:
                # Fixed number of requests
                semaphore = asyncio.Semaphore(concurrent_requests)
                
                async def bounded_request(request_id):
                    async with semaphore:
                        return await self.make_vrp_request(session, request_id)
                
                # Create all tasks
                tasks = [bounded_request(i) for i in range(total_requests)]
                
                # Execute with progress reporting
                batch_size = 20
                for i in range(0, len(tasks), batch_size):
                    batch = tasks[i:i + batch_size]
                    results = await asyncio.gather(*batch, return_exceptions=True)
                    
                    # Process results
                    for result in results:
                        if isinstance(result, dict):
                            self._process_result(result)
                            completed_requests += 1
                    
                    # Progress update
                    elapsed = time.time() - start_time
                    rate = completed_requests / elapsed if elapsed > 0 else 0
                    print(f"Progress: {completed_requests}/{total_requests} ({completed_requests/total_requests*100:.1f}%), "
                          f"Rate: {rate:.1f} req/s")
        
        # Calculate final results
        total_time = time.time() - start_time
        self.results["test_duration"] = total_time
        self.results["requests"] = completed_requests
        
        self._calculate_statistics()
        self._print_summary()
        
        return self.results
    
    def _process_result(self, result):
        """Process individual request result."""
        if result["success"]:
            self.results["successful_requests"] += 1
            self.results["latencies"].append(result["latency"])
        else:
            self.results["failed_requests"] += 1
            error_info = {
                "request_id": result["request_id"],
                "status_code": result.get("status_code", 0),
                "error": result.get("error", "Unknown error")
            }
            self.results["errors"].append(error_info)
    
    def _calculate_statistics(self):
        """Calculate performance statistics."""
        latencies = self.results["latencies"]
        
        if latencies:
            self.results["avg_latency_ms"] = np.mean(latencies)
            self.results["median_latency_ms"] = np.median(latencies)
            self.results["p95_latency_ms"] = np.percentile(latencies, 95)
            self.results["p99_latency_ms"] = np.percentile(latencies, 99)
            self.results["min_latency_ms"] = np.min(latencies)
            self.results["max_latency_ms"] = np.max(latencies)
            self.results["std_latency_ms"] = np.std(latencies)
        else:
            self.results["avg_latency_ms"] = 0
            self.results["median_latency_ms"] = 0
            self.results["p95_latency_ms"] = 0
            self.results["p99_latency_ms"] = 0
            self.results["min_latency_ms"] = 0
            self.results["max_latency_ms"] = 0
            self.results["std_latency_ms"] = 0
        
        # Calculate throughput
        if self.results["test_duration"] > 0:
            self.results["requests_per_second"] = self.results["successful_requests"] / self.results["test_duration"]
        else:
            self.results["requests_per_second"] = 0
        
        # Calculate success rate
        if self.results["requests"] > 0:
            self.results["success_rate"] = self.results["successful_requests"] / self.results["requests"]
        else:
            self.results["success_rate"] = 0
    
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        
        print(f"Total Requests:      {self.results['requests']:,}")
        print(f"Successful:          {self.results['successful_requests']:,}")
        print(f"Failed:              {self.results['failed_requests']:,}")
        print(f"Success Rate:        {self.results['success_rate']*100:.2f}%")
        print(f"Test Duration:       {self.results['test_duration']:.2f}s")
        print(f"Throughput:          {self.results['requests_per_second']:.2f} req/s")
        
        print(f"\nLatency Statistics:")
        print(f"  Mean:              {self.results['avg_latency_ms']:.2f}ms")
        print(f"  Median:            {self.results['median_latency_ms']:.2f}ms")
        print(f"  95th percentile:   {self.results['p95_latency_ms']:.2f}ms")
        print(f"  99th percentile:   {self.results['p99_latency_ms']:.2f}ms")
        print(f"  Min:               {self.results['min_latency_ms']:.2f}ms")
        print(f"  Max:               {self.results['max_latency_ms']:.2f}ms")
        print(f"  Std deviation:     {self.results['std_latency_ms']:.2f}ms")
        
        if self.results['errors']:
            print(f"\nError Summary:")
            error_counts = {}
            for error in self.results['errors']:
                error_type = error.get('error', 'Unknown')
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            for error_type, count in error_counts.items():
                print(f"  {error_type}: {count}")
        
        print("="*60)
    
    def save_results(self, filename=None):
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_{timestamp}.json"
        
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {filepath}")
        return filepath
    
    async def health_check(self):
        """Check if the API is healthy before starting tests."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"API health check passed: {data}")
                        return True
                    else:
                        print(f"API health check failed: HTTP {response.status}")
                        return False
        except Exception as e:
            print(f"API health check failed: {e}")
            return False


async def main():
    """Main function to run load tests."""
    parser = argparse.ArgumentParser(description="Run load tests against BMSSP routing API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--requests", type=int, default=100, help="Total number of requests")
    parser.add_argument("--concurrent", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--duration", type=int, help="Test duration in seconds (overrides --requests)")
    parser.add_argument("--output", help="Output filename")
    parser.add_argument("--no-health-check", action="store_true", help="Skip health check")
    
    args = parser.parse_args()
    
    # Create load tester
    tester = LoadTester(args.url)
    
    # Health check
    if not args.no_health_check:
        print("Performing health check...")
        if not await tester.health_check():
            print("Health check failed. Aborting load test.")
            sys.exit(1)
        print()
    
    try:
        # Run load test
        results = await tester.run_load_test(
            total_requests=args.requests,
            concurrent_requests=args.concurrent,
            duration=args.duration
        )
        
        # Save results
        results_file = tester.save_results(args.output)
        
        print(f"\nLoad test completed successfully!")
        print(f"Results saved to: {results_file}")
        
        # Exit with error code if success rate is too low
        if results["success_rate"] < 0.95:
            print(f"WARNING: Success rate ({results['success_rate']*100:.2f}%) is below 95%")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nLoad test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running load test: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
