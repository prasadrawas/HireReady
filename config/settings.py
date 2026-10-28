"""Configuration settings for HireReady pipeline."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini LLM configuration
    google_api_key: str = Field(default="", validation_alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    gemini_fallback_models: str = Field(default="", validation_alias="GEMINI_FALLBACK_MODELS")

    @property
    def fallback_models(self) -> list[str]:
        """Parse comma-separated fallback models into a list."""
        if not self.gemini_fallback_models:
            return []
        return [m.strip() for m in self.gemini_fallback_models.split(",") if m.strip()]

    @property
    def all_models(self) -> list[str]:
        """Primary model + fallbacks in order."""
        return [self.gemini_model] + self.fallback_models

    # PDF output settings
    max_resume_pages: int = Field(default=2, validation_alias="MAX_RESUME_PAGES")
    pdf_paper_size: str = Field(default="A4", validation_alias="PDF_PAPER_SIZE")
    pdf_margin_top: str = Field(default="15mm", validation_alias="PDF_MARGIN_TOP")
    pdf_margin_bottom: str = Field(default="15mm", validation_alias="PDF_MARGIN_BOTTOM")
    pdf_margin_left: str = Field(default="15mm", validation_alias="PDF_MARGIN_LEFT")
    pdf_margin_right: str = Field(default="15mm", validation_alias="PDF_MARGIN_RIGHT")

    # Scoring thresholds
    quick_score_threshold: float = Field(default=0.4, validation_alias="QUICK_SCORE_THRESHOLD")
    max_deep_score_candidates: int = Field(default=30, validation_alias="MAX_DEEP_SCORE_CANDIDATES")

    # Logging
    log_level: str = Field(default="WARNING", validation_alias="LOG_LEVEL")

    # Base directory paths
    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def input_dir(self) -> Path:
        return self.base_dir / "input"

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def templates_dir(self) -> Path:
        return self.base_dir / "templates"

    @property
    def config_dir(self) -> Path:
        return self.base_dir / "config"

    @property
    def master_resume_path(self) -> Path:
        return self.input_dir / "master_resume.html"

    @property
    def preferences_path(self) -> Path:
        return self.input_dir / "preferences.yaml"

    @property
    def ats_companies_path(self) -> Path:
        return self.config_dir / "ats_companies.json"

    @property
    def seen_jobs_path(self) -> Path:
        return self.data_dir / "seen_jobs.json"

    @property
    def tracker_path(self) -> Path:
        return self.data_dir / "tracker.json"


settings = Settings()
