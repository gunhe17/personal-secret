from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    ...


class Model(Base):
    __abstract__ = True
