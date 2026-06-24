from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import hashlib

from ..config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# --- SSH 密码 AES 加密 ---

def _get_cipher() -> Fernet:
    """Derive a Fernet key from CIPHER_KEY."""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(settings.CIPHER_KEY.encode()).digest()
    )
    return Fernet(key)


def encrypt_ssh_password(plain: str) -> str:
    return _get_cipher().encrypt(plain.encode()).decode()


def decrypt_ssh_password(encrypted: str) -> str:
    return _get_cipher().decrypt(encrypted.encode()).decode()
