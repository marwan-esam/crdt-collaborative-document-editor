import uuid
from uuid import UUID
from sqlalchemy import Uuid, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.db.database import Base

class Document(Base):
  __tablename__ = "documents"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  title: Mapped[str] = mapped_column(String, default="Untitled Document")
  content: Mapped[str] = mapped_column(Text, default="")