"""Orchestrator: Claude / OpenAI / Workers AI expand judge findings into rich coaching.

Decision agents (Clef/Drex/local) act as judges with typed probabilities.
LLM providers act as creative orchestrators (aesthetic, CTA timing, caption rewrite).
Falls back to rules-based coaching when no key / LLM fails.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.coach import (
    extract_quality_scores,
    quality_to_dict,
    rules_content_tips,
    rules_timeline_cues,
)
from app.config import Settings
from app.rules import rules_suggestions
from app.schemas import ContentTip, QualityScores, SuggestionProvider, TimelineCue, Violation

logger = logging.getLogger(__name__)


def clamp_temperature(value: float | None, default: float) -> float:
    t = default if value is None else float(value)
    return max(0.0, min(2.0, t))


def _orchestrator_prompt(
    *,
    platform: str,
    caption: str,
    hashtags: str,
    violations: list[Violation],
    caption_issues: list[str],
    media_summary: dict[str, Any],
    quality: QualityScores,
    base_tips: list[ContentTip],
    base_cues: list[TimelineCue],
    policy_suggestions: list[str],
) -> str:
    return f"""Kamu adalah creative director + policy coach untuk kreator Instagram/TikTok di Indonesia.

Decision judge (Clef/Drex/Jev-style) sudah menilai konten dengan probabilitas. Tugasmu sebagai ORCHESTRATOR:
perluas temuan itu jadi saran yang konkret, actionable, dan spesifik waktu (untuk video).

Kembalikan HANYA JSON object (tanpa markdown) dengan bentuk:
{{
  "suggestions": ["...string saran policy/umum..."],
  "content_tips": [
    {{"area":"estetika|hook|cta|pacing|caption|umum","title":"...","detail":"...","priority":"tinggi|sedang|rendah"}}
  ],
  "timeline_cues": [
    {{"at_sec":0.0,"end_sec":3.0,"action":"...","detail":"...","kind":"hook|cta|visual|pacing|umum"}}
  ]
}}

Aturan:
- Bahasa Indonesia, singkat, operasional (bukan teori).
- Kalau media = video: WAJIB isi timeline_cues (minimal hook 0–3s + CTA di detik tertentu).
- Kalau foto: fokus estetika/crop/lighting + caption; timeline_cues boleh [].
- Contoh CTA bagus: "Di detik 4.5–6.0 tampilkan teks 'Simpan biar nggak hilang'".
- Contoh estetika: "Frame buram — naikkan exposure / ganti angle close-up subjek".
- Jangan mengarang pelanggaran policy yang tidak ada di judge findings.
- 3–6 suggestions, 2–5 content_tips, 2–5 timeline_cues (jika video).

DATA:
platform: {platform}
caption: {caption}
hashtags: {hashtags}
violations: {json.dumps([v.model_dump() for v in violations], ensure_ascii=False)}
caption_issues: {json.dumps(caption_issues, ensure_ascii=False)}
media: {json.dumps(media_summary, ensure_ascii=False)}
quality_scores_0_to_1: {json.dumps(quality_to_dict(quality), ensure_ascii=False)}
seed_policy_suggestions: {json.dumps(policy_suggestions, ensure_ascii=False)}
seed_content_tips: {json.dumps([t.model_dump() for t in base_tips], ensure_ascii=False)}
seed_timeline_cues: {json.dumps([c.model_dump() for c in base_cues], ensure_ascii=False)}
"""


def _parse_orchestrator(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return {"suggestions": data, "content_tips": [], "timeline_cues": []}
    except json.JSONDecodeError:
        pass
    return None


def _coerce_tips(raw: Any) -> list[ContentTip]:
    out: list[ContentTip] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append(ContentTip(area="umum", title="Saran", detail=item.strip()))
            continue
        if not isinstance(item, dict):
            continue
        try:
            out.append(
                ContentTip(
                    area=str(item.get("area") or "umum"),
                    title=str(item.get("title") or "Saran"),
                    detail=str(item.get("detail") or item.get("text") or ""),
                    priority=item.get("priority") or "sedang",  # type: ignore[arg-type]
                )
            )
        except Exception:  # noqa: BLE001
            continue
    return [t for t in out if t.detail]


def _coerce_cues(raw: Any) -> list[TimelineCue]:
    out: list[TimelineCue] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            at = float(item.get("at_sec", item.get("second", 0)))
            end = item.get("end_sec")
            out.append(
                TimelineCue(
                    at_sec=at,
                    end_sec=float(end) if end is not None else None,
                    action=str(item.get("action") or "Edit"),
                    detail=str(item.get("detail") or ""),
                    kind=str(item.get("kind") or "umum"),
                )
            )
        except Exception:  # noqa: BLE001
            continue
    return [c for c in out if c.detail]


async def _openai_raw(prompt: str, *, api_key: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "temperature": temperature,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only a valid JSON object. No markdown.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
        )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


async def _claude_raw(prompt: str, *, api_key: str, temperature: float) -> str:
    t = min(temperature, 1.0)
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1600,
                "temperature": t,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    resp.raise_for_status()
    blocks = resp.json().get("content") or []
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


async def _workers_ai_raw(prompt: str, *, settings: Settings, temperature: float) -> str:
    if not settings.clef_configured:
        raise RuntimeError("Workers AI credentials missing")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}"
        f"/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.cf_api_token}"},
            json={
                "messages": [
                    {"role": "system", "content": "Return only a valid JSON object."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
            },
        )
    resp.raise_for_status()
    payload = resp.json()
    result = payload.get("result", payload)
    content = result.get("response") or result.get("result") or ""
    if isinstance(content, dict):
        content = content.get("response", str(content))
    return str(content)


async def generate_coaching(
    *,
    settings: Settings,
    provider: SuggestionProvider,
    temperature: float | None,
    platform: str,
    caption: str,
    hashtags: str,
    violations: list[Violation],
    caption_issues: list[str],
    media_summary: dict[str, Any],
    answers: dict[str, Any],
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
) -> tuple[list[str], list[ContentTip], list[TimelineCue], QualityScores, SuggestionProvider, float]:
    """
    Returns suggestions, content_tips, timeline_cues, quality, used_provider, temperature.
    """
    temp = clamp_temperature(temperature, settings.default_temperature)
    quality = extract_quality_scores(answers)
    media_kind = str(media_summary.get("kind") or "none")
    duration = media_summary.get("duration_sec")
    stamps = media_summary.get("sample_timestamps_sec") or []

    policy = rules_suggestions(violations, caption_issues)
    tips = rules_content_tips(quality, media_kind=media_kind, platform=platform)
    cues = rules_timeline_cues(
        quality,
        media_kind=media_kind,
        duration_sec=float(duration) if duration is not None else None,
        sample_timestamps=[float(x) for x in stamps] if isinstance(stamps, list) else [],
    )

    if provider == "rules":
        # Flatten tips into suggestions list for backward-compatible checklist
        merged = list(policy)
        for tip in tips:
            line = f"{tip.title}: {tip.detail}"
            if line not in merged:
                merged.append(line)
        for cue in cues[:3]:
            end = f"–{cue.end_sec:.1f}s" if cue.end_sec is not None else ""
            line = f"[{cue.at_sec:.1f}s{end}] {cue.action} — {cue.detail}"
            if line not in merged:
                merged.append(line)
        return merged, tips, cues, quality, "rules", temp

    prompt = _orchestrator_prompt(
        platform=platform,
        caption=caption,
        hashtags=hashtags,
        violations=violations,
        caption_issues=caption_issues,
        media_summary=media_summary,
        quality=quality,
        base_tips=tips,
        base_cues=cues,
        policy_suggestions=policy,
    )

    openai_key = (openai_api_key or settings.openai_api_key or "").strip()
    claude_key = (anthropic_api_key or settings.anthropic_api_key or "").strip()

    try:
        if provider == "openai":
            if not openai_key:
                return await generate_coaching(
                    settings=settings,
                    provider="rules",
                    temperature=temp,
                    platform=platform,
                    caption=caption,
                    hashtags=hashtags,
                    violations=violations,
                    caption_issues=caption_issues,
                    media_summary=media_summary,
                    answers=answers,
                )
            raw = await _openai_raw(prompt, api_key=openai_key, temperature=temp)
            used: SuggestionProvider = "openai"
        elif provider == "claude":
            if not claude_key:
                return await generate_coaching(
                    settings=settings,
                    provider="rules",
                    temperature=temp,
                    platform=platform,
                    caption=caption,
                    hashtags=hashtags,
                    violations=violations,
                    caption_issues=caption_issues,
                    media_summary=media_summary,
                    answers=answers,
                )
            raw = await _claude_raw(prompt, api_key=claude_key, temperature=temp)
            used = "claude"
        elif provider == "workers_ai":
            raw = await _workers_ai_raw(prompt, settings=settings, temperature=temp)
            used = "workers_ai"
        else:
            return policy, tips, cues, quality, "rules", temp

        parsed = _parse_orchestrator(raw)
        if not parsed:
            raise RuntimeError("Orchestrator returned unparseable JSON")

        suggestions = [
            s.strip()
            for s in (parsed.get("suggestions") or [])
            if isinstance(s, str) and s.strip()
        ] or policy
        out_tips = _coerce_tips(parsed.get("content_tips")) or tips
        out_cues = _coerce_cues(parsed.get("timeline_cues")) or cues
        return suggestions, out_tips, out_cues, quality, used, temp
    except Exception as exc:  # noqa: BLE001
        logger.warning("Orchestrator failed (%s): %s — rules coaching", provider, exc)
        return await generate_coaching(
            settings=settings,
            provider="rules",
            temperature=temp,
            platform=platform,
            caption=caption,
            hashtags=hashtags,
            violations=violations,
            caption_issues=caption_issues,
            media_summary=media_summary,
            answers=answers,
        )


# Back-compat alias used by older imports
async def generate_suggestions(**kwargs):  # type: ignore[no-untyped-def]
    suggestions, _tips, _cues, _q, provider, temp = await generate_coaching(**kwargs)
    return suggestions, provider, temp
