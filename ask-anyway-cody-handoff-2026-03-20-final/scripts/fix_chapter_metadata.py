#!/usr/bin/env python3
import re
from pathlib import Path

# Map of chapter to batch/priority
chapter_priority = {
    1: ("batch-1", "high"), 4: ("batch-1", "high"), 6: ("batch-1", "high"),
    8: ("batch-1", "high"), 23: ("batch-1", "high"), 36: ("batch-1", "high"),
    24: ("batch-2", "medium"), 26: ("batch-2", "medium"), 27: ("batch-2", "medium"),
    29: ("batch-2", "medium"), 30: ("batch-2", "medium"), 31: ("batch-2", "medium"),
}

for f in Path("content/topic-guides/chapters").glob("ch-*.md"):
    with open(f, 'r') as fp:
        content = fp.read()
    
    # Extract chapter number
    match = re.match(r"ch-(\d+)", f.stem)
    ch_num = int(match.group(1))
    
    # Get batch and priority
    batch, priority = chapter_priority.get(ch_num, ("batch-3", "medium"))
    
    # Check if metadata exists
    if not re.search(r"^Status: draft_v1_complete", content, re.MULTILINE):
        # Extract title
        title_match = re.match(r"# (.*?)\n", content)
        title = title_match.group(1) if title_match else ""
        
        # Build new metadata
        metadata = f"""# {title}

Status: draft_v1_complete
Guide ID: ch-{ch_num:02d}
Guide type: chapter
Source: Ch{ch_num}
Batch: {batch}
Priority: {priority}

"""
        
        # Remove old title line if present
        new_content = re.sub(r"^# .*?\n\n+", "", content, count=1)
        
        # Prepend metadata
        new_content = metadata + new_content
        
        with open(f, 'w') as fp:
            fp.write(new_content)
        
        print(f"✓ Fixed: {f.name}")

print("\nMetadata restoration complete.")
