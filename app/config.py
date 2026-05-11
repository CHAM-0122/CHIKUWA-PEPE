import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(slots=True)
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite:///./dog_growth.db"
    upload_dir: str = "uploads"
    secret_key: str = "change-me"
    max_upload_size: int = 5 * 1024 * 1024
    allowed_image_extensions: set[str] = field(
        default_factory=lambda: {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    )

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./dog_growth.db"),
            upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
            secret_key=os.getenv("SECRET_KEY", "change-me"),
            max_upload_size=int(os.getenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024))),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
