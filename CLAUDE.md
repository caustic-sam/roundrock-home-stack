# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the RoundRock Home Stack - a comprehensive containerized home lab and smart home monitoring solution designed for Raspberry Pi deployment. The stack combines traditional home services (Pi-hole, Plex, Home Assistant) with enterprise-grade monitoring (Prometheus, Grafana, AlertManager) and experimental AI capabilities.

## Architecture

The project is organized into service-based modules under the `svc/` directory:

- **Applications (`svc/applications/`)**: Core home services including Pi-hole, Plex, Home Assistant, and Jellyfin
- **Monitoring (`svc/monitoring/`)**: Full observability stack with Prometheus, Grafana, AlertManager, Node Exporter, and cAdvisor
- **Management (`svc/portainer/`)**: Container management through Portainer

Each service uses Docker Compose for orchestration with dedicated configuration directories.

## Key Commands

### Service Management
```bash
# Start monitoring stack
cd svc/monitoring && docker-compose up -d

# Start application services
cd svc/applications && docker-compose up -d

# Start Portainer for container management
cd svc/portainer && docker-compose up -d

# View all running containers
docker ps

# Check service logs
docker-compose logs [service-name]
```

### Environment Configuration
- Environment variables are defined in `.rr.live.env` and `.rr.uat.env` files in the project root
- Copy appropriate env file to `.env` before deployment
- Key services use host networking for LAN visibility

### AI/ML Capabilities
```bash
# Set up AI environment (Raspberry Pi)
./rpicortex_setup.sh

# Start AI metrics collection
systemctl start rpicortex-metrics

# Access Jupyter Lab
# Default: http://[raspberry-pi-ip]:8888

# Run AI benchmarks
cd ~/rpicortex && source ai-env/bin/activate
python experiments/model_benchmark.py
```

### Monitoring Setup
```bash
# Initialize Grafana dashboards
./setup-Home_Stack_Dashboards.sh

# Access monitoring services
# Grafana: http://[host-ip]:3001 (admin/admin123)
# Prometheus: http://[host-ip]:9091
# AlertManager: http://[host-ip]:9094
```

## Service Access

| Service | Port | Default Credentials |
|---------|------|-------------------|
| Pi-hole | 80 | admin / `${PIHOLE_PASSWORD}` |
| Home Assistant | 8123 | Setup on first login |
| Plex | 32400 | Plex account required |
| Grafana | 3001 | admin / admin123 |
| Prometheus | 9091 | No auth |
| AlertManager | 9094 | No auth |
| Portainer | 9000 | Setup on first login |
| Node Exporter | 9101 | Metrics endpoint |
| cAdvisor | 8020 | No auth |

## Configuration Structure

- **Environment Files**: `.rr.live.env`, `.rr.uat.env` contain service credentials and paths
- **Prometheus Config**: `svc/monitoring/svc-prometheus/prometheus.yml` and `rules/` directory
- **Grafana**: Datasources in `svc/monitoring/svc-grafana/datasources/`, dashboards provisioned via JSON files
- **AlertManager**: Configuration in `svc/monitoring/svc-alertcenter/alertmanager.yml`

## AI Integration

The stack includes experimental AI monitoring via `ai-hat-monitor.py` which:
- Detects AI HAT hardware on Raspberry Pi
- Exports AI-specific metrics to Prometheus
- Monitors CPU/GPU temperatures during ML workloads
- Integrates with the broader monitoring ecosystem

## Development Workflow

1. Make configuration changes to appropriate service directories
2. Test changes with `docker-compose config` to validate YAML
3. Apply changes with `docker-compose up -d --force-recreate [service]`
4. Monitor service health through Grafana dashboards
5. Check logs for any issues with `docker-compose logs`

## File Organization

```
roundrock-home-stack/
├── svc/
│   ├── applications/          # Home services
│   ├── monitoring/           # Observability stack
│   └── portainer/           # Container management
├── docs/                    # Documentation
├── .rr.live.env            # Live environment config
├── .rr.uat.env             # UAT environment config
├── rpicortex_setup.sh      # AI environment setup
└── setup-Home_Stack_Dashboards.sh  # Grafana setup
```

## Testing

No formal test suite exists. Validate deployments by:
1. Checking service health endpoints
2. Verifying metrics collection in Prometheus targets
3. Confirming dashboard functionality in Grafana
4. Testing alerting rules in AlertManager

## Important Notes

- Services use host networking for local network visibility
- Persistent data stored in Docker named volumes
- AI features require Raspberry Pi with compatible hardware
- All credentials should be updated from defaults before production use