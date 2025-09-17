"""Regular Node Agent with CoAP support for ARM Cortex A55 IoT updates."""

import asyncio
import logging
import socket
import os
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
            logger.info(f"Attempting to register with main server at: {self.main_server_url}")
            
            # Create client context for registration
            client_context = await Context.create_client_context()
            
            # Get system information
            hostname = socket.gethostname()
            
            # Get IP address more reliably (avoid DNS resolution issues)
            try:
                # Try to get IP from hostname first
                ip_address = socket.gethostbyname(hostname)
            except socket.gaierror:
                # If hostname resolution fails, get IP from network interface
                import subprocess
                try:
                    result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        ip_address = result.stdout.strip().split()[0]  # Get first IP
                    else:
                        ip_address = "127.0.0.1"  # Fallback
                except:
                    ip_address = "127.0.0.1"  # Fallback
            
            # Minimal registration data to avoid CoAP message size limits
            node_info = {
                "node_id": self.node_id,
                "hostname": hostname,
                "ip_address": ip_address,
                "status": "online",
                "last_seen": datetime.now().isoformat()
            }
            
            payload_data = json.dumps(node_info).encode('utf-8')
            logger.info(f"Sending registration data: {json.dumps(node_info, indent=2)}")
            logger.info(f"Payload size: {len(payload_data)} bytes")
            
            # Send registration via CoAP
            request = Message(
                code=Code.POST,
                uri=f"{self.main_server_url}/nodes",
                payload=payload_data
            )
            
            logger.info(f"Sending CoAP request to: {self.main_server_url}/nodes")
            response = await client_context.request(request).response
            
            if response.code.is_successful():
                logger.info("Successfully registered with main server via CoAP")
            else:
                logger.error(f"Failed to register with main server: {response.code}")
                
        except Exception as e:
            logger.error(f"Error registering with main server: {e} - {self.main_server_url} - {client_context}")
    
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
                uri=f"{self.main_server_url}/health",
                payload=json.dumps(health_result).encode('utf-8')
            )
            
            logger.info(f"Sending health check to: {self.main_server_url}/health")
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
    
    # Get main server URL from environment variable or use default
    main_server_host = os.getenv('MAIN_SERVER_HOST', '')
    main_server_port = os.getenv('MAIN_SERVER_PORT', '5683')
    main_server_url = f"coap://{main_server_host}:{main_server_port}"
    
    logger.info(f"Environment MAIN_SERVER_HOST: {os.getenv('MAIN_SERVER_HOST', 'NOT_SET')}")
    logger.info(f"Environment MAIN_SERVER_PORT: {os.getenv('MAIN_SERVER_PORT', 'NOT_SET')}")
    logger.info(f"Using main server URL: {main_server_url}")
    
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
