from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import expression
import uuid

from app.db.session import Base  # Импорт из session.py


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    yandex_id = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    is_superuser = Column(Boolean, server_default=expression.false(), nullable=False)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    token_expires = Column(Integer, nullable=True)