#!/bin/bash
# Script de utilidad para resetear contraseñas en LAMS

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        LAMS - Utilidad de Reseteo de Contraseñas          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Verificar que el contenedor esté corriendo
if ! docker ps | grep -q lams-server; then
    echo "❌ Error: El contenedor lams-server no está en ejecución"
    echo "   Ejecuta: docker-compose up -d"
    exit 1
fi

echo "📋 Usuarios disponibles:"
docker exec lams-server python -c "
import asyncio
from sqlalchemy.future import select
from database.database import async_session_maker
from database.models import User

async def list_users():
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            print(f'   • {user.email} ({user.role})')

asyncio.run(list_users())
" 2>/dev/null

echo ""
echo "🔧 Reseteando contraseña de admin@lams.io a 'lams2024'..."

docker exec lams-server python reset_admin_password.py

echo ""
echo "✅ ¡Listo! Ahora puedes iniciar sesión con:"
echo "   • Email: admin@lams.io"
echo "   • Password: lams2024"
echo ""
echo "🌐 Accede al dashboard en: http://localhost:3001"
