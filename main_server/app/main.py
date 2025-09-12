"""Main Server FastAPI application."""

import logging
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .models import UpdateRequest, NodeInfo, HealthCheckResult, NodeStatus
from .database import Database
from .update_manager import UpdateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db = None
update_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db, update_manager
    
    # Startup
    logger.info("Starting Main Server...")
    db = Database()
    update_manager = UpdateManager(db)
    logger.info("Main Server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Main Server...")


app = FastAPI(
    title="Central Service & Driver Management System",
    description="Main Server for managing updates across regular nodes",
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Central Service & Driver Management System - Main Server",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


# Node management endpoints
@app.post("/api/nodes/register")
async def register_node(node_info: NodeInfo):
    """Register a new regular node."""
    try:
        success = db.register_node(node_info)
        if success:
            return {"message": "Node registered successfully", "node_id": node_info.node_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to register node")
    except Exception as e:
        logger.error(f"Error registering node: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nodes")
async def get_nodes():
    """Get all registered nodes."""
    try:
        nodes = db.get_all_nodes()
        return {"nodes": [node.dict() for node in nodes]}
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nodes/{node_id}")
async def get_node(node_id: str):
    """Get specific node information."""
    try:
        node = db.get_node(node_id)
        if node:
            return {"node": node.dict()}
        else:
            raise HTTPException(status_code=404, detail="Node not found")
    except Exception as e:
        logger.error(f"Error getting node {node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nodes/{node_id}/status")
async def update_node_status(node_id: str, status: NodeStatus):
    """Update node status."""
    try:
        success = db.update_node_status(node_id, status)
        if success:
            return {"message": "Node status updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Node not found")
    except Exception as e:
        logger.error(f"Error updating node status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Update management endpoints
@app.post("/api/updates")
async def create_update(update_request: UpdateRequest, background_tasks: BackgroundTasks):
    """Create a new update request."""
    try:
        # Validate target nodes
        for node_id in update_request.target_nodes:
            node = db.get_node(node_id)
            if not node:
                raise HTTPException(status_code=400, detail=f"Node {node_id} not found")
            if node.status != NodeStatus.ONLINE:
                raise HTTPException(status_code=400, detail=f"Node {node_id} is not online")
        
        # Process update request
        job_id = await update_manager.process_update_request(update_request)
        
        return {
            "message": "Update request created successfully",
            "job_id": job_id,
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/updates/{job_id}")
async def get_update_status(job_id: str):
    """Get update job status."""
    try:
        status = update_manager.get_job_status(job_id)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting update status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/updates")
async def get_all_updates():
    """Get all update jobs."""
    try:
        jobs = update_manager.get_all_jobs()
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check reporting endpoint
@app.post("/api/health-checks")
async def report_health_check(health_check: HealthCheckResult):
    """Receive health check reports from nodes."""
    try:
        success = db.save_health_check(health_check)
        if success:
            return {"message": "Health check reported successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save health check")
    except Exception as e:
        logger.error(f"Error reporting health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Node agent endpoints (for receiving status updates)
@app.post("/api/agent/update-status")
async def update_status_report(node_id: str, job_id: str, status: str, error_message: str = None):
    """Receive update status reports from node agents."""
    try:
        # This would update the node update status in the database
        # Implementation depends on the specific status reporting format
        logger.info(f"Received status update from node {node_id} for job {job_id}: {status}")
        return {"message": "Status update received"}
    except Exception as e:
        logger.error(f"Error processing status update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
