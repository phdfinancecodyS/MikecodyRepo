"""SQLite-backed leads database. Handles 1M+ records with dedup, export, and funnel tracking."""
import csv
import io
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DB_PATH = Path(os.environ.get(
    "CCE_LEADS_DB",
    Path(__file__).resolve().parent.parent / "data" / "leads.db",
))
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Thread-local connection with WAL mode for concurrent reads."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
    return _local.conn


def init_db() -> None:
    """Create leads table if not exists. Safe to call multiple times."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            first_name TEXT,
            email_opted_in INTEGER NOT NULL DEFAULT 0,
            sms_opted_in INTEGER NOT NULL DEFAULT 0,
            risk_band TEXT,
            topics TEXT,
            audience_bucket TEXT,
            conversation_turns INTEGER DEFAULT 0,
            moderation_warnings INTEGER DEFAULT 0,
            sentiment TEXT,
            source TEXT DEFAULT 'conversation',
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            captured_at TEXT NOT NULL,
            updated_at TEXT,
            UNIQUE(session_id)
        );

        CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
        CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
        CREATE INDEX IF NOT EXISTS idx_leads_captured_at ON leads(captured_at);
        CREATE INDEX IF NOT EXISTS idx_leads_risk_band ON leads(risk_band);
        CREATE INDEX IF NOT EXISTS idx_leads_sms_opted_in ON leads(sms_opted_in);
    """)
    conn.commit()


def upsert_lead(
    session_id: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    email_opted_in: bool = False,
    sms_opted_in: bool = False,
    risk_band: Optional[str] = None,
    topics: Optional[List[str]] = None,
    audience_bucket: Optional[str] = None,
    conversation_turns: int = 0,
    moderation_warnings: int = 0,
    sentiment: Optional[str] = None,
    source: str = "conversation",
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert or update a lead. Returns the lead record. Deduplicates by session_id."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    topics_json = json.dumps(topics) if topics else None

    conn.execute("""
        INSERT INTO leads (
            session_id, email, phone, first_name,
            email_opted_in, sms_opted_in,
            risk_band, topics, audience_bucket,
            conversation_turns, moderation_warnings, sentiment,
            source, utm_source, utm_medium, utm_campaign,
            captured_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            email = COALESCE(excluded.email, leads.email),
            phone = COALESCE(excluded.phone, leads.phone),
            first_name = COALESCE(excluded.first_name, leads.first_name),
            email_opted_in = MAX(excluded.email_opted_in, leads.email_opted_in),
            sms_opted_in = MAX(excluded.sms_opted_in, leads.sms_opted_in),
            risk_band = COALESCE(excluded.risk_band, leads.risk_band),
            topics = COALESCE(excluded.topics, leads.topics),
            audience_bucket = COALESCE(excluded.audience_bucket, leads.audience_bucket),
            conversation_turns = MAX(excluded.conversation_turns, leads.conversation_turns),
            moderation_warnings = MAX(excluded.moderation_warnings, leads.moderation_warnings),
            sentiment = COALESCE(excluded.sentiment, leads.sentiment),
            updated_at = excluded.updated_at
    """, (
        session_id, email, phone, first_name,
        int(email_opted_in), int(sms_opted_in),
        risk_band, topics_json, audience_bucket,
        conversation_turns, moderation_warnings, sentiment,
        source, utm_source, utm_medium, utm_campaign,
        now, now,
    ))
    conn.commit()

    return {"ok": True, "captured_at": now, "is_new": conn.total_changes == 1}


def get_lead(session_id: str) -> Optional[Dict[str, Any]]:
    """Get a single lead by session_id."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM leads WHERE session_id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def count_leads() -> Dict[str, int]:
    """Quick stats for admin dashboard."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    with_email = conn.execute("SELECT COUNT(*) FROM leads WHERE email IS NOT NULL").fetchone()[0]
    with_phone = conn.execute("SELECT COUNT(*) FROM leads WHERE phone IS NOT NULL").fetchone()[0]
    sms_opted = conn.execute("SELECT COUNT(*) FROM leads WHERE sms_opted_in = 1").fetchone()[0]
    email_opted = conn.execute("SELECT COUNT(*) FROM leads WHERE email_opted_in = 1").fetchone()[0]

    # Today's captures
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE captured_at >= ?", (today,)
    ).fetchone()[0]

    # Band breakdown
    bands = {}
    for row in conn.execute("SELECT risk_band, COUNT(*) as c FROM leads GROUP BY risk_band"):
        bands[row[0] or "unknown"] = row[1]

    return {
        "total": total,
        "with_email": with_email,
        "with_phone": with_phone,
        "email_opted_in": email_opted,
        "sms_opted_in": sms_opted,
        "today": today_count,
        "by_band": bands,
    }


def export_leads(
    limit: int = 10000,
    offset: int = 0,
    sms_only: bool = False,
    email_only: bool = False,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Export leads as list of dicts. Supports filters for targeted export."""
    conn = _get_conn()
    conditions = []
    params: list = []

    if sms_only:
        conditions.append("sms_opted_in = 1 AND phone IS NOT NULL")
    if email_only:
        conditions.append("email_opted_in = 1 AND email IS NOT NULL")
    if since:
        conditions.append("captured_at >= ?")
        params.append(since)

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM leads WHERE {where} ORDER BY captured_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def export_csv(sms_only: bool = False, email_only: bool = False, since: Optional[str] = None) -> str:
    """Export leads as CSV string for bulk upload to SendGrid/Twilio/ConvertKit."""
    leads = export_leads(limit=1000000, sms_only=sms_only, email_only=email_only, since=since)
    if not leads:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=leads[0].keys())
    writer.writeheader()
    writer.writerows(leads)
    return output.getvalue()


# Initialize on import
init_db()
