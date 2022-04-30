from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.db.models import Resource
from api.graphql.core.dataloader import DataLoader


class ResourceByIdLoader(DataLoader):
    context_key = "resource_by_id"
    order_key = "id"

    async def batch_load_fn(self, keys):
        query = (
            select(Resource)
            .where(Resource.id.in_(keys))
            .options(selectinload(Resource.tags))
        )
        session = self.context["db"]
        res = await session.execute(query)
        return res.scalars().all()
