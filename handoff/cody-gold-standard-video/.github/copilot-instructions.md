# Copilot Instructions: Gold Standard Video Bundle

This workspace is a focused handoff for the Ask Anyway gold standard campaign video pipeline.

## Primary objective

Understand and improve the gold-standard video renderer while preserving brand voice, safety language, and build reproducibility.

## Read order

1. `replication-manifest.json`
2. `OPEN-FIRST-CODY.md`
3. `DECISION-LOG.md`
4. `VERIFICATION-CHECKLIST.md`
5. `scripts/build_campaign_video_v3.py`
6. `scripts/build_voiceover_elevenlabs.py`
7. `scripts/_gen_ambient.py`
8. `output/videos/vo2/manifest.json`

## Important constraints

- Keep output vertical 1080x1920.
- Preserve crisis resource lines on CTA slide.
- Keep voiceover timing alignment from `vo2/manifest.json` unless intentionally changed.
- Keep brand color family and Montserrat font usage.
- Do not remove the approved reference file `output/videos/ask-anyway-gold-standard.mp4`.

## When making changes

- Explain visual or timing impact before editing.
- Prefer small, testable edits.
- Rebuild and verify final file plays with audio sync.
- Run checksum validation if any source file in `checksums.sha256` changes.
- Document changed parameters in `CHANGELOG.md` if you add that file.
