"""Database operations for CoAP Main Server."""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from models import NodeInfo, UpdateJob, NodeUpdateStatus, HealthCheckResult, UpdateStatus, NodeStatus


class Database:
    """SQLite database operations for the main server."""
    
    def __init__(self, db_path: str = "/opt/management-system/database.db"):
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create nodes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_seen TIMESTAMP NOT NULL,
                    services TEXT,
                    drivers TEXT,
                    system_info TEXT
                )
            ''')
            
            # Create update_jobs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS update_jobs (
                    job_id TEXT PRIMARY KEY,
                    update_request TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    node_statuses TEXT,
                    error_message TEXT
                )
            ''')
            
            # Create node_update_statuses table
            cursor.execute('''
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
            ''')
            
            # Create health_checks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    overall_healthy BOOLEAN NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    temperature REAL,
                    services_status TEXT,
                    error_messages TEXT,
                    FOREIGN KEY (node_id) REFERENCES nodes (node_id)
                )
            ''')
            
            conn.commit()
    
    def register_node(self, node_info: NodeInfo) -> bool:
        """Register a new node."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO nodes 
                    (node_id, hostname, ip_address, status, last_seen, services, drivers, system_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
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
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT node_id, hostname, ip_address, status, last_seen, services, drivers, system_info
                    FROM nodes WHERE node_id = ?
                ''', (node_id,))
                
                row = cursor.fetchone()
                if row:
                    return NodeInfo(
                        node_id=row[0],
                        hostname=row[1],
                        ip_address=row[2],
                        status=NodeStatus(row[3]),
                        last_seen=datetime.fromisoformat(row[4]),
                        services=json.loads(row[5]) if row[5] else [],
                        drivers=json.loads(row[6]) if row[6] else [],
                        system_info=json.loads(row[7]) if row[7] else {}
                    )
                return None
        except Exception as e:
            print(f"Error getting node: {e}")
            return None
    
    def get_all_nodes(self) -> List[NodeInfo]:
        """Get all registered nodes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT node_id, hostname, ip_address, status, last_seen, services, drivers, system_info
                    FROM nodes ORDER BY last_seen DESC
                ''')
                
                nodes = []
                for row in cursor.fetchall():
                    nodes.append(NodeInfo(
                        node_id=row[0],
                        hostname=row[1],
                        ip_address=row[2],
                        status=NodeStatus(row[3]),
                        last_seen=datetime.fromisoformat(row[4]),
                        services=json.loads(row[5]) if row[5] else [],
                        drivers=json.loads(row[6]) if row[6] else [],
                        system_info=json.loads(row[7]) if row[7] else {}
                    ))
                return nodes
        except Exception as e:
            print(f"Error getting all nodes: {e}")
            return []
    
    def update_node_status(self, node_id: str, status: NodeStatus) -> bool:
        """Update node status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE nodes SET status = ?, last_seen = ? WHERE node_id = ?
                ''', (status.value, datetime.now(), node_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating node status: {e}")
            return False
    
    def create_update_job(self, job: UpdateJob) -> bool:
        """Create a new update job."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO update_jobs 
                    (job_id, update_request, status, created_at, started_at, completed_at, node_statuses, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job.job_id,
                    json.dumps({
                        'target_nodes': job.update_request.target_nodes,
                        'update_type': job.update_request.update_type.value,
                        'package_name': job.update_request.package_name,
                        'package_version': job.update_request.package_version,
                        'package_size': job.update_request.package_size,
                        'checksum': job.update_request.checksum,
                        'description': job.update_request.description
                    }),
                    job.status.value,
                    job.created_at,
                    job.started_at,
                    job.completed_at,
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
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT job_id, update_request, status, created_at, started_at, completed_at, node_statuses, error_message
                    FROM update_jobs WHERE job_id = ?
                ''', (job_id,))
                
                row = cursor.fetchone()
                if row:
                    update_request_data = json.loads(row[1])
                    return UpdateJob(
                        job_id=row[0],
                        update_request=update_request_data,
                        status=UpdateStatus(row[2]),
                        created_at=datetime.fromisoformat(row[3]),
                        started_at=datetime.fromisoformat(row[4]) if row[4] else None,
                        completed_at=datetime.fromisoformat(row[5]) if row[5] else None,
                        node_statuses=json.loads(row[6]) if row[6] else {},
                        error_message=row[7]
                    )
                return None
        except Exception as e:
            print(f"Error getting update job: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: UpdateStatus, error_message: str = None) -> bool:
        """Update job status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE update_jobs SET status = ?, error_message = ? WHERE job_id = ?
                ''', (status.value, error_message, job_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating job status: {e}")
            return False
    
    def create_node_update_status(self, node_status: NodeUpdateStatus) -> bool:
        """Create node update status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO node_update_statuses 
                    (node_id, job_id, status, started_at, completed_at, error_message, health_check_passed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_status.node_id,
                    node_status.job_id,
                    node_status.status.value,
                    node_status.started_at,
                    node_status.completed_at,
                    node_status.error_message,
                    node_status.health_check_passed
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE node_update_statuses 
                    SET status = ?, error_message = ?, health_check_passed = ?, completed_at = ?
                    WHERE node_id = ? AND job_id = ?
                ''', (status.value, error_message, health_check_passed, datetime.now(), node_id, job_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating node update status: {e}")
            return False
    
    def save_health_check(self, health_check: HealthCheckResult) -> bool:
        """Save health check result."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO health_checks 
                    (node_id, timestamp, overall_healthy, cpu_percent, memory_percent, disk_percent, 
                     temperature, services_status, error_messages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    health_check.node_id,
                    health_check.timestamp,
                    health_check.overall_healthy,
                    health_check.cpu_percent,
                    health_check.memory_percent,
                    health_check.disk_percent,
                    health_check.temperature,
                    json.dumps(health_check.services_status),
                    json.dumps(health_check.error_messages)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving health check: {e}")
            return False
    
    def get_latest_health_check(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get latest health check for a node."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT node_id, timestamp, overall_healthy, cpu_percent, memory_percent, 
                           disk_percent, temperature, services_status, error_messages
                    FROM health_checks 
                    WHERE node_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (node_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'node_id': row[0],
                        'timestamp': row[1],
                        'overall_healthy': bool(row[2]),
                        'cpu_percent': row[3],
                        'memory_percent': row[4],
                        'disk_percent': row[5],
                        'temperature': row[6],
                        'services_status': json.loads(row[7]) if row[7] else {},
                        'error_messages': json.loads(row[8]) if row[8] else []
                    }
                return None
        except Exception as e:
            print(f"Error getting latest health check: {e}")
            return None
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all nodes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT n.node_id, n.hostname, n.status, h.overall_healthy, h.timestamp
                    FROM nodes n
                    LEFT JOIN health_checks h ON n.node_id = h.node_id
                    WHERE h.timestamp = (
                        SELECT MAX(timestamp) FROM health_checks h2 
                        WHERE h2.node_id = n.node_id
                    )
                ''')
                
                summary = {
                    'total_nodes': 0,
                    'online_nodes': 0,
                    'healthy_nodes': 0,
                    'nodes': []
                }
                
                for row in cursor.fetchall():
                    summary['total_nodes'] += 1
                    if row[2] == 'online':
                        summary['online_nodes'] += 1
                    if row[3]:
                        summary['healthy_nodes'] += 1
                    
                    summary['nodes'].append({
                        'node_id': row[0],
                        'hostname': row[1],
                        'status': row[2],
                        'healthy': bool(row[3]),
                        'last_health_check': row[4]
                    })
                
                return summary
        except Exception as e:
            print(f"Error getting health summary: {e}")
            return {'total_nodes': 0, 'online_nodes': 0, 'healthy_nodes': 0, 'nodes': []}
