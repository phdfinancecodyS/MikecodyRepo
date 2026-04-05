"""Quick verification of topic matching and unmatched demand tracking."""
import requests
import json

BASE = "http://localhost:8000"

def test_topic(msg):
    r = requests.post(f"{BASE}/session/start", json={"tree_id": "main-flow"})
    sid = r.json()["session_id"]
    r2 = requests.post(f"{BASE}/session/{sid}/respond", json={"message": msg})
    return r2.json()["status"]


print("=== MATCHED TOPICS ===")
for msg in [
    "my anxiety is killing me",
    "I lost my dad last year",
    "work is burning me out",
    "my marriage is falling apart",
]:
    status = test_topic(msg)
    print(f"  {msg:50} -> {status}")


print()
print("=== UNMATCHED (should log for demand tracking) ===")
for msg in [
    "my ADHD makes everything harder",
    "I keep binge eating",
    "I feel like Im watching myself from outside",
    "my bipolar is cycling again",
    "intrusive thoughts wont stop",
    "body image issues after surgery",
]:
    status = test_topic(msg)
    print(f"  {msg:50} -> {status}")


print()
r = requests.get(f"{BASE}/admin/metrics")
m = r.json()

print("=== TOPIC COUNTERS ===")
for k, v in sorted(m["totals"].items()):
    if "topic" in k:
        print(f"  {k}: {v}")

print()
print("=== UNMATCHED TOPICS LOG ===")
ut = m["unmatched_topics"]
print(f"  Total: {ut['total']}, Today: {ut['today']}")
for entry in ut["recent"]:
    print(f"  - {entry['text'][:60]}")
