#!/bin/bash

# Script para compilar y ejecutar el agente LAMS
# Captura métricas del servidor zeus2 cada 15 segundos

cd "$(dirname "$0")/agent"

echo "🔨 Compilando agente Go..."
go build -o lams-agent main.go

if [ $? -ne 0 ]; then
    echo "❌ Error compilando el agente"
    exit 1
fi

echo "✅ Agente compilado exitosamente"
echo ""
echo "🚀 Iniciando agente LAMS..."
echo "   - Host ID: zeus2"  
echo "   - Servidor: http://192.168.0.8:8080"
echo "   - Intervalo: 15 segundos"
echo ""

# Configurar variables de entorno
export LAMS_SERVER_URL="http://192.168.0.8:8080"
export LAMS_HOST_ID="zeus2"

# Ejecutar el agente
./lams-agent
