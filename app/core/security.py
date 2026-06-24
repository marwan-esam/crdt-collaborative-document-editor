import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

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