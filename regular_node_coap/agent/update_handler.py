"""CoAP-based update handling for Regular Node agent."""

import asyncio
import logging
import os
import subprocess
import shutil
import aiohttp
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
from aiocoap import Context, Message, Code
import json

logger = logging.getLogger(__name__)


class CoAPUpdateHandler:
    """Handles update operations on the regular node using CoAP."""
    
    def __init__(self, node_id: str, main_server_url: str):
        self.node_id = node_id
        self.main_server_url = main_server_url
        self.update_dir = Path("/opt/node-updates")
        self.backup_dir = Path("/opt/node-backups")
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.architecture = self._detect_architecture()
        self.active_updates = {}  # Track active updates
    
    async def handle_update_available(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update available notification."""
        try:
            update_id = update_data.get('update_id')
            logger.info(f"Update available: {update_id}")
            
            # Store update data
            self.active_updates[update_id] = update_data
            
            # Acknowledge the update
            await self._send_coap_message(
                f"updates/{self.node_id}/ack",
                {
                    "job_id": update_id,
                    "status": "acknowledged",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {"success": True, "message": "Update acknowledged"}
            
        except Exception as e:
            logger.error(f"Error handling update available: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start the update process."""
        try:
            update_id = update_data.get('job_id')
            logger.info(f"Starting update process for job: {update_id}")
            
            # Get update data
            if update_id not in self.active_updates:
                return {"success": False, "error": "Update not found"}
            
            update_info = self.active_updates[update_id]
            
            # Start update process asynchronously
            asyncio.create_task(self._process_update(update_id, update_info))
            
            return {"success": True, "message": "Update process started"}
            
        except Exception as e:
            logger.error(f"Error starting update: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_update(self, update_id: str, update_info: Dict[str, Any]):
        """Process the update installation."""
        try:
            # Report progress
            await self._send_coap_message(
                f"updates/{self.node_id}/progress",
                {
                    "job_id": update_id,
                    "status": "started",
                    "progress": 0,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Install the update
            result = await self.install_update(update_info)
            
            # Report completion
            if result["success"]:
                await self._send_coap_message(
                    f"updates/{self.node_id}/complete",
                    {
                        "job_id": update_id,
                        "success": True,
                        "health_check_passed": result.get('health_check_passed', False),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            else:
                await self._send_coap_message(
                    f"updates/{self.node_id}/failed",
                    {
                        "job_id": update_id,
                        "success": False,
                        "error_message": result.get('error_message', 'Unknown error'),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            # Clean up
            if update_id in self.active_updates:
                del self.active_updates[update_id]
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            await self._send_coap_message(
                f"updates/{self.node_id}/failed",
                {
                    "job_id": update_id,
                    "success": False,
                    "error_message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    async def install_update(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Install an update based on the update type."""
        try:
            update_id = update_data.get('update_id')
            update_type = update_data.get('update_type', 'package')
            package_name = update_data.get('package_name')
            package_version = update_data.get('version')
            download_url = update_data.get('download_url')
            checksum = update_data.get('checksum')
            
            logger.info(f"Installing {update_type} update: {package_name} v{package_version}")
            
            # Create backup before update
            backup_path = await self._create_backup(package_name, update_type)
            
            # Download the update package
            download_path = await self._download_update(download_url, package_name, package_version)
            
            # Verify checksum if provided
            if checksum and not await self._verify_checksum(download_path, checksum):
                raise Exception("Checksum verification failed")
            
            # Install based on update type
            if update_type == "service":
                result = await self._install_service_update(package_name, package_version, download_path)
            elif update_type == "driver":
                result = await self._install_driver_update(package_name, package_version, download_path)
            elif update_type == "package":
                result = await self._install_package_update(package_name, package_version, download_path)
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
    
    async def _download_update(self, download_url: str, package_name: str, version: str) -> Path:
        """Download update package from CoAP URL."""
        try:
            # Create download path
            if download_url.endswith('.deb'):
                download_path = self.update_dir / f"{package_name}_{version}.deb"
            elif download_url.endswith('.tar.gz'):
                download_path = self.update_dir / f"{package_name}_{version}.tar.gz"
            elif download_url.endswith('.ko'):
                download_path = self.update_dir / f"{package_name}_{version}.ko"
            else:
                download_path = self.update_dir / f"{package_name}_{version}"
            
            logger.info(f"Downloading update from {download_url}")
            
            # Download file using CoAP
            context = await Context.create_client_context()
            request = Message(code=Code.GET, uri=download_url)
            
            response = await context.request(request).response
            
            if response.code.is_successful():
                with open(download_path, 'wb') as f:
                    f.write(response.payload)
                logger.info(f"Download completed: {download_path}")
                return download_path
            else:
                raise Exception(f"Failed to download file: CoAP {response.code}")
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            raise
    
    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum."""
        try:
            if not expected_checksum:
                return True
            
            # Extract algorithm and hash
            if ':' in expected_checksum:
                algorithm, hash_value = expected_checksum.split(':', 1)
            else:
                algorithm = 'sha256'
                hash_value = expected_checksum
            
            # Calculate file hash
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            
            calculated_hash = hash_obj.hexdigest()
            is_valid = calculated_hash == hash_value
            
            if is_valid:
                logger.info(f"Checksum verification passed: {algorithm}")
            else:
                logger.error(f"Checksum verification failed: expected {hash_value}, got {calculated_hash}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying checksum: {e}")
            return False
    
    async def _create_backup(self, package_name: str, update_type: str) -> str:
        """Create a backup of the current state before update."""
        try:
            import time
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
    
    async def _install_service_update(self, package_name: str, version: str, download_path: Path) -> Dict[str, Any]:
        """Install a service update."""
        try:
            # Stop the service
            await self._run_command(f"systemctl stop {package_name}")
            
            # Extract and install based on file type
            if download_path.suffix == '.tar.gz':
                # Extract tar.gz
                extract_dir = self.update_dir / f"{package_name}_{version}"
                await self._run_command(f"tar -xzf {download_path} -C {self.update_dir}")
                
                # Copy files to target location
                if extract_dir.exists():
                    await self._run_command(f"cp -r {extract_dir}/* /opt/services/{package_name}/")
            elif download_path.suffix == '.deb':
                # Install .deb package
                await self._run_command(f"dpkg -i {download_path}")
            
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
    
    async def _install_driver_update(self, package_name: str, version: str, download_path: Path) -> Dict[str, Any]:
        """Install a driver update."""
        try:
            # Remove old driver if loaded
            await self._run_command(f"rmmod {package_name}")
            
            # Install new driver
            driver_path = f"/lib/modules/$(uname -r)/kernel/drivers/{package_name}.ko"
            await self._run_command(f"cp {download_path} {driver_path}")
            await self._run_command("depmod")
            await self._run_command(f"modprobe {package_name}")
            
            return {"success": True, "message": f"Driver {package_name} updated successfully"}
            
        except Exception as e:
            logger.error(f"Driver update failed: {e}")
            return {"success": False, "error_message": str(e)}
    
    async def _install_package_update(self, package_name: str, version: str, download_path: Path) -> Dict[str, Any]:
        """Install a package update using system package manager."""
        try:
            # Update package lists
            await self._run_command("apt-get update")
            
            # Install based on file type
            if download_path.suffix == '.deb':
                # Install .deb package
                await self._run_command(f"dpkg -i {download_path}")
            else:
                # Install from repository - ARM packages are usually available
                await self._run_command(f"apt-get install -y {package_name}={version}")
            
            return {"success": True, "message": f"Package {package_name} updated successfully on {self.architecture}"}
            
        except Exception as e:
            logger.error(f"Package update failed: {e}")
            return {"success": False, "error_message": str(e)}
    
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
    
    async def _send_coap_message(self, path: str, data: Dict[str, Any]) -> bool:
        """Send a CoAP message to the main server."""
        try:
            context = await Context.create_client_context()
            
            request = Message(
                code=Code.POST,
                uri=f"coap://main-server:5683/{path}",
                payload=json.dumps(data).encode('utf-8')
            )
            
            response = await context.request(request).response
            
            if response.code.is_successful():
                logger.debug(f"CoAP message sent successfully to {path}")
                return True
            else:
                logger.error(f"CoAP message failed: {response.code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending CoAP message: {e}")
            return False
    
    def get_update_status(self, update_id: str) -> Dict[str, Any]:
        """Get update status."""
        if update_id in self.active_updates:
            return {
                "update_id": update_id,
                "status": "in_progress",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "update_id": update_id,
                "status": "not_found",
                "timestamp": datetime.now().isoformat()
            }
    
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


# Import datetime for timestamp
from datetime import datetime
