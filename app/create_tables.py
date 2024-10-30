# create_tables.py
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base  # Ensure this points to your Base definition
from app.config import settings  # Adjust based on where your settings are

async def create_tables():
    async_engine = create_async_engine(settings.database_url, echo=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await async_engine.dispose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(create_tables())