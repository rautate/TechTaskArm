#!/bin/bash

# Example API usage script for Central Service & Driver Management System

set -e

MAIN_SERVER="http://localhost:8080"
NODE1="http://localhost:8081"
NODE2="http://localhost:8082"
NODE3="http://localhost:8083"

echo "=== Central Service & Driver Management System - API Test ==="
echo ""

# Function to make API calls with error handling
api_call() {
    local method="$1"
    local url="$2"
    local data="$3"
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "$url" -H "Content-Type: application/json" -d "$data"
    else
        curl -s -X "$method" "$url"
    fi
}

# Test 1: Check system health
echo "1. Checking system health..."
echo "Main Server: $(api_call GET "$MAIN_SERVER/health" | jq -r '.status')"
echo "Node 1: $(api_call GET "$NODE1/health" | jq -r '.status')"
echo "Node 2: $(api_call GET "$NODE2/health" | jq -r '.status')"
echo "Node 3: $(api_call GET "$NODE3/health" | jq -r '.status')"
echo ""

# Test 2: List all nodes
echo "2. Listing all registered nodes..."
api_call GET "$MAIN_SERVER/api/nodes" | jq '.nodes[] | {node_id, hostname, status}'
echo ""

# Test 3: Create a service update
echo "3. Creating a service update..."
UPDATE_RESPONSE=$(api_call POST "$MAIN_SERVER/api/updates" '{
    "update_id": "test-update-001",
    "update_type": "service",
    "package_name": "test-service",
    "package_version": "1.0.0",
    "package_url": "https://example.com/test-service-1.0.0.tar.gz",
    "target_nodes": ["node-1", "node-2", "node-3"],
    "description": "Test service update"
}')

JOB_ID=$(echo "$UPDATE_RESPONSE" | jq -r '.job_id')
echo "Update created with job ID: $JOB_ID"
echo ""

# Test 4: Monitor update progress
echo "4. Monitoring update progress..."
for i in {1..5}; do
    echo "Check $i:"
    STATUS=$(api_call GET "$MAIN_SERVER/api/updates/$JOB_ID" | jq -r '.status')
    echo "  Status: $STATUS"
    
    if [ "$STATUS" = "success" ] || [ "$STATUS" = "failed" ]; then
        break
    fi
    
    sleep 5
done
echo ""

# Test 5: Check node services
echo "5. Checking services on Node 1..."
api_call GET "$NODE1/agent/services" | jq '.services | keys[]'
echo ""

# Test 6: Get update job details
echo "6. Getting update job details..."
api_call GET "$MAIN_SERVER/api/updates/$JOB_ID" | jq '.'
echo ""

# Test 7: Create a driver update
echo "7. Creating a driver update..."
DRIVER_UPDATE_RESPONSE=$(api_call POST "$MAIN_SERVER/api/updates" '{
    "update_id": "test-driver-001",
    "update_type": "driver",
    "package_name": "test-driver",
    "package_version": "2.0.0",
    "package_url": "https://example.com/test-driver-2.0.0.ko",
    "target_nodes": ["node-1"],
    "description": "Test driver update"
}')

DRIVER_JOB_ID=$(echo "$DRIVER_UPDATE_RESPONSE" | jq -r '.job_id')
echo "Driver update created with job ID: $DRIVER_JOB_ID"
echo ""

# Test 8: Create a package update
echo "8. Creating a package update..."
PACKAGE_UPDATE_RESPONSE=$(api_call POST "$MAIN_SERVER/api/updates" '{
    "update_id": "test-package-001",
    "update_type": "package",
    "package_name": "htop",
    "package_version": "3.0.0",
    "package_url": "https://example.com/htop-3.0.0.deb",
    "target_nodes": ["node-2", "node-3"],
    "description": "Test package update"
}')

PACKAGE_JOB_ID=$(echo "$PACKAGE_UPDATE_RESPONSE" | jq -r '.job_id')
echo "Package update created with job ID: $PACKAGE_JOB_ID"
echo ""

# Test 9: List all update jobs
echo "9. Listing all update jobs..."
api_call GET "$MAIN_SERVER/api/updates" | jq '.jobs[] | {job_id, status, created_at}'
echo ""

# Test 10: Check specific node health details
echo "10. Checking detailed health for Node 1..."
api_call GET "$NODE1/health" | jq '.details'
echo ""

echo "=== API Test Completed ==="
echo ""
echo "Summary:"
echo "- Created 3 test updates (service, driver, package)"
echo "- Monitored update progress"
echo "- Checked node health and services"
echo "- Verified system functionality"
echo ""
echo "To view detailed logs:"
echo "  docker-compose logs -f"
echo ""
echo "To check specific service logs:"
echo "  curl $NODE1/agent/logs/test-service"
