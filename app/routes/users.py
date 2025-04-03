from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List

from app.schemas.user import UserInDB, UserUpdate
from app.services.auth import AuthService
from app.models.user import User
from sqlalchemy.future import select
from app.db.session import async_session_maker as AsyncSessionLocal

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/yandex")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = await AuthService.verify_token(token)
    if not payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if user is None:
            raise credentials_exception
        
        return user

async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/me", response_model=UserInDB)
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserInDB)
async def update_user_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    async with AsyncSessionLocal() as session:
        for var, value in vars(user_update).items():
            if value is not None:
                setattr(current_user, var, value)
        
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)
        return current_user

@router.get("/", response_model=List[UserInDB])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser)
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).offset(skip).limit(limit))
        users = result.scalars().all()
        return users

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_superuser)
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        await session.delete(user)
        await session.commit()
        return {"ok": True}