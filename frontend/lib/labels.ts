export const CATEGORY_LABELS: Record<string, string> = {
  none: "Aman",
  nudity_sexual: "Nudity / seksual",
  kekerasan_gore: "Kekerasan / gore",
  ujaran_kebencian: "Ujaran kebencian",
  perundungan: "Perundungan",
  aksi_berbahaya: "Aksi berbahaya",
  narkoba_rokok_alkohol: "Narkoba / rokok / alkohol",
  penipuan_spam: "Penipuan / spam",
  misinformasi: "Misinformasi",
  keselamatan_anak: "Keselamatan anak",
  judi: "Judi",
};

export const SEVERITY_LABELS: Record<string, string> = {
  aman: "Aman",
  ringan: "Ringan",
  berat: "Berat",
  banned: "Harus dihapus",
};

export const ENGINE_LABELS: Record<string, string> = {
  clef: "Clef (Workers AI)",
  drex: "Drex (Nace AI)",
  local: "Classifier lokal",
  local_fallback: "Classifier lokal (fallback)",
};

export const AGENT_LABELS: Record<string, string> = {
  clef: "Clef",
  drex: "Drex",
  local: "Lokal",
};

export const PROVIDER_LABELS: Record<string, string> = {
  rules: "Rules",
  openai: "OpenAI",
  claude: "Claude",
  workers_ai: "Workers AI",
};

export function categoryLabel(id: string) {
  return CATEGORY_LABELS[id] ?? id.replace(/_/g, " ");
}
