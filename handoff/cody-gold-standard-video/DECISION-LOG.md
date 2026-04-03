# Decision Log: Gold Standard Video

## Why v3 became gold standard

- v3 switched to frame-by-frame rendering and ffmpeg pipe output for stability.
- v3 improved visual quality with stronger typography treatment, grain, vignette, and staged watermark buildup.
- v3 combined stick-figure animation for slides 1-3 with branded cards for slides 4-6.

## Why voice direction landed here

- Three audition voices were generated and retained in `output/videos/vo_audition/`.
- Production render path defaults to `jessica` in `scripts/build_voiceover_elevenlabs.py`.
- Current timing contract is locked by `output/videos/vo2/manifest.json` and three slide mp3 files.

## Timing strategy

- Slides 1-3: VO duration + per-slide pad in builder.
- Slides 4-6: fixed end-slide durations in builder.
- Final target is pacing tuned for short-form vertical social delivery.

## Audio strategy

- Ambient bed generated locally (`_gen_ambient.py`) for copyright-safe background.
- VO clips delayed and mixed with explicit ffmpeg filter graph in v3 builder.
- Normalization is intentionally disabled in final amix stages to preserve set levels.

## Safety and CTA constraints

- Final CTA slide includes crisis resource lines.
- CTA includes free quiz action prompt and keeps supportive tone.
