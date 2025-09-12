#!/bin/bash

# Uninstall script for systemd-based deployment

set -e

echo "=========================================="
echo "Uninstalling Management System (systemd)"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Stop and disable services
echo "🛑 Stopping services..."
systemctl stop main-server regular-node || true
systemctl disable main-server regular-node || true

# Remove systemd service files
echo "🗑️ Removing systemd services..."
rm -f /etc/systemd/system/main-server.service
rm -f /etc/systemd/system/regular-node.service
systemctl daemon-reload

# Remove application files
echo "📁 Removing application files..."
rm -rf /opt/management-system
rm -rf /var/log/management-system
rm -rf /etc/management-system

# Remove system user
echo "👤 Removing system user..."
userdel management-system || true

# Remove directories
echo "🗑️ Removing directories..."
rm -rf /opt/node-updates
rm -rf /opt/node-backups

echo "✅ Uninstallation completed!"
echo "=========================================="
