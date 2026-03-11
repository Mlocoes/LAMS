# LAMS — Linux Autonomous Monitoring System

![CI/CD](https://github.com/USUARIO/REPO/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/USUARIO/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USUARIO/REPO)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Go](https://img.shields.io/badge/go-1.21-blue)

LAMS is an automatic administrator and monitoring platform for Linux servers, tailored for small and medium infrastructures (up to 50 servers).

## Architecture Highlights
- **Central Server:** Built with Python (FastAPI), acting as the core orchestration and aggregation layer.
- **Monitor Agent:** A lightweight Go binary running on each node, gathering metrics and communicating securely.
- **Web Dashboard:** A modern Next.js React frontend for visualization.
- **Database:** PostgreSQL for robust metrics, alerts, and configuration storage.

## Repository Structure
- `server/`: FastAPI Backend.
- `agent/`: Go remote monitoring agent.
- `frontend/`: Next.js web application.
- `docs/`: Technical documentation.
- `docker-compose.yml`: Local deployment stack.

## Quick Start (Local Development)

### 1. Start the Stack

```bash
# Clone the repository
git clone https://github.com/YOUR-USER/LAMS.git
cd LAMS

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 2. Access the Dashboard

Open your browser and navigate to: `http://localhost:3000`

**Default Credentials:**
```
Email: admin@lams.io
Password: lams2024
```

### 3. Register Your First Agent

On the monitored server:

```bash
# Download and install agent
wget https://github.com/YOUR-USER/LAMS/releases/latest/download/lams-agent
chmod +x lams-agent

# Install as systemd service
sudo ./install-agent.sh \
  --server http://YOUR-SERVER-IP:8080 \
  --host-id $(hostname)

# Verify agent is running
systemctl status lams-agent
```

### 4. API Access

The API is available at `http://localhost:8080`

```bash
# Get authentication token
TOKEN=$(curl -s -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@lams.io&password=lams2024" | jq -r '.access_token')

# List all hosts
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/hosts/"

# Get metrics for a host
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/metrics/HOST_ID?limit=10"
```

### Troubleshooting

**Login fails with "Invalid credentials":**
- Use the "✨ Autocompletar credenciales" button on the login page
- Or manually enter: `admin@lams.io` / `lams2024`
- Verify backend is running: `docker logs lams-server --tail 50`

**Frontend can't connect to backend:**
- Check `.env.local` in `frontend/` directory
- Run diagnostics: Navigate to `http://localhost:3000/diagnostic`

**Agent not sending metrics:**
- Check agent logs: `journalctl -u lams-agent -f`
- Verify server URL in `/etc/lams/agent.conf`
- Check host is registered: `curl http://YOUR-SERVER:8080/api/v1/hosts/`

## Testing & CI/CD

LAMS includes comprehensive testing infrastructure:

### Unit Tests
- **200+ backend tests** with pytest (≥70% coverage)
- **Go agent tests** with native testing framework
- **Fixtures and mocks** for isolated testing

```bash
# Run backend tests
cd server
./run_tests.sh              # With coverage
./run_tests.sh quick        # Fast mode
./run_tests.sh module auth  # Specific module
```

### Integration Tests
- **12 E2E tests** covering full system flow
- Automatic docker-compose orchestration
- Authentication, metrics, alerts, Docker management

```bash
# Run integration tests
./test_integration.sh
./test_integration.sh --no-cleanup  # Keep containers for debugging
```

### CI/CD Pipeline
- Automated testing on push and PRs
- Code quality checks (flake8, black, isort)
- Security scanning with Trivy
- Automatic Docker Hub builds on main branch

See [docs/FASE2_1_TESTS_UNITARIOS.md](./docs/FASE2_1_TESTS_UNITARIOS.md) and [docs/FASE2_2_INTEGRACION_CI.md](./docs/FASE2_2_INTEGRACION_CI.md) for details.

## Production Deployment

LAMS includes production-ready configuration with Traefik reverse proxy:

### Features
- **SSL/TLS Automatic** with Let's Encrypt
- **Reverse Proxy** with Traefik v2.10
- **Rate Limiting** per service
- **Security Headers** (HSTS, XSS Protection, etc.)
- **HTTP/2 & Compression** enabled
- **Health Checks** automatic
- **Centralized Logging** in JSON format

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Edit with your domain and passwords

# 2. Run production setup
sudo ./setup-production.sh

# 3. Access your deployment
# - Dashboard: https://your-domain.com
# - API: https://api.your-domain.com
# - Traefik Dashboard: https://traefik.your-domain.com:8888
```

### Prerequisites
- Server with public IP
- Domain with DNS configured (A records for main domain and api subdomain)
- Ports 80, 443 open in firewall
- Docker & Docker Compose installed

See [docs/FASE3_1_REVERSE_PROXY.md](./docs/FASE3_1_REVERSE_PROXY.md) for detailed production setup guide.

## 📊 Prometheus & Grafana Integration

LAMS includes native Prometheus metrics export and Grafana dashboards for advanced monitoring and visualization.

### Quick Start

**1. Start monitoring stack:**
```bash
docker-compose up -d prometheus grafana
```

**2. Access dashboards:**
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3002 (admin/lams2024)

### Available Metrics

LAMS exposes 13 metric types in Prometheus format at `/api/v1/metrics`:

**Host Metrics:**
- `lams_host_cpu_usage_percent` - CPU usage by host
- `lams_host_memory_usage_percent` - Memory usage by host
- `lams_host_memory_total_bytes` - Total memory in bytes
- `lams_host_memory_used_bytes` - Used memory in bytes
- `lams_host_disk_usage_percent` - Disk usage by host
- `lams_host_temperature_celsius` - CPU temperature
- `lams_host_network_receive_bytes_total` - Network bytes received (counter)
- `lams_host_network_transmit_bytes_total` - Network bytes transmitted (counter)
- `lams_host_up` - Host status (1=online, 0=offline)
- `lams_host_info` - Host information and metadata

**Docker Metrics:**
- `lams_docker_container_cpu_percent` - Container CPU usage
- `lams_docker_container_memory_bytes` - Container memory usage
- `lams_docker_container_up` - Container status (1=running, 0=stopped)

### Example Queries

```promql
# Average CPU across all hosts
avg(lams_host_cpu_usage_percent)

# Hosts with high memory usage (>80%)
lams_host_memory_usage_percent > 80

# Total network traffic rate (last 5 minutes)
sum(rate(lams_host_network_receive_bytes_total[5m]))

# Count of running Docker containers
count(lams_docker_container_up == 1)

# Top 5 containers by memory usage
topk(5, lams_docker_container_memory_bytes)
```

### Pre-built Dashboards

LAMS includes a comprehensive Grafana dashboard:

**LAMS - System Overview** (`lams-system-overview`)
- CPU Usage (timeseries per host)
- Memory Usage (timeseries per host)
- Disk Usage (gauge with thresholds)
- CPU Temperature (gauge with alerts)
- Network Traffic (RX/TX rates)
- Docker Container CPU (all containers)
- Docker Container Memory (all containers)
- Variable template for host filtering
- Auto-refresh every 30s

Access at: http://localhost:3002/d/lams-system-overview

### Configuration

**Prometheus scraping interval:** 30 seconds  
**Data retention:** 30 days  
**Grafana provisioning:** Automatic on startup

**Custom dashboards:** Place JSON files in `grafana/dashboards/`  
**Additional datasources:** Add YAML to `grafana/provisioning/datasources/`

### Advanced Usage

For detailed query examples and best practices, see:
- [docs/PROMETHEUS_QUERIES.md](./docs/PROMETHEUS_QUERIES.md) - Complete query guide
- [docs/FASE4_4_PROMETHEUS_GRAFANA.md](./docs/FASE4_4_PROMETHEUS_GRAFANA.md) - Implementation details

### Ports

- **8080** - LAMS Backend API (includes `/api/v1/metrics`)
- **9090** - Prometheus UI
- **3002** - Grafana UI

See the [docs/](./docs/) directory for detailed system information.
