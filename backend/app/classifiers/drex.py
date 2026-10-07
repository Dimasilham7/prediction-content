"""Drex (Nace AI) SystemOne client — same typed decision API as Clef/Jev.

Hosted: POST https://drex.nace.ai/v1/systemone  (Bearer DREX_API_KEY)
Local:  POST {DREX_BASE_URL}/v1/systemone       (optional key)

Drex hosted/local open-source runners are text-oriented; media frames are
summarized into `state` (ffmpeg probe) rather than embedded as images.
See: https://huggingface.co/nace-ai/drex-dlm
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.questions import build_questions, build_state


class DrexError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


async def run_drex(
    *,
    settings: Settings,
    platform: str,
    caption: str,
    hashtags: str,
    media_summary: dict,
    api_key: str | None = None,
) -> dict[str, Any]:
    key = (api_key or settings.drex_api_key or "").strip()
    base = settings.drex_base_url.rstrip("/")
    # Local servers often don't need a key; hosted does.
    hosted = "drex.nace.ai" in base
    if hosted and not key:
        raise DrexError("Drex API key required for hosted API (drex.nace.ai)")

    body: dict[str, Any] = {
        "model": settings.drex_model,
        "state": build_state(
            platform=platform,
            caption=caption,
            hashtags=hashtags,
            media_summary=media_summary,
        ),
        "questions": build_questions(platform),
    }

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    url = f"{base}/v1/systemone"
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=body)

    if resp.status_code in {401, 402, 403}:
        raise DrexError("Drex auth failed / invalid key", status_code=resp.status_code)
    if resp.status_code == 429:
        raise DrexError("Drex rate limited", status_code=429)
    if resp.status_code >= 400:
        raise DrexError(
            f"Drex HTTP {resp.status_code}: {resp.text[:500]}",
            status_code=resp.status_code,
        )

    payload = resp.json()
    if isinstance(payload, dict) and "answers" in payload:
        return payload
    if isinstance(payload, dict) and "result" in payload:
        result = payload["result"]
        if isinstance(result, dict) and "answers" in result:
            return result
    raise DrexError(f"Unexpected Drex response shape: {str(payload)[:300]}")
