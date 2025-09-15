"""CoAP-based update management for the Main Server."""

import asyncio
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

from models import UpdateRequest, UpdateJob, NodeInfo, NodeUpdateStatus, UpdateStatus, NodeStatus
from database import Database

logger = logging.getLogger(__name__)


class CoAPUpdateManager:
    """Manages update operations across regular nodes using CoAP."""
    
    def __init__(self, db: Database):
        self.db = db
        self.active_jobs: Dict[str, UpdateJob] = {}
        self.observers = {}  # Track observers for each update
    
    async def create_update(self, update_request: Dict[str, Any]) -> str:
        """Create a new update request and return job ID."""
        try:
            job_id = str(uuid.uuid4())
            
            # Parse update request
            parsed_request = self._parse_update_request(update_request)
            
            # Create update job
            job = UpdateJob(
                job_id=job_id,
                update_request=parsed_request,
                status=UpdateStatus.PENDING,
                created_at=datetime.now()
            )
            
            # Save to database
            if not self.db.create_update_job(job):
                raise Exception("Failed to create update job")
            
            # Store in active jobs
            self.active_jobs[job_id] = job
            
            logger.info(f"Created update job {job_id} for {len(parsed_request.target_nodes)} nodes")
            
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating update: {e}")
            raise
    
    async def trigger_update(self, job_id: str) -> Dict[str, Any]:
        """Trigger update execution for a job."""
        try:
            if job_id not in self.active_jobs:
                return {"success": False, "error": "Job not found"}
            
            job = self.active_jobs[job_id]
            
            # Update job status to in progress
            job.status = UpdateStatus.IN_PROGRESS
            job.started_at = datetime.now()
            self.db.update_job_status(job.job_id, job.status)
            
            # Start processing asynchronously
            asyncio.create_task(self._execute_update_job(job))
            
            return {
                "success": True,
                "message": f"Update job {job_id} triggered successfully",
                "job_id": job_id
            }
            
        except Exception as e:
            logger.error(f"Error triggering update: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_update_job(self, job: UpdateJob):
        """Execute an update job across all target nodes using CoAP."""
        try:
            logger.info(f"Starting CoAP update job {job.job_id} for {len(job.update_request.target_nodes)} nodes")
            
            # Get node information
            nodes = []
            for node_id in job.update_request.target_nodes:
                node = self.db.get_node(node_id)
                if node and node.status == NodeStatus.ONLINE:
                    nodes.append(node)
                else:
                    logger.warning(f"Node {node_id} is not available")
            
            if not nodes:
                raise Exception("No online nodes available for update")
            
            # Send update notifications via CoAP
            for node in nodes:
                await self._send_update_notification(node, job)
            
            logger.info(f"Update notifications sent to {len(nodes)} nodes via CoAP")
            
        except Exception as e:
            logger.error(f"Update job {job.job_id} failed: {e}")
            job.status = UpdateStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            self.db.update_job_status(job.job_id, job.status, str(e))
    
    async def _send_update_notification(self, node: NodeInfo, job: UpdateJob):
        """Send update notification to a specific node via CoAP."""
        try:
            # Create node update status
            node_status = NodeUpdateStatus(
                node_id=node.node_id,
                job_id=job.job_id,
                status=UpdateStatus.PENDING,
                started_at=datetime.now()
            )
            self.db.create_node_update_status(node_status)
            
            # Prepare update information
            update_info = {
                "update_id": job.job_id,
                "version": job.update_request.package_version,
                "size": job.update_request.package_size or 0,
                "download_url": f"coap://{node.ip_address}:5683/updates/{job.job_id}/download",
                "checksum": job.update_request.checksum,
                "timestamp": datetime.now().isoformat(),
                "update_type": job.update_request.update_type.value,
                "package_name": job.update_request.package_name,
                "description": job.update_request.description
            }
            
            # Send CoAP notification
            success = await self._send_coap_message(
                node.ip_address, 5683,
                f"updates/{node.node_id}/available",
                update_info
            )
            
            if success:
                logger.info(f"Update notification sent to node {node.node_id} via CoAP")
            else:
                logger.error(f"Failed to send update notification to node {node.node_id}")
                # Mark as failed
                self.db.update_node_update_status(
                    node.node_id, job.job_id, UpdateStatus.FAILED,
                    error_message="Failed to send CoAP notification"
                )
            
        except Exception as e:
            logger.error(f"Error sending update notification to node {node.node_id}: {e}")
            self.db.update_node_update_status(
                node.node_id, job.job_id, UpdateStatus.FAILED,
                error_message=str(e)
            )
    
    async def _send_coap_message(self, host: str, port: int, path: str, data: Dict[str, Any]) -> bool:
        """Send a CoAP message to a node."""
        try:
            from aiocoap import Context, Message, Code
            import json
            
            # Create CoAP context
            context = await Context.create_client_context()
            
            # Prepare message
            payload = json.dumps(data).encode('utf-8')
            request = Message(
                code=Code.POST,
                uri=f"coap://{host}:{port}/{path}",
                payload=payload
            )
            
            # Send request
            response = await context.request(request).response
            
            if response.code.is_successful():
                logger.debug(f"CoAP message sent successfully to {host}:{port}/{path}")
                return True
            else:
                logger.error(f"CoAP message failed: {response.code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending CoAP message: {e}")
            return False
    
    def get_update_info(self, update_id: str) -> Dict[str, Any]:
        """Get update information."""
        if update_id in self.active_jobs:
            job = self.active_jobs[update_id]
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "target_nodes": job.update_request.target_nodes,
                "package_name": job.update_request.package_name,
                "package_version": job.update_request.package_version,
                "update_type": job.update_request.update_type.value,
                "description": job.update_request.description
            }
        else:
            return None
    
    def get_update_status(self, update_id: str) -> Dict[str, Any]:
        """Get update status."""
        if update_id in self.active_jobs:
            job = self.active_jobs[update_id]
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "node_statuses": job.node_statuses,
                "error_message": job.error_message
            }
        else:
            return {"error": "Update not found"}
    
    def get_firmware_path(self, update_id: str) -> str:
        """Get firmware file path for an update."""
        if update_id in self.active_jobs:
            job = self.active_jobs[update_id]
            firmware_dir = f"/opt/firmware/{update_id}"
            if os.path.exists(firmware_dir):
                # Find the first file in the directory
                for file in os.listdir(firmware_dir):
                    return os.path.join(firmware_dir, file)
        return None
    
    def get_all_updates(self) -> List[Dict[str, Any]]:
        """Get all update jobs."""
        return [self.get_update_info(job_id) for job_id in self.active_jobs.keys()]
    
    def _parse_update_request(self, data: Dict[str, Any]) -> UpdateRequest:
        """Parse update request from dictionary."""
        # This would create an UpdateRequest object from the data
        # For now, return a simple object
        class SimpleUpdateRequest:
            def __init__(self, data):
                self.target_nodes = data.get('target_nodes', [])
                self.package_name = data.get('package_name', '')
                self.package_version = data.get('package_version', '')
                self.package_size = data.get('package_size', 0)
                self.checksum = data.get('checksum', '')
                self.update_type = data.get('update_type', 'package')
                self.description = data.get('description', '')
        
        return SimpleUpdateRequest(data)
