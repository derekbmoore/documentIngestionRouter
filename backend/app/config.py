"""
Document Ingestion Router — Configuration
==========================================
Pydantic-based settings loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration."""

    # ---- Application ----
    app_name: str = "Document Ingestion Router"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    debug: bool = False

    # ---- PostgreSQL ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "doc_ingestion"
    postgres_user: str = "dir_admin"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ---- Azure OpenAI (Embeddings) ----
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_embedding_deployment: str = "text-embedding-ada-002"

    # ---- Zep ----
    zep_api_url: str = "http://localhost:8000"
    zep_api_key: Optional[str] = None

    # ---- Temporal ----
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"

    # ---- Auth ----
    auth_required: bool = False
    azure_ad_tenant_id: Optional[str] = None
    azure_ad_client_id: Optional[str] = None

    # ---- Engines ----
    docling_enabled: bool = True

    # ---- Compliance ----
    fips_mode: bool = False
    encryption_at_rest: bool = True

    # ---- Upload ----
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 500

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
