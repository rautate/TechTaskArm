# Deployment Options for ARM Cortex-A55

## 🎯 **Two Production-Ready Solutions**

This repository provides two complete deployment solutions optimized for ARM Cortex-A55 quad-core devices:

### **1. systemd-based Deployment** (Recommended)
- **Resource Usage**: ~300MB RAM, ~0.3 CPU cores
- **Best For**: Production deployments, balanced performance
- **Features**: Virtual environments, resource limits, security

### **2. Bare Metal Deployment** (Maximum Performance)
- **Resource Usage**: ~225MB RAM, ~0.2 CPU cores  
- **Best For**: Maximum performance, minimal overhead
- **Features**: System-wide Python, optimized for ARM

---

## 🚀 **Quick Start**

### **Option 1: systemd-based (Recommended)**
```bash
# Install
sudo ./deployment/systemd/install.sh

# Check status
systemctl status main-server regular-node

# View logs
journalctl -u main-server -f

# Health check
/opt/management-system/health-check.sh

# Uninstall
sudo ./deployment/systemd/uninstall.sh
```

### **Option 2: Bare Metal (Maximum Performance)**
```bash
# Install
sudo ./deployment/bare-metal/install.sh

# Check status
systemctl status main-server regular-node

# Performance monitor
/opt/management-system/performance-monitor.sh

# Health check
/opt/management-system/health-check.sh

# Uninstall
sudo ./deployment/bare-metal/uninstall.sh
```

---

## 📊 **Detailed Comparison**

| Feature | systemd-based | Bare Metal |
|---------|---------------|------------|
| **RAM Usage** | ~300MB | ~225MB |
| **CPU Usage** | ~0.3 cores | ~0.2 cores |
| **Setup Time** | 2-3 minutes | 1-2 minutes |
| **Python Isolation** | ✅ Virtual envs | ❌ System-wide |
| **Security** | ✅ High | ⚠️ Medium |
| **Performance** | ✅ Good | ✅ Excellent |
| **Maintenance** | ✅ Easy | ✅ Easy |
| **ARM Optimization** | ✅ Yes | ✅ Yes |

---

## 🏗️ **Architecture Details**

### **systemd-based Architecture**
```
┌─────────────────────────────────────┐
│           systemd Services          │
├─────────────────┬───────────────────┤
│  main-server    │  regular-node     │
│  (Python venv)  │  (Python venv)    │
│  Port: 8080     │  Port: 8081       │
│  RAM: ~200MB    │  RAM: ~100MB      │
└─────────────────┴───────────────────┘
│
├─ Resource Limits (systemd)
├─ Security Policies
├─ Automatic Restart
└─ Log Management
```

### **Bare Metal Architecture**
```
┌─────────────────────────────────────┐
│           systemd Services          │
├─────────────────┬───────────────────┤
│  main-server    │  regular-node     │
│  (System Python)│  (System Python)  │
│  Port: 8080     │  Port: 8081       │
│  RAM: ~150MB    │  RAM: ~75MB       │
└─────────────────┴───────────────────┘
│
├─ Direct System Integration
├─ Minimal Overhead
├─ Maximum Performance
└─ ARM-Optimized
```

---

## 🔧 **Configuration Options**

### **systemd-based Configuration**
```bash
# Edit service files
sudo nano /etc/systemd/system/main-server.service
sudo nano /etc/systemd/system/regular-node.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart main-server regular-node
```

### **Bare Metal Configuration**
```bash
# Edit startup scripts
sudo nano /opt/management-system/main-server/start.sh
sudo nano /opt/management-system/regular-node/start.sh

# Restart services
sudo systemctl restart main-server regular-node
```

---

## 📈 **Performance Monitoring**

### **systemd-based Monitoring**
```bash
# Resource usage
systemctl status main-server regular-node

# Memory usage
systemctl show main-server --property=MemoryCurrent
systemctl show regular-node --property=MemoryCurrent

# Health check
/opt/management-system/health-check.sh
```

### **Bare Metal Monitoring**
```bash
# Performance monitor
/opt/management-system/performance-monitor.sh

# Process monitoring
ps aux | grep -E '(main-server|regular-node)'

# ARM-specific monitoring
cat /sys/class/thermal/thermal_zone*/temp
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
```

---

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **Service Won't Start**
```bash
# Check logs
journalctl -u main-server -f
journalctl -u regular-node -f

# Check permissions
ls -la /opt/management-system/
sudo chown -R management-system:management-system /opt/management-system/
```

#### **High Memory Usage**
```bash
# Check resource limits
systemctl show main-server --property=MemoryLimit
systemctl show regular-node --property=MemoryLimit

# Adjust limits in service files
sudo nano /etc/systemd/system/main-server.service
```

#### **API Not Responding**
```bash
# Check if services are running
systemctl is-active main-server regular-node

# Check ports
netstat -tlnp | grep -E '(8080|8081)'

# Test API
curl http://localhost:8080/health
curl http://localhost:8081/health
```

---

## 🔄 **Migration Between Options**

### **From systemd to Bare Metal**
```bash
# Stop systemd services
sudo systemctl stop main-server regular-node

# Install bare metal
sudo ./deployment/bare-metal/install.sh
```

### **From Bare Metal to systemd**
```bash
# Stop bare metal services
sudo systemctl stop main-server regular-node

# Install systemd
sudo ./deployment/systemd/install.sh
```

---

## 🎯 **Recommendations**

### **Choose systemd-based if:**
- You want Python environment isolation
- You need higher security
- You're deploying in production
- You want easy maintenance

### **Choose Bare Metal if:**
- You need maximum performance
- You have limited resources
- You want minimal overhead
- You're deploying on embedded systems

---

## 📚 **Additional Resources**

- **API Documentation**: http://localhost:8080/docs
- **Health Check**: `/opt/management-system/health-check.sh`
- **Performance Monitor**: `/opt/management-system/performance-monitor.sh`
- **Logs**: `journalctl -u main-server -f`
- **Configuration**: `/etc/systemd/system/`

---

## 🆘 **Support**

For issues or questions:
1. Check the troubleshooting section
2. Review service logs
3. Run health checks
4. Check system resources

Both deployments are optimized for ARM Cortex-A55 quad-core processors and provide excellent performance for your use case!

