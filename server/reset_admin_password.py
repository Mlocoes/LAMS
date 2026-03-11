#!/usr/bin/env python3
"""Script para resetear la contraseña del usuario admin"""
import asyncio
import os
from sqlalchemy.future import select
from database.database import async_session_maker
from database.models import User
from auth.security import get_password_hash

async def reset_admin_password():
    # Get admin credentials from environment variables
    admin_email = os.getenv("ADMIN_EMAIL", "admin@lams.io")
    admin_password = os.getenv("ADMIN_PASSWORD", "lams2024")
    
    async with async_session_maker() as session:
        # Buscar el usuario admin
        result = await session.execute(select(User).where(User.email == admin_email))
        admin = result.scalar_one_or_none()
        
        if admin:
            # Actualizar la contraseña
            admin.password_hash = get_password_hash(admin_password)
            await session.commit()
            print(f"✅ Contraseña del usuario {admin_email} reseteada")
        else:
            # Crear el usuario admin si no existe
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                is_admin=True,
            )
            session.add(admin)
            await session.commit()
            print(f"✅ Usuario {admin_email} creado")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())
