import uuid
from uuid import UUID
from sqlalchemy import Uuid, String, JSON
from sqlalchemy.orm import mapped_column, Mapped
from app.db.database import Base

class User(Base):
  __tablename__ = "users"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
  hashed_password: Mapped[str] = mapped_column(String, nullable=False)

class Document(Base):
  __tablename__ = "documents"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  title: Mapped[str] = mapped_column(String, default="Untitled Document")
  crdt_state: Mapped[list] = mapped_column(JSON, default=list)