#!/bin/bash
# =============================================================================
# Pi-hole Prometheus Exporter Setup for rpi-edge
# =============================================================================
# This script sets up monitoring for Pi-hole running on rpi-edge
# =============================================================================

echo "🛡️ Setting up Pi-hole monitoring for rpi-edge"
echo "=============================================="

# Install Pi-hole exporter using Docker
echo "🐳 Setting up Pi-hole exporter container..."

# Create docker-compose for Pi-hole exporter on rpi-edge
sudo tee /home/pi/pihole-exporter-compose.yml > /dev/null <<EOF
version: '3.8'

services:
  pihole-exporter:
    image: ekofr/pihole-exporter:latest
    container_name: pihole-exporter
    ports:
      - "9617:9617"
    environment:
      - PIHOLE_HOSTNAME=localhost
      - PIHOLE_PORT=80
      - PIHOLE_PASSWORD=\${PIHOLE_PASSWORD}
      - INTERVAL=30s
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    external: true
EOF

echo "✅ Pi-hole exporter docker-compose created"
echo ""
echo "🔧 To start the exporter on rpi-edge:"
echo "1. SSH to rpi-edge:"
echo "   ssh pi@rpi-edge"
echo ""
echo "2. Set your Pi-hole password:"
echo "   export PIHOLE_PASSWORD='your_pihole_password'"
echo ""
echo "3. Start the exporter:"
echo "   docker-compose -f pihole-exporter-compose.yml up -d"
echo ""
echo "4. Add to Prometheus config on rpicortex:"
cat << 'PROMETHEUS_CONFIG'

  # Pi-hole on rpi-edge
  - job_name: 'pihole'
    static_configs:
      - targets: ['rpi-edge:9617']
    scrape_interval: 30s
PROMETHEUS_CONFIG

echo ""
echo "📊 Metrics will be available at: http://rpi-edge:9617/metrics"