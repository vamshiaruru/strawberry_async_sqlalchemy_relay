import strawberry
from strawberry.types import Info
from sqlalchemy import select

from api.db.models import Resource as ResourceModel
from api.graphql.core.relay import Connection, Optional, PaginationHelper
from api.graphql.resource.dataloaders import ResourceByIdLoader
from api.graphql.resource.types import Resource, ResourcesSorter, ResourcesFilter

@strawberry.type
class Query:
    @strawberry.field
    async def resource(self, info: Info, id: int) -> Resource:
        return await ResourceByIdLoader(info.context).load(id)

    @strawberry.field
    async def resources(
        self,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        sortBy: ResourcesSorter = ResourcesSorter.default(),
        filter: ResourcesFilter = ResourcesFilter.default(),
    ) -> Connection[Resource]:
        """
        We fetch paginated ids first and then use dataloader to fetch resources
        associated with those ids to leverage dataloader cache.
        """
        db = info.context["db"]
        helper = PaginationHelper(before, after, first, last)
        query = sortBy.add_sorters(filter.add_filters(select(ResourceModel.id)))
        _data = await helper.paginate(query=query, db=db)
        _data["nodes"] = await ResourceByIdLoader(info.context).load_many(
            _node[0] for _node in _data["nodes"]
        )
        return helper.build_connection(**_data)
