from fastapi import APIRouter, HTTPException
import requests
from fastapi.responses import JSONResponse
from app.core.config import settings

yandex_router = APIRouter()

@yandex_router.get("/callback")
async def yandex_callback(code: str, client_id: str, client_secret: str):
    """
    Обработка callback от Yandex для получения токена.
    """
    token_url = "https://oauth.yandex.ru/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
    }
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Yandex OAuth error: {e}")
