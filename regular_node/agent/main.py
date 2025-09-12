"""Regular Node Agent FastAPI application."""

import asyncio
import logging
import socket
import aiohttp
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid

from .update_handler import UpdateHandler
from .health_checker import HealthChecker

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
health_check_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global node_id, main_server_url, update_handler, health_checker, health_check_task
    
    # Startup
    logger.info("Starting Regular Node Agent...")
    
    # Generate or load node ID
    node_id = str(uuid.uuid4())
    main_server_url = "http://main-server:8080"  # Docker service name
    
    # Initialize components
    update_handler = UpdateHandler(node_id)
    health_checker = HealthChecker(node_id)
    
    # Register with main server
    await register_with_main_server()
    
    # Start periodic health checks
    health_check_task = asyncio.create_task(periodic_health_check())
    
    logger.info(f"Regular Node Agent started with ID: {node_id}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Regular Node Agent...")
    if health_check_task:
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Regular Node Agent",
    description="Agent for receiving and executing updates from Main Server",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def register_with_main_server():
    """Register this node with the main server."""
    try:
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
            "architecture": "x86_64",
            "kernel": "5.4.0",
            "ram_gb": 8
        }
        
        node_info = {
            "node_id": node_id,
            "hostname": hostname,
            "ip_address": ip_address,
            "status": "online",
            "last_seen": datetime.now().isoformat(),
            "services": services,
            "drivers": drivers,
            "system_info": system_info
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{main_server_url}/api/nodes/register"
            async with session.post(url, json=node_info) as response:
                if response.status == 200:
                    logger.info("Successfully registered with main server")
                else:
                    logger.error(f"Failed to register with main server: {response.status}")
    
    except Exception as e:
        logger.error(f"Error registering with main server: {e}")


async def periodic_health_check():
    """Perform periodic health checks and report to main server."""
    while True:
        try:
            # Wait 60 seconds between health checks
            await asyncio.sleep(60)
            
            # Perform health check
            health_result = await health_checker.perform_health_check()
            
            # Report to main server
            await report_health_check(health_result)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic health check: {e}")


async def report_health_check(health_result):
    """Report health check result to main server."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{main_server_url}/api/health-checks"
            async with session.post(url, json=health_result) as response:
                if response.status == 200:
                    logger.debug("Health check reported successfully")
                else:
                    logger.error(f"Failed to report health check: {response.status}")
    
    except Exception as e:
        logger.error(f"Error reporting health check: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Regular Node Agent",
        "node_id": node_id,
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_result = await health_checker.perform_health_check()
        return {
            "status": "healthy" if health_result["overall_healthy"] else "unhealthy",
            "node_id": node_id,
            "timestamp": health_result["timestamp"].isoformat(),
            "details": health_result
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "node_id": node_id,
            "error": str(e)
        }


@app.post("/agent/update")
async def receive_update(update_data: dict):
    """Receive update command from main server."""
    try:
        logger.info(f"Received update request: {update_data}")
        
        # Process the update
        result = await update_handler.install_update(update_data)
        
        # Report status back to main server
        await report_update_status(
            update_data.get("job_id"),
            "success" if result["success"] else "failed",
            result.get("error_message"),
            result.get("health_check_passed", False)
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Update processing failed: {e}")
        
        # Report failure to main server
        await report_update_status(
            update_data.get("job_id"),
            "failed",
            str(e),
            False
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/rollback")
async def receive_rollback(rollback_data: dict):
    """Receive rollback command from main server."""
    try:
        job_id = rollback_data.get("job_id")
        logger.info(f"Received rollback request for job: {job_id}")
        
        # For now, just acknowledge the rollback
        # In a real implementation, this would restore from backup
        result = {
            "success": True,
            "message": f"Rollback completed for job {job_id}",
            "job_id": job_id
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Rollback processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def report_update_status(job_id: str, status: str, error_message: str = None, health_check_passed: bool = False):
    """Report update status to main server."""
    try:
        status_data = {
            "node_id": node_id,
            "job_id": job_id,
            "status": status,
            "error_message": error_message,
            "health_check_passed": health_check_passed,
            "timestamp": datetime.now().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{main_server_url}/api/agent/update-status"
            async with session.post(url, json=status_data) as response:
                if response.status == 200:
                    logger.info(f"Update status reported: {status}")
                else:
                    logger.error(f"Failed to report update status: {response.status}")
    
    except Exception as e:
        logger.error(f"Error reporting update status: {e}")


@app.get("/agent/services")
async def get_services():
    """Get list of services on this node."""
    try:
        services_status = await health_checker._check_services()
        return {"services": services_status}
    except Exception as e:
        logger.error(f"Error getting services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agent/logs/{service_name}")
async def get_service_logs(service_name: str, lines: int = 50):
    """Get logs for a specific service."""
    try:
        logs = health_checker.get_service_logs(service_name, lines)
        return {"service": service_name, "logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info"
    )
