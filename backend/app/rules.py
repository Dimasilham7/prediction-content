"""Map violation categories to human-readable fixes and caption issues."""

from __future__ import annotations

from typing import Any

from app.schemas import Severity, Violation

CATEGORY_FIXES: dict[str, str] = {
    "none": "Tidak ada perbaikan wajib; konten terlihat aman untuk feed publik.",
    "nudity_sexual": (
        "Crop / blur area sensitif, ganti thumbnail, atau ubah framing agar tidak sugestif."
    ),
    "kekerasan_gore": (
        "Hapus adegan kekerasan/gore, atau tambahkan peringatan jelas dan potong shot grafis."
    ),
    "ujaran_kebencian": (
        "Hapus kata/ujaran yang menyerang identitas atau kelompok; tulis ulang caption netral."
    ),
    "perundungan": (
        "Hapus ejekan/nama orang yang di-bully; fokus ke topik, bukan menyerang individu."
    ),
    "aksi_berbahaya": (
        "Potong adegan berbahaya atau tambahkan teks 'jangan ditiru' dan konteks edukatif."
    ),
    "narkoba_rokok_alkohol": (
        "Jangan mempromosikan narkoba/rokok/alkohol; hapus produk atau framing ajakan pakai."
    ),
    "penipuan_spam": (
        "Hapus CTA spam/scam, janji palsu, dan hashtag bait; tulis caption jujur dan spesifik."
    ),
    "misinformasi": (
        "Koreksi klaim yang tidak terverifikasi; tambahkan sumber atau ubah wording jadi opini."
    ),
    "keselamatan_anak": (
        "Jangan unggah konten yang berisiko bagi anak; ganti media atau batasi audiens."
    ),
    "judi": "Hapus ajakan judi/slot/betting dan hashtag terkait perjudian.",
}

SEVERITY_LABELS = ["aman", "ringan", "berat", "banned"]


def severity_from_score(score_answer: Any) -> Severity:
    if isinstance(score_answer, dict):
        score = score_answer.get("score")
        probs = score_answer.get("probabilities")
        if isinstance(probs, list) and probs:
            idx = max(range(len(probs)), key=lambda i: probs[i])
            return SEVERITY_LABELS[min(idx, 3)]  # type: ignore[return-value]
        if isinstance(score, (int, float)):
            if score < 0.75:
                return "aman"
            if score < 1.5:
                return "ringan"
            if score < 2.5:
                return "berat"
            return "banned"
    return "ringan"


def noul_prob(answer: Any) -> float:
    if isinstance(answer, (int, float)):
        return float(answer)
    if isinstance(answer, dict):
        if "probability" in answer:
            return float(answer["probability"])
        if "probabilities" in answer and isinstance(answer["probabilities"], dict):
            return float(answer["probabilities"].get("true", answer["probabilities"].get("yes", 0)))
    return 0.0


def choice_info(answer: Any) -> tuple[str, float, dict[str, float]]:
    if not isinstance(answer, dict):
        return "none", 0.0, {}
    choice = str(answer.get("choice") or "none")
    conf = float(answer.get("confidence") or 0.0)
    probs = answer.get("probabilities") or {}
    if isinstance(probs, dict):
        probs_f = {str(k): float(v) for k, v in probs.items()}
        if choice in probs_f:
            conf = max(conf, probs_f[choice])
        return choice, conf, probs_f
    return choice, conf, {}


def build_caption_issues(answers: dict[str, Any], hashtags: str) -> list[str]:
    issues: list[str] = []
    if noul_prob(answers.get("caption_clickbait_spam")) >= 0.55:
        issues.append("Caption terdeteksi clickbait/spam atau engagement bait.")
    if noul_prob(answers.get("hashtag_terlarang")) >= 0.55:
        tag_preview = (hashtags or "").strip()[:80]
        if tag_preview:
            issues.append(f"Hashtag berisiko / dibatasi: {tag_preview}")
        else:
            issues.append("Hashtag terdeteksi berisiko atau dibatasi platform.")
    if noul_prob(answers.get("teks_kasar_di_media")) >= 0.55:
        issues.append("Teks di media berisi kata kasar / ujaran yang bermasalah.")
    if noul_prob(answers.get("cocok_di_bawah_18")) <= 0.4:
        issues.append("Konten kurang cocok untuk penonton di bawah 18 tahun.")
    return issues


def build_violations(
    answers: dict[str, Any],
    *,
    sample_timestamps: list[float] | None = None,
) -> list[Violation]:
    category, prob, _ = choice_info(answers.get("kategori_pelanggaran"))
    severity = severity_from_score(answers.get("tingkat_keparahan"))
    evidence = None
    if sample_timestamps:
        mid = sample_timestamps[len(sample_timestamps) // 2]
        m, s = divmod(int(mid), 60)
        evidence = f"frame sampel sekitar {m:02d}:{s:02d}"

    violations: list[Violation] = []
    if category != "none" and prob >= 0.35:
        violations.append(
            Violation(
                category=category,
                probability=round(prob, 4),
                severity=severity if severity != "aman" else "ringan",
                evidence=evidence,
                fix=CATEGORY_FIXES.get(category, "Perbaiki bagian yang melanggar pedoman komunitas."),
            )
        )

    # Secondary flags become soft violations / caption-linked fixes
    if noul_prob(answers.get("caption_clickbait_spam")) >= 0.55 and category != "penipuan_spam":
        violations.append(
            Violation(
                category="penipuan_spam",
                probability=round(noul_prob(answers.get("caption_clickbait_spam")), 4),
                severity="ringan",
                evidence="caption",
                fix=CATEGORY_FIXES["penipuan_spam"],
            )
        )
    return violations


def rules_suggestions(violations: list[Violation], caption_issues: list[str]) -> list[str]:
    suggestions: list[str] = []
    for v in violations:
        suggestions.append(v.fix)
    for issue in caption_issues:
        if "Hashtag" in issue:
            suggestions.append("Ganti/hapus hashtag berisiko; pakai tag relevan dan aman.")
        elif "clickbait" in issue.lower() or "spam" in issue.lower():
            suggestions.append("Tulis ulang caption tanpa janji palsu atau CTA spam.")
        elif "18" in issue:
            suggestions.append("Pertimbangkan age gate / ubah framing agar lebih aman untuk semua usia.")
        else:
            suggestions.append(f"Perbaiki: {issue}")
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            out.append(s)
    if not out:
        out.append("Konten tampak layak. Tetap cek ulang caption, musik, dan thumbnail sebelum publish.")
    return out
