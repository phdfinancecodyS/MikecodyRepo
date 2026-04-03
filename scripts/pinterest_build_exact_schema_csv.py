#!/usr/bin/env python3
import csv
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src = root / 'output' / 'pinterest' / 'pins_first4_pinterest_image_import.csv'
out = root / 'output' / 'pinterest' / 'pins_first4_pinterest_exact_schema.csv'

keywords_by_title = {
    "Hyperarousal: Still On Alert - When Your Brain Won't Stop Scanning for Danger": "printable worksheet, conversation guide, instant download, hyperarousal",
    "On Guard in Your Own Home: Dealing With Hypervigilance": "printable worksheet, conversation guide, instant download, hypervigilance",
    "Anger and Short-Fuse Days": "printable worksheet, conversation guide, instant download, anger",
    "Depression and Numbness": "printable worksheet, conversation guide, instant download, depression",
}

desc_by_title = {
    "Hyperarousal: Still On Alert - When Your Brain Won't Stop Scanning for Danger": "Hyperarousal printable worksheet and conversation guide for stress. Instant download you can use today. Use this printable guide to start hard conversations with less panic and more clarity.",
    "On Guard in Your Own Home: Dealing With Hypervigilance": "Hypervigilance printable worksheet and conversation guide for home. Instant download you can use today. Use this printable guide to start hard conversations with less panic and more clarity.",
    "Anger and Short-Fuse Days": "Anger printable worksheet and conversation guide for irritability. Instant download you can use today. Use this printable guide to start hard conversations with less panic and more clarity.",
    "Depression and Numbness": "Depression printable worksheet and conversation guide for numbness. Instant download you can use today. Use this printable guide to start hard conversations with less panic and more clarity.",
}

rows = []
with src.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        title = row['Title'].strip()[:100]
        rows.append({
            'Title': title,
            'Media URL': row['Media URL'].strip(),
            'Pinterest board': row['Pinterest board'].strip(),
            'Thumbnail': '',
            'Description': desc_by_title.get(title, ''),
            'Link': row['Link'].strip(),
            'Publish date': '',
            'Keywords': keywords_by_title.get(title, ''),
        })

with out.open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(
        f,
        fieldnames=['Title', 'Media URL', 'Pinterest board', 'Thumbnail', 'Description', 'Link', 'Publish date', 'Keywords']
    )
    writer.writeheader()
    writer.writerows(rows)

print(out)
