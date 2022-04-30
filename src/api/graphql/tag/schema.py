from typing import Optional

import strawberry
from sqlalchemy import select
from strawberry.types import Info

from api.db.models import Tag as TagModel
from api.graphql.core.relay import Connection, PaginationHelper
from api.graphql.tag.dataloaders import TagByIdLoader
from api.graphql.tag.types import Tag, TagsFilter, TagsSorter


@strawberry.type
class Query:
    @strawberry.field
    async def tag(self, info: Info, id: int) -> Optional[Tag]:
        return await TagByIdLoader(info.context).load(id)

    @strawberry.field
    async def tags(
        self,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        sortBy: TagsSorter = TagsSorter.default(),
        filter: TagsFilter = TagsFilter.default(),
    ) -> Connection[Tag]:
        helper = PaginationHelper(before, after, first, last)
        query = filter.add_filters(sortBy.add_sorters(select(TagModel.id)))
        _data = await helper.paginate(query, info.context["db"])
        _data["nodes"] = await TagByIdLoader(info.context).load_many(
            [_node[0] for _node in _data["nodes"]]
        )
        return helper.build_connection(**_data)
