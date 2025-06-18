"""
Simple authentication routes
"""

from fastapi import APIRouter, HTTPException, status
from api.core.simple_auth import (
    UserCreate, UserLogin, TokenResponse, User,
    register_user, authenticate_user, create_access_token
)

router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        user = register_user(user_data.email, user_data.password)
        access_token = create_access_token(user.id)
        
        return TokenResponse(
            access_token=access_token,
            user_id=user.id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login user"""
    user = authenticate_user(user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    access_token = create_access_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        user_id=user.id
    )

@router.get("/demo-token", response_model=TokenResponse)
async def get_demo_token():
    """Get demo token for testing"""
    # Find demo user
    from api.core.simple_auth import USERS_DB
    
    demo_user = None
    for email, data in USERS_DB.items():
        if email == "demo@studywise.ai":
            demo_user = data['user']
            break
    
    if not demo_user:
        raise HTTPException(status_code=404, detail="Demo user not found")
    
    access_token = create_access_token(demo_user.id)
    
    return TokenResponse(
        access_token=access_token,
        user_id=demo_user.id
    )