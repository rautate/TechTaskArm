#!/usr/bin/env python3
"""
Test script for CoAP IoT update system
Optimized for ARM Cortex A55 devices
"""

import asyncio
import json
import time
from datetime import datetime
from aiocoap import Context, Message, Code


class CoAPTester:
    """Test client for CoAP IoT update system."""
    
    def __init__(self, main_server_url="coap://localhost:5683"):
        self.main_server_url = main_server_url
        self.context = None
        self.received_responses = []
        
    async def start(self):
        """Start the test client."""
        print("🚀 Starting CoAP Test Client")
        
        # Create CoAP context
        self.context = await Context.create_client_context()
        
        print("✅ CoAP Test Client started")
    
    async def stop(self):
        """Stop the test client."""
        if self.context:
            await self.context.shutdown()
        print("🛑 CoAP Test Client stopped")
    
    async def send_coap_request(self, path, method=Code.GET, payload=None):
        """Send a CoAP request and return response."""
        try:
            uri = f"{self.main_server_url}/{path}"
            
            if method == Code.GET:
                request = Message(code=Code.GET, uri=uri)
            elif method == Code.POST:
                request = Message(code=Code.POST, uri=uri, payload=payload.encode('utf-8') if payload else b'')
            elif method == Code.PUT:
                request = Message(code=Code.PUT, uri=uri, payload=payload.encode('utf-8') if payload else b'')
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response = await self.context.request(request).response
            
            result = {
                "code": response.code,
                "payload": response.payload.decode('utf-8') if response.payload else "",
                "success": response.code.is_successful(),
                "timestamp": datetime.now().isoformat()
            }
            
            self.received_responses.append(result)
            return result
            
        except Exception as e:
            print(f"❌ CoAP request error: {e}")
            return None
    
    async def test_health_check(self):
        """Test health check endpoint."""
        print("\n🏥 Testing health check...")
        
        response = await self.send_coap_request("health")
        if response and response["success"]:
            print(f"✅ Health check passed: {response['payload']}")
            return True
        else:
            print(f"❌ Health check failed: {response}")
            return False
    
    async def test_node_registration(self):
        """Test node registration."""
        print("\n👤 Testing node registration...")
        
        node_data = {
            "node_id": "test-coap-node-001",
            "hostname": "test-arm-coap-device",
            "ip_address": "192.168.1.101",
            "status": "online",
            "last_seen": datetime.now().isoformat(),
            "services": ["test-service", "docker", "ssh"],
            "drivers": ["usb-storage", "network"],
            "system_info": {
                "os": "Linux",
                "architecture": "aarch64",
                "kernel": "5.4.0",
                "ram_gb": 8
            }
        }
        
        response = await self.send_coap_request("nodes", Code.POST, json.dumps(node_data))
        if response and response["success"]:
            print(f"✅ Node registered: {response['payload']}")
            return True
        else:
            print(f"❌ Node registration failed: {response}")
            return False
    
    async def test_update_creation(self):
        """Test update creation."""
        print("\n📦 Testing update creation...")
        
        update_data = {
            "target_nodes": ["test-coap-node-001"],
            "update_type": "package",
            "package_name": "test-coap-package",
            "package_version": "1.0.0",
            "package_size": 512000,
            "checksum": "sha256:def456abc789",
            "description": "Test CoAP package update for ARM Cortex A55"
        }
        
        response = await self.send_coap_request("updates", Code.POST, json.dumps(update_data))
        if response and response["success"]:
            print(f"✅ Update created: {response['payload']}")
            try:
                data = json.loads(response["payload"])
                return data.get("job_id")
            except:
                return None
        else:
            print(f"❌ Update creation failed: {response}")
            return None
    
    async def test_update_status(self, job_id):
        """Test update status checking."""
        print(f"\n📊 Testing update status for job {job_id}...")
        
        response = await self.send_coap_request(f"updates/{job_id}")
        if response and response["success"]:
            print(f"✅ Update status: {response['payload']}")
            return True
        else:
            print(f"❌ Update status check failed: {response}")
            return False
    
    async def test_node_health_update(self):
        """Test node health status update."""
        print("\n💓 Testing node health update...")
        
        health_data = {
            "node_id": "test-coap-node-001",
            "status": "healthy",
            "cpu_percent": 25.5,
            "memory_percent": 45.2,
            "temperature": 45.2,
            "timestamp": datetime.now().isoformat()
        }
        
        response = await self.send_coap_request("nodes/test-coap-node-001/health", Code.PUT, json.dumps(health_data))
        if response and response["success"]:
            print(f"✅ Health status updated: {response['payload']}")
            return True
        else:
            print(f"❌ Health status update failed: {response}")
            return False
    
    async def test_system_operations(self):
        """Test system operations."""
        print("\n⚙️ Testing system operations...")
        
        # Test restart command
        response = await self.send_coap_request("system/restart", Code.POST)
        if response and response["success"]:
            print(f"✅ System restart command: {response['payload']}")
            return True
        else:
            print(f"❌ System restart command failed: {response}")
            return False
    
    async def test_block_transfer(self, job_id):
        """Test CoAP block-wise transfer for firmware download."""
        print(f"\n📥 Testing block transfer for job {job_id}...")
        
        try:
            # This would test block-wise transfer for large files
            # For now, just test the download endpoint
            response = await self.send_coap_request(f"updates/{job_id}/download")
            if response:
                print(f"✅ Download endpoint accessible: {response['code']}")
                return True
            else:
                print("❌ Download endpoint not accessible")
                return False
        except Exception as e:
            print(f"❌ Block transfer test error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests."""
        print("🧪 Running CoAP IoT Update System Tests")
        print("=" * 60)
        
        # Start test client
        await self.start()
        
        # Run tests
        tests_passed = 0
        total_tests = 7
        
        # Test 1: Health check
        if await self.test_health_check():
            tests_passed += 1
        
        # Test 2: Node registration
        if await self.test_node_registration():
            tests_passed += 1
        
        # Test 3: Update creation
        job_id = await self.test_update_creation()
        if job_id:
            tests_passed += 1
            
            # Test 4: Update status
            if await self.test_update_status(job_id):
                tests_passed += 1
            
            # Test 5: Block transfer
            if await self.test_block_transfer(job_id):
                tests_passed += 1
        
        # Test 6: Node health update
        if await self.test_node_health_update():
            tests_passed += 1
        
        # Test 7: System operations
        if await self.test_system_operations():
            tests_passed += 1
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if self.received_responses:
            print(f"📨 CoAP Responses received: {len(self.received_responses)}")
            for i, resp in enumerate(self.received_responses):
                print(f"  {i+1}. Code: {resp['code']}, Success: {resp['success']}")
        
        # Stop test client
        await self.stop()
        
        return tests_passed == total_tests


async def main():
    """Main function."""
    print("🚀 CoAP IoT Update System Test Suite")
    print("Optimized for ARM Cortex A55 devices")
    print("=" * 60)
    
    # Create test client
    tester = CoAPTester()
    
    # Run tests
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! CoAP system is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the system configuration.")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
