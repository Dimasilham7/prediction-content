"""Media preprocessing with ffmpeg/ffprobe — extracts frames AND measurable values."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import uuid
from fractions import Fraction
from pathlib import Path

from PIL import Image

from app.config import Settings
from app.schemas import MediaProbe

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MAX_IMAGES_FOR_CLEF = 4
MAX_IMAGE_EDGE = 1280


class PreprocessError(ValueError):
    pass


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def tool_ok(path: str) -> bool:
    p = Path(path)
    return p.is_file()


def probe_media(path: Path, settings: Settings) -> dict:
    """Return raw ffprobe JSON for a media file."""
    cmd = [
        settings.ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise PreprocessError(f"ffprobe failed: {result.stderr.strip() or result.stdout}")
    return json.loads(result.stdout)


def _parse_fps(stream: dict) -> float | None:
    for key in ("avg_frame_rate", "r_frame_rate"):
        raw = stream.get(key)
        if not raw or raw in {"0/0", "0"}:
            continue
        try:
            return float(Fraction(raw))
        except (ValueError, ZeroDivisionError):
            continue
    return None


def _aspect_ratio(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    g = math.gcd(width, height)
    return f"{width // g}:{height // g}"


def media_probe_from_ffprobe(path: Path, data: dict, kind: str) -> MediaProbe:
    fmt = data.get("format") or {}
    streams = data.get("streams") or []
    vstream = next((s for s in streams if s.get("codec_type") == "video"), None)
    astream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    width = int(vstream["width"]) if vstream and vstream.get("width") else None
    height = int(vstream["height"]) if vstream and vstream.get("height") else None
    duration = None
    if fmt.get("duration"):
        duration = float(fmt["duration"])
    elif vstream and vstream.get("duration"):
        duration = float(vstream["duration"])

    bitrate = None
    if fmt.get("bit_rate"):
        bitrate = int(fmt["bit_rate"])
    elif vstream and vstream.get("bit_rate"):
        bitrate = int(vstream["bit_rate"])

    warnings: list[str] = []
    if kind == "video" and duration is not None and duration > 180:
        warnings.append("Video lebih dari 3 menit; frame diambil sampel merata.")
    if width and height and (width < 320 or height < 320):
        warnings.append("Resolusi rendah; kualitas deteksi visual bisa menurun.")
    if kind == "video" and astream is None:
        warnings.append("Video tanpa audio track.")

    return MediaProbe(
        kind=kind,  # type: ignore[arg-type]
        duration_sec=duration,
        width=width,
        height=height,
        fps=_parse_fps(vstream) if vstream else None,
        bitrate=bitrate,
        video_codec=(vstream or {}).get("codec_name"),
        audio_codec=(astream or {}).get("codec_name"),
        has_audio=astream is not None,
        file_size_bytes=int(fmt["size"]) if fmt.get("size") else path.stat().st_size,
        format_name=fmt.get("format_name"),
        aspect_ratio=_aspect_ratio(width, height),
        warnings=warnings,
    )


def resize_image(path: Path, out_dir: Path) -> Path:
    out = out_dir / f"{path.stem}_resized.jpg"
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
        im.save(out, format="JPEG", quality=85)
    return out


def extract_video_frames(
    path: Path,
    out_dir: Path,
    settings: Settings,
    *,
    max_frames: int = MAX_IMAGES_FOR_CLEF,
) -> tuple[list[Path], list[float]]:
    """Extract evenly spaced frames; returns paths and timestamps (seconds)."""
    probe = probe_media(path, settings)
    media = media_probe_from_ffprobe(path, probe, "video")
    duration = media.duration_sec or 0.0
    if duration <= 0:
        # fallback: take first few frames at fixed intervals
        timestamps = [0.0, 1.0, 2.0, 3.0][:max_frames]
    else:
        # sample interior points: avoid exact start/end black frames when possible
        if duration < 1.0:
            timestamps = [0.0]
        else:
            step = duration / (max_frames + 1)
            timestamps = [round(step * (i + 1), 3) for i in range(max_frames)]

    frames: list[Path] = []
    kept_ts: list[float] = []
    for i, ts in enumerate(timestamps):
        out = out_dir / f"frame_{i:02d}_{ts:.2f}s.jpg"
        cmd = [
            settings.ffmpeg_path,
            "-y",
            "-ss",
            str(ts),
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
        result = _run(cmd)
        if result.returncode == 0 and out.exists() and out.stat().st_size > 0:
            frames.append(resize_image(out, out_dir))
            kept_ts.append(ts)
    if not frames:
        raise PreprocessError("Gagal mengekstrak frame video dengan ffmpeg.")
    return frames, kept_ts


def save_upload(data: bytes, filename: str, settings: Settings) -> Path:
    if len(data) > settings.max_upload_bytes:
        raise PreprocessError(f"File terlalu besar (maks {settings.max_upload_mb} MB).")
    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXTS | VIDEO_EXTS:
        raise PreprocessError(
            f"Tipe file tidak didukung: {ext or '(tanpa ekstensi)'}. "
            f"Gunakan gambar ({', '.join(sorted(IMAGE_EXTS))}) "
            f"atau video ({', '.join(sorted(VIDEO_EXTS))})."
        )
    work = settings.upload_path / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)
    dest = work / f"source{ext}"
    dest.write_bytes(data)
    return dest


def prepare_media(
    file_bytes: bytes | None,
    filename: str | None,
    settings: Settings,
) -> tuple[list[Path], MediaProbe, Path | None]:
    """
    Validate upload, run ffprobe for measurable values, extract/resize frames.
    Returns (image_paths_for_model, media_probe, work_dir).
    """
    if not file_bytes or not filename:
        return [], MediaProbe(kind="none"), None

    source = save_upload(file_bytes, filename, settings)
    work = source.parent
    ext = source.suffix.lower()

    try:
        if ext in IMAGE_EXTS:
            data = probe_media(source, settings)
            probe = media_probe_from_ffprobe(source, data, "image")
            resized = resize_image(source, work)
            probe.frame_count_extracted = 1
            probe.sample_timestamps_sec = [0.0]
            return [resized], probe, work

        data = probe_media(source, settings)
        probe = media_probe_from_ffprobe(source, data, "video")
        frames, timestamps = extract_video_frames(source, work, settings)
        probe.frame_count_extracted = len(frames)
        probe.sample_timestamps_sec = timestamps
        return frames, probe, work
    except PreprocessError:
        cleanup_work(work)
        raise
    except Exception as exc:  # noqa: BLE001
        cleanup_work(work)
        raise PreprocessError(str(exc)) from exc


def cleanup_work(work: Path | None) -> None:
    if work and work.exists():
        shutil.rmtree(work, ignore_errors=True)


def media_summary_for_state(probe: MediaProbe) -> dict:
    return {
        "kind": probe.kind,
        "duration_sec": probe.duration_sec,
        "width": probe.width,
        "height": probe.height,
        "fps": probe.fps,
        "bitrate": probe.bitrate,
        "video_codec": probe.video_codec,
        "audio_codec": probe.audio_codec,
        "has_audio": probe.has_audio,
        "aspect_ratio": probe.aspect_ratio,
        "format_name": probe.format_name,
        "file_size_bytes": probe.file_size_bytes,
        "sampled_frames": probe.frame_count_extracted,
        "sample_timestamps_sec": probe.sample_timestamps_sec,
        "warnings": probe.warnings,
    }
