#!/bin/bash

# Health Check Script for Regular Node
# This script performs comprehensive health checks

set -e

LOG_FILE="/var/log/node-agent/health_check.log"
HEALTH_STATUS=0

echo "Starting health check at $(date)" | tee -a "$LOG_FILE"

# Function to check service status
check_service() {
    local service_name="$1"
    if systemctl is-active --quiet "$service_name"; then
        echo "✓ Service $service_name is running" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ Service $service_name is not running" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    local threshold=90
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt "$threshold" ]; then
        echo "✓ Disk usage is $usage% (under $threshold%)" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ Disk usage is $usage% (over $threshold%)" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to check memory usage
check_memory() {
    local threshold=90
    local usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$usage" -lt "$threshold" ]; then
        echo "✓ Memory usage is $usage% (under $threshold%)" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ Memory usage is $usage% (over $threshold%)" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to check CPU load
check_cpu_load() {
    local threshold=4.0
    local load=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
    
    if (( $(echo "$load < $threshold" | bc -l) )); then
        echo "✓ CPU load is $load (under $threshold)" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ CPU load is $load (over $threshold)" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to check network connectivity
check_network() {
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        echo "✓ Network connectivity is working" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ Network connectivity is not working" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to check DNS resolution
check_dns() {
    if nslookup google.com >/dev/null 2>&1; then
        echo "✓ DNS resolution is working" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ DNS resolution is not working" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Function to check critical processes
check_processes() {
    local processes=("node-agent" "systemd" "docker")
    local all_good=true
    
    for process in "${processes[@]}"; do
        if pgrep "$process" >/dev/null; then
            echo "✓ Process $process is running" | tee -a "$LOG_FILE"
        else
            echo "✗ Process $process is not running" | tee -a "$LOG_FILE"
            all_good=false
        fi
    done
    
    if [ "$all_good" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to check system logs for errors
check_system_logs() {
    local error_count=$(journalctl --since "1 hour ago" --priority=err --no-pager | wc -l)
    
    if [ "$error_count" -lt 10 ]; then
        echo "✓ System logs show $error_count errors in the last hour (acceptable)" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ System logs show $error_count errors in the last hour (too many)" | tee -a "$LOG_FILE"
        return 1
    fi
}

# Run all health checks
echo "Running health checks..." | tee -a "$LOG_FILE"

# Check critical services
echo "Checking services..." | tee -a "$LOG_FILE"
check_service "node-agent" || HEALTH_STATUS=1
check_service "docker" || HEALTH_STATUS=1
check_service "systemd-resolved" || HEALTH_STATUS=1

# Check system resources
echo "Checking system resources..." | tee -a "$LOG_FILE"
check_disk_space || HEALTH_STATUS=1
check_memory || HEALTH_STATUS=1
check_cpu_load || HEALTH_STATUS=1

# Check network
echo "Checking network..." | tee -a "$LOG_FILE"
check_network || HEALTH_STATUS=1
check_dns || HEALTH_STATUS=1

# Check processes
echo "Checking processes..." | tee -a "$LOG_FILE"
check_processes || HEALTH_STATUS=1

# Check system logs
echo "Checking system logs..." | tee -a "$LOG_FILE"
check_system_logs || HEALTH_STATUS=1

# Final status
if [ $HEALTH_STATUS -eq 0 ]; then
    echo "✓ All health checks passed" | tee -a "$LOG_FILE"
    echo "HEALTHY" > /tmp/health_status
else
    echo "✗ Some health checks failed" | tee -a "$LOG_FILE"
    echo "UNHEALTHY" > /tmp/health_status
fi

echo "Health check completed at $(date)" | tee -a "$LOG_FILE"
exit $HEALTH_STATUS
