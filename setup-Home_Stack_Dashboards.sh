#!/bin/bash
# =============================================================================
# RoundRock Home Stack - Dashboard Setup Script
# =============================================================================
# This script sets up impressive Grafana dashboards for your monitoring stack
# Run this from your project root directory
# =============================================================================

set -e  # Exit on any error

echo "🏠 Setting up RoundRock Monitoring Dashboards..."
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [[ ! -f "svc/monitoring/docker-compose.yml" ]]; then
    echo -e "${RED}❌ Error: Please run this script from the roundrock-home-stack root directory${NC}"
    exit 1
fi

# Create dashboard directories
echo -e "${BLUE}📁 Creating dashboard directories...${NC}"
mkdir -p svc/monitoring/svc-grafana/dashboards/json
mkdir -p svc/monitoring/svc-grafana/datasources

# Create the datasource configuration
echo -e "${BLUE}🔗 Setting up Prometheus datasource...${NC}"
cat > svc/monitoring/svc-grafana/datasources/prometheus.yml << 'EOF'
# Grafana datasource configuration
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    basicAuth: false
    jsonData:
      timeInterval: "15s"
      queryTimeout: "60s"
      httpMethod: "POST"
    version: 1
EOF

# Create dashboard provider configuration
echo -e "${BLUE}📊 Setting up dashboard providers...${NC}"
cat > svc/monitoring/svc-grafana/dashboards/dashboards.yml << 'EOF'
# Grafana dashboard provider configuration
apiVersion: 1

providers:
  - name: 'roundrock-dashboards'
    orgId: 1
    folder: 'RoundRock Home'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards/json
EOF

echo -e "${GREEN}✅ Dashboard setup complete!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Save the dashboard JSONs to: svc/monitoring/svc-grafana/dashboards/json/"
echo "2. Restart your monitoring stack:"
echo "   cd svc/monitoring && docker-compose restart grafana"
echo ""
echo -e "${BLUE}🌐 Access your dashboards at:${NC}"
echo "   Grafana: http://192.168.1.20:3001 (admin/admin123)"
echo ""
echo -e "${GREEN}🎉 Your impressive dashboards include:${NC}"
echo "   • 🏠 System Overview - CPU, Memory, Disk, Temperature"
echo "   • 🐳 Container Monitoring - Docker container metrics"
echo "   • 🏡 Home Services - HA, Plex, Jellyfin, Pi-hole status"
echo ""
echo -e "${YELLOW}💡 Pro Tips:${NC}"
echo "   • Use 'now-1h' to 'now' for real-time monitoring"
echo "   • Set refresh to 30s for live updates"
echo "   • Check alerts in AlertManager: http://192.168.1.20:9094"