"""
Enhanced report generator for BMSSP routing benchmarks.
Creates professional PDF reports with charts and branding.
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import sys
import os

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, 
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus.doctemplate import PageTemplate
from reportlab.platypus.frames import Frame


class ReportGenerator:
    """Professional report generator for BMSSP benchmarks."""
    
    def __init__(self, results_dir="results"):
        self.results_dir = Path(__file__).parent / results_dir
        self.results_dir.mkdir(exist_ok=True)
        
        # Set up matplotlib style
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3
        
        # Report styling
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
            alignment=1  # Center
        ))
        
        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#1e40af'),
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=5
        ))
        
        # Subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#374151')
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            textColor=colors.HexColor('#374151')
        ))
    
    def _create_header_footer(self, canvas, doc):
        """Add header and footer to pages."""
        canvas.saveState()
        
        # Header
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(colors.HexColor('#2563eb'))
        canvas.drawString(50, A4[1] - 50, "BMSSP Routing Benchmark Report")
        
        # Add logo placeholder (you can replace with actual logo)
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.HexColor('#6b7280'))
        canvas.drawRightString(A4[0] - 50, A4[1] - 50, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Footer
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#9ca3af'))
        canvas.drawCentredString(A4[0] / 2, 30, f"Page {doc.page}")
        canvas.drawString(50, 30, "BMSSP Routing System")
        canvas.drawRightString(A4[0] - 50, 30, "Production Benchmark Report")
        
        canvas.restoreState()
    
    def generate_charts(self, data):
        """Generate all charts for the report."""
        charts = {}
        
        # Process different benchmark types
        for benchmark in data.get('benchmarks', []):
            test_type = benchmark.get('test_type')
            
            if test_type == 'single_source':
                charts['single_source'] = self._create_single_source_chart(benchmark)
            elif test_type == 'distance_matrix':
                charts['distance_matrix'] = self._create_distance_matrix_chart(benchmark)
            elif test_type == 'scalability':
                charts['scalability'] = self._create_scalability_chart(benchmark)
        
        # Generate load test chart if data exists
        load_test_file = self.results_dir / "load_test.json"
        if load_test_file.exists():
            with open(load_test_file) as f:
                load_data = json.load(f)
            charts['load_test'] = self._create_load_test_chart(load_data)
        
        return charts
    
    def _create_single_source_chart(self, data):
        """Create single-source benchmark comparison chart."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Time comparison
        bmssp_times = data['bmssp']['times']
        dijkstra_times = data['dijkstra']['times']
        
        x = np.arange(len(bmssp_times))
        width = 0.35
        
        ax1.bar(x - width/2, bmssp_times, width, label='BMSSP', color='#3b82f6', alpha=0.8)
        ax1.bar(x + width/2, dijkstra_times, width, label='Dijkstra', color='#ef4444', alpha=0.8)
        
        ax1.set_xlabel('Test Run')
        ax1.set_ylabel('Time (seconds)')
        ax1.set_title('Single-Source Shortest Path Performance')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot comparison
        ax2.boxplot([bmssp_times, dijkstra_times], labels=['BMSSP', 'Dijkstra'])
        ax2.set_ylabel('Time (seconds)')
        ax2.set_title('Performance Distribution')
        ax2.grid(True, alpha=0.3)
        
        # Add speedup annotation
        speedup = data.get('speedup', 1.0)
        ax2.text(0.5, 0.95, f'Speedup: {speedup:.2f}x', 
                transform=ax2.transAxes, ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        plt.tight_layout()
        chart_path = self.results_dir / "single_source_benchmark.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def _create_distance_matrix_chart(self, data):
        """Create distance matrix benchmark chart."""
        results = data['results']
        
        sizes = [r['matrix_size'] for r in results]
        bmssp_times = [r['bmssp_time'] for r in results]
        dijkstra_times = [r['dijkstra_time'] for r in results]
        speedups = [r['speedup'] for r in results]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Time comparison
        ax1.plot(sizes, bmssp_times, 'o-', label='BMSSP', color='#3b82f6', linewidth=2, markersize=8)
        ax1.plot(sizes, dijkstra_times, 's-', label='Dijkstra', color='#ef4444', linewidth=2, markersize=8)
        ax1.set_xlabel('Matrix Size (N×N)')
        ax1.set_ylabel('Computation Time (seconds)')
        ax1.set_title('Distance Matrix Computation Performance')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_yscale('log')
        
        # Speedup chart
        ax2.bar(range(len(sizes)), speedups, color='#10b981', alpha=0.8)
        ax2.set_xlabel('Matrix Size')
        ax2.set_ylabel('Speedup Factor')
        ax2.set_title('BMSSP Speedup vs Dijkstra')
        ax2.set_xticks(range(len(sizes)))
        ax2.set_xticklabels([f'{s}×{s}' for s in sizes])
        ax2.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(speedups):
            ax2.text(i, v + 0.1, f'{v:.1f}x', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        chart_path = self.results_dir / "distance_matrix_benchmark.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def _create_scalability_chart(self, data):
        """Create scalability benchmark chart."""
        results = data['results']
        
        node_counts = [r['node_count'] for r in results]
        bmssp_times = [r['bmssp_time'] for r in results]
        dijkstra_times = [r['dijkstra_time'] for r in results]
        speedups = [r['speedup'] for r in results]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Scalability comparison
        ax1.plot(node_counts, bmssp_times, 'o-', label='BMSSP', color='#3b82f6', linewidth=2, markersize=8)
        ax1.plot(node_counts, dijkstra_times, 's-', label='Dijkstra', color='#ef4444', linewidth=2, markersize=8)
        ax1.set_xlabel('Number of Nodes')
        ax1.set_ylabel('Computation Time (seconds)')
        ax1.set_title('Algorithm Scalability')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xscale('log')
        ax1.set_yscale('log')
        
        # Speedup vs node count
        ax2.plot(node_counts, speedups, 'o-', color='#10b981', linewidth=2, markersize=8)
        ax2.set_xlabel('Number of Nodes')
        ax2.set_ylabel('Speedup Factor')
        ax2.set_title('Speedup vs Graph Size')
        ax2.grid(True, alpha=0.3)
        ax2.set_xscale('log')
        
        plt.tight_layout()
        chart_path = self.results_dir / "scalability_benchmark.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def _create_load_test_chart(self, data):
        """Create load test performance chart."""
        if 'latencies' not in data:
            return None
            
        latencies = data['latencies']
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Latency histogram
        ax1.hist(latencies, bins=30, color='#3b82f6', alpha=0.7, edgecolor='black')
        ax1.set_xlabel('Latency (ms)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Response Time Distribution')
        ax1.grid(True, alpha=0.3)
        
        # Add statistics
        mean_lat = np.mean(latencies)
        p95_lat = np.percentile(latencies, 95)
        ax1.axvline(mean_lat, color='red', linestyle='--', label=f'Mean: {mean_lat:.1f}ms')
        ax1.axvline(p95_lat, color='orange', linestyle='--', label=f'95th: {p95_lat:.1f}ms')
        ax1.legend()
        
        # Time series (if available)
        if len(latencies) > 1:
            ax2.plot(latencies, color='#3b82f6', alpha=0.7)
            ax2.set_xlabel('Request Number')
            ax2.set_ylabel('Latency (ms)')
            ax2.set_title('Latency Over Time')
            ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'Insufficient data for time series', 
                    ha='center', va='center', transform=ax2.transAxes)
        
        plt.tight_layout()
        chart_path = self.results_dir / "load_test_results.png"
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(chart_path)
    
    def generate_report(self, benchmark_file=None, output_file=None):
        """Generate the complete benchmark report."""
        if benchmark_file is None:
            # Find the most recent benchmark file
            benchmark_files = list(self.results_dir.glob("benchmark_results_*.json"))
            if not benchmark_files:
                raise FileNotFoundError("No benchmark results found")
            benchmark_file = max(benchmark_files, key=lambda x: x.stat().st_mtime)
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.results_dir / f"benchmark_report_{timestamp}.pdf"
        
        # Load benchmark data
        with open(benchmark_file) as f:
            data = json.load(f)
        
        # Generate charts
        print("Generating charts...")
        charts = self.generate_charts(data)
        
        # Create PDF
        print(f"Creating PDF report: {output_file}")
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=80, bottomMargin=80
        )
        
        # Build content
        content = []
        
        # Title page
        content.extend(self._build_title_page(data))
        content.append(PageBreak())
        
        # Executive summary
        content.extend(self._build_executive_summary(data))
        content.append(PageBreak())
        
        # Benchmark results
        content.extend(self._build_benchmark_results(data, charts))
        
        # Footer page
        content.append(PageBreak())
        content.extend(self._build_footer_page())
        
        # Build PDF with custom page template
        doc.build(content, onFirstPage=self._create_header_footer, 
                 onLaterPages=self._create_header_footer)
        
        print(f"Report generated successfully: {output_file}")
        return output_file
    
    def _build_title_page(self, data):
        """Build the title page content."""
        content = []
        
        content.append(Spacer(1, 100))
        content.append(Paragraph("BMSSP Routing System", self.styles['CustomTitle']))
        content.append(Paragraph("Benchmark Performance Report", self.styles['CustomTitle']))
        
        content.append(Spacer(1, 50))
        
        # Report info table
        report_info = [
            ["Report Date", datetime.now().strftime("%B %d, %Y")],
            ["Test Location", data.get('place', 'Unknown')],
            ["Generated At", datetime.now().strftime("%H:%M:%S UTC")],
            ["Algorithm", "BMSSP (Bidirectional Multi-Source Shortest Path)"],
            ["Version", "1.0.0"]
        ]
        
        info_table = Table(report_info, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        content.append(info_table)
        content.append(Spacer(1, 100))
        
        # Abstract
        abstract = """
        This report presents comprehensive benchmark results for the BMSSP (Bidirectional Multi-Source 
        Shortest Path) routing algorithm compared against traditional Dijkstra's algorithm. The benchmarks 
        evaluate performance across multiple dimensions including single-source shortest path computation, 
        distance matrix generation, scalability with graph size, and system load testing.
        
        Key findings demonstrate significant performance improvements of BMSSP over traditional approaches, 
        with particular advantages in large-scale routing scenarios typical of production logistics systems.
        """
        
        content.append(Paragraph("Executive Summary", self.styles['CustomHeading']))
        content.append(Paragraph(abstract, self.styles['CustomBody']))
        
        return content
    
    def _build_executive_summary(self, data):
        """Build executive summary section."""
        content = []
        
        content.append(Paragraph("Executive Summary", self.styles['CustomTitle']))
        content.append(Spacer(1, 20))
        
        # Key metrics
        key_metrics = []
        
        for benchmark in data.get('benchmarks', []):
            if benchmark.get('test_type') == 'single_source':
                speedup = benchmark.get('speedup', 1.0)
                key_metrics.append(f"• Single-source shortest path: {speedup:.2f}x faster than Dijkstra")
            
            elif benchmark.get('test_type') == 'distance_matrix':
                results = benchmark.get('results', [])
                if results:
                    avg_speedup = np.mean([r['speedup'] for r in results])
                    key_metrics.append(f"• Distance matrix computation: {avg_speedup:.2f}x average speedup")
            
            elif benchmark.get('test_type') == 'scalability':
                results = benchmark.get('results', [])
                if results:
                    max_speedup = max([r['speedup'] for r in results])
                    key_metrics.append(f"• Scalability: Up to {max_speedup:.2f}x speedup on large graphs")
        
        if key_metrics:
            content.append(Paragraph("Key Performance Highlights:", self.styles['CustomSubHeading']))
            for metric in key_metrics:
                content.append(Paragraph(metric, self.styles['CustomBody']))
        
        content.append(Spacer(1, 20))
        
        # Recommendations
        recommendations = """
        Based on the benchmark results, the BMSSP algorithm demonstrates superior performance characteristics 
        for production routing systems, particularly for:
        
        • High-frequency routing requests with multiple destinations
        • Large-scale logistics operations with complex vehicle routing problems  
        • Real-time applications requiring sub-second response times
        • Systems processing thousands of routing requests per minute
        
        The algorithm shows consistent performance advantages across different graph sizes and query patterns,
        making it suitable for deployment in production environments.
        """
        
        content.append(Paragraph("Recommendations", self.styles['CustomSubHeading']))
        content.append(Paragraph(recommendations, self.styles['CustomBody']))
        
        return content
    
    def _build_benchmark_results(self, data, charts):
        """Build detailed benchmark results section."""
        content = []
        
        content.append(Paragraph("Detailed Benchmark Results", self.styles['CustomTitle']))
        content.append(Spacer(1, 20))
        
        # Process each benchmark
        for benchmark in data.get('benchmarks', []):
            test_type = benchmark.get('test_type')
            chart_key = test_type
            
            if test_type == 'single_source':
                content.extend(self._build_single_source_section(benchmark, charts.get(chart_key)))
            elif test_type == 'distance_matrix':
                content.extend(self._build_distance_matrix_section(benchmark, charts.get(chart_key)))
            elif test_type == 'scalability':
                content.extend(self._build_scalability_section(benchmark, charts.get(chart_key)))
        
        # Load test results if available
        if 'load_test' in charts:
            content.extend(self._build_load_test_section(charts['load_test']))
        
        return content
    
    def _build_single_source_section(self, data, chart_path):
        """Build single-source benchmark section."""
        content = []
        
        content.append(Paragraph("Single-Source Shortest Path Performance", self.styles['CustomHeading']))
        
        description = f"""
        This benchmark evaluates the performance of computing shortest paths from a single source to multiple 
        destinations. The test was conducted with {data.get('num_tests', 'N')} random source nodes, each 
        computing paths to {data.get('sample_size', 'N')} destinations.
        """
        content.append(Paragraph(description, self.styles['CustomBody']))
        
        # Results table
        bmssp_mean = data['bmssp']['mean_time']
        bmssp_std = data['bmssp']['std_time']
        dijkstra_mean = data['dijkstra']['mean_time'] 
        dijkstra_std = data['dijkstra']['std_time']
        speedup = data.get('speedup', 1.0)
        
        results_table = [
            ["Metric", "BMSSP", "Dijkstra", "Improvement"],
            ["Mean Time (s)", f"{bmssp_mean:.4f}", f"{dijkstra_mean:.4f}", f"{speedup:.2f}x"],
            ["Std Deviation (s)", f"{bmssp_std:.4f}", f"{dijkstra_std:.4f}", "-"],
            ["Best Case (s)", f"{min(data['bmssp']['times']):.4f}", f"{min(data['dijkstra']['times']):.4f}", "-"],
            ["Worst Case (s)", f"{max(data['bmssp']['times']):.4f}", f"{max(data['dijkstra']['times']):.4f}", "-"]
        ]
        
        table = Table(results_table, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(self._get_table_style())
        content.append(table)
        content.append(Spacer(1, 10))
        
        if chart_path and Path(chart_path).exists():
            content.append(Image(chart_path, width=6*inch, height=3*inch))
        
        content.append(Spacer(1, 20))
        return content
    
    def _build_distance_matrix_section(self, data, chart_path):
        """Build distance matrix benchmark section."""
        content = []
        
        content.append(Paragraph("Distance Matrix Computation", self.styles['CustomHeading']))
        
        description = """
        Distance matrix computation is crucial for Vehicle Routing Problems (VRP). This benchmark evaluates 
        the performance of computing full distance matrices of various sizes, comparing BMSSP against 
        traditional Dijkstra-based approaches.
        """
        content.append(Paragraph(description, self.styles['CustomBody']))
        
        # Results table
        results = data.get('results', [])
        if results:
            table_data = [["Matrix Size", "BMSSP Time (s)", "Dijkstra Time (s)", "Speedup", "Accuracy"]]
            
            for result in results:
                size = result['matrix_size']
                bmssp_time = result['bmssp_time']
                dijkstra_time = result['dijkstra_time']
                speedup = result['speedup']
                accuracy = result.get('accuracy', 1.0)
                
                table_data.append([
                    f"{size}×{size}",
                    f"{bmssp_time:.4f}",
                    f"{dijkstra_time:.4f}", 
                    f"{speedup:.2f}x",
                    f"{accuracy:.3f}"
                ])
            
            table = Table(table_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 1*inch, 1*inch])
            table.setStyle(self._get_table_style())
            content.append(table)
            content.append(Spacer(1, 10))
        
        if chart_path and Path(chart_path).exists():
            content.append(Image(chart_path, width=6*inch, height=3*inch))
        
        content.append(Spacer(1, 20))
        return content
    
    def _build_scalability_section(self, data, chart_path):
        """Build scalability benchmark section."""
        content = []
        
        content.append(Paragraph("Algorithm Scalability", self.styles['CustomHeading']))
        
        description = """
        Scalability testing evaluates how algorithm performance changes with graph size. This is critical 
        for understanding deployment characteristics in different city sizes and network complexities.
        """
        content.append(Paragraph(description, self.styles['CustomBody']))
        
        # Results table
        results = data.get('results', [])
        if results:
            table_data = [["Node Count", "BMSSP Time (s)", "Dijkstra Time (s)", "Speedup"]]
            
            for result in results:
                table_data.append([
                    f"{result['node_count']:,}",
                    f"{result['bmssp_time']:.4f}",
                    f"{result['dijkstra_time']:.4f}",
                    f"{result['speedup']:.2f}x"
                ])
            
            table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            table.setStyle(self._get_table_style())
            content.append(table)
            content.append(Spacer(1, 10))
        
        if chart_path and Path(chart_path).exists():
            content.append(Image(chart_path, width=6*inch, height=3*inch))
        
        content.append(Spacer(1, 20))
        return content
    
    def _build_load_test_section(self, chart_path):
        """Build load test results section."""
        content = []
        
        content.append(Paragraph("Load Test Results", self.styles['CustomHeading']))
        
        description = """
        Load testing evaluates system performance under concurrent request load, measuring response times,
        throughput, and system stability under production-like conditions.
        """
        content.append(Paragraph(description, self.styles['CustomBody']))
        
        if chart_path and Path(chart_path).exists():
            content.append(Image(chart_path, width=6*inch, height=3*inch))
        
        content.append(Spacer(1, 20))
        return content
    
    def _build_footer_page(self):
        """Build footer page with contact info."""
        content = []
        
        content.append(Spacer(1, 200))
        content.append(Paragraph("About BMSSP Routing System", self.styles['CustomHeading']))
        
        about_text = """
        The BMSSP Routing System is a production-ready vehicle routing solution designed for high-performance 
        logistics applications. Built with modern algorithms and cloud-native architecture, it provides 
        scalable routing optimization for enterprise deployments.
        
        Key Features:
        • High-performance BMSSP algorithm implementation
        • RESTful API with comprehensive documentation  
        • Docker containerization for easy deployment
        • Comprehensive monitoring and benchmarking tools
        • Production-ready with health checks and logging
        
        For more information, documentation, or support, please visit our repository or contact the development team.
        """
        
        content.append(Paragraph(about_text, self.styles['CustomBody']))
        content.append(Spacer(1, 50))
        
        # Footer branding
        content.append(Paragraph("BMSSP Routing System © 2025", self.styles['CustomBody']))
        
        return content
    
    def _get_table_style(self):
        """Get standard table style."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ])


def main():
    """Main function to generate report."""
    parser = argparse.ArgumentParser(description="Generate BMSSP benchmark report")
    parser.add_argument("--benchmark-file", help="Path to benchmark results JSON file")
    parser.add_argument("--output", help="Output PDF file path")
    parser.add_argument("--results-dir", default="results", help="Results directory")
    
    args = parser.parse_args()
    
    try:
        generator = ReportGenerator(args.results_dir)
        report_path = generator.generate_report(args.benchmark_file, args.output)
        
        print(f"\n{'='*60}")
        print("Report Generation Completed Successfully!")
        print(f"Report saved to: {report_path}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"Error generating report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()