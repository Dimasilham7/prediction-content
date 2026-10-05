from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Platform = Literal["instagram", "tiktok", "both"]
Verdict = Literal["layak", "perlu_revisi", "tidak_layak"]
SuggestionProvider = Literal["rules", "openai", "claude", "workers_ai"]
Severity = Literal["aman", "ringan", "berat", "banned"]


class MediaProbe(BaseModel):
    """Values extracted via ffprobe/ffmpeg for the uploaded media."""

    kind: Literal["image", "video", "none"] = "none"
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    bitrate: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    has_audio: bool = False
    file_size_bytes: int | None = None
    format_name: str | None = None
    frame_count_extracted: int = 0
    sample_timestamps_sec: list[float] = Field(default_factory=list)
    aspect_ratio: str | None = None
    warnings: list[str] = Field(default_factory=list)


class Violation(BaseModel):
    category: str
    probability: float
    severity: Severity
    evidence: str | None = None
    fix: str


class AnalyzeResponse(BaseModel):
    verdict: Verdict
    confidence: float
    platform: Platform
    violations: list[Violation] = Field(default_factory=list)
    caption_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    engine: str
    suggestion_provider: SuggestionProvider = "rules"
    temperature: float | None = None
    media: MediaProbe | None = None
    category_probabilities: dict[str, float] = Field(default_factory=dict)
    raw_answers: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    clef_configured: bool
    local_fallback: bool
    ffmpeg_ok: bool
    ffprobe_ok: bool
    openai_configured: bool
    claude_configured: bool
    suggestion_providers: list[str]
