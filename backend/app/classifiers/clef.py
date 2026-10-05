"""Cloudflare Workers AI Clef client (SystemOne-compatible)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.questions import build_questions, build_state


class ClefError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _image_payload(path: Path) -> dict[str, str]:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    suffix = path.suffix.lower().lstrip(".")
    mime = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(suffix, "image/jpeg")
    return {"mime": mime, "data": b64}


async def run_clef(
    *,
    settings: Settings,
    platform: str,
    caption: str,
    hashtags: str,
    media_summary: dict,
    image_paths: list[Path],
) -> dict[str, Any]:
    if not settings.clef_configured:
        raise ClefError("Cloudflare credentials not configured")

    body: dict[str, Any] = {
        "model": settings.clef_model_name,
        "state": build_state(
            platform=platform,
            caption=caption,
            hashtags=hashtags,
            media_summary=media_summary,
        ),
        "questions": build_questions(platform),
    }
    if image_paths:
        # Workers AI Clef accepts up to 4 embedded images
        body["images"] = [_image_payload(p) for p in image_paths[:4]]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cf_account_id}"
        f"/ai/run/{settings.clef_model}"
    )
    headers = {
        "Authorization": f"Bearer {settings.cf_api_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=body)

    if resp.status_code in {401, 403}:
        raise ClefError("Cloudflare auth failed", status_code=resp.status_code)
    if resp.status_code == 429:
        raise ClefError("Clef rate limited / quota exceeded", status_code=429)
    if resp.status_code >= 400:
        raise ClefError(
            f"Clef HTTP {resp.status_code}: {resp.text[:500]}",
            status_code=resp.status_code,
        )

    payload = resp.json()
    # Workers AI wraps result under "result" for many models
    if isinstance(payload, dict) and "result" in payload:
        result = payload["result"]
        if isinstance(result, dict):
            return result
    if isinstance(payload, dict) and "answers" in payload:
        return payload
    raise ClefError(f"Unexpected Clef response shape: {str(payload)[:300]}")
