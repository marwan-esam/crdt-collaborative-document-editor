import re
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from uuid import UUID

class UserCreate(BaseModel):
  email: EmailStr
  username: str
  password: str

  @field_validator('password')
  @classmethod
  def validate_password_complexity(cls, v: str) -> str:
    if len(v) < 8:
      raise ValueError('Password must be at least 8 characters long')
    if not re.search(r'[A-Z]', v):
      raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', v):
      raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'[0-9]', v):
      raise ValueError('Password must contain at least one number')
    if not re.search(r'[\W_]', v):
      raise ValueError('Password must contain at least one special character')
    
    return v
    
  model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
  email: EmailStr
  password: str

class UserResponse(BaseModel):
  id: UUID
  email: EmailStr

  model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
  access_token: str
  token_type: str


class CollaboratorResponse(BaseModel):
  id: UUID
  username: str

  model_config = ConfigDict(from_attributes=True)