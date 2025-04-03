from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class AudioFileBase(BaseModel):
    original_filename: str
    file_size: int
    content_type: str

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileInDB(AudioFileBase):
    id: UUID
    user_id: UUID
    file_path: str
    created_at: datetime
    updated_at: Optional[datetime]


    class Config:
        from_attributes = True  # <-- Добавьте это