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
    
    async def render(self, request):
        """Override render method to add URI parsing."""
        logger.info(f"UpdateResource.render called with method: {request.code}")
        logger.info(f"UpdateResource URI path: {request.opt.uri_path}")
        logger.info(f"UpdateResource _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
        
        # Try to parse URI if path is empty
        path = request.opt.uri_path
        if not path or len(path) == 0:
            # Try multiple methods to get the URI
            uri_to_parse = None
            
            # Method 1: Try _original_request_uri (this has the correct path)
            try:
                uri_to_parse = getattr(request, '_original_request_uri', None)
            except Exception as e:
                pass
            
            # Method 2: Try get_request_uri() (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = request.get_request_uri()
                except Exception as e:
                    pass
            
            # Method 3: Try requested_path (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = getattr(request, 'requested_path', None)
                except Exception as e:
                    pass
            
            # Parse the URI if we found one
            if uri_to_parse:
                from urllib.parse import urlparse
                parsed = urlparse(uri_to_parse)
                if parsed.path:
                    path_parts = [part for part in parsed.path.split('/') if part]
                    path = tuple(path_parts)
                    # Update the request's URI path
                    request.opt.uri_path = path
                    logger.info(f"UpdateResource: Parsed URI path: {path}")
                else:
                    logger.warning(f"UpdateResource: URI has no path: {uri_to_parse}")
            else:
                logger.warning("UpdateResource: No URI found in request")
        
        # Route to the appropriate method based on the request code
        if request.code == Code.GET:
            return await self.render_get(request)
        elif request.code == Code.POST:
            return await self.render_post(request)
        else:
            return Message(code=Code.METHOD_NOT_ALLOWED, payload=b"Method not allowed")
    
    async def render_get(self, request):
        """Handle GET requests for updates."""
        try:
            path = request.opt.uri_path
            logger.info(f"GET request to /updates, path: {path}, path length: {len(path)}")
            
            if len(path) == 0 or (len(path) == 1 and path[0] == "updates"):  # /updates
                # List all updates
                updates = self.update_manager.get_all_updates()
                payload = json.dumps({"updates": updates}).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            elif len(path) == 2 and path[0] == "updates":  # /updates/{update_id}
                update_id = path[1]
                update_info = self.update_manager.get_update_info(update_id)
                
                if update_info:
                    payload = json.dumps(update_info).encode('utf-8')
                    return Message(code=Code.CONTENT, payload=payload)
                else:
                    return Message(code=Code.NOT_FOUND, payload=b"Update not found")
            
            elif len(path) == 2 and path[0] == "updates":  # /updates/{update_id}
                update_id = path[1]
                # Check if this is a download request by looking at query parameters or options
                if request.opt.uri_query and "action=download" in request.opt.uri_query:
                    # Handle firmware download with block-wise transfer
                    return await self._handle_download(request, update_id)
                else:
                    # Get update info (default behavior)
                    update_info = self.update_manager.get_update_info(update_id)
                    if update_info:
                        payload = json.dumps(update_info).encode('utf-8')
                        return Message(code=Code.CONTENT, payload=payload)
                    else:
                        return Message(code=Code.NOT_FOUND, payload=b"Update not found")
            
            else:
                logger.warning(f"Invalid path structure for GET /updates: {path}")
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in GET /updates: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_post(self, request):
        """Handle POST requests for updates."""
        try:
            path = request.opt.uri_path
            
            if len(path) == 1 and path[0] == "updates":  # /updates
                logger.info(f"UpdateResource.render_post: Received payload: {request.payload}")
                logger.info(f"UpdateResource.render_post: Payload length: {len(request.payload)}")
                
                if not request.payload:
                    return Message(code=Code.BAD_REQUEST, payload=b"Empty payload")
                
                try:
                    data = json.loads(request.payload.decode('utf-8'))
                    logger.info(f"UpdateResource.render_post: Parsed JSON: {data}")
                except json.JSONDecodeError as e:
                    logger.error(f"UpdateResource.render_post: JSON decode error: {e}")
                    return Message(code=Code.BAD_REQUEST, payload=f"Invalid JSON: {str(e)}".encode('utf-8'))
                
                # Check if this is a create request or an action request
                action = data.get('action', '')
                
                if action == "install":
                    # Trigger update installation
                    job_id = data.get('job_id', '')
                    if not job_id:
                        return Message(code=Code.BAD_REQUEST, payload=b"Missing job_id for install action")
                    
                    result = await self.update_manager.trigger_update(job_id)
                    
                    if result["success"]:
                        payload = json.dumps(result).encode('utf-8')
                        return Message(code=Code.CHANGED, payload=payload)
                    else:
                        payload = json.dumps(result).encode('utf-8')
                        return Message(code=Code.BAD_REQUEST, payload=payload)
                        
                elif action == "status":
                    # Get update status
                    job_id = data.get('job_id', '')
                    if not job_id:
                        return Message(code=Code.BAD_REQUEST, payload=b"Missing job_id for status action")
                    
                    status = self.update_manager.get_update_status(job_id)
                    payload = json.dumps(status).encode('utf-8')
                    return Message(code=Code.CONTENT, payload=payload)
                    
                else:
                    # Create new update (default behavior when no action specified)
                    update_request = self._parse_update_request(data)
                    
                    job_id = await self.update_manager.create_update(update_request)
                    
                    response_data = {
                        "job_id": job_id,
                        "status": "created",
                        "message": "Update request created successfully"
                    }
                    
                    payload = json.dumps(response_data).encode('utf-8')
                    return Message(code=Code.CREATED, payload=payload)
            
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
        from models import UpdateRequest, UpdateType
        
        logger.info(f"UpdateResource._parse_update_request: Received data: {data}")
        logger.info(f"UpdateResource._parse_update_request: Type of data: {type(data)}")
        
        # Map package_type to valid UpdateType
        package_type = data.get('package_type', 'package')
        if package_type in ['pip', 'npm', 'apt', 'yum', 'docker']:
            # These are all package types
            update_type = UpdateType.PACKAGE
        elif package_type in ['service', 'systemd']:
            update_type = UpdateType.SERVICE
        elif package_type in ['driver', 'kernel']:
            update_type = UpdateType.DRIVER
        else:
            update_type = UpdateType.PACKAGE  # Default to package
        
        logger.info(f"UpdateResource._parse_update_request: update_type: {update_type}")
        
        # Create UpdateRequest object directly
        update_request = UpdateRequest(
            target_nodes=data.get('target_nodes', []),
            update_type=update_type,
            package_name=data.get('name', ''),
            package_version=data.get('version', ''),
            package_size=data.get('file_size', 0),
            checksum=data.get('checksum', ''),
            description=data.get('description', '')
        )
        
        logger.info(f"UpdateResource._parse_update_request: Created UpdateRequest: {update_request}")
        logger.info(f"UpdateResource._parse_update_request: Type of result: {type(update_request)}")
        
        return update_request


class NodeResource(resource.Resource):
    """CoAP resource for handling node operations."""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.observers = {}  # Track observers for each node
    
    async def render(self, request):
        """Override render method to add debugging and URI parsing."""
        logger.info(f"NodeResource.render called with method: {request.code}, path: {request.opt.uri_path}")
        logger.info(f"NodeResource _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
        logger.info("NodeResource is handling this request")
        
        # Try to parse URI if path is empty
        path = request.opt.uri_path
        if not path or len(path) == 0:
            # Try multiple methods to get the URI
            uri_to_parse = None
            
            # Method 1: Try _original_request_uri (this has the correct path)
            try:
                uri_to_parse = getattr(request, '_original_request_uri', None)
            except Exception as e:
                pass
            
            # Method 2: Try get_request_uri() (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = request.get_request_uri()
                except Exception as e:
                    pass
            
            # Method 3: Try requested_path (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = getattr(request, 'requested_path', None)
                except Exception as e:
                    pass
            
            # Parse the URI if we found one
            if uri_to_parse:
                from urllib.parse import urlparse
                parsed = urlparse(uri_to_parse)
                if parsed.path:
                    path_parts = [part for part in parsed.path.split('/') if part]
                    path = tuple(path_parts)
                    # Update the request's URI path
                    request.opt.uri_path = path
                    logger.info(f"Parsed URI path: {path}")
                else:
                    logger.warning(f"URI has no path: {uri_to_parse}")
            else:
                logger.warning("No URI found in request")
        
        # Route to the appropriate method based on the request code
        if request.code == Code.GET:
            return await self.render_get(request)
        elif request.code == Code.POST:
            return await self.render_post(request)
        elif request.code == Code.PUT:
            return await self.render_put(request)
        else:
            return Message(code=Code.METHOD_NOT_ALLOWED, payload=b"Method not allowed")
    
    async def render_get(self, request):
        """Handle GET requests for nodes."""
        try:
            logger.info(f"NodeResource.render_get called with method: {request.code}, path: {request.opt.uri_path}")
            
            # Try to parse URI if path is empty
            path = request.opt.uri_path
            if not path or len(path) == 0:
                # Try multiple methods to get the URI
                uri_to_parse = None
                
                # Method 1: Try _original_request_uri (this has the correct path)
                try:
                    uri_to_parse = getattr(request, '_original_request_uri', None)
                except Exception as e:
                    pass
                
                # Method 2: Try get_request_uri() (fallback)
                if not uri_to_parse:
                    try:
                        uri_to_parse = request.get_request_uri()
                    except Exception as e:
                        pass
                
                # Method 3: Try requested_path (fallback)
                if not uri_to_parse:
                    try:
                        uri_to_parse = getattr(request, 'requested_path', None)
                    except Exception as e:
                        pass
                
                # Parse the URI if we found one
                if uri_to_parse:
                    from urllib.parse import urlparse
                    parsed = urlparse(uri_to_parse)
                    if parsed.path:
                        path_parts = [part for part in parsed.path.split('/') if part]
                        path = tuple(path_parts)
                        # Update the request's URI path
                        request.opt.uri_path = path
                        logger.info(f"GET: Parsed URI path: {path}")
                    else:
                        logger.warning(f"GET: URI has no path: {uri_to_parse}")
                else:
                    logger.warning("GET: No URI found in request")
            
            path = request.opt.uri_path
            
            if len(path) == 1 and path[0] == "nodes":  # /nodes
                # List all nodes
                nodes = self.db.get_all_nodes()
                nodes_data = [node.dict() for node in nodes]
                payload = json.dumps({"nodes": nodes_data}).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            elif len(path) == 2 and path[0] == "nodes":  # /nodes/{node_id}
                node_id = path[1]
                node = self.db.get_node(node_id)
                
                if node:
                    payload = json.dumps(node.dict()).encode('utf-8')
                    return Message(code=Code.CONTENT, payload=payload)
                else:
                    return Message(code=Code.NOT_FOUND, payload=b"Node not found")
            
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in GET /nodes: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_post(self, request):
        """Handle POST requests for nodes."""
        try:
            logger.info(f"POST request to /nodes, path: {request.opt.uri_path}")
            
            # Try to parse URI if path is empty
            path = request.opt.uri_path
            if not path or len(path) == 0:
                # Try multiple methods to get the URI
                uri_to_parse = None
                
                # Method 1: Try _original_request_uri (this has the correct path)
                try:
                    uri_to_parse = getattr(request, '_original_request_uri', None)
                except Exception as e:
                    pass
                
                # Method 2: Try get_request_uri() (fallback)
                if not uri_to_parse:
                    try:
                        uri_to_parse = request.get_request_uri()
                    except Exception as e:
                        pass
                
                # Method 3: Try requested_path (fallback)
                if not uri_to_parse:
                    try:
                        uri_to_parse = getattr(request, 'requested_path', None)
                    except Exception as e:
                        pass
                
                # Parse the URI if we found one
                if uri_to_parse:
                    from urllib.parse import urlparse
                    parsed = urlparse(uri_to_parse)
                    if parsed.path:
                        path_parts = [part for part in parsed.path.split('/') if part]
                        path = tuple(path_parts)
                        # Update the request's URI path
                        request.opt.uri_path = path
                        logger.info(f"POST: Parsed URI path: {path}")
                    else:
                        logger.warning(f"POST: URI has no path: {uri_to_parse}")
                else:
                    logger.warning("POST: No URI found in request")
            
            path = request.opt.uri_path
            
            if len(path) == 1 and path[0] == "nodes":  # /nodes
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
            
            elif len(path) == 0:  # Handle empty path - might be a registration request
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
            logger.info(f"PUT request to /nodes, path: {request.opt.uri_path}")
            logger.info(f"PUT request method: {request.code}")
            logger.info(f"PUT request _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
            
            # Try to parse URI if path is empty
            path = request.opt.uri_path
            if not path or len(path) == 0:
                # Try multiple methods to get the URI
                uri_to_parse = None
                
                # Method 1: Try _original_request_uri (this has the correct path)
                try:
                    uri_to_parse = getattr(request, '_original_request_uri', None)
                except Exception as e:
                    pass
                
                # Method 2: Try get_request_uri() (fallback)
                if not uri_to_parse:
                    try:
                        uri_to_parse = request.get_request_uri()
                    except Exception as e:
                        pass
                
                # Method 3: Try requested_path (fallback)
                if not uri_to_parse:
                    try:
                        uri_to_parse = getattr(request, 'requested_path', None)
                    except Exception as e:
                        pass
                
                # Parse the URI if we found one
                if uri_to_parse:
                    from urllib.parse import urlparse
                    parsed = urlparse(uri_to_parse)
                    if parsed.path:
                        path_parts = [part for part in parsed.path.split('/') if part]
                        path = tuple(path_parts)
                        # Update the request's URI path
                        request.opt.uri_path = path
                        logger.info(f"PUT: Parsed URI path: {path}")
                    else:
                        logger.warning(f"PUT: URI has no path: {uri_to_parse}")
                else:
                    logger.warning("PUT: No URI found in request")
            
            path = request.opt.uri_path
            
            if len(path) == 0:  # Handle empty path - might be a health check request
                # Try to extract node_id from payload or use a default approach
                data = json.loads(request.payload.decode('utf-8'))
                node_id = data.get('node_id', 'unknown')
                
                success = self.db.save_health_check(data)
                
                if success:
                    # Notify observers
                    await self._notify_observers(f"nodes/{node_id}/health", data)
                    return Message(code=Code.CHANGED, payload=b"Health status updated")
                else:
                    return Message(code=Code.INTERNAL_SERVER_ERROR, payload=b"Failed to update health status")
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid path")
                
        except Exception as e:
            logger.error(f"Error in PUT /nodes: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    def _parse_node_info(self, data: Dict[str, Any]):
        """Parse node info from JSON data."""
        from models import NodeInfo, NodeStatus
        from datetime import datetime
        
        # Create NodeInfo object from the data
        return NodeInfo(
            node_id=data.get('node_id', ''),
            hostname=data.get('hostname', ''),
            ip_address=data.get('ip_address', ''),
            status=NodeStatus(data.get('status', 'offline')),
            last_seen=datetime.fromisoformat(data.get('last_seen', datetime.now().isoformat())),
            services=data.get('services', []),
            drivers=data.get('drivers', []),
            system_info=data.get('system_info', {})
        )
    
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
    
    async def render(self, request):
        """Override render method to add URI parsing."""
        logger.info(f"HealthResource.render called with method: {request.code}")
        logger.info(f"HealthResource URI path: {request.opt.uri_path}")
        logger.info(f"HealthResource _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
        
        # Try to parse URI if path is empty
        path = request.opt.uri_path
        if not path or len(path) == 0:
            # Try multiple methods to get the URI
            uri_to_parse = None
            
            # Method 1: Try _original_request_uri (this has the correct path)
            try:
                uri_to_parse = getattr(request, '_original_request_uri', None)
            except Exception as e:
                pass
            
            # Method 2: Try get_request_uri() (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = request.get_request_uri()
                except Exception as e:
                    pass
            
            # Method 3: Try requested_path (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = getattr(request, 'requested_path', None)
                except Exception as e:
                    pass
            
            # Parse the URI if we found one
            if uri_to_parse:
                from urllib.parse import urlparse
                parsed = urlparse(uri_to_parse)
                if parsed.path:
                    path_parts = [part for part in parsed.path.split('/') if part]
                    path = tuple(path_parts)
                    # Update the request's URI path
                    request.opt.uri_path = path
                    logger.info(f"HealthResource: Parsed URI path: {path}")
                else:
                    logger.warning(f"HealthResource: URI has no path: {uri_to_parse}")
            else:
                logger.warning("HealthResource: No URI found in request")
        
        # Route to the appropriate method based on the request code
        if request.code == Code.GET:
            return await self.render_get(request)
        elif request.code == Code.PUT:
            return await self.render_put(request)
        else:
            return Message(code=Code.METHOD_NOT_ALLOWED, payload=b"Method not allowed")
    
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
    
    async def render_put(self, request):
        """Handle PUT requests for health updates."""
        try:
            logger.info(f"HealthResource.render_put called with method: {request.code}")
            
            # Parse health check data from payload
            data = json.loads(request.payload.decode('utf-8'))
            logger.info(f"Health check data: {data}")
            
            # Convert dictionary to HealthCheckResult object
            from models import HealthCheckResult
            from datetime import datetime
            
            # Parse timestamp if it's a string
            timestamp = data.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            else:
                timestamp = datetime.now()
            
            health_check = HealthCheckResult(
                node_id=data.get('node_id', ''),
                timestamp=timestamp,
                overall_healthy=data.get('overall_healthy', True),
                cpu_percent=data.get('cpu_percent', 0.0),
                memory_percent=data.get('memory_percent', 0.0),
                disk_percent=data.get('disk_percent', 0.0),
                temperature=data.get('temperature', 0.0),
                services_status=data.get('services_status', {}),
                error_messages=data.get('error_messages', [])
            )
            
            # Save health check to database
            success = self.db.save_health_check(health_check)
            
            if success:
                logger.info(f"Health check saved successfully for node: {health_check.node_id}")
                return Message(code=Code.CHANGED, payload=b"Health status updated")
            else:
                logger.error("Failed to save health check")
                return Message(code=Code.INTERNAL_SERVER_ERROR, payload=b"Failed to update health status")
                
        except Exception as e:
            logger.error(f"Error in PUT /health: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))


class SystemResource(resource.Resource):
    """CoAP resource for handling system operations."""
    
    def __init__(self):
        super().__init__()
    
    async def render(self, request):
        """Override render method to add URI parsing."""
        logger.info(f"SystemResource.render called with method: {request.code}")
        logger.info(f"SystemResource URI path: {request.opt.uri_path}")
        logger.info(f"SystemResource _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
        
        # Try to parse URI if path is empty
        path = request.opt.uri_path
        if not path or len(path) == 0:
            # Try multiple methods to get the URI
            uri_to_parse = None
            
            # Method 1: Try _original_request_uri (this has the correct path)
            try:
                uri_to_parse = getattr(request, '_original_request_uri', None)
            except Exception as e:
                pass
            
            # Method 2: Try get_request_uri() (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = request.get_request_uri()
                except Exception as e:
                    pass
            
            # Method 3: Try requested_path (fallback)
            if not uri_to_parse:
                try:
                    uri_to_parse = getattr(request, 'requested_path', None)
                except Exception as e:
                    pass
            
            # Parse the URI if we found one
            if uri_to_parse:
                from urllib.parse import urlparse
                parsed = urlparse(uri_to_parse)
                if parsed.path:
                    path_parts = [part for part in parsed.path.split('/') if part]
                    path = tuple(path_parts)
                    # Update the request's URI path
                    request.opt.uri_path = path
                    logger.info(f"SystemResource: Parsed URI path: {path}")
                else:
                    logger.warning(f"SystemResource: URI has no path: {uri_to_parse}")
            else:
                logger.warning("SystemResource: No URI found in request")
        
        # Route to the appropriate method based on the request code
        if request.code == Code.GET:
            return await self.render_get(request)
        elif request.code == Code.POST:
            return await self.render_post(request)
        elif request.code == Code.PUT:
            return await self.render_put(request)
        else:
            return Message(code=Code.METHOD_NOT_ALLOWED, payload=b"Method not allowed")
    
    async def render_post(self, request):
        """Handle POST requests for system operations."""
        try:
            logger.info(f"SystemResource.render_post called with method: {request.code}")
            
            # Parse action from payload
            data = json.loads(request.payload.decode('utf-8'))
            action = data.get('action', '')
            logger.info(f"System action requested: {action}")
            
            if action == "restart":
                # Restart system
                response_data = {
                    "message": "System restart initiated",
                    "timestamp": datetime.now().isoformat(),
                    "action": "restart"
                }
                payload = json.dumps(response_data).encode('utf-8')
                return Message(code=Code.CHANGED, payload=payload)
            
            elif action == "shutdown":
                # Shutdown system
                response_data = {
                    "message": "System shutdown initiated",
                    "timestamp": datetime.now().isoformat(),
                    "action": "shutdown"
                }
                payload = json.dumps(response_data).encode('utf-8')
                return Message(code=Code.CHANGED, payload=payload)
            
            elif action == "status":
                # Get system status
                status_info = {
                    "status": "running",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "main_server": "running",
                        "database": "connected"
                    },
                    "action": "status"
                }
                payload = json.dumps(status_info).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid action. Use: restart, shutdown, or status")
                
        except Exception as e:
            logger.error(f"Error in POST /system: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_get(self, request):
        """Handle GET requests for system information."""
        try:
            # Get system information
            system_info = {
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "uptime": "unknown",  # Could be enhanced to get actual uptime
                "version": "1.0.0",
                "endpoints": {
                    "health": "/health",
                    "nodes": "/nodes",
                    "updates": "/updates",
                    "system": "/system"
                },
                "available_actions": [
                    "restart",
                    "shutdown",
                    "status"
                ]
            }
            
            payload = json.dumps(system_info).encode('utf-8')
            return Message(code=Code.CONTENT, payload=payload)
                
        except Exception as e:
            logger.error(f"Error in GET /system: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))
    
    async def render_put(self, request):
        """Handle PUT requests for system operations."""
        try:
            logger.info(f"SystemResource.render_put called with method: {request.code}")
            
            # Parse action from payload
            data = json.loads(request.payload.decode('utf-8'))
            action = data.get('action', '')
            logger.info(f"System action requested: {action}")
            
            if action == "restart":
                # Restart system
                response_data = {
                    "message": "System restart initiated",
                    "timestamp": datetime.now().isoformat(),
                    "action": "restart"
                }
                payload = json.dumps(response_data).encode('utf-8')
                return Message(code=Code.CHANGED, payload=payload)
            
            elif action == "shutdown":
                # Shutdown system
                response_data = {
                    "message": "System shutdown initiated",
                    "timestamp": datetime.now().isoformat(),
                    "action": "shutdown"
                }
                payload = json.dumps(response_data).encode('utf-8')
                return Message(code=Code.CHANGED, payload=payload)
            
            elif action == "status":
                # Get system status
                status_info = {
                    "status": "running",
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "main_server": "running",
                        "database": "connected"
                    },
                    "action": "status"
                }
                payload = json.dumps(status_info).encode('utf-8')
                return Message(code=Code.CONTENT, payload=payload)
            
            else:
                return Message(code=Code.BAD_REQUEST, payload=b"Invalid action. Use: restart, shutdown, or status")
                
        except Exception as e:
            logger.error(f"Error in PUT /system: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR, payload=str(e).encode('utf-8'))


# Import os for file operations
import os
