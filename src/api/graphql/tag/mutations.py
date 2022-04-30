import strawberry
from strawberry.types import Info

from api.db.models import Tag as TagModel
from api.graphql.tag.dataloaders import TagByIdLoader
from api.graphql.tag.types import Tag


@strawberry.input
class TagCreateInput:
    name: str

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def tag_create(self, info: Info, input: TagCreateInput) -> Tag:
        db = info.context["db"]
        tag = TagModel(name=input.name)
        db.add(tag)
        await db.commit()
        return await TagByIdLoader(info.context).load(tag.id)
