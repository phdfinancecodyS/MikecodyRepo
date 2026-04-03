# Cody Gold Standard Video Bundle

This bundle contains everything needed to understand and rebuild the Ask Anyway gold standard campaign video.

## Start here

1. Open this folder in VS Code as its own workspace.
2. Read `OPEN-FIRST-CODY.md`.
3. Review `replication-manifest.json` for the exact command sequence and source files.
4. Validate files with `shasum -a 256 -c checksums.sha256`.
3. Run the setup and build commands in that file.

## What is included

- Gold standard renderer: `scripts/build_campaign_video_v3.py`
- Voiceover generator (ElevenLabs): `scripts/build_voiceover_elevenlabs.py`
- Ambient bed generator: `scripts/_gen_ambient.py`
- Lineage scripts: `scripts/build_campaign_video.py`, `scripts/build_campaign_video_v2.py`, `scripts/build_voiceover.py`, `scripts/build_voiceover_v2.py`
- Brand fonts used by renderer: `assets/fonts/`
- Final export and audio inputs: `output/videos/`
- Script template reference: `video-script-templates.md`
- Dependency snapshot: `dependency-lock.txt`
- Integrity checksums: `checksums.sha256`
- Decision rationale: `DECISION-LOG.md`
- QA checklist: `VERIFICATION-CHECKLIST.md`
- Rebuild manifest: `replication-manifest.json`

## Expected output

- `output/videos/ask-anyway-v3.mp4` after rebuild
- Current approved file included: `output/videos/ask-anyway-gold-standard.mp4`
