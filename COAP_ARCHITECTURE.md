# Pure CoAP Update System Architecture

## System Overview

This system uses CoAP (Constrained Application Protocol) for all communication, optimized for resource-constrained ARM Cortex A55 IoT devices.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL TRIGGER                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   POSTMAN   │    │  DASHBOARD  │    │   OTHER     │        │
│  │   (CoAP)    │    │   (Web UI)  │    │  TRIGGERS   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ CoAP POST /updates
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MAIN SERVER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   CoAP      │  │   CoAP      │  │   CoAP      │            │
│  │   SERVER    │  │   PROXY     │  │   OBSERVE   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   DATABASE  │  │   UPDATE    │  │   FIRMWARE  │            │
│  │  (SQLite)   │  │  MANAGER    │  │   STORAGE   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │ CoAP Messages (UDP)
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

## CoAP Resource Structure

### Update Resources
- `/updates` - List available updates
- `/updates/{update_id}` - Get specific update info
- `/updates/{update_id}/download` - Download update package
- `/updates/{update_id}/install` - Install update
- `/updates/{update_id}/status` - Update status (observable)

### Node Resources
- `/nodes` - List all nodes
- `/nodes/{node_id}` - Get node information
- `/nodes/{node_id}/health` - Node health (observable)
- `/nodes/{node_id}/metrics` - Node metrics (observable)
- `/nodes/{node_id}/services` - Node services
- `/nodes/{node_id}/logs` - Node logs

### System Resources
- `/system/restart` - Restart system
- `/system/shutdown` - Shutdown system
- `/system/config` - System configuration

## CoAP Features Used

### 1. RESTful API
- **GET**: Retrieve resources
- **POST**: Create/trigger actions
- **PUT**: Update resources
- **DELETE**: Remove resources

### 2. Observing (Publish/Subscribe)
- **Health Monitoring**: Observe `/nodes/{node_id}/health`
- **Update Status**: Observe `/updates/{update_id}/status`
- **System Metrics**: Observe `/nodes/{node_id}/metrics`

### 3. Block-wise Transfer
- **Large Files**: Split firmware into blocks
- **Progress Tracking**: Track download progress
- **Resume Support**: Resume interrupted downloads

### 4. Security (DTLS)
- **Encryption**: All communication encrypted
- **Authentication**: Certificate-based auth
- **Integrity**: Message integrity verification

## Communication Flow

### 1. Update Process
1. **Trigger**: External system sends CoAP POST to `/updates`
2. **Notification**: Server notifies nodes via CoAP Observe
3. **Download**: Node downloads via CoAP GET with block-wise transfer
4. **Install**: Node sends CoAP POST to `/updates/{id}/install`
5. **Status**: Node observes `/updates/{id}/status` for progress
6. **Completion**: Server updates status, nodes receive notification

### 2. Health Monitoring
1. **Registration**: Node registers with server via CoAP POST
2. **Observing**: Server observes `/nodes/{id}/health`
3. **Updates**: Node sends health updates via CoAP PUT
4. **Alerts**: Server sends alerts via CoAP Observe

## Technology Stack

### Main Server
- **Language**: Python 3.9+
- **CoAP Library**: aiocoap (async CoAP server)
- **Database**: SQLite (embedded)
- **Security**: DTLS (aiocoap-tinydtls)

### Regular Nodes
- **Language**: Python 3.9+
- **CoAP Library**: aiocoap (async CoAP client)
- **Process Management**: systemd
- **Security**: DTLS client

## Resource Usage (ARM Cortex A55)

### Main Server
- **RAM**: ~200MB (CoAP server + database)
- **CPU**: ~0.2 cores
- **Storage**: ~100MB (excluding firmware files)
- **Network**: UDP port 5683 (CoAP), 5684 (DTLS)

### Regular Node
- **RAM**: ~100MB (CoAP client)
- **CPU**: ~0.1 cores
- **Storage**: ~30MB (excluding updates)
- **Network**: UDP port 5683 (CoAP), 5684 (DTLS)

## CoAP Message Examples

### Update Notification
```
POST /updates
Content-Format: application/json
Payload: {
  "update_id": "fw-v2.1.0",
  "version": "2.1.0",
  "size": 1048576,
  "checksum": "sha256:abc123...",
  "target_nodes": ["node1", "node2"]
}
```

### Health Status
```
PUT /nodes/node1/health
Content-Format: application/json
Payload: {
  "status": "healthy",
  "cpu_percent": 25.5,
  "memory_percent": 45.2,
  "temperature": 45.2,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Firmware Download (Block-wise)
```
GET /updates/fw-v2.1.0/download
Block1: 0/1024/1024  (block 0, more blocks, block size 1024)
Block2: 1/1024/1024  (block 1, more blocks, block size 1024)
...
BlockN: N/0/1024     (block N, last block, block size 1024)
```

## Security Implementation

### DTLS Configuration
```python
# Server DTLS setup
context = await Context.create_server_context(
    bind=("0.0.0.0", 5684),
    server_credentials=load_certificate_chain("server.crt"),
    private_key=load_private_key("server.key")
)

# Client DTLS setup
context = await Context.create_client_context(
    server_credentials=load_certificate_chain("ca.crt")
)
```

### Certificate Management
- **CA Certificate**: Root certificate authority
- **Server Certificate**: Main server certificate
- **Client Certificates**: Node certificates
- **Certificate Validation**: Mutual TLS authentication

## Advantages

### CoAP Benefits
- **Lightweight**: ~4 bytes overhead per message
- **UDP-based**: Lower overhead than TCP
- **Built-in Security**: DTLS support
- **RESTful**: Familiar HTTP-like API
- **Observing**: Built-in pub/sub mechanism
- **Block Transfer**: Efficient large file handling

### ARM Cortex A55 Optimization
- **Low Memory**: Minimal RAM usage
- **Low CPU**: Efficient processing
- **Low Power**: UDP reduces power consumption
- **Real-time**: Immediate message delivery

## Disadvantages

### CoAP Limitations
- **UDP Reliability**: No guaranteed delivery (use confirmable messages)
- **Firewall Issues**: UDP may be blocked
- **Complexity**: More complex than HTTP
- **Limited Libraries**: Fewer CoAP libraries available

### Implementation Challenges
- **DTLS Setup**: Certificate management complexity
- **Block Transfer**: Implementation complexity
- **Error Handling**: UDP-specific error handling
- **Debugging**: Harder to debug than HTTP

## Implementation Priority

1. **Phase 1**: Basic CoAP server and client
2. **Phase 2**: DTLS security implementation
3. **Phase 3**: Block-wise transfer for large files
4. **Phase 4**: Observing mechanism for real-time updates
5. **Phase 5**: Advanced features (QoS, persistence)

## Comparison with MQTT+HTTP

| Feature | CoAP | MQTT+HTTP |
|---------|------|-----------|
| Memory Usage | ~100MB | ~150MB |
| CPU Usage | ~0.1 cores | ~0.2 cores |
| Protocol Overhead | ~4 bytes | ~2KB (MQTT) + HTTP |
| Security | Built-in DTLS | TLS + MQTT security |
| Large Files | Block transfer | HTTP download |
| Real-time | Observing | MQTT pub/sub |
| Complexity | Medium | High |
| Reliability | UDP-based | TCP-based |

This pure CoAP approach provides the most resource-efficient solution for ARM Cortex A55 IoT devices, with built-in security and efficient large file handling.
