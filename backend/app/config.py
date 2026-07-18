"""
Application configuration using pydantic-settings.
All values can be overridden via environment variables or a .env file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    app_name: str = "CAD-CAE Analyzer"
    app_env: Literal["development", "production", "testing"] = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    api_prefix: str = "/api"

    # ── Database ──────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./cae_local.db"

    # ── Redis / Celery ────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Storage ───────────────────────────────────────────────
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: Path = Path("./storage")
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "cae-files"
    s3_endpoint_url: str = ""

    # ── Solvers ───────────────────────────────────────────────
    ccx_binary: str = "ccx"
    gmsh_binary: str = "gmsh"
    openfoam_script: str = "/opt/openfoam10/etc/bashrc"
    mock_solver_mode: bool = True   # Safe default for local dev
    mock_cad_mode: bool = True      # trimesh only (no pythonocc)

    @property
    def solver_workspace(self) -> Path:
        """Cross-platform solver workspace directory."""
        import tempfile
        return Path(tempfile.gettempdir()) / "cae_jobs"

    # ── Chatbot ───────────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-5"
    rag_collection_name: str = "cae_knowledge"
    chatbot_enabled: bool = True

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null",   # file:// origin
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # ── File Upload ───────────────────────────────────────────
    max_file_size_mb: int = 500
    allowed_extensions: Any = [
        ".step", ".stp", ".iges", ".igs", ".stl", ".obj"
    ]

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v):
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    # ── Jobs ──────────────────────────────────────────────────
    job_timeout_seconds: int = 3600
    max_concurrent_jobs_per_user: int = 3

    # ── Computed helpers ──────────────────────────────────────
    @property
    def upload_dir(self) -> Path:
        return self.local_storage_path / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.local_storage_path / "jobs"

    @property
    def results_dir(self) -> Path:
        return self.local_storage_path / "results"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()

# Ensure storage directories exist on startup
for _dir in [
    settings.local_storage_path,
    settings.upload_dir,
    settings.jobs_dir,
    settings.results_dir,
    settings.solver_workspace,
]:
    _dir.mkdir(parents=True, exist_ok=True)
