"""Update handling logic for Regular Node agent."""

import os
import subprocess
import logging
import shutil
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class UpdateHandler:
    """Handles update operations on the regular node."""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.update_dir = Path("/opt/node-updates")
        self.backup_dir = Path("/opt/node-backups")
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.architecture = self._detect_architecture()
    
    async def install_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install an update based on the update type."""
        try:
            update_type = update_data.get("update_type")
            package_name = update_data.get("package_name")
            package_version = update_data.get("package_version")
            package_url = update_data.get("package_url")
            
            logger.info(f"Installing {update_type} update: {package_name} v{package_version}")
            
            # Create backup before update
            backup_path = await self._create_backup(package_name, update_type)
            
            # Install based on update type
            if update_type == "service":
                result = await self._install_service_update(package_name, package_version, package_url)
            elif update_type == "driver":
                result = await self._install_driver_update(package_name, package_version, package_url)
            elif update_type == "package":
                result = await self._install_package_update(package_name, package_version, package_url)
            else:
                raise ValueError(f"Unknown update type: {update_type}")
            
            if result["success"]:
                # Run health check after successful update
                health_check_passed = await self._run_health_check()
                result["health_check_passed"] = health_check_passed
                
                if not health_check_passed:
                    logger.warning("Health check failed after update, triggering rollback")
                    await self._rollback_update(backup_path, package_name, update_type)
                    return {
                        "success": False,
                        "error_message": "Health check failed after update",
                        "rolled_back": True
                    }
            else:
                # Update failed, restore backup
                await self._rollback_update(backup_path, package_name, update_type)
            
            return result
            
        except Exception as e:
            logger.error(f"Update installation failed: {e}")
            return {
                "success": False,
                "error_message": str(e)
            }
    
    async def _create_backup(self, package_name: str, update_type: str) -> str:
        """Create a backup of the current state before update."""
        try:
            backup_name = f"{package_name}_{update_type}_{int(time.time())}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            if update_type == "service":
                # Backup service files and configuration
                service_files = [
                    f"/etc/systemd/system/{package_name}.service",
                    f"/opt/services/{package_name}",
                    f"/etc/{package_name}"
                ]
                
                for file_path in service_files:
                    if os.path.exists(file_path):
                        dest = backup_path / Path(file_path).name
                        if os.path.isdir(file_path):
                            shutil.copytree(file_path, dest)
                        else:
                            shutil.copy2(file_path, dest)
            
            elif update_type == "driver":
                # Backup driver files
                driver_files = [
                    f"/lib/modules/$(uname -r)/kernel/drivers/{package_name}",
                    f"/etc/modprobe.d/{package_name}.conf"
                ]
                
                for file_path in driver_files:
                    if os.path.exists(file_path):
                        dest = backup_path / Path(file_path).name
                        if os.path.isdir(file_path):
                            shutil.copytree(file_path, dest)
                        else:
                            shutil.copy2(file_path, dest)
            
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    async def _install_service_update(self, package_name: str, version: str, package_url: str) -> Dict[str, Any]:
        """Install a service update."""
        try:
            # Stop the service
            await self._run_command(f"systemctl stop {package_name}")
            
            # Download and install the update
            if package_url.startswith("http"):
                # Download from URL
                download_path = self.update_dir / f"{package_name}_{version}.tar.gz"
                await self._download_file(package_url, download_path)
                
                # Extract and install
                extract_dir = self.update_dir / f"{package_name}_{version}"
                await self._run_command(f"tar -xzf {download_path} -C {self.update_dir}")
                
                # Copy files to target location
                if extract_dir.exists():
                    await self._run_command(f"cp -r {extract_dir}/* /opt/services/{package_name}/")
            
            # Reload systemd and start service
            await self._run_command("systemctl daemon-reload")
            await self._run_command(f"systemctl enable {package_name}")
            await self._run_command(f"systemctl start {package_name}")
            
            # Verify service is running
            result = await self._run_command(f"systemctl is-active {package_name}")
            if result["returncode"] == 0 and "active" in result["stdout"]:
                return {"success": True, "message": f"Service {package_name} updated successfully"}
            else:
                return {"success": False, "error_message": "Service failed to start after update"}
                
        except Exception as e:
            logger.error(f"Service update failed: {e}")
            return {"success": False, "error_message": str(e)}
    
    async def _install_driver_update(self, package_name: str, version: str, package_url: str) -> Dict[str, Any]:
        """Install a driver update."""
        try:
            # Download driver
            if package_url.startswith("http"):
                download_path = self.update_dir / f"{package_name}_{version}.ko"
                await self._download_file(package_url, download_path)
                
                # Install driver
                driver_path = f"/lib/modules/$(uname -r)/kernel/drivers/{package_name}.ko"
                await self._run_command(f"cp {download_path} {driver_path}")
                await self._run_command("depmod")
                await self._run_command(f"modprobe {package_name}")
            
            return {"success": True, "message": f"Driver {package_name} updated successfully"}
            
        except Exception as e:
            logger.error(f"Driver update failed: {e}")
            return {"success": False, "error_message": str(e)}
    
    async def _install_package_update(self, package_name: str, version: str, package_url: str) -> Dict[str, Any]:
        """Install a package update using system package manager."""
        try:
            # Update package lists
            await self._run_command("apt-get update")
            
            # Install or upgrade package
            if package_url.startswith("http"):
                # Download and install from URL
                # Handle ARM-specific package naming
                if self.architecture == 'arm64':
                    # Try ARM64 package first, fallback to generic
                    arm_url = package_url.replace('.deb', f'_arm64.deb')
                    download_path = self.update_dir / f"{package_name}_{version}_arm64.deb"
                else:
                    download_path = self.update_dir / f"{package_name}_{version}.deb"
                
                await self._download_file(package_url, download_path)
                await self._run_command(f"dpkg -i {download_path}")
            else:
                # Install from repository - ARM packages are usually available
                await self._run_command(f"apt-get install -y {package_name}={version}")
            
            return {"success": True, "message": f"Package {package_name} updated successfully on {self.architecture}"}
            
        except Exception as e:
            logger.error(f"Package update failed: {e}")
            return {"success": False, "error_message": str(e)}
    
    async def _download_file(self, url: str, destination: Path) -> None:
        """Download a file from URL."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(destination, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                else:
                    raise Exception(f"Failed to download file: HTTP {response.status}")
    
    async def _run_command(self, command: str) -> Dict[str, Any]:
        """Run a shell command and return result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
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
    
    async def _run_health_check(self) -> bool:
        """Run health check after update."""
        try:
            # Run the health check script
            result = await self._run_command("/opt/node-agent/scripts/health_check.sh")
            return result["returncode"] == 0
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def _rollback_update(self, backup_path: str, package_name: str, update_type: str) -> None:
        """Rollback an update using backup."""
        try:
            logger.info(f"Rolling back update for {package_name}")
            
            if update_type == "service":
                # Stop service
                await self._run_command(f"systemctl stop {package_name}")
                
                # Restore files
                backup_dir = Path(backup_path)
                for item in backup_dir.iterdir():
                    if item.is_file():
                        dest = Path(f"/etc/systemd/system/{item.name}")
                        shutil.copy2(item, dest)
                    elif item.is_dir():
                        dest = Path(f"/opt/services/{item.name}")
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                
                # Restart service
                await self._run_command("systemctl daemon-reload")
                await self._run_command(f"systemctl start {package_name}")
            
            elif update_type == "driver":
                # Remove new driver and restore old one
                await self._run_command(f"rmmod {package_name}")
                
                backup_dir = Path(backup_path)
                for item in backup_dir.iterdir():
                    if item.is_file():
                        dest = Path(f"/lib/modules/$(uname -r)/kernel/drivers/{item.name}")
                        shutil.copy2(item, dest)
                
                await self._run_command("depmod")
                await self._run_command(f"modprobe {package_name}")
            
            logger.info(f"Rollback completed for {package_name}")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise
    
    def _detect_architecture(self) -> str:
        """Detect system architecture for ARM-specific handling."""
        try:
            import platform
            arch = platform.machine().lower()
            if 'arm' in arch or 'aarch64' in arch:
                return 'arm64'
            elif 'x86_64' in arch or 'amd64' in arch:
                return 'amd64'
            else:
                return arch
        except:
            return 'unknown'


# Import time module for backup naming
import time
