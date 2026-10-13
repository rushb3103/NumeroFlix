import json
import subprocess
from pathlib import Path


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

