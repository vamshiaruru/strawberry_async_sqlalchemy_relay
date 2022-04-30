"""Composes all queries, mutations, and subscriptions and returns schema"""
from typing import Optional

import strawberry
from strawberry.extensions import AddValidationRules, QueryDepthLimiter

from api.graphql.core.extensions import RelayIdExtension
from api.graphql.core.validators.query_cost import cost_validator
from api.graphql.resource.schema import Query as ResourceQuery
from api.graphql.resource.mutations import Mutation as ResourceMutation
from api.graphql.query_cost_map import COST_MAP
from api.graphql.tag.mutations import Mutation as TagMutation
from api.graphql.tag.schema import Query as TagQuery
from api.settings import get_settings

settings = get_settings()


@strawberry.type
class Query(ResourceQuery, TagQuery):
    """
    We have to inherit from every Query we want. Each module in this folder
    would expose Query, and we import that into this file, and add it just like
    ResourceQuery.
    """

    _service: Optional[str]


@strawberry.type
class Mutation(TagMutation, ResourceMutation):
    pass


schema = strawberry.federation.Schema(
    Query,
    Mutation,
    extensions=[
        RelayIdExtension,
        QueryDepthLimiter(max_depth=settings.max_query_depth),
        AddValidationRules(
            [cost_validator(maximum_cost=settings.max_query_cost, cost_map=COST_MAP)]
        ),
    ],
)
