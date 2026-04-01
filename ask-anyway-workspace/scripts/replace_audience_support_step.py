"""
Replace the generic "Audience-lens support step" placeholder in all 1,343
audience variant files with bucket-specific, actionable copy.

Each replacement is written for the lived context of that audience bucket.
Run from the repo root:
    python3 scripts/replace_audience_support_step.py
"""

import os
import sys
from pathlib import Path

SLANTS_DIR = Path("content/topic-guides/audience-slants")

# Map: bucket folder name -> (old placeholder text, new copy)
REPLACEMENTS = {
    "addiction-recovery": (
        "- Audience-lens support step: use one support, person, community, or routine that fits addiction / recovery life.",
        "- Recovery support step: reach out to your sponsor, home group, or one person from your program today — not to explain everything, just to make contact.",
    ),
    "bipoc-racial-trauma": (
        "- Audience-lens support step: use one support, person, community, or routine that fits bipoc / racial trauma life.",
        "- Community support step: connect with one person or space that actually understands what you carry — where you do not have to explain the racial or cultural layer before getting to the real support.",
    ),
    "christian": (
        "- Audience-lens support step: use one support, person, community, or routine that fits christian life.",
        "- Faith support step: take this to prayer or bring it to one trusted person in your faith community — you do not have to carry this privately when you have a whole community and a God you can bring it to.",
    ),
    "chronic-illness-chronic-pain": (
        "- Audience-lens support step: use one support, person, community, or routine that fits chronic illness / chronic pain life.",
        "- Energy-aware support step: plan one support action that accounts for your actual capacity today — not what you could do on a good day — and give yourself permission to count small as real.",
    ),
    "educators": (
        "- Audience-lens support step: use one support, person, community, or routine that fits educators life.",
        "- Boundary support step: use one habit that genuinely separates your teacher identity from your recovery space today — no lesson plans, no parent emails, no student problems — even for 30 minutes.",
    ),
    "faith-beyond-christian": (
        "- Audience-lens support step: use one support, person, community, or routine that fits faith beyond christian life.",
        "- Spiritual support step: use one practice from your tradition that helps you return to your center — meditation, prayer, ceremony, sacred reading, or grounding in your community.",
    ),
    "first-responder": (
        "- Audience-lens support step: use one support, person, community, or routine that fits first responder life.",
        "- Off-shift support step: use one physical off-shift ritual that signals to your nervous system the scene is over — a deliberate action, not just a change of location.",
    ),
    "general-mental-health": (
        "- Audience-lens support step: use one support, person, community, or routine that fits general mental health life.",
        "- Support step: identify one person or resource you trust — a friend, a therapist, a support line — and make one contact today, even a short one.",
    ),
    "grief-loss": (
        "- Audience-lens support step: use one support, person, community, or routine that fits grief / loss life.",
        "- Grief support step: let yourself have the moment without needing it to be done or resolved — then identify one small act of care you can offer yourself before the day ends.",
    ),
    "healthcare-workers": (
        "- Audience-lens support step: use one support, person, community, or routine that fits healthcare workers life.",
        "- Boundary support step: use one hard boundary between patient care and your own recovery space today — even imperfect counts, and your health is not less important than your patients'.",
    ),
    "high-stress-jobs": (
        "- Audience-lens support step: use one support, person, community, or routine that fits high stress jobs life.",
        "- Decompression support step: build one deliberate wind-down window into today — not passive (scrolling) but active (a walk, a call, a physical task that clears your head).",
    ),
    "lgbtq": (
        "- Audience-lens support step: use one support, person, community, or routine that fits lgbtq+ life.",
        "- Affirming support step: connect with one person or space where you do not have to justify or explain yourself before you can be supported — chosen family, a community group, or one person who already gets it.",
    ),
    "military-veteran": (
        "- Audience-lens support step: use one support, person, community, or routine that fits military / veteran life.",
        "- Peer support step: lean on one person from your unit, your post, a vet peer support network, or your VA team today — calling for backup is not a weakness in the field and it is not one now.",
    ),
    "neurodivergent": (
        "- Audience-lens support step: use one support, person, community, or routine that fits neurodivergent life.",
        "- Brain-friendly support step: use a structure that works with how your brain actually operates — a visual reminder, a body double, a voice memo, or a low-barrier check-in that does not require sitting down and writing.",
    ),
    "single-parent": (
        "- Audience-lens support step: use one support, person, community, or routine that fits single parent life.",
        "- Solo support step: identify one 5-to-10 minute window today that belongs only to you — no child need, no task list, no obligation — and protect it the same way you would protect something for your kid.",
    ),
    "social-workers-counselors": (
        "- Audience-lens support step: use one support, person, community, or routine that fits social workers / counselors life.",
        "- Peer support step: use supervision, clinical consultation, or one trusted colleague check-in today — you provide this container for others every day; practice receiving it yourself.",
    ),
    "young-adult-gen-z": (
        "- Audience-lens support step: use one support, person, community, or routine that fits young adults / gen z life.",
        "- Connection support step: text, DM, or voice-note one person you actually trust today — you do not have to be fine, and you do not have to explain the whole backstory before they can show up for you.",
    ),
}


def run():
    if not SLANTS_DIR.exists():
        print(f"ERROR: {SLANTS_DIR} not found. Run from repo root.", file=sys.stderr)
        sys.exit(1)

    total_files = 0
    total_replaced = 0
    not_found = []

    for bucket, (old_text, new_text) in REPLACEMENTS.items():
        bucket_dir = SLANTS_DIR / bucket
        if not bucket_dir.exists():
            print(f"  WARN: bucket dir not found: {bucket_dir}")
            continue

        files = sorted(bucket_dir.glob("*.md"))
        bucket_replaced = 0

        for fpath in files:
            content = fpath.read_text(encoding="utf-8")
            if old_text in content:
                fpath.write_text(content.replace(old_text, new_text), encoding="utf-8")
                bucket_replaced += 1
            else:
                not_found.append(str(fpath))

        total_files += len(files)
        total_replaced += bucket_replaced
        print(f"  {bucket}: {bucket_replaced}/{len(files)} files updated")

    print()
    print(f"Done. {total_replaced}/{total_files} files updated.")

    if not_found:
        print(f"\nWARN: placeholder not found in {len(not_found)} files:")
        for f in not_found[:20]:
            print(f"  {f}")
        if len(not_found) > 20:
            print(f"  ... and {len(not_found) - 20} more")


if __name__ == "__main__":
    run()
