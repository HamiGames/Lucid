#!/usr/bin/env python3
"""
LUCID Monitoring Service - SPEC-1B Implementation
Monitoring and metrics collection for microservices
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import psutil
import aiohttp
from fastapi import FastAPI, HTTPException, Request
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceMetrics:
    """Service metrics structure"""
    service_name: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    request_count: int
    error_count: int
    response_time_avg: float
    response_time_p95: float
    response_time_p99: float
    active_connections: int

@dataclass
class SystemMetrics:
    """System metrics structure"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    load_average: List[float]
    uptime: int

class MonitoringService:
    """Monitoring service for Lucid microservices"""
    
    def __init__(self):
        self.app = FastAPI(
            title="LUCID Monitoring Service",
            description="Monitoring and metrics collection for Lucid RDP services",
            version="1.0.0"
        )
        
        # Metrics storage
        self.metrics: Dict[str, List[ServiceMetrics]] = {}
        self.system_metrics: List[SystemMetrics] = []
        
        # Configuration
        self.config = {
            'metrics_retention_hours': 24,
            'collection_interval': 30,
            'alert_thresholds': {
                'cpu_usage': 80.0,
                'memory_usage': 85.0,
                'disk_usage': 90.0,
                'response_time_p95': 1000.0,
                'error_rate': 5.0
            }
        }
        
        # Setup routes
        self.setup_routes()
        
        # Start metrics collection
        asyncio.create_task(self.metrics_collection_loop())
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "monitored_services": len(self.metrics)
            }
        
        @self.app.post("/api/v1/metrics/submit")
        async def submit_metrics(request: Request):
            """Submit metrics for a service"""
            try:
                data = await request.json()
                
                # Validate required fields
                required_fields = ['service_name', 'timestamp']
                for field in required_fields:
                    if field not in data:
                        raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
                
                # Create metrics object
                metrics = ServiceMetrics(
                    service_name=data['service_name'],
                    timestamp=datetime.fromisoformat(data['timestamp']),
                    cpu_usage=data.get('cpu_usage', 0.0),
                    memory_usage=data.get('memory_usage', 0.0),
                    disk_usage=data.get('disk_usage', 0.0),
                    network_io=data.get('network_io', {}),
                    request_count=data.get('request_count', 0),
                    error_count=data.get('error_count', 0),
                    response_time_avg=data.get('response_time_avg', 0.0),
                    response_time_p95=data.get('response_time_p95', 0.0),
                    response_time_p99=data.get('response_time_p99', 0.0),
                    active_connections=data.get('active_connections', 0)
                )
                
                # Store metrics
                await self.store_metrics(metrics)
                
                return {
                    "status": "success",
                    "message": f"Metrics submitted for {data['service_name']}"
                }
                
            except Exception as e:
                logger.error(f"Submit metrics error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/metrics/services")
        async def list_services():
            """List all monitored services"""
            try:
                services = list(self.metrics.keys())
                
                return {
                    "status": "success",
                    "services": services,
                    "total": len(services)
                }
                
            except Exception as e:
                logger.error(f"List services error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/metrics/services/{service_name}")
        async def get_service_metrics(service_name: str, hours: int = 1):
            """Get metrics for a specific service"""
            try:
                if service_name not in self.metrics:
                    raise HTTPException(status_code=404, detail="Service not found")
                
                # Filter metrics by time range
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                filtered_metrics = [
                    m for m in self.metrics[service_name]
                    if m.timestamp >= cutoff_time
                ]
                
                # Convert to dict for JSON serialization
                metrics_data = [asdict(m) for m in filtered_metrics]
                
                return {
                    "status": "success",
                    "service_name": service_name,
                    "metrics": metrics_data,
                    "total": len(metrics_data)
                }
                
            except Exception as e:
                logger.error(f"Get service metrics error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/metrics/system")
        async def get_system_metrics(hours: int = 1):
            """Get system metrics"""
            try:
                # Filter metrics by time range
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                filtered_metrics = [
                    m for m in self.system_metrics
                    if m.timestamp >= cutoff_time
                ]
                
                # Convert to dict for JSON serialization
                metrics_data = [asdict(m) for m in filtered_metrics]
                
                return {
                    "status": "success",
                    "system_metrics": metrics_data,
                    "total": len(metrics_data)
                }
                
            except Exception as e:
                logger.error(f"Get system metrics error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/metrics/alerts")
        async def get_alerts():
            """Get current alerts"""
            try:
                alerts = await self.check_alerts()
                
                return {
                    "status": "success",
                    "alerts": alerts,
                    "total": len(alerts)
                }
                
            except Exception as e:
                logger.error(f"Get alerts error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        @self.app.get("/api/v1/metrics/dashboard")
        async def get_dashboard_data():
            """Get dashboard data"""
            try:
                dashboard_data = await self.generate_dashboard_data()
                
                return {
                    "status": "success",
                    "dashboard": dashboard_data
                }
                
            except Exception as e:
                logger.error(f"Get dashboard data error: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    
    async def store_metrics(self, metrics: ServiceMetrics):
        """Store service metrics"""
        try:
            service_name = metrics.service_name
            
            if service_name not in self.metrics:
                self.metrics[service_name] = []
            
            # Add metrics
            self.metrics[service_name].append(metrics)
            
            # Clean up old metrics
            await self.cleanup_old_metrics()
            
        except Exception as e:
            logger.error(f"Store metrics error: {e}")
    
    async def cleanup_old_metrics(self):
        """Clean up old metrics"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.config['metrics_retention_hours'])
            
            for service_name in self.metrics:
                self.metrics[service_name] = [
                    m for m in self.metrics[service_name]
                    if m.timestamp >= cutoff_time
                ]
            
            # Clean up system metrics
            self.system_metrics = [
                m for m in self.system_metrics
                if m.timestamp >= cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Cleanup old metrics error: {e}")
    
    async def collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # Get system information
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            load_avg = psutil.getloadavg()
            uptime = int(time.time() - psutil.boot_time())
            
            # Create system metrics
            system_metrics = SystemMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                network_io={
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                load_average=list(load_avg),
                uptime=uptime
            )
            
            # Store system metrics
            self.system_metrics.append(system_metrics)
            
        except Exception as e:
            logger.error(f"Collect system metrics error: {e}")
    
    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alerts based on thresholds"""
        try:
            alerts = []
            
            # Check system metrics
            if self.system_metrics:
                latest_system = self.system_metrics[-1]
                
                if latest_system.cpu_usage > self.config['alert_thresholds']['cpu_usage']:
                    alerts.append({
                        "type": "system",
                        "metric": "cpu_usage",
                        "value": latest_system.cpu_usage,
                        "threshold": self.config['alert_thresholds']['cpu_usage'],
                        "severity": "high",
                        "timestamp": latest_system.timestamp.isoformat()
                    })
                
                if latest_system.memory_usage > self.config['alert_thresholds']['memory_usage']:
                    alerts.append({
                        "type": "system",
                        "metric": "memory_usage",
                        "value": latest_system.memory_usage,
                        "threshold": self.config['alert_thresholds']['memory_usage'],
                        "severity": "high",
                        "timestamp": latest_system.timestamp.isoformat()
                    })
                
                if latest_system.disk_usage > self.config['alert_thresholds']['disk_usage']:
                    alerts.append({
                        "type": "system",
                        "metric": "disk_usage",
                        "value": latest_system.disk_usage,
                        "threshold": self.config['alert_thresholds']['disk_usage'],
                        "severity": "critical",
                        "timestamp": latest_system.timestamp.isoformat()
                    })
            
            # Check service metrics
            for service_name, metrics_list in self.metrics.items():
                if not metrics_list:
                    continue
                
                latest_metrics = metrics_list[-1]
                
                # Check response time
                if latest_metrics.response_time_p95 > self.config['alert_thresholds']['response_time_p95']:
                    alerts.append({
                        "type": "service",
                        "service": service_name,
                        "metric": "response_time_p95",
                        "value": latest_metrics.response_time_p95,
                        "threshold": self.config['alert_thresholds']['response_time_p95'],
                        "severity": "medium",
                        "timestamp": latest_metrics.timestamp.isoformat()
                    })
                
                # Check error rate
                if latest_metrics.request_count > 0:
                    error_rate = (latest_metrics.error_count / latest_metrics.request_count) * 100
                    if error_rate > self.config['alert_thresholds']['error_rate']:
                        alerts.append({
                            "type": "service",
                            "service": service_name,
                            "metric": "error_rate",
                            "value": error_rate,
                            "threshold": self.config['alert_thresholds']['error_rate'],
                            "severity": "high",
                            "timestamp": latest_metrics.timestamp.isoformat()
                        })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Check alerts error: {e}")
            return []
    
    async def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate dashboard data"""
        try:
            dashboard_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "services": {},
                "system": {},
                "alerts": await self.check_alerts()
            }
            
            # Get latest system metrics
            if self.system_metrics:
                latest_system = self.system_metrics[-1]
                dashboard_data["system"] = asdict(latest_system)
            
            # Get latest service metrics
            for service_name, metrics_list in self.metrics.items():
                if metrics_list:
                    latest_metrics = metrics_list[-1]
                    dashboard_data["services"][service_name] = asdict(latest_metrics)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Generate dashboard data error: {e}")
            return {"timestamp": datetime.utcnow().isoformat(), "error": str(e)}
    
    async def metrics_collection_loop(self):
        """Periodic metrics collection loop"""
        while True:
            try:
                # Collect system metrics
                await self.collect_system_metrics()
                
                # Clean up old metrics
                await self.cleanup_old_metrics()
                
                await asyncio.sleep(self.config['collection_interval'])
                
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(10)

# Initialize monitoring service
monitoring_service = MonitoringService()

if __name__ == "__main__":
    uvicorn.run(
        "monitoring:monitoring_service.app",
        host="0.0.0.0",
        port=8084,
        reload=True,
        log_level="info"
    )
