import uuid
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import Uuid, String, JSON, ForeignKey, DateTime, Table, Column
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.db.database import Base

user_documents = Table(
  "user_documents",
  Base.metadata,
  Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
  Column("document_id", Uuid, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
  __tablename__ = "users"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  username: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
  email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
  hashed_password: Mapped[str] = mapped_column(String, nullable=False)

  owned_documents: Mapped[list["Document"]] = relationship("Document", back_populates="owner")
  shared_documents: Mapped[list["Document"]] = relationship("Document", secondary=user_documents, back_populates="collaborators")

class Document(Base):
  __tablename__ = "documents"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  title: Mapped[str] = mapped_column(String, default="Untitled Document")
  crdt_state: Mapped[list] = mapped_column(JSON, default=list)

  owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

  owner: Mapped["User"] = relationship("User", back_populates="owned_documents")
  collaborators: Mapped[list["User"]] = relationship("User", secondary=user_documents, back_populates="shared_documents")


class ActivityLog(Base):
  __tablename__ = "activity_logs"

  id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
  user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
  action: Mapped[str] = mapped_column(String)
  timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))