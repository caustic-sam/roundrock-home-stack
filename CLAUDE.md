# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Raspberry Pi home stack deployment repository containing containerized services for smart home automation, monitoring, and media streaming. The stack is designed to run on Raspberry Pi hardware with Docker Compose orchestration.

## Architecture

The repository follows a service-oriented architecture with each service isolated in its own directory under `svc/`:

- **svc/svc-homeassistant/** - Home Assistant smart home platform
- **svc/svc-plex/** - Plex media server
- **svc/svc-jellyfin/** - Jellyfin media server (alternative to Plex)
- **svc/svc-portainer/** - Docker container management UI
- **svc/monitoring/** - Complete monitoring stack with Prometheus, Grafana, AlertManager
- **svc/svc-alertcenter/** - AlertManager configuration
- **tools/** - Utility scripts for setup and maintenance

## Environment Configuration

The system uses environment files for configuration:
- `.rr.live.env` - Production environment template
- `.rr.uat.env` - UAT environment template
- `svc/monitoring/._env_monitoring` - Monitoring stack specific variables

Key environment variables include paths for media (`MEDIA_DIR`), configuration (`CONFIG_DIR`), and service-specific settings for Pi-hole, Plex, Grafana, Prometheus, and Home Assistant.

## Common Development Commands

### Service Management
```bash
# Start all services
cd svc/monitoring && docker compose up -d

# Start specific service
cd svc/svc-homeassistant && docker compose up -d

# Restart Grafana after configuration changes
cd svc/monitoring && docker compose restart grafana
```

### Monitoring Stack
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9091
- **AlertManager**: http://localhost:9094
- **Node Exporter**: http://localhost:9101/metrics
- **cAdvisor**: http://localhost:8020

### Utility Scripts
- `tools/rpicortex_setup.sh` - Complete Raspberry Pi AI/ML environment setup
- `tools/pihole-prometheus.sh` - Pi-hole metrics exporter setup
- `tools/rpi-diagnostics.py` - System diagnostics and health checks

## Service Configuration Structure

Each service follows a consistent pattern:
- `docker-compose.yml` - Service orchestration
- Configuration files mounted as volumes
- Environment variables sourced from root-level `.env` files
- Network isolation where appropriate
- Health checks and restart policies

## Key Design Patterns

1. **Host Networking**: Home Assistant uses host network mode for device discovery
2. **Volume Mounts**: Persistent data stored in `${CONFIG_DIR}` with service subdirectories
3. **Environment Templating**: Centralized environment variable management
4. **Monitoring Integration**: All services expose metrics for Prometheus scraping
5. **Security**: Default passwords defined in environment files (should be changed)

## Development Workflow

When modifying services:
1. Update relevant `docker-compose.yml` in service directory
2. Modify environment variables in root-level `.env` files
3. Test service independently before integration
4. Use monitoring stack to verify service health
5. Check logs via Docker Compose or Portainer UI

## Network Architecture

Services communicate through:
- Docker bridge networks for internal communication
- Host networking for Home Assistant device discovery
- Exposed ports for web interfaces and API access
- Prometheus service discovery for monitoring targets