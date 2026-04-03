#!/usr/bin/env python3
import json
from pathlib import Path
import re

root = Path('/Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health')

guide_ids = [
    'ch-01', 'ch-03', 'ch-04', 'ch-06', 'ch-08', 'ch-09', 'ch-11', 'ch-12', 'ch-13', 'ch-14',
    'ch-19', 'ch-20', 'ch-21', 'ch-22', 'ch-23', 'ch-24', 'ch-26', 'ch-27', 'ch-28', 'ch-29',
    'ch-30', 'ch-31', 'ch-33', 'ch-34', 'ch-35', 'ch-36', 'ch-37', 'ch-38', 'ch-39', 'ch-41',
    'ch-42', 'ch-45', 'ch-46',
    'split-01', 'split-02', 'split-03', 'split-04', 'split-05', 'split-06', 'split-07', 'split-08',
    'split-09', 'split-10', 'split-11', 'split-12', 'split-13', 'split-14', 'split-15', 'split-16',
    'split-17', 'split-18', 'split-19', 'split-20', 'split-21', 'split-22', 'split-23', 'split-24',
    'split-25', 'split-26', 'split-27', 'split-28',
    'new-01', 'new-02', 'new-03', 'new-04', 'new-05', 'new-06', 'new-07', 'new-08', 'new-09', 'new-10',
    'new-11', 'new-12', 'new-13', 'new-14', 'new-15', 'new-16', 'new-17', 'new-18'
]

def find_guide_file(guide_id):
    """Find the markdown file for a guide ID."""
    base = root / 'content' / 'topic-guides'
    for dir_path in [base / 'chapters', base / 'splits', base / 'new-topics']:
        for p in dir_path.glob('*.md'):
            if guide_id in p.name:
                return p
    return None

def score_guide(text):
    """Score a guide on key dimensions."""
    scores = {
        'has_what_to_say': bool(re.search(r'\bwhat to say\b', text, re.I)),
        'has_what_to_do': bool(re.search(r'\bwhat to do\b', text, re.I)),
        'has_scripts': bool(re.search(r'\bscript|exact words|exact phrases', text, re.I)),
        'has_follow_up': bool(re.search(r'follow.?up|24.?hour action plan|next step', text, re.I)),
        'has_worksheets': bool(re.search(r'worksheet|prompt', text, re.I)),
        'has_safety': bool(re.search(r'\b988\b|crisis text line|741741', text, re.I)),
        'warm_tone': bool(re.search(r"you're|don't|it's|won't|can't|here's", text, re.I)),
    }
    intent_score = (
        scores['has_what_to_say'] * 2 +
        scores['has_scripts'] * 2 +
        scores['has_what_to_do'] +
        scores['has_follow_up'] +
        scores['has_worksheets']
    ) / 7.0 * 100
    return scores, int(intent_score)

def extract_title(text):
    """Extract the guide title."""
    match = re.search(r'^#\s+(.+)$', text, re.M)
    return match.group(1) if match else "Unknown"

results = []
for guide_id in guide_ids:
    fpath = find_guide_file(guide_id)
    if not fpath:
        results.append({
            'guide_id': guide_id,
            'status': 'NOT_FOUND',
            'scores': {},
            'intent_score': 0
        })
        continue
    
    text = fpath.read_text(encoding='utf-8', errors='ignore')
    title = extract_title(text)
    scores, intent_score = score_guide(text)
    
    results.append({
        'guide_id': guide_id,
        'title': title,
        'fpath': str(fpath.relative_to(root)),
        'status': 'OK',
        'scores': scores,
        'intent_score': intent_score
    })

summary = {
    'total': len(results),
    'found': sum(1 for r in results if r['status'] == 'OK'),
    'not_found': sum(1 for r in results if r['status'] != 'OK'),
    'avg_intent_score': int(sum(r['intent_score'] for r in results) / len(results)),
    'guides_with_all_signals': sum(1 for r in results if r['status'] == 'OK' and all(r['scores'].values()) if 'scores' in r),
}

# Write JSON report
json_report = root / 'output' / 'etsy' / 'qualitative-guide-audit.json'
with json_report.open('w', encoding='utf-8') as f:
    json.dump({'summary': summary, 'guides': results}, f, indent=2)

# Write text report
txt_report = root / 'output' / 'etsy' / 'qualitative-guide-audit.txt'
with txt_report.open('w', encoding='utf-8') as f:
    f.write('QUALITATIVE GUIDE AUDIT (79 Base Guides)\n')
    f.write('=' * 80 + '\n\n')
    f.write(json.dumps(summary, indent=2) + '\n\n')
    f.write('DETAILED RESULTS\n')
    f.write('-' * 80 + '\n\n')
    
    # Sort by intent score descending
    sorted_results = sorted(results, key=lambda r: r['intent_score'], reverse=True)
    for r in sorted_results:
        if r['status'] == 'OK':
            scores = r['scores']
            signal_count = sum(1 for v in scores.values() if v)
            f.write(f"{r['intent_score']:3d} | {r['guide_id']:8s} | {signal_count}/7 signals | {r['title']}\n")
            f.write(f"      {json.dumps(scores)}\n")
        else:
            f.write(f"   - | {r['guide_id']:8s} | NOT FOUND\n")

print('WROTE', json_report)
print('WROTE', txt_report)
print('SUMMARY', json.dumps(summary))
