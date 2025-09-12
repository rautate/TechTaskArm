#!/bin/bash

# Rollback Script for Regular Node
# This script handles rollback of failed updates

set -e

JOB_ID="$1"
BACKUP_DIR="/opt/node-backups"
LOG_FILE="/var/log/node-agent/rollback.log"

echo "Starting rollback for job: $JOB_ID" | tee -a "$LOG_FILE"

# Find the backup directory for this job
BACKUP_PATH=$(find "$BACKUP_DIR" -name "*${JOB_ID}*" -type d | head -1)

if [ -z "$BACKUP_PATH" ]; then
    echo "No backup found for job $JOB_ID" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Found backup at: $BACKUP_PATH" | tee -a "$LOG_FILE"

# Restore files from backup
if [ -d "$BACKUP_PATH" ]; then
    echo "Restoring files from backup..." | tee -a "$LOG_FILE"
    
    # Restore service files
    if [ -f "$BACKUP_PATH/${PACKAGE_NAME}.service" ]; then
        cp "$BACKUP_PATH/${PACKAGE_NAME}.service" "/etc/systemd/system/"
        systemctl daemon-reload
        systemctl restart "$PACKAGE_NAME"
        echo "Service files restored" | tee -a "$LOG_FILE"
    fi
    
    # Restore driver files
    if [ -f "$BACKUP_PATH/${PACKAGE_NAME}.ko" ]; then
        rmmod "$PACKAGE_NAME" || true
        cp "$BACKUP_PATH/${PACKAGE_NAME}.ko" "/lib/modules/$(uname -r)/kernel/drivers/"
        depmod
        modprobe "$PACKAGE_NAME"
        echo "Driver files restored" | tee -a "$LOG_FILE"
    fi
    
    # Restore configuration files
    if [ -d "$BACKUP_PATH/config" ]; then
        cp -r "$BACKUP_PATH/config"/* "/etc/"
        echo "Configuration files restored" | tee -a "$LOG_FILE"
    fi
    
    # Restore application files
    if [ -d "$BACKUP_PATH/app" ]; then
        cp -r "$BACKUP_PATH/app"/* "/opt/services/"
        echo "Application files restored" | tee -a "$LOG_FILE"
    fi
else
    echo "Backup directory not found: $BACKUP_PATH" | tee -a "$LOG_FILE"
    exit 1
fi

# Restart affected services
echo "Restarting affected services..." | tee -a "$LOG_FILE"
systemctl daemon-reload

# Try to restart the main service
if systemctl is-enabled "$PACKAGE_NAME" >/dev/null 2>&1; then
    systemctl restart "$PACKAGE_NAME"
    if systemctl is-active --quiet "$PACKAGE_NAME"; then
        echo "Service $PACKAGE_NAME restarted successfully" | tee -a "$LOG_FILE"
    else
        echo "Failed to restart service $PACKAGE_NAME" | tee -a "$LOG_FILE"
    fi
fi

# Clean up temporary files
echo "Cleaning up temporary files..." | tee -a "$LOG_FILE"
rm -rf "/opt/node-updates/${PACKAGE_NAME}_${PACKAGE_VERSION}"

echo "Rollback completed for job: $JOB_ID" | tee -a "$LOG_FILE"
