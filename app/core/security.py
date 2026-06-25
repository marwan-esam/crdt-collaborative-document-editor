import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
  pwd_bytes = password.encode('utf-8')
  salt = bcrypt.gensalt()
  hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)

  return hashed_bytes.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
  return bcrypt.checkpw(
    plain_password.encode('utf-8'),
    hashed_password.encode('utf-8')
  )


def create_access_token(data: dict, expires_delta: timedelta | None = None):
  to_encode = data.copy()

  if expires_delta:
    expire = datetime.now(timezone.utc) + expires_delta
  else:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)

  to_encode.update({"exp": expire})

  encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

  return encoded_jwt


def get_current_user_id(token: str = Depends(oauth2_scheme)):
  try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    user_id: str = payload.get("sub")
    if user_id is None:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate", "Bearer"}
      )
    
    return user_id
  except jwt.PyJWTError:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Could not validate user credentials",
      headers={"WWW-Authenticate": "Bearer"}
    )