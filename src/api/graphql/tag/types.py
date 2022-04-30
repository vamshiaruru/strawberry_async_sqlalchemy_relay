from enum import Enum
from typing import List, Optional

import strawberry
from graphql_relay import from_global_id
from sqlalchemy.sql.selectable import Select

from api.db.models import Tag as TagModel
from api.graphql.core.types import BaseFilter, BaseSorter


@strawberry.enum
class TagsSorterFields(Enum):
    NAME = "NAME"


@strawberry.input
class TagsSorter(BaseSorter):
    field: Optional[str] = None

    def _add_sorters(self, query: Select) -> Select:
        sqla_sorter = self.get_sqlalchemy_sorter()
        if self.field:
            query = query.order_by(sqla_sorter(TagModel.name))
        # add a default sorter
        query = query.order_by(sqla_sorter(TagModel.id))
        return query


@strawberry.input
class TagsFilter(BaseFilter):
    ids: Optional[List[str]] = None
    search: Optional[str] = None

    def _add_filters(self, query: Select) -> Select:
        if self.ids:
            ids = [int(from_global_id(id)[1]) for id in self.ids]
            query = query.filter(TagModel.id.in_(ids))
        if self.search:
            query = query.filter(TagModel.slug.like(f"%{self.search.lower()}%"))
        return query


@strawberry.type
class Tag:
    id: strawberry.ID
    name: str
