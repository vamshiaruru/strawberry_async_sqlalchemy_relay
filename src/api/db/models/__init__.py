# Import everything here so that Base.metadata is populated with all the tables

from api.db.models.base import Base
from api.db.models.tag import Tag
from api.db.models.resource import Resource, ResourceTagAssociation
