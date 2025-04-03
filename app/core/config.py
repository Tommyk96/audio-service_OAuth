from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, SecretStr, validator
from functools import lru_cache
from typing import Optional, List


class DatabaseSettings(BaseSettings):
    user: str = Field(..., alias="DB_POSTGRES_USER")
    password: SecretStr = Field(..., alias="DB_POSTGRES_PASSWORD")
    db: str = Field(..., alias="DB_POSTGRES_DB")
    host: str = Field("db", alias="DB_POSTGRES_HOST")
    port: int = Field(5432, alias="DB_POSTGRES_PORT")
    
    pool_size: int = Field(5, alias="POOL_SIZE")
    max_overflow: int = Field(10, alias="MAX_OVERFLOW")
    pool_timeout: int = Field(30, alias="POOL_TIMEOUT")
    echo_sql: bool = Field(False, alias="ECHO_SQL")

    @property
    def async_url(self) -> str:
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            path=self.db or ""  # Убираем добавление слеша
            ))

    @validator('port', pre=True)
    def parse_port(cls, v):
        if isinstance(v, str):
            return int(v.strip('"\' '))  # Удаляем возможные кавычки и пробелы
        return v

class AuthSettings(BaseSettings):
    secret_key: SecretStr = Field(..., alias="SECRET_KEY")
    algorithm: str = Field("HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

#class YandexOAuthSettings(BaseSettings):
 #   client_id: str = Field(..., alias="YANDEX_CLIENT_ID")
  #  client_secret: SecretStr = Field(..., alias="YANDEX_CLIENT_SECRET")
   # redirect_uri: str = Field(..., alias="YANDEX_REDIRECT_URI")
    #frontend_url: str = Field(..., alias="FRONTEND_URL")

class YandexOAuthSettings(BaseSettings):
    client_id: str = Field(..., alias="YANDEX_CLIENT_ID")
    client_secret: SecretStr = Field(..., alias="YANDEX_CLIENT_SECRET")
    redirect_uri: str = Field("http://localhost:8000/auth/yandex/callback", alias="YANDEX_REDIRECT_URI")
    frontend_url: str = Field("http://localhost:3000", alias="FRONTEND_URL")
    token_url: str = Field("https://oauth.yandex.ru/token", alias="YANDEX_TOKEN_URL")
    auth_url: str = Field("https://oauth.yandex.ru/authorize", alias="YANDEX_AUTH_URL")

class AppSettings(BaseSettings):
    project_name: str = Field(..., alias="PROJECT_NAME")
    debug: bool = Field(False, alias="DEBUG")

    environment: str = Field("production", alias="APP_ENV")
    cors_origins: list[str] = ["*"]

    @validator("debug", pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

class AudioSettings(BaseSettings):
    max_file_size: int = 10_000_000  # 10MB
    allowed_types: list[str] = ["audio/mpeg", "audio/wav"]


class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    auth: AuthSettings = AuthSettings()
    yandex: YandexOAuthSettings = YandexOAuthSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Для совместимости
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()