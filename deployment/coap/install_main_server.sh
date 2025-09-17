#!/bin/bash

# CoAP Main Server deployment for Central Service & Driver Management System
# Optimized for ARM Cortex A55 quad-core devices
# Resource usage: ~200MB RAM, ~0.2 CPU cores

set -e

echo "=========================================="
echo "Central Service & Driver Management System"
echo "CoAP Main Server Deployment for ARM"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Detect architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    echo "✓ Detected ARM64 architecture (Cortex-A55 compatible)"
    PYTHON_ARCH="linux-aarch64"
elif [[ "$ARCH" == "armv7l" ]]; then
    echo "✓ Detected ARM32 architecture"
    PYTHON_ARCH="linux-armv7l"
else
    echo "✓ Detected x86_64 architecture"
    PYTHON_ARCH="linux-x86_64"
fi

# Update system packages
echo "📦 Updating system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 wget curl systemd

# Create system user
echo "👤 Creating system user..."
useradd -r -s /bin/false -d /opt/management-system management-system || echo "User already exists"

# Create application directories
echo "📁 Creating directories..."
mkdir -p /opt/management-system/main-server
mkdir -p /var/log/management-system
mkdir -p /etc/management-system
mkdir -p /opt/firmware

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv /opt/management-system/main-server/venv

# Install Python packages
echo "📚 Installing Python dependencies..."
/opt/management-system/main-server/venv/bin/pip install --upgrade pip
/opt/management-system/main-server/venv/bin/pip install aiocoap==0.4.4 pydantic==2.5.0

# Copy application files
echo "📋 Copying application files..."
cp -r main_server_coap/* /opt/management-system/main-server/

# Create startup script
echo "🚀 Creating startup script..."
cat > /opt/management-system/main-server/start.sh << 'EOF'
#!/bin/bash
cd /opt/management-system/main-server
source venv/bin/activate
python app/main.py
EOF

chmod +x /opt/management-system/main-server/start.sh

# Create systemd service file
echo "⚙️ Creating systemd service..."

# Main Server service
cat > /etc/systemd/system/main-server-coap.service << 'EOF'
[Unit]
Description=Central Service & Driver Management System - Main Server (CoAP)
Documentation=https://github.com/your-repo/management-system
After=network.target
Wants=network.target

[Service]
Type=simple
User=management-system
Group=management-system
WorkingDirectory=/opt/management-system/main-server
ExecStart=/opt/management-system/main-server/start.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=main-server-coap

# Resource limits for ARM optimization
MemoryLimit=200M
CPUQuota=20%

# Environment
Environment=PYTHONPATH=/opt/management-system/main-server
Environment=PYTHONUNBUFFERED=1
Environment=COAP_HOST=0.0.0.0
Environment=COAP_PORT=5683

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/management-system /var/log/management-system /opt/firmware

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
echo "🔐 Setting permissions..."
chown -R management-system:management-system /opt/management-system
chown -R management-system:management-system /var/log/management-system
chown -R management-system:management-system /opt/firmware

# Create health check script
echo "🏥 Creating health check script..."
cat > /opt/management-system/health-check-main-server.sh << 'EOF'
#!/bin/bash

# Health check script for CoAP Main Server
echo "=== Main Server Health Check (CoAP) ==="
echo "Timestamp: $(date)"
echo ""

# Check main server
echo "Main Server Status:"
systemctl is-active main-server-coap && echo "✓ Running" || echo "✗ Not running"
systemctl is-enabled main-server-coap && echo "✓ Enabled" || echo "✗ Not enabled"
echo "Memory usage: $(systemctl show main-server-coap --property=MemoryCurrent --value) bytes"
echo ""

# Check CoAP endpoints
echo "CoAP Health Checks:"
# Test CoAP server with coap-client if available
if command -v coap-client &> /dev/null; then
    coap-client -m get coap://localhost:5683/health && echo "✓ Main Server CoAP responding" || echo "✗ Main Server CoAP not responding"
else
    echo "⚠ coap-client not available, skipping CoAP health checks"
fi
echo ""

# System resources
echo "System Resources:"
echo "CPU usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk usage: $(df -h / | awk 'NR==2{print $5}')"
echo ""

echo "=== Health Check Complete ==="
EOF

chmod +x /opt/management-system/health-check-main-server.sh

# Enable and start service
echo "🚀 Starting main server..."
systemctl daemon-reload
systemctl enable main-server-coap
systemctl start main-server-coap

# Wait for service to be ready
echo "⏳ Waiting for main server to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
systemctl status main-server-coap --no-pager -l
echo ""

# Run health check
echo "🏥 Running health check..."
/opt/management-system/health-check-main-server.sh

echo ""
echo "=========================================="
echo "✅ CoAP Main Server Installation completed!"
echo "=========================================="
echo ""
echo "🌐 Access Points:"
echo "  Main Server CoAP: coap://$(hostname -I | awk '{print $1}'):5683"
echo "  CoAP Resources:"
echo "    - /updates - Update management"
echo "    - /nodes - Node management"
echo "    - /health - Health monitoring"
echo "    - /system - System operations"
echo ""
echo "🔧 Management Commands:"
echo "  Check status: systemctl status main-server-coap"
echo "  View logs: journalctl -u main-server-coap -f"
echo "  Health check: /opt/management-system/health-check-main-server.sh"
echo "  Restart: systemctl restart main-server-coap"
echo "  Stop: systemctl stop main-server-coap"
echo ""
echo "📊 Resource Usage:"
echo "  Main Server: ~200MB RAM, ~0.2 CPU cores"
echo ""
echo "🎯 Main Server ready for ARM Cortex-A55 nodes!"
echo "=========================================="
