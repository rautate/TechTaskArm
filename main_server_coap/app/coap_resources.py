"""CoAP resource handlers for the Main Server."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from aiocoap import resource, Message, Code
# Response codes are available directly from aiocoap.numbers

logger = logging.getLogger(__name__)


class UpdateResource(resource.Resource):
    """CoAP resource for handling update operations."""
    
    def __init__(self, update_manager):
        super().__init__()
        self.update_manager = update_manager
        self.observers = {}  # Track observers for each update
    
    async def render_get(self, request):
        """Handle GET requests for updates."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 1:  # /updates
                # List all updates
                updates = self.update_manager.get_all_updates()
                payload = json.dumps({"updates": updates}).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            elif len(path) == 2:  # /updates/{update_id}
                update_id = path[1]
                update_info = self.update_manager.get_update_info(update_id)
                
                if update_info:
                    payload = json.dumps(update_info).encode('utf-8')
                    return Message(code=Code.CONTENT, payload=payload)
                else:
                    return Message(code=Code.NOT_FOUND, payload=b"Update not found")
            
            elif len(path) == 3:  # /updates/{update_id}/status
                update_id = path[1]
                action = path[2]
                
                if action == "status":
                    status = self.update_manager.get_update_status(update_id)
                    payload = json.dumps(status).encode('utf-8')
                    return Message(code=Code.CONTENT, payload=payload)
                elif action == "download":
                    # Handle firmware download with block-wise transfer
                    return await self._handle_download(request, update_id)
                else:
                    return Message(code=Code.BAD_REQUEST, payload=b"Invalid action")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in GET /updates: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_post(self, request):
        """Handle POST requests for updates."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 1:  # /updates
                # Create new update
                data = json.loads(request.payload.decode('utf-8'))
                update_request = self._parse_update_request(data)
                
                job_id = await self.update_manager.create_update(update_request)
                
                response_data = {
                    "job_id": job_id,
                    "status": "created",
                    "message": "Update request created successfully"
                }
                
                payload = json.dumps(response_data).encode('utf-8')
                return Message(code=Code.CREATED, payload=payload)
            
            elif len(path) == 3:  # /updates/{update_id}/install
                update_id = path[1]
                action = path[2]
                
                if action == "install":
                    # Trigger update installation
                    result = await self.update_manager.trigger_update(update_id)
                    
                    if result["success"]:
                        payload = json.dumps(result).encode('utf-8')
                        return Message(code=Code.CHANGED, payload=payload)
                    else:
                        payload = json.dumps(result).encode('utf-8')
                        return Message(code=Code.BAD_REQUEST, payload=payload)
                else:
                    return Message(code=Code.BAD_REQUEST, payload=b"Invalid action")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in POST /updates: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def _handle_download(self, request, update_id: str):
        """Handle firmware download with block-wise transfer."""
        try:
            # Get firmware file path
            firmware_path = self.update_manager.get_firmware_path(update_id)
            
            if not firmware_path or not os.path.exists(firmware_path):
                return Message(code=Code.NOT_FOUND, payload=b"Firmware not found")
            
            # Check for block-wise transfer
            block1 = request.opt.block1
            if block1:
                # Handle block-wise transfer
                return await self._handle_block_transfer(firmware_path, block1)
            else:
                # Send entire file (for small files)
                with open(firmware_path, 'rb') as f:
                    data = f.read()
                
                return Message(
                    code=Code.CONTENT,
                    payload=data,
                    opt=request.opt
                )
                
        except Exception as e:
            logger.error(f"Error handling download: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def _handle_block_transfer(self, file_path: str, block1):
        """Handle CoAP block-wise transfer."""
        try:
            block_size = 2 ** (4 + block1.szx)
            block_num = block1.num
            more = block1.m
            
            with open(file_path, 'rb') as f:
                f.seek(block_num * block_size)
                data = f.read(block_size)
            
            # Check if this is the last block
            file_size = os.path.getsize(file_path)
            is_last_block = (block_num + 1) * block_size >= file_size
            
            # Create response with block1 option
            response = Message(
                code=Code.CONTENT,
                payload=data
            )
            
            # Add block1 option
            from aiocoap.optiontypes import Block1
            response.opt.block1 = Block1(
                num=block_num,
                m=not is_last_block,
                szx=block1.szx
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in block transfer: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    def _parse_update_request(self, data: Dict[str, Any]):
        """Parse update request from JSON data."""
        # This would create an UpdateRequest object
        # For now, return the data as-is
        return data


class NodeResource(resource.Resource):
    """CoAP resource for handling node operations."""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.observers = {}  # Track observers for each node
    
    async def render_get(self, request):
        """Handle GET requests for nodes."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 1:  # /nodes
                # List all nodes
                nodes = self.db.get_all_nodes()
                nodes_data = [node.dict() for node in nodes]
                payload = json.dumps({"nodes": nodes_data}).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            elif len(path) == 2:  # /nodes/{node_id}
                node_id = path[1]
                node = self.db.get_node(node_id)
                
                if node:
                    payload = json.dumps(node.dict()).encode('utf-8')
                    return Message(code=Code.CONTENT, payload=payload)
                else:
                    return Message(code=Code.NOT_FOUND, payload=b"Node not found")
            
            elif len(path) == 3:  # /nodes/{node_id}/health
                node_id = path[1]
                action = path[2]
                
                if action == "health":
                    # Get node health status
                    health_data = self.db.get_latest_health_check(node_id)
                    if health_data:
                        payload = json.dumps(health_data).encode('utf-8')
                        return Message(code=Code.CONTENT, payload=payload)
                    else:
                        return Message(code=Code.NOT_FOUND, payload=b"Health data not found")
                else:
                    return Message(code=Code.BAD_REQUEST, payload=b"Invalid action")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in GET /nodes: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_post(self, request):
        """Handle POST requests for nodes."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 1:  # /nodes
                # Register new node
                data = json.loads(request.payload.decode('utf-8'))
                node_info = self._parse_node_info(data)
                
                success = self.db.register_node(node_info)
                
                if success:
                    response_data = {
                        "message": "Node registered successfully",
                        "node_id": node_info.node_id
                    }
                    payload = json.dumps(response_data).encode('utf-8')
                    return Message(code=Code.CREATED, payload=payload)
                else:
                    return Message(code=Code.INTERNAL_SERVER_ERROR, payload=b"Failed to register node")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in POST /nodes: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_put(self, request):
        """Handle PUT requests for nodes."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 3:  # /nodes/{node_id}/health
                node_id = path[1]
                action = path[2]
                
                if action == "health":
                    # Update node health status
                    data = json.loads(request.payload.decode('utf-8'))
                    success = self.db.save_health_check(data)
                    
                    if success:
                        # Notify observers
                        await self._notify_observers(f"nodes/{node_id}/health", data)
                        return Message(code=Code.CHANGED, payload=b"Health status updated")
                    else:
                        return Message(code=Code.INTERNAL_SERVER_ERROR, payload=b"Failed to update health status")
                else:
                    return Message(code=Code.BAD_REQUEST, payload=b"Invalid action")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in PUT /nodes: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    def _parse_node_info(self, data: Dict[str, Any]):
        """Parse node info from JSON data."""
        # This would create a NodeInfo object
        # For now, return the data as-is
        return data
    
    async def _notify_observers(self, topic: str, data: Dict[str, Any]):
        """Notify observers of changes."""
        if topic in self.observers:
            for observer in self.observers[topic]:
                try:
                    await observer(topic, data)
                except Exception as e:
                    logger.error(f"Error notifying observer: {e}")


class HealthResource(resource.Resource):
    """CoAP resource for handling health operations."""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
    
    async def render_get(self, request):
        """Handle GET requests for health."""
        try:
            # Get overall system health
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "nodes": self.db.get_health_summary()
            }
            
            payload = json.dumps(health_data).encode('utf-8')
            return Message(code=Code.CONTENT, payload=payload)
            
        except Exception as e:
            logger.error(f"Error in GET /health: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))


class SystemResource(resource.Resource):
    """CoAP resource for handling system operations."""
    
    def __init__(self):
        super().__init__()
    
    async def render_post(self, request):
        """Handle POST requests for system operations."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 2:  # /system/{action}
                action = path[1]
                
                if action == "restart":
                    # Restart system
                    response_data = {
                        "message": "System restart initiated",
                        "timestamp": datetime.now().isoformat()
                    }
                    payload = json.dumps(response_data).encode('utf-8')
                    return Message(code=Code.CHANGED, payload=payload)
                
                elif action == "shutdown":
                    # Shutdown system
                    response_data = {
                        "message": "System shutdown initiated",
                        "timestamp": datetime.now().isoformat()
                    }
                    payload = json.dumps(response_data).encode('utf-8')
                    return Message(code=Code.CHANGED, payload=payload)
                
                else:
                    return Message(code=Code.BAD_REQUEST, payload=b"Invalid action")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in POST /system: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))


# Import os for file operations
import os
