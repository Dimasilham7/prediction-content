"""Orchestrates preprocess → classifier → rules → optional LLM suggestions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.classifiers.clef import ClefError, run_clef
from app.classifiers.local import run_local
from app.config import Settings
from app.preprocess import cleanup_work, media_summary_for_state, prepare_media
from app.recommend import generate_suggestions
from app.rules import build_caption_issues, build_violations, choice_info, noul_prob, severity_from_score
from app.schemas import AnalyzeResponse, MediaProbe, SuggestionProvider, Verdict

logger = logging.getLogger(__name__)


def _verdict_from_answers(answers: dict[str, Any]) -> tuple[Verdict, float]:
    layak = noul_prob(answers.get("layak_tampil"))
    category, cat_p, _ = choice_info(answers.get("kategori_pelanggaran"))
    severity = severity_from_score(answers.get("tingkat_keparahan"))

    if category != "none" and (severity in {"berat", "banned"} or cat_p >= 0.7 or layak <= 0.35):
        return "tidak_layak", max(cat_p, 1.0 - layak)
    if category != "none" or severity == "ringan" or layak < 0.65:
        return "perlu_revisi", max(cat_p, 1.0 - layak, 0.55)
    return "layak", max(layak, 1.0 - cat_p)


def _category_probabilities(answers: dict[str, Any]) -> dict[str, float]:
    _, _, probs = choice_info(answers.get("kategori_pelanggaran"))
    return {k: round(v, 4) for k, v in probs.items()}


async def analyze_content(
    *,
    settings: Settings,
    platform: str,
    caption: str,
    hashtags: str,
    file_bytes: bytes | None,
    filename: str | None,
    suggestion_provider: SuggestionProvider = "rules",
    temperature: float | None = None,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    force_local: bool = False,
) -> AnalyzeResponse:
    image_paths: list[Path]
    media: MediaProbe
    work: Path | None
    image_paths, media, work = prepare_media(file_bytes, filename, settings)
    summary = media_summary_for_state(media)

    engine = "local"
    answers: dict[str, Any]

    try:
        if force_local or not settings.clef_configured:
            answers = run_local(
                caption=caption, hashtags=hashtags, image_paths=image_paths
            )
            engine = "local"
        else:
            try:
                result = await run_clef(
                    settings=settings,
                    platform=platform,
                    caption=caption,
                    hashtags=hashtags,
                    media_summary=summary,
                    image_paths=image_paths,
                )
                answers = result.get("answers") or result
                engine = "clef"
            except ClefError as exc:
                logger.warning("Clef failed: %s", exc)
                if not settings.use_local_fallback:
                    raise
                answers = run_local(
                    caption=caption, hashtags=hashtags, image_paths=image_paths
                )
                engine = "local_fallback"

        verdict, confidence = _verdict_from_answers(answers)
        violations = build_violations(
            answers, sample_timestamps=media.sample_timestamps_sec
        )
        caption_issues = build_caption_issues(answers, hashtags)

        suggestions, used_provider, used_temp = await generate_suggestions(
            settings=settings,
            provider=suggestion_provider,
            temperature=temperature,
            platform=platform,
            caption=caption,
            hashtags=hashtags,
            violations=violations,
            caption_issues=caption_issues,
            media_summary=summary,
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
        )

        return AnalyzeResponse(
            verdict=verdict,
            confidence=round(float(confidence), 4),
            platform=platform,  # type: ignore[arg-type]
            violations=violations,
            caption_issues=caption_issues,
            suggestions=suggestions,
            engine=engine,
            suggestion_provider=used_provider,
            temperature=used_temp,
            media=media,
            category_probabilities=_category_probabilities(answers),
            raw_answers=answers if isinstance(answers, dict) else {},
        )
    finally:
        cleanup_work(work)
