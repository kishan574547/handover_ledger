import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_FALLBACK_MODELS: str = "gemini-flash-lite-latest,gemini-3.8-flash"
    GITHUB_TOKEN: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./handoverledger.db"
    DATA_DIR: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def data_directory(self) -> Path:
        if self.DATA_DIR and self.DATA_DIR.strip():
            d = Path(self.DATA_DIR.strip()).resolve()
        else:
            d = BACKEND_DIR / "data"
        d.mkdir(parents=True, exist_ok=True)
        (d / "uploads").mkdir(parents=True, exist_ok=True)
        (d / "logs").mkdir(parents=True, exist_ok=True)
        return d

    @property
    def effective_database_url(self) -> str:
        url = (self.DATABASE_URL or "").strip()
        if not url:
            db_path = self.data_directory / "handoverledger.db"
            return f"sqlite:///{db_path}"

        # Cloud PostgreSQL providers (e.g. Supabase, Render, Heroku) often provide 'postgres://'
        # SQLAlchemy 2.0 requires 'postgresql://' or 'postgresql+psycopg://'
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)

        if url.startswith("sqlite:///./") or url == "sqlite:///handoverledger.db":
            # Direct SQLite database file to data_directory to avoid hot-reloads
            db_path = self.data_directory / "handoverledger.db"
            return f"sqlite:///{db_path}"
        return url

    @property
    def fallback_models_list(self) -> List[str]:
        if not self.GEMINI_FALLBACK_MODELS:
            return []
        return [m.strip() for m in self.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]

    @property
    def all_gemini_models(self) -> List[str]:
        candidates = [self.GEMINI_MODEL]
        for m in self.fallback_models_list:
            if m not in candidates:
                candidates.append(m)
        return candidates

    @property
    def cors_origins_list(self) -> List[str]:
        default_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://handoverledger.vercel.app",
        ]
        if not self.CORS_ORIGINS:
            return default_origins
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        for default in default_origins:
            if default not in origins:
                origins.append(default)
        return origins

settings = Settings()
