#!/bin/bash
# Script para ejecutar tests de LAMS backend

set -e

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     LAMS Backend Test Suite           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Navegar al directorio del servidor
cd "$(dirname "$0")"

# Opción 1: Tests rápidos (sin cobertura)
if [ "$1" == "quick" ]; then
    echo -e "${GREEN}Ejecutando tests rápidos...${NC}"
    pytest tests/ -v
    exit 0
fi

# Opción 2: Tests específicos
if [ "$1" == "file" ] && [ -n "$2" ]; then
    echo -e "${GREEN}Ejecutando tests de $2...${NC}"
    pytest "tests/$2" -v
    exit 0
fi

# Opción 3: Tests por módulo
if [ "$1" == "module" ] && [ -n "$2" ]; then
    echo -e "${GREEN}Ejecutando tests de módulo $2...${NC}"
    pytest "tests/test_$2.py" -v
    exit 0
fi

# Opción 4: Tests con cobertura (default)
echo -e "${GREEN}Ejecutando suite completa con análisis de cobertura...${NC}"
echo ""

# Ejecutar tests con cobertura
pytest tests/ \
    --cov=. \
    --cov-report=html \
    --cov-report=term \
    --cov-report=term-missing \
    -v

# Mostrar resumen
echo ""
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Tests Completados                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Reporte HTML generado en: htmlcov/index.html${NC}"
echo -e "${GREEN}Abrir con: firefox htmlcov/index.html${NC}"
echo ""
echo -e "${BLUE}Uso:${NC}"
echo -e "  ./run_tests.sh             # Todos los tests con cobertura"
echo -e "  ./run_tests.sh quick       # Tests rápidos sin cobertura"
echo -e "  ./run_tests.sh module auth # Tests de módulo específico"
echo -e "  ./run_tests.sh file test_api_hosts.py # Archivo específico"
