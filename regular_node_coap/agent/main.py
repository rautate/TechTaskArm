"""Regular Node Agent with CoAP support for ARM Cortex A55 IoT updates."""

import asyncio
import logging
import socket
from datetime import datetime
from aiocoap import Context, Message, Code, resource
# Response codes are available directly from aiocoap.numbers
import json
import uuid

from update_handler import CoAPUpdateHandler
from health_checker import HealthChecker
from coap_resources import NodeUpdateResource, HealthResource, SystemResource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
node_id = None
main_server_url = None
update_handler = None
health_checker = None
coap_server = None
health_check_task = None


class CoAPNodeAgent:
    """CoAP-based node agent for IoT device management."""
    
    def __init__(self, node_id: str, main_server_url: str):
        self.node_id = node_id
        self.main_server_url = main_server_url
        self.update_handler = CoAPUpdateHandler(node_id, main_server_url)
        self.health_checker = HealthChecker(node_id)
        self.context = None
        self.health_check_task = None
        
    async def start(self, host: str = "0.0.0.0", port: int = 5683):
        """Start the CoAP node agent."""
        try:
            # Create root resource
            root = resource.Site()
            
            # Add resource handlers
            root.add_resource(['updates'], NodeUpdateResource(self.update_handler))
            root.add_resource(['health'], HealthResource(self.health_checker))
            root.add_resource(['system'], SystemResource())
            
            # Create and start CoAP server context
            self.context = await Context.create_server_context(root, bind=(host, port))
            
            # Register with main server
            await self.register_with_main_server()
            
            # Start periodic health checks
            self.health_check_task = asyncio.create_task(self.periodic_health_check())
            
            logger.info(f"CoAP node agent started on {host}:{port}")
            
        except Exception as e:
            logger.error(f"Error starting CoAP node agent: {e}")
            raise
    
    async def stop(self):
        """Stop the CoAP node agent."""
        try:
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self.context:
                await self.context.shutdown()
                logger.info("CoAP node agent stopped")
        except Exception as e:
            logger.error(f"Error stopping CoAP node agent: {e}")
    
    async def register_with_main_server(self):
        """Register this node with the main server via CoAP."""
        try:
            # Create client context for registration
            client_context = await Context.create_client_context()
            
            # Get system information
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            
            # Get list of services (simplified)
            services = ["node-agent", "docker", "systemd-resolved", "ssh"]
            
            # Get list of drivers (simplified)
            drivers = ["usb-storage", "network", "audio"]
            
            # System info
            system_info = {
                "os": "Linux",
                "architecture": "aarch64",  # ARM Cortex A55
                "kernel": "5.4.0",
                "ram_gb": 8
            }
            
            node_info = {
                "node_id": self.node_id,
                "hostname": hostname,
                "ip_address": ip_address,
                "status": "online",
                "last_seen": datetime.now().isoformat(),
                "services": services,
                "drivers": drivers,
                "system_info": system_info
            }
            
            # Send registration via CoAP
            request = Message(
                code=Code.POST,
                uri=f"coap://main-server:5683/nodes",
                payload=json.dumps(node_info).encode('utf-8')
            )
            
            response = await client_context.request(request).response
            
            if response.code.is_successful():
                logger.info("Successfully registered with main server via CoAP")
            else:
                logger.error(f"Failed to register with main server: {response.code}")
                
        except Exception as e:
            logger.error(f"Error registering with main server: {e}")
    
    async def periodic_health_check(self):
        """Perform periodic health checks and report to main server."""
        while True:
            try:
                # Wait 60 seconds between health checks
                await asyncio.sleep(60)
                
                # Perform health check
                health_result = await self.health_checker.perform_health_check()
                
                # Report to main server via CoAP
                await self.report_health_check(health_result)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
    
    async def report_health_check(self, health_result):
        """Report health check result to main server via CoAP."""
        try:
            # Create client context for health reporting
            client_context = await Context.create_client_context()
            
            request = Message(
                code=Code.PUT,
                uri=f"coap://main-server:5683/nodes/{self.node_id}/health",
                payload=json.dumps(health_result).encode('utf-8')
            )
            
            response = await client_context.request(request).response
            
            if response.code.is_successful():
                logger.debug("Health check reported successfully via CoAP")
            else:
                logger.error(f"Failed to report health check: {response.code}")
                
        except Exception as e:
            logger.error(f"Error reporting health check: {e}")


async def main():
    """Main function to start the CoAP node agent."""
    global node_id, main_server_url, update_handler, health_checker, coap_server, health_check_task
    
    logger.info("Starting Regular Node Agent with CoAP support...")
    
    # Generate or load node ID
    node_id = str(uuid.uuid4())
    main_server_url = "coap://main-server:5683"
    
    # Initialize components
    update_handler = CoAPUpdateHandler(node_id, main_server_url)
    health_checker = HealthChecker(node_id)
    
    # Create and start CoAP node agent
    coap_server = CoAPNodeAgent(node_id, main_server_url)
    await coap_server.start()
    
    logger.info(f"Regular Node Agent started with ID: {node_id}")
    
    try:
        # Keep server running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await coap_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
