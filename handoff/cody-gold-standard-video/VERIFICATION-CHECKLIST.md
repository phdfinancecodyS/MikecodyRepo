# Verification Checklist: Gold Standard Rebuild

## Rebuild integrity

- [ ] Python version is 3.9.x compatible with this bundle.
- [ ] `pip install -r requirements.txt` succeeds.
- [ ] `ELEVENLABS_API_KEY` is set if regenerating VO.
- [ ] `bash scripts/rebuild_gold_standard.sh` runs without error.

## Artifact integrity

- [ ] `shasum -a 256 -c checksums.sha256` passes for current reference files.
- [ ] Rebuilt output file exists at `output/videos/ask-anyway-v3.mp4`.

## Video QA

- [ ] Output is vertical 1080x1920.
- [ ] Slides 1-3 show stick-figure sequence with readable captions.
- [ ] Slides 4-6 show branded card sequence and final CTA logo.
- [ ] Crisis resources are visible on final slide.

## Audio QA

- [ ] Voiceover aligns with slides 1-3.
- [ ] Ambient bed is audible but under VO.
- [ ] No clipping, pops, or silent sections in final export.

## Delivery QA

- [ ] Compare rebuilt output against `output/videos/ask-anyway-gold-standard.mp4`.
- [ ] Document any intentional diffs in a changelog before release.
