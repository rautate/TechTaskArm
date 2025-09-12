# Central Service & Driver Management System

A prototype system for managing services and drivers across multiple Linux machines with centralized update orchestration.

## Overview

This system provides a centralized way to manage updates for services and drivers across multiple regular nodes (worker machines) from a main server. It's designed to work efficiently on low-power hardware with 8GB RAM, with **specialized support for ARM architecture** including quad-core ARM Cortex-A55 processors commonly found in embedded systems and IoT devices.

## Architecture

- **Main Server**: Central coordination server that receives update requests and orchestrates updates across regular nodes
- **Regular Nodes**: Worker machines that run agents to receive and execute updates
- **Update Flow**: Main Server → Regular Nodes → Status Reporting → Rollback (if needed)

## Features

- ✅ Centralized update management
- ✅ Automatic health checks after updates
- ✅ Rollback mechanism for failed updates
- ✅ Lightweight and resource-efficient
- ✅ **ARM architecture support** (Cortex-A55, A72, A78)
- ✅ **Quad-core ARM optimization**
- ✅ Scalable to many regular nodes
- ✅ Comprehensive logging and monitoring
- ✅ Docker-based deployment with multi-architecture support
- ✅ REST API for integration

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Linux system (tested on Ubuntu 20.04+)
- Minimum 8GB RAM
- Network connectivity between nodes

### Installation

1. Clone or download this repository
2. Run the setup script:

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Build Docker images for main server and regular nodes
- Start all services
- Verify health of all components

### Access Points

- **Main Server API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **Regular Node 1**: http://localhost:8081
- **Regular Node 2**: http://localhost:8082
- **Regular Node 3**: http://localhost:8083

## Usage Examples

### 1. Check System Status

```bash
# Check main server health
curl http://localhost:8080/health

# Check all registered nodes
curl http://localhost:8080/api/nodes

# Check specific node health
curl http://localhost:8081/health
```

### 2. Create an Update Request

```bash
curl -X POST http://localhost:8080/api/updates \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": "update-001",
    "update_type": "service",
    "package_name": "my-service",
    "package_version": "1.2.0",
    "package_url": "https://example.com/my-service-1.2.0.tar.gz",
    "target_nodes": ["node-1", "node-2", "node-3"],
    "description": "Update my-service to version 1.2.0"
  }'
```

### 3. Monitor Update Progress

```bash
# Get update job status
curl http://localhost:8080/api/updates/{job_id}

# Get all update jobs
curl http://localhost:8080/api/updates
```

### 4. Check Node Services

```bash
# Get services running on a node
curl http://localhost:8081/agent/services

# Get logs for a specific service
curl http://localhost:8081/agent/logs/my-service
```

## API Reference

### Main Server Endpoints

#### Node Management
- `GET /api/nodes` - List all registered nodes
- `GET /api/nodes/{node_id}` - Get specific node information
- `POST /api/nodes/register` - Register a new node
- `POST /api/nodes/{node_id}/status` - Update node status

#### Update Management
- `POST /api/updates` - Create new update request
- `GET /api/updates` - List all update jobs
- `GET /api/updates/{job_id}` - Get update job status

#### Health Monitoring
- `POST /api/health-checks` - Receive health check reports
- `GET /health` - Main server health check

### Regular Node Endpoints

- `GET /health` - Node health check
- `POST /agent/update` - Receive update command
- `POST /agent/rollback` - Receive rollback command
- `GET /agent/services` - List node services
- `GET /agent/logs/{service_name}` - Get service logs

## Update Types

The system supports three types of updates:

### 1. Service Updates
- Updates application services
- Stops service, installs update, restarts service
- Includes systemd service file updates

### 2. Driver Updates
- Updates kernel drivers
- Removes old driver, installs new one, loads module
- Includes depmod and modprobe operations

### 3. Package Updates
- Updates system packages
- Uses apt/dpkg for installation
- Supports both repository and direct package installation

## Health Checks

The system performs comprehensive health checks including:

- **Service Status**: Checks if critical services are running
- **System Resources**: CPU, memory, and disk usage monitoring
- **Network Connectivity**: DNS resolution and internet connectivity
- **Process Monitoring**: Ensures critical processes are running
- **Log Analysis**: Monitors system logs for errors

## Rollback Mechanism

If an update fails or health checks fail after update:

1. System automatically triggers rollback
2. Restores files from backup
3. Restarts affected services
4. Reports rollback status to main server

## Configuration

### Environment Variables

#### Main Server
- `PYTHONPATH`: Python path for imports
- `DATABASE_URL`: SQLite database path (default: main_server.db)

#### Regular Nodes
- `NODE_ID`: Unique identifier for the node
- `MAIN_SERVER_URL`: URL of the main server
- `PYTHONPATH`: Python path for imports

### Docker Configuration

The system uses Docker Compose with:
- **Networks**: Isolated management network
- **Volumes**: Persistent storage for updates, backups, and logs
- **Health Checks**: Automatic service health monitoring
- **Restart Policies**: Automatic restart on failure

## Monitoring and Logging

### Log Locations
- **Main Server**: Docker logs (`docker-compose logs main-server`)
- **Regular Nodes**: `/var/log/node-agent/` inside containers
- **System Logs**: Available via journalctl

### Health Monitoring
- Automatic health checks every 60 seconds
- Real-time status reporting to main server
- Comprehensive system resource monitoring

## Scaling

To add more regular nodes:

1. Add new service to `docker-compose.yml`
2. Update port mappings
3. Add new volumes
4. Restart with `docker-compose up -d`

Example for node-4:
```yaml
regular-node-4:
  build: ./regular_node
  container_name: regular-node-4
  ports:
    - "8084:8081"
  volumes:
    - node4_data:/opt/node-updates
    - node4_backups:/opt/node-backups
    - node4_logs:/var/log/node-agent
  environment:
    - NODE_ID=node-4
  networks:
    - management_network
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   - Check Docker logs: `docker-compose logs`
   - Verify port availability
   - Check system resources

2. **Update failures**
   - Check node agent logs
   - Verify package URLs are accessible
   - Check disk space on nodes

3. **Health check failures**
   - Review health check logs
   - Check system resource usage
   - Verify network connectivity

### Debug Commands

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f main-server
docker-compose logs -f regular-node-1

# Check service status
docker-compose ps

# Restart specific service
docker-compose restart main-server

# Access container shell
docker-compose exec regular-node-1 /bin/bash
```

## Development

### Project Structure
```
cvtask/
├── main_server/          # Main server application
│   ├── app/             # Python application code
│   ├── Dockerfile       # Main server container
│   └── requirements.txt # Python dependencies
├── regular_node/        # Regular node agent
│   ├── agent/          # Python agent code
│   ├── scripts/        # Shell scripts for updates
│   ├── Dockerfile      # Node agent container
│   └── requirements.txt # Python dependencies
├── docker-compose.yml   # Docker orchestration
├── setup.sh            # Setup script
└── README.md           # This file
```

### Adding New Features

1. **New Update Types**: Extend `UpdateType` enum and update handlers
2. **New Health Checks**: Add methods to `HealthChecker` class
3. **New API Endpoints**: Add routes to FastAPI applications
4. **New Monitoring**: Extend logging and status reporting

## License

This project is a prototype for demonstration purposes.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Docker logs
3. Check system resource usage
4. Verify network connectivity
