from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cf_account_id: str = ""
    cf_api_token: str = ""
    clef_model: str = "@cf/cloudflare/clef"
    clef_model_name: str = "clef"

    # Drex (Nace AI) — SystemOne-compatible decision model
    # Hosted: https://drex.nace.ai  | Local e.g. http://127.0.0.1:8097
    drex_api_key: str = ""
    drex_base_url: str = "https://drex.nace.ai"
    drex_model: str = "drex-v1.0"
    default_decision_agent: str = "clef"

    use_local_fallback: bool = True

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    enable_llm_suggestions: bool = False
    default_suggestion_provider: str = "rules"
    default_temperature: float = 0.3

    ffmpeg_path: str = r"D:\devtools\ffmpeg\bin\ffmpeg.exe"
    ffprobe_path: str = r"D:\devtools\ffmpeg\bin\ffprobe.exe"

    hf_home: str = r"D:\devtools\hf-cache"
    torch_home: str = r"D:\devtools\torch-cache"

    upload_dir: str = "uploads"
    max_upload_mb: int = 50
    cors_origins: str = "http://localhost:3000"

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def clef_configured(self) -> bool:
        return bool(self.cf_account_id and self.cf_api_token)

    @property
    def drex_configured(self) -> bool:
        """Hosted needs a key; local base URL without nace.ai is treated as ready."""
        base = (self.drex_base_url or "").lower()
        if "drex.nace.ai" in base:
            return bool(self.drex_api_key)
        return bool(self.drex_base_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
