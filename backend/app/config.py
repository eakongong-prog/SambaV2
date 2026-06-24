from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "SambaV2"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///" + str(
        Path(__file__).resolve().parent.parent / "sambav2.db"
    )

    # JWT
    SECRET_KEY: str = "sambav2-secret-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # 默认管理员
    DEFAULT_ADMIN_USERNAME: str = "sys_admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    # SSH 连接池
    SSH_TIMEOUT: int = 10
    SSH_POOL_TTL: int = 300  # 连接缓存 5 分钟

    # AES 加密密钥（用于存储 SSH 密码）
    CIPHER_KEY: str = "sambav2-cipher-key-change-me-2026"

    class Config:
        env_file = ".env"


settings = Settings()
