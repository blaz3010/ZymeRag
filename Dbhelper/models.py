from dataclasses import dataclass
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime,
    Integer, Text, func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FileType(str, PyEnum):
    pdf     = "pdf"
    csv     = "csv"
    txt     = "txt"
    docx    = "docx"
    image   = "image"
    audio   = "audio"
    video   = "video"
    website = "website"


_file_type_sa = SAEnum(
    FileType,
    name="file_type_enum",
    create_type=False,
    values_callable=lambda obj: [e.value for e in obj],
)


class ContentModel(Base):
    __tablename__ = "contents"

    id          = Column("id",          BigInteger, primary_key=True, autoincrement=True)
    content_id  = Column("content_id",  Text, unique=True, nullable=False)
    name        = Column("name",        Text, nullable=False)
    file_type   = Column("file_type",   _file_type_sa, nullable=False, server_default="pdf")
    file_size   = Column("file_size",   BigInteger, nullable=True)
    chunks      = Column("chunks",      Integer, nullable=False, server_default="0")
    inserted_at = Column("inserted_at", DateTime(timezone=True), server_default=func.now(), nullable=False)
    deleted_at  = Column("deleted_at",  DateTime(timezone=True), nullable=True)


class FeedModel(Base):
    __tablename__ = "feeds"

    id          = Column("id",          BigInteger, primary_key=True, autoincrement=True)
    feed_id     = Column("feed_id",     Text, unique=True, nullable=False)
    url         = Column("url",         Text, nullable=False)
    chunks      = Column("chunks",      Integer, nullable=False, server_default="0")
    inserted_at = Column("inserted_at", DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column("updated_at",  DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at  = Column("deleted_at",  DateTime(timezone=True), nullable=True)


@dataclass
class ContentItem:
    content_id: str
    name: str
    file_type: FileType
    chunks: int
    id: Optional[int] = None
    file_size: Optional[int] = None
    inserted_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


@dataclass
class FeedItem:
    feed_id: str
    url: str
    chunks: int
    id: Optional[int] = None
    inserted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None