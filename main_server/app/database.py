"""Database operations for the Main Server."""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import (
    UpdateJob, NodeInfo, NodeUpdateStatus, HealthCheckResult,
    UpdateStatus, NodeStatus
)


class Database:
    """SQLite database operations."""
    
    def __init__(self, db_path: str = "main_server.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    services TEXT DEFAULT '[]',
                    drivers TEXT DEFAULT '[]',
                    system_info TEXT DEFAULT '{}'
                )
            """)
            
            # Create update_jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS update_jobs (
                    job_id TEXT PRIMARY KEY,
                    update_request TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    node_statuses TEXT DEFAULT '{}',
                    error_message TEXT
                )
            """)
            
            # Create node_update_statuses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS node_update_statuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    health_check_passed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (node_id) REFERENCES nodes (node_id),
                    FOREIGN KEY (job_id) REFERENCES update_jobs (job_id)
                )
            """)
            
            # Create health_checks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    services_status TEXT NOT NULL,
                    system_health TEXT NOT NULL,
                    overall_healthy BOOLEAN NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes (node_id)
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # Node operations
    def register_node(self, node_info: NodeInfo) -> bool:
        """Register a new node or update existing node info."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO nodes 
                    (node_id, hostname, ip_address, status, last_seen, services, drivers, system_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node_info.node_id,
                    node_info.hostname,
                    node_info.ip_address,
                    node_info.status.value,
                    node_info.last_seen,
                    json.dumps(node_info.services),
                    json.dumps(node_info.drivers),
                    json.dumps(node_info.system_info)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error registering node: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[NodeInfo]:
        """Get node information by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            
            if row:
                return NodeInfo(
                    node_id=row['node_id'],
                    hostname=row['hostname'],
                    ip_address=row['ip_address'],
                    status=NodeStatus(row['status']),
                    last_seen=datetime.fromisoformat(row['last_seen']),
                    services=json.loads(row['services']),
                    drivers=json.loads(row['drivers']),
                    system_info=json.loads(row['system_info'])
                )
            return None
    
    def get_all_nodes(self) -> List[NodeInfo]:
        """Get all registered nodes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes ORDER BY hostname")
            rows = cursor.fetchall()
            
            nodes = []
            for row in rows:
                nodes.append(NodeInfo(
                    node_id=row['node_id'],
                    hostname=row['hostname'],
                    ip_address=row['ip_address'],
                    status=NodeStatus(row['status']),
                    last_seen=datetime.fromisoformat(row['last_seen']),
                    services=json.loads(row['services']),
                    drivers=json.loads(row['drivers']),
                    system_info=json.loads(row['system_info'])
                ))
            return nodes
    
    def update_node_status(self, node_id: str, status: NodeStatus) -> bool:
        """Update node status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE nodes SET status = ?, last_seen = ? WHERE node_id = ?",
                    (status.value, datetime.now().isoformat(), node_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating node status: {e}")
            return False
    
    # Update job operations
    def create_update_job(self, job: UpdateJob) -> bool:
        """Create a new update job."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO update_jobs 
                    (job_id, update_request, status, created_at, started_at, completed_at, node_statuses, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id,
                    job.update_request.json(),
                    job.status.value,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    json.dumps(job.node_statuses),
                    job.error_message
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating update job: {e}")
            return False
    
    def get_update_job(self, job_id: str) -> Optional[UpdateJob]:
        """Get update job by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM update_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                from .models import UpdateRequest
                return UpdateJob(
                    job_id=row['job_id'],
                    update_request=UpdateRequest.parse_raw(row['update_request']),
                    status=UpdateStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    node_statuses=json.loads(row['node_statuses']),
                    error_message=row['error_message']
                )
            return None
    
    def update_job_status(self, job_id: str, status: UpdateStatus, error_message: str = None) -> bool:
        """Update job status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE update_jobs 
                    SET status = ?, error_message = ?, completed_at = ?
                    WHERE job_id = ?
                """, (
                    status.value,
                    error_message,
                    datetime.now().isoformat() if status in [UpdateStatus.SUCCESS, UpdateStatus.FAILED, UpdateStatus.ROLLED_BACK] else None,
                    job_id
                ))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating job status: {e}")
            return False
    
    # Node update status operations
    def create_node_update_status(self, status: NodeUpdateStatus) -> bool:
        """Create node update status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO node_update_statuses 
                    (node_id, job_id, status, started_at, completed_at, error_message, health_check_passed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    status.node_id,
                    status.job_id,
                    status.status.value,
                    status.started_at.isoformat(),
                    status.completed_at.isoformat() if status.completed_at else None,
                    status.error_message,
                    status.health_check_passed
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating node update status: {e}")
            return False
    
    def update_node_update_status(self, node_id: str, job_id: str, status: UpdateStatus, 
                                error_message: str = None, health_check_passed: bool = False) -> bool:
        """Update node update status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE node_update_statuses 
                    SET status = ?, completed_at = ?, error_message = ?, health_check_passed = ?
                    WHERE node_id = ? AND job_id = ?
                """, (
                    status.value,
                    datetime.now().isoformat(),
                    error_message,
                    health_check_passed,
                    node_id,
                    job_id
                ))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating node update status: {e}")
            return False
    
    # Health check operations
    def save_health_check(self, health_check: HealthCheckResult) -> bool:
        """Save health check result."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO health_checks 
                    (node_id, timestamp, services_status, system_health, overall_healthy)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    health_check.node_id,
                    health_check.timestamp.isoformat(),
                    json.dumps(health_check.services_status),
                    json.dumps(health_check.system_health),
                    health_check.overall_healthy
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving health check: {e}")
            return False
