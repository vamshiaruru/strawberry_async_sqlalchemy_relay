"""Defines context getter for fastapi route"""
from fastapi import Depends

from dependencies.db import get_db


async def get_context_for_fastapi(db=Depends(get_db)):
    return {"db": db}
