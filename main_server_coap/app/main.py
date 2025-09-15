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
            
            # Create and start CoAP server context
            self.context = await Context.create_server_context(root, bind=(host, port))
            
            logger.info(f"CoAP server started on {host}:{port}")
            
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
