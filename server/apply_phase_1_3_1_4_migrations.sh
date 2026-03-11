#!/usr/bin/env bash
# Script para aplicar migraciones de Fase 1.3 y 1.4
# Aplica las tablas notification_configs y remote_commands

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_NAME="${LAMS_DB_NAME:-lams_db}"
DB_USER="${LAMS_DB_USER:-postgres}"

echo "════════════════════════════════════════════════════════"
echo "  LAMS - Aplicación de Migraciones Fase 1.3 y 1.4"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Base de datos: $DB_NAME"
echo "Usuario: $DB_USER"
echo ""

# Check if running as postgres user or with sudo
if [ "$USER" != "$DB_USER" ] && [ "$EUID" -ne 0 ]; then
    echo "⚠️  Este script debe ejecutarse como usuario $DB_USER o con sudo"
    echo ""
    echo "Ejecuta:"
    echo "  sudo $0"
    echo "o:"
    echo "  sudo -u $DB_USER $0"
    exit 1
fi

# Function to apply migration
apply_migration() {
    local migration_file="$1"
    local migration_name=$(basename "$migration_file" .sql)
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Aplicando migración: $migration_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ ! -f "$migration_file" ]; then
        echo "❌ Error: Archivo no encontrado: $migration_file"
        return 1
    fi
    
    if sudo -u "$DB_USER" psql "$DB_NAME" -f "$migration_file"; then
        echo "✅ Migración $migration_name aplicada correctamente"
        echo ""
        return 0
    else
        echo "❌ Error aplicando migración $migration_name"
        return 1
    fi
}

# Apply migrations
echo "🚀 Aplicando migraciones..."
echo ""

# Fase 1.3: Notificaciones
if apply_migration "$SCRIPT_DIR/migrations/add_notification_configs_table.sql"; then
    echo "✓ Fase 1.3: notification_configs [OK]"
else
    echo "✗ Fase 1.3: notification_configs [FAILED]"
    exit 1
fi

# Fase 1.4: Comandos Remotos
if apply_migration "$SCRIPT_DIR/migrations/add_remote_commands_table.sql"; then
    echo "✓ Fase 1.4: remote_commands [OK]"
else
    echo "✗ Fase 1.4: remote_commands [FAILED]"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅  Todas las migraciones aplicadas correctamente"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📊 Verificando tablas creadas..."
echo ""

# Verify tables exist
sudo -u "$DB_USER" psql "$DB_NAME" -c "\dt notification_configs" 2>/dev/null
sudo -u "$DB_USER" psql "$DB_NAME" -c "\dt remote_commands" 2>/dev/null

echo ""
echo "🎉 Instalación completada con éxito"
echo ""
echo "Próximos pasos:"
echo "  1. Reiniciar el servidor backend:"
echo "     docker-compose restart server"
echo ""
echo "  2. Reiniciar agentes en hosts monitoreados:"
echo "     systemctl restart lams-agent"
echo ""
echo "  3. Acceder al dashboard y configurar notificaciones:"
echo "     http://localhost:3000 → Notificaciones"
echo ""
echo "📖 Documentación completa: docs/FASE1_3_Y_1_4_COMPLETADA.md"
echo ""
