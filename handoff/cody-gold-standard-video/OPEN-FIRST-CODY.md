# Open First: Gold Standard Video Context

## Goal

Rebuild and iterate on the exact production pipeline that generated the gold standard campaign video.

## Read this set in order

1. `replication-manifest.json`
2. `DECISION-LOG.md`
3. `VERIFICATION-CHECKLIST.md`
4. `scripts/build_campaign_video_v3.py`

## Pipeline at a glance

1. Generate or refresh ambient music bed.
2. Generate or refresh voiceover clips for slides 1 to 3.
3. Render frame-by-frame video with the v3 builder.
4. Merge VO + ambient using ffmpeg filters baked into the builder.

## Why this version is the gold standard

- Uses frame-by-frame rendering instead of timeline composition.
- Uses hand-animated stick-figure opening with caption overlays.
- Uses stronger branded typography and CTA card.
- Handles audio merge in ffmpeg with explicit gain and delay.

## Inputs used

- `assets/fonts/Montserrat-Black.ttf`
- `assets/fonts/Montserrat-Bold.ttf`
- `assets/fonts/Montserrat-Regular.ttf`
- `output/videos/vo2/manifest.json`
- `output/videos/vo2/slide-01.mp3`
- `output/videos/vo2/slide-02.mp3`
- `output/videos/vo2/slide-03.mp3`
- `output/videos/ambient_pad.wav`

## Scripts used

- `scripts/_gen_ambient.py`
- `scripts/build_voiceover_elevenlabs.py`
- `scripts/build_campaign_video_v3.py`

## Provenance scripts included

- `scripts/build_campaign_video.py`
- `scripts/build_campaign_video_v2.py`
- `scripts/build_voiceover.py`
- `scripts/build_voiceover_v2.py`

## Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Required env var for ElevenLabs VO

```bash
export ELEVENLABS_API_KEY="YOUR_KEY_HERE"
```

## Rebuild commands

```bash
source .venv/bin/activate
python scripts/_gen_ambient.py
python scripts/build_voiceover_elevenlabs.py render jessica
python scripts/build_campaign_video_v3.py
```

## Deterministic integrity check

```bash
shasum -a 256 -c checksums.sha256
```

## If you only want to rerender with existing VO files

```bash
source .venv/bin/activate
python scripts/build_campaign_video_v3.py
```

## Produced files

- New build target: `output/videos/ask-anyway-v3.mp4`
- Included approved reference: `output/videos/ask-anyway-gold-standard.mp4`

## Notes

- Slides 1 to 3 are VO-driven by `vo2/manifest.json` durations.
- Slides 4 to 6 use fixed durations coded in the builder.
- Watermark opacity ramps up through most of the video.
- Final slide has full CTA logo and crisis resources.
- Full dependency snapshot is in `dependency-lock.txt`.
