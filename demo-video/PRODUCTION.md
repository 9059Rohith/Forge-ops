# ForgeGuard narrated demo

The finished 1920×1080, 24 fps MP4 is at [docs/demo/forgeguard-demo.mp4](../docs/demo/forgeguard-demo.mp4). It includes English narration, readable scene captions, and an original synthesized ambient score. The SRT transcript is beside the video.

This is an explicitly enabled deterministic showcase, captured from the actual application. No API responses are mocked by the capture script. The flight recorder and proof panels are expanded for readability during capture. Reviewer/model-backed production behavior is described separately from the showcase.

## Reproduce

1. Install frontend and backend dependencies using the root README. Start an isolated backend with `DEMO_MODE=true`, then the frontend pointing to that backend. The capture defaults to `http://127.0.0.1:3000`; override with `DEMO_URL`.
2. From the repository root, run `node demo-video/capture.mjs`. This submits a real demo task, waits for VERIFIED, captures the UI, and downloads its receipt.
3. From this folder, run `npm ci`. The exact Remotion version is locked independently of the application.
4. Optional narration regeneration: `pip install edge-tts imageio-ffmpeg` then `python generate_audio.py`. Existing audio is reused. Remove only the scene audio you intend to regenerate after changing `scenes.json`.
5. Run `npm run lint`, then `npx remotion render ForgeGuardDemo ../docs/demo/forgeguard-demo.mp4 --codec=h264 --crf=20 --concurrency=2`.
6. Preview with `npx remotion studio --no-open`.
7. Run `python verify_video.py` to decode the entire export and verify its codecs, duration, and audible, unclipped audio.

The eight scenes and voiceover script are in `scenes.json`; generated frame timing is in `src/timing.json`. Narration uses the Edge TTS `en-US-GuyNeural` voice. The background score is generated locally from sine-wave chords, with no stock music dependency.
