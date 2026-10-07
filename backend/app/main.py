from __future__ import annotations

import logging
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.preprocess import PreprocessError, tool_ok
from app.schemas import AnalyzeResponse, DecisionAgent, HealthResponse, SuggestionProvider
from app.service import analyze_content

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Prediction Content",
    description=(
        "Prediksi kelayakan konten IG/TikTok — decision agent Clef / Drex / lokal "
        "+ saran Rules/Claude/OpenAI"
    ),
    version="0.2.0",
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
    providers = ["rules", "openai", "claude", "workers_ai"]
    agents = ["clef", "drex", "local"]

    return HealthResponse(
        status="ok",
        clef_configured=settings.clef_configured,
        drex_configured=settings.drex_configured,
        local_fallback=settings.use_local_fallback,
        ffmpeg_ok=tool_ok(settings.ffmpeg_path),
        ffprobe_ok=tool_ok(settings.ffprobe_path),
        openai_configured=bool(settings.openai_api_key),
        claude_configured=bool(settings.anthropic_api_key),
        decision_agents=agents,
        suggestion_providers=providers,
        default_decision_agent=settings.default_decision_agent
        if settings.default_decision_agent in agents
        else "clef",
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    platform: Annotated[str, Form()] = "tiktok",
    caption: Annotated[str, Form()] = "",
    hashtags: Annotated[str, Form()] = "",
    decision_agent: Annotated[str, Form()] = "clef",
    suggestion_provider: Annotated[str, Form()] = "rules",
    temperature: Annotated[float, Form()] = 0.3,
    openai_api_key: Annotated[str, Form()] = "",
    anthropic_api_key: Annotated[str, Form()] = "",
    drex_api_key: Annotated[str, Form()] = "",
    force_local: Annotated[bool, Form()] = False,
    file: UploadFile | None = File(None),
) -> AnalyzeResponse:
    if platform not in {"instagram", "tiktok", "both"}:
        raise HTTPException(400, "platform harus instagram | tiktok | both")

    if decision_agent not in {"clef", "drex", "local"}:
        raise HTTPException(400, "decision_agent harus clef | drex | local")
    agent: DecisionAgent = decision_agent  # type: ignore[assignment]

    if suggestion_provider not in {"rules", "openai", "claude", "workers_ai"}:
        raise HTTPException(400, "suggestion_provider tidak valid")
    provider: SuggestionProvider = suggestion_provider  # type: ignore[assignment]

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
            decision_agent=agent,
            suggestion_provider=provider,
            temperature=temperature,
            openai_api_key=openai_api_key or None,
            anthropic_api_key=anthropic_api_key or None,
            drex_api_key=drex_api_key or None,
            force_local=force_local,
        )
    except PreprocessError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze failed")
        raise HTTPException(500, f"Analisis gagal: {exc}") from exc
