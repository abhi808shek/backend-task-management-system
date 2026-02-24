# app/modules/users/utils.py
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone

MAX_BCRYPT_BYTES = 72
BCRYPT_ROUNDS = 12
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")  # separate secret for refresh tokens
ALGORITHM = "HS256"

# ---------------- Password ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

# ---------------- Access Token ----------------
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ---------------- Refresh Token ----------------
def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    # Signed with a different secret so access/refresh tokens can't be swapped
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

# ---------------- Decode Token (handles both) ----------------
def decode_token(token: str) -> dict | None:
    # Try access token secret first, then refresh secret
    for secret in [SECRET_KEY, REFRESH_SECRET_KEY]:
        try:
            return jwt.decode(token, secret, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None  
        except jwt.InvalidTokenError:
            continue    
    return None