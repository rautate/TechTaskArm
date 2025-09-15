# CoAP IoT Update System Deployment Guide

## 🎯 **Deployment Overview**

This guide explains how to deploy the CoAP-based IoT update system across your ARM Cortex A55 infrastructure.

## 📋 **Prerequisites**

- ARM Cortex A55 devices (or compatible ARM64)
- Ubuntu 20.04+ or Debian 11+
- Root access on all devices
- Network connectivity between devices
- Python 3.9+

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN SERVER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   CoAP      │  │   CoAP      │  │   CoAP      │            │
│  │   SERVER    │  │   PROXY     │  │   OBSERVE   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   DATABASE  │  │   UPDATE    │  │   FIRMWARE  │            │
│  │  (SQLite)   │  │  MANAGER    │  │   STORAGE   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │ CoAP Messages (UDP:5683)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REGULAR NODES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   NODE 1    │  │   NODE 2    │  │   NODE N    │            │
│  │   (CoAP)    │  │   (CoAP)    │  │   (CoAP)    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  SERVICES   │  │  SERVICES   │  │  SERVICES   │            │
│  │  & DRIVERS  │  │  & DRIVERS  │  │  & DRIVERS  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 **Step-by-Step Deployment**

### **Step 1: Deploy Main Server**

1. **Copy files to main server:**
   ```bash
   # On main server
   scp -r main_server_coap/ user@main-server:/tmp/
   scp deployment/coap/install_main_server.sh user@main-server:/tmp/
   ```

2. **Run main server installation:**
   ```bash
   # On main server
   sudo chmod +x /tmp/install_main_server.sh
   sudo /tmp/install_main_server.sh
   ```

3. **Verify main server:**
   ```bash
   # Check service status
   sudo systemctl status main-server-coap
   
   # Check CoAP endpoint
   coap-client -m get coap://localhost:5683/health
   ```

### **Step 2: Deploy Regular Nodes**

1. **Copy files to each regular node:**
   ```bash
   # On each regular node
   scp -r regular_node_coap/ user@node:/tmp/
   scp deployment/coap/install_regular_node.sh user@node:/tmp/
   ```

2. **Run regular node installation:**
   ```bash
   # On each regular node
   sudo chmod +x /tmp/install_regular_node.sh
   MAIN_SERVER_IP=192.168.1.100 sudo /tmp/install_regular_node.sh
   ```
   
   Replace `192.168.1.100` with your actual main server IP address.

3. **Verify regular node:**
   ```bash
   # Check service status
   sudo systemctl status regular-node-coap
   
   # Check CoAP endpoint
   coap-client -m get coap://localhost:5683/health
   ```

### **Step 3: Test the System**

2. **Verify node registration:**
   ```bash
   # Check registered nodes
   coap-client -m get coap://localhost:5683/nodes
   ```

## 🔧 **Configuration**

### **Main Server Configuration**

The main server runs on:
- **CoAP Port**: 5683 (UDP)
- **DTLS Port**: 5684 (UDP, if enabled)
- **Resource Paths**:
  - `/updates` - Update management
  - `/nodes` - Node management
  - `/health` - Health monitoring
  - `/system` - System operations

### **Regular Node Configuration**

Each regular node:
- **Connects to**: Main server CoAP endpoint
- **Runs on**: Port 5683 (UDP)
- **Registers with**: Main server on startup
- **Reports health**: Every 60 seconds

## 📊 **Resource Usage**

### **Main Server**
- **RAM**: ~200MB
- **CPU**: ~0.2 cores
- **Storage**: ~100MB + firmware files

### **Regular Node**
- **RAM**: ~100MB
- **CPU**: ~0.1 cores
- **Storage**: ~50MB + update files

## 🔒 **Security Configuration**

### **Enable DTLS (Optional)**

1. **Generate certificates:**
   ```bash
   # On main server
   openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes
   ```

2. **Configure DTLS in CoAP server:**
   ```python
   # In main_server_coap/app/main.py
   context = await Context.create_server_context(
       bind=("0.0.0.0", 5684),
       server_credentials=load_certificate_chain("server.crt"),
       private_key=load_private_key("server.key")
   )
   ```

## 🛠️ **Management Commands**

### **Main Server Commands**
```bash
# Check status
sudo systemctl status main-server-coap

# View logs
sudo journalctl -u main-server-coap -f

# Restart service
sudo systemctl restart main-server-coap

# Health check
sudo /opt/management-system/health-check-main-server.sh
```

### **Regular Node Commands**
```bash
# Check status
sudo systemctl status regular-node-coap

# View logs
sudo journalctl -u regular-node-coap -f

# Restart service
sudo systemctl restart regular-node-coap

# Health check
sudo /opt/management-system/health-check-regular-node.sh
```

## 🔍 **Troubleshooting**

### **Common Issues**

1. **CoAP connection failed**
   ```bash
   # Check if UDP port 5683 is open
   sudo netstat -ulpn | grep 5683
   
   # Check firewall
   sudo ufw status
   sudo ufw allow 5683/udp
   ```

2. **Service won't start**
   ```bash
   # Check logs
   sudo journalctl -u main-server-coap -n 50
   
   # Check Python dependencies
   /opt/management-system/main-server/venv/bin/pip list
   ```

3. **Node registration failed**
   ```bash
   # Check network connectivity
   ping main-server-ip
   
   # Check CoAP endpoint
   coap-client -m get coap://main-server-ip:5683/health
   ```

### **Debug Commands**

```bash
# Test CoAP connectivity
coap-client -m get coap://localhost:5683/health

# Check system resources
htop
free -h
df -h

# Check network connections
netstat -ulpn | grep 5683
```

## 📈 **Monitoring**

### **Health Check Endpoints**
- **Main Server**: `coap://main-server:5683/health`
- **Regular Node**: `coap://node:5683/health`

### **Resource Monitoring**
```bash
# Check memory usage
systemctl show main-server-coap --property=MemoryCurrent

# Check CPU usage
systemctl show main-server-coap --property=CPUUsageNSec
```

## 🔄 **Updates and Maintenance**

### **Update the System**
1. Stop services
2. Update code
3. Restart services
4. Verify functionality

### **Backup Configuration**
```bash
# Backup configuration
sudo tar -czf coap-backup-$(date +%Y%m%d).tar.gz /opt/management-system /etc/systemd/system/*coap*
```

## 📚 **Additional Resources**

- [CoAP Protocol Specification](https://tools.ietf.org/html/rfc7252)
- [aiocoap Library Documentation](https://aiocoap.readthedocs.io/)
- [ARM Cortex A55 Documentation](https://developer.arm.com/ip-products/processors/cortex-a/cortex-a55)

## 🤝 **Support**

For issues and questions:
1. Check the troubleshooting section
2. Review system logs
3. Verify network connectivity
4. Check resource usage

## 📄 **License**

This deployment guide is part of the Central Service & Driver Management System project.
