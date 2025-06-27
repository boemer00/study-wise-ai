"""
Simple, production-ready authentication system
Uses basic JWT tokens with user registration/login
"""

import os
import jwt
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

security = HTTPBearer()

# JWT secret - check multiple environment variables for compatibility
JWT_SECRET = (
    os.getenv('JWT_SECRET') or
    os.getenv('SUPABASE_JWT_SECRET') or
    os.getenv('SECRET_KEY') or
    'your-secret-key-change-in-production'
)
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

class User(BaseModel):
    id: str
    email: str
    created_at: datetime

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str

# In-memory user store for MVP (replace with database for production)
USERS_DB = {}

# File-based persistence for MVP
import json
from pathlib import Path

USER_STORE_FILE = Path("data/users.json")

def load_users():
    """Load users from file if exists."""
    global USERS_DB
    if USER_STORE_FILE.exists():
        try:
            with open(USER_STORE_FILE, 'r') as f:
                data = json.load(f)
                # Reconstruct User objects from JSON data
                for email, user_data in data.items():
                    user = User(
                        id=user_data['user']['id'],
                        email=user_data['user']['email'],
                        created_at=datetime.fromisoformat(user_data['user']['created_at'])
                    )
                    USERS_DB[email] = {
                        'user': user,
                        'password_hash': user_data['password_hash']
                    }
                print(f"✅ Loaded {len(USERS_DB)} users from {USER_STORE_FILE}")
        except Exception as e:
            print(f"⚠️ Could not load users from file: {e}")

def save_users():
    """Save users to file."""
    try:
        USER_STORE_FILE.parent.mkdir(exist_ok=True)
        # Convert datetime objects to strings for JSON serialization
        data_to_save = {}
        for email, user_data in USERS_DB.items():
            data_copy = {
                'user': {
                    'id': user_data['user'].id,
                    'email': user_data['user'].email,
                    'created_at': user_data['user'].created_at.isoformat()
                },
                'password_hash': user_data['password_hash']
            }
            data_to_save[email] = data_copy

        with open(USER_STORE_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        print(f"✅ Saved {len(USERS_DB)} users to {USER_STORE_FILE}")
    except Exception as e:
        print(f"⚠️ Could not save users to file: {e}")

# Load existing users on startup
load_users()

def hash_password(password: str) -> str:
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def create_access_token(user_id: str) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def register_user(email: str, password: str) -> User:
    """Register a new user"""
    if email in USERS_DB:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=email,
        created_at=datetime.utcnow()
    )

    USERS_DB[email] = {
        'user': user,
        'password_hash': hash_password(password)
    }

    # Save to file for persistence
    save_users()

    return user

def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user with email/password"""
    if email not in USERS_DB:
        return None

    user_data = USERS_DB[email]
    if not verify_password(password, user_data['password_hash']):
        return None

    return user_data['user']

async def get_current_user_id(token: Optional[str] = Depends(security)) -> str:
    """Extract user ID from JWT token"""
    if not token or not token.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


class SimpleAuth:
    def delete_user(self, *, email: str | None = None, user_id: str | None = None) -> bool:
        """Remove a user from the in-memory & file JSON store.

        Either *email* or *user_id* must be provided. Returns ``True`` if a
        record was actually removed.
        """

        if not email and not user_id:
            raise ValueError("email or user_id must be provided")

        # Resolve email if only user_id given
        if not email:
            for em, data in USERS_DB.items():
                if data["user"].id == user_id:
                    email = em
                    break

        if not email or email not in USERS_DB:
            return False

        # Remove from in-memory store and persist to disk
        USERS_DB.pop(email, None)
        save_users()
        return True
