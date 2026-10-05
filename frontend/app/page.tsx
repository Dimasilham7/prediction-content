"use client";

import { useEffect, useMemo, useState } from "react";
import { ResultCard } from "@/components/ResultCard";
import type { AnalyzeResponse, HealthResponse, SuggestionProvider } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function HomePage() {
  const [platform, setPlatform] = useState<"instagram" | "tiktok" | "both">(
    "tiktok"
  );
  const [caption, setCaption] = useState("");
  const [hashtags, setHashtags] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [provider, setProvider] = useState<SuggestionProvider>("rules");
  const [temperature, setTemperature] = useState(0.3);
  const [openaiKey, setOpenaiKey] = useState("");
  const [claudeKey, setClaudeKey] = useState("");
  const [forceLocal, setForceLocal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((r) => r.json())
      .then((d: HealthResponse) => setHealth(d))
      .catch(() => setHealth(null));
  }, []);

  const previewUrl = useMemo(
    () => (file ? URL.createObjectURL(file) : null),
    [file]
  );

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const body = new FormData();
    body.set("platform", platform);
    body.set("caption", caption);
    body.set("hashtags", hashtags);
    body.set("suggestion_provider", provider);
    body.set("temperature", String(temperature));
    body.set("force_local", String(forceLocal));
    if (openaiKey.trim()) body.set("openai_api_key", openaiKey.trim());
    if (claudeKey.trim()) body.set("anthropic_api_key", claudeKey.trim());
    if (file) body.set("file", file);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      const data = (await res.json()) as AnalyzeResponse;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menganalisis");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-10 sm:px-8 sm:py-14">
      <header className="animate-rise mb-12">
        <p className="text-sm uppercase tracking-[0.28em] text-[var(--accent)]">
          Prediction Content
        </p>
        <h1 className="mt-3 max-w-3xl font-display text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Cek kelayakan konten Instagram & TikTok sebelum publish
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-[var(--muted)]">
          Upload media + caption. Sistem memakai Clef (Workers AI) atau classifier
          lokal, ffmpeg untuk nilai media, lalu menyarankan perbaikan — opsional
          lewat OpenAI / Claude dengan temperature yang bisa kamu atur.
        </p>
        {health && (
          <p className="mt-4 text-sm text-[var(--muted)]">
            ffmpeg {health.ffmpeg_ok ? "✓" : "✗"} · ffprobe{" "}
            {health.ffprobe_ok ? "✓" : "✗"} · Clef{" "}
            {health.clef_configured ? "siap" : "belum dikonfigurasi"} · fallback
            lokal {health.local_fallback ? "on" : "off"}
          </p>
        )}
      </header>

      <form onSubmit={onSubmit} className="animate-rise space-y-8">
        <div className="grid gap-6 md:grid-cols-2">
          <label className="block">
            <span className="text-sm text-[var(--muted)]">Platform</span>
            <select
              className="mt-2 w-full border border-[var(--line)] bg-transparent px-3 py-2 outline-none focus:border-[var(--accent)]"
              value={platform}
              onChange={(e) =>
                setPlatform(e.target.value as "instagram" | "tiktok" | "both")
              }
            >
              <option value="tiktok">TikTok</option>
              <option value="instagram">Instagram</option>
              <option value="both">Keduanya</option>
            </select>
          </label>

          <label className="block">
            <span className="text-sm text-[var(--muted)]">Media (gambar/video)</span>
            <input
              type="file"
              accept="image/*,video/*"
              className="mt-2 block w-full text-sm file:mr-3 file:border-0 file:bg-[var(--accent)] file:px-3 file:py-2 file:text-[var(--bg0)]"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        {previewUrl && file && (
          <div className="overflow-hidden border border-[var(--line)]">
            {file.type.startsWith("video/") ? (
              <video src={previewUrl} controls className="max-h-80 w-full object-contain" />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={previewUrl}
                alt="Preview"
                className="max-h-80 w-full object-contain"
              />
            )}
          </div>
        )}

        <label className="block">
          <span className="text-sm text-[var(--muted)]">Caption</span>
          <textarea
            className="mt-2 min-h-28 w-full border border-[var(--line)] bg-transparent px-3 py-2 outline-none focus:border-[var(--accent)]"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Tulis caption postingan..."
          />
        </label>

        <label className="block">
          <span className="text-sm text-[var(--muted)]">Hashtags</span>
          <input
            className="mt-2 w-full border border-[var(--line)] bg-transparent px-3 py-2 outline-none focus:border-[var(--accent)]"
            value={hashtags}
            onChange={(e) => setHashtags(e.target.value)}
            placeholder="#fyp #creator ..."
          />
        </label>

        <fieldset className="space-y-4 border border-[var(--line)] p-4">
          <legend className="px-2 text-sm uppercase tracking-wider text-[var(--muted)]">
            Saran perbaikan (opsional LLM)
          </legend>
          <p className="text-sm text-[var(--muted)]">
            Default memakai rules (gratis, tanpa API). OpenAI / Claude hanya dipakai
            jika kamu isi API key sendiri — tidak disimpan di server.
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-sm text-[var(--muted)]">Provider saran</span>
              <select
                className="mt-2 w-full border border-[var(--line)] bg-transparent px-3 py-2 outline-none focus:border-[var(--accent)]"
                value={provider}
                onChange={(e) =>
                  setProvider(e.target.value as SuggestionProvider)
                }
              >
                <option value="rules">Rules (tanpa API)</option>
                <option value="openai">OpenAI</option>
                <option value="claude">Claude (Anthropic)</option>
                <option value="workers_ai">Workers AI (Cloudflare)</option>
              </select>
            </label>

            <label className="block">
              <span className="text-sm text-[var(--muted)]">
                Temperature: {temperature.toFixed(2)}
              </span>
              <input
                type="range"
                min={0}
                max={provider === "claude" ? 1 : 2}
                step={0.05}
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
                className="mt-3 w-full accent-[var(--accent)]"
              />
              <span className="mt-1 block text-xs text-[var(--muted)]">
                Lebih rendah = saran lebih konsisten; lebih tinggi = lebih kreatif.
                Claude max 1.0.
              </span>
            </label>
          </div>

          {provider === "openai" && (
            <label className="block">
              <span className="text-sm text-[var(--muted)]">OpenAI API key</span>
              <input
                type="password"
                autoComplete="off"
                className="mt-2 w-full border border-[var(--line)] bg-transparent px-3 py-2 outline-none focus:border-[var(--accent)]"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-... (opsional, hanya untuk sesi ini)"
              />
            </label>
          )}

          {provider === "claude" && (
            <label className="block">
              <span className="text-sm text-[var(--muted)]">Anthropic API key</span>
              <input
                type="password"
                autoComplete="off"
                className="mt-2 w-full border border-[var(--line)] bg-transparent px-3 py-2 outline-none focus:border-[var(--accent)]"
                value={claudeKey}
                onChange={(e) => setClaudeKey(e.target.value)}
                placeholder="sk-ant-... (opsional, hanya untuk sesi ini)"
              />
            </label>
          )}

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={forceLocal}
              onChange={(e) => setForceLocal(e.target.checked)}
            />
            Paksa classifier lokal (skip Clef)
          </label>
        </fieldset>

        <button
          type="submit"
          disabled={loading}
          className="bg-[var(--accent)] px-6 py-3 font-medium text-[var(--bg0)] transition hover:brightness-110 disabled:opacity-50"
        >
          {loading ? "Menganalisis…" : "Analisis kelayakan"}
        </button>
      </form>

      {error && (
        <p className="mt-8 border border-[var(--bad)]/40 bg-[var(--bad)]/10 px-4 py-3 text-sm text-[#ffb4a2]">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-12">
          <ResultCard result={result} />
        </div>
      )}
    </main>
  );
}
