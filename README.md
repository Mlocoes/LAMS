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

See the [docs/](./docs/) directory for detailed system information.
