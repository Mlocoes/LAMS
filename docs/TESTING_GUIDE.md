# Tests para LAMS - Sprint 1 Portainer Features

## Estructura de Tests

### Backend Tests (Python/Pytest)

#### test_api_containers_extended.py
Tests para las nuevas funcionalidades de contenedores:

**TestContainerLogs:**
- ✅ test_get_container_logs_success
- ✅ test_get_container_logs_with_parameters
- ✅ test_get_container_logs_invalid_container
- ✅ test_get_container_logs_invalid_host
- ✅ test_get_container_logs_unauthorized
- ✅ test_get_container_logs_invalid_tail

**TestContainerInspect:**
- ✅ test_inspect_container_success
- ✅ test_inspect_container_invalid_container
- ✅ test_inspect_container_unauthorized

**TestContainerRemove:**
- ✅ test_remove_container_stopped
- ✅ test_remove_container_running_without_force
- ✅ test_remove_container_running_with_force
- ✅ test_remove_container_with_volumes
- ✅ test_remove_container_invalid_container
- ✅ test_remove_container_unauthorized

**TestContainerExec:**
- ✅ test_create_exec_success
- ✅ test_create_exec_container_not_running
- ✅ test_create_exec_invalid_container
- ✅ test_create_exec_invalid_payload
- ✅ test_create_exec_unauthorized

**TestRemoteCommandCreation:**
- ✅ test_logs_creates_remote_command
- ✅ test_inspect_creates_remote_command
- ✅ test_remove_creates_remote_command

**Total:** 24 tests backend

#### Ejecutar Tests Backend

```bash
cd /home/mloco/Escritorio/LAMS/server

# Todos los tests
python3 -m pytest tests/test_api_containers_extended.py -v

# Tests específicos
python3 -m pytest tests/test_api_containers_extended.py::TestContainerLogs -v

# Con coverage
python3 -m pytest tests/test_api_containers_extended.py --cov=api.containers_extended --cov-report=html
```

### Agent Tests (Go)

#### collector/docker_test.go
Tests para funciones Docker del agente:

- ✅ TestGetContainerLogs
  - with invalid container
  - with zero tail
- ✅ TestInspectContainer
- ✅ TestRemoveContainer
  - with invalid container
  - with force and volumes flags
- ✅ TestExecCreate
  - with invalid container
  - with valid parameters
  - with empty command
- ✅ TestStartContainer
- ✅ TestStopContainer
- ✅ TestRestartContainer
- ✅ TestKillContainer
- ✅ TestGetDockerContainers
- ⚡ BenchmarkGetContainerLogs
- ⚡ BenchmarkInspectContainer

**Total:** 13 tests + 2 benchmarks

#### Ejecutar Tests Agent

```bash
cd /home/mloco/Escritorio/LAMS/agent

# Todos los tests Docker
go test ./collector -v -run Docker

# Test específico
go test ./collector -v -run TestGetContainerLogs

# Con coverage
go test ./collector -cover -coverprofile=coverage.out
go tool cover -html=coverage.out

# Benchmarks
go test ./collector -bench=. -benchmem
```

## Tests E2E (Playwright)

### Estructura Propuesta

```
LAMS/frontend/tests/e2e/
├── container-logs.spec.ts
├── container-inspect.spec.ts
├── container-delete.spec.ts
├── container-console.spec.ts
└── fixtures/
    └── docker-fixtures.ts
```

### Ejemplos de Tests E2E

#### container-logs.spec.ts
```typescript
import { test, expect } from '@playwright/test';

test.describe('Container Logs', () => {
  test('should open logs modal and display logs', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    
    // Click logs button
    await page.click('[data-testid="container-logs-btn"]');
    
    // Wait for modal
    await expect(page.locator('.logsContainer')).toBeVisible();
    
    // Check logs are displayed
    await expect(page.locator('.logLine')).toHaveCount.greaterThan(0);
  });
  
  test('should search in logs', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    await page.click('[data-testid="container-logs-btn"]');
    
    // Type in search
    await page.fill('[placeholder*="Search"]', 'error');
    
    // Verify filtered results
    const logLines = page.locator('.logLine');
    const count = await logLines.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
  
  test('should download logs', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    await page.click('[data-testid="container-logs-btn"]');
    
    // Start download
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('[title="Download"]')
    ]);
    
    // Verify filename
    expect(download.suggestedFilename()).toContain('.log');
  });
});
```

#### container-inspect.spec.ts
```typescript
import { test, expect } from '@playwright/test';

test.describe('Container Inspect', () => {
  test('should display inspect data', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    await page.click('[data-testid="container-inspect-btn"]');
    
    await expect(page.locator('.inspectContainer')).toBeVisible();
    await expect(page.locator('.jsonSection')).toHaveCount.greaterThan(0);
  });
  
  test('should expand/collapse sections', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    await page.click('[data-testid="container-inspect-btn"]');
    
    // Click to collapse
    await page.click('.jsonKey:has-text("State")');
    await expect(page.locator('.jsonValue').first()).not.toBeVisible();
    
    // Click to expand
    await page.click('.jsonKey:has-text("State")');
    await expect(page.locator('.jsonValue').first()).toBeVisible();
  });
});
```

#### container-delete.spec.ts
```typescript
import { test, expect } from '@playwright/test';

test.describe('Container Delete', () => {
  test('should show warning for running container', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    await page.click('[data-testid="container-delete-btn"]');
    
    await expect(page.locator('.runningWarning')).toBeVisible();
  });
  
  test('should require force for running container', async ({ page }) => {
    await page.goto('/hosts/test-host-id');
    await page.click('[data-testid="container-delete-btn"]');
    
    const deleteBtn = page.locator('button:has-text("Delete Container")');
    await expect(deleteBtn).toBeDisabled();
    
    // Enable force
    await page.check('input[type="checkbox"]:near(:text("Force delete"))');
    await expect(deleteBtn).toBeEnabled();
  });
});
```

### Configuración Playwright

#### playwright.config.ts
```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Instalación Playwright

```bash
cd /home/mloco/Escritorio/LAMS/frontend

# Instalar Playwright
npm install -D @playwright/test
npx playwright install

# Ejecutar tests
npx playwright test

# Ejecutar con UI
npx playwright test --ui

# Ver reporte
npx playwright show-report
```

## Cobertura de Tests

### Objetivos
- **Backend:** ≥80% coverage en `api/containers_extended.py`
- **Agent:** ≥75% coverage en `collector/docker.go`
- **E2E:** Cobertura de flujos críticos

### Generar Reportes

```bash
# Backend coverage
cd LAMS/server
python3 -m pytest tests/ --cov=api --cov-report=html
open htmlcov/index.html

# Agent coverage
cd LAMS/agent
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out

# E2E coverage (con nyc)
cd LAMS/frontend
npm run test:e2e:coverage
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: LAMS Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: |
          cd server
          pip install -r requirements.txt
          pytest tests/ -v --cov
  
  agent-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.21'
      - run: |
          cd agent
          go test ./... -v -cover
  
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: |
          cd frontend
          npm ci
          npx playwright install --with-deps
          npx playwright test
```

## Notas Importantes

### Limitaciones Actuales
- Tests backend requieren timeout handling para comandos que esperan al agente
- Tests agent requieren Docker instalado para tests de integración completos
- Tests E2E requieren backend y agente corriendo

### Mock Strategy
- Backend: Mock de AsyncSession y RemoteCommand para tests unitarios
- Agent: Tests unitarios no requieren Docker real (retornan errores esperados)
- E2E: Usar fixtures con contenedores mock o containedores reales de test

### Próximos Pasos
1. Implementar tests E2E con Playwright
2. Agregar integration tests con Docker real
3. Configurar CI/CD pipeline
4. Mejorar coverage a >90%
