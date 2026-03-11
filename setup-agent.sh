#!/bin/bash
# Script para configurar el agente LAMS

echo "🔧 Configurando agente LAMS..."

# 1. Registrar el host
echo "📝 Registrando host zeus2 en el servidor..."
curl -s -X POST "http://localhost:8080/api/v1/hosts/register" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "zeus2",
    "hostname": "zeus2",
    "ip": "127.0.0.1",
    "os": "Linux",
    "kernel_version": "'"$(uname -r)"'",
    "cpu_cores": '"$(nproc)"',
    "total_memory": '"$(free -m | awk '/^Mem:/{print $2}')"'
  }' | jq .

# 2. Obtener token de admin
echo ""
echo "🔑 Obteniendo token de administrador..."
ADMIN_TOKEN=$(curl -s -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@lams.io","password":"XrJCb2-3KQaZ6hZUf-t2fg"}' | jq -r '.access_token')

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
    echo "❌ Error: No se pudo obtener el token de administrador"
    exit 1
fi

echo "✅ Token obtenido"

# 3. Generar API key para el agente
echo ""
echo "🔐 Generando API key para el agente..."
API_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/v1/agents/generate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"host_id": "zeus2"}')

API_KEY=$(echo "$API_RESPONSE" | jq -r '.api_key')

if [ -z "$API_KEY" ] || [ "$API_KEY" = "null" ]; then
    echo "❌ Error generando API key:"
    echo "$API_RESPONSE" | jq .
    exit 1
fi

echo "✅ API key generada: ${API_KEY:0:20}..."

# 4. Actualizar configuración
echo ""
echo "📝 Actualizando configuración del agente..."
cat > /home/mloco/Escritorio/LAMS/agent/agent.conf << EOF
# LAMS Agent Configuration
LAMS_SERVER_URL=http://localhost:8080
LAMS_HOST_ID=zeus2
LAMS_AGENT_TOKEN=$API_KEY
LAMS_METRICS_INTERVAL=15
LAMS_LOG_LEVEL=info
EOF

echo "✅ Configuración actualizada"

# 5. Instrucciones finales
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Configuración completada!"
echo ""
echo "Para aplicar los cambios, ejecuta:"
echo ""
echo "  sudo cp /home/mloco/Escritorio/LAMS/agent/agent.conf /etc/lams/"
echo "  sudo systemctl restart lams-agent"
echo "  sudo systemctl status lams-agent"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

