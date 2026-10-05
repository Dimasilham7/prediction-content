"""Local fallback classifiers (text toxicity + NSFW image)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger(__name__)

TEXT_MODEL = "unitary/multilingual-toxic-xlm-roberta"
NSFW_MODEL = "Falconsai/nsfw_image_detection"

# Map local signals -> policy categories used by the aggregator
TOXIC_LABEL_MAP = {
    "toxic": "ujaran_kebencian",
    "severe_toxic": "ujaran_kebencian",
    "obscene": "nudity_sexual",
    "threat": "kekerasan_gore",
    "insult": "perundungan",
    "identity_hate": "ujaran_kebencian",
}


_text_pipe_failed = False
_nsfw_pipe_failed = False


@lru_cache(maxsize=1)
def _text_pipe():
    from transformers import pipeline

    return pipeline(
        "text-classification",
        model=TEXT_MODEL,
        top_k=None,
        truncation=True,
        max_length=512,
    )


@lru_cache(maxsize=1)
def _nsfw_pipe():
    from transformers import pipeline

    return pipeline("image-classification", model=NSFW_MODEL)


def _get_text_pipe():
    global _text_pipe_failed
    if _text_pipe_failed:
        return None
    try:
        return _text_pipe()
    except Exception as exc:  # noqa: BLE001
        _text_pipe_failed = True
        logger.warning("Local text model unavailable: %s", exc)
        return None


def _get_nsfw_pipe():
    global _nsfw_pipe_failed
    if _nsfw_pipe_failed:
        return None
    try:
        return _nsfw_pipe()
    except Exception as exc:  # noqa: BLE001
        _nsfw_pipe_failed = True
        logger.warning("Local NSFW model unavailable: %s", exc)
        return None


def _empty_answers() -> dict[str, Any]:
    return {
        "layak_tampil": 0.7,
        "kategori_pelanggaran": {
            "choice": "none",
            "confidence": 0.5,
            "probabilities": {"none": 0.5},
        },
        "tingkat_keparahan": {
            "score": 0.0,
            "confidence": 0.5,
            "legend": ["aman", "ringan", "berat", "banned"],
            "probabilities": [0.7, 0.2, 0.07, 0.03],
        },
        "caption_clickbait_spam": 0.1,
        "hashtag_terlarang": 0.05,
        "teks_kasar_di_media": 0.05,
        "cocok_di_bawah_18": 0.8,
    }


def _classify_text(caption: str, hashtags: str) -> dict[str, float]:
    text = f"{caption}\n{hashtags}".strip()
    scores: dict[str, float] = {}
    if not text:
        return scores
    pipe = _get_text_pipe()
    if pipe is None:
        return scores
    try:
        raw = pipe(text)[0]
        for item in raw:
            label = str(item["label"]).lower()
            score = float(item["score"])
            cat = TOXIC_LABEL_MAP.get(label)
            if cat:
                scores[cat] = max(scores.get(cat, 0.0), score)
            if label in {"toxic", "LABEL_1"} and "toxic" not in TOXIC_LABEL_MAP:
                scores["ujaran_kebencian"] = max(scores.get("ujaran_kebencian", 0.0), score)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Local text classifier failed: %s", exc)
    return scores


def _classify_images(image_paths: list[Path]) -> float:
    """Return max NSFW probability across frames."""
    if not image_paths:
        return 0.0
    pipe = _get_nsfw_pipe()
    if pipe is None:
        return 0.0

    max_nsfw = 0.0
    for path in image_paths[:8]:
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                results = pipe(im)
            for item in results:
                label = str(item["label"]).lower()
                score = float(item["score"])
                if label in {"nsfw", "porn", "hentai", "sexy"}:
                    max_nsfw = max(max_nsfw, score)
        except Exception as exc:  # noqa: BLE001
            logger.warning("NSFW classify failed for %s: %s", path, exc)
    return max_nsfw


def _heuristic_caption(caption: str, hashtags: str) -> dict[str, float]:
    text = f"{caption} {hashtags}".lower()
    spam_markers = [
        "follow for follow",
        "f4f",
        "link in bio",
        "klik link",
        "dm me",
        "giveaway palsu",
        "100% menang",
        "cepat kaya",
    ]
    banned_tags = ["#xxx", "#nude", "#onlyfans", "#porn", "#judi", "#slotgacor", "#togel"]
    clickbait = any(m in text for m in spam_markers)
    hashtag_hit = any(t in text for t in banned_tags)
    return {
        "caption_clickbait_spam": 0.85 if clickbait else 0.12,
        "hashtag_terlarang": 0.9 if hashtag_hit else 0.08,
    }


def run_local(
    *,
    caption: str,
    hashtags: str,
    image_paths: list[Path],
) -> dict[str, Any]:
    """
    Produce a Clef-like answers dict from local models + light heuristics.
    """
    answers = _empty_answers()
    heuristics = _heuristic_caption(caption, hashtags)
    answers["caption_clickbait_spam"] = heuristics["caption_clickbait_spam"]
    answers["hashtag_terlarang"] = heuristics["hashtag_terlarang"]

    text_scores = _classify_text(caption, hashtags)
    nsfw = _classify_images(image_paths)
    if nsfw > 0.35:
        text_scores["nudity_sexual"] = max(text_scores.get("nudity_sexual", 0.0), nsfw)

    if not text_scores:
        # still adjust layak based on heuristics
        risk = max(heuristics.values())
        answers["layak_tampil"] = max(0.05, 1.0 - risk)
        if risk > 0.7:
            answers["kategori_pelanggaran"] = {
                "choice": "penipuan_spam",
                "confidence": risk,
                "probabilities": {"penipuan_spam": risk, "none": 1 - risk},
            }
            answers["tingkat_keparahan"] = {
                "score": 1.5,
                "confidence": risk,
                "legend": ["aman", "ringan", "berat", "banned"],
                "probabilities": [0.1, 0.45, 0.35, 0.1],
            }
        return answers

    top_cat, top_p = max(text_scores.items(), key=lambda kv: kv[1])
    probs = {**{k: 0.02 for k in text_scores}, top_cat: top_p, "none": max(0.01, 1.0 - top_p)}
    # normalize lightly
    total = sum(probs.values())
    probs = {k: v / total for k, v in probs.items()}

    answers["kategori_pelanggaran"] = {
        "choice": top_cat if top_p >= 0.45 else "none",
        "confidence": top_p,
        "probabilities": probs,
    }
    answers["layak_tampil"] = max(0.02, 1.0 - top_p)
    answers["teks_kasar_di_media"] = text_scores.get("ujaran_kebencian", 0.05)
    answers["cocok_di_bawah_18"] = max(0.05, 1.0 - max(nsfw, top_p * 0.8))

    if top_p >= 0.8:
        sev_probs = [0.05, 0.15, 0.35, 0.45]
        score = 2.5
    elif top_p >= 0.55:
        sev_probs = [0.1, 0.25, 0.45, 0.2]
        score = 1.8
    elif top_p >= 0.35:
        sev_probs = [0.2, 0.5, 0.25, 0.05]
        score = 1.0
    else:
        sev_probs = [0.7, 0.2, 0.08, 0.02]
        score = 0.3

    answers["tingkat_keparahan"] = {
        "score": score,
        "confidence": top_p,
        "legend": ["aman", "ringan", "berat", "banned"],
        "probabilities": sev_probs,
    }
    return answers
