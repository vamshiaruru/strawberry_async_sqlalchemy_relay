import logging
import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as exc:
            logger.error(exc)
            logger.error(traceback.format_exc())
            await session.rollback()
            raise
        finally:
            await session.close()
