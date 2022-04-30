from typing import Generic, List, Optional, TypeVar

import strawberry
from aio_sqlakeyset.paging import get_page
from aio_sqlakeyset.results import Paging, unserialize_bookmark
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Select

from exceptions import InvalidPaginationArgsError

GenericType = TypeVar("GenericType")


@strawberry.type
class Connection(Generic[GenericType]):
    """Represents a paginated relationship between two entities

    This pattern is used when the relationship itself has attributes.
    In a Facebook-based domain example, a friendship between two people
    would be a connection that might have a `friendshipStartTime`
    """

    page_info: "PageInfo"
    edges: list["Edge[GenericType]"]


@strawberry.type
class PageInfo:
    """Pagination context to navigate objects with cursor-based pagination

    Instead of classic offset pagination via `page` and `limit` parameters,
    here we have a cursor of the last object and we fetch items starting from that one

    Read more at:
        - https://graphql.org/learn/pagination/#pagination-and-edges
        - https://relay.dev/graphql/connections.htm
    """

    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]


@strawberry.type
class Edge(Generic[GenericType]):
    """An edge may contain additional information of the relationship. This is the trivial case"""

    node: GenericType
    cursor: str


class PaginationHelper:
    """
    Helper object, takes a query and returns relay compliant paginated data.
    Create a new helper object for every new query. Don't reuse existing helper
    objects
    """

    def __init__(
        self,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
    ):
        self.before = before
        self.after = after
        self.first = first
        self.last = last

        self.validate()

    def validate(self):
        if not (self.first or self.last):
            raise InvalidPaginationArgsError("Please provide one of first or last.")

        if self.first and self.last:
            raise InvalidPaginationArgsError(
                "Providing both first and last is strongly discouraged, as it "
                "leads to confusing queries and results. This server does not "
                "support providing both of them."
            )

        if self.first and self.first < 0:
            raise InvalidPaginationArgsError("First cannot be less than zero.")
        if self.last and self.last < 0:
            raise InvalidPaginationArgsError("Last cannot be less than zero.")

        if self.before and self.last is None:
            raise InvalidPaginationArgsError("Before without last is not supported.")
        if self.after and self.first is None:
            raise InvalidPaginationArgsError("After without first is not supported.")

        if self.before and self.after:
            raise InvalidPaginationArgsError(
                "Mixing before and after is not supported."
            )

    @property
    def mode(self):
        if self.last:
            return "backwards"
        if self.first:
            return "forwards"

    def __translate_args_to_sqlakeyset_args(self):
        backwards = self.mode == "backwards"
        cursor = self.before if backwards else self.after
        per_page = self.last if backwards else self.first
        place, _ = unserialize_bookmark(cursor) if cursor else (None, None)
        return {"backwards": backwards, "place": place, "per_page": per_page}

    def build_connection(self, nodes: List, paging: Paging) -> Connection:
        """Build the connection object to return."""
        edges = [Edge(node=node, cursor="") for node in nodes]
        if edges:
            edges[0].cursor = paging.bookmark_first
            # TODO: Add cursor for other edges as well.
            edges[-1].cursor = paging.bookmark_last
        page_info = PageInfo(
            has_next_page=paging.has_next,
            has_previous_page=paging.has_previous,
            start_cursor=paging.bookmark_first,
            end_cursor=paging.bookmark_last,
        )
        return Connection(page_info=page_info, edges=edges)

    async def paginate(self, query: Select, db: AsyncSession):
        """
        Paginates the given query with pagination data. Pass as effecient a query
        as possible, and fetch extra information from dataloader if needed. Or,
        call this from dataloader itself if needed.
        """
        sqlakeyset_args = self.__translate_args_to_sqlakeyset_args()
        page = await get_page(query, db=db, **sqlakeyset_args)
        paging = page.paging
        return {"nodes": page, "paging": paging}
