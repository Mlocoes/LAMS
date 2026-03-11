"""Script to create all database tables"""
import asyncio
from database.database import Base, engine
from database import models  # noqa: F401 - Import to register all models


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created successfully")
    print(f"Tables: {list(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    asyncio.run(create_tables())
