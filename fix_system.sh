#!/bin/bash
# Script para reparar LAMS después de la implementación del Sprint 1
# Este script ejecuta las migraciones de BD necesarias y reinicia los servicios

set -e

echo "================================"
echo "LAMS System Repair Script"
echo "Sprint 1 - Database Migration"
echo "================================"
echo ""

cd "$(dirname "$0")"

echo "1. Deteniendo servicios LAMS..."
docker compose down || true
sleep 2

echo ""
echo "2. Reconstruyendo imágenes Docker con código actualizado..."
docker compose build --no-cache server

echo ""
echo "3. Verificando base de datos..."
docker compose up -d postgres
sleep 5

echo ""
echo "4. Ejecutando migraciones de base de datos..."
# Ejecutar migraciones de alembic - usar python -m alembic
docker compose run --rm --workdir /app server python -m alembic upgrade head

echo ""
echo "5. Iniciando todos los servicios..."
docker compose up -d

echo ""
echo "6. Esperando a que los servicios estén listos..."
sleep 10

echo ""
echo "7. Verificando estado de los servicios..."
docker compose ps

echo ""
echo "8. Probando conectividad..."
echo "- Backend (http://localhost:8080/api/v1/health):"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/health || echo "No disponible"

echo ""
echo "- Frontend (http://localhost:3001):"  
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 || echo "No disponible"

echo ""
echo "================================"
echo "Reparación completada"
echo "================================"
echo ""
echo "Accede a LAMS en: http://localhost:3001"
echo "API disponible en: http://localhost:8080"
echo "Grafana: http://localhost:3002"
echo "Prometheus: http://localhost:9090"
echo ""
echo "Para ver logs:"
echo "  docker compose logs -f server"
echo "  docker compose logs -f frontend"