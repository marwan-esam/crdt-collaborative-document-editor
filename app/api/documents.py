from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.domain.models import Document, ActivityLog
from app.schemas.document import DocumentCreate, DocumentResponse
from app.core.limiter import limiter
from app.core.security import get_current_user_id

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/", response_model=DocumentResponse)
@limiter.limit("10/minute")
async def create_document(request: Request, doc_in: DocumentCreate, db: AsyncSession = Depends(get_db), user_id: str = Depends(get_current_user_id)):
  new_doc = Document(title=doc_in.title)
  db.add(new_doc)

  try:
    await db.commit()
    await db.refresh(new_doc)
    return new_doc
  except Exception:
    await db.rollback()
    raise HTTPException(status_code=500, detail="Failed to create document")
  

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, db: AsyncSession = Depends(get_db)):
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