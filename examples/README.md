# IoT Update System Examples

This directory contains examples and test scripts for both MQTT+HTTP and CoAP IoT update systems, optimized for ARM Cortex A55 devices.

## 📁 Files

### Test Scripts
- `coap_test.py` - Test script for pure CoAP system

### Configuration Examples
- `coap_config.json` - CoAP server configuration example

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- CoAP server (for CoAP tests)
- ARM Cortex A55 device or emulator

### CoAP System Testing

1. **Install dependencies:**
   ```bash
   pip install aiocoap
   ```

2. **Start the CoAP system:**
   ```bash
   sudo ./deployment/coap/install.sh
   ```

3. **Run tests:**
   ```bash
   python examples/coap_test.py
   ```

## 🧪 Test Coverage

### CoAP Tests
- ✅ Health check endpoint
- ✅ Node registration
- ✅ Update creation
- ✅ Update status checking
- ✅ Node health update
- ✅ System operations
- ✅ Block transfer (firmware download)

## 📊 Performance Comparison

| Feature | MQTT + HTTP | CoAP |
|---------|-------------|------|
| Memory Usage | ~578MB | ~300MB |
| CPU Usage | ~0.6 cores | ~0.3 cores |
| Protocol Overhead | ~2KB (MQTT) + HTTP | ~4 bytes |
| Security | TLS + MQTT security | Built-in DTLS |
| Large Files | HTTP download | Block transfer |
| Real-time | MQTT pub/sub | Observing |
| Complexity | High | Medium |
| Reliability | TCP-based | UDP-based |

## 🔧 Configuration Examples

### CoAP Server Configuration
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5683,
    "dtls_port": 5684,
    "max_connections": 1000,
    "block_size": 1024
  },
  "resources": {
    "updates": "/updates",
    "nodes": "/nodes",
    "health": "/health",
    "system": "/system"
  }
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **CoAP Connection Failed**
   - Check if CoAP server is running
   - Verify UDP port 5683 is open
   - Check network connectivity

2. **ARM Architecture Issues**
   - Ensure ARM64 packages are available
   - Check Python dependencies compatibility
   - Verify system architecture detection

### Debug Commands

```bash
# Check CoAP server status
systemctl status main-server-coap

# View logs
journalctl -u main-server-coap -f

# Test CoAP connection
coap-client -m get coap://localhost:5683/health
```

## 📈 Monitoring

### Health Check Endpoints
- **CoAP**: `coap://localhost:5683/health`

### Resource Monitoring
```bash
# Check system resources
htop

# Check memory usage
free -h

# Check disk usage
df -h

# Check network connections
netstat -tulpn
```

## 🔒 Security Considerations

### CoAP Security
- Use DTLS for secure communication
- Implement certificate management
- Use mutual TLS authentication
- Secure firmware storage

## 📚 Additional Resources

- [CoAP Protocol Specification](https://tools.ietf.org/html/rfc7252)
- [ARM Cortex A55 Documentation](https://developer.arm.com/ip-products/processors/cortex-a/cortex-a55)
