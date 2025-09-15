"""Data models for CoAP Main Server."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class UpdateType(str, Enum):
    """Update type enumeration."""
    SERVICE = "service"
    DRIVER = "driver"
    PACKAGE = "package"


class UpdateStatus(str, Enum):
    """Update status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class NodeStatus(str, Enum):
    """Node status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class UpdateRequest:
    """Update request model."""
    
    def __init__(self, **kwargs):
        self.target_nodes: List[str] = kwargs.get('target_nodes', [])
        self.update_type: UpdateType = UpdateType(kwargs.get('update_type', 'package'))
        self.package_name: str = kwargs.get('package_name', '')
        self.package_version: str = kwargs.get('package_version', '')
        self.package_size: int = kwargs.get('package_size', 0)
        self.checksum: str = kwargs.get('checksum', '')
        self.description: str = kwargs.get('description', '')


class UpdateJob:
    """Update job model."""
    
    def __init__(self, **kwargs):
        self.job_id: str = kwargs.get('job_id', '')
        self.update_request: UpdateRequest = kwargs.get('update_request')
        self.status: UpdateStatus = UpdateStatus(kwargs.get('status', 'pending'))
        self.created_at: datetime = kwargs.get('created_at', datetime.now())
        self.started_at: Optional[datetime] = kwargs.get('started_at')
        self.completed_at: Optional[datetime] = kwargs.get('completed_at')
        self.node_statuses: Dict[str, str] = kwargs.get('node_statuses', {})
        self.error_message: Optional[str] = kwargs.get('error_message')


class NodeInfo:
    """Node information model."""
    
    def __init__(self, **kwargs):
        self.node_id: str = kwargs.get('node_id', '')
        self.hostname: str = kwargs.get('hostname', '')
        self.ip_address: str = kwargs.get('ip_address', '')
        self.status: NodeStatus = NodeStatus(kwargs.get('status', 'offline'))
        self.last_seen: datetime = kwargs.get('last_seen', datetime.now())
        self.services: List[str] = kwargs.get('services', [])
        self.drivers: List[str] = kwargs.get('drivers', [])
        self.system_info: Dict[str, Any] = kwargs.get('system_info', {})
    
    def dict(self):
        """Convert to dictionary."""
        return {
            'node_id': self.node_id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat(),
            'services': self.services,
            'drivers': self.drivers,
            'system_info': self.system_info
        }


class NodeUpdateStatus:
    """Node update status model."""
    
    def __init__(self, **kwargs):
        self.node_id: str = kwargs.get('node_id', '')
        self.job_id: str = kwargs.get('job_id', '')
        self.status: UpdateStatus = UpdateStatus(kwargs.get('status', 'pending'))
        self.started_at: datetime = kwargs.get('started_at', datetime.now())
        self.completed_at: Optional[datetime] = kwargs.get('completed_at')
        self.error_message: Optional[str] = kwargs.get('error_message')
        self.health_check_passed: bool = kwargs.get('health_check_passed', False)


class HealthCheckResult:
    """Health check result model."""
    
    def __init__(self, **kwargs):
        self.node_id: str = kwargs.get('node_id', '')
        self.timestamp: datetime = kwargs.get('timestamp', datetime.now())
        self.overall_healthy: bool = kwargs.get('overall_healthy', True)
        self.cpu_percent: float = kwargs.get('cpu_percent', 0.0)
        self.memory_percent: float = kwargs.get('memory_percent', 0.0)
        self.disk_percent: float = kwargs.get('disk_percent', 0.0)
        self.temperature: float = kwargs.get('temperature', 0.0)
        self.services_status: Dict[str, bool] = kwargs.get('services_status', {})
        self.error_messages: List[str] = kwargs.get('error_messages', [])
    
    def dict(self):
        """Convert to dictionary."""
        return {
            'node_id': self.node_id,
            'timestamp': self.timestamp.isoformat(),
            'overall_healthy': self.overall_healthy,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'temperature': self.temperature,
            'services_status': self.services_status,
            'error_messages': self.error_messages
        }
