from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.domain.models import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == user_in.email))

  if result.scalar_one_or_none():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Email already registered"
    )
  

  new_user = User(
    email=user_in.email,
    hashed_password=hash_password(user_in.password)
  )

  db.add(new_user)

  try:
    await db.commit()
    await db.refresh(new_user)
    return new_user
  except Exception:
    await db.rollback()
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during registration")
  

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == user_in.email))
  user = result.scalar_one_or_none()

  if not user or not verify_password(user_in.password, user.hashed_password):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect email or password"
    )
  

  access_token = create_access_token(data={"sub": str(user.id)})

  return {"access_token": access_token, "token_type": "bearer"}
