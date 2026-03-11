#!/bin/bash
# Comandos para aplicar la configuración del agente LAMS
# Ejecuta este script con: sudo bash apply-agent-config.sh

echo "🔧 Aplicando configuración del agente LAMS..."

# Copiar configuración
echo "📋 Copiando configuración a /etc/lams/..."
cp /home/mloco/Escritorio/LAMS/agent/agent.conf /etc/lams/

# Verificar que se copió correctamente
if [ -f "/etc/lams/agent.conf" ]; then
    echo "✅ Configuración copiada correctamente"
    echo ""
    echo "📄 Contenido de /etc/lams/agent.conf:"
    cat /etc/lams/agent.conf
else
    echo "❌ Error: No se pudo copiar la configuración"
    exit 1
fi

# Reiniciar servicio
echo ""
echo "🔄 Reiniciando servicio lams-agent..."
systemctl restart lams-agent

# Esperar un momento
sleep 2

# Mostrar estado
echo ""
echo "📊 Estado del servicio:"
systemctl status lams-agent --no-pager -l | head -20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Configuración aplicada!"
echo ""
echo "Para ver los logs del agente en tiempo real:"
echo "  sudo journalctl -u lams-agent -f"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
