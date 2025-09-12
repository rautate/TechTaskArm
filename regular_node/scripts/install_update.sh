#!/bin/bash

# Install Update Script for Regular Node
# This script handles the actual installation of updates

set -e

UPDATE_TYPE="$1"
PACKAGE_NAME="$2"
PACKAGE_VERSION="$3"
PACKAGE_URL="$4"
INSTALL_DIR="/opt/node-updates"

echo "Starting update installation..."
echo "Type: $UPDATE_TYPE"
echo "Package: $PACKAGE_NAME"
echo "Version: $PACKAGE_VERSION"
echo "URL: $PACKAGE_URL"

# Create installation directory
mkdir -p "$INSTALL_DIR"

# Download the package
echo "Downloading package..."
if [[ "$PACKAGE_URL" == http* ]]; then
    wget -O "$INSTALL_DIR/${PACKAGE_NAME}_${PACKAGE_VERSION}.tar.gz" "$PACKAGE_URL"
else
    echo "Invalid package URL: $PACKAGE_URL"
    exit 1
fi

# Extract package
echo "Extracting package..."
cd "$INSTALL_DIR"
tar -xzf "${PACKAGE_NAME}_${PACKAGE_VERSION}.tar.gz"

# Install based on type
case "$UPDATE_TYPE" in
    "service")
        echo "Installing service update..."
        install_service_update "$PACKAGE_NAME" "$PACKAGE_VERSION"
        ;;
    "driver")
        echo "Installing driver update..."
        install_driver_update "$PACKAGE_NAME" "$PACKAGE_VERSION"
        ;;
    "package")
        echo "Installing package update..."
        install_package_update "$PACKAGE_NAME" "$PACKAGE_VERSION"
        ;;
    *)
        echo "Unknown update type: $UPDATE_TYPE"
        exit 1
        ;;
esac

echo "Update installation completed successfully"

# Function to install service update
install_service_update() {
    local service_name="$1"
    local version="$2"
    
    # Stop the service
    systemctl stop "$service_name" || true
    
    # Copy service files
    if [ -d "${PACKAGE_NAME}_${version}" ]; then
        cp -r "${PACKAGE_NAME}_${version}"/* "/opt/services/$service_name/"
    fi
    
    # Copy systemd service file
    if [ -f "${PACKAGE_NAME}_${version}/${service_name}.service" ]; then
        cp "${PACKAGE_NAME}_${version}/${service_name}.service" "/etc/systemd/system/"
    fi
    
    # Reload systemd and start service
    systemctl daemon-reload
    systemctl enable "$service_name"
    systemctl start "$service_name"
    
    # Verify service is running
    if systemctl is-active --quiet "$service_name"; then
        echo "Service $service_name started successfully"
    else
        echo "Failed to start service $service_name"
        exit 1
    fi
}

# Function to install driver update
install_driver_update() {
    local driver_name="$1"
    local version="$2"
    
    # Remove old driver
    rmmod "$driver_name" || true
    
    # Install new driver
    if [ -f "${PACKAGE_NAME}_${version}/${driver_name}.ko" ]; then
        cp "${PACKAGE_NAME}_${version}/${driver_name}.ko" "/lib/modules/$(uname -r)/kernel/drivers/"
        depmod
        modprobe "$driver_name"
    else
        echo "Driver file not found"
        exit 1
    fi
}

# Function to install package update
install_package_update() {
    local package_name="$1"
    local version="$2"
    
    # Update package lists
    apt-get update
    
    # Install package
    if [ -f "${PACKAGE_NAME}_${version}.deb" ]; then
        dpkg -i "${PACKAGE_NAME}_${version}.deb"
    else
        apt-get install -y "$package_name=$version"
    fi
}
