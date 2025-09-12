# Manual Testing Steps

## 🚀 **Manual Testing Steps**

### **Step 1: Start the System**

Since you're on Windows, you can start the system using:

```bash
# Option 1: Using Docker Desktop (if installed)
docker-compose up --build -d

# Option 2: Using Python directly (if Python 3.9+ is installed)
cd main_server
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### **Step 2: Test the API**

Once the system is running, you can test it using:

#### **A. Check System Health**
```bash
# Main Server Health
curl http://localhost:8080/health

# Regular Node Health (if running)
curl http://localhost:8081/health
```

#### **B. Create an Update Request**
```bash
curl -X POST http://localhost:8080/api/updates \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": "test-update-001",
    "update_type": "service",
    "package_name": "test-service",
    "package_version": "1.0.0",
    "package_url": "https://example.com/test-service-1.0.0.tar.gz",
    "target_nodes": ["node-1", "node-2", "node-3"],
    "description": "Test service update"
  }'
```

#### **C. Monitor Update Progress**
```bash
# Get update status (replace {job_id} with actual job ID from step B)
curl http://localhost:8080/api/updates/{job_id}

# List all updates
curl http://localhost:8080/api/updates
```

### **Step 3: Use the Web Interface**

Open your browser and go to:
- **Main Server API Docs**: http://localhost:8080/docs
- **Interactive API Testing**: http://localhost:8080/redoc

### **Step 4: Import Postman Collection**

1. Open Postman
2. Import the file: `examples/postman_collection.json`
3. Set the environment variables:
   - `base_url`: http://localhost:8080
   - `node1_url`: http://localhost:8081
   - `node2_url`: http://localhost:8082
   - `node3_url`: http://localhost:8083

### **Step 5: Run the Test Script**

```bash
# Make executable (on Linux/Mac)
chmod +x examples/test_api.sh

# Run the test script
./examples/test_api.sh
```

## 🔍 **What to Expect**

### **Successful Startup:**
- Main Server should respond with `{"status": "healthy"}`
- API documentation should be accessible at `/docs`
- Regular nodes should register automatically

### **Update Flow:**
1. Send update request → Get job ID
2. Monitor job status → See "pending" → "in_progress" → "success/failed"
3. Check node health → Verify services are running
4. If failure → Automatic rollback should trigger

### **Health Monitoring:**
- Regular health checks every 60 seconds
- Comprehensive system resource monitoring
- Service status verification
- Network connectivity tests

## 🐛 **Troubleshooting**

If you encounter issues:

1. **Check Docker logs:**
   ```bash
   docker-compose logs -f
   ```

2. **Check specific service logs:**
   ```bash
   docker-compose logs main-server
   docker-compose logs regular-node-1
   ```

3. **Verify ports are available:**
   - Main Server: 8080
   - Regular Nodes: 8081, 8082, 8083

4. **Check system resources:**
   - Ensure 8GB RAM is available
   - Check disk space for Docker images

## 📊 **Expected Results**

The system should demonstrate:
- ✅ Centralized update management
- ✅ Automatic health checks
- ✅ Rollback on failure
- ✅ Real-time status monitoring
- ✅ Scalable architecture
- ✅ Comprehensive logging

## 🔧 **Alternative Testing Methods**

### **Using PowerShell (Windows)**
```powershell
# Check health
Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get

# Create update
$body = @{
    update_id = "test-update-001"
    update_type = "service"
    package_name = "test-service"
    package_version = "1.0.0"
    package_url = "https://example.com/test-service-1.0.0.tar.gz"
    target_nodes = @("node-1", "node-2", "node-3")
    description = "Test service update"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8080/api/updates" -Method Post -Body $body -ContentType "application/json"
```

### **Using Python Script**
```python
import requests
import json

# Check health
response = requests.get("http://localhost:8080/health")
print(response.json())

# Create update
update_data = {
    "update_id": "test-update-001",
    "update_type": "service",
    "package_name": "test-service",
    "package_version": "1.0.0",
    "package_url": "https://example.com/test-service-1.0.0.tar.gz",
    "target_nodes": ["node-1", "node-2", "node-3"],
    "description": "Test service update"
}

response = requests.post("http://localhost:8080/api/updates", json=update_data)
print(response.json())
```

## 📝 **Test Scenarios**

### **Scenario 1: Service Update**
1. Create a service update request
2. Monitor the update progress
3. Verify the service is running after update
4. Check health status

### **Scenario 2: Driver Update**
1. Create a driver update request
2. Monitor the update progress
3. Verify the driver is loaded
4. Check system logs

### **Scenario 3: Package Update**
1. Create a package update request
2. Monitor the update progress
3. Verify the package is installed
4. Check package version

### **Scenario 4: Failure and Rollback**
1. Create an update with invalid URL
2. Monitor the failure
3. Verify rollback is triggered
4. Check system is restored

### **Scenario 5: Health Monitoring**
1. Check initial health status
2. Wait for periodic health checks
3. Verify health reports are sent
4. Check health check logs

## 🎯 **Success Criteria**

The system is working correctly if:
- ✅ All services start without errors
- ✅ API endpoints respond correctly
- ✅ Updates can be created and monitored
- ✅ Health checks run automatically
- ✅ Rollback works on failure
- ✅ Logs are generated and accessible
- ✅ System recovers from failures
