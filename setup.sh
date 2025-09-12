#!/bin/bash

# Setup script for Central Service & Driver Management System

set -e

echo "Setting up Central Service & Driver Management System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data/main_server
mkdir -p data/node1/{updates,backups,logs}
mkdir -p data/node2/{updates,backups,logs}
mkdir -p data/node3/{updates,backups,logs}

# Set permissions
echo "Setting permissions..."
chmod +x regular_node/scripts/*.sh
chmod +x setup.sh

# Build and start services
echo "Building and starting services..."
docker-compose build

echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Check service health
echo "Checking service health..."

# Check main server
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "✓ Main Server is healthy"
else
    echo "✗ Main Server is not responding"
fi

# Check regular nodes
for port in 8081 8082 8083; do
    if curl -f http://localhost:$port/health >/dev/null 2>&1; then
        echo "✓ Regular Node on port $port is healthy"
    else
        echo "✗ Regular Node on port $port is not responding"
    fi
done

echo ""
echo "Setup completed!"
echo ""
echo "Services are running on:"
echo "  Main Server: http://localhost:8080"
echo "  Regular Node 1: http://localhost:8081"
echo "  Regular Node 2: http://localhost:8082"
echo "  Regular Node 3: http://localhost:8083"
echo ""
echo "API Documentation:"
echo "  Main Server API: http://localhost:8080/docs"
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
echo "To restart services: docker-compose restart"
