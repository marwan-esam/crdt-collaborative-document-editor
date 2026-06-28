from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.domain.models import Document, ActivityLog, User
from app.schemas.document import DocumentCreate, DocumentResponse
from app.schemas.user import CollaboratorResponse
from app.core.limiter import limiter
from app.core.security import get_current_user_id

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/", response_model=list[DocumentResponse])
async def get_my_documents(db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
  user_uuid = UUID(user_id)
  query = select(User).where(User.id == user_uuid).options(
    selectinload(User.owned_documents),
    selectinload(User.shared_documents)
  )

  result = await db.execute(query)
  user = result.scalar_one_or_none()

  if not user:
    raise HTTPException(
      status_code=404, detail="User not found"
    )
  
  all_docs = user.owned_documents + user.shared_documents
  unique_docs = {doc.id: doc for doc in all_docs}.values()

  return list(unique_docs)


@router.post("/", response_model=DocumentResponse)
@limiter.limit("10/minute")
async def create_document(request: Request, doc_in: DocumentCreate, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
  new_doc = Document(title=doc_in.title, owner_id=UUID(user_id))
  db.add(new_doc)

  try:
    await db.commit()
    await db.refresh(new_doc)
    return new_doc
  except Exception:
    await db.rollback()
    raise HTTPException(status_code=500, detail="Failed to create document")
  

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
  result = await db.execute(select(Document).where(Document.id == document_id))
  doc = result.scalar_one_or_none()

  if not doc:
    raise HTTPException(status_code=404, detail="Document not found")
  
  return doc


@router.get("/{document_id}/analytics")
@limiter.limit("5/minute")
async def get_document_analytics(
  request: Request,
  document_id: UUID,
  db: AsyncSession = Depends(get_db),
  user_id: str = Depends(get_current_user_id)
):
  edits_cte = select(
    ActivityLog.user_id,
    func.count(ActivityLog.id).label("total_edits")
  ).where(
    ActivityLog.document_id == document_id,
    ActivityLog.action == "edit"
  ).group_by(
    ActivityLog.user_id
  ).cte("user_edits_cte")


  rank_query = select(
    edits_cte.c.user_id,
    edits_cte.c.total_edits,
    func.rank().over(order_by=edits_cte.c.total_edits.desc()).label("contributor_rank")
  )

  result = await db.execute(rank_query)
  rows = result.all()

  analytics = [
    {
      "user_id": row.user_id,
      "total_edits": row.total_edits,
      "rank": row.contributor_rank
    }
    for row in rows
  ]

  return {"document_id": document_id, "top_contributors": analytics}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
  document_id: UUID,
  db: AsyncSession = Depends(get_db),
  user_id: UUID = Depends(get_current_user_id)
):
  result = await db.execute(select(Document).where(Document.id == document_id))
  doc = result.scalar_one_or_none()

  if not doc:
    raise HTTPException(status_code=404, detail="Document not found")
  
  if doc.owner_id != user_id:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="You do not have permission to delete this document"
    )

  try: 
    async with db.begin():
     db.delete(doc)
  except SQLAlchemyError as e:
    print(f"Datbase crash: {e}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Database internal error occurred"
    )
  return None

@router.get("/{document_id}/collaborators", response_model=list[CollaboratorResponse])
async def get_document_collaborators(
  document_id: UUID,
  db: AsyncSession = Depends(get_db),
  user_id: UUID = Depends(get_current_user_id)
):
  query = select(Document).where(Document.id == document_id).options(
    selectinload(Document.collaborators),
    selectinload(Document.owner)
  )

  result = await db.execute(query)
  doc = result.scalar_one_or_none()

  if not doc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Document not found"
    )
  
  all_users = {doc.owner.id: doc.owner}
  for collaborator in doc.collaborators:
    all_users[collaborator.id] = collaborator

  return list(all_users.values())

@router.get("/{document_id}/owner", response_model=CollaboratorResponse)
async def get_document_owner(
  document_id: UUID,
  db: AsyncSession = Depends(get_db),
  user_id: UUID = Depends(get_current_user_id)
):
  query = select(Document).where(Document.id == document_id).options(
    selectinload(Document.owner)
  )

  result = await db.execute(query)
  doc = result.scalar_one_or_none()

  if not doc:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Document not found"
    )
  
  return doc.owner