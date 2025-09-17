"""Main Server with CoAP support for ARM Cortex A55 IoT updates."""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from aiocoap import Context, Message, Code, resource
# Response codes are available directly from aiocoap.numbers
import os

from models import UpdateRequest, NodeInfo, HealthCheckResult, NodeStatus
from database import Database
from update_manager import CoAPUpdateManager
from coap_resources import UpdateResource, NodeResource, HealthResource, SystemResource

class NodeResourceWrapper(resource.Resource):
    """Wrapper resource to handle all /nodes/* paths."""
    
    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.node_resource = NodeResource(db)
    
    async def render(self, request):
        """Handle all /nodes/* requests."""
        logger.info("=" * 50)
        logger.info("NodeResourceWrapper.render called!")
        logger.info(f"Method: {request.code}")
        logger.info(f"Request URI: {getattr(request, 'uri', 'No URI')}")
        logger.info(f"Request options: {request.opt}")
        logger.info(f"URI path: {request.opt.uri_path}")
        logger.info(f"NodeResourceWrapper _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
        logger.info("=" * 50)
        
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
                    logger.info(f"NodeResourceWrapper: Parsed URI path: {path}")
                else:
                    logger.warning(f"NodeResourceWrapper: URI has no path: {uri_to_parse}")
            else:
                logger.warning("NodeResourceWrapper: No URI found in request")
        
        # Route to the appropriate method based on the request code
        if request.code == Code.GET:
            return await self.node_resource.render_get(request)
        elif request.code == Code.POST:
            return await self.node_resource.render_post(request)
        elif request.code == Code.PUT:
            return await self.node_resource.render_put(request)
        else:
            return Message(code=Code.METHOD_NOT_ALLOWED, payload=b"Method not allowed")

class DebugResource(resource.Resource):
    """Debug resource to catch all requests."""
    
    def __init__(self, db=None, update_manager=None):
        super().__init__()
        self.db = db
        self.update_manager = update_manager
    
    async def render(self, request):
        """Handle all requests for debugging."""
        logger.info("=" * 50)
        logger.info("DebugResource.render called!")
        logger.info(f"Method: {request.code}")
        logger.info(f"Request URI: {getattr(request, 'uri', 'No URI')}")
        logger.info(f"Request options: {request.opt}")
        logger.info(f"URI path: {request.opt.uri_path}")
        logger.info(f"DebugResource _original_request_uri: {getattr(request, '_original_request_uri', 'NO_ORIGINAL_REQUEST_URI')}")
        logger.info("DebugResource is handling this request - this means no specific resource matched")
        logger.info("This should NOT happen for /nodes/* requests - they should go to NodeResourceWrapper")
        logger.info("=" * 50)
        
        # Try to parse URI if path is empty
        path = request.opt.uri_path
        if not path or len(path) == 0:
            # Try to extract path from URI if available
            if hasattr(request, 'uri') and request.uri:
                from urllib.parse import urlparse
                parsed = urlparse(request.uri)
                if parsed.path:
                    path_parts = [part for part in parsed.path.split('/') if part]
                    logger.info(f"Parsed path from URI: {path_parts}")
                    path = tuple(path_parts)
                    # Update the request's URI path
                    request.opt.uri_path = path
                    logger.info(f"Updated URI path: {path}")
        
        # Try to route to appropriate resource based on path
        
        if len(path) >= 1:
            if path[0] == 'nodes':
                # Route to NodeResource
                node_resource = NodeResource(self.db)
                return await node_resource.render(request)
            elif path[0] == 'updates':
                # Route to UpdateResource
                update_resource = UpdateResource(self.update_manager)
                return await update_resource.render(request)
            elif path[0] == 'health':
                # Route to HealthResource
                health_resource = HealthResource(self.db)
                return await health_resource.render(request)
            elif path[0] == 'system':
                # Route to SystemResource
                system_resource = SystemResource()
                return await system_resource.render(request)
        
        # If no specific resource matches, return not found
        return Message(code=Code.NOT_FOUND, payload=b"Resource not found")

class TestResource(resource.Resource):
    """Simple test resource."""
    
    async def render(self, request):
        """Handle test requests."""
        logger.info(f"TestResource.render called with method: {request.code}")
        logger.info(f"Request URI: {getattr(request, 'uri', 'No URI')}")
        logger.info(f"Request options: {request.opt}")
        logger.info(f"URI path: {request.opt.uri_path}")
        
        # Try to parse URI if path is empty
        path = request.opt.uri_path
        if not path or len(path) == 0:
            # Try to extract path from URI if available
            if hasattr(request, 'uri') and request.uri:
                from urllib.parse import urlparse
                parsed = urlparse(request.uri)
                if parsed.path:
                    path_parts = [part for part in parsed.path.split('/') if part]
                    logger.info(f"TestResource parsed path from URI: {path_parts}")
                    path = tuple(path_parts)
                    # Update the request's URI path
                    request.opt.uri_path = path
                    logger.info(f"TestResource updated URI path: {path}")
        
        return Message(code=Code.CONTENT, payload=b"Test resource working")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db = None
update_manager = None
coap_server = None


class CoAPMainServer:
    """Main CoAP server for IoT device management."""
    
    def __init__(self):
        self.db = Database()
        self.update_manager = CoAPUpdateManager(self.db)
        self.context = None
        
    async def start(self, host: str = "0.0.0.0", port: int = 5683):
        """Start the CoAP server."""
        try:
            # Create root resource
            root = resource.Site()
            
            # Add resource handlers
            root.add_resource(['updates'], UpdateResource(self.update_manager))
            root.add_resource(['nodes'], NodeResource(self.db))
            root.add_resource(['health'], HealthResource(self.db))
            root.add_resource(['system'], SystemResource())
            
            # Add a simple test resource
            root.add_resource(['test'], TestResource())
            
            # Add a catch-all resource for debugging (must be last)
            root.add_resource([], DebugResource(self.db, self.update_manager))
            
            # Create and start CoAP server context
            self.context = await Context.create_server_context(root, bind=(host, port))
            
            logger.info(f"CoAP server started on {host}:{port}")
            logger.info(f"Server context: {self.context}")
            logger.info(f"Root resource: {root}")
            
        except Exception as e:
            logger.error(f"Error starting CoAP server: {e}")
            raise
    
    async def stop(self):
        """Stop the CoAP server."""
        try:
            if self.context:
                await self.context.shutdown()
                logger.info("CoAP server stopped")
        except Exception as e:
            logger.error(f"Error stopping CoAP server: {e}")


async def main():
    """Main function to start the CoAP server."""
    global db, update_manager, coap_server
    
    logger.info("Starting Main Server with CoAP support...")
    
    # Initialize database
    db = Database()
    
    # Initialize update manager
    update_manager = CoAPUpdateManager(db)
    
    # Create and start CoAP server
    coap_server = CoAPMainServer()
    await coap_server.start()
    
    logger.info("Main Server started successfully")
    
    try:
        # Keep server running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await coap_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
