from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.domain.models import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.core.security import hash_password, verify_password, create_access_token, get_current_user_id
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(User).where(User.email == form_data.username))
  user = result.scalar_one_or_none()

  if not user or not verify_password(form_data.password, user.hashed_password):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect email or password"
    )
  

  access_token = create_access_token(data={"sub": str(user.id)})

  return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
@limiter.limit("20/minute")
def get_my_profile(request: Request, user_id: str = Depends(get_current_user_id)):
  return {"user_id": user_id}
