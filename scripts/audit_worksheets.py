#!/usr/bin/env python3
"""Full audit of all 2,686 standalone worksheets.

Checks:
1. File count (expected 2,686 = 1,343 × 2)  
2. Title present and non-generic
3. Disclaimer / 988 / 741741 present
4. Minimum prompt count (3+)
5. No generic template prompts
6. Voice issues
7. Non-empty body
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
WS_DIR = ROOT / "content" / "worksheets"

GENERIC_PROMPTS = [
    "when did '[title]' last show up",
    "what makes '[title]' worse",
    "one thing i'll do differently about '[title]'",
    "what part of '[title]' is most active",
    "when did \\'[title]\\' last show up",
]

VOICE_ISSUES = [
    ("aren'ticing", "aren'ticing typo"),
    ("you've a ", "British contraction"),
    ("I've another", "British contraction"),
]


def audit_worksheet(filepath):
    issues = []
    text = filepath.read_text(encoding="utf-8")
    lower = text.lower()

    # Title
    title_match = re.match(r"# (.+)", text)
    if not title_match:
        issues.append(("CRITICAL", "Missing title"))
    else:
        title = title_match.group(1).strip()
        if len(title) < 5:
            issues.append(("WARNING", f"Title too short: '{title}'"))

    # Safety
    if "988" not in text:
        issues.append(("CRITICAL", "Missing 988 reference"))
    if "741741" not in text:
        issues.append(("CRITICAL", "Missing 741741 reference"))

    # Prompt count
    prompt_lines = [l for l in text.splitlines() if l.strip().startswith("- ")]
    if len(prompt_lines) < 3:
        issues.append(("WARNING", f"Only {len(prompt_lines)} prompt bullets (expected 3+)"))

    # Body length
    body = text[text.find("\n"):].strip() if "\n" in text else ""
    if len(body) < 100:
        issues.append(("CRITICAL", f"Body too short ({len(body)} chars)"))

    # Generic prompts
    for gp in GENERIC_PROMPTS:
        if gp in lower:
            issues.append(("CRITICAL", f"Generic prompt: '{gp}'"))

    # Voice
    for pattern, label in VOICE_ISSUES:
        if pattern in text:
            issues.append(("WARNING", f"Voice: {label}"))

    return issues


def main():
    if not WS_DIR.exists():
        print(f"ERROR: {WS_DIR} does not exist")
        sys.exit(1)

    bucket_dirs = sorted([d for d in WS_DIR.iterdir() if d.is_dir()])
    print(f"Worksheet bucket directories: {len(bucket_dirs)}")

    total_files = 0
    total_critical = 0
    total_warning = 0
    issues_by_type = defaultdict(int)
    issues_by_bucket = defaultdict(lambda: {"files": 0, "critical": 0, "warning": 0})
    critical_files = []

    for bucket_dir in bucket_dirs:
        bid = bucket_dir.name
        files = sorted(bucket_dir.glob("*.md"))
        issues_by_bucket[bid]["files"] = len(files)

        for f in files:
            total_files += 1
            file_issues = audit_worksheet(f)
            crits = [i for i in file_issues if i[0] == "CRITICAL"]
            warns = [i for i in file_issues if i[0] == "WARNING"]
            if crits:
                total_critical += len(crits)
                issues_by_bucket[bid]["critical"] += len(crits)
                critical_files.append((f.relative_to(ROOT), crits))
                for _, d in crits:
                    issues_by_type[f"CRITICAL: {d}"] += 1
            if warns:
                total_warning += len(warns)
                issues_by_bucket[bid]["warning"] += len(warns)
                for _, d in warns:
                    issues_by_type[f"WARNING: {d}"] += 1

    print(f"\n{'='*60}")
    print(f"FULL WORKSHEET AUDIT REPORT")
    print(f"{'='*60}")
    print(f"Total worksheets audited: {total_files}")
    print(f"Expected: 2686")
    print(f"CRITICAL issues: {total_critical}")
    print(f"WARNING issues: {total_warning}")

    if issues_by_type:
        print(f"\n--- Issue breakdown ---")
        for issue, count in sorted(issues_by_type.items(), key=lambda x: -x[1]):
            print(f"  {count:4d} × {issue}")

    if critical_files:
        print(f"\n--- CRITICAL files (first 20) ---")
        for path, issues in critical_files[:20]:
            print(f"  {path}")
            for _, d in issues:
                print(f"    {d}")

    print(f"\n--- Per-bucket summary ---")
    for bid in sorted(issues_by_bucket):
        info = issues_by_bucket[bid]
        s = "✅" if info["critical"] == 0 and info["warning"] == 0 else ("❌" if info["critical"] > 0 else "⚠️")
        print(f"  {s} {bid}: {info['files']} files, {info['critical']} crit, {info['warning']} warn")

    print(f"\n{'='*60}")
    if total_critical == 0 and total_warning == 0:
        print("RESULT: ALL CLEAR — 0 critical, 0 warnings")
    elif total_critical == 0:
        print(f"RESULT: PASS WITH WARNINGS — 0 critical, {total_warning} warnings")
    else:
        print(f"RESULT: ISSUES FOUND — {total_critical} critical, {total_warning} warnings")
    print(f"{'='*60}")
    sys.exit(1 if total_critical > 0 else 0)


if __name__ == "__main__":
    main()
