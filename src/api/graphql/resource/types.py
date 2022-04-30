from enum import Enum
from typing import Optional, List
import strawberry
from graphql_relay import from_global_id
from sqlalchemy import func
from sqlalchemy.sql.selectable import Select
from api.db.models import Resource as ResourceModel, Tag as TagModel, ResourceTagAssociation
from api.graphql.tag.types import Tag
from api.graphql.core.types import BaseFilter, BaseSorter

@strawberry.enum
class ResourcesSorterFields(str, Enum):
    NAME = "NAME"


@strawberry.input
class ResourcesSorter(BaseSorter):
    field: Optional[ResourcesSorterFields] = None

    def _add_sorters(self, query: Select) -> Select:
        sqla_sorter = self.get_sqlalchemy_sorter()
        if self.field:
            query = query.order_by(sqla_sorter(ResourceModel.name))
        # add a default sorter
        query = query.order_by(sqla_sorter(ResourceModel.id))
        return query

@strawberry.input
class ResourcesFilter(BaseFilter):
    ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    search: Optional[str] = None

    def validate(self) -> bool:
        if self.ids:
            assert len(self.ids) <= 10, "Cannot provide more than ten ids at a time."
        if self.tags:
            assert len(self.tags) <= 10, "Cannot provide more than ten tags at a time"
        return True

    def _add_filters(self, query: Select):
        if self.ids:
            ids = [int(from_global_id(id)[1]) for id in self.ids]
            query = query.filter(ResourceModel.id.in_(ids))
        if self.tags:
            query = (
                query.filter(
                    ResourceModel.id == ResourceTagAssociation.resource_id,
                    ResourceTagAssociation.tag_id == TagModel.id,
                    TagModel.name.in_(self.tags),
                )
                .group_by(ResourceModel.id)
                .having(func.count(ResourceModel.id) >= len(self.tags))
            )
        if self.search:
            query = query.filter(ResourceModel.slug.like(f"%{self.search.lower()}%"))
        return query

@strawberry.type
class Resource:
    id: strawberry.ID
    name: str
    description: str

    @strawberry.field
    async def tags(self) -> List[Tag]:
        return self.tags

