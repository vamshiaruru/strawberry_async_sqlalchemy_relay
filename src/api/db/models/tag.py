"""Model for tag table"""
from sqlalchemy import Column, String

from api.db.models.base import Base, IDPrimaryKey


# For now this is just a stub.
class Tag(Base, IDPrimaryKey):
    __tablename__ = "tag_tag"
    name = Column(String, index=True, unique=True)

