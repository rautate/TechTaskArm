"""Update management logic for the Main Server."""

import asyncio
import aiohttp
import uuid
from datetime import datetime
from typing import List, Dict, Any
import logging

from .models import UpdateRequest, UpdateJob, NodeInfo, NodeUpdateStatus, UpdateStatus, NodeStatus
from .database import Database

logger = logging.getLogger(__name__)


class UpdateManager:
    """Manages update operations across regular nodes."""
    
    def __init__(self, db: Database):
        self.db = db
        self.active_jobs: Dict[str, UpdateJob] = {}
    
    async def process_update_request(self, update_request: UpdateRequest) -> str:
        """Process an update request and return job ID."""
        job_id = str(uuid.uuid4())
        
        # Create update job
        job = UpdateJob(
            job_id=job_id,
            update_request=update_request,
            status=UpdateStatus.PENDING,
            created_at=datetime.now()
        )
        
        # Save to database
        if not self.db.create_update_job(job):
            raise Exception("Failed to create update job")
        
        # Start processing asynchronously
        asyncio.create_task(self._execute_update_job(job))
        
        return job_id
    
    async def _execute_update_job(self, job: UpdateJob):
        """Execute an update job across all target nodes."""
        try:
            # Update job status to in progress
            job.status = UpdateStatus.IN_PROGRESS
            job.started_at = datetime.now()
            self.db.update_job_status(job.job_id, job.status)
            
            logger.info(f"Starting update job {job.job_id} for {len(job.update_request.target_nodes)} nodes")
            
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
            
            # Send update commands to all nodes concurrently
            tasks = []
            for node in nodes:
                task = asyncio.create_task(
                    self._send_update_to_node(node, job)
                )
                tasks.append(task)
            
            # Wait for all updates to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            success_count = 0
            failed_count = 0
            
            for i, result in enumerate(results):
                node = nodes[i]
                if isinstance(result, Exception):
                    logger.error(f"Update failed on node {node.node_id}: {result}")
                    failed_count += 1
                    job.node_statuses[node.node_id] = UpdateStatus.FAILED.value
                else:
                    if result.get('success', False):
                        success_count += 1
                        job.node_statuses[node.node_id] = UpdateStatus.SUCCESS.value
                    else:
                        failed_count += 1
                        job.node_statuses[node.node_id] = UpdateStatus.FAILED.value
            
            # Update job status
            if failed_count == 0:
                job.status = UpdateStatus.SUCCESS
                logger.info(f"Update job {job.job_id} completed successfully")
            elif success_count > 0:
                job.status = UpdateStatus.FAILED
                logger.warning(f"Update job {job.job_id} partially failed: {success_count} success, {failed_count} failed")
                # Trigger rollback for failed nodes
                await self._rollback_failed_nodes(job)
            else:
                job.status = UpdateStatus.FAILED
                logger.error(f"Update job {job.job_id} failed completely")
                # Trigger rollback for all nodes
                await self._rollback_failed_nodes(job)
            
            job.completed_at = datetime.now()
            self.db.update_job_status(job.job_id, job.status)
            
        except Exception as e:
            logger.error(f"Update job {job.job_id} failed: {e}")
            job.status = UpdateStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            self.db.update_job_status(job.job_id, job.status, str(e))
    
    async def _send_update_to_node(self, node: NodeInfo, job: UpdateJob) -> Dict[str, Any]:
        """Send update command to a specific node."""
        try:
            # Create node update status
            node_status = NodeUpdateStatus(
                node_id=node.node_id,
                job_id=job.job_id,
                status=UpdateStatus.IN_PROGRESS,
                started_at=datetime.now()
            )
            self.db.create_node_update_status(node_status)
            
            # Send HTTP request to node agent
            update_payload = {
                "job_id": job.job_id,
                "update_type": job.update_request.update_type.value,
                "package_name": job.update_request.package_name,
                "package_version": job.update_request.package_version,
                "package_url": job.update_request.package_url,
                "description": job.update_request.description
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"http://{node.ip_address}:8081/agent/update"
                async with session.post(url, json=update_payload, timeout=300) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Update node status
                        if result.get('success', False):
                            self.db.update_node_update_status(
                                node.node_id, job.job_id, UpdateStatus.SUCCESS,
                                health_check_passed=result.get('health_check_passed', False)
                            )
                        else:
                            self.db.update_node_update_status(
                                node.node_id, job.job_id, UpdateStatus.FAILED,
                                error_message=result.get('error_message', 'Unknown error')
                            )
                        
                        return result
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        self.db.update_node_update_status(
                            node.node_id, job.job_id, UpdateStatus.FAILED,
                            error_message=error_msg
                        )
                        return {"success": False, "error_message": error_msg}
        
        except asyncio.TimeoutError:
            error_msg = "Update timeout on node"
            self.db.update_node_update_status(
                node.node_id, job.job_id, UpdateStatus.FAILED,
                error_message=error_msg
            )
            return {"success": False, "error_message": error_msg}
        
        except Exception as e:
            error_msg = f"Error sending update to node: {e}"
            self.db.update_node_update_status(
                node.node_id, job.job_id, UpdateStatus.FAILED,
                error_message=error_msg
            )
            return {"success": False, "error_message": error_msg}
    
    async def _rollback_failed_nodes(self, job: UpdateJob):
        """Rollback updates on failed nodes."""
        logger.info(f"Starting rollback for job {job.job_id}")
        
        # Find failed nodes
        failed_nodes = [
            node_id for node_id, status in job.node_statuses.items()
            if status == UpdateStatus.FAILED.value
        ]
        
        if not failed_nodes:
            return
        
        # Send rollback commands
        tasks = []
        for node_id in failed_nodes:
            node = self.db.get_node(node_id)
            if node:
                task = asyncio.create_task(self._send_rollback_to_node(node, job.job_id))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Rollback completed for job {job.job_id}")
    
    async def _send_rollback_to_node(self, node: NodeInfo, job_id: str):
        """Send rollback command to a specific node."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{node.ip_address}:8081/agent/rollback"
                payload = {"job_id": job_id}
                
                async with session.post(url, json=payload, timeout=60) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success', False):
                            logger.info(f"Rollback successful on node {node.node_id}")
                        else:
                            logger.error(f"Rollback failed on node {node.node_id}: {result.get('error_message')}")
                    else:
                        logger.error(f"Rollback HTTP error on node {node.node_id}: {response.status}")
        
        except Exception as e:
            logger.error(f"Error sending rollback to node {node.node_id}: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of an update job."""
        job = self.db.get_update_job(job_id)
        if not job:
            return {"error": "Job not found"}
        
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "node_statuses": job.node_statuses,
            "error_message": job.error_message
        }
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all update jobs."""
        # This would need to be implemented in the database class
        # For now, return active jobs
        return [self.get_job_status(job_id) for job_id in self.active_jobs.keys()]
