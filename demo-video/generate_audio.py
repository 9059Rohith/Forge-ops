"""Generate narration, timing, subtitles and original ambient audio.

Requires: pip install edge-tts imageio-ffmpeg
"""
import asyncio
import json
import math
import re
import struct
import subprocess
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


async def main():
    scenes = json.loads((ROOT / "scenes.json").read_text(encoding="utf-8"))
    public = ROOT / "public"
    public.mkdir(exist_ok=True)
    position = 0
    captions = []
    for index, scene in enumerate(scenes):
        target = public / f"{scene['id']}.mp3"
        if not target.exists():
            await edge_tts.Communicate(scene["voice"], "en-US-GuyNeural", rate="-4%").save(str(target))
        result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(target)], capture_output=True, text=True)
        match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", result.stderr)
        if not match:
            raise RuntimeError(result.stderr)
        seconds = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])
        scene["frames"] = math.ceil((seconds + 1.5) * 24)
        scene["from"] = position
        captions.append(f"{index + 1}\n{stamp(position / 24)} --> {stamp((position + scene['frames']) / 24)}\n{scene['voice']}\n")
        position += scene["frames"]
    (ROOT / "src" / "timing.json").write_text(json.dumps(scenes, indent=2))
    (public / "narration.srt").write_text("\n".join(captions), encoding="utf-8")
    sample_rate = 22050
    with wave.open(str(public / "ambient.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        duration = position / 24
        for second in range(math.ceil(duration)):
            samples = bytearray()
            for i in range(sample_rate):
                t = second + i / sample_rate
                fade = max(0, min(1, t / 3, (duration - t) / 4))
                chord = [(130.81, 164.81, 196), (110, 130.81, 164.81), (87.31, 130.81, 174.61), (98, 146.83, 196)][int(t // 8) % 4]
                value = sum(math.sin(2 * math.pi * frequency * t) for frequency in chord) / 3
                samples.extend(struct.pack('<h', int(value * fade * 750 * (0.8 + 0.2 * math.sin(t * 1.5)))))
            output.writeframes(samples)
    print(f"Generated {len(scenes)} scenes, {position} frames, {duration:.1f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
