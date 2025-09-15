#!/bin/bash

# CoAP Regular Node deployment for Central Service & Driver Management System
# Optimized for ARM Cortex A55 quad-core devices
# Resource usage: ~100MB RAM, ~0.1 CPU cores

set -e

echo "=========================================="
echo "Central Service & Driver Management System"
echo "CoAP Regular Node Deployment for ARM"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Get main server IP
if [ -z "$MAIN_SERVER_IP" ]; then
    echo "Please provide the main server IP address:"
    echo "Usage: MAIN_SERVER_IP=192.168.1.100 sudo ./install_regular_node.sh"
    echo "Or set MAIN_SERVER_IP environment variable"
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

echo "✓ Main Server IP: $MAIN_SERVER_IP"

# Update system packages
echo "📦 Updating system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv sqlite3 wget curl systemd

# Create system user
echo "👤 Creating system user..."
useradd -r -s /bin/false -d /opt/management-system management-system || echo "User already exists"

# Create application directories
echo "📁 Creating directories..."
mkdir -p /opt/management-system/regular-node
mkdir -p /var/log/management-system
mkdir -p /opt/node-updates
mkdir -p /opt/node-backups

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv /opt/management-system/regular-node/venv

# Install Python packages
echo "📚 Installing Python dependencies..."
/opt/management-system/regular-node/venv/bin/pip install --upgrade pip
/opt/management-system/regular-node/venv/bin/pip install aiocoap==0.4.4 aiohttp==3.9.1 psutil==5.9.6

# Copy application files
echo "📋 Copying application files..."
cp -r regular_node_coap/* /opt/management-system/regular-node/

# Create startup script
echo "🚀 Creating startup script..."
cat > /opt/management-system/regular-node/start.sh << 'EOF'
#!/bin/bash
cd /opt/management-system/regular-node
source venv/bin/activate
python agent/main.py
EOF

chmod +x /opt/management-system/regular-node/start.sh

# Create systemd service file
echo "⚙️ Creating systemd service..."

# Regular Node service
cat > /etc/systemd/system/regular-node-coap.service << EOF
[Unit]
Description=Central Service & Driver Management System - Regular Node (CoAP)
Documentation=https://github.com/your-repo/management-system
After=network.target
Wants=network.target

[Service]
Type=simple
User=management-system
Group=management-system
WorkingDirectory=/opt/management-system/regular-node
ExecStart=/opt/management-system/regular-node/start.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=regular-node-coap

# Resource limits for ARM optimization
MemoryLimit=100M
CPUQuota=10%

# Environment
Environment=PYTHONPATH=/opt/management-system/regular-node
Environment=PYTHONUNBUFFERED=1
Environment=MAIN_SERVER_URL=coap://$MAIN_SERVER_IP:5683
Environment=COAP_HOST=0.0.0.0
Environment=COAP_PORT=5683

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/management-system /var/log/management-system /opt/node-updates /opt/node-backups

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
echo "🔐 Setting permissions..."
chown -R management-system:management-system /opt/management-system
chown -R management-system:management-system /var/log/management-system
chown -R management-system:management-system /opt/node-updates
chown -R management-system:management-system /opt/node-backups

# Create health check script
echo "🏥 Creating health check script..."
cat > /opt/management-system/health-check-regular-node.sh << 'EOF'
#!/bin/bash

# Health check script for CoAP Regular Node
echo "=== Regular Node Health Check (CoAP) ==="
echo "Timestamp: $(date)"
echo ""

# Check regular node
echo "Regular Node Status:"
systemctl is-active regular-node-coap && echo "✓ Running" || echo "✗ Not running"
systemctl is-enabled regular-node-coap && echo "✓ Enabled" || echo "✗ Not enabled"
echo "Memory usage: $(systemctl show regular-node-coap --property=MemoryCurrent --value) bytes"
echo ""

# Check CoAP endpoints
echo "CoAP Health Checks:"
# Test CoAP client with coap-client if available
if command -v coap-client &> /dev/null; then
    coap-client -m get coap://localhost:5683/health && echo "✓ Regular Node CoAP responding" || echo "✗ Regular Node CoAP not responding"
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

chmod +x /opt/management-system/health-check-regular-node.sh

# Enable and start service
echo "🚀 Starting regular node..."
systemctl daemon-reload
systemctl enable regular-node-coap
systemctl start regular-node-coap

# Wait for service to be ready
echo "⏳ Waiting for regular node to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
systemctl status regular-node-coap --no-pager -l
echo ""

# Run health check
echo "🏥 Running health check..."
/opt/management-system/health-check-regular-node.sh

echo ""
echo "=========================================="
echo "✅ CoAP Regular Node Installation completed!"
echo "=========================================="
echo ""
echo "🌐 Access Points:"
echo "  Regular Node CoAP: coap://$(hostname -I | awk '{print $1}'):5683"
echo "  Main Server: coap://$MAIN_SERVER_IP:5683"
echo ""
echo "🔧 Management Commands:"
echo "  Check status: systemctl status regular-node-coap"
echo "  View logs: journalctl -u regular-node-coap -f"
echo "  Health check: /opt/management-system/health-check-regular-node.sh"
echo "  Restart: systemctl restart regular-node-coap"
echo "  Stop: systemctl stop regular-node-coap"
echo ""
echo "📊 Resource Usage:"
echo "  Regular Node: ~100MB RAM, ~0.1 CPU cores"
echo ""
echo "🎯 Regular Node ready for ARM Cortex-A55!"
echo "=========================================="
