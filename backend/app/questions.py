"""Clef / Drex / SystemOne question schema — policy judge + content-quality judge.

Inspired by Jev-as-a-Judge: typed questions with criteria, probabilities per option.
See: https://academy.dair.ai/labs/jev-as-a-judge-for-agent-evals
"""

from __future__ import annotations

CATEGORY_CRITERIA = {
    "none": "No policy violation; safe for public feed.",
    "nudity_sexual": "Nudity, sexual content, or suggestive imagery.",
    "kekerasan_gore": "Violence, gore, graphic injury, or weapons used to harm.",
    "ujaran_kebencian": "Hate speech targeting protected groups or identities.",
    "perundungan": "Bullying, harassment, or shaming of individuals.",
    "aksi_berbahaya": "Dangerous acts that could encourage self-harm or injury.",
    "narkoba_rokok_alkohol": "Drugs, tobacco, vaping, or alcohol promotion.",
    "penipuan_spam": "Scams, phishing, engagement bait, or spam.",
    "misinformasi": "False or misleading claims presented as fact.",
    "keselamatan_anak": "Child safety risks or inappropriate content involving minors.",
    "judi": "Gambling, betting, or casino promotion.",
}

SEVERITY_CRITERIA = [
    "Aman untuk feed publik",
    "Perlu revisi ringan (edit caption/crop)",
    "Pelanggaran berat (potong adegan / rewrite)",
    "Harus dihapus atau dilarang tampil",
]

AESTHETIC_CRITERIA = [
    "Lemah — gelap, buram, framing semrawut, atau terlihat tidak sengaja",
    "Cukup — bisa ditonton tapi kurang menonjol di feed",
    "Baik — lighting/framing rapi, siap bersaing di FYP/Explore",
    "Sangat kuat — visual khas brand, thumb-stopping",
]

HOOK_CRITERIA = [
    "Tidak ada hook di 0–3 detik pertama",
    "Hook lemah / lambat — penonton mudah swipe",
    "Hook cukup jelas di awal",
    "Hook sangat kuat (teks/gerak/pertanyaan langsung)",
]

CTA_CRITERIA = [
    "Tidak ada CTA sama sekali",
    "CTA ada tapi samar atau terlalu spammy",
    "CTA jelas tapi timing kurang pas",
    "CTA jelas dan dipasang di momen yang tepat",
]

PACING_CRITERIA = [
    "Monoton / terlalu lambat — mudah ditinggal",
    "Agak lambat atau lompatan kasar",
    "Pacing cukup untuk platform pendek",
    "Ritme edit kuat, cut tajam, mudah ditonton ulang",
]

CAPTION_QUALITY_CRITERIA = [
    "Caption kosong atau tidak membantu",
    "Ada caption tapi generik / tidak spesifik",
    "Caption jelas dan relevan",
    "Caption kuat: hook teks + nilai + CTA alami",
]


def build_questions(platform: str) -> dict:
    platform_label = {
        "instagram": "Instagram",
        "tiktok": "TikTok",
        "both": "Instagram and TikTok",
    }.get(platform, platform)

    return {
        # --- Policy judge ---
        "layak_tampil": {
            "type": "noul",
            "instructions": (
                f"Is this content safe and suitable to publish on the public {platform_label} feed "
                "without policy risk?"
            ),
        },
        "kategori_pelanggaran": {
            "type": "choice",
            "instructions": (
                f"What is the primary {platform_label} community-guideline violation category, "
                "if any?"
            ),
            "criteria": CATEGORY_CRITERIA,
        },
        "tingkat_keparahan": {
            "type": "score",
            "instructions": "How severe is the policy risk for publishing this content?",
            "criteria": SEVERITY_CRITERIA,
        },
        "caption_clickbait_spam": {
            "type": "noul",
            "instructions": "Does the caption use clickbait, spammy CTAs, or engagement bait?",
        },
        "hashtag_terlarang": {
            "type": "noul",
            "instructions": (
                f"Do any hashtags look banned, shadowbanned, or against {platform_label} rules?"
            ),
        },
        "teks_kasar_di_media": {
            "type": "noul",
            "instructions": "Does on-screen text contain profanity, slurs, or hate speech?",
        },
        "cocok_di_bawah_18": {
            "type": "noul",
            "instructions": "Is this content appropriate for viewers under 18?",
        },
        # --- Content-quality judge (Jev-as-a-Judge style) ---
        "estetika_visual": {
            "type": "score",
            "instructions": (
                f"How strong is the visual aesthetic for a {platform_label} feed "
                "(lighting, framing, sharpness, composition)?"
            ),
            "criteria": AESTHETIC_CRITERIA,
        },
        "hook_awal": {
            "type": "score",
            "instructions": (
                "How strong is the opening hook in the first 0–3 seconds "
                "(or first glance for a static image)?"
            ),
            "criteria": HOOK_CRITERIA,
        },
        "cta_kejelasan": {
            "type": "score",
            "instructions": (
                "How clear and well-timed is the call-to-action "
                "(on-screen, spoken, or in caption)?"
            ),
            "criteria": CTA_CRITERIA,
        },
        "pacing_edit": {
            "type": "score",
            "instructions": (
                "How good is the pacing/editing rhythm for short-form viewing? "
                "For a still image, score composition dynamism / interest."
            ),
            "criteria": PACING_CRITERIA,
        },
        "kualitas_caption": {
            "type": "score",
            "instructions": (
                "Ignoring policy spam flags, how strong is the caption as creator copy "
                "(clarity, specificity, value)?"
            ),
            "criteria": CAPTION_QUALITY_CRITERIA,
        },
        "perlu_perbaikan_konten": {
            "type": "noul",
            "instructions": (
                "Even if policy-safe, does this content need creative improvements "
                "before publishing (aesthetic, hook, CTA, pacing, or caption)?"
            ),
        },
    }


def build_state(
    *,
    platform: str,
    caption: str,
    hashtags: str,
    media_summary: dict,
) -> dict:
    return {
        "platform": platform,
        "caption": caption or "",
        "hashtags": hashtags or "",
        "media": media_summary,
        "task": (
            "Act as a production-grade content judge for Instagram/TikTok. "
            "First decide policy safety with calibrated probabilities. "
            "Then score creative quality (aesthetic, hook, CTA, pacing, caption) "
            "so an orchestrator can give timestamped improvement advice."
        ),
        "creator_goal": (
            "Help the creator publish safer AND higher-performing content, "
            "with concrete edits (e.g. CTA at second X, crop, lighting, caption rewrite)."
        ),
    }
