from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
from datetime import datetime

class TokenBase(BaseModel):
    """Базовая схема для токенов"""
    access_token: str
    token_type: str = "bearer"

class Token(TokenBase):
    """Схема ответа с токеном и данными пользователя"""
    user: Optional['UserInDB'] = None

class UserBase(BaseModel):
    """Базовая схема пользователя"""
    email: EmailStr
    name: Optional[str] = Field(
        None, 
        min_length=2, 
        max_length=50,
        example="Иван Иванов"
    )

class UserCreate(UserBase):
    """Схема для создания пользователя"""
    yandex_id: str = Field(..., min_length=1)
    access_token: str = Field(..., min_length=1)
    refresh_token: str = Field(..., min_length=1)
    token_expires: int = Field(
        ...,
        gt=0,
        description="Время истечения токена в секундах с эпохи Unix"
    )

class UserUpdate(UserBase):
    """Схема для обновления пользователя"""
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class UserInDB(UserBase):
    """Схема пользователя в БД"""
    id: uuid.UUID = Field(..., example="a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8")
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Ранее known_as orm_mode
        json_schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
                "email": "user@example.com",
                "name": "Иван Иванов",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }

# Для циклических ссылок (если нужно)
Token.update_forward_refs()