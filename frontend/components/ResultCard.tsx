"use client";

import type { AnalyzeResponse } from "@/lib/types";

const verdictStyle: Record<
  AnalyzeResponse["verdict"],
  { label: string; color: string; bg: string }
> = {
  layak: { label: "Layak tampil", color: "#3f9d6a", bg: "rgba(63,157,106,0.15)" },
  perlu_revisi: {
    label: "Perlu revisi",
    color: "#d4a017",
    bg: "rgba(212,160,23,0.15)",
  },
  tidak_layak: {
    label: "Tidak layak",
    color: "#d65a3a",
    bg: "rgba(214,90,58,0.15)",
  },
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
  const probs = Object.entries(result.category_probabilities).sort(
    (a, b) => b[1] - a[1]
  );
  const media = result.media;

  return (
    <section className="animate-rise-delay space-y-8 border-t border-[var(--line)] pt-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">
            Hasil analisis
          </p>
          <h2
            className="mt-2 font-display text-4xl font-semibold tracking-tight"
            style={{ color: v.color }}
          >
            {v.label}
          </h2>
          <p className="mt-2 text-[var(--muted)]">
            Confidence {(result.confidence * 100).toFixed(0)}% · engine{" "}
            <span className="text-[var(--fg)]">{result.engine}</span> · saran via{" "}
            <span className="text-[var(--fg)]">{result.suggestion_provider}</span>
            {result.temperature != null && (
              <>
                {" "}
                · temp <span className="text-[var(--fg)]">{result.temperature}</span>
              </>
            )}
          </p>
        </div>
        <div
          className="rounded-full px-4 py-2 text-sm font-medium"
          style={{ background: v.bg, color: v.color }}
        >
          {result.platform}
        </div>
      </div>

      {media && media.kind !== "none" && (
        <div>
          <h3 className="font-display text-xl">Nilai media (ffmpeg/ffprobe)</h3>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-4">
            <Stat label="Jenis" value={media.kind} />
            <Stat
              label="Durasi"
              value={
                media.duration_sec != null
                  ? `${media.duration_sec.toFixed(2)} s`
                  : "—"
              }
            />
            <Stat
              label="Resolusi"
              value={
                media.width && media.height
                  ? `${media.width}×${media.height}`
                  : "—"
              }
            />
            <Stat label="Aspect" value={media.aspect_ratio ?? "—"} />
            <Stat
              label="FPS"
              value={media.fps != null ? media.fps.toFixed(2) : "—"}
            />
            <Stat label="Bitrate" value={formatBitrate(media.bitrate)} />
            <Stat label="Video codec" value={media.video_codec ?? "—"} />
            <Stat
              label="Audio"
              value={
                media.has_audio
                  ? media.audio_codec ?? "yes"
                  : "tidak ada"
              }
            />
            <Stat label="Ukuran file" value={formatBytes(media.file_size_bytes)} />
            <Stat label="Format" value={media.format_name ?? "—"} />
            <Stat
              label="Frame diekstrak"
              value={String(media.frame_count_extracted)}
            />
            <Stat
              label="Timestamp sampel"
              value={
                media.sample_timestamps_sec.length
                  ? media.sample_timestamps_sec
                      .map((t) => `${t.toFixed(1)}s`)
                      .join(", ")
                  : "—"
              }
            />
          </dl>
          {media.warnings.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-[var(--warn)]">
              {media.warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {probs.length > 0 && (
        <div>
          <h3 className="font-display text-xl">Probabilitas kategori</h3>
          <ul className="mt-4 space-y-3">
            {probs.slice(0, 8).map(([cat, p]) => (
              <li key={cat}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{cat}</span>
                  <span className="text-[var(--muted)]">
                    {(p * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-[var(--accent)] transition-all duration-700"
                    style={{ width: `${Math.min(100, p * 100)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.violations.length > 0 && (
        <div>
          <h3 className="font-display text-xl">Pelanggaran</h3>
          <ul className="mt-4 space-y-4">
            {result.violations.map((vItem, i) => (
              <li
                key={`${vItem.category}-${i}`}
                className="border-l-2 border-[var(--bad)] pl-4"
              >
                <p className="font-medium">
                  {vItem.category}{" "}
                  <span className="text-sm text-[var(--muted)]">
                    ({vItem.severity}, {(vItem.probability * 100).toFixed(0)}%)
                  </span>
                </p>
                {vItem.evidence && (
                  <p className="text-sm text-[var(--muted)]">
                    Evidence: {vItem.evidence}
                  </p>
                )}
                <p className="mt-1 text-sm">{vItem.fix}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.caption_issues.length > 0 && (
        <div>
          <h3 className="font-display text-xl">Isu caption / hashtag</h3>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {result.caption_issues.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h3 className="font-display text-xl">Yang harus dibetulkan</h3>
        <ol className="mt-4 list-decimal space-y-2 pl-5">
          {result.suggestions.map((s) => (
            <li key={s} className="pl-1">
              {s}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[var(--line)] px-3 py-2">
      <dt className="text-xs uppercase tracking-wider text-[var(--muted)]">
        {label}
      </dt>
      <dd className="mt-1 break-all font-medium">{value}</dd>
    </div>
  );
}
