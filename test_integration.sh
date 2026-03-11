#!/bin/bash
# =================================================================
# LAMS Integration Test Suite
# Tests del flujo completo: Agente → Servidor → Base de Datos → API
# =================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$TEST_DIR/docker-compose.yml"
SERVER_URL="http://localhost:8080"
DASHBOARD_URL="http://localhost:3001"
TEST_HOST_ID="test-integration-host"
ADMIN_EMAIL="admin@lams.io"
# Get password from environment or use default (NOT recommended for production)
ADMIN_PASSWORD="${ADMIN_PASSWORD:-lams2024}"

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# =================================================================
# Funciones auxiliares
# =================================================================

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                      ║${NC}"
    echo -e "${BLUE}║         LAMS Integration Test Suite                 ║${NC}"
    echo -e "${BLUE}║                                                      ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
}

test_passed() {
    ((TESTS_PASSED++))
    ((TESTS_TOTAL++))
    echo -e "${GREEN}  ✓ $1${NC}"
}

test_failed() {
    ((TESTS_FAILED++))
    ((TESTS_TOTAL++))
    echo -e "${RED}  ✗ $1${NC}"
    if [ -n "$2" ]; then
        echo -e "${RED}    Razón: $2${NC}"
    fi
}

# =================================================================
# Tests
# =================================================================

cleanup() {
    log_step "Limpiando entorno..."
    
    # Detener contenedores
    docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
    
    # Limpiar volúmenes
    docker volume rm lams_pg_data 2>/dev/null || true
    
    log_info "Entorno limpiado"
}

setup_environment() {
    log_step "Configurando entorno de test..."
    
    # Build imágenes
    log_info "Construyendo imágenes Docker..."
    docker-compose -f "$COMPOSE_FILE" build --quiet
    
    # Levantar servicios
    log_info "Levantando servicios..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Esperar a que servicios estén listos
    log_info "Esperando a que servicios estén listos..."
    local max_wait=60
    local waited=0
    
    while ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up (healthy)"; do
        if [ $waited -ge $max_wait ]; then
            log_error "Timeout esperando servicios"
            return 1
        fi
        sleep 2
        ((waited+=2))
        echo -n "."
    done
    echo ""
    
    log_info "Servicios listos"
    sleep 5  # Tiempo adicional para estabilización
}

test_server_health() {
    log_step "Test 1: Verificar salud del servidor"
    
    if curl -s "$SERVER_URL/" | grep -q "LAMS Central Server"; then
        test_passed "Servidor responde correctamente"
        return 0
    else
        test_failed "Servidor no responde" "$(curl -s $SERVER_URL/ 2>&1)"
        return 1
    fi
}

test_api_docs() {
    log_step "Test 2: Verificar documentación API"
    
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$SERVER_URL/docs")
    
    if [ "$status" == "200" ]; then
        test_passed "Documentación API accesible"
        return 0
    else
        test_failed "Documentación API no accesible" "HTTP $status"
        return 1
    fi
}

get_auth_token() {
    log_step "Test 3: Autenticación"
    
    local response=$(curl -s -X POST "$SERVER_URL/api/v1/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$ADMIN_EMAIL&password=$ADMIN_PASSWORD")
    
    TOKEN=$(echo $response | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
    
    if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
        test_passed "Login exitoso, token obtenido"
        return 0
    else
        test_failed "Login falló" "$response"
        return 1
    fi
}

test_register_host() {
    log_step "Test 4: Registrar host de prueba"
    
    local response=$(curl -s -X POST "$SERVER_URL/api/v1/hosts/register" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\": \"$TEST_HOST_ID\",
            \"hostname\": \"integration-test-server\",
            \"ip\": \"192.168.100.100\",
            \"os\": \"Ubuntu 22.04 LTS\",
            \"kernel_version\": \"5.15.0-generic\",
            \"cpu_cores\": 4,
            \"total_memory\": 8192.0
        }")
    
    if echo $response | grep -q "$TEST_HOST_ID"; then
        test_passed "Host registrado correctamente"
        return 0
    else
        test_failed "Registro de host falló" "$response"
        return 1
    fi
}

test_submit_metric() {
    log_step "Test 5: Enviar métrica"
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local response=$(curl -s -X POST "$SERVER_URL/api/v1/metrics/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"host_id\": \"$TEST_HOST_ID\",
            \"timestamp\": \"$timestamp\",
            \"cpu_usage\": 75.5,
            \"memory_used\": 4096.0,
            \"memory_total\": 8192.0,
            \"disk_used\": 60.0,
            \"disk_total\": 100.0,
            \"network_received\": 1500.0,
            \"network_sent\": 800.0,
            \"cpu_temp\": 50.0
        }")
    
    if echo $response | grep -q "$TEST_HOST_ID\|cpu_usage"; then
        test_passed "Métrica enviada correctamente"
        return 0
    else
        test_failed "Envío de métrica falló" "$response"
        return 1
    fi
}

test_retrieve_metrics() {
    log_step "Test 6: Consultar métricas"
    
    local response=$(curl -s "$SERVER_URL/api/v1/metrics/$TEST_HOST_ID?limit=10" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo $response | grep -q "$TEST_HOST_ID\|cpu_usage\|\[\]"; then
        test_passed "Métricas recuperadas correctamente"
        return 0
    else
        test_failed "Consulta de métricas falló" "$response"
        return 1
    fi
}

test_create_alert_rule() {
    log_step "Test 7: Crear regla de alerta"
    
    local response=$(curl -s -X POST "$SERVER_URL/api/v1/alert-rules/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"Integration Test Alert\",
            \"description\": \"Test alert rule for integration tests\",
            \"host_id\": \"$TEST_HOST_ID\",
            \"metric_name\": \"cpu_usage\",
            \"operator\": \">\",
            \"threshold\": 50.0,
            \"severity\": \"warning\",
            \"enabled\": true
        }")
    
    RULE_ID=$(echo $response | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    
    if [ -n "$RULE_ID" ] && [ "$RULE_ID" != "null" ]; then
        test_passed "Regla de alerta creada (ID: $RULE_ID)"
        return 0
    else
        test_failed "Creación de regla falló" "$response"
        return 1
    fi
}

test_list_alert_rules() {
    log_step "Test 8: Listar reglas de alerta"
    
    local response=$(curl -s "$SERVER_URL/api/v1/alert-rules/" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo $response | grep -q "Integration Test Alert\|\[\]"; then
        test_passed "Reglas listadas correctamente"
        return 0
    else
        test_failed "Listado de reglas falló" "$response"
        return 1
    fi
}

test_list_hosts() {
    log_step "Test 9: Listar hosts"
    
    local response=$(curl -s "$SERVER_URL/api/v1/hosts/" \
        -H "Authorization: Bearer $TOKEN")
    
    if echo $response | grep -q "$TEST_HOST_ID"; then
        test_passed "Hosts listados correctamente"
        return 0
    else
        test_failed "Listado de hosts falló" "$response"
        return 1
    fi
}

test_dashboard_accessible() {
    log_step "Test 10: Verificar accesibilidad del dashboard"
    
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$DASHBOARD_URL")
    
    if [ "$status" == "200" ]; then
        test_passed "Dashboard accesible"
        return 0
    else
        test_failed "Dashboard no accesible" "HTTP $status"
        return 1
    fi
}

test_database_connection() {
    log_step "Test 11: Verificar conexión a base de datos"
    
    local db_check=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U lams -d lams -c "SELECT COUNT(*) FROM hosts;" 2>&1)
    
    if echo "$db_check" | grep -q "[0-9]"; then
        test_passed "Base de datos accesible"
        return 0
    else
        test_failed "Conexión a base de datos falló" "$db_check"
        return 1
    fi
}

test_docker_sync() {
    log_step "Test 12: Sincronizar contenedores Docker"
    
    local response=$(curl -s -X POST "$SERVER_URL/api/v1/docker/$TEST_HOST_ID/sync" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"containers\": [
                {
                    \"container_id\": \"test123\",
                    \"name\": \"test-container\",
                    \"image\": \"nginx:latest\",
                    \"status\": \"running\",
                    \"ports\": {\"80/tcp\": \"8080\"}
                }
            ]
        }")
    
    if echo $response | grep -q "success\|synced\|added"; then
        test_passed "Contenedores Docker sincronizados"
        return 0
    else
        test_failed "Sincronización Docker falló" "$response"
        return 1
    fi
}

show_summary() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                 Test Summary                         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Total:  ${BLUE}$TESTS_TOTAL${NC}"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ Todos los tests de integración pasaron correctamente${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ Algunos tests fallaron${NC}"
        echo ""
        return 1
    fi
}

# =================================================================
# Main
# =================================================================

main() {
    print_header
    
    # Cleanup anterior si existe
    cleanup
    
    # Setup
    if ! setup_environment; then
        log_error "Fallo en setup del entorno"
        cleanup
        exit 1
    fi
    
    # Ejecutar tests
    test_server_health || true
    test_api_docs || true
    get_auth_token || { log_error "Sin token no se pueden ejecutar más tests"; cleanup; exit 1; }
    test_register_host || true
    test_submit_metric || true
    test_retrieve_metrics || true
    test_create_alert_rule || true
    test_list_alert_rules || true
    test_list_hosts || true
    test_dashboard_accessible || true
    test_database_connection || true
    test_docker_sync || true
    
    # Mostrar resumen
    show_summary
    local exit_code=$?
    
    # Cleanup (opcional, comentar si quieres inspeccionar el estado)
    if [ "$1" != "--no-cleanup" ]; then
        cleanup
    else
        log_warn "Entorno dejado activo para inspección (usa --no-cleanup)"
    fi
    
    exit $exit_code
}

# Ejecutar
main "$@"
