#!/usr/bin/env python3
"""Full audit of all 1,343 audience-slant variants.

Checks:
1. Structural completeness (all required sections)
2. Safety disclaimers present
3. Audience-specific content injected
4. No template contamination
5. Worksheet prompt quality
6. Section length minimums
7. Voice / tone issues
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SLANTS_DIR = ROOT / "content" / "topic-guides" / "audience-slants"

REQUIRED_SECTIONS = [
    "What This Helps With",
    "What Is Happening",
    "What To Do Now",
    "What To Say",
    "Common Mistakes To Avoid",
    "24-Hour Action Plan",
]

TEMPLATE_BODY_FRAGMENTS = [
    # Generic body-symptom template
    "Body-based symptoms can feel scary and make decision-making harder",
    # Generic sleep template (only a problem if it's NOT a sleep-topic guide)
    # Generic habit loop template (only a problem if it's NOT a habit-topic guide)
    # Work/identity template (only a problem if it's NOT work-identity guide)
    "Work and identity stress often blends pressure, uncertainty, and loss of control",
]

# These patterns in "What To Say" indicate template leakage
TEMPLATE_SAY_FRAGMENTS = [
    "My system is spiking right now, and I'm using my reset plan",
    "I'm not in danger right now; I'm in a surge and taking control steps",
]

# Template Common Mistakes patterns (should have been eliminated from base guides)
TEMPLATE_MISTAKE_PATTERNS = [
    "Trying to quit a loop with no replacement routine",
    "Bringing five old fights into one conversation",
    "Ignoring early symptoms until they become overwhelming",
    "Doing nothing while waiting to feel perfect",
    "Treating every problem like it must be solved tonight",
    "Waiting for the perfect wording while risk rises",
]

# Generic worksheet prompts (should be gone)
GENERIC_WS_PROMPTS = [
    "When did '[Title]' last show up",
    "When did \\'[Title]\\' last show up",
    "What makes '[Title]' worse",
    "What makes \\'[Title]\\' worse",
    "One thing I'll do differently about '[Title]'",
]

# Voice issues
VOICE_ISSUES = [
    ("aren'ticing", "aren'ticing typo"),
    ("you've a ", "British contraction (you've a)"),
    ("I've another", "British contraction (I've another)"),
]

SECTION_PATTERN = re.compile(r"^## (?P<name>.+?)\n", re.MULTILINE)

BUCKETS_EXPECTED = 17
GUIDES_EXPECTED = 79


def audit_file(filepath):
    issues = []
    text = filepath.read_text(encoding="utf-8")
    rel = filepath.relative_to(ROOT)
    
    # 1. Required sections
    found_sections = [m.group("name").strip() for m in SECTION_PATTERN.finditer(text)]
    for req in REQUIRED_SECTIONS:
        if req not in found_sections:
            issues.append(("CRITICAL", f"Missing section: {req}"))
    
    # Check worksheets by prefix
    has_ws1 = any(s.startswith("Worksheet 1") for s in found_sections)
    has_ws2 = any(s.startswith("Worksheet 2") for s in found_sections)
    if not has_ws1:
        issues.append(("CRITICAL", "Missing Worksheet 1"))
    if not has_ws2:
        issues.append(("CRITICAL", "Missing Worksheet 2"))
    
    # 2. Safety disclaimers
    if "988" not in text:
        issues.append(("CRITICAL", "Missing 988 crisis reference"))
    if "741741" not in text:
        issues.append(("CRITICAL", "Missing Crisis Text Line 741741"))
    if "Disclaimer" not in text:
        issues.append(("CRITICAL", "Missing disclaimer block"))
    
    # 3. Audience content injected
    if "Audience Bucket:" not in text:
        issues.append(("CRITICAL", "Missing Audience Bucket metadata"))
    
    # 4. Template contamination
    for frag in TEMPLATE_BODY_FRAGMENTS:
        # work/identity template is fine in split-23
        if "split-23" in filepath.name and "Work and identity" in frag:
            continue
        if frag in text:
            issues.append(("CRITICAL", f"Template body fragment: '{frag[:60]}...'"))
    
    for frag in TEMPLATE_SAY_FRAGMENTS:
        if frag in text:
            issues.append(("WARNING", f"Template 'What To Say' fragment: '{frag[:50]}...'"))
    
    for pat in TEMPLATE_MISTAKE_PATTERNS:
        if pat in text:
            issues.append(("WARNING", f"Template Common Mistake: '{pat[:50]}...'"))
    
    # 5. Generic worksheet prompts
    for gp in GENERIC_WS_PROMPTS:
        if gp.lower() in text.lower():
            issues.append(("CRITICAL", f"Generic worksheet prompt: '{gp}'"))
    
    # 6. Section length checks (extract each section body)
    sections = {}
    matches = list(SECTION_PATTERN.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[m.group("name").strip()] = body
    
    for sec_name in REQUIRED_SECTIONS:
        body = sections.get(sec_name, "")
        if len(body) < 50:
            issues.append(("WARNING", f"Section '{sec_name}' suspiciously short ({len(body)} chars)"))
    
    # Check worksheet bodies
    for sec_name, body in sections.items():
        if sec_name.startswith("Worksheet") and len(body) < 80:
            issues.append(("WARNING", f"Section '{sec_name}' suspiciously short ({len(body)} chars)"))
    
    # Common Mistakes count
    mistakes_body = sections.get("Common Mistakes To Avoid", "")
    mistake_count = len([l for l in mistakes_body.splitlines() if l.strip().startswith("- ")])
    if mistake_count < 4:
        issues.append(("WARNING", f"Common Mistakes only has {mistake_count} items (expected 4+)"))
    
    # What To Do Now count (should be 4+ with audience step prepended)
    do_body = sections.get("What To Do Now", "")
    do_count = len(re.findall(r"^\d+\.", do_body, re.MULTILINE))
    if do_count < 4:
        issues.append(("WARNING", f"What To Do Now only has {do_count} items (expected 4+)"))
    
    # What To Say count (should be 5+ with audience says prepended)
    say_body = sections.get("What To Say", "")
    say_count = len([l for l in say_body.splitlines() if l.strip().startswith("- ")])
    if say_count < 4:
        issues.append(("WARNING", f"What To Say only has {say_count} items (expected 4+)"))
    
    # 7. Voice issues
    for pattern, label in VOICE_ISSUES:
        if pattern in text:
            issues.append(("WARNING", f"Voice issue: {label}"))
    
    # Check audience-lens support step in action plan
    action_body = sections.get("24-Hour Action Plan", "")
    if "Audience-lens support step" not in action_body:
        issues.append(("WARNING", "Missing 'Audience-lens support step' in 24-Hour Action Plan"))
    
    return issues


def main():
    if not SLANTS_DIR.exists():
        print(f"ERROR: {SLANTS_DIR} does not exist")
        sys.exit(1)
    
    bucket_dirs = sorted([d for d in SLANTS_DIR.iterdir() if d.is_dir()])
    print(f"Audience bucket directories found: {len(bucket_dirs)}")
    
    if len(bucket_dirs) != BUCKETS_EXPECTED:
        print(f"  WARNING: Expected {BUCKETS_EXPECTED}, found {len(bucket_dirs)}")
    
    total_files = 0
    total_critical = 0
    total_warning = 0
    issues_by_type = defaultdict(int)
    issues_by_bucket = defaultdict(lambda: {"files": 0, "critical": 0, "warning": 0})
    critical_files = []
    warning_files = []
    
    for bucket_dir in bucket_dirs:
        bucket_id = bucket_dir.name
        files = sorted(bucket_dir.glob("*.md"))
        issues_by_bucket[bucket_id]["files"] = len(files)
        
        if len(files) != GUIDES_EXPECTED:
            print(f"  WARNING: Bucket '{bucket_id}' has {len(files)} files, expected {GUIDES_EXPECTED}")
        
        for f in files:
            total_files += 1
            file_issues = audit_file(f)
            
            crits = [i for i in file_issues if i[0] == "CRITICAL"]
            warns = [i for i in file_issues if i[0] == "WARNING"]
            
            if crits:
                total_critical += len(crits)
                issues_by_bucket[bucket_id]["critical"] += len(crits)
                critical_files.append((f.relative_to(ROOT), crits))
                for _, desc in crits:
                    issues_by_type[f"CRITICAL: {desc}"] += 1
            
            if warns:
                total_warning += len(warns)
                issues_by_bucket[bucket_id]["warning"] += len(warns)
                warning_files.append((f.relative_to(ROOT), warns))
                for _, desc in warns:
                    issues_by_type[f"WARNING: {desc}"] += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"FULL AUDIENCE VARIANT AUDIT REPORT")
    print(f"{'='*60}")
    print(f"Total files audited: {total_files}")
    print(f"Expected: {BUCKETS_EXPECTED * GUIDES_EXPECTED} ({BUCKETS_EXPECTED} buckets × {GUIDES_EXPECTED} guides)")
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
            for _, desc in issues:
                print(f"    CRITICAL: {desc}")
    
    if warning_files and not critical_files:
        print(f"\n--- WARNING files (first 20) ---")
        for path, issues in warning_files[:20]:
            print(f"  {path}")
            for _, desc in issues:
                print(f"    WARNING: {desc}")
    elif warning_files:
        # Show unique warning types only
        print(f"\n--- WARNING samples (one per type) ---")
        seen = set()
        for path, issues in warning_files:
            for _, desc in issues:
                if desc not in seen:
                    seen.add(desc)
                    print(f"  {desc}")
                    print(f"    Example: {path}")
    
    print(f"\n--- Per-bucket summary ---")
    for bid in sorted(issues_by_bucket):
        info = issues_by_bucket[bid]
        status = "✅" if info["critical"] == 0 and info["warning"] == 0 else ("❌" if info["critical"] > 0 else "⚠️")
        print(f"  {status} {bid}: {info['files']} files, {info['critical']} critical, {info['warning']} warning")
    
    print(f"\n{'='*60}")
    if total_critical == 0 and total_warning == 0:
        print("RESULT: ALL CLEAR  - 0 critical, 0 warnings")
    elif total_critical == 0:
        print(f"RESULT: PASS WITH WARNINGS  - 0 critical, {total_warning} warnings")
    else:
        print(f"RESULT: ISSUES FOUND  - {total_critical} critical, {total_warning} warnings")
    print(f"{'='*60}")
    
    sys.exit(1 if total_critical > 0 else 0)


if __name__ == "__main__":
    main()
