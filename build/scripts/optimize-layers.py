#!/usr/bin/env python3
# Path: build/scripts/optimize-layers.py
# Layer optimization script for distroless images
# Analyzes and optimizes Docker image layers for better caching and smaller sizes

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DockerImageAnalyzer:
    """Analyzes Docker images and provides optimization recommendations."""
    
    def __init__(self, image_name: str, registry: str = "ghcr.io", project_name: str = "HamiGames/Lucid"):
        self.image_name = image_name
        self.registry = registry
        self.project_name = project_name
        self.full_image_name = f"{registry}/{project_name}/{image_name}"
        self.analysis_results = {}
        
    def analyze_image(self) -> Dict:
        """Analyze the Docker image and return detailed information."""
        logger.info(f"Analyzing image: {self.full_image_name}")
        
        try:
            # Get image history
            history = self._get_image_history()
            
            # Get image layers
            layers = self._get_image_layers()
            
            # Get image size
            size = self._get_image_size()
            
            # Analyze layer efficiency
            layer_analysis = self._analyze_layers(layers)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(layer_analysis, history)
            
            self.analysis_results = {
                "image_name": self.full_image_name,
                "size": size,
                "layers": layers,
                "history": history,
                "layer_analysis": layer_analysis,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat()
            }
            
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"Failed to analyze image: {e}")
            raise
    
    def _get_image_history(self) -> List[Dict]:
        """Get the history of Docker image layers."""
        try:
            result = subprocess.run(
                ["docker", "history", "--format", "json", self.full_image_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            history = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        history.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            return history
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get image history: {e}")
            return []
    
    def _get_image_layers(self) -> List[Dict]:
        """Get detailed information about image layers."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{json .RootFS.Layers}}", self.full_image_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            layer_ids = json.loads(result.stdout)
            layers = []
            
            for i, layer_id in enumerate(layer_ids):
                layers.append({
                    "index": i,
                    "id": layer_id,
                    "size": self._get_layer_size(layer_id)
                })
            
            return layers
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get image layers: {e}")
            return []
    
    def _get_layer_size(self, layer_id: str) -> int:
        """Get the size of a specific layer."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.Size}}", layer_id],
                capture_output=True,
                text=True,
                check=True
            )
            
            return int(result.stdout.strip())
            
        except (subprocess.CalledProcessError, ValueError):
            return 0
    
    def _get_image_size(self) -> Dict[str, int]:
        """Get the total size of the image."""
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Size}}", self.full_image_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            size_str = result.stdout.strip()
            size_bytes = self._parse_size_string(size_str)
            
            return {
                "formatted": size_str,
                "bytes": size_bytes
            }
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get image size: {e}")
            return {"formatted": "Unknown", "bytes": 0}
    
    def _parse_size_string(self, size_str: str) -> int:
        """Parse size string like '1.2GB' or '500MB' to bytes."""
        if not size_str or size_str == "Unknown":
            return 0
        
        # Extract number and unit
        match = re.match(r'([\d.]+)([KMGTPE]?B)', size_str.upper())
        if not match:
            return 0
        
        size_value = float(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
            'PB': 1024 ** 5,
            'EB': 1024 ** 6
        }
        
        return int(size_value * multipliers.get(unit, 1))
    
    def _analyze_layers(self, layers: List[Dict]) -> Dict:
        """Analyze layer efficiency and identify optimization opportunities."""
        if not layers:
            return {"error": "No layers to analyze"}
        
        total_size = sum(layer["size"] for layer in layers)
        layer_count = len(layers)
        
        # Identify large layers
        large_layers = [layer for layer in layers if layer["size"] > total_size * 0.1]
        
        # Identify empty or small layers
        empty_layers = [layer for layer in layers if layer["size"] < 1024]
        
        # Calculate efficiency metrics
        efficiency_score = self._calculate_efficiency_score(layers, total_size)
        
        return {
            "total_size": total_size,
            "layer_count": layer_count,
            "average_layer_size": total_size / layer_count if layer_count > 0 else 0,
            "large_layers": large_layers,
            "empty_layers": empty_layers,
            "efficiency_score": efficiency_score,
            "size_distribution": self._calculate_size_distribution(layers)
        }
    
    def _calculate_efficiency_score(self, layers: List[Dict], total_size: int) -> float:
        """Calculate layer efficiency score (0-100)."""
        if not layers or total_size == 0:
            return 0.0
        
        # Penalize too many layers
        layer_penalty = max(0, (len(layers) - 10) * 2)
        
        # Penalize large layers
        size_penalty = sum(layer["size"] / total_size * 10 for layer in layers if layer["size"] > total_size * 0.2)
        
        # Base score
        base_score = 100.0
        
        return max(0.0, base_score - layer_penalty - size_penalty)
    
    def _calculate_size_distribution(self, layers: List[Dict]) -> Dict:
        """Calculate size distribution across layers."""
        if not layers:
            return {}
        
        sizes = [layer["size"] for layer in layers]
        sizes.sort(reverse=True)
        
        return {
            "largest_layer": sizes[0] if sizes else 0,
            "smallest_layer": sizes[-1] if sizes else 0,
            "median_size": sizes[len(sizes) // 2] if sizes else 0,
            "size_variance": self._calculate_variance(sizes)
        }
    
    def _calculate_variance(self, sizes: List[int]) -> float:
        """Calculate variance in layer sizes."""
        if len(sizes) < 2:
            return 0.0
        
        mean = sum(sizes) / len(sizes)
        variance = sum((size - mean) ** 2 for size in sizes) / len(sizes)
        return variance
    
    def _generate_recommendations(self, layer_analysis: Dict, history: List[Dict]) -> List[str]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        if layer_analysis.get("efficiency_score", 0) < 70:
            recommendations.append("Consider optimizing layer structure - efficiency score is low")
        
        if layer_analysis.get("layer_count", 0) > 20:
            recommendations.append("Too many layers detected - consider combining RUN commands")
        
        large_layers = layer_analysis.get("large_layers", [])
        if large_layers:
            recommendations.append(f"Found {len(large_layers)} large layers - consider splitting or optimizing")
        
        empty_layers = layer_analysis.get("empty_layers", [])
        if empty_layers:
            recommendations.append(f"Found {len(empty_layers)} empty/small layers - consider removing")
        
        # Check for common optimization opportunities
        if history:
            for layer in history:
                command = layer.get("CreatedBy", "")
                if "RUN apt-get update" in command and "RUN apt-get install" in command:
                    recommendations.append("Combine apt-get commands into single RUN instruction")
                
                if "COPY" in command and "RUN" in command:
                    recommendations.append("Consider separating COPY and RUN operations")
        
        return recommendations

class LayerOptimizer:
    """Provides layer optimization strategies and generates optimized Dockerfiles."""
    
    def __init__(self, analysis_results: Dict):
        self.analysis_results = analysis_results
        self.optimization_strategies = []
    
    def generate_optimization_strategies(self) -> List[Dict]:
        """Generate specific optimization strategies based on analysis."""
        strategies = []
        layer_analysis = self.analysis_results.get("layer_analysis", {})
        recommendations = self.analysis_results.get("recommendations", [])
        
        # Strategy 1: Multi-stage build optimization
        if layer_analysis.get("layer_count", 0) > 15:
            strategies.append({
                "type": "multi_stage",
                "priority": "high",
                "description": "Implement multi-stage build to reduce final image size",
                "estimated_savings": "20-40%",
                "implementation": "Use separate build and runtime stages"
            })
        
        # Strategy 2: Layer consolidation
        if layer_analysis.get("efficiency_score", 0) < 80:
            strategies.append({
                "type": "layer_consolidation",
                "priority": "medium",
                "description": "Consolidate RUN commands to reduce layer count",
                "estimated_savings": "10-20%",
                "implementation": "Combine related RUN instructions with &&"
            })
        
        # Strategy 3: Base image optimization
        if any("large layers" in rec.lower() for rec in recommendations):
            strategies.append({
                "type": "base_image",
                "priority": "high",
                "description": "Use optimized base image (distroless or alpine)",
                "estimated_savings": "30-60%",
                "implementation": "Switch to distroless or alpine base image"
            })
        
        # Strategy 4: Dependency optimization
        if any("apt-get" in rec.lower() for rec in recommendations):
            strategies.append({
                "type": "dependency_cleanup",
                "priority": "medium",
                "description": "Clean up package managers and caches",
                "estimated_savings": "5-15%",
                "implementation": "Remove package caches and unnecessary packages"
            })
        
        self.optimization_strategies = strategies
        return strategies
    
    def generate_optimized_dockerfile(self, service_name: str) -> str:
        """Generate an optimized Dockerfile based on analysis."""
        strategies = self.optimization_strategies
        
        dockerfile_lines = [
            "# Optimized Dockerfile generated by layer optimizer",
            f"# Service: {service_name}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "# Multi-stage build for optimization",
            "FROM python:3.11-slim as builder",
            "",
            "# Install build dependencies",
            "RUN apt-get update && apt-get install -y \\",
            "    build-essential \\",
            "    && rm -rf /var/lib/apt/lists/* \\",
            "    && apt-get clean",
            "",
            "# Copy requirements and install Python dependencies",
            "COPY requirements.txt .",
            "RUN pip install --no-cache-dir --user -r requirements.txt",
            "",
            "# Runtime stage with distroless base",
            "FROM gcr.io/distroless/python3-debian11",
            "",
            "# Copy Python dependencies from builder",
            "COPY --from=builder /root/.local /root/.local",
            "",
            "# Copy application code",
            "COPY . /app",
            "WORKDIR /app",
            "",
            "# Set Python path",
            "ENV PYTHONPATH=/root/.local/lib/python3.11/site-packages:$PYTHONPATH",
            "",
            "# Run application",
            "ENTRYPOINT [\"python3\", \"-m\", \"app\"]",
        ]
        
        return "\n".join(dockerfile_lines)
    
    def generate_optimization_report(self) -> str:
        """Generate a detailed optimization report."""
        report_lines = [
            "# Docker Image Layer Optimization Report",
            f"Generated: {datetime.now().isoformat()}",
            f"Image: {self.analysis_results.get('image_name', 'Unknown')}",
            "",
            "## Analysis Summary",
            f"- Total Size: {self.analysis_results.get('size', {}).get('formatted', 'Unknown')}",
            f"- Layer Count: {self.analysis_results.get('layer_analysis', {}).get('layer_count', 'Unknown')}",
            f"- Efficiency Score: {self.analysis_results.get('layer_analysis', {}).get('efficiency_score', 0):.1f}/100",
            "",
            "## Recommendations",
        ]
        
        recommendations = self.analysis_results.get("recommendations", [])
        for i, rec in enumerate(recommendations, 1):
            report_lines.append(f"{i}. {rec}")
        
        if self.optimization_strategies:
            report_lines.extend([
                "",
                "## Optimization Strategies",
            ])
            
            for strategy in self.optimization_strategies:
                report_lines.extend([
                    f"### {strategy['type'].replace('_', ' ').title()}",
                    f"**Priority:** {strategy['priority']}",
                    f"**Description:** {strategy['description']}",
                    f"**Estimated Savings:** {strategy['estimated_savings']}",
                    f"**Implementation:** {strategy['implementation']}",
                    ""
                ])
        
        return "\n".join(report_lines)

def main():
    """Main function to run the layer optimization script."""
    parser = argparse.ArgumentParser(
        description="Optimize Docker image layers for better caching and smaller sizes"
    )
    parser.add_argument(
        "--service", 
        required=True,
        help="Service name to optimize (e.g., gui, blockchain, rdp)"
    )
    parser.add_argument(
        "--image",
        help="Full image name (overrides service-based naming)"
    )
    parser.add_argument(
        "--registry",
        default="ghcr.io",
        help="Container registry (default: ghcr.io)"
    )
    parser.add_argument(
        "--project-name",
        default="HamiGames/Lucid",
        help="Project name (default: HamiGames/Lucid)"
    )
    parser.add_argument(
        "--output-dir",
        default="build/optimization",
        help="Output directory for reports and optimized files"
    )
    parser.add_argument(
        "--generate-dockerfile",
        action="store_true",
        help="Generate optimized Dockerfile"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine image name
    if args.image:
        image_name = args.image
    else:
        image_name = args.service
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Analyze the image
        analyzer = DockerImageAnalyzer(
            image_name=image_name,
            registry=args.registry,
            project_name=args.project_name
        )
        
        logger.info("Starting image analysis...")
        analysis_results = analyzer.analyze_image()
        
        # Generate optimization strategies
        optimizer = LayerOptimizer(analysis_results)
        strategies = optimizer.generate_optimization_strategies()
        
        # Save analysis results
        analysis_file = output_dir / f"{args.service}_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis_results, f, indent=2)
        logger.info(f"Analysis results saved to: {analysis_file}")
        
        # Generate optimization report
        report = optimizer.generate_optimization_report()
        report_file = output_dir / f"{args.service}_optimization_report.md"
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"Optimization report saved to: {report_file}")
        
        # Generate optimized Dockerfile if requested
        if args.generate_dockerfile:
            optimized_dockerfile = optimizer.generate_optimized_dockerfile(args.service)
            dockerfile_file = output_dir / f"Dockerfile.{args.service}.optimized"
            with open(dockerfile_file, 'w') as f:
                f.write(optimized_dockerfile)
            logger.info(f"Optimized Dockerfile saved to: {dockerfile_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("LAYER OPTIMIZATION SUMMARY")
        print("="*60)
        print(f"Service: {args.service}")
        print(f"Image: {analysis_results.get('image_name', 'Unknown')}")
        print(f"Size: {analysis_results.get('size', {}).get('formatted', 'Unknown')}")
        print(f"Layers: {analysis_results.get('layer_analysis', {}).get('layer_count', 'Unknown')}")
        print(f"Efficiency Score: {analysis_results.get('layer_analysis', {}).get('efficiency_score', 0):.1f}/100")
        print(f"Strategies Generated: {len(strategies)}")
        print("="*60)
        
        if strategies:
            print("\nTop Optimization Strategies:")
            for i, strategy in enumerate(strategies[:3], 1):
                print(f"{i}. {strategy['description']} (Priority: {strategy['priority']})")
        
        print(f"\nDetailed report available at: {report_file}")
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == "__main__":
    main()