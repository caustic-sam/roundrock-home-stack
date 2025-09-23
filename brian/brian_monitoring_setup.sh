#!/bin/bash

# Brian (RPi5 16GB) Monitoring Setup Script
# Run this on your main RPi5 system

set -e

echo "Setting up comprehensive monitoring on Brian..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv curl git htop iotop

# Create monitoring directory
mkdir -p ~/brian-monitoring/{scripts,configs,logs}
cd ~/brian-monitoring

# Install Docker if not already installed
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    sudo apt install docker-compose-plugin -y
fi

# Create Python virtual environment for custom metrics
python3 -m venv venv
source venv/bin/activate
pip install psutil GPUtil prometheus_client requests

# Create custom metrics collectors
cat > scripts/ai_hat_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
AI HAT monitoring script for Brian
Collects AI HAT specific metrics and exports to Prometheus
"""

import time
import psutil
import subprocess
import json
from prometheus_client import start_http_server, Gauge, Counter

# Prometheus metrics
ai_hat_temp = Gauge('ai_hat_temperature_celsius', 'AI HAT temperature in Celsius')
ai_hat_util = Gauge('ai_hat_utilization_percent', 'AI HAT utilization percentage')
ai_hat_memory = Gauge('ai_hat_memory_bytes', 'AI HAT memory usage in bytes')
ai_hat_power = Gauge('ai_hat_power_watts', 'AI HAT power consumption in watts')

def get_thermal_zone_temp(zone_name="cpu-thermal"):
    """Get temperature from thermal zone"""
    try:
        with open(f'/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000.0
        return temp
    except:
        return 0

def get_ai_hat_metrics():
    """Collect AI HAT specific metrics"""
    try:
        # CPU temperature (proxy for AI HAT temp)
        temp = get_thermal_zone_temp()
        ai_hat_temp.set(temp)
        
        # GPU utilization (if available through vcgencmd)
        try:
            result = subprocess.run(['vcgencmd', 'get_throttled'], 
                                  capture_output=True, text=True)
            throttled = result.stdout.strip()
            # Parse throttling status
        except:
            pass
        
        # Mock AI utilization - replace with actual HAT metrics
        # You'll need to integrate with actual AI HAT monitoring APIs
        cpu_percent = psutil.cpu_percent(interval=1)
        ai_hat_util.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        ai_hat_memory.set(memory.used)
        
        # Power estimation (mock - integrate with actual power monitoring)
        power_estimate = 5.0 + (cpu_percent / 100.0) * 10.0  # 5-15W estimate
        ai_hat_power.set(power_estimate)
        
    except Exception as e:
        print(f"Error collecting AI HAT metrics: {e}")

def main():
    # Start Prometheus metrics server
    start_http_server(9101)
    print("AI HAT metrics server started on port 9101")
    
    while True:
        get_ai_hat_metrics()
        time.sleep(15)

if __name__ == '__main__':
    main()
EOF

# Create hardware monitoring script
cat > scripts/hardware_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Hardware monitoring script for Brian
Monitors temperatures, voltages, and hardware health
"""

import time
import subprocess
import re
from prometheus_client import start_http_server, Gauge

# Prometheus metrics
cpu_temp = Gauge('rpi_cpu_temperature_celsius', 'CPU temperature')
gpu_temp = Gauge('rpi_gpu_temperature_celsius', 'GPU temperature')
cpu_voltage = Gauge('rpi_cpu_voltage_volts', 'CPU voltage')
throttle_status = Gauge('rpi_throttle_status', 'Throttle status bitmask')
fan_speed = Gauge('rpi_fan_speed_rpm', 'Cooling fan speed in RPM')

def get_vcgencmd_value(command):
    """Get value from vcgencmd"""
    try:
        result = subprocess.run(['vcgencmd'] + command.split(), 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return None

def collect_hardware_metrics():
    """Collect Raspberry Pi hardware metrics"""
    try:
        # CPU Temperature
        temp_output = get_vcgencmd_value('measure_temp')
        if temp_output:
            temp_match = re.search(r'temp=(\d+\.?\d*)\'C', temp_output)
            if temp_match:
                cpu_temp.set(float(temp_match.group(1)))
        
        # CPU Voltage
        volt_output = get_vcgencmd_value('measure_volts core')
        if volt_output:
            volt_match = re.search(r'volt=(\d+\.?\d*)V', volt_output)
            if volt_match:
                cpu_voltage.set(float(volt_match.group(1)))
        
        # Throttle status
        throttle_output = get_vcgencmd_value('get_throttled')
        if throttle_output:
            throttle_match = re.search(r'throttled=0x(\w+)', throttle_output)
            if throttle_match:
                throttle_value = int(throttle_match.group(1), 16)
                throttle_status.set(throttle_value)
        
        # Fan speed (if available)
        # This would need to be adapted based on your actual fan controller
        # For now, we'll estimate based on temperature
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_raw = int(f.read().strip()) / 1000.0
                # Estimate fan speed based on temperature
                if temp_raw > 60:
                    estimated_fan_speed = min(3000, (temp_raw - 40) * 100)
                else:
                    estimated_fan_speed = 800  # Minimum speed
                fan_speed.set(estimated_fan_speed)
        except:
            pass
            
    except Exception as e:
        print(f"Error collecting hardware metrics: {e}")

def main():
    start_http_server(9104)
    print("Hardware metrics server started on port 9104")
    
    while True:
        collect_hardware_metrics()
        time.sleep(10)

if __name__ == '__main__':
    main()
EOF

# Create network monitoring script
cat > scripts/network_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Network monitoring script for Brian
Monitors network performance, connectivity, and security
"""

import time
import psutil
import subprocess
import socket
from prometheus_client import start_http_server, Gauge, Counter

# Network metrics
network_bytes_sent = Counter('network_bytes_sent_total', 'Total bytes sent', ['interface'])
network_bytes_recv = Counter('network_bytes_recv_total', 'Total bytes received', ['interface'])
network_latency = Gauge('network_latency_ms', 'Network latency to target', ['target'])
network_bandwidth_up = Gauge('network_bandwidth_upload_mbps', 'Upload bandwidth in Mbps')
network_bandwidth_down = Gauge('network_bandwidth_download_mbps', 'Download bandwidth in Mbps')

def test_connectivity():
    """Test network connectivity to various targets"""
    targets = ['8.8.8.8', '1.1.1.1', 'google.com']
    
    for target in targets:
        try:
            # Ping test
            result = subprocess.run(['ping', '-c', '1', '-W', '3', target], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Extract latency
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'time=' in line:
                        time_part = line.split('time=')[1].split(' ')[0]
                        latency = float(time_part)
                        network_latency.labels(target=target).set(latency)
                        break
            else:
                network_latency.labels(target=target).set(9999)  # Connection failed
        except:
            network_latency.labels(target=target).set(9999)

def collect_network_stats():
    """Collect network interface statistics"""
    try:
        net_io = psutil.net_io_counters(pernic=True)
        for interface, stats in net_io.items():
            if interface != 'lo':  # Skip loopback
                network_bytes_sent.labels(interface=interface).inc(stats.bytes_sent)
                network_bytes_recv.labels(interface=interface).inc(stats.bytes_recv)
    except Exception as e:
        print(f"Error collecting network stats: {e}")

def main():
    start_http_server(9103)
    print("Network monitoring server started on port 9103")
    
    while True:
        collect_network_stats()
        test_connectivity()
        time.sleep(30)

if __name__ == '__main__':
    main()
EOF

# Create systemd services
sudo tee /etc/systemd/system/brian-ai-monitor.service > /dev/null << EOF
[Unit]
Description=Brian AI HAT Monitor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/brian-monitoring
ExecStart=$HOME/brian-monitoring/venv/bin/python scripts/ai_hat_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/brian-hardware-monitor.service > /dev/null << EOF
[Unit]
Description=Brian Hardware Monitor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/brian-monitoring
ExecStart=$HOME/brian-monitoring/venv/bin/python scripts/hardware_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/brian-network-monitor.service > /dev/null << EOF
[Unit]
Description=Brian Network Monitor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/brian-monitoring
ExecStart=$HOME/brian-monitoring/venv/bin/python scripts/network_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Make scripts executable
chmod +x scripts/*.py

# Create Docker compose for standard exporters
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  node-exporter:
    image: prom/node-exporter:latest
    container_name: brian-node-exporter
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
      - '--collector.textfile.directory=/etc/node-exporter/'
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
      - ./textfile-metrics:/etc/node-exporter:ro
    network_mode: host
    restart: unless-stopped

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: brian-cadvisor
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    devices:
      - /dev/kmsg
    privileged: true
    restart: unless-stopped
EOF

echo "Setup complete! Next steps:"
echo "1. Start Docker containers: docker compose up -d"
echo "2. Enable and start custom monitoring services:"
echo "   sudo systemctl enable brian-ai-monitor.service"
echo "   sudo systemctl enable brian-hardware-monitor.service"
echo "   sudo systemctl enable brian-network-monitor.service"
echo "   sudo systemctl start brian-ai-monitor.service"
echo "   sudo systemctl start brian-hardware-monitor.service"
echo "   sudo systemctl start brian-network-monitor.service"
echo ""
echo "Custom metrics will be available on:"
echo "- AI HAT metrics: http://brian-ip:9101/metrics"
echo "- Hardware metrics: http://brian-ip:9104/metrics"
echo "- Network metrics: http://brian-ip:9103/metrics"
echo "- Node metrics: http://brian-ip:9100/metrics"
echo "- Container metrics: http://brian-ip:8080/metrics"