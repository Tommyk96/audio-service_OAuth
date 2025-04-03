import httpx
from fastapi import HTTPException, status
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from pydantic import ValidationError

from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserInDB
from app.db.session import AsyncSession, async_session_maker
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_yandex_user_info(self, access_token: str) -> Dict[str, Any]:
        """Получение и валидация информации о пользователе из Yandex OAuth"""
        async with httpx.AsyncClient() as client:
            try:
                # Проверка валидности токена и получение scope
                token_response = await client.get(
                    "https://oauth.yandex.ru/tokeninfo",
                    params={"access_token": access_token},
                    timeout=10.0
                )
                token_response.raise_for_status()
                token_data = token_response.json()

                # Получение данных пользователя
                user_response = await client.get(
                    "https://login.yandex.ru/info",
                    headers={"Authorization": f"OAuth {access_token}"},
                    params={"format": "json", "with_openid_identity": "true"},
                    timeout=10.0
                )
                user_response.raise_for_status()
                user_data = user_response.json()

                return {
                    **token_data,
                    **user_data,
                    "access_token": access_token
                }

            except httpx.HTTPStatusError as exc:
                error_detail = f"Yandex API error: {exc.response.text}"
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_detail
                ) from exc
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Yandex OAuth service unavailable"
                ) from exc

    async def authenticate_user(self, yandex_token: str) -> User:
        """Аутентификация или регистрация пользователя через Yandex"""
        try:
            yandex_data = await self.get_yandex_user_info(yandex_token)
            
            # Валидация обязательных полей
            if not all(key in yandex_data for key in ['user_id', 'default_email']):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Incomplete Yandex user data"
                )

            # Подготовка данных пользователя
            user_data = {
                "yandex_id": yandex_data['user_id'],
                "email": yandex_data['default_email'],
                "name": yandex_data.get('real_name') or 
                        yandex_data.get('display_name') or 
                        yandex_data['default_email'].split('@')[0],
                "access_token": yandex_token,
                "token_expires": int((datetime.now() + timedelta(days=30)).timestamp()
            )}

            # Поиск или создание пользователя
            try:
                user = await self._get_or_create_user(user_data)
                return user
            except IntegrityError as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already exists with different credentials"
                ) from exc

        except HTTPException:
            raise
        except Exception as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {str(exc)}"
            ) from exc

    async def _get_or_create_user(self, user_data: Dict[str, Any]) -> User:
        """Внутренний метод для поиска/создания пользователя"""
        result = await self.session.execute(
            select(User).where(
                (User.yandex_id == user_data['yandex_id']) | 
                (User.email == user_data['email'])
            )
        )
        user = result.scalars().first()

        if user:
            # Обновление существующего пользователя
            user.access_token = user_data['access_token']
            user.token_expires = user_data['token_expires']
            if user.yandex_id != user_data['yandex_id']:
                user.yandex_id = user_data['yandex_id']
            if user.name != user_data['name']:
                user.name = user_data['name']
        else:
            # Создание нового пользователя
            user = User(
                **user_data,
                refresh_token="",  # Yandex не предоставляет refresh token
                is_active=True,
                is_superuser=False
            )
            self.session.add(user)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    @staticmethod
    def create_access_token(data: Dict[str, Any]) -> str:
        """Создание JWT токена с обработкой ошибок"""
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode.update({"exp": expire})
            return jwt.encode(
                to_encode, 
                settings.SECRET_KEY, 
                algorithm=settings.ALGORITHM
            )
        except (JWTError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Token creation failed: {str(exc)}"
            ) from exc

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Верификация JWT токена с детализированными ошибками"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.auth.ALGORITHM],

                options={"require": ["exp", "sub"]}
            )
            return payload
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            ) from exc
        except jwt.JWTClaimsError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            ) from exc
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            ) from exc

# Фабрика для dependency injection
async def get_auth_service():
    """Генератор сессий для инъекции зависимостей"""
    async with async_session_maker() as session:
        try:
            yield AuthService(session)
        finally:
            await session.close()