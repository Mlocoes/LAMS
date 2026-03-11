#!/bin/bash
set -e

# ============================================================================
# LAMS Agent Uninstallation Script
# ============================================================================
# Este script desinstala el agente de monitoreo LAMS del sistema
# 
# Uso:
#   sudo ./uninstall-agent.sh [opciones]
#
# Opciones:
#   --keep-config       Mantener archivo de configuración  
#   --force             No pedir confirmación
#   --help              Mostrar esta ayuda
# ============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
KEEP_CONFIG=false
FORCE=false
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/lams"
CONFIG_FILE="$CONFIG_DIR/agent.conf"
SERVICE_FILE="/etc/systemd/system/lams-agent.service"
BINARY_NAME="lams-agent"

# ============================================================================
# Funciones auxiliares
# ============================================================================

print_banner() {
    echo -e "${BLUE}"
    echo "============================================"
    echo "   LAMS Agent Uninstallation Script"
    echo "   Linux Autonomous Monitoring System"
    echo "============================================"
    echo -e "${NC}"
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

show_help() {
    cat << EOF
LAMS Agent Uninstallation Script

Uso:
  sudo $0 [opciones]

Opciones:
  --keep-config       Mantener archivo de configuración en $CONFIG_DIR
  --force             No pedir confirmación
  --help              Mostrar esta ayuda

Ejemplos:
  # Desinstalación normal (pide confirmación)
  sudo $0

  # Desinstalar manteniendo configuración
  sudo $0 --keep-config

  # Desinstalar sin confirmación
  sudo $0 --force

EOF
    exit 0
}

check_root() {
    if [ "$EUID" -ne 0 ]; then 
        log_error "Este script debe ejecutarse como root (usa sudo)"
        exit 1
    fi
}

parse_args() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --keep-config) KEEP_CONFIG=true ;;
            --force) FORCE=true ;;
            --help) show_help ;;
            *) 
                log_error "Parámetro desconocido: $1"
                echo "Usa --help para ver opciones disponibles"
                exit 1 
                ;;
        esac
        shift
    done
}

confirm_uninstall() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
    echo ""
    log_warn "Esta acción desinstalará el agente LAMS del sistema"
    echo ""
    echo "Se eliminarán:"
    echo "  - Binario: $INSTALL_DIR/$BINARY_NAME"
    echo "  - Servicio systemd: $SERVICE_FILE"
    if [ "$KEEP_CONFIG" = false ]; then
        echo "  - Configuración: $CONFIG_DIR"
    else
        log_info "La configuración en $CONFIG_DIR será CONSERVADA"
    fi
    echo ""
    read -p "¿Deseas continuar? (s/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
        log_info "Desinstalación cancelada"
        exit 0
    fi
}

stop_service() {
    if systemctl list-unit-files | grep -q "lams-agent.service"; then
        log_info "Deteniendo servicio lams-agent..."
        
        if systemctl is-active --quiet lams-agent; then
            systemctl stop lams-agent
            log_info "Servicio detenido"
        fi
        
        if systemctl is-enabled --quiet lams-agent 2>/dev/null; then
            systemctl disable lams-agent
            log_info "Servicio deshabilitado"
        fi
    else
        log_info "Servicio systemd no encontrado (puede que no estuviera instalado)"
    fi
}

remove_service_file() {
    if [ -f "$SERVICE_FILE" ]; then
        log_info "Eliminando archivo de servicio systemd..."
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
        log_info "Archivo de servicio eliminado: $SERVICE_FILE"
    fi
}

remove_binary() {
    if [ -f "$INSTALL_DIR/$BINARY_NAME" ]; then
        log_info "Eliminando binario..."
        rm -f "$INSTALL_DIR/$BINARY_NAME"
        log_info "Binario eliminado: $INSTALL_DIR/$BINARY_NAME"
    else
        log_warn "Binario no encontrado en $INSTALL_DIR/$BINARY_NAME"
    fi
}

remove_config() {
    if [ "$KEEP_CONFIG" = true ]; then
        log_info "Manteniendo configuración en $CONFIG_DIR (--keep-config especificado)"
        return 0
    fi
    
    if [ -d "$CONFIG_DIR" ]; then
        log_info "Eliminando configuración..."
        rm -rf "$CONFIG_DIR"
        log_info "Configuración eliminada: $CONFIG_DIR"
    fi
}

show_summary() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Desinstalación Completada${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    
    if [ "$KEEP_CONFIG" = true ]; then
        log_info "Configuración conservada en: $CONFIG_DIR"
        log_info "Para reinstalar: ./install-agent.sh --server <URL>"
    else
        log_info "El agente LAMS ha sido completamente eliminado"
    fi
    echo ""
}

# ============================================================================
# Script principal
# ============================================================================

main() {
    print_banner
    
    # Parsear argumentos
    parse_args "$@"
    
    # Verificar root
    check_root
    
    # Confirmar desinstalación
    confirm_uninstall
    
    # Detener y deshabilitar servicio
    stop_service
    
    # Eliminar archivos
    remove_service_file
    remove_binary
    remove_config
    
    # Mostrar resumen
    show_summary
    
    log_info "¡Desinstalación completada!"
}

# Ejecutar script principal
main "$@"
