"""Content coach: turn judge scores + media timestamps into actionable tips.

Works with rules (no LLM) or Claude/OpenAI as orchestrator after the decision judge.
"""

from __future__ import annotations

from typing import Any

from app.rules import noul_prob, severity_from_score
from app.schemas import ContentTip, QualityScores, TimelineCue


QUALITY_KEYS = (
    "estetika_visual",
    "hook_awal",
    "cta_kejelasan",
    "pacing_edit",
    "kualitas_caption",
)

QUALITY_LABELS = {
    "estetika_visual": "Estetika visual",
    "hook_awal": "Hook awal",
    "cta_kejelasan": "CTA",
    "pacing_edit": "Pacing / edit",
    "kualitas_caption": "Kualitas caption",
}

# score is 0..3 expected value from SystemOne score questions
def _score_value(answer: Any) -> float | None:
    if not isinstance(answer, dict):
        return None
    score = answer.get("score")
    if isinstance(score, (int, float)):
        return float(score)
    probs = answer.get("probabilities")
    if isinstance(probs, list) and probs:
        return sum(i * float(p) for i, p in enumerate(probs))
    if isinstance(probs, dict) and probs:
        total = 0.0
        for k, p in probs.items():
            try:
                total += int(k) * float(p)
            except (TypeError, ValueError):
                continue
        return total
    # map severity-like labels if present
    sev = severity_from_score(answer)
    mapping = {"aman": 0.0, "ringan": 1.0, "berat": 2.0, "banned": 3.0}
    return mapping.get(sev)


def extract_quality_scores(answers: dict[str, Any]) -> QualityScores:
    def one(key: str) -> float | None:
        v = _score_value(answers.get(key))
        if v is None:
            return None
        # normalize 0..3 → 0..1 for UI bars
        return round(max(0.0, min(1.0, v / 3.0)), 4)

    return QualityScores(
        estetika_visual=one("estetika_visual"),
        hook_awal=one("hook_awal"),
        cta_kejelasan=one("cta_kejelasan"),
        pacing_edit=one("pacing_edit"),
        kualitas_caption=one("kualitas_caption"),
        perlu_perbaikan_konten=noul_prob(answers.get("perlu_perbaikan_konten"))
        if answers.get("perlu_perbaikan_konten") is not None
        else None,
    )


def _weak(score_01: float | None, threshold: float = 0.55) -> bool:
    return score_01 is not None and score_01 < threshold


def rules_content_tips(
    quality: QualityScores,
    *,
    media_kind: str,
    platform: str,
) -> list[ContentTip]:
    tips: list[ContentTip] = []
    plat = "TikTok" if platform == "tiktok" else "Instagram" if platform == "instagram" else "IG/TikTok"

    if _weak(quality.estetika_visual):
        if media_kind == "image":
            tips.append(
                ContentTip(
                    area="estetika",
                    title="Foto kurang estetis untuk feed",
                    detail=(
                        f"Naikkan kontras/lighting, crop subjek ke rule-of-thirds, "
                        f"hindari noise. Thumbnail {plat} harus kebaca di ukuran kecil."
                    ),
                    priority="tinggi",
                )
            )
        else:
            tips.append(
                ContentTip(
                    area="estetika",
                    title="Frame visual kurang menarik",
                    detail=(
                        "Stabilkan kamera, perbaiki exposure, dan pilih angle yang lebih dekat "
                        "ke subjek di 2–3 detik pertama agar tidak terlihat amatir."
                    ),
                    priority="tinggi",
                )
            )

    if _weak(quality.hook_awal):
        tips.append(
            ContentTip(
                area="hook",
                title="Hook awal lemah",
                detail=(
                    "Mulai dengan teks besar / gerakan / pertanyaan di 0–3 detik. "
                    "Jangan buka dengan logo diam atau intro panjang."
                ),
                priority="tinggi",
            )
        )

    if _weak(quality.cta_kejelasan):
        tips.append(
            ContentTip(
                area="cta",
                title="CTA belum jelas",
                detail=(
                    "Tambahkan CTA spesifik (ikuti, simpan, komentar jawaban, swipe). "
                    "Hindari CTA spam seperti 'DM me 100% menang'."
                ),
                priority="sedang",
            )
        )

    if _weak(quality.pacing_edit) and media_kind == "video":
        tips.append(
            ContentTip(
                area="pacing",
                title="Pacing terasa datar",
                detail=(
                    "Potong jeda mati, ganti shot tiap 1–2 detik di bagian awal, "
                    "pakai zoom/cut-on-action biar ritmenya hidup."
                ),
                priority="sedang",
            )
        )

    if _weak(quality.kualitas_caption):
        tips.append(
            ContentTip(
                area="caption",
                title="Caption perlu ditulis ulang",
                detail=(
                    "Pakai pola: hook 1 baris → 1 insight konkret → CTA alami. "
                    "Sebut topik spesifik, bukan kalimat generik."
                ),
                priority="sedang",
            )
        )

    if not tips and (quality.perlu_perbaikan_konten or 0) >= 0.55:
        tips.append(
            ContentTip(
                area="umum",
                title="Masih ada ruang perbaikan kreatif",
                detail=(
                    "Konten relatif aman, tapi naikkan daya tahan di feed: "
                    "perkuat hook, estetika, dan satu CTA yang jelas."
                ),
                priority="rendah",
            )
        )

    return tips


def rules_timeline_cues(
    quality: QualityScores,
    *,
    media_kind: str,
    duration_sec: float | None,
    sample_timestamps: list[float] | None,
) -> list[TimelineCue]:
    if media_kind != "video":
        return []

    duration = duration_sec or 0.0
    stamps = sample_timestamps or []
    cues: list[TimelineCue] = []

    # Hook window — always for short-form video coaching
    cues.append(
        TimelineCue(
            at_sec=0.0,
            end_sec=min(3.0, duration) if duration else 3.0,
            action="Pasang hook",
            detail=(
                "Tampilkan teks hook / gerakan utama segera. "
                "Contoh: '3 kesalahan yang bikin kontenmu di-skip'."
            ),
            kind="hook",
        )
    )

    if _weak(quality.estetika_visual) and stamps:
        mid = stamps[len(stamps) // 2]
        cues.append(
            TimelineCue(
                at_sec=round(mid, 2),
                end_sec=None,
                action="Perbaiki frame ini",
                detail=(
                    f"Sekitar detik {mid:.1f}: cek lighting/crop. "
                    "Ganti shot yang gelap atau goyang."
                ),
                kind="visual",
            )
        )

    # CTA timing: ~70% into video or last 3s
    if duration > 0:
        cta_at = max(0.0, round(duration * 0.7, 2))
        cta_end = round(duration, 2)
    else:
        cta_at, cta_end = 5.0, 8.0

    # CTA window — always suggest a concrete second range
    cues.append(
        TimelineCue(
            at_sec=cta_at,
            end_sec=cta_end,
            action="Munculkan CTA",
            detail=(
                f"Di detik {cta_at:.1f}-{cta_end:.1f}: tampilkan CTA on-screen "
                "(ikuti / simpan / komentar). Ulangi singkat di caption."
            ),
            kind="cta",
        )
    )

    if _weak(quality.pacing_edit) and duration >= 4:
        cues.append(
            TimelineCue(
                at_sec=round(min(2.0, duration / 3), 2),
                end_sec=round(min(duration, duration * 0.55), 2),
                action="Percepat ritme",
                detail="Tambah cut / B-roll agar bagian tengah tidak datar.",
                kind="pacing",
            )
        )

    # dedupe by (at_sec, action)
    seen: set[tuple[float, str]] = set()
    out: list[TimelineCue] = []
    for c in cues:
        key = (c.at_sec, c.action)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def quality_to_dict(quality: QualityScores) -> dict[str, float | None]:
    return quality.model_dump()
