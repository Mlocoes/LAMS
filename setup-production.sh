#!/bin/bash

# LAMS Production Setup Script
# Este script prepara el entorno de producción con Traefik

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║                                                      ║"
echo "║         LAMS Production Setup                        ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}[ERROR]${NC} Este script debe ejecutarse como root (use sudo)"
    exit 1
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Docker no está instalado"
    echo "Instala Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check Docker Compose installation
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Docker Compose no está instalado"
    echo "Instala Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}[✓]${NC} Docker y Docker Compose detectados"
echo ""

# Create necessary directories
echo -e "${YELLOW}[INFO]${NC} Creando directorios necesarios..."
mkdir -p traefik/letsencrypt
mkdir -p traefik/logs
mkdir -p traefik/dynamic
chmod 600 traefik/letsencrypt

echo -e "${GREEN}[✓]${NC} Directorios creados"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}[INFO]${NC} Archivo .env no encontrado, copiando desde .env.example"
    cp .env.example .env
    echo -e "${RED}[IMPORTANTE]${NC} Edita el archivo .env con tu configuración:"
    echo "  - DOMAIN: Tu dominio real"
    echo "  - ACME_EMAIL: Tu email para Let's Encrypt"
    echo "  - POSTGRES_PASSWORD: Contraseña segura"
    echo "  - SECRET_KEY: Clave secreta JWT"
    echo "  - ADMIN_PASSWORD: Contraseña del administrador"
    echo ""
    echo "Después ejecuta nuevamente este script"
    exit 0
fi

echo -e "${GREEN}[✓]${NC} Archivo .env encontrado"
echo ""

# Load environment variables
source .env

# Validate critical variables
if [ "$POSTGRES_PASSWORD" = "CHANGE_THIS_SECURE_PASSWORD" ]; then
    echo -e "${RED}[ERROR]${NC} Debes cambiar POSTGRES_PASSWORD en .env"
    exit 1
fi

if [ "$SECRET_KEY" = "CHANGE_THIS_TO_RANDOM_64_CHAR_HEX" ]; then
    echo -e "${RED}[ERROR]${NC} Debes cambiar SECRET_KEY en .env"
    exit 1
fi

if [ "$ADMIN_PASSWORD" = "CHANGE_THIS_ADMIN_PASSWORD" ]; then
    echo -e "${RED}[ERROR]${NC} Debes cambiar ADMIN_PASSWORD en .env"
    exit 1
fi

echo -e "${GREEN}[✓]${NC} Variables de entorno validadas"
echo ""

# Update Traefik configuration with domain
echo -e "${YELLOW}[INFO]${NC} Actualizando configuración de Traefik..."
sed -i "s/lams\.example\.com/$DOMAIN/g" traefik/traefik.yml
sed -i "s/admin@example\.com/$ACME_EMAIL/g" traefik/traefik.yml

echo -e "${GREEN}[✓]${NC} Configuración actualizada"
echo ""

# Create acme.json if it doesn't exist
if [ ! -f traefik/letsencrypt/acme.json ]; then
    touch traefik/letsencrypt/acme.json
    chmod 600 traefik/letsencrypt/acme.json
    echo -e "${GREEN}[✓]${NC} Archivo acme.json creado"
fi

# Build images
echo -e "${YELLOW}[INFO]${NC} Construyendo imágenes Docker..."
docker-compose -f docker-compose.production.yml build

echo -e "${GREEN}[✓]${NC} Imágenes construidas"
echo ""

# Start services
echo -e "${YELLOW}[INFO]${NC} Iniciando servicios..."
docker-compose -f docker-compose.production.yml up -d

echo -e "${GREEN}[✓]${NC} Servicios iniciados"
echo ""

# Wait for services to be healthy
echo -e "${YELLOW}[INFO]${NC} Esperando a que los servicios estén listos..."
sleep 10

# Show status
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✓ LAMS Production está funcionando${NC}"
echo ""
echo "Servicios disponibles:"
echo "  • Dashboard: https://$DOMAIN"
echo "  • API: https://api.$DOMAIN"
echo "  • Traefik Dashboard: https://traefik.$DOMAIN (solo localhost)"
echo ""
echo "Estado de servicios:"
docker-compose -f docker-compose.production.yml ps
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo "Próximos pasos:"
echo "  1. Configura DNS A records para tu dominio"
echo "     - $DOMAIN → IP_DEL_SERVIDOR"
echo "     - api.$DOMAIN → IP_DEL_SERVIDOR"
echo "     - traefik.$DOMAIN → IP_DEL_SERVIDOR"
echo ""
echo "  2. Espera a que Let's Encrypt genere los certificados SSL"
echo "     (puede tomar unos minutos)"
echo ""
echo "  3. Verifica los logs:"
echo "     docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "  4. Accede al dashboard en https://$DOMAIN"
echo ""
echo "════════════════════════════════════════════════════════"
