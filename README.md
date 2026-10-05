# Prediction Content

Aplikasi fullstack untuk memprediksi apakah konten **Instagram / TikTok** layak tampil, apa yang salah, dan apa yang harus dibetulkan.

- **Classifier utama:** [Cloudflare Clef](https://huggingface.co/Cloudflare/clef) via Workers AI  
- **Fallback:** model lokal (`toxic` text + NSFW image)  
- **Media values:** `ffprobe` (durasi, resolusi, fps, bitrate, codec, …) + `ffmpeg` (ekstrak frame)  
- **Saran perbaikan:** rules (default) · opsional **OpenAI** / **Claude** / Workers AI, dengan **temperature** yang bisa diubah di UI  

Semua tools, cache, dan model diarahkan ke **`D:\devtools`** (bukan C:).

## Struktur

```
prediction-content/
  scripts/setup-env.ps1      # path env → D:\devtools
  scripts/install-devtools.ps1
  backend/                   # FastAPI
  frontend/                  # Next.js + Tailwind
```

## Setup sekali (D:)

Di PowerShell dari folder `prediction-content`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-devtools.ps1
. .\scripts\setup-env.ps1
```

Ini memasang / memakai:

| Tool | Lokasi |
|------|--------|
| uv + Python | `D:\devtools\uv\` |
| Node.js portable | `D:\devtools\node\` |
| ffmpeg / ffprobe | `D:\devtools\ffmpeg\bin\` |
| HF / torch cache | `D:\devtools\hf-cache`, `D:\devtools\torch-cache` |
| npm cache | `D:\devtools\npm-cache` (via `frontend/.npmrc`) |

## Backend

```powershell
. .\scripts\setup-env.ps1
cd backend
copy .env.example .env
# isi CF_ACCOUNT_ID + CF_API_TOKEN jika punya Workers AI
# OPENAI_API_KEY / ANTHROPIC_API_KEY opsional (boleh dikosongkan)
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tanpa kredensial Cloudflare, set `USE_LOCAL_FALLBACK=true` (default) — analisis tetap jalan lewat classifier lokal. Model lokal pertama kali akan terunduh ke `D:\devtools\hf-cache`.

### Env penting (`backend/.env`)

| Key | Keterangan |
|-----|------------|
| `CF_ACCOUNT_ID` / `CF_API_TOKEN` | Workers AI untuk Clef |
| `USE_LOCAL_FALLBACK` | `true` = fallback otomatis jika Clef gagal |
| `OPENAI_API_KEY` | Opsional (boleh diisi dari UI per request) |
| `ANTHROPIC_API_KEY` | Opsional (Claude) |
| `DEFAULT_TEMPERATURE` | Default slider temperature saran |
| `FFMPEG_PATH` / `FFPROBE_PATH` | Default `D:\devtools\ffmpeg\bin\...` |

## Frontend

```powershell
. .\scripts\setup-env.ps1
cd frontend
npm install
npm run dev
```

Buka [http://localhost:3000](http://localhost:3000). API default: `http://localhost:8000` (override dengan `NEXT_PUBLIC_API_BASE`).

## API

### `GET /api/health`

Status ffmpeg, Clef, provider saran.

### `POST /api/analyze` (multipart)

Field:

- `platform`: `instagram` \| `tiktok` \| `both`
- `caption`, `hashtags`
- `file`: gambar/video (opsional)
- `suggestion_provider`: `rules` \| `openai` \| `claude` \| `workers_ai`
- `temperature`: `0`–`2` (Claude di-clamp ke `1`)
- `openai_api_key` / `anthropic_api_key`: opsional per request
- `force_local`: paksa skip Clef

Response memuat `verdict`, `violations`, `suggestions`, dan objek `media` berisi nilai dari ffmpeg/ffprobe.

## Catatan saran LLM

Kalau kamu **tidak punya** OpenAI/Claude API, biarkan provider = **Rules**. Key tidak wajib di `.env`; user lain bisa menempelkan key di UI (hanya untuk request itu, tidak ditulis ke disk).

## Lisensi model

Clef: Apache-2.0 (lihat model card Hugging Face).
