import json
import re
import subprocess
from pathlib import Path


def first_frame_resolution(path: Path, ffmpeg_path: str) -> str | None:
    try:
        result = subprocess.run(
            [
                ffmpeg_path, "-nostdin", "-v", "info", "-noautorotate", "-i", str(path),
                "-map", "0:V:0", "-vf", "showinfo", "-frames:v", "1", "-f", "null", "-",
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    frame = re.search(rb"\[Parsed_showinfo_\d+ [^\]]+\]\s+n:\s*0\s+[^\r\n]*?\bs:(\d+x\d+)\b", result.stderr)
    return frame[1].decode("ascii") if frame else None


def inspect_media(path: Path, ffprobe_path: str) -> dict[str, str | float | None]:
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    payload = json.loads(result.stdout)
    video = next((item for item in payload.get("streams", []) if item.get("codec_type") == "video"), {})
    audio = next((item for item in payload.get("streams", []) if item.get("codec_type") == "audio"), {})
    width, height = video.get("width"), video.get("height")
    return {
        "duration_seconds": float(payload.get("format", {}).get("duration", 0)) or None,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "resolution": f"{width}x{height}" if width and height else None,
    }

