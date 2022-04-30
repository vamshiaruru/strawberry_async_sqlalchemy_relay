"""Model for resources table"""
from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from api.db.models.base import Base, IDPrimaryKey

class Resource(Base, IDPrimaryKey):
    __tablename__ = "resource_resource"
    name = Column(String, index=True, unique=True)
    description = Column(Text)
    tags = relationship(
        "Tag", secondary=lambda: ResourceTagAssociation.__table__, backref="resources"
    )

class ResourceTagAssociation(Base):
    __tablename__ = "resource_resourcetagassociation"
    tag_id = Column(Integer, ForeignKey("tag_tag.id"))
    resource_id = Column(Integer, ForeignKey("resource_resource.id"))

    __table_args__ = (
        PrimaryKeyConstraint("tag_id", "resource_id"),
        Index("tag_resource_association_idx_tag_resource", "resource_id", "tag_id"),
    )
