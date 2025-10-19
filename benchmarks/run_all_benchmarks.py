#!/usr/bin/env python3
"""
Main script to run all benchmarks and generate report.
"""
import sys
import asyncio
import time
import subprocess
from pathlib import Path
import argparse


async def run_benchmarks():
    """Run complete benchmark suite."""
    print("="*80)
    print("BMSSP ROUTING BENCHMARK SUITE")
    print("="*80)
    
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Step 1: Run algorithm benchmarks
    print("\n1. Running BMSSP vs Dijkstra benchmarks...")
    try:
        result = subprocess.run([
            sys.executable, "benchmark_vs_dijkstra.py",
            "--place", "Kuala Lumpur, Malaysia"
        ], check=True, capture_output=True, text=True)
        print("✓ Algorithm benchmarks completed")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Algorithm benchmarks failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False
    
    # Step 2: Wait for backend to be ready
    print("\n2. Waiting for backend API to be ready...")
    backend_ready = False
    max_retries = 30
    
    for i in range(max_retries):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://backend:8000/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        backend_ready = True
                        print("✓ Backend API is ready")
                        break
        except Exception:
            pass
        
        print(f"Waiting for backend... ({i+1}/{max_retries})")
        await asyncio.sleep(2)
    
    if not backend_ready:
        print("✗ Backend API not ready, skipping load tests")
        # Continue with report generation even if load tests fail
    else:
        # Step 3: Run load tests
        print("\n3. Running load tests...")
        try:
            result = subprocess.run([
                sys.executable, "load_test.py",
                "--url", "http://backend:8000",
                "--requests", "50",
                "--concurrent", "5"
            ], check=True, capture_output=True, text=True)
            print("✓ Load tests completed")
            if result.stdout:
                print(f"Output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Load tests failed: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            # Continue with report generation
    
    # Step 4: Generate report
    print("\n4. Generating comprehensive report...")
    try:
        result = subprocess.run([
            sys.executable, "report_generator.py"
        ], check=True, capture_output=True, text=True)
        print("✓ Report generated successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Report generation failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False
    
    print("\n" + "="*80)
    print("BENCHMARK SUITE COMPLETED SUCCESSFULLY!")
    print("="*80)
    print(f"\nResults available in: {results_dir}")
    
    # List generated files
    files = list(results_dir.glob("*"))
    if files:
        print("\nGenerated files:")
        for file in sorted(files):
            print(f"  - {file.name}")
    
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run complete BMSSP benchmark suite")
    parser.add_argument("--place", default="Kuala Lumpur, Malaysia", 
                        help="Place to run benchmarks for")
    parser.add_argument("--load-test-requests", type=int, default=50,
                        help="Number of requests for load testing")
    parser.add_argument("--load-test-concurrent", type=int, default=5,
                        help="Concurrent requests for load testing")
    
    args = parser.parse_args()
    
    try:
        success = asyncio.run(run_benchmarks())
        if success:
            print("\n🎉 All benchmarks completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some benchmarks failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
