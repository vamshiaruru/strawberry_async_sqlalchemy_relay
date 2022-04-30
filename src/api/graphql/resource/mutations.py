from typing import Annotated, Optional, List
import strawberry
from strawberry.types import Info
from graphql_relay import from_global_id
from sqlalchemy import select

from api.db.models import Resource as ResourceModel
from api.graphql.resource.types import Resource
from api.graphql.tag.dataloaders import TagByIdLoader

@strawberry.input
class _ResourceCreateInput:
    name: str
    tags: Optional[List[strawberry.ID]]
    description: str = None

ResourceCreateInput = Annotated[
    _ResourceCreateInput,
    strawberry.argument("Input for creating a resource. Tags is list of global ids.")
]

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def resource_create(self, info: Info, input: ResourceCreateInput) -> Resource:
        db = info.context["db"]
        resource = ResourceModel(
            name=input.name, description=input.description
        )
        if input.tags:
            ids = [int(from_global_id(_id)[1]) for _id in input.tags]
            tags = await TagByIdLoader(info.context).load_many(ids)
            # Since we defined relationship on the model, we can just add to resource.tags
            # and sqlalchemy takes care of populating the association table
            resource.tags.extend(tags)
        db.add(resource)
        await db.commit()
        return resource # committing automatically adds id back to the resource.
