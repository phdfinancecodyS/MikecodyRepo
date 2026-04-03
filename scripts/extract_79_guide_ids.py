import json
from pathlib import Path

root = Path('/Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health')
listings_path = root / 'output' / 'etsy' / 'listings.json'

with listings_path.open() as f:
    data = json.load(f)

guide_ids = [item['guide_id'] for item in data['listings']]
for gid in guide_ids:
    print(gid)
