export type Verdict = "layak" | "perlu_revisi" | "tidak_layak";
export type DecisionAgent = "clef" | "drex" | "local";
export type SuggestionProvider = "rules" | "openai" | "claude" | "workers_ai";

export type MediaProbe = {
  kind: "image" | "video" | "none";
  duration_sec: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  bitrate: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  has_audio: boolean;
  file_size_bytes: number | null;
  format_name: string | null;
  frame_count_extracted: number;
  sample_timestamps_sec: number[];
  aspect_ratio: string | null;
  warnings: string[];
};

export type Violation = {
  category: string;
  probability: number;
  severity: "aman" | "ringan" | "berat" | "banned";
  evidence: string | null;
  fix: string;
};

export type QualityScores = {
  estetika_visual: number | null;
  hook_awal: number | null;
  cta_kejelasan: number | null;
  pacing_edit: number | null;
  kualitas_caption: number | null;
  perlu_perbaikan_konten: number | null;
};

export type ContentTip = {
  area: string;
  title: string;
  detail: string;
  priority: "tinggi" | "sedang" | "rendah";
};

export type TimelineCue = {
  at_sec: number;
  end_sec: number | null;
  action: string;
  detail: string;
  kind: string;
};

export type AnalyzeResponse = {
  verdict: Verdict;
  confidence: number;
  platform: string;
  violations: Violation[];
  caption_issues: string[];
  suggestions: string[];
  content_tips: ContentTip[];
  timeline_cues: TimelineCue[];
  quality: QualityScores | null;
  engine: string;
  suggestion_provider: SuggestionProvider;
  temperature: number | null;
  media: MediaProbe | null;
  category_probabilities: Record<string, number>;
  raw_answers: Record<string, unknown>;
};

export type HealthResponse = {
  status: string;
  clef_configured: boolean;
  drex_configured: boolean;
  local_fallback: boolean;
  ffmpeg_ok: boolean;
  ffprobe_ok: boolean;
  openai_configured: boolean;
  claude_configured: boolean;
  decision_agents: string[];
  suggestion_providers: string[];
  default_decision_agent: string;
};
