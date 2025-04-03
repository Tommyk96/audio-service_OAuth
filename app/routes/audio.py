from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import os
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.audio import AudioFileInDB
from app.services.audio import AudioService
from app.routes.users import get_current_user
from app.models.user import User
from app.core.config import settings
from app.db.session import get_async_session

router = APIRouter(prefix="/audio", tags=["audio"])

@router.post("/upload", response_model=AudioFileInDB, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Загрузка аудиофайла"""
    # Проверка типа файла
    if file.content_type not in settings.audio.allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.audio.allowed_types)}"
        )
    
    # Проверка размера файла
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.audio.max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.audio.max_file_size} bytes"
        )
    
    return await AudioService.save_audio_file(
        user_id=current_user.id,
        file=file,
        session=session,
        storage_path=settings.audio.storage_path
    )

@router.get("/my", response_model=list[AudioFileInDB])
async def get_my_audio_files(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Получить список моих аудиофайлов"""
    return await AudioService.get_user_audio_files(current_user.id, session)

@router.get("/download/{file_id}")
async def download_audio_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Скачать аудиофайл"""
    audio_file = await AudioService.get_audio_file(file_id, current_user.id, session)
    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )
    
    file_path = Path(audio_file.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="File no longer exists on server"
        )
    
    return FileResponse(
        file_path,
        media_type=audio_file.content_type,
        filename=audio_file.original_filename
    )

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Удалить аудиофайл"""
    success = await AudioService.delete_audio_file(
        file_id=file_id,
        user_id=current_user.id,
        session=session
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found or you don't have permission"
        )