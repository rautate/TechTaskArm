# Multi-architecture support for ARM and x86
FROM --platform=$BUILDPLATFORM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    systemd \
    bc \
    procps \
    dnsutils \
    iputils-ping \
    file \
    lscpu \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY agent/ ./agent/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /opt/node-updates /opt/node-backups /var/log/node-agent /opt/services

# Make scripts executable
RUN chmod +x ./scripts/*.sh

# Copy scripts to system location
RUN cp ./scripts/*.sh /usr/local/bin/

# Expose port
EXPOSE 8081

# Run the application
CMD ["python", "-m", "uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8081"]
