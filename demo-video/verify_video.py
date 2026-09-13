"""Decode the export, verify duration/streams, and produce a media QA record."""
import json
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
video = ROOT.parent / "docs" / "demo" / "forgeguard-demo.mp4"
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
result = subprocess.run(
    [ffmpeg, "-hide_banner", "-i", str(video), "-af", "volumedetect", "-f", "null", "-"],
    capture_output=True, text=True, check=True,
)
metadata = result.stderr
assert "1920x1080" in metadata, "Export must be full HD"
assert "Video: h264" in metadata, "Expected H.264 video"
assert "Audio: aac" in metadata, "Expected AAC audio"
duration_match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", metadata)
assert duration_match
duration = int(duration_match[1]) * 3600 + int(duration_match[2]) * 60 + float(duration_match[3])
scenes = json.loads((ROOT / "src" / "timing.json").read_text())
expected = sum(scene["frames"] for scene in scenes) / 24
assert abs(duration - expected) < 0.2, (duration, expected)
peak = float(re.search(r"max_volume: ([-\d.]+) dB", metadata)[1])
mean = float(re.search(r"mean_volume: ([-\d.]+) dB", metadata)[1])
assert -45 < mean < -5, f"Unexpected mean audio volume: {mean}"
assert -30 < peak < 0, f"Audio should be audible and not clip: {peak}"
report = {
    "resolution": "1920x1080", "fps": 24, "video_codec": "h264", "audio_codec": "aac",
    "duration_seconds": duration, "mean_volume_db": mean, "peak_volume_db": peak,
    "bytes": video.stat().st_size, "full_decode": "passed",
}
(video.parent / "media-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
