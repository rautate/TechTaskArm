#!/bin/bash

# systemd-based deployment for Central Service & Driver Management System
# Optimized for ARM Cortex-A55 quad-core devices
# Minimal resource usage: ~200MB RAM, ~0.2 CPU cores

set -e

echo "=========================================="
echo "Central Service & Driver Management System"
echo "systemd-based Deployment for ARM"
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
mkdir -p /opt/management-system/{main-server,regular-node}
mkdir -p /var/log/management-system
mkdir -p /etc/management-system
mkdir -p /opt/node-updates
mkdir -p /opt/node-backups

# Create virtual environments
echo "🐍 Setting up Python environments..."
python3 -m venv /opt/management-system/main-server/venv
python3 -m venv /opt/management-system/regular-node/venv

# Install Python packages
echo "📚 Installing Python dependencies..."
/opt/management-system/main-server/venv/bin/pip install --upgrade pip
/opt/management-system/main-server/venv/bin/pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 aiohttp==3.9.1 pydantic==2.5.0

/opt/management-system/regular-node/venv/bin/pip install --upgrade pip
/opt/management-system/regular-node/venv/bin/pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 aiohttp==3.9.1 psutil==5.9.6

# Copy application files
echo "📋 Copying application files..."
cp -r main_server/* /opt/management-system/main-server/
cp -r regular_node/* /opt/management-system/regular-node/

# Create startup scripts
echo "🚀 Creating startup scripts..."
cat > /opt/management-system/main-server/start.sh << 'EOF'
#!/bin/bash
cd /opt/management-system/main-server
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1
EOF

cat > /opt/management-system/regular-node/start.sh << 'EOF'
#!/bin/bash
cd /opt/management-system/regular-node
source venv/bin/activate
python -m uvicorn agent.main:app --host 0.0.0.0 --port 8081 --workers 1
EOF

chmod +x /opt/management-system/*/start.sh

# Create systemd service files
echo "⚙️ Creating systemd services..."

# Main Server service
cat > /etc/systemd/system/main-server.service << 'EOF'
[Unit]
Description=Central Service & Driver Management System - Main Server
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
SyslogIdentifier=main-server

# Resource limits for ARM optimization
MemoryLimit=512M
CPUQuota=50%

# Environment
Environment=PYTHONPATH=/opt/management-system/main-server
Environment=PYTHONUNBUFFERED=1

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/management-system /var/log/management-system

[Install]
WantedBy=multi-user.target
EOF

# Regular Node service
cat > /etc/systemd/system/regular-node.service << 'EOF'
[Unit]
Description=Central Service & Driver Management System - Regular Node
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
SyslogIdentifier=regular-node

# Resource limits for ARM optimization
MemoryLimit=256M
CPUQuota=25%

# Environment
Environment=PYTHONPATH=/opt/management-system/regular-node
Environment=PYTHONUNBUFFERED=1
Environment=MAIN_SERVER_URL=http://localhost:8080

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
cat > /opt/management-system/health-check.sh << 'EOF'
#!/bin/bash

# Health check script for systemd services
echo "=== Management System Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check main server
echo "Main Server Status:"
systemctl is-active main-server && echo "✓ Running" || echo "✗ Not running"
systemctl is-enabled main-server && echo "✓ Enabled" || echo "✗ Not enabled"
echo "Memory usage: $(systemctl show main-server --property=MemoryCurrent --value) bytes"
echo ""

# Check regular node
echo "Regular Node Status:"
systemctl is-active regular-node && echo "✓ Running" || echo "✗ Not running"
systemctl is-enabled regular-node && echo "✓ Enabled" || echo "✗ Not enabled"
echo "Memory usage: $(systemctl show regular-node --property=MemoryCurrent --value) bytes"
echo ""

# Check API endpoints
echo "API Health Checks:"
curl -s http://localhost:8080/health >/dev/null && echo "✓ Main Server API responding" || echo "✗ Main Server API not responding"
curl -s http://localhost:8081/health >/dev/null && echo "✓ Regular Node API responding" || echo "✗ Regular Node API not responding"
echo ""

# System resources
echo "System Resources:"
echo "CPU usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk usage: $(df -h / | awk 'NR==2{print $5}')"
echo ""

echo "=== Health Check Complete ==="
EOF

chmod +x /opt/management-system/health-check.sh

# Enable and start services
echo "🚀 Starting services..."
systemctl daemon-reload
systemctl enable main-server
systemctl enable regular-node

# Start services with a delay
systemctl start main-server
sleep 5
systemctl start regular-node

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
systemctl status main-server --no-pager -l
echo ""
systemctl status regular-node --no-pager -l
echo ""

# Run health check
echo "🏥 Running health check..."
/opt/management-system/health-check.sh

echo ""
echo "=========================================="
echo "✅ Installation completed successfully!"
echo "=========================================="
echo ""
echo "🌐 Access Points:"
echo "  Main Server API: http://localhost:8080"
echo "  API Documentation: http://localhost:8080/docs"
echo "  Regular Node API: http://localhost:8081"
echo ""
echo "🔧 Management Commands:"
echo "  Check status: systemctl status main-server regular-node"
echo "  View logs: journalctl -u main-server -f"
echo "  View logs: journalctl -u regular-node -f"
echo "  Health check: /opt/management-system/health-check.sh"
echo "  Restart: systemctl restart main-server regular-node"
echo "  Stop: systemctl stop main-server regular-node"
echo ""
echo "📊 Resource Usage:"
echo "  Main Server: ~200MB RAM, ~0.2 CPU cores"
echo "  Regular Node: ~100MB RAM, ~0.1 CPU cores"
echo "  Total: ~300MB RAM, ~0.3 CPU cores"
echo ""
echo "🎯 Optimized for ARM Cortex-A55 quad-core!"
echo "=========================================="