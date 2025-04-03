import sys
from pathlib import Path
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.routes import auth_router, users_router, audio_router, yandex_router

# 1. Настройка путей и окружения
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR))

# 2. Загрузка .env ДО всех других импортов
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

# 3. Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка .env
logger.info(f"Checking .env at: {ENV_PATH}")
if not ENV_PATH.exists():
    logger.error(".env file NOT FOUND!")
    raise RuntimeError("Missing .env file")

# 4. Импорт настроек ПОСЛЕ загрузки .env
from app.core.config import settings

# 5. Создание директорий
STATIC_DIR = BASE_DIR / "static/audio_files"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# 6. Создание приложения
app = FastAPI(
    title=settings.app.project_name,
    version="1.0.0",
    debug=settings.app.debug,
    docs_url="/docs" if settings.app.debug else None,
    redoc_url="/redoc" if settings.app.debug else None
)

# 7. Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 8. Подключение статических файлов
app.mount("/static/audio_files", StaticFiles(directory=STATIC_DIR), name="audio_files")

# 9. Регистрация роутеров
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(audio_router, prefix="/audio", tags=["audio"])
app.include_router(yandex_router, prefix="/auth/yandex", tags=["yandex-oauth"])

# 10. Инициализация базы данных
@app.on_event("startup")
async def startup_db():
    """Инициализация базы данных при запуске"""
    from app.db.session import Base, engine
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except SQLAlchemyError as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

# 11. Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok"}

# 12. Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.app.project_name,
        "version": "1.0.0",
        "environment": "development" if settings.app.debug else "production"
    }

# 13. Дополнительная обработка ошибок (например, для OAuth)
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc: HTTPException):
    logger.error(f"HTTPException occurred: {exc.detail}")
    return {"detail": exc.detail, "status_code": exc.status_code}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
        log_level="info"
    )

