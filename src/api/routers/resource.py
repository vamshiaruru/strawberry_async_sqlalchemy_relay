from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.db.models import Resource as ResourceModel
from dependencies.db import get_db
from schemas.resource import Resource

router = APIRouter()

@router.get("/{id}", responses={status.HTTP_200_OK: {"model": Resource}})
async def get_resource(id: int, db = Depends(get_db)):
    query = (
        select(ResourceModel)
        .where(ResourceModel.id == id)
        .options(selectinload(ResourceModel.tags))
    )
    res = await db.execute(query)
    res = res.scalars().first()
    tags = [tag.name for tag in res.tags]
    return Resource(name=res.name, description=res.description, tags=tags)
