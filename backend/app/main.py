from __future__ import annotations

import logging
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.preprocess import PreprocessError, tool_ok
from app.schemas import AnalyzeResponse, HealthResponse, SuggestionProvider
from app.service import analyze_content

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Prediction Content",
    description="Prediksi kelayakan konten IG/TikTok (Clef + local fallback + saran opsional)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    providers = ["rules"]
    if settings.openai_api_key:
        providers.append("openai")
    if settings.anthropic_api_key:
        providers.append("claude")
    if settings.clef_configured:
        providers.append("workers_ai")
    # Always advertise optional providers (keys may be sent per-request from UI)
    for p in ("openai", "claude", "workers_ai"):
        if p not in providers:
            providers.append(p)

    return HealthResponse(
        status="ok",
        clef_configured=settings.clef_configured,
        local_fallback=settings.use_local_fallback,
        ffmpeg_ok=tool_ok(settings.ffmpeg_path),
        ffprobe_ok=tool_ok(settings.ffprobe_path),
        openai_configured=bool(settings.openai_api_key),
        claude_configured=bool(settings.anthropic_api_key),
        suggestion_providers=providers,
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    platform: Annotated[str, Form()] = "tiktok",
    caption: Annotated[str, Form()] = "",
    hashtags: Annotated[str, Form()] = "",
    suggestion_provider: Annotated[str, Form()] = "rules",
    temperature: Annotated[float, Form()] = 0.3,
    openai_api_key: Annotated[str, Form()] = "",
    anthropic_api_key: Annotated[str, Form()] = "",
    force_local: Annotated[bool, Form()] = False,
    file: UploadFile | None = File(None),
) -> AnalyzeResponse:
    if platform not in {"instagram", "tiktok", "both"}:
        raise HTTPException(400, "platform harus instagram | tiktok | both")

    provider: SuggestionProvider
    if suggestion_provider not in {"rules", "openai", "claude", "workers_ai"}:
        raise HTTPException(400, "suggestion_provider tidak valid")
    provider = suggestion_provider  # type: ignore[assignment]

    file_bytes: bytes | None = None
    filename: str | None = None
    if file is not None and file.filename:
        file_bytes = await file.read()
        filename = file.filename
        if not file_bytes:
            file_bytes = None
            filename = None

    if not caption.strip() and not hashtags.strip() and not file_bytes:
        raise HTTPException(400, "Isi caption/hashtag atau upload media.")

    try:
        return await analyze_content(
            settings=settings,
            platform=platform,
            caption=caption,
            hashtags=hashtags,
            file_bytes=file_bytes,
            filename=filename,
            suggestion_provider=provider,
            temperature=temperature,
            openai_api_key=openai_api_key or None,
            anthropic_api_key=anthropic_api_key or None,
            force_local=force_local,
        )
    except PreprocessError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze failed")
        raise HTTPException(500, f"Analisis gagal: {exc}") from exc
