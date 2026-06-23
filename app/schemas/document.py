from pydantic import BaseModel, ConfigDict
from uuid import UUID

class DocumentCreate(BaseModel):
  title: str = "Untitled Document"


class DocumentResponse(BaseModel):
  id: UUID
  title: str

  model_config = ConfigDict(from_attributes=True)