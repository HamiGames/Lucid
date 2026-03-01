#!/usr/bin/env python3
"""
Elasticsearch Distroless Startup Script
Handles Elasticsearch initialization and configuration for distroless container
"""

import os
import sys
import subprocess
import signal
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('elasticsearch-distroless')

class ElasticsearchDistroless:
    def __init__(self):
        self.elasticsearch_process = None
        self.data_dir = Path('/usr/share/elasticsearch/data')
        
    def setup_directories(self):
        """Create necessary directories with proper permissions"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {self.data_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            sys.exit(1)
    
    def get_elasticsearch_command(self):
        """Build Elasticsearch command with security and performance settings"""
        # Set Java options
        java_opts = os.getenv('ES_JAVA_OPTS', '-Xms512m -Xmx512m')
        os.environ['ES_JAVA_OPTS'] = java_opts
        
        cmd = [
            '/usr/bin/elasticsearch',
            '-E', 'discovery.type=single-node',
            '-E', 'xpack.security.enabled=false',
            '-E', f'cluster.name={os.getenv("ELASTICSEARCH_CLUSTER_NAME", "lucid-cluster")}',
            '-E', f'node.name={os.getenv("ELASTICSEARCH_NODE_NAME", "lucid-node")}',
            '-E', 'bootstrap.memory_lock=true'
        ]
        
        return cmd
    
    def start_elasticsearch(self):
        """Start Elasticsearch with proper configuration"""
        try:
            cmd = self.get_elasticsearch_command()
            logger.info(f"Starting Elasticsearch with command: {' '.join(cmd)}")
            
            # Start Elasticsearch process
            self.elasticsearch_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for Elasticsearch to start
            time.sleep(10)
            
            if self.elasticsearch_process.poll() is None:
                logger.info("Elasticsearch started successfully")
                return True
            else:
                logger.error("Elasticsearch failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Elasticsearch: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down Elasticsearch...")
        if self.elasticsearch_process:
            self.elasticsearch_process.terminate()
            self.elasticsearch_process.wait(timeout=30)
        sys.exit(0)
    
    def run(self):
        """Main execution loop"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Setup directories
        self.setup_directories()
        
        # Start Elasticsearch
        if not self.start_elasticsearch():
            logger.error("Failed to start Elasticsearch")
            sys.exit(1)
        
        # Keep running
        try:
            while True:
                if self.elasticsearch_process and self.elasticsearch_process.poll() is not None:
                    logger.error("Elasticsearch process died unexpectedly")
                    sys.exit(1)
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            self.signal_handler(signal.SIGTERM, None)

if __name__ == '__main__':
    elasticsearch = ElasticsearchDistroless()
    elasticsearch.run()
