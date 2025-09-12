"""Health checking functionality for Regular Node agent."""

import psutil
import subprocess
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs health checks on the regular node."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.services_to_check = [
            "node-agent",
            "docker",
            "systemd-resolved",
            "ssh"
        ]
        self.architecture = self._detect_architecture()
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        try:
            # Check system resources
            system_health = await self._check_system_resources()
            
            # Check services
            services_status = await self._check_services()
            
            # Check disk space
            disk_health = await self._check_disk_space()
            
            # Check network connectivity
            network_health = await self._check_network()
            
            # Overall health assessment
            overall_healthy = (
                system_health["healthy"] and
                all(status["healthy"] for status in services_status.values()) and
                disk_health["healthy"] and
                network_health["healthy"]
            )
            
            health_result = {
                "node_id": self.node_id,
                "timestamp": datetime.now(),
                "architecture": self.architecture,
                "services_status": services_status,
                "system_health": {
                    **system_health,
                    "disk": disk_health,
                    "network": network_health
                },
                "overall_healthy": overall_healthy
            }
            
            logger.info(f"Health check completed for node {self.node_id}: {'HEALTHY' if overall_healthy else 'UNHEALTHY'}")
            return health_result
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "node_id": self.node_id,
                "timestamp": datetime.now(),
                "architecture": self.architecture,
                "services_status": {},
                "system_health": {"error": str(e)},
                "overall_healthy": False
            }
    
    def _detect_architecture(self) -> Dict[str, str]:
        """Detect system architecture and CPU information."""
        try:
            import platform
            import subprocess
            
            # Get basic architecture info
            arch = platform.machine().lower()
            processor = platform.processor()
            
            # Get detailed CPU info for ARM
            cpu_info = {}
            try:
                result = subprocess.run(
                    ["lscpu"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            cpu_info[key.strip()] = value.strip()
            except:
                pass
            
            # Detect ARM-specific details
            if 'arm' in arch or 'aarch64' in arch:
                arm_type = "unknown"
                if 'cortex-a55' in processor.lower():
                    arm_type = "Cortex-A55"
                elif 'cortex-a72' in processor.lower():
                    arm_type = "Cortex-A72"
                elif 'cortex-a78' in processor.lower():
                    arm_type = "Cortex-A78"
                
                return {
                    "architecture": arch,
                    "processor": processor,
                    "arm_type": arm_type,
                    "cores": cpu_info.get("CPU(s)", "unknown"),
                    "model": cpu_info.get("Model name", "unknown"),
                    "is_arm": True
                }
            else:
                return {
                    "architecture": arch,
                    "processor": processor,
                    "cores": cpu_info.get("CPU(s)", "unknown"),
                    "model": cpu_info.get("Model name", "unknown"),
                    "is_arm": False
                }
                
        except Exception as e:
            logger.error(f"Architecture detection failed: {e}")
            return {
                "architecture": "unknown",
                "processor": "unknown",
                "is_arm": False,
                "error": str(e)
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check CPU, memory, and load average."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Load average
            load_avg = psutil.getloadavg()
            
            # Determine if healthy based on thresholds
            healthy = (
                cpu_percent < 90 and  # CPU usage under 90%
                memory_percent < 90 and  # Memory usage under 90%
                load_avg[0] < 4.0  # 1-minute load average under 4.0
            )
            
            return {
                "healthy": healthy,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_available_gb": memory.available / (1024**3),
                "load_avg_1min": load_avg[0],
                "load_avg_5min": load_avg[1],
                "load_avg_15min": load_avg[2]
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    async def _check_services(self) -> Dict[str, Dict[str, Any]]:
        """Check status of critical services."""
        services_status = {}
        
        for service in self.services_to_check:
            try:
                # Check if service is active
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                is_active = result.returncode == 0 and "active" in result.stdout
                
                # Get additional service info
                status_result = subprocess.run(
                    ["systemctl", "show", service, "--property=ActiveState,SubState,LoadState"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                service_info = {}
                if status_result.returncode == 0:
                    for line in status_result.stdout.strip().split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            service_info[key] = value
                
                services_status[service] = {
                    "healthy": is_active,
                    "active": is_active,
                    "state": service_info.get("ActiveState", "unknown"),
                    "substate": service_info.get("SubState", "unknown"),
                    "loaded": service_info.get("LoadState", "unknown")
                }
                
            except subprocess.TimeoutExpired:
                services_status[service] = {
                    "healthy": False,
                    "active": False,
                    "error": "Service check timeout"
                }
            except Exception as e:
                logger.error(f"Service check failed for {service}: {e}")
                services_status[service] = {
                    "healthy": False,
                    "active": False,
                    "error": str(e)
                }
        
        return services_status
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage."""
        try:
            disk_usage = psutil.disk_usage('/')
            
            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            percent_used = (used_gb / total_gb) * 100
            
            # Consider healthy if less than 90% full
            healthy = percent_used < 90
            
            return {
                "healthy": healthy,
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_used": round(percent_used, 2)
            }
            
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    async def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity."""
        try:
            # Check if we can resolve DNS
            dns_result = subprocess.run(
                ["nslookup", "google.com"],
                capture_output=True,
                text=True,
                timeout=10
            )
            dns_healthy = dns_result.returncode == 0
            
            # Check if we can ping a reliable host
            ping_result = subprocess.run(
                ["ping", "-c", "1", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )
            ping_healthy = ping_result.returncode == 0
            
            # Check network interfaces
            interfaces = psutil.net_if_addrs()
            active_interfaces = []
            for interface, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == 2:  # IPv4
                        active_interfaces.append({
                            "interface": interface,
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
            
            healthy = dns_healthy and ping_healthy and len(active_interfaces) > 0
            
            return {
                "healthy": healthy,
                "dns_resolution": dns_healthy,
                "internet_connectivity": ping_healthy,
                "active_interfaces": active_interfaces
            }
            
        except Exception as e:
            logger.error(f"Network check failed: {e}")
            return {"healthy": False, "error": str(e)}
    
    def get_service_logs(self, service_name: str, lines: int = 50) -> str:
        """Get recent logs for a service."""
        try:
            result = subprocess.run(
                ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting logs: {result.stderr}"
                
        except Exception as e:
            return f"Error getting logs: {e}"
    
    def get_system_logs(self, lines: int = 100) -> str:
        """Get recent system logs."""
        try:
            result = subprocess.run(
                ["journalctl", "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting system logs: {result.stderr}"
                
        except Exception as e:
            return f"Error getting system logs: {e}"
