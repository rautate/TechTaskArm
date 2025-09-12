"""Data models for the Main Server."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class UpdateType(str, Enum):
    """Types of updates that can be performed."""
    SERVICE = "service"
    DRIVER = "driver"
    PACKAGE = "package"


class UpdateStatus(str, Enum):
    """Status of an update operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class NodeStatus(str, Enum):
    """Status of a regular node."""
    ONLINE = "online"
    OFFLINE = "offline"
    UPDATING = "updating"
    ERROR = "error"


class UpdateRequest(BaseModel):
    """Request to update services or drivers."""
    update_id: str
    update_type: UpdateType
    package_name: str
    package_version: str
    package_url: str
    target_nodes: List[str]
    description: Optional[str] = None


class NodeInfo(BaseModel):
    """Information about a regular node."""
    node_id: str
    hostname: str
    ip_address: str
    status: NodeStatus
    last_seen: datetime
    services: List[str] = []
    drivers: List[str] = []
    system_info: dict = {}


class UpdateJob(BaseModel):
    """An update job being processed."""
    job_id: str
    update_request: UpdateRequest
    status: UpdateStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    node_statuses: dict = {}  # node_id -> status
    error_message: Optional[str] = None


class NodeUpdateStatus(BaseModel):
    """Status of an update on a specific node."""
    node_id: str
    job_id: str
    status: UpdateStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    health_check_passed: bool = False


class HealthCheckResult(BaseModel):
    """Result of a health check on a node."""
    node_id: str
    timestamp: datetime
    services_status: dict  # service_name -> status
    system_health: dict  # CPU, memory, disk usage
    overall_healthy: bool
