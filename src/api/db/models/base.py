from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class IDPrimaryKey:
    # We want to use Integer primary key with autoincrement to enable cursor
    # based pagination
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        unique=True,
    )
