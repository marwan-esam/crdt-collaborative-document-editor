import uuid
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import Uuid, String, JSON, ForeignKey, DateTime
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


class ActivityLog(Base):
  __tablename__ = "activity_logs"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
  user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  action: Mapped[str] = mapped_column(String)
  timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))