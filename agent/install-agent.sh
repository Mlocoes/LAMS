#!/bin/bash
set -e

# ============================================================================
# LAMS Agent Installation Script - Interactive & Auto-Discovery
# ============================================================================
# Este script instala el agente de monitoreo LAMS como un servicio systemd
# 
# Modos de uso:
#   sudo ./install-agent.sh                    (Modo interactivo - RECOMENDADO)
#   sudo ./install-agent.sh --auto             (Auto-descubrimiento + auto-config)
#   sudo ./install-agent.sh --server <URL>     (Modo CLI clásico)
#
# Opciones CLI:
#   --auto              Modo automático: buscar servidor y auto-configurar
#   --server URL        URL del servidor LAMS central
#   --token TOKEN       Token de autenticación
#   --host-id ID        ID personalizado del host (default: hostname)
#   --build-local       Compilar binario localmente (requiere Go)
#   --skip-systemd      No instalar como servicio systemd
#   --non-interactive   No hacer preguntas (usar valores por defecto)
#   --help              Mostrar esta ayuda
# ============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Variables por defecto
SERVER_URL=""
AGENT_TOKEN=""
HOST_ID=$(hostname)
BUILD_LOCAL=false
SKIP_SYSTEMD=false
INTERACTIVE=true
AUTO_MODE=false
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/lams"
CONFIG_FILE="$CONFIG_DIR/agent.conf"
SERVICE_FILE="/etc/systemd/system/lams-agent.service"
BINARY_NAME="lams-agent"

# Puertos comunes para LAMS
LAMS_PORTS=(8080 8000 3000 80 443)

# Array global para servidores descubiertos
declare -a local_servers

# ============================================================================
# Funciones auxiliares
# ============================================================================

print_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                                                                ║"
    echo "║           🖥️  LAMS Agent Installation Script  🚀               ║"
    echo "║                                                                ║"
    echo "║         Linux Autonomous Monitoring System v2.0                ║"
    echo "║                                                                ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

log_success() {
    echo -e "${GREEN}${BOLD}[✓✓✓]${NC} $1"
}

# Spinner para operaciones largas
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " ${CYAN}[%c]${NC}  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Barra de progreso
progress_bar() {
    local current=$1
    local total=$2
    local width=50
    local percentage=$((current * 100 / total))
    local completed=$((width * current / total))
    local remaining=$((width - completed))
    
    printf "\r${CYAN}["
    printf "%${completed}s" | tr ' ' '█'
    printf "%${remaining}s" | tr ' ' '░'
    printf "]${NC} %3d%%" $percentage
}

# Prompt con valor por defecto
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local response
    
    # Escribir el prompt en stderr para no mezclarlo con el valor retornado
    echo -ne "${CYAN}${prompt}${NC}" >&2
    if [ -n "$default" ]; then
        echo -ne " ${YELLOW}[${default}]${NC}: " >&2
    else
        echo -ne ": " >&2
    fi
    
    read response
    if [ -z "$response" ]; then
        echo "$default"
    else
        echo "$response"
    fi
}

# Menú de selección
select_option() {
    local prompt="$1"
    shift
    local options=("$@")
    local selected=0
    local key
    
    # Guardar configuración del terminal
    local old_stty_cfg=$(stty -g)
    
    while true; do
        echo -e "\n${CYAN}${BOLD}${prompt}${NC}\n"
        
        for i in "${!options[@]}"; do
            if [ $i -eq $selected ]; then
                echo -e "  ${GREEN}▶ ${options[$i]}${NC}"
            else
                echo -e "    ${options[$i]}"
            fi
        done
        
        echo -e "\n${YELLOW}Use ↑↓ para navegar, Enter para seleccionar${NC}"
        
        # Leer una tecla
        stty raw -echo
        key=$(dd bs=1 count=1 2>/dev/null)
        stty $old_stty_cfg
        
        case "$key" in
            $'\x1b')  # ESC sequence
                read -rsn2 key # Read 2 more chars
                case "$key" in
                    '[A') # Up arrow
                        ((selected--))
                        [ $selected -lt 0 ] && selected=$((${#options[@]} - 1))
                        ;;
                    '[B') # Down arrow
                        ((selected++))
                        [ $selected -ge ${#options[@]} ] && selected=0
                        ;;
                esac
                ;;
            '') # Enter
                echo "${options[$selected]}"
                return $selected
                ;;
        esac
        
        # Limpiar pantalla para redibujar
        tput cuu $((${#options[@]} + 3))
        tput ed
    done
}

show_help() {
    cat << EOF
${BOLD}LAMS Agent Installation Script${NC}

${CYAN}Uso:${NC}
  sudo $0                          (Modo interactivo - RECOMENDADO)
  sudo $0 --auto                   (Auto-descubrimiento)
  sudo $0 --server <URL>           (Modo CLI)

${CYAN}Opciones:${NC}
  ${GREEN}--auto${NC}              Modo automático: buscar servidor y auto-configurar
  ${GREEN}--server URL${NC}        URL del servidor LAMS central
                      Ejemplo: http://192.168.1.10:8080
  ${GREEN}--token TOKEN${NC}       Token de autenticación
  ${GREEN}--host-id ID${NC}        ID personalizado del host (default: $(hostname))
  ${GREEN}--build-local${NC}       Compilar binario localmente (requiere Go)
  ${GREEN}--skip-systemd${NC}      No instalar como servicio systemd
  ${GREEN}--non-interactive${NC}   No hacer preguntas (usar valores por defecto)
  ${GREEN}--help${NC}              Mostrar esta ayuda

${CYAN}Ejemplos:${NC}
  ${YELLOW}# Instalación interactiva (recomendado)${NC}
  sudo $0

  ${YELLOW}# Auto-descubrimiento de servidor${NC}
  sudo $0 --auto

  ${YELLOW}# Instalación con servidor específico${NC}
  sudo $0 --server http://192.168.0.8:8080 --token mi_token

  ${YELLOW}# Compilar localmente y usar host-id personalizado${NC}
  sudo $0 --server http://192.168.0.8:8080 --build-local --host-id web-server-01

EOF
    exit 0
}

# ============================================================================
# Funciones de descubrimiento automático
# ============================================================================

# Detectar información del sistema
detect_system_info() {
    log_step "Detectando información del sistema..."
    
    # Detectar distribución
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$NAME"
        OS_VERSION="$VERSION_ID"
    else
        OS_NAME=$(uname -s)
        OS_VERSION=$(uname -r)
    fi
    
    # Detectar núcleos CPU
    CPU_CORES=$(nproc 2>/dev/null || echo "desconocido")
    
    # Detectar RAM total (en MB)
    if command -v free &> /dev/null; then
        TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
    else
        TOTAL_RAM_MB="desconocido"
    fi
    
    # Detectar espacio en disco (en GB)
    if command -v df &> /dev/null; then
        TOTAL_DISK_GB=$(df -BG / | awk 'NR==2 {print $2}' | sed 's/G//')
    else
        TOTAL_DISK_GB="desconocido"
    fi
    
    log_info "Sistema: ${OS_NAME} ${OS_VERSION}"
    log_info "CPU: ${CPU_CORES} núcleos"
    log_info "RAM: ${TOTAL_RAM_MB} MB"
    log_info "Disco: ${TOTAL_DISK_GB} GB"
    echo ""
}

# Escanear red local buscando servidores LAMS
discover_lams_servers() {
    log_step "Buscando servidores LAMS en la red local..."
    echo ""
    
    # Limpiar array de servidores
    local_servers=()
    
    # Obtener IP local y red
    local local_ip=$(ip route get 1 2>/dev/null | awk '{print $7; exit}')
    if [ -z "$local_ip" ]; then
        local_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    
    if [ -z "$local_ip" ]; then
        log_warn "No se pudo detectar la IP local"
        return 1
    fi
    
    log_info "IP local: ${local_ip}"
    
    # Calcular red local (asumiendo /24)
    local network=$(echo $local_ip | cut -d'.' -f1-3)
    
    # Escanear IPs comunes primero (localhost, gateway, servidor común)
    local priority_ips=("127.0.0.1" "$local_ip" "${network}.1" "${network}.10" "${network}.8")
    
    log_step "Escaneando hosts prioritarios..."
    for ip in "${priority_ips[@]}"; do
        for port in "${LAMS_PORTS[@]}"; do
            check_lams_server "$ip" "$port"
        done
    done
    
    # Si no encontramos nada, escanear toda la red /24
    if [ ${#local_servers[@]} -eq 0 ]; then
        log_step "Escaneando red completa ${network}.0/24..."
        log_warn "Esto puede tomar unos minutos..."
        
        local scanned=0
        local total=254
        
        for i in $(seq 1 254); do
            local ip="${network}.${i}"
            
            # Skip IPs ya escaneadas
            if [[ " ${priority_ips[@]} " =~ " ${ip} " ]]; then
                continue
            fi
            
            # Mostrar progreso
            ((scanned++))
            progress_bar $scanned $total
            
            # Escanear solo puerto 8080 para ser más rápido
            check_lams_server "$ip" "8080" &
            
            # Limitar procesos paralelos
            if [ $(jobs -r | wc -l) -ge 20 ]; then
                wait -n
            fi
        done
        
        wait
        echo ""
    fi
    
    if [ ${#local_servers[@]} -eq 0 ]; then
        log_warn "No se encontraron servidores LAMS automáticamente"
        return 1
    fi
    
    log_success "Se encontraron ${#local_servers[@]} servidor(es) LAMS"
    return 0
}

# Verificar si una IP:Puerto es un servidor LAMS
check_lams_server() {
    local ip=$1
    local port=$2
    local url="http://${ip}:${port}"
    
    # Timeout corto para escaneo rápido
    if timeout 2 curl -s -f "${url}/docs" -o /dev/null 2>&1 || \
       timeout 2 curl -s -f "${url}/api/v1/health" -o /dev/null 2>&1 || \
       timeout 2 curl -s -f "${url}/" | grep -q "LAMS" 2>&1; then
        local_servers+=("$url")
        log_info "✓ Servidor LAMS encontrado: ${url}"
    fi
}

# Testar conectividad con el servidor
test_server_connection() {
    local server=$1
    
    log_step "Probando conexión con ${server}..."
    
    # Intentar acceder a /docs (Swagger)
    if timeout 5 curl -s -f "${server}/docs" -o /dev/null 2>&1; then
        log_success "Conexión exitosa con el servidor"
        return 0
    fi
    
    # Intentar acceder a /api/v1/health
    if timeout 5 curl -s -f "${server}/api/v1/health" -o /dev/null 2>&1; then
        log_success "Conexión exitosa con el servidor"
        return 0
    fi
    
    # Intentar acceso básico
    if timeout 5 curl -s -f "${server}/" -o /dev/null 2>&1; then
        log_warn "Servidor responde pero no se pudo verificar que es LAMS"
        return 0
    fi
    
    log_error "No se pudo conectar al servidor: ${server}"
    return 1
}

# Generar API key automáticamente
generate_api_key() {
    local server=$1
    local host_id=$2
    
    log_step "Generando API key para el host ${host_id}..."
    echo ""
    
    # Pedir credenciales de admin
    echo -e "${YELLOW}${BOLD}Se requieren credenciales de administrador para generar la API key${NC}"
    echo ""
    
    local admin_email
    local admin_password
    
    echo -ne "${CYAN}Email del administrador: ${NC}"
    read admin_email
    
    echo -ne "${CYAN}Contraseña: ${NC}"
    read -s admin_password
    echo ""
    echo ""
    
    # Validar que se introdujeron
    if [ -z "$admin_email" ] || [ -z "$admin_password" ]; then
        log_error "Email y contraseña son obligatorios"
        return 1
    fi
    
    # Login para obtener token JWT
    log_step "Autenticando con el servidor..."
    local login_response=$(curl -s -X POST "${server}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${admin_email}\",\"password\":\"${admin_password}\"}" 2>&1)
    
    local jwt_token=$(echo "$login_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$jwt_token" ] || [ "$jwt_token" = "null" ]; then
        log_error "Autenticación fallida. Verifica las credenciales."
        echo -e "${RED}Respuesta del servidor: ${login_response}${NC}"
        return 1
    fi
    
    log_info "Autenticación exitosa"
    
    # PASO 1: Registrar el host primero (obligatorio antes de generar API key)
    log_step "Registrando host en el servidor..."
    
    local os_info=$(uname -s)
    local kernel_version=$(uname -r)
    local cpu_cores=$(nproc)
    local total_memory=$(free -m | awk '/^Mem:/{print $2}')
    
    local register_response=$(curl -s -X POST "${server}/api/v1/hosts/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\":\"${host_id}\",
            \"hostname\":\"${host_id}\",
            \"ip\":\"127.0.0.1\",
            \"os\":\"${os_info}\",
            \"kernel_version\":\"${kernel_version}\",
            \"cpu_cores\":${cpu_cores},
            \"total_memory\":${total_memory}
        }" 2>&1)
    
    # Verificar si el registro fue exitoso (puede devolver 200 si ya existe)
    if echo "$register_response" | grep -q '"id"'; then
        log_info "Host registrado correctamente"
    else
        log_warn "El host podría estar ya registrado (continuando...)"
    fi
    echo ""
    
    # Generar API key
    log_step "Generando API key para el agente..."
    local api_response=$(curl -s -X POST "${server}/api/v1/agents/generate" \
        -H "Authorization: Bearer ${jwt_token}" \
        -H "Content-Type: application/json" \
        -d "{\"host_id\":\"${host_id}\"}" 2>&1)
    
    AGENT_TOKEN=$(echo "$api_response" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$AGENT_TOKEN" ] || [ "$AGENT_TOKEN" = "null" ]; then
        log_error "No se pudo generar la API key"
        echo -e "${RED}Respuesta del servidor: ${api_response}${NC}"
        
        # Si ya existe, preguntar si revocar
        if echo "$api_response" | grep -q "already exists"; then
            echo ""
            log_warn "Ya existe una API key para este host"
            echo -ne "${YELLOW}¿Deseas revocar la clave existente y generar una nueva? [s/N]: ${NC}"
            read revoke_choice
            
            if [[ "$revoke_choice" =~ ^[Ss]$ ]]; then
                log_step "Revocando API key existente..."
                curl -s -X POST "${server}/api/v1/agents/revoke" \
                    -H "Authorization: Bearer ${jwt_token}" \
                    -H "Content-Type: application/json" \
                    -d "{\"host_id\":\"${host_id}\"}" > /dev/null
                
                log_step "Generando nueva API key..."
                api_response=$(curl -s -X POST "${server}/api/v1/agents/generate" \
                    -H "Authorization: Bearer ${jwt_token}" \
                    -H "Content-Type: application/json" \
                    -d "{\"host_id\":\"${host_id}\"}" 2>&1)
                
                AGENT_TOKEN=$(echo "$api_response" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
                
                if [ -z "$AGENT_TOKEN" ] || [ "$AGENT_TOKEN" = "null" ]; then
                    log_error "No se pudo generar la API key después de revocar"
                    return 1
                fi
            else
                return 1
            fi
        else
            return 1
        fi
    fi
    
    log_success "API key generada exitosamente: ${AGENT_TOKEN:0:20}..."
    echo ""
    return 0
}

# ============================================================================
# Funciones de instalación interactiva
# ============================================================================

interactive_setup() {
    echo -e "${BOLD}=== Configuración Interactiva ===${NC}\n"
    
    # Detectar información del sistema
    detect_system_info
    
    # Opción 1: Buscar servidores automáticamente
    echo -e "${CYAN}${BOLD}¿Deseas buscar servidores LAMS automáticamente en la red?${NC}"
    echo -e "  ${GREEN}1)${NC} Sí, buscar automáticamente (recomendado)"
    echo -e "  ${GREEN}2)${NC} No, introduciré la URL manualmente"
    echo ""
    
    local choice=$(prompt_with_default "Selecciona una opción" "1")
    
    if [ "$choice" = "1" ]; then
        if discover_lams_servers; then
            # Mostrar servidores encontrados
            echo -e "\n${CYAN}${BOLD}Servidores LAMS encontrados:${NC}"
            for i in "${!local_servers[@]}"; do
                echo -e "  ${GREEN}$((i+1)))${NC} ${local_servers[$i]}"
            done
            echo -e "  ${GREEN}$((${#local_servers[@]}+1)))${NC} Introducir URL manualmente"
            echo ""
            
            local server_choice=$(prompt_with_default "Selecciona el servidor" "1")
            
            if [ "$server_choice" -le "${#local_servers[@]}" ] && [ "$server_choice" -ge 1 ]; then
                SERVER_URL="${local_servers[$((server_choice-1))]}"
                log_info "Servidor seleccionado: ${SERVER_URL}"
            else
                SERVER_URL=$(prompt_with_default "Introduce la URL del servidor LAMS" "http://192.168.0.8:8080")
            fi
        else
            SERVER_URL=$(prompt_with_default "Introduce la URL del servidor LAMS" "http://192.168.0.8:8080")
        fi
    else
        SERVER_URL=$(prompt_with_default "Introduce la URL del servidor LAMS" "http://192.168.0.8:8080")
    fi
    
    echo ""
    
    # Probar conexión
    test_server_connection "$SERVER_URL" || {
        log_warn "No se pudo verificar la conectividad, pero continuaremos..."
        echo ""
    }
    
    # Host ID primero (lo necesitamos para generar la API key)
    HOST_ID=$(prompt_with_default "ID del host" "$HOST_ID")
    echo ""
    
    # Token de autenticación - OBLIGATORIO mediante generación automática
    echo -e "${CYAN}${BOLD}Configuración de autenticación${NC}"
    echo -e "${YELLOW}El agente requiere una API key para autenticarse con el servidor${NC}"
    echo ""
    echo -e "  ${GREEN}1)${NC} Generar API key automáticamente (recomendado)"
    echo -e "  ${GREEN}2)${NC} Tengo una API key existente"
    echo ""
    
    local auth_choice=$(prompt_with_default "Selecciona una opción" "1")
    echo ""
    
    if [ "$auth_choice" = "1" ]; then
        # Generar API key automáticamente
        if ! generate_api_key "$SERVER_URL" "$HOST_ID"; then
            log_error "No se pudo generar la API key. La instalación no puede continuar sin autenticación."
            exit 1
        fi
    else
        # Pedir API key existente
        AGENT_TOKEN=$(prompt_with_default "Introduce la API key" "")
        
        if [ -z "$AGENT_TOKEN" ]; then
            log_error "La API key no puede estar vacía. La instalación no puede continuar sin autenticación."
            exit 1
        fi
    fi
    
    # Compilar localmente
    echo ""
    if command -v go &> /dev/null; then
        echo -e "${CYAN}${BOLD}Se detectó Go instalado. ¿Compilar el agente localmente?${NC}"
        local compile_choice=$(prompt_with_default "Compilar localmente [s/N]" "n")
        if [[ "$compile_choice" =~ ^[Ss]$ ]]; then
            BUILD_LOCAL=true
            log_info "El agente se compilará localmente"
        fi
    else
        log_warn "Go no está instalado. Se usará el binario pre-compilado"
        BUILD_LOCAL=false
    fi
    
    echo ""
}

# ============================================================================
# Funciones de validación y checks
# ============================================================================

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "Este script debe ejecutarse como root (usa sudo)"
        echo ""
        echo -e "${YELLOW}Ejecuta: ${BOLD}sudo $0${NC}"
        echo ""
        exit 1
    fi
}

check_dependencies() {
    log_step "Verificando dependencias del sistema..."
    
    local missing_deps=()
    
    # Verificar curl (necesario para el agente)
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    # Verificar systemd (si no se salta)
    if [ "$SKIP_SYSTEMD" = false ]; then
        if ! command -v systemctl &> /dev/null; then
            log_warn "systemd no está disponible en este sistema"
            log_info "El agente se instalará sin servicio systemd"
            SKIP_SYSTEMD=true
        fi
    fi
    
    # Verificar Go si se va a compilar localmente
    if [ "$BUILD_LOCAL" = true ]; then
        if ! command -v go &> /dev/null; then
            log_error "Go no está instalado pero se especificó --build-local"
            log_info "Opciones:"
            log_info "  1. Instala Go desde: https://go.dev/dl/"
            log_info "  2. Ejecuta sin --build-local para usar binario pre-compilado"
            exit 1
        fi
        local go_version=$(go version | awk '{print $3}')
        log_info "Go detectado: ${go_version}"
    fi
    
    # Reportar dependencias faltantes
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Dependencias faltantes: ${missing_deps[*]}"
        log_info "Instala con: ${BOLD}apt install ${missing_deps[*]}${NC} (Debian/Ubuntu)"
        log_info "          o: ${BOLD}yum install ${missing_deps[*]}${NC} (RHEL/CentOS)"
        exit 1
    fi
    
    log_success "Todas las dependencias están instaladas"
    echo ""
}

parse_args() {
    # Si no hay argumentos, activar modo interactivo
    if [ $# -eq 0 ]; then
        INTERACTIVE=true
        return
    fi
    
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --auto) 
                AUTO_MODE=true
                INTERACTIVE=false
                ;;
            --server) 
                SERVER_URL="$2"
                INTERACTIVE=false
                shift 
                ;;
            --token) 
                AGENT_TOKEN="$2"
                shift 
                ;;
            --host-id) 
                HOST_ID="$2"
                shift 
                ;;
            --build-local) 
                BUILD_LOCAL=true 
                ;;
            --skip-systemd) 
                SKIP_SYSTEMD=true 
                ;;
            --non-interactive)
                INTERACTIVE=false
                ;;
            --help) 
                show_help 
                ;;
            *) 
                log_error "Parámetro desconocido: $1"
                echo "Usa --help para ver opciones disponibles"
                exit 1 
                ;;
        esac
        shift
    done

    # En modo auto, buscar servidor automáticamente
    if [ "$AUTO_MODE" = true ]; then
        log_info "Modo automático activado"
        return
    fi
    
    # En modo CLI, validar que se proporcionó servidor
    if [ "$INTERACTIVE" = false ] && [ -z "$SERVER_URL" ]; then
        log_error "En modo no-interactivo, el parámetro --server es requerido"
        echo "Opciones:"
        echo "  1. Usa: $0 --server http://192.168.0.8:8080"
        echo "  2. Usa: $0 --auto (para auto-descubrimiento)"
        echo "  3. Usa: $0 (sin parámetros para modo interactivo)"
        exit 1
    fi
}

build_binary() {
    log_info "Compilando binario del agente..."
    
    # Obtener directorio del script
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    # Verificar que existe main.go
    if [ ! -f "$SCRIPT_DIR/main.go" ]; then
        log_error "No se encontró main.go en $SCRIPT_DIR"
        exit 1
    fi
    
    # Compilar
    cd "$SCRIPT_DIR"
    log_info "Descargando dependencias de Go..."
    go mod download
    
    log_info "Compilando (esto puede tomar unos segundos)..."
    go build -o "$BINARY_NAME" -ldflags="-s -w" main.go
    
    if [ ! -f "$BINARY_NAME" ]; then
        log_error "Falló la compilación del binario"
        exit 1
    fi
    
    log_info "Binario compilado exitosamente: $BINARY_NAME"
}

install_binary() {
    log_info "Instalando binario en $INSTALL_DIR..."
    
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    if [ ! -f "$SCRIPT_DIR/$BINARY_NAME" ]; then
        log_error "No se encontró el binario $BINARY_NAME en $SCRIPT_DIR"
        log_error "Usa --build-local para compilarlo primero"
        exit 1
    fi
    
    # Detener servicio si está corriendo
    if [ "$SKIP_SYSTEMD" = false ] && systemctl is-active --quiet lams-agent 2>/dev/null; then
        log_info "Deteniendo servicio existente..."
        systemctl stop lams-agent
    fi
    
    # Copiar binario
    cp "$SCRIPT_DIR/$BINARY_NAME" "$INSTALL_DIR/$BINARY_NAME"
    chmod +x "$INSTALL_DIR/$BINARY_NAME"
    
    log_info "Binario instalado: $INSTALL_DIR/$BINARY_NAME"
}

create_config() {
    log_info "Creando configuración en $CONFIG_DIR..."
    
    # Crear directorio de configuración
    mkdir -p "$CONFIG_DIR"
    
    # Crear archivo de configuración
    cat > "$CONFIG_FILE" <<EOF
# LAMS Agent Configuration File
# Generado automáticamente el $(date)

# URL del servidor central LAMS
LAMS_SERVER_URL=$SERVER_URL

# ID único del host
LAMS_HOST_ID=$HOST_ID

# Token de autenticación del agente
LAMS_AGENT_TOKEN=$AGENT_TOKEN

# Intervalo de recolección de métricas en segundos
LAMS_METRICS_INTERVAL=15

# Nivel de logging (debug, info, warning, error)
LAMS_LOG_LEVEL=info
EOF

    # Permisos restrictivos (puede contener token secreto)
    chmod 600 "$CONFIG_FILE"
    
    log_info "Configuración creada: $CONFIG_FILE"
}

install_systemd_service() {
    log_info "Instalando servicio systemd..."
    
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    TEMPLATE_FILE="$SCRIPT_DIR/lams-agent.service.template"
    
    # Verificar que existe el template
    if [ ! -f "$TEMPLATE_FILE" ]; then
        log_warn "No se encontró lams-agent.service.template, creando uno básico..."
        
        # Crear template básico
        cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=LAMS Monitoring Agent
Documentation=https://github.com/Mlocoes/LAMS
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lams-agent
EnvironmentFile=$CONFIG_FILE
ExecStart=$INSTALL_DIR/$BINARY_NAME

[Install]
WantedBy=multi-user.target
EOF
    else
        # Copiar template
        cp "$TEMPLATE_FILE" "$SERVICE_FILE"
    fi
    
    # Recargar systemd
    systemctl daemon-reload
    
    log_info "Servicio systemd instalado: $SERVICE_FILE"
}

start_service() {
    log_info "Habilitando y arrancando servicio..."
    
    # Habilitar para arranque automático
    systemctl enable lams-agent
    
    # Iniciar servicio
    systemctl start lams-agent
    
    # Esperar un segundo
    sleep 2
    
    # Verificar estado
    if systemctl is-active --quiet lams-agent; then
        log_info "Servicio lams-agent está corriendo correctamente"
    else
        log_error "El servicio no pudo iniciarse"
        log_info "Revisa los logs con: journalctl -u lams-agent -n 50"
        exit 1
    fi
}

show_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                                ║${NC}"
    echo -e "${GREEN}${BOLD}║         ✓  Instalación Completada Exitosamente  ✓             ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                                ║${NC}"
    echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}📁 Archivos Instalados:${NC}"
    echo -e "  ${GREEN}▶${NC} Binario:        ${BOLD}$INSTALL_DIR/$BINARY_NAME${NC}"
    echo -e "  ${GREEN}▶${NC} Configuración:  ${BOLD}$CONFIG_FILE${NC}"
    if [ "$SKIP_SYSTEMD" = false ]; then
        echo -e "  ${GREEN}▶${NC} Servicio:       ${BOLD}$SERVICE_FILE${NC}"
    fi
    echo ""
    echo -e "${CYAN}${BOLD}⚙️  Configuración:${NC}"
    echo -e "  ${GREEN}▶${NC} Servidor:       ${BOLD}$SERVER_URL${NC}"
    echo -e "  ${GREEN}▶${NC} Host ID:        ${BOLD}$HOST_ID${NC}"
    echo -e "  ${GREEN}▶${NC} Token:          ${BOLD}${AGENT_TOKEN:-<no configurado>}${NC}"
    echo ""
    
    if [ "$SKIP_SYSTEMD" = false ]; then
        echo -e "${CYAN}${BOLD}🔧 Comandos Útiles:${NC}"
        echo -e "  ${YELLOW}▶${NC} Ver estado:     ${BOLD}systemctl status lams-agent${NC}"
        echo -e "  ${YELLOW}▶${NC} Ver logs:       ${BOLD}journalctl -u lams-agent -f${NC}"
        echo -e "  ${YELLOW}▶${NC} Reiniciar:      ${BOLD}systemctl restart lams-agent${NC}"
        echo -e "  ${YELLOW}▶${NC} Detener:        ${BOLD}systemctl stop lams-agent${NC}"
        echo -e "  ${YELLOW}▶${NC} Desinstalar:    ${BOLD}./uninstall-agent.sh${NC}"
        echo ""
        
        # Verificar estado actual
        if systemctl is-active --quiet lams-agent; then
            echo -e "${GREEN}${BOLD}✓ El agente está corriendo y enviando métricas${NC}"
            echo -e "${GREEN}  Verifica en el dashboard: ${BOLD}${SERVER_URL}${NC}"
        else
            echo -e "${RED}⚠ El agente no está corriendo. Revisa los logs para detalles${NC}"
        fi
    else
        echo -e "${CYAN}${BOLD}🔧 Ejecución Manual:${NC}"
        echo -e "  Para ejecutar el agente manualmente:"
        echo -e "  ${BOLD}$INSTALL_DIR/$BINARY_NAME${NC}"
        echo ""
    fi
    
    echo ""
    echo -e "${MAGENTA}${BOLD}📊 Dashboard Web:${NC} ${BOLD}${SERVER_URL}${NC}"
    echo -e "${MAGENTA}${BOLD}📡 API Docs:${NC} ${BOLD}${SERVER_URL}/docs${NC}"
    echo ""
}

# ============================================================================
# Script principal
# ============================================================================

main() {
    # Parsear argumentos primero
    parse_args "$@"
    
    # Mostrar banner
    print_banner
    
    # Verificar root
    check_root
    
    # Verificar dependencias
    check_dependencies
    
    # Modo interactivo
    if [ "$INTERACTIVE" = true ]; then
        interactive_setup
    fi
    
    # Modo automático
    if [ "$AUTO_MODE" = true ]; then
        log_step "Iniciando auto-configuración..."
        echo ""
        
        detect_system_info
        
        if discover_lams_servers; then
            if [ ${#local_servers[@]} -eq 1 ]; then
                SERVER_URL="${local_servers[0]}"
                log_success "Usando servidor detectado: ${SERVER_URL}"
            else
                SERVER_URL="${local_servers[0]}"
                log_info "Múltiples servidores detectados, usando el primero: ${SERVER_URL}"
            fi
        else
            log_error "No se pudo detectar ningún servidor LAMS automáticamente"
            log_info "Usa modo interactivo: sudo $0"
            log_info "O especifica el servidor: sudo $0 --server http://..."
            exit 1
        fi
        
        # Test de conectividad
        if ! test_server_connection "$SERVER_URL"; then
            log_error "No se pudo conectar al servidor detectado"
            exit 1
        fi
        
        echo ""
    fi
    
    # Validar que tenemos servidor configurado
    if [ -z "$SERVER_URL" ]; then
        log_error "No se configuró ningún servidor LAMS"
        exit 1
    fi
    
    # Validar que el token existe (CRÍTICO para autenticación)
    if [ -z "$AGENT_TOKEN" ]; then
        log_error "La API key es obligatoria para la autenticación del agente"
        log_error "El agente no puede funcionar sin una API key válida"
        echo ""
        log_info "Para generar una API key, ejecuta el script en modo interactivo:"
        log_info "  ${BOLD}sudo $0${NC}"
        echo ""
        log_info "O genera manualmente una API key desde el servidor y usa:"
        log_info "  ${BOLD}sudo $0 --server URL --token TU_API_KEY${NC}"
        echo ""
        exit 1
    fi
    
    # Mostrar resumen de configuración
    echo -e "${BOLD}=== Resumen de Configuración ===${NC}"
    echo -e "  Servidor:     ${GREEN}${SERVER_URL}${NC}"
    echo -e "  Host ID:      ${GREEN}${HOST_ID}${NC}"
    echo -e "  Token:        ${GREEN}${AGENT_TOKEN:0:20}...${NC} ${CYAN}(${#AGENT_TOKEN} caracteres)${NC}"
    echo -e "  Compilación:  ${GREEN}$([ "$BUILD_LOCAL" = true ] && echo "Local (Go)" || echo "Binario pre-compilado")${NC}"
    echo -e "  Systemd:      ${GREEN}$([ "$SKIP_SYSTEMD" = false ] && echo "Sí" || echo "No")${NC}"
    echo ""
    
    # Confirmación (solo en modo interactivo)
    if [ "$INTERACTIVE" = true ]; then
        echo -e "${YELLOW}${BOLD}¿Continuar con la instalación?${NC} [S/n]"
        read -r confirmation
        if [[ "$confirmation" =~ ^[Nn]$ ]]; then
            log_warn "Instalación cancelada por el usuario"
            exit 0
        fi
        echo ""
    fi
    
    # Compilar si se solicitó
    if [ "$BUILD_LOCAL" = true ]; then
        build_binary
    fi
    
    # Instalar binario
    install_binary
    
    # Crear configuración
    create_config
    
    # Instalar y arrancar servicio systemd (si no se salta)
    if [ "$SKIP_SYSTEMD" = false ]; then
        install_systemd_service
        start_service
    fi
    
    # Mostrar resumen final
    show_summary
    
    log_success "¡Instalación completada exitosamente!"
    echo ""
}

# Ejecutar script principal
main "$@"
