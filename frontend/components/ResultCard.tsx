"use client";

import {
  ENGINE_LABELS,
  PROVIDER_LABELS,
  SEVERITY_LABELS,
  categoryLabel,
} from "@/lib/labels";
import type { AnalyzeResponse } from "@/lib/types";

const verdictStyle: Record<
  AnalyzeResponse["verdict"],
  { label: string; hint: string; color: string; bg: string }
> = {
  layak: {
    label: "Layak tampil",
    hint: "Tidak ada pelanggaran yang terdeteksi.",
    color: "var(--ok)",
    bg: "rgba(63,157,106,0.14)",
  },
  perlu_revisi: {
    label: "Perlu revisi",
    hint: "Masih bisa tayang setelah beberapa bagian diperbaiki.",
    color: "var(--warn)",
    bg: "rgba(212,160,23,0.14)",
  },
  tidak_layak: {
    label: "Tidak layak",
    hint: "Berisiko diturunkan atau dibatasi platform.",
    color: "var(--bad)",
    bg: "rgba(214,90,58,0.14)",
  },
};

const severityColor: Record<string, string> = {
  aman: "var(--ok)",
  ringan: "var(--warn)",
  berat: "var(--bad)",
  banned: "var(--bad)",
};

function formatBytes(n: number | null | undefined) {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 ** 2).toFixed(1)} MB`;
}

function formatBitrate(n: number | null | undefined) {
  if (!n) return "—";
  return `${Math.round(n / 1000)} kbps`;
}

export function ResultCard({ result }: { result: AnalyzeResponse }) {
  const v = verdictStyle[result.verdict];
  const probs = Object.entries(result.category_probabilities)
    .filter(([cat]) => cat !== "none")
    .sort((a, b) => b[1] - a[1]);
  const media = result.media;

  return (
    <div className="animate-rise space-y-7">
      <div
        className="rounded-lg border p-5"
        style={{ borderColor: v.color, background: v.bg }}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
              Hasil analisis
            </p>
            <h2
              className="mt-1 font-display text-3xl font-semibold tracking-tight"
              style={{ color: v.color }}
            >
              {v.label}
            </h2>
            <p className="mt-1 text-sm text-[var(--fg)]/80">{v.hint}</p>
          </div>
          <div className="text-right">
            <p className="font-display text-3xl font-semibold">
              {(result.confidence * 100).toFixed(0)}%
            </p>
            <p className="text-xs text-[var(--muted)]">confidence</p>
          </div>
        </div>
        <p className="mt-4 text-xs text-[var(--muted)]">
          {result.platform} · {ENGINE_LABELS[result.engine] ?? result.engine} ·
          saran via {PROVIDER_LABELS[result.suggestion_provider]}
          {result.temperature != null &&
            result.suggestion_provider !== "rules" &&
            ` · temperature ${result.temperature}`}
        </p>
      </div>

      <Section title="Yang harus dibetulkan">
        <ol className="space-y-2">
          {result.suggestions.map((s, i) => (
            <li key={s} className="flex gap-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-xs font-semibold text-[var(--bg0)]">
                {i + 1}
              </span>
              <span className="leading-relaxed">{s}</span>
            </li>
          ))}
        </ol>
      </Section>

      {result.violations.length > 0 && (
        <Section title="Pelanggaran terdeteksi">
          <ul className="space-y-2">
            {result.violations.map((vItem, i) => (
              <li
                key={`${vItem.category}-${i}`}
                className="flex items-center justify-between gap-3 rounded-md border border-[var(--line)] px-3 py-2"
              >
                <div>
                  <p className="font-medium">{categoryLabel(vItem.category)}</p>
                  {vItem.evidence && (
                    <p className="text-xs text-[var(--muted)]">
                      Bukti: {vItem.evidence}
                    </p>
                  )}
                </div>
                <div className="text-right text-sm">
                  <span
                    className="rounded-full px-2 py-0.5 text-xs font-medium"
                    style={{
                      color: severityColor[vItem.severity],
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    {SEVERITY_LABELS[vItem.severity]}
                  </span>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    {(vItem.probability * 100).toFixed(0)}%
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {result.caption_issues.length > 0 && (
        <Section title="Isu caption / hashtag">
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--fg)]/85">
            {result.caption_issues.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </Section>
      )}

      {probs.length > 0 && (
        <Section title="Risiko per kategori">
          <ul className="space-y-3">
            {probs.slice(0, 6).map(([cat, p]) => (
              <li key={cat}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{categoryLabel(cat)}</span>
                  <span className="text-[var(--muted)]">
                    {(p * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${Math.min(100, p * 100)}%`,
                      background:
                        p >= 0.7 ? "var(--bad)" : p >= 0.4 ? "var(--warn)" : "var(--accent)",
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {media && media.kind !== "none" && (
        <Section title="Nilai media (ffmpeg / ffprobe)">
          <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            <Stat label="Jenis" value={media.kind} />
            <Stat
              label="Durasi"
              value={media.duration_sec != null ? `${media.duration_sec.toFixed(2)} s` : "—"}
            />
            <Stat
              label="Resolusi"
              value={media.width && media.height ? `${media.width}×${media.height}` : "—"}
            />
            <Stat label="Aspect" value={media.aspect_ratio ?? "—"} />
            <Stat label="FPS" value={media.fps != null ? media.fps.toFixed(0) : "—"} />
            <Stat label="Bitrate" value={formatBitrate(media.bitrate)} />
            <Stat label="Video codec" value={media.video_codec ?? "—"} />
            <Stat
              label="Audio"
              value={media.has_audio ? media.audio_codec ?? "ada" : "tidak ada"}
            />
            <Stat label="Ukuran" value={formatBytes(media.file_size_bytes)} />
            <Stat label="Frame dianalisis" value={String(media.frame_count_extracted)} />
            <Stat
              label="Timestamp"
              value={
                media.sample_timestamps_sec.length
                  ? media.sample_timestamps_sec.map((t) => `${t.toFixed(1)}s`).join(", ")
                  : "—"
              }
              wide
            />
          </dl>
          {media.warnings.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-[var(--warn)]">
              {media.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-3 font-display text-lg">{title}</h3>
      {children}
    </section>
  );
}

function Stat({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div
      className={`rounded-md border border-[var(--line)] px-3 py-2 ${wide ? "col-span-2 sm:col-span-3" : ""}`}
    >
      <dt className="text-[10px] uppercase tracking-wider text-[var(--muted)]">{label}</dt>
      <dd className="mt-0.5 break-words font-medium">{value}</dd>
    </div>
  );
}
