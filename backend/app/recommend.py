"""Optional LLM rewrite of fix suggestions (OpenAI / Claude / Workers AI)."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import httpx

from app.config import Settings
from app.rules import rules_suggestions
from app.schemas import SuggestionProvider, Violation

logger = logging.getLogger(__name__)

Provider = Literal["rules", "openai", "claude", "workers_ai"]


def clamp_temperature(value: float | None, default: float) -> float:
    t = default if value is None else float(value)
    return max(0.0, min(2.0, t))


def _prompt(
    *,
    platform: str,
    caption: str,
    hashtags: str,
    violations: list[Violation],
    caption_issues: list[str],
    media_summary: dict[str, Any],
) -> str:
    return (
        "You are a social media policy coach for Instagram/TikTok creators in Indonesia.\n"
        "Given the moderation findings, write 3-6 concrete, actionable fix suggestions in Bahasa Indonesia.\n"
        "Return ONLY a JSON array of strings. No markdown.\n\n"
        f"platform: {platform}\n"
        f"caption: {caption}\n"
        f"hashtags: {hashtags}\n"
        f"violations: {json.dumps([v.model_dump() for v in violations], ensure_ascii=False)}\n"
        f"caption_issues: {json.dumps(caption_issues, ensure_ascii=False)}\n"
        f"media: {json.dumps(media_summary, ensure_ascii=False)}\n"
    )


def _parse_suggestions(text: str) -> list[str] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            return [x.strip() for x in data if x.strip()]
    except json.JSONDecodeError:
        pass
    # fallback: split lines
    lines = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip()]
    return lines or None


async def _openai(
    prompt: str, *, api_key: str, temperature: float, model: str = "gpt-4o-mini"
) -> list[str]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": "Return only JSON array of strings."},
                    {"role": "user", "content": prompt},
                ],
            },
        )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    parsed = _parse_suggestions(content)
    if not parsed:
        raise RuntimeError("OpenAI returned unparseable suggestions")
    return parsed


async def _claude(
    prompt: str, *, api_key: str, temperature: float, model: str = "claude-haiku-4-5-20251001"
) -> list[str]:
    # Anthropic temperature max is 1.0
    t = min(temperature, 1.0)
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 800,
                "temperature": t,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    resp.raise_for_status()
    blocks = resp.json().get("content") or []
    content = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    parsed = _parse_suggestions(content)
    if not parsed:
        raise RuntimeError("Claude returned unparseable suggestions")
    return parsed


async def _workers_ai(prompt: str, *, settings: Settings, temperature: float) -> list[str]:
    if not settings.clef_configured:
        raise RuntimeError("Workers AI credentials missing")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}"
        f"/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.cf_api_token}"},
            json={
                "messages": [
                    {"role": "system", "content": "Return only JSON array of strings."},
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
    parsed = _parse_suggestions(str(content))
    if not parsed:
        raise RuntimeError("Workers AI returned unparseable suggestions")
    return parsed


async def generate_suggestions(
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
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
) -> tuple[list[str], SuggestionProvider, float]:
    """
    Always safe: falls back to rules if provider missing keys or call fails.
    Temperature is user-configurable (0..2; Claude clamped to 1).
    """
    temp = clamp_temperature(temperature, settings.default_temperature)
    base = rules_suggestions(violations, caption_issues)

    if provider == "rules":
        return base, "rules", temp

    prompt = _prompt(
        platform=platform,
        caption=caption,
        hashtags=hashtags,
        violations=violations,
        caption_issues=caption_issues,
        media_summary=media_summary,
    )

    openai_key = (openai_api_key or settings.openai_api_key or "").strip()
    claude_key = (anthropic_api_key or settings.anthropic_api_key or "").strip()

    try:
        if provider == "openai":
            if not openai_key:
                logger.info("OpenAI selected but no key; using rules")
                return base, "rules", temp
            return await _openai(prompt, api_key=openai_key, temperature=temp), "openai", temp
        if provider == "claude":
            if not claude_key:
                logger.info("Claude selected but no key; using rules")
                return base, "rules", temp
            return await _claude(prompt, api_key=claude_key, temperature=temp), "claude", temp
        if provider == "workers_ai":
            return await _workers_ai(prompt, settings=settings, temperature=temp), "workers_ai", temp
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM suggestions failed (%s): %s — falling back to rules", provider, exc)
        return base, "rules", temp

    return base, "rules", temp
