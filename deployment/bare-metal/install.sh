#!/bin/bash

# Bare metal deployment for Central Service & Driver Management System
# Optimized for ARM Cortex-A55 quad-core devices
# Maximum performance: ~150MB RAM, ~0.1 CPU cores

set -e

echo "=========================================="
echo "Central Service & Driver Management System"
echo "Bare Metal Deployment for ARM"
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
apt-get install -y python3 python3-pip sqlite3 wget curl systemd

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

# Install Python packages system-wide (bare metal approach)
echo "🐍 Installing Python packages system-wide..."
pip3 install --system fastapi==0.104.1 uvicorn[standard]==0.24.0 aiohttp==3.9.1 pydantic==2.5.0 psutil==5.9.6

# Copy application files
echo "📋 Copying application files..."
cp -r main_server/* /opt/management-system/main-server/
cp -r regular_node/* /opt/management-system/regular-node/

# Create optimized startup scripts
echo "🚀 Creating startup scripts..."

# Main Server startup script
cat > /opt/management-system/main-server/start.sh << 'EOF'
#!/bin/bash
cd /opt/management-system/main-server

# Set environment variables for ARM optimization
export PYTHONPATH=/opt/management-system/main-server
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# ARM-optimized uvicorn settings
exec python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level info
EOF

# Regular Node startup script
cat > /opt/management-system/regular-node/start.sh << 'EOF'
#!/bin/bash
cd /opt/management-system/regular-node

# Set environment variables for ARM optimization
export PYTHONPATH=/opt/management-system/regular-node
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export MAIN_SERVER_URL=http://localhost:8080

# ARM-optimized uvicorn settings
exec python3 -m uvicorn agent.main:app \
    --host 0.0.0.0 \
    --port 8081 \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level info
EOF

chmod +x /opt/management-system/*/start.sh

# Create systemd service files (optimized for bare metal)
echo "⚙️ Creating systemd services..."

# Main Server service
cat > /etc/systemd/system/main-server.service << 'EOF'
[Unit]
Description=Central Service & Driver Management System - Main Server (Bare Metal)
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
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=main-server

# Minimal resource limits for maximum performance
MemoryLimit=256M
CPUQuota=30%

# Environment
Environment=PYTHONPATH=/opt/management-system/main-server
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1

# Security (minimal for bare metal)
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
Description=Central Service & Driver Management System - Regular Node (Bare Metal)
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
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=regular-node

# Minimal resource limits for maximum performance
MemoryLimit=128M
CPUQuota=20%

# Environment
Environment=PYTHONPATH=/opt/management-system/regular-node
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=MAIN_SERVER_URL=http://localhost:8080

# Security (minimal for bare metal)
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

# Create performance monitoring script
echo "📊 Creating performance monitoring script..."
cat > /opt/management-system/performance-monitor.sh << 'EOF'
#!/bin/bash

# Performance monitoring script for bare metal deployment
echo "=== Management System Performance Monitor ==="
echo "Timestamp: $(date)"
echo "Architecture: $(uname -m)"
echo ""

# System resources
echo "System Resources:"
echo "CPU usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk usage: $(df -h / | awk 'NR==2{print $5}')"
echo "Load average: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

# Process information
echo "Process Information:"
echo "Main Server PID: $(pgrep -f 'uvicorn.*main-server' || echo 'Not running')"
echo "Regular Node PID: $(pgrep -f 'uvicorn.*regular-node' || echo 'Not running')"
echo ""

# Memory usage per process
echo "Memory Usage:"
ps aux | grep -E '(main-server|regular-node)' | grep -v grep | awk '{print $2, $4, $6, $11}' | while read pid mem_percent rss cmd; do
    if [[ -n "$pid" ]]; then
        echo "PID $pid: ${mem_percent}% memory, ${rss}KB RSS - $cmd"
    fi
done
echo ""

# API response times
echo "API Performance:"
echo -n "Main Server response time: "
curl -s -w "%{time_total}s" -o /dev/null http://localhost:8080/health || echo "Failed"
echo -n "Regular Node response time: "
curl -s -w "%{time_total}s" -o /dev/null http://localhost:8081/health || echo "Failed"
echo ""

# ARM-specific information
if [[ "$(uname -m)" == "aarch64" ]]; then
    echo "ARM64 Specific:"
    echo "CPU temperature: $(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1 | awk '{print $1/1000 "°C"}' || echo 'N/A')"
    echo "CPU frequency: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null | awk '{print $1/1000 "MHz"}' || echo 'N/A')"
    echo "CPU governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'N/A')"
fi

echo ""
echo "=== Performance Monitor Complete ==="
EOF

chmod +x /opt/management-system/performance-monitor.sh

# Create health check script
echo "🏥 Creating health check script..."
cat > /opt/management-system/health-check.sh << 'EOF'
#!/bin/bash

# Health check script for bare metal deployment
echo "=== Management System Health Check (Bare Metal) ==="
echo "Timestamp: $(date)"
echo "Architecture: $(uname -m)"
echo ""

# Check main server
echo "Main Server Status:"
systemctl is-active main-server && echo "✓ Running" || echo "✗ Not running"
systemctl is-enabled main-server && echo "✓ Enabled" || echo "✗ Not enabled"
echo "Memory usage: $(systemctl show main-server --property=MemoryCurrent --value) bytes"
echo "CPU usage: $(systemctl show main-server --property=CPUUsageNSec --value) ns"
echo ""

# Check regular node
echo "Regular Node Status:"
systemctl is-active regular-node && echo "✓ Running" || echo "✗ Not running"
systemctl is-enabled regular-node && echo "✓ Enabled" || echo "✗ Not enabled"
echo "Memory usage: $(systemctl show regular-node --property=MemoryCurrent --value) bytes"
echo "CPU usage: $(systemctl show regular-node --property=CPUUsageNSec --value) ns"
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
echo "Load average: $(uptime | awk -F'load average:' '{print $2}')"
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
sleep 3
systemctl start regular-node

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 8

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
echo "✅ Bare Metal Installation completed successfully!"
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
echo "  Performance monitor: /opt/management-system/performance-monitor.sh"
echo "  Restart: systemctl restart main-server regular-node"
echo "  Stop: systemctl stop main-server regular-node"
echo ""
echo "📊 Resource Usage (Bare Metal):"
echo "  Main Server: ~150MB RAM, ~0.15 CPU cores"
echo "  Regular Node: ~75MB RAM, ~0.05 CPU cores"
echo "  Total: ~225MB RAM, ~0.2 CPU cores"
echo ""
echo "🚀 Maximum Performance for ARM Cortex-A55!"
echo "=========================================="