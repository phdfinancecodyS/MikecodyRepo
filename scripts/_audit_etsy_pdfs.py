#!/usr/bin/env python3
"""Audit all Etsy PDFs for quality, em dashes, and required elements."""
import glob
from pypdf import PdfReader

pdfs = sorted(glob.glob('output/etsy/**/*.pdf', recursive=True))
print(f"Total PDFs found: {len(pdfs)}\n")

# --- EM DASH / EN DASH AUDIT ---
print("=== EM DASH / EN DASH AUDIT ===")
em_dash = "\u2014"
en_dash = "\u2013"
problems = []

for p in pdfs:
    reader = PdfReader(p)
    text = ""
    for page in reader.pages:
        t = page.extract_text() or ""
        text += t
    em_count = text.count(em_dash)
    en_count = text.count(en_dash)
    name = p.split("/")[-1]
    if em_count > 0 or en_count > 0:
        problems.append((name, em_count, en_count))

if problems:
    print(f"FOUND DASHES IN {len(problems)} files:")
    for name, em, en in problems:
        parts = []
        if em:
            parts.append(f"{em} em")
        if en:
            parts.append(f"{en} en")
        print(f"  {name}: {' + '.join(parts)} dashes")
else:
    print("CLEAN: No em/en dashes found in any PDF. All 79 pass.")

# --- CONTENT ELEMENT AUDIT ---
print("\n=== FULL CONTENT ELEMENT AUDIT ===")
missing_cover = []
missing_988 = []
missing_crisis = []
missing_disclaimer = []
missing_worksheets = []

for p in pdfs:
    reader = PdfReader(p)
    name = p.split("/")[-1]
    n_pages = len(reader.pages)

    # Aggressively strip all spaces for keyword matching (pypdf letter-spacing artifacts)
    def nospace(t): return (t or "").replace(" ", "").lower()
    first_ns = nospace(reader.pages[0].extract_text())
    last_ns = nospace(reader.pages[-1].extract_text())

    # Full text for worksheet check
    full_ns = ""
    for page in reader.pages:
        full_ns += nospace(page.extract_text())

    if "guide" not in first_ns:
        missing_cover.append(name)
    if "988" not in last_ns:
        missing_988.append(name)
    if "crisis" not in last_ns:
        missing_crisis.append(name)
    if "educational" not in last_ns and "substitute" not in last_ns:
        missing_disclaimer.append(name)
    if "worksheet" not in full_ns:
        missing_worksheets.append(name)

print(f"Cover page (has 'Guide'):     {79 - len(missing_cover)}/79 pass", end="")
if missing_cover:
    print(f"  FAIL: {missing_cover}")
else:
    print()

print(f"988 on back page:             {79 - len(missing_988)}/79 pass", end="")
if missing_988:
    print(f"  FAIL: {missing_988}")
else:
    print()

print(f"Crisis resources on back:     {79 - len(missing_crisis)}/79 pass", end="")
if missing_crisis:
    print(f"  FAIL: {missing_crisis}")
else:
    print()

print(f"Disclaimer on back:           {79 - len(missing_disclaimer)}/79 pass", end="")
if missing_disclaimer:
    print(f"  FAIL: {missing_disclaimer}")
else:
    print()

print(f"Worksheets present:           {79 - len(missing_worksheets)}/79 pass", end="")
if missing_worksheets:
    print(f"  FAIL: {missing_worksheets}")
else:
    print()

# --- SUMMARY ---
total_issues = len(missing_cover) + len(missing_988) + len(missing_crisis) + len(missing_disclaimer) + len(missing_worksheets) + len(problems)
print(f"\n{'=' * 40}")
if total_issues == 0:
    print("ALL 79 PDFs PASS AUDIT. Zero issues.")
else:
    print(f"TOTAL ISSUES: {total_issues}")
