"""Clef / SystemOne question schema for IG & TikTok content policy."""

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


def build_questions(platform: str) -> dict:
    platform_label = {
        "instagram": "Instagram",
        "tiktok": "TikTok",
        "both": "Instagram and TikTok",
    }.get(platform, platform)

    return {
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
            "Decide whether this Instagram/TikTok post is suitable to show on a public feed, "
            "and identify policy issues that creators should fix."
        ),
    }
