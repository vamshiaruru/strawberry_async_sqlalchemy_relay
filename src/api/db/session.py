from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.settings import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_dsn)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
