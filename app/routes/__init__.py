from .auth import router as auth_router
from .users import router as users_router
from .audio import router as audio_router
from .yandex import yandex_router  # Добавьте этот импорт

__all__ = ["auth_router", "users_router", "audio_router", "yandex_router"]

