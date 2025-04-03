from app.models.audio import AudioFile
from app.schemas.audio import AudioFileCreate, AudioFileInDB
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from fastapi import UploadFile
from app.core.config import settings

class AudioService:
    @staticmethod
    async def save_audio_file(
        user_id: str,
        file: UploadFile,
        session: AsyncSession
    ) -> AudioFileInDB:
        """Сохраняет аудиофайл на сервере и в базе данных"""
        try:
            # Генерация уникального имени файла
            file_ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid4()}{file_ext}"
            file_path = Path(settings.AUDIO_UPLOAD_DIR) / filename
            
            # Создание директории, если не существует
            file_path.parent.mkdir(exist_ok=True, parents=True)
            
            # Сохранение файла
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Получение размера файла
            file_size = os.path.getsize(file_path)
            
            # Сохранение в БД
            audio_file = AudioFile(
                user_id=user_id,
                original_filename=file.filename,
                file_path=str(file_path),
                file_size=file_size,
                content_type=file.content_type
            )
            
            session.add(audio_file)
            await session.commit()
            await session.refresh(audio_file)
            
            return AudioFileInDB.from_orm(audio_file)
        finally:
            await file.close()

    @staticmethod
    async def get_user_audio_files(
        user_id: str,
        session: AsyncSession
    ) -> List[AudioFileInDB]:
        """Получает список аудиофайлов пользователя"""
        result = await session.execute(
            select(AudioFile).where(AudioFile.user_id == user_id)
        )
        return [AudioFileInDB.from_orm(f) for f in result.scalars().all()]

    @staticmethod
    async def get_audio_file(
        file_id: str,
        user_id: str,
        session: AsyncSession
    ) -> Optional[AudioFileInDB]:
        """Получает конкретный аудиофайл пользователя"""
        result = await session.execute(
            select(AudioFile)
            .where(AudioFile.id == file_id)
            .where(AudioFile.user_id == user_id)
        )
        file = result.scalar_one_or_none()
        return AudioFileInDB.from_orm(file) if file else None

    @staticmethod
    async def delete_audio_file(
        file_id: str,
        user_id: str,
        session: AsyncSession
    ) -> bool:
        """Удаляет аудиофайл и его запись из БД"""
        result = await session.execute(
            select(AudioFile)
            .where(AudioFile.id == file_id)
            .where(AudioFile.user_id == user_id)
        )
        file = result.scalar_one_or_none()
        
        if file:
            try:
                os.unlink(file.file_path)
            except OSError as e:
                print(f"Error deleting file: {e}")
            
            await session.delete(file)
            await session.commit()
            return True
        
        return False