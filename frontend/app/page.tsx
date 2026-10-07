"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ResultCard } from "@/components/ResultCard";
import type {
  AnalyzeResponse,
  DecisionAgent,
  HealthResponse,
  SuggestionProvider,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const inputClass =
  "mt-1.5 w-full rounded-md border border-[var(--line)] bg-white/[0.03] px-3 py-2 outline-none transition focus:border-[var(--accent)] focus:bg-white/[0.05]";

type Platform = "instagram" | "tiktok" | "both";

const PLATFORMS: { id: Platform; label: string }[] = [
  { id: "tiktok", label: "TikTok" },
  { id: "instagram", label: "Instagram" },
  { id: "both", label: "Keduanya" },
];

const AGENTS: {
  id: DecisionAgent;
  label: string;
  hint: string;
}[] = [
  {
    id: "clef",
    label: "Clef",
    hint: "Cloudflare Workers AI · vision (gambar/frame)",
  },
  {
    id: "drex",
    label: "Drex",
    hint: "Nace AI SystemOne · open source / hosted",
  },
  {
    id: "local",
    label: "Lokal",
    hint: "Fallback offline · tanpa API decision model",
  },
];

const PROVIDERS: { id: SuggestionProvider; label: string }[] = [
  { id: "rules", label: "Rules (tanpa API)" },
  { id: "openai", label: "OpenAI" },
  { id: "claude", label: "Claude" },
  { id: "workers_ai", label: "Workers AI" },
];

export default function HomePage() {
  const [platform, setPlatform] = useState<Platform>("tiktok");
  const [agent, setAgent] = useState<DecisionAgent>("clef");
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [provider, setProvider] = useState<SuggestionProvider>("rules");
  const [temperature, setTemperature] = useState(0.3);
  const [openaiKey, setOpenaiKey] = useState("");
  const [claudeKey, setClaudeKey] = useState("");
  const [drexKey, setDrexKey] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthFailed, setHealthFailed] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then((d: HealthResponse) => {
        setHealth(d);
        if (
          d.default_decision_agent === "clef" ||
          d.default_decision_agent === "drex" ||
          d.default_decision_agent === "local"
        ) {
          setAgent(d.default_decision_agent);
        }
      })
      .catch(() => setHealthFailed(true));
  }, []);

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    if (provider === "claude" && temperature > 1) setTemperature(1);
  }, [provider, temperature]);

  const canSubmit = !loading && (caption.trim() || hashtags.trim() || file);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    setResult(null);

    const body = new FormData();
    body.set("platform", platform);
    body.set("caption", caption);
    body.set("hashtags", hashtags);
    body.set("decision_agent", agent);
    body.set("suggestion_provider", provider);
    body.set("temperature", String(temperature));
    if (openaiKey.trim()) body.set("openai_api_key", openaiKey.trim());
    if (claudeKey.trim()) body.set("anthropic_api_key", claudeKey.trim());
    if (drexKey.trim()) body.set("drex_api_key", drexKey.trim());
    if (file) body.set("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body });
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const j = await res.json();
          if (j?.detail) detail = String(j.detail);
        } catch {
          /* non-JSON error body */
        }
        throw new Error(detail);
      }
      setResult((await res.json()) as AnalyzeResponse);
      if (window.matchMedia("(max-width: 1023px)").matches) {
        requestAnimationFrame(() =>
          resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
        );
      }
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Backend tidak bisa dihubungi. Pastikan server berjalan di " + API_BASE
          : err instanceof Error
            ? err.message
            : "Gagal menganalisis"
      );
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-5 py-8 sm:px-8 lg:py-12">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[var(--accent)]">
            Prediction Content
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
            Cek kelayakan konten sebelum publish
          </h1>
          <p className="mt-2 max-w-xl text-[var(--muted)]">
            Upload media dan caption Instagram / TikTok. Hasilnya: layak atau tidak, apa yang
            melanggar, dan apa yang perlu dibetulkan.
          </p>
        </div>
        <StatusBar health={health} failed={healthFailed} />
      </header>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <form
          onSubmit={onSubmit}
          className="space-y-6 rounded-xl border border-[var(--line)] bg-white/[0.02] p-5 sm:p-6"
        >
          <div>
            <span className="text-sm text-[var(--muted)]">Platform</span>
            <div className="mt-1.5 grid grid-cols-3 gap-1 rounded-md border border-[var(--line)] p-1">
              {PLATFORMS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPlatform(p.id)}
                  className={`rounded px-3 py-1.5 text-sm transition ${
                    platform === p.id
                      ? "bg-[var(--accent)] font-medium text-[var(--bg0)]"
                      : "text-[var(--muted)] hover:text-[var(--fg)]"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-[var(--muted)]">Decision agent</span>
              {agent === "drex" && (
                <span className="text-xs text-[var(--warn)]">teks + metadata media</span>
              )}
              {agent === "clef" && (
                <span className="text-xs text-[var(--accent)]">vision + teks</span>
              )}
            </div>
            <div className="mt-1.5 grid grid-cols-3 gap-1.5">
              {AGENTS.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => setAgent(a.id)}
                  className={`rounded-md border px-2 py-2 text-left transition ${
                    agent === a.id
                      ? "border-[var(--accent)] bg-[var(--accent)]/15"
                      : "border-[var(--line)] bg-white/[0.03] hover:border-[var(--accent)]/50"
                  }`}
                >
                  <span
                    className={`block text-sm font-medium ${
                      agent === a.id ? "text-[var(--fg)]" : "text-[var(--muted)]"
                    }`}
                  >
                    {a.label}
                  </span>
                  <span className="mt-0.5 block text-[10px] leading-snug text-[var(--muted)]">
                    {a.hint}
                  </span>
                </button>
              ))}
            </div>
            {agent === "drex" && (
              <label className="mt-3 block">
                <span className="text-sm text-[var(--muted)]">
                  Drex API key{" "}
                  <span className="text-[var(--muted)]/70">(opsional jika server lokal)</span>
                </span>
                <input
                  type="password"
                  autoComplete="off"
                  className={inputClass}
                  value={drexKey}
                  onChange={(e) => setDrexKey(e.target.value)}
                  placeholder="Bearer key dari drex.nace.ai — tidak disimpan"
                />
                <span className="mt-1 block text-xs text-[var(--muted)]">
                  Open source:{" "}
                  <a
                    className="text-[var(--accent)] underline"
                    href="https://huggingface.co/nace-ai/drex-dlm"
                    target="_blank"
                    rel="noreferrer"
                  >
                    nace-ai/drex-dlm
                  </a>
                </span>
              </label>
            )}
          </div>

          <div>
            <span className="text-sm text-[var(--muted)]">Media (gambar / video)</span>
            <input
              ref={fileInput}
              type="file"
              accept="image/*,video/*"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file && previewUrl ? (
              <div className="mt-1.5 overflow-hidden rounded-md border border-[var(--line)]">
                {file.type.startsWith("video/") ? (
                  <video src={previewUrl} controls className="max-h-64 w-full bg-black object-contain" />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={previewUrl} alt="Preview" className="max-h-64 w-full bg-black object-contain" />
                )}
                <div className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                  <span className="truncate text-[var(--muted)]">
                    {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB
                  </span>
                  <button
                    type="button"
                    className="shrink-0 text-[var(--bad)] hover:underline"
                    onClick={() => {
                      setFile(null);
                      if (fileInput.current) fileInput.current.value = "";
                    }}
                  >
                    Hapus
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`mt-1.5 flex w-full flex-col items-center justify-center rounded-md border border-dashed px-4 py-8 text-center transition ${
                  dragging
                    ? "border-[var(--accent)] bg-[var(--accent)]/10"
                    : "border-[var(--line)] hover:border-[var(--accent)]/60"
                }`}
              >
                <span className="font-medium">Klik atau seret file ke sini</span>
                <span className="mt-1 text-xs text-[var(--muted)]">
                  JPG, PNG, WEBP, MP4, MOV, WEBM · maks 50 MB · opsional
                </span>
              </button>
            )}
          </div>

          <label className="block">
            <span className="text-sm text-[var(--muted)]">Caption</span>
            <textarea
              className={`${inputClass} min-h-24`}
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Tulis caption postingan..."
            />
          </label>

          <label className="block">
            <span className="text-sm text-[var(--muted)]">Hashtag</span>
            <input
              className={inputClass}
              value={hashtags}
              onChange={(e) => setHashtags(e.target.value)}
              placeholder="#fyp #creator ..."
            />
          </label>

          <div className="rounded-md border border-[var(--line)]">
            <button
              type="button"
              onClick={() => setShowAdvanced((s) => !s)}
              className="flex w-full items-center justify-between px-4 py-3 text-sm"
              aria-expanded={showAdvanced}
            >
              <span>
                Pengaturan saran{" "}
                <span className="text-[var(--muted)]">
                  · {PROVIDERS.find((p) => p.id === provider)?.label ?? provider} · temp{" "}
                  {temperature.toFixed(2)}
                </span>
              </span>
              <span className="text-[var(--muted)]">{showAdvanced ? "−" : "+"}</span>
            </button>

            {showAdvanced && (
              <div className="space-y-4 border-t border-[var(--line)] px-4 py-4">
                <p className="text-xs text-[var(--muted)]">
                  Rules gratis dan tanpa API. OpenAI / Claude dipakai hanya jika kamu isi API key
                  sendiri — key tidak disimpan di server.
                </p>
                <div>
                  <span className="text-sm text-[var(--muted)]">Provider</span>
                  <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                    {PROVIDERS.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setProvider(p.id)}
                        className={`rounded-md border px-3 py-2 text-left text-sm transition ${
                          provider === p.id
                            ? "border-[var(--accent)] bg-[var(--accent)]/15 text-[var(--fg)]"
                            : "border-[var(--line)] bg-white/[0.03] text-[var(--muted)] hover:border-[var(--accent)]/50 hover:text-[var(--fg)]"
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                <label className="block">
                  <span className="flex justify-between text-sm text-[var(--muted)]">
                    <span>Temperature</span>
                    <span className="text-[var(--fg)]">{temperature.toFixed(2)}</span>
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={provider === "claude" ? 1 : 2}
                    step={0.05}
                    value={temperature}
                    disabled={provider === "rules"}
                    onChange={(e) => setTemperature(Number(e.target.value))}
                    className="mt-3 w-full accent-[var(--accent)] disabled:opacity-40"
                  />
                  <span className="mt-1 block text-xs text-[var(--muted)]">
                    {provider === "rules"
                      ? "Tidak berpengaruh untuk Rules."
                      : "Rendah = konsisten, tinggi = kreatif." +
                        (provider === "claude" ? " Claude maks 1.0." : "")}
                  </span>
                </label>

                {provider === "openai" && (
                  <label className="block">
                    <span className="text-sm text-[var(--muted)]">OpenAI API key</span>
                    <input
                      type="password"
                      autoComplete="off"
                      className={inputClass}
                      value={openaiKey}
                      onChange={(e) => setOpenaiKey(e.target.value)}
                      placeholder="sk-..."
                    />
                  </label>
                )}
                {provider === "claude" && (
                  <label className="block">
                    <span className="text-sm text-[var(--muted)]">Anthropic API key</span>
                    <input
                      type="password"
                      autoComplete="off"
                      className={inputClass}
                      value={claudeKey}
                      onChange={(e) => setClaudeKey(e.target.value)}
                      placeholder="sk-ant-..."
                    />
                  </label>
                )}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full rounded-md bg-[var(--accent)] px-6 py-3 font-medium text-[var(--bg0)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Menganalisis…" : "Analisis kelayakan"}
          </button>
          {!canSubmit && !loading && (
            <p className="-mt-3 text-center text-xs text-[var(--muted)]">
              Isi caption, hashtag, atau upload media dulu.
            </p>
          )}
        </form>

        <div ref={resultRef} className="lg:sticky lg:top-8 lg:max-h-[calc(100vh-4rem)] lg:self-start lg:overflow-y-auto">
          <div className="rounded-xl border border-[var(--line)] bg-white/[0.02] p-5 sm:p-6">
            {error && (
              <div className="rounded-md border border-[var(--bad)]/50 bg-[var(--bad)]/10 px-4 py-3 text-sm text-[#ffb4a2]">
                {error}
              </div>
            )}
            {loading && <LoadingState hasMedia={!!file} />}
            {!loading && !error && result && <ResultCard result={result} />}
            {!loading && !error && !result && <EmptyState />}
          </div>
        </div>
      </div>
    </main>
  );
}

function StatusBar({ health, failed }: { health: HealthResponse | null; failed: boolean }) {
  if (failed) {
    return (
      <p className="rounded-full border border-[var(--bad)]/50 px-3 py-1 text-xs text-[#ffb4a2]">
        Backend offline
      </p>
    );
  }
  if (!health) return null;
  const items = [
    { label: "ffmpeg", ok: health.ffmpeg_ok && health.ffprobe_ok },
    { label: "Clef", ok: health.clef_configured },
    { label: "Drex", ok: health.drex_configured },
    { label: "Fallback lokal", ok: health.local_fallback },
  ];
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {items.map((i) => (
        <span
          key={i.label}
          className="flex items-center gap-1.5 rounded-full border border-[var(--line)] px-3 py-1 text-[var(--muted)]"
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: i.ok ? "var(--ok)" : "var(--muted)" }}
          />
          {i.label}
        </span>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex min-h-72 flex-col items-center justify-center text-center">
      <p className="font-display text-xl">Hasil akan muncul di sini</p>
      <p className="mt-2 max-w-xs text-sm text-[var(--muted)]">
        Kamu akan melihat status kelayakan, pelanggaran yang terdeteksi, daftar perbaikan, dan
        nilai media dari ffmpeg.
      </p>
    </div>
  );
}

function LoadingState({ hasMedia }: { hasMedia: boolean }) {
  return (
    <div className="space-y-4" aria-live="polite">
      <p className="text-sm text-[var(--muted)]">
        {hasMedia
          ? "Mengekstrak frame dengan ffmpeg dan menjalankan classifier…"
          : "Menjalankan classifier…"}
      </p>
      {[80, 55, 70, 40].map((w) => (
        <div
          key={w}
          className="h-4 animate-pulse rounded bg-white/10"
          style={{ width: `${w}%` }}
        />
      ))}
      <p className="text-xs text-[var(--muted)]">
        Analisis pertama dengan model lokal bisa lebih lama karena model sedang diunduh.
      </p>
    </div>
  );
}
