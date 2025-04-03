from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import json
from urllib.parse import urlencode, quote
import logging

from app.schemas.user import UserInDB, Token
from app.models.user import User
from app.services.auth import AuthService, get_auth_service
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/yandex")

async def get_yandex_user_info(access_token: str) -> dict:
    """Get user info from Yandex API with proper encoding"""
    try:
        headers = {
            "Authorization": f"OAuth {access_token}",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://login.yandex.ru/info",
                headers=headers,
                params={"format": "json"},
                timeout=10.0
            )

            if response.status_code != 200:
                error_msg = f"Yandex API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", error_msg)
                except json.JSONDecodeError:
                    error_msg = response.text[:200]
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_msg
                )
                
            return response.json()
            
    except httpx.RequestError as e:
        logger.error(f"Request to Yandex API failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Yandex service unavailable"
        )

@router.post("/yandex", response_model=Token)
async def auth_via_yandex_token(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate with Yandex OAuth token"""
    try:
        content_type = request.headers.get('content-type', '')
        if 'application/json' in content_type:
            data = await request.json()
            yandex_token = data.get("access_token")
        else:
            form_data = await request.form()
            yandex_token = form_data.get("access_token")
        
        if not yandex_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yandex access token is required"
            )

        user_data = await get_yandex_user_info(yandex_token)
        
        if not user_data.get("id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user data from Yandex"
            )

        user = await auth_service.authenticate_user({
            "yandex_id": user_data["id"],
            "email": user_data.get("default_email", ""),
            "access_token": yandex_token
        })

        return Token(
            access_token=auth_service.create_access_token(data={"sub": str(user.id)}),
            token_type="bearer",
            user=UserInDB.from_orm(user)
        )
            
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request format"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/yandex/login")
async def login_via_yandex(settings: Settings = Depends(get_settings)):
    """Redirect to Yandex OAuth authorization page"""
    yandex_settings = settings.yandex
    
    params = {
        "response_type": "code",
        "client_id": yandex_settings.YANDEX_CLIENT_ID,
        "redirect_uri": yandex_settings.YANDEX_REDIRECT_URI,
        "scope": "login:email login:info",
    }
    
    auth_url = f"{yandex_settings.AUTH_URL}?{urlencode(params)}"
    
    logger.debug(f"Yandex OAuth redirect URL: {auth_url}")
    
    return RedirectResponse(auth_url)

@router.get("/yandex/callback")
async def yandex_callback(
    code: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings)
):
    """Handle Yandex OAuth callback"""
    try:
        if error:
            raise HTTPException(
                status_code=400,
                detail=f"Yandex OAuth error: {error_description or error}"
            )
        
        if not code:
            logger.error("Authorization code is missing")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )

        logger.debug(f"Exchanging code, client_id: {settings.yandex.YANDEX_CLIENT_ID}, "
                   f"redirect_uri: {settings.yandex.YANDEX_REDIRECT_URI}")

        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth.yandex.ru/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.yandex.YANDEX_CLIENT_ID,
                    "client_secret": settings.yandex.YANDEX_CLIENT_SECRET.get_secret_value(),
                    "redirect_uri": settings.yandex.YANDEX_REDIRECT_URI
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )
            
            if token_response.status_code != 200:
                error_detail = "Failed to exchange code for token"
                try:
                    error_data = token_response.json()
                    error_detail = error_data.get("error_description", error_detail)
                    logger.error(f"Token exchange failed: {error_detail}")
                except json.JSONDecodeError:
                    logger.error(f"Token exchange failed with status {token_response.status_code}: {token_response.text}")
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error_detail
                )
                
            token_data = token_response.json()
            logger.debug("Successfully received token from Yandex")

        # Get user info
        user_data = await get_yandex_user_info(token_data["access_token"])
        if not user_data.get("id"):
            logger.error("Invalid user data received from Yandex")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user data from Yandex"
            )

        # Authenticate user
        user = await auth_service.authenticate_user({
            "yandex_id": user_data["id"],
            "email": user_data.get("default_email", ""),
            "access_token": token_data["access_token"]
        })
        logger.info(f"Authenticated user: {user.id}")

        # Create JWT token
        token = auth_service.create_access_token(data={"sub": str(user.id)})
        
        # Redirect to frontend with token
        frontend_redirect_url = (
            f"{settings.FRONTEND_URL}/oauth-callback?"
            f"token={token}&user_id={user.id}"
        )
        return RedirectResponse(url=frontend_redirect_url)
        
    except HTTPException as he:
        logger.error(f"Callback error: {he.detail}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OAuth processing"
        )
