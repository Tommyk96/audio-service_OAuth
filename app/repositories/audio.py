# app/repositories/audio.py
from app.models.audio import AudioFile
from app.schemas.audio import AudioFileCreate

class AudioRepository:
    def __init__(self, session):
        self.session = session
    
    async def create(self, audio: AudioFileCreate):
        ...