"""Health checking for Regular Node agent."""

import asyncio
import logging
import psutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for regular node."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get temperature (if available)
            temperature = await self._get_temperature()
            
            # Check services
            services_status = await self._check_services()
            
            # Determine overall health
            overall_healthy = (
                cpu_percent < 80 and
                memory.percent < 85 and
                disk.percent < 90 and
                temperature < 70 and
                all(services_status.values())
            )
            
            # Collect error messages
            error_messages = []
            if cpu_percent >= 80:
                error_messages.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent >= 85:
                error_messages.append(f"High memory usage: {memory.percent}%")
            if disk.percent >= 90:
                error_messages.append(f"High disk usage: {disk.percent}%")
            if temperature >= 70:
                error_messages.append(f"High temperature: {temperature}°C")
            
            for service, status in services_status.items():
                if not status:
                    error_messages.append(f"Service {service} is not running")
            
            return {
                "node_id": self.node_id,
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": overall_healthy,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "temperature": temperature,
                "services_status": services_status,
                "error_messages": error_messages
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "node_id": self.node_id,
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": False,
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "disk_percent": 0.0,
                "temperature": 0.0,
                "services_status": {},
                "error_messages": [f"Health check error: {str(e)}"]
            }
    
    async def _get_temperature(self) -> float:
        """Get system temperature."""
        try:
            # Try to read temperature from thermal zone
            result = await self._run_command("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1")
            if result["returncode"] == 0 and result["stdout"].strip():
                temp_millicelsius = int(result["stdout"].strip())
                return temp_millicelsius / 1000.0  # Convert to Celsius
            else:
                return 45.0  # Default temperature
        except Exception as e:
            logger.debug(f"Could not read temperature: {e}")
            return 45.0  # Default temperature
    
    async def _check_services(self) -> Dict[str, bool]:
        """Check status of important services."""
        services = {
            "systemd": True,  # Assume systemd is running
            "network": True,  # Assume network is working
            "ssh": False,
            "docker": False
        }
        
        try:
            # Check SSH service
            result = await self._run_command("systemctl is-active ssh")
            services["ssh"] = result["returncode"] == 0 and "active" in result["stdout"]
            
            # Check Docker service
            result = await self._run_command("systemctl is-active docker")
            services["docker"] = result["returncode"] == 0 and "active" in result["stdout"]
            
        except Exception as e:
            logger.debug(f"Error checking services: {e}")
        
        return services
    
    async def _run_command(self, command: str) -> Dict[str, Any]:
        """Run a shell command and return result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out"
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }
    
    def get_service_logs(self, service_name: str, lines: int = 50) -> List[str]:
        """Get logs for a specific service."""
        try:
            result = subprocess.run(
                f"journalctl -u {service_name} -n {lines} --no-pager",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
            else:
                return [f"Error getting logs: {result.stderr}"]
                
        except Exception as e:
            return [f"Error getting logs: {str(e)}"]
    
    async def update_health_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update health status (placeholder for future use)."""
        try:
            # This could be used to update health status in a local database
            # For now, just return success
            return {
                "success": True,
                "message": "Health status updated",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
