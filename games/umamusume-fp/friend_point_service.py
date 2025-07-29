"""
Friend Point Service Management
Handles the business logic for the friend point spam service
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class ServiceStatus(Enum):
    """Service status enumeration"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ServiceRequest:
    """Friend point service request"""
    request_id: str
    buyer_id: str
    target_points: int
    support_card_type: str
    priority: str = "normal"
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    status: ServiceStatus = ServiceStatus.IDLE
    points_earned: int = 0
    cycles_completed: int = 0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ServiceStats:
    """Service statistics"""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    total_points_earned: int = 0
    average_points_per_request: float = 0.0
    total_runtime_hours: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class FriendPointService:
    """Friend Point Spam Service Manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "games/umamusume-fp/config.json"
        self.config = self._load_config()
        
        # Service state
        self.requests: Dict[str, ServiceRequest] = {}
        self.active_requests: List[str] = []
        self.stats = ServiceStats()
        
        # Service settings
        self.max_concurrent_requests = self.config.get('service_config', {}).get('max_concurrent_requests', 3)
        self.auto_restart = self.config.get('service_config', {}).get('auto_restart_on_completion', True)
        self.point_target = self.config.get('service_config', {}).get('friend_point_target', 1000)
        
        # Notification settings
        self.notification_config = self.config.get('service_config', {}).get('notification_settings', {})
        
        # Load existing requests if any
        self._load_requests()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load service configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def _load_requests(self):
        """Load existing requests from storage"""
        try:
            requests_file = Path("games/umamusume-fp/requests.json")
            if requests_file.exists():
                with open(requests_file, 'r') as f:
                    data = json.load(f)
                    for req_data in data.get('requests', []):
                        request = ServiceRequest(**req_data)
                        request.created_at = datetime.fromisoformat(req_data['created_at'])
                        if req_data.get('completed_at'):
                            request.completed_at = datetime.fromisoformat(req_data['completed_at'])
                        request.status = ServiceStatus(req_data['status'])
                        self.requests[request.request_id] = request
                
                # Load stats
                stats_data = data.get('stats', {})
                self.stats = ServiceStats(**stats_data)
                if stats_data.get('last_updated'):
                    self.stats.last_updated = datetime.fromisoformat(stats_data['last_updated'])
                    
        except Exception as e:
            print(f"❌ Error loading requests: {e}")
    
    def _save_requests(self):
        """Save requests to storage"""
        try:
            requests_file = Path("games/umamusume-fp/requests.json")
            
            # Convert requests to serializable format
            requests_data = []
            for request in self.requests.values():
                req_dict = asdict(request)
                req_dict['created_at'] = request.created_at.isoformat()
                if request.completed_at:
                    req_dict['completed_at'] = request.completed_at.isoformat()
                req_dict['status'] = request.status.value
                requests_data.append(req_dict)
            
            # Convert stats to serializable format
            stats_dict = asdict(self.stats)
            stats_dict['last_updated'] = self.stats.last_updated.isoformat()
            
            data = {
                'requests': requests_data,
                'stats': stats_dict
            }
            
            with open(requests_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"❌ Error saving requests: {e}")
    
    def create_request(self, buyer_id: str, target_points: int, support_card_type: str = "auto", 
                      priority: str = "normal") -> str:
        """Create a new friend point service request"""
        request_id = f"fp_{int(time.time())}_{buyer_id}"
        
        request = ServiceRequest(
            request_id=request_id,
            buyer_id=buyer_id,
            target_points=target_points,
            support_card_type=support_card_type,
            priority=priority
        )
        
        self.requests[request_id] = request
        self.stats.total_requests += 1
        self._save_requests()
        
        print(f"✅ Created friend point request: {request_id}")
        print(f"   👤 Buyer: {buyer_id}")
        print(f"   🎯 Target: {target_points} points")
        print(f"   🎴 Support card: {support_card_type}")
        print(f"   ⚡ Priority: {priority}")
        
        return request_id
    
    def start_request(self, request_id: str) -> bool:
        """Start processing a friend point request"""
        if request_id not in self.requests:
            print(f"❌ Request {request_id} not found")
            return False
        
        request = self.requests[request_id]
        
        if request.status != ServiceStatus.IDLE:
            print(f"❌ Request {request_id} is not in idle state")
            return False
        
        if len(self.active_requests) >= self.max_concurrent_requests:
            print(f"❌ Maximum concurrent requests reached ({self.max_concurrent_requests})")
            return False
        
        request.status = ServiceStatus.RUNNING
        self.active_requests.append(request_id)
        self._save_requests()
        
        print(f"🚀 Started processing request: {request_id}")
        return True
    
    def pause_request(self, request_id: str) -> bool:
        """Pause processing a friend point request"""
        if request_id not in self.requests:
            return False
        
        request = self.requests[request_id]
        if request.status == ServiceStatus.RUNNING:
            request.status = ServiceStatus.PAUSED
            if request_id in self.active_requests:
                self.active_requests.remove(request_id)
            self._save_requests()
            print(f"⏸️ Paused request: {request_id}")
            return True
        
        return False
    
    def resume_request(self, request_id: str) -> bool:
        """Resume processing a friend point request"""
        if request_id not in self.requests:
            return False
        
        request = self.requests[request_id]
        if request.status == ServiceStatus.PAUSED and len(self.active_requests) < self.max_concurrent_requests:
            request.status = ServiceStatus.RUNNING
            self.active_requests.append(request_id)
            self._save_requests()
            print(f"▶️ Resumed request: {request_id}")
            return True
        
        return False
    
    def complete_request(self, request_id: str, points_earned: int, cycles_completed: int, 
                       error_message: Optional[str] = None) -> bool:
        """Mark a request as completed"""
        if request_id not in self.requests:
            return False
        
        request = self.requests[request_id]
        request.completed_at = datetime.now()
        request.points_earned = points_earned
        request.cycles_completed = cycles_completed
        
        if error_message:
            request.status = ServiceStatus.ERROR
            request.error_message = error_message
            self.stats.failed_requests += 1
        else:
            request.status = ServiceStatus.COMPLETED
            self.stats.completed_requests += 1
            self.stats.total_points_earned += points_earned
        
        if request_id in self.active_requests:
            self.active_requests.remove(request_id)
        
        # Update average points
        if self.stats.completed_requests > 0:
            self.stats.average_points_per_request = self.stats.total_points_earned / self.stats.completed_requests
        
        self.stats.last_updated = datetime.now()
        self._save_requests()
        
        print(f"✅ Completed request: {request_id}")
        print(f"   💎 Points earned: {points_earned}")
        print(f"   🔄 Cycles completed: {cycles_completed}")
        if error_message:
            print(f"   ❌ Error: {error_message}")
        
        return True
    
    def update_request_progress(self, request_id: str, points_earned: int, cycles_completed: int) -> bool:
        """Update progress for an active request"""
        if request_id not in self.requests:
            return False
        
        request = self.requests[request_id]
        if request.status == ServiceStatus.RUNNING:
            request.points_earned = points_earned
            request.cycles_completed = cycles_completed
            
            # Check if target reached
            if points_earned >= request.target_points:
                self.complete_request(request_id, points_earned, cycles_completed)
                return True
            
            self._save_requests()
            return True
        
        return False
    
    def get_request(self, request_id: str) -> Optional[ServiceRequest]:
        """Get a specific request"""
        return self.requests.get(request_id)
    
    def get_active_requests(self) -> List[ServiceRequest]:
        """Get all active requests"""
        return [self.requests[req_id] for req_id in self.active_requests if req_id in self.requests]
    
    def get_pending_requests(self) -> List[ServiceRequest]:
        """Get all pending (idle) requests"""
        return [req for req in self.requests.values() if req.status == ServiceStatus.IDLE]
    
    def get_service_stats(self) -> ServiceStats:
        """Get current service statistics"""
        return self.stats
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'total_requests': len(self.requests),
            'active_requests': len(self.active_requests),
            'pending_requests': len(self.get_pending_requests()),
            'max_concurrent': self.max_concurrent_requests,
            'stats': asdict(self.stats)
        }
    
    def should_send_notification(self, request: ServiceRequest, points_earned: int) -> bool:
        """Check if a notification should be sent"""
        if not self.notification_config:
            return False
        
        # Check for SSR support notification
        if self.notification_config.get('notify_on_ssr_support', False):
            # This would need to be implemented based on actual support card detection
            pass
        
        # Check for high points notification
        if self.notification_config.get('notify_on_high_points', False):
            threshold = self.notification_config.get('high_points_threshold', 100)
            if points_earned >= threshold:
                return True
        
        return False
    
    def format_notification_message(self, request: ServiceRequest, points_earned: int) -> str:
        """Format a notification message for Discord"""
        message = f"🎯 **Friend Point Service Update**\n"
        message += f"📋 Request: `{request.request_id}`\n"
        message += f"👤 Buyer: `{request.buyer_id}`\n"
        message += f"💎 Points Earned: `{points_earned}`\n"
        message += f"🎯 Target: `{request.target_points}`\n"
        message += f"🔄 Cycles: `{request.cycles_completed}`\n"
        
        if points_earned >= request.target_points:
            message += f"✅ **TARGET REACHED!**\n"
        
        return message 