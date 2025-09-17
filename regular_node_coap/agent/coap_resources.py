"""CoAP resource handlers for the Regular Node Agent."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any
from aiocoap import resource, Message, Code
# Response codes are available directly from aiocoap.numbers

logger = logging.getLogger(__name__)


class NodeUpdateResource(resource.Resource):
    """CoAP resource for handling update operations on the node."""
    
    def __init__(self, update_handler):
        super().__init__()
        self.update_handler = update_handler
    
    async def render_post(self, request):
        """Handle POST requests for updates."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 2 and path[0] == "updates":  # /updates/{action}
                action = path[1]
                
                if action == "available":
                    # Handle update available notification
                    data = json.loads(request.payload.decode('utf-8'))
                    result = await self.update_handler.handle_update_available(data)
                    
                    response_data = {
                        "status": "acknowledged",
                        "message": "Update notification received",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    payload = json.dumps(response_data).encode('utf-8')
                    return Message(code=Code.CHANGED, payload=payload)
                
                elif action == "start":
                    # Handle update start command
                    data = json.loads(request.payload.decode('utf-8'))
                    result = await self.update_handler.start_update(data)
                    
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
    
    async def render_get(self, request):
        """Handle GET requests for updates."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 2 and path[0] == "updates":  # /updates/{update_id}
                update_id = path[1]
                status = await self.update_handler.get_update_status(update_id)
                
                payload = json.dumps(status).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in GET /updates: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))


class HealthResource(resource.Resource):
    """CoAP resource for handling health operations on the node."""
    
    def __init__(self, health_checker):
        super().__init__()
        self.health_checker = health_checker
    
    async def render_get(self, request):
        """Handle GET requests for health."""
        try:
            # Perform health check
            health_result = await self.health_checker.perform_health_check()
            
            payload = json.dumps(health_result).encode('utf-8')
            return Message(code=Code.CONTENT, payload=payload)
            
        except Exception as e:
            logger.error(f"Error in GET /health: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_put(self, request):
        """Handle PUT requests for health updates."""
        try:
            # Update health status
            data = json.loads(request.payload.decode('utf-8'))
            result = await self.health_checker.update_health_status(data)
            
            if result["success"]:
                payload = json.dumps(result).encode('utf-8')
                return Message(code=Code.CHANGED, payload=payload)
            else:
                payload = json.dumps(result).encode('utf-8')
                return Message(code=Code.BAD_REQUEST, payload=payload)
                
        except Exception as e:
            logger.error(f"Error in PUT /health: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))


class SystemResource(resource.Resource):
    """CoAP resource for handling system operations on the node."""
    
    def __init__(self):
        super().__init__()
    
    async def render_post(self, request):
        """Handle POST requests for system operations."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 2 and path[0] == "system":  # /system/{action}
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
