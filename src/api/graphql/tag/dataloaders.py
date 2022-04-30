from sqlalchemy import select

from api.db.models import Tag
from api.graphql.core.dataloader import DataLoader


class TagByIdLoader(DataLoader):
    context_key = "tag_by_id"
    order_key = "id"

    async def batch_load_fn(self, keys):
        query = select(Tag).filter(Tag.id.in_(keys))
        res = await self.context["db"].execute(query)
        return res.scalars().all()
