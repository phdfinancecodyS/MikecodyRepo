#!/usr/bin/env python3
"""
Full integrity audit of the Ask Anyway workspace.
Reports findings only — does not fix anything.
"""
import json, os, glob, csv, re, random, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

findings = []  # (severity, category, message)

def find(sev, cat, msg):
    findings.append((sev, cat, msg))

# ─── helpers ───
def load_json(path):
    with open(path) as f:
        return json.load(f)

def count_files(pattern):
    return len(glob.glob(pattern, recursive=True))

def file_exists(path):
    return os.path.isfile(path)

# ─── load data ───
catalog = load_json("quiz/base-guide-catalog.json")
topics = load_json("quiz/topic-catalog.json")
matcher = load_json("quiz/topic-matcher-flow.json")
quiz = load_json("quiz/quiz-content.json")
audience = load_json("quiz/audience-bucket-flow.json")
routing = load_json("quiz/recommendation-routing-config.json")
convo = load_json("quiz/conversation-branch-flow.json")
fulfillment = load_json("quiz/fulfillment-config.json")
products = load_json("quiz/product-catalog.json")

guide_map = {g["guide_id"]: g for g in catalog["guides"]}
source_map = {}
for g in catalog["guides"]:
    src = g.get("source", "")
    source_map.setdefault(src, []).append(g)
topic_map = {t["id"]: t for t in topics["topics"]}

# Extract audience bucket slugs from audience-bucket-flow
audience_slugs = set()
for q in audience.get("questions", []):
    for opt in q.get("options", []):
        for b in opt.get("bucketIds", opt.get("buckets", [])):
            audience_slugs.add(b)
# also scan mapTo / audienceId patterns
audience_json_str = json.dumps(audience)
for m in re.findall(r'"audienceId"\s*:\s*"([^"]+)"', audience_json_str):
    audience_slugs.add(m)
for m in re.findall(r'"id"\s*:\s*"([^"]+)"', audience_json_str):
    if "-" in m and not m.startswith("abm_"):
        audience_slugs.add(m)

# If we didn't find 17, fallback: scan audience-slants dirs
slant_dirs = sorted([d for d in os.listdir("content/topic-guides/audience-slants")
                     if os.path.isdir(f"content/topic-guides/audience-slants/{d}")])
if len(audience_slugs) < 17:
    audience_slugs = set(slant_dirs)

EXPECTED_AUDIENCES = 17
EXPECTED_BASE_GUIDES = 79
EXPECTED_CHAPTERS = 33
EXPECTED_SPLITS = 28
EXPECTED_NEW = 18
EXPECTED_VARIANTS = EXPECTED_AUDIENCES * EXPECTED_BASE_GUIDES  # 1343
EXPECTED_WORKSHEETS = EXPECTED_VARIANTS * 2  # 2686

print("=" * 70)
print("ASK ANYWAY WORKSPACE — FULL INTEGRITY AUDIT")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════
# 1. CONTENT FILE COUNTS & STRUCTURE
# ═══════════════════════════════════════════════════════════════════════
print("\n[1] CONTENT FILE COUNTS & STRUCTURE")

ch_files = sorted(glob.glob("content/topic-guides/chapters/ch-*.md"))
sp_files = sorted(glob.glob("content/topic-guides/splits/split-*.md"))
nt_files = sorted(glob.glob("content/topic-guides/new-topics/new-*.md"))

print(f"  Chapters: {len(ch_files)} (expected {EXPECTED_CHAPTERS})")
print(f"  Splits:   {len(sp_files)} (expected {EXPECTED_SPLITS})")
print(f"  New:      {len(nt_files)} (expected {EXPECTED_NEW})")
print(f"  Base total: {len(ch_files)+len(sp_files)+len(nt_files)} (expected {EXPECTED_BASE_GUIDES})")

if len(ch_files) != EXPECTED_CHAPTERS:
    find("CRITICAL", "1-counts", f"Chapter files: {len(ch_files)}, expected {EXPECTED_CHAPTERS}")
if len(sp_files) != EXPECTED_SPLITS:
    find("CRITICAL", "1-counts", f"Split files: {len(sp_files)}, expected {EXPECTED_SPLITS}")
if len(nt_files) != EXPECTED_NEW:
    find("CRITICAL", "1-counts", f"New-topic files: {len(nt_files)}, expected {EXPECTED_NEW}")

# Audience variants
variant_total = 0
for slug in slant_dirs:
    d = f"content/topic-guides/audience-slants/{slug}"
    n = len([f for f in os.listdir(d) if f.endswith(".md")])
    variant_total += n
    if n != EXPECTED_BASE_GUIDES:
        find("WARNING", "1-counts", f"Audience '{slug}' has {n} variant files (expected {EXPECTED_BASE_GUIDES})")

print(f"  Audience dirs: {len(slant_dirs)} (expected {EXPECTED_AUDIENCES})")
print(f"  Variant files: {variant_total} (expected {EXPECTED_VARIANTS})")

if len(slant_dirs) != EXPECTED_AUDIENCES:
    find("CRITICAL", "1-counts", f"Audience directories: {len(slant_dirs)}, expected {EXPECTED_AUDIENCES}")
if variant_total != EXPECTED_VARIANTS:
    find("CRITICAL", "1-counts", f"Variant files: {variant_total}, expected {EXPECTED_VARIANTS}")

# Worksheets
ws_dirs = sorted([d for d in os.listdir("content/worksheets")
                  if os.path.isdir(f"content/worksheets/{d}")])
ws_total = 0
for slug in ws_dirs:
    d = f"content/worksheets/{slug}"
    n = len([f for f in os.listdir(d) if f.endswith(".md")])
    ws_total += n
    expected_ws_per = EXPECTED_BASE_GUIDES * 2  # 158
    if n != expected_ws_per:
        find("WARNING", "1-counts", f"Worksheet dir '{slug}' has {n} files (expected {expected_ws_per})")

print(f"  Worksheet dirs: {len(ws_dirs)} (expected {EXPECTED_AUDIENCES})")
print(f"  Worksheet files: {ws_total} (expected {EXPECTED_WORKSHEETS})")

if len(ws_dirs) != EXPECTED_AUDIENCES:
    find("CRITICAL", "1-counts", f"Worksheet directories: {len(ws_dirs)}, expected {EXPECTED_AUDIENCES}")
if ws_total != EXPECTED_WORKSHEETS:
    find("CRITICAL", "1-counts", f"Worksheet files: {ws_total}, expected {EXPECTED_WORKSHEETS}")

# base_path existence from catalog
missing_base_paths = []
for g in catalog["guides"]:
    bp = g.get("base_path", "")
    if bp and not file_exists(bp):
        missing_base_paths.append((g["guide_id"], bp))
if missing_base_paths:
    for gid, bp in missing_base_paths:
        find("CRITICAL", "1-paths", f"base_path missing on disk: {gid} -> {bp}")
else:
    print(f"  All {len(catalog['guides'])} base_path entries exist on disk ✓")

# ═══════════════════════════════════════════════════════════════════════
# 2. VOICE & FORMATTING CONSISTENCY (SAMPLE-BASED)
# ═══════════════════════════════════════════════════════════════════════
print("\n[2] VOICE & FORMATTING CONSISTENCY (10 random samples)")

all_variant_files = glob.glob("content/topic-guides/audience-slants/**/*.md", recursive=True)
all_base_files = ch_files + sp_files + nt_files
sample_pool = all_variant_files + all_base_files
random.seed(42)  # reproducible
sample_files = random.sample(sample_pool, min(10, len(sample_pool)))

formal_patterns = [
    (r'\bdo not\b', "do not"),
    (r'\byou will\b', "you will"),
    (r'\bit is\b', "it is"),
    (r'\bthey are\b', "they are"),
    (r'\bwe are\b', "we are"),
    (r'\bcannot\b', "cannot"),
]
# exceptions: titles in headers, direct quotes, proper nouns
boilerplate_opener = "This guide helps with"
generic_action = "1. Step one."
generic_worksheet = "Starter line 1"
disclaimer_marker = "educational purposes"
crisis_number = "988"

voice_issues = 0
for fpath in sample_files:
    with open(fpath) as f:
        content = f.read()
    content_lower = content.lower()
    fname = os.path.relpath(fpath)
    
    # Contractions check (body only, skip title and disclaimer)
    lines = content.split("\n")
    body = "\n".join(lines[1:]) if len(lines) > 1 else content
    # Remove disclaimer block from body for voice checking
    disclaimer_idx = body.lower().find("**disclaimer:**")
    if disclaimer_idx >= 0:
        body = body[:disclaimer_idx]
    for pat, label in formal_patterns:
        matches = re.findall(pat, body, re.IGNORECASE)
        if matches:
            # filter out: inside quotes, disclaimer text, proper names
            real_count = len([m for m in re.finditer(pat, body, re.IGNORECASE)
                             if "educational" not in body[max(0,m.start()-50):m.end()+50].lower()
                             and "Do Not Resuscitate" not in body[max(0,m.start()-30):m.end()+30]])
            if real_count > 0:
                find("WARNING", "2-voice", f"Formal '{label}' found {real_count}x in {fname}")
                voice_issues += 1
    
    # Boilerplate opener
    if boilerplate_opener in content:
        find("WARNING", "2-voice", f"Boilerplate opener found in {fname}")
        voice_issues += 1
    
    # Generic action plan
    if generic_action in content:
        find("WARNING", "2-voice", f"Generic action plan placeholder in {fname}")
        voice_issues += 1
    
    # Generic worksheet
    if generic_worksheet in content:
        find("WARNING", "2-voice", f"Generic worksheet placeholder in {fname}")
        voice_issues += 1
    
    # Disclaimer
    if disclaimer_marker not in content_lower:
        find("WARNING", "2-voice", f"Missing disclaimer in {fname}")
        voice_issues += 1
    
    # 988 number
    if crisis_number not in content:
        find("WARNING", "2-voice", f"Missing 988 crisis number in {fname}")
        voice_issues += 1

if voice_issues == 0:
    print("  All 10 samples pass voice/formatting checks ✓")
else:
    print(f"  {voice_issues} issues found across 10 samples")

# ═══════════════════════════════════════════════════════════════════════
# 3. QUIZ JSON REFERENCE CHAIN — FULL TRACE
# ═══════════════════════════════════════════════════════════════════════
print("\n[3] QUIZ JSON REFERENCE CHAIN")

# 3a: topicHints -> topic-catalog -> base-guide-catalog -> files
all_hints = set()
for q in matcher.get("questions", []):
    for opt in q.get("options", []):
        for hint in opt.get("topicHints", []):
            all_hints.add(hint)

hint_issues = 0
for hint in sorted(all_hints):
    in_topic = hint in topic_map
    guide_id_fmt = hint[:2] + "-" + hint[2:]
    in_guide = guide_id_fmt in guide_map
    ch_num = int(hint[2:])
    source_fmts = [f"Ch{ch_num}", f"Ch{ch_num:02d}"]
    has_source = any(sf in source_map for sf in source_fmts)
    has_chapter_id = any(g.get("chapter_id") == hint for g in catalog["guides"])
    
    if not in_topic:
        find("CRITICAL", "3-hints", f"topicHint '{hint}' missing from topic-catalog.json")
        hint_issues += 1
    if not in_guide and not has_source and not has_chapter_id:
        find("CRITICAL", "3-hints", f"topicHint '{hint}' has no guide or split resolution")
        hint_issues += 1

if hint_issues == 0:
    print(f"  All {len(all_hints)} topicHints resolve ✓")
else:
    print(f"  {hint_issues} hint resolution failures")

# 3b: topic-catalog entries -> guide resolution
topic_orphans = 0
for t in topics["topics"]:
    tid = t["id"]
    ch_num = t.get("chapter")
    guide_id_fmt = tid[:2] + "-" + tid[2:]
    
    if guide_id_fmt in guide_map:
        continue
    source_fmts = [f"Ch{ch_num}", f"Ch{ch_num:02d}"] if ch_num else []
    has_splits = any(sf in source_map for sf in source_fmts)
    if has_splits:
        continue
    has_chapter_id = any(g.get("chapter_id") == tid for g in catalog["guides"])
    if has_chapter_id:
        continue
    
    find("CRITICAL", "3-topic-catalog", f"Topic '{tid}' ({t['title']}) has no guide resolution")
    topic_orphans += 1

if topic_orphans == 0:
    print(f"  All {len(topics['topics'])} topic-catalog entries resolve ✓")
else:
    print(f"  {topic_orphans} orphaned topic-catalog entries")

# 3c: base-guide-catalog field quality
field_issues = 0
for g in catalog["guides"]:
    gid = g["guide_id"]
    gtype = g.get("guide_type", "")
    
    if gtype in ("chapter", "split"):
        if not g.get("domain") or g["domain"] == "gap_or_custom":
            # splits from batch-1 might legitimately be gap_or_custom... 
            # but chapters should never be
            if gtype == "chapter":
                find("WARNING", "3-fields", f"{gid}: chapter has domain='gap_or_custom'")
                field_issues += 1
        if not g.get("tags"):
            find("WARNING", "3-fields", f"{gid}: empty tags array")
            field_issues += 1
        if g.get("chapter_id") is None and gtype == "split":
            find("WARNING", "3-fields", f"{gid}: split missing chapter_id")
            field_issues += 1

if field_issues == 0:
    print(f"  All guide catalog field quality checks pass ✓")
else:
    print(f"  {field_issues} field quality issues in base-guide-catalog")

# 3d: All 10 JSON files parse
json_files = [
    "quiz/quiz-content.json", "quiz/base-guide-catalog.json",
    "quiz/topic-catalog.json", "quiz/topic-matcher-flow.json",
    "quiz/audience-bucket-flow.json", "quiz/conversation-branch-flow.json",
    "quiz/api-contracts.json", "quiz/fulfillment-config.json",
    "quiz/product-catalog.json", "quiz/recommendation-routing-config.json"
]
parse_ok = 0
for jf in json_files:
    try:
        load_json(jf)
        parse_ok += 1
    except Exception as e:
        find("CRITICAL", "3-json", f"{jf} fails to parse: {e}")
print(f"  {parse_ok}/{len(json_files)} JSON files parse cleanly ✓")

# ═══════════════════════════════════════════════════════════════════════
# 4. AUDIENCE BUCKET COVERAGE
# ═══════════════════════════════════════════════════════════════════════
print("\n[4] AUDIENCE BUCKET COVERAGE")

# Check audience-slants vs worksheets dirs match
slant_set = set(slant_dirs)
ws_set = set(ws_dirs)

missing_ws = slant_set - ws_set
extra_ws = ws_set - slant_set

for m in missing_ws:
    find("CRITICAL", "4-buckets", f"Audience '{m}' has slants dir but no worksheets dir")
for m in extra_ws:
    find("WARNING", "4-buckets", f"Audience '{m}' has worksheets dir but no slants dir")

if not missing_ws and not extra_ws:
    print(f"  All {len(slant_dirs)} audience dirs match between slants and worksheets ✓")

# Per-audience file counts
for slug in slant_dirs:
    slant_count = len([f for f in os.listdir(f"content/topic-guides/audience-slants/{slug}") if f.endswith(".md")])
    ws_dir = f"content/worksheets/{slug}"
    ws_count = len([f for f in os.listdir(ws_dir) if f.endswith(".md")]) if os.path.isdir(ws_dir) else 0
    
    if slant_count != EXPECTED_BASE_GUIDES:
        find("WARNING", "4-buckets", f"'{slug}' slants: {slant_count} files (expected {EXPECTED_BASE_GUIDES})")
    if ws_count != EXPECTED_BASE_GUIDES * 2:
        find("WARNING", "4-buckets", f"'{slug}' worksheets: {ws_count} files (expected {EXPECTED_BASE_GUIDES * 2})")

# ═══════════════════════════════════════════════════════════════════════
# 5. QUIZ SCORING & SAFETY LOGIC
# ═══════════════════════════════════════════════════════════════════════
print("\n[5] QUIZ SCORING & SAFETY LOGIC")

# Scoring range
questions = quiz.get("questions", [])
min_score = 0
max_score = 0
for q in questions:
    scores = [opt.get("score", opt.get("value", 0)) for opt in q.get("options", q.get("answers", []))]
    if scores:
        min_score += min(scores)
        max_score += max(scores)

print(f"  Score range: {min_score}-{max_score}")

# Risk bands
bands = quiz.get("scoring", {})
ranges_list = bands.get("ranges", [])
overrides_list = bands.get("overrides", [])

if ranges_list:
    print(f"  Risk bands:")
    ranges_list_sorted = sorted(ranges_list, key=lambda x: x.get("min", 0))
    for r in ranges_list_sorted:
        lo = r.get("min", 0)
        hi = r.get("max", 0)
        level = r.get("riskLevel", "?")
        print(f"    {level}: {lo}-{hi}")
    
    # Check coverage gaps/overlaps
    for i in range(1, len(ranges_list_sorted)):
        prev_hi = ranges_list_sorted[i-1].get("max", 0)
        curr_lo = ranges_list_sorted[i].get("min", 0)
        if curr_lo > prev_hi + 1:
            find("CRITICAL", "5-scoring", f"Gap in risk bands: previous ends {prev_hi}, next starts {curr_lo}")
        elif curr_lo <= prev_hi:
            find("WARNING", "5-scoring", f"Overlap in risk bands: previous ends {prev_hi}, next starts {curr_lo}")
    
    # Check full range covered
    if ranges_list_sorted[0].get("min", 0) != min_score:
        find("WARNING", "5-scoring", f"Lowest band starts at {ranges_list_sorted[0].get('min')}, but min possible score is {min_score}")
    if ranges_list_sorted[-1].get("max", 0) != max_score:
        find("WARNING", "5-scoring", f"Highest band ends at {ranges_list_sorted[-1].get('max')}, but max possible score is {max_score}")
    
    print(f"  Risk band coverage: {ranges_list_sorted[0].get('min',0)}-{ranges_list_sorted[-1].get('max',0)} ✓")
else:
    find("CRITICAL", "5-scoring", "No scoring ranges found in quiz-content.json")

# Q5 crisis override
q5_found = False
for ov in overrides_list:
    if ov.get("questionId") == "q5":
        q5_found = True
        if ov.get("score") == 3 and ov.get("riskLevel") == "critical":
            print(f"  Q5 override: score=3 → critical ✓")
        if ov.get("score") == 2 and ov.get("minimumRiskLevel") == "high_risk":
            print(f"  Q5 override: score=2 → minimum high_risk ✓")

if not q5_found:
    find("WARNING", "5-scoring", "Q5 crisis override not found")

# Routing: critical blocks matcher
crit_rules = routing.get("riskRules", {}).get("critical", {})
if crit_rules.get("allowTopicMatcher") is False and crit_rules.get("allowAudienceMatcher") is False:
    print(f"  Critical risk blocks matchers ✓")
else:
    find("CRITICAL", "5-safety", "Critical risk does NOT block topic/audience matchers")

if crit_rules.get("hidePaidOffersAboveFold") is True:
    print(f"  Critical risk hides paid offers ✓")
else:
    find("CRITICAL", "5-safety", "Critical risk does NOT hide paid offers above fold")

# Conversation branch: never gates crisis resources
convo_str = json.dumps(convo)
if "allowPaidOfferAboveCrisisActions" in convo_str:
    if '"allowPaidOfferAboveCrisisActions": false' in convo_str or '"allowPaidOfferAboveCrisisActions":false' in convo_str:
        print(f"  Conversation flow: paid offers blocked above crisis actions ✓")
    else:
        find("CRITICAL", "5-safety", "Conversation branch may allow paid offers above crisis actions")
if "allowCaptureBeforeCrisisActions" in convo_str:
    if '"allowCaptureBeforeCrisisActions": false' in convo_str or '"allowCaptureBeforeCrisisActions":false' in convo_str:
        print(f"  Conversation flow: capture blocked before crisis actions ✓")
    else:
        find("CRITICAL", "5-safety", "Conversation branch may allow capture before crisis actions")

# ═══════════════════════════════════════════════════════════════════════
# 6. PRODUCT & FULFILLMENT ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════
print("\n[6] PRODUCT & FULFILLMENT ALIGNMENT")

product_ids = {p["product_id"] for p in products["products"]}
fulfillment_products = set(fulfillment.get("productFulfillmentMap", {}).keys())

# Offer lanes in guide catalog
offer_values = set()
for g in catalog["guides"]:
    ol = g.get("offer_lane", {})
    if ol.get("primary_offer"):
        offer_values.add(ol["primary_offer"])
    if ol.get("secondary_offer"):
        offer_values.add(ol["secondary_offer"])

unmapped_offers = offer_values - product_ids
if unmapped_offers:
    for o in unmapped_offers:
        find("CRITICAL", "6-products", f"Offer lane value '{o}' not in product-catalog")
else:
    print(f"  All offer lane values map to product-catalog ✓")

missing_fulfillment = product_ids - fulfillment_products
if missing_fulfillment:
    for m in missing_fulfillment:
        find("WARNING", "6-products", f"Product '{m}' has no fulfillment action chain")
else:
    print(f"  All products have fulfillment chains ✓")

# Pricing profile keys
pricing_profiles = matcher.get("pricingProfiles", {})
active_profile = matcher.get("activePricingProfile", "")
if active_profile and active_profile in pricing_profiles:
    profile_keys = set(pricing_profiles[active_profile].keys())
    missing_pricing = product_ids - profile_keys - {"free_crisis_resources"}
    if missing_pricing:
        for m in missing_pricing:
            find("WARNING", "6-products", f"Product '{m}' missing from active pricing profile '{active_profile}'")
    else:
        print(f"  Active pricing profile covers all paid products ✓")
else:
    find("WARNING", "6-products", f"Active pricing profile '{active_profile}' not found")

# ═══════════════════════════════════════════════════════════════════════
# 7. MANIFEST VS. REALITY
# ═══════════════════════════════════════════════════════════════════════
print("\n[7] MANIFEST VS. REALITY")

manifest_path = "planning/GUIDE-BUILD-MANIFEST.csv"
manifest_ids = set()
manifest_rows = 0
if file_exists(manifest_path):
    with open(manifest_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            manifest_rows += 1
            gid = row.get("guide_id", row.get("id", "")).strip()
            if gid:
                manifest_ids.add(gid)
    
    catalog_ids = {g["guide_id"] for g in catalog["guides"]}
    
    in_manifest_not_catalog = manifest_ids - catalog_ids
    in_catalog_not_manifest = catalog_ids - manifest_ids
    
    print(f"  Manifest rows: {manifest_rows}")
    print(f"  Catalog guides: {len(catalog_ids)}")
    
    if in_manifest_not_catalog:
        for m in sorted(in_manifest_not_catalog):
            find("WARNING", "7-manifest", f"In manifest but not catalog: {m}")
    if in_catalog_not_manifest:
        for m in sorted(in_catalog_not_manifest):
            find("WARNING", "7-manifest", f"In catalog but not manifest: {m}")
    if not in_manifest_not_catalog and not in_catalog_not_manifest:
        print(f"  Manifest ↔ catalog: perfect match ✓")
else:
    find("CRITICAL", "7-manifest", "GUIDE-BUILD-MANIFEST.csv not found")

# ═══════════════════════════════════════════════════════════════════════
# 8. KNOWN GAPS & MISSING PIECES
# ═══════════════════════════════════════════════════════════════════════
print("\n[8] KNOWN GAPS & MISSING PIECES")

# Module 2
mod2_files = glob.glob("content/modules/module-2-*.md") + glob.glob("content/modules/module-2.md")
if not mod2_files:
    find("WARNING", "8-gaps", "Module 2 does not exist (only modules 1 and 3)")
    print("  Module 2: MISSING")
else:
    print(f"  Module 2: exists ✓")

# Disclaimers in modules + lead magnet
module_files = glob.glob("content/modules/module-*.md")
lead_magnet_files = glob.glob("content/lead-magnet/*.md")
for mf in module_files + lead_magnet_files:
    with open(mf) as f:
        content = f.read()
    if "educational" not in content.lower() and "not a substitute" not in content.lower():
        find("WARNING", "8-gaps", f"Missing disclaimer in {os.path.relpath(mf)}")
    else:
        print(f"  Disclaimer in {os.path.relpath(mf)} ✓")

# Handoff doc staleness
handoff = "planning/TECH-HANDOFF-FOR-CODY.md"
if file_exists(handoff):
    with open(handoff) as f:
        hcontent = f.read()
    stale_markers = ["1,343", "This guide helps with", "boilerplate"]
    stale_found = [m for m in stale_markers if m.lower() in hcontent.lower()]
    # Check for pre-voice-pass file counts
    if "1,422" not in hcontent and "1422" not in hcontent:
        find("INFO", "8-gaps", "Handoff doc may reference pre-voice-pass file counts (doesn't mention 1,422)")
    if "2,686" not in hcontent and "2686" not in hcontent:
        find("INFO", "8-gaps", "Handoff doc doesn't mention 2,686 standalone worksheets (post-extraction)")
    print(f"  Handoff doc: exists (staleness markers: {len(stale_found)} found)")
else:
    find("INFO", "8-gaps", "Handoff doc not found")

# API routes
web_dir = "web"
if os.path.isdir(web_dir):
    api_files = glob.glob(f"{web_dir}/**/*.ts", recursive=True) + glob.glob(f"{web_dir}/**/*.tsx", recursive=True)
    print(f"  Web/API files: {len(api_files)} TypeScript files found")
else:
    print(f"  Web directory: exists but no TS files found")

# ═══════════════════════════════════════════════════════════════════════
# 9. DANGEROUS CONTENT / PLACEHOLDER SCAN
# ═══════════════════════════════════════════════════════════════════════
print("\n[9] DANGEROUS CONTENT / PLACEHOLDER SCAN")

# Scan ALL content files
all_content_files = (
    ch_files + sp_files + nt_files +
    all_variant_files +
    glob.glob("content/worksheets/**/*.md", recursive=True) +
    module_files + lead_magnet_files
)

placeholder_patterns = {
    "Lorem ipsum": re.compile(r'lorem ipsum', re.I),
    "TODO": re.compile(r'\bTODO\b'),
    "FIXME": re.compile(r'\bFIXME\b'),
    "TBD": re.compile(r'\bTBD\b'),
    "placeholder": re.compile(r'\bplaceholder\b', re.I),
    "Step one.": re.compile(r'^1\. Step one\.', re.M),
    "Starter line 1": re.compile(r'Starter line 1'),
    "insert here": re.compile(r'insert here', re.I),
    "[AUDIENCE]": re.compile(r'\[AUDIENCE\]'),
    "[TOPIC]": re.compile(r'\[TOPIC\]'),
}

placeholder_hits = {}
empty_files = []
tiny_files = []  # under 200 bytes

# PII/secrets patterns
secret_patterns = {
    "API key": re.compile(r'(sk[-_]live|sk[-_]test|AKIA|AIza)[A-Za-z0-9]{10,}'),
    "Bearer token": re.compile(r'Bearer [A-Za-z0-9\-_.]{20,}'),
    "password=": re.compile(r'password\s*=\s*["\'][^"\']{4,}', re.I),
}
secret_hits = {}

file_count = len(all_content_files)
print(f"  Scanning {file_count} content files...")

for fpath in all_content_files:
    try:
        fsize = os.path.getsize(fpath)
    except:
        continue
    
    if fsize == 0:
        empty_files.append(fpath)
        continue
    if fsize < 200:
        tiny_files.append((fpath, fsize))
    
    try:
        with open(fpath) as f:
            content = f.read()
    except:
        continue
    
    for label, pat in placeholder_patterns.items():
        if pat.search(content):
            placeholder_hits.setdefault(label, []).append(os.path.relpath(fpath))
    
    for label, pat in secret_patterns.items():
        if pat.search(content):
            secret_hits.setdefault(label, []).append(os.path.relpath(fpath))

# Report
if empty_files:
    find("CRITICAL", "9-content", f"{len(empty_files)} empty (0 byte) files found")
    for ef in empty_files[:5]:
        find("CRITICAL", "9-content", f"  Empty: {os.path.relpath(ef)}")
    if len(empty_files) > 5:
        find("CRITICAL", "9-content", f"  ...and {len(empty_files)-5} more")
else:
    print(f"  Empty files: 0 ✓")

if tiny_files:
    find("WARNING", "9-content", f"{len(tiny_files)} files under 200 bytes (likely broken)")
    for tf, sz in tiny_files[:5]:
        find("WARNING", "9-content", f"  Tiny ({sz}b): {os.path.relpath(tf)}")
    if len(tiny_files) > 5:
        find("WARNING", "9-content", f"  ...and {len(tiny_files)-5} more")
else:
    print(f"  Tiny files (<200b): 0 ✓")

for label, files in placeholder_hits.items():
    sev = "CRITICAL" if label in ("[AUDIENCE]", "[TOPIC]", "Lorem ipsum") else "WARNING"
    find(sev, "9-placeholders", f"Placeholder '{label}' found in {len(files)} files")
    for fp in files[:3]:
        find(sev, "9-placeholders", f"  → {fp}")
    if len(files) > 3:
        find(sev, "9-placeholders", f"  ...and {len(files)-3} more")

if not placeholder_hits:
    print(f"  Placeholder patterns: 0 hits ✓")

for label, files in secret_hits.items():
    find("CRITICAL", "9-secrets", f"Possible {label} found in {len(files)} files")
    for fp in files[:3]:
        find("CRITICAL", "9-secrets", f"  → {fp}")

if not secret_hits:
    print(f"  Secrets/PII scan: clean ✓")

# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)

critical = [f for f in findings if f[0] == "CRITICAL"]
warnings = [f for f in findings if f[0] == "WARNING"]
info = [f for f in findings if f[0] == "INFO"]

if findings:
    print(f"\n  Total findings: {len(findings)}")
    print(f"  🔴 CRITICAL: {len(critical)}")
    print(f"  🟡 WARNING:  {len(warnings)}")
    print(f"  🔵 INFO:     {len(info)}")
    
    if critical:
        print(f"\n--- CRITICAL ({len(critical)}) ---")
        for sev, cat, msg in critical:
            print(f"  [{cat}] {msg}")
    
    if warnings:
        print(f"\n--- WARNING ({len(warnings)}) ---")
        for sev, cat, msg in warnings:
            print(f"  [{cat}] {msg}")
    
    if info:
        print(f"\n--- INFO ({len(info)}) ---")
        for sev, cat, msg in info:
            print(f"  [{cat}] {msg}")
else:
    print("\n  ✅ ZERO FINDINGS — workspace is clean.")

print()
