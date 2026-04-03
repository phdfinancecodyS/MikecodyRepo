# Pinterest Automation Runbook

## What Is Automated

- Generate pin metadata for all live Etsy listings.
- Build tracked Etsy URLs with UTM parameters.
- Assign each pin to a board category.
- Produce a 14-day publish schedule.

## Generate Files

Run:

```bash
/Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/.venv/bin/python scripts/pinterest_automation.py --start-date 2026-03-27 --daily-pins 4
```

Output files:

- `output/pinterest/pins_master.csv`
- `output/pinterest/pins_14day_schedule.csv`
- `output/pinterest/pinterest_summary.json`

## What Is Still Manual

- Claim Etsy account in Pinterest Business settings.
- Upload pin images and metadata in Pinterest.
- Schedule or publish based on `pins_14day_schedule.csv`.

## Recommended Flow

1. Open `pins_14day_schedule.csv` and post in daily order.
2. Use `image_path` for pin creative source.
3. Paste `pin_title`, `pin_description`, and `destination_url`.
4. Check Pinterest outbound clicks weekly and keep top-performing boards.
