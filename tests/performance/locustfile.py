"""
Locust Performance Testing Configuration for Lucid RDP System

This file defines Locust load testing scenarios for the Lucid RDP system.
It tests various endpoints with realistic user behavior patterns.

Usage:
    locust -f tests/performance/locustfile.py --host=http://localhost:8080
    locust -f tests/performance/locustfile.py --host=http://localhost:8080 --users=100 --spawn-rate=10
"""

from locust import HttpUser, task, between, SequentialTaskSet
import random
import json
import time
from typing import Dict, Any


class UserBehavior(SequentialTaskSet):
    """Simulates realistic user behavior patterns"""
    
    def on_start(self):
        """Called when a user starts"""
        self.user_id = f"user_{random.randint(1000, 9999)}"
        self.session_id = None
        self.auth_token = None
        
    @task(3)
    def health_check(self):
        """Check system health - most common operation"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(2)
    def authenticate(self):
        """User authentication flow"""
        login_data = {
            "username": f"test_user_{random.randint(1, 100)}",
            "password": "test_password_123"
        }
        
        with self.client.post("/auth/login", 
                             json=login_data, 
                             catch_response=True) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.auth_token = data.get("token")
                    response.success()
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Authentication failed: {response.status_code}")
    
    @task(1)
    def create_session(self):
        """Create a new RDP session"""
        if not self.auth_token:
            return
            
        session_data = {
            "user_id": self.user_id,
            "session_type": "rdp",
            "duration_minutes": random.randint(30, 180)
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.post("/sessions", 
                             json=session_data,
                             headers=headers,
                             catch_response=True) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.session_id = data.get("session_id")
                    response.success()
                except:
                    response.failure("Invalid session response")
            else:
                response.failure(f"Session creation failed: {response.status_code}")
    
    @task(2)
    def get_sessions(self):
        """Retrieve user sessions"""
        if not self.auth_token:
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get("/sessions", 
                           headers=headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get sessions failed: {response.status_code}")
    
    @task(1)
    def get_blockchain_info(self):
        """Get blockchain information"""
        with self.client.get("/chain/info", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Blockchain info failed: {response.status_code}")
    
    @task(1)
    def get_node_status(self):
        """Get node status information"""
        with self.client.get("/nodes/status", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Node status failed: {response.status_code}")
    
    @task(1)
    def terminate_session(self):
        """Terminate a session"""
        if not self.session_id or not self.auth_token:
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.delete(f"/sessions/{self.session_id}",
                               headers=headers,
                               catch_response=True) as response:
            if response.status_code in [200, 204]:
                self.session_id = None
                response.success()
            else:
                response.failure(f"Session termination failed: {response.status_code}")


class APIUser(HttpUser):
    """Main user class for API Gateway testing"""
    tasks = [UserBehavior]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts"""
        pass
    
    def on_stop(self):
        """Called when a user stops"""
        pass


class BlockchainUser(HttpUser):
    """Specialized user for blockchain operations"""
    tasks = [BlockchainBehavior]
    wait_time = between(5, 10)  # Blockchain operations are less frequent


class BlockchainBehavior(SequentialTaskSet):
    """Blockchain-specific user behavior"""
    
    @task(3)
    def get_chain_info(self):
        """Get blockchain information"""
        with self.client.get("/chain/info", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Chain info failed: {response.status_code}")
    
    @task(2)
    def get_latest_block(self):
        """Get latest block information"""
        with self.client.get("/chain/blocks/latest", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Latest block failed: {response.status_code}")
    
    @task(1)
    def anchor_session(self):
        """Anchor a session to blockchain"""
        session_data = {
            "session_id": f"session_{random.randint(1000, 9999)}",
            "data_hash": f"hash_{random.randint(10000, 99999)}",
            "timestamp": int(time.time())
        }
        
        with self.client.post("/chain/anchor", 
                             json=session_data,
                             catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Session anchoring failed: {response.status_code}")
    
    @task(1)
    def get_consensus_status(self):
        """Get consensus status"""
        with self.client.get("/chain/consensus/status", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Consensus status failed: {response.status_code}")


class SessionUser(HttpUser):
    """Specialized user for session management"""
    tasks = [SessionBehavior]
    wait_time = between(2, 5)


class SessionBehavior(SequentialTaskSet):
    """Session management user behavior"""
    
    def on_start(self):
        """Initialize session user"""
        self.session_id = None
        self.auth_token = None
    
    @task(2)
    def authenticate(self):
        """Authenticate user"""
        login_data = {
            "username": f"session_user_{random.randint(1, 50)}",
            "password": "session_password_123"
        }
        
        with self.client.post("/auth/login", 
                             json=login_data,
                             catch_response=True) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.auth_token = data.get("token")
                    response.success()
                except:
                    response.failure("Invalid auth response")
            else:
                response.failure(f"Authentication failed: {response.status_code}")
    
    @task(3)
    def create_session(self):
        """Create new session"""
        if not self.auth_token:
            return
            
        session_data = {
            "user_id": f"user_{random.randint(1000, 9999)}",
            "session_type": "rdp",
            "duration_minutes": random.randint(30, 120),
            "quality": random.choice(["low", "medium", "high"])
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.post("/sessions", 
                             json=session_data,
                             headers=headers,
                             catch_response=True) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.session_id = data.get("session_id")
                    response.success()
                except:
                    response.failure("Invalid session response")
            else:
                response.failure(f"Session creation failed: {response.status_code}")
    
    @task(4)
    def get_session_status(self):
        """Get session status"""
        if not self.session_id or not self.auth_token:
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get(f"/sessions/{self.session_id}",
                           headers=headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get session failed: {response.status_code}")
    
    @task(1)
    def terminate_session(self):
        """Terminate session"""
        if not self.session_id or not self.auth_token:
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.delete(f"/sessions/{self.session_id}",
                               headers=headers,
                               catch_response=True) as response:
            if response.status_code in [200, 204]:
                self.session_id = None
                response.success()
            else:
                response.failure(f"Session termination failed: {response.status_code}")


class AdminUser(HttpUser):
    """Specialized user for admin operations"""
    tasks = [AdminBehavior]
    wait_time = between(10, 30)  # Admin operations are less frequent


class AdminBehavior(SequentialTaskSet):
    """Admin user behavior"""
    
    def on_start(self):
        """Initialize admin user"""
        self.admin_token = None
    
    @task(1)
    def admin_login(self):
        """Admin authentication"""
        admin_data = {
            "username": "admin",
            "password": "admin_password_123"
        }
        
        with self.client.post("/admin/auth/login", 
                             json=admin_data,
                             catch_response=True) as response:
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    self.admin_token = data.get("token")
                    response.success()
                except:
                    response.failure("Invalid admin auth response")
            else:
                response.failure(f"Admin login failed: {response.status_code}")
    
    @task(2)
    def get_dashboard(self):
        """Get admin dashboard"""
        if not self.admin_token:
            return
            
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        with self.client.get("/admin/dashboard/overview",
                           headers=headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Dashboard failed: {response.status_code}")
    
    @task(1)
    def get_system_metrics(self):
        """Get system metrics"""
        if not self.admin_token:
            return
            
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        with self.client.get("/admin/dashboard/metrics",
                           headers=headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")
    
    @task(1)
    def get_user_list(self):
        """Get user list"""
        if not self.admin_token:
            return
            
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        with self.client.get("/admin/users/",
                           headers=headers,
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"User list failed: {response.status_code}")


# Performance test scenarios
class PerformanceTestScenarios:
    """Predefined performance test scenarios"""
    
    @staticmethod
    def get_light_load_scenario():
        """Light load scenario - 50 users"""
        return {
            "users": 50,
            "spawn_rate": 5,
            "duration": "5m"
        }
    
    @staticmethod
    def get_medium_load_scenario():
        """Medium load scenario - 200 users"""
        return {
            "users": 200,
            "spawn_rate": 10,
            "duration": "10m"
        }
    
    @staticmethod
    def get_heavy_load_scenario():
        """Heavy load scenario - 500 users"""
        return {
            "users": 500,
            "spawn_rate": 20,
            "duration": "15m"
        }
    
    @staticmethod
    def get_stress_test_scenario():
        """Stress test scenario - 1000 users"""
        return {
            "users": 1000,
            "spawn_rate": 50,
            "duration": "20m"
        }


# Custom metrics for monitoring
class CustomMetrics:
    """Custom metrics for performance monitoring"""
    
    @staticmethod
    def calculate_response_time_percentiles(response_times: list) -> Dict[str, float]:
        """Calculate response time percentiles"""
        if not response_times:
            return {}
        
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        
        return {
            "p50": sorted_times[int(n * 0.5)],
            "p90": sorted_times[int(n * 0.9)],
            "p95": sorted_times[int(n * 0.95)],
            "p99": sorted_times[int(n * 0.99)],
            "max": sorted_times[-1]
        }
    
    @staticmethod
    def calculate_throughput(total_requests: int, duration_seconds: float) -> float:
        """Calculate requests per second"""
        return total_requests / duration_seconds if duration_seconds > 0 else 0
    
    @staticmethod
    def calculate_error_rate(failed_requests: int, total_requests: int) -> float:
        """Calculate error rate percentage"""
        return (failed_requests / total_requests * 100) if total_requests > 0 else 0


if __name__ == "__main__":
    # Run with default settings
    print("Locust performance testing for Lucid RDP System")
    print("Usage: locust -f tests/performance/locustfile.py --host=http://localhost:8080")
    print("Available user classes:")
    print("- APIUser: General API operations")
    print("- BlockchainUser: Blockchain-specific operations")
    print("- SessionUser: Session management operations")
    print("- AdminUser: Admin operations")
