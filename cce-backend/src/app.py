"""FastAPI application for the Clinical Conversation Engine."""
import os
import re
import json
import time
import random
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .engine import (
    TREES,
    create_session,
    get_outcome,
    get_session,
    process_response,
)
from .models import (
    HealthResponse,
    RespondRequest,
    RespondResponse,
    SessionStartResponse,
    StartRequest,
    TreesResponse,
)

# ─── CORS ──────────────────────────────────────────────────────────────────────

_default_origins = [
    "http://localhost:3131",
    "http://127.0.0.1:3131",
    "http://localhost:5173",
    "http://localhost:3000",
]

_env_origins = os.getenv("CCE_CORS_ORIGINS", "")
ALLOWED_ORIGINS: List[str] = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    or _default_origins
)

# ─── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

# ─── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Clinical Conversation Engine",
    description="Session-based conversation engine for mental health triage and psychoeducation.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@app.get("/trees", response_model=TreesResponse)
async def trees():
    tree_list = [
        {"id": tid, "name": tdata.get("name", tid), "description": tdata.get("description", "")}
        for tid, tdata in TREES.items()
    ]
    return TreesResponse(trees=tree_list)


@app.post("/session/start", response_model=SessionStartResponse)
@limiter.limit("30/minute")
async def session_start(request: Request, body: StartRequest):
    try:
        session, prompt = create_session(body.tree_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SessionStartResponse(
        session_id=session.session_id,
        current_prompt=prompt,
        status="in_progress",
    )


@app.post("/session/{session_id}/respond", response_model=RespondResponse)
@limiter.limit("60/minute")
async def session_respond(request: Request, session_id: str, body: RespondRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.is_complete:
        raise HTTPException(status_code=409, detail="Session already complete")
    if not body.option_id and not body.message:
        raise HTTPException(status_code=422, detail="Provide option_id or message")
    try:
        result = process_response(session_id, body.option_id, body.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RespondResponse(**result)


# ─── Therapist Finder ─────────────────────────────────────────────────────────

# Map chatbot topic → Psychology Today category slug
TOPIC_TO_PT_CATEGORY = {
    "relationship": "relationship-issues",
    "loneliness":   "loneliness",
    "anxiety":      "anxiety",
    "work":         "stress",
    "loss":         "grief",
    "family":       "family-conflicts",
    "recovery":     "addiction",
    "general":      "depression",
}

PT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.psychologytoday.com/",
    "Cache-Control": "no-cache",
}


def _parse_pt_jsonld(html: str, zip_code: str) -> list[dict]:
    """
    PT embeds a schema.org SearchResultsPage JSON-LD block.
    Extract therapists from mainEntity[]; pull credentials from meta description.
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── Build credential map from meta description ─────────────────────────
    cred_map: dict[str, str] = {}
    meta = (
        soup.find("meta", attrs={"name": "description"}) or
        soup.find("meta", attrs={"property": "og:description"})
    )
    if meta:
        desc = meta.get("content", "") or ""
        cred_part = desc.split(" - ", 1)[-1] if " - " in desc else ""
        for entry in cred_part.split(";"):
            entry = entry.strip()
            if "," in entry:
                ci = entry.index(",")
                cname = entry[:ci].strip()
                ccred  = entry[ci + 1:].strip()
                if cname:
                    cred_map[cname] = ccred

    # ── Extract therapists from JSON-LD ────────────────────────────────────
    therapists = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue

        if data.get("@type") != "SearchResultsPage":
            continue

        entities = data.get("mainEntity", [])
        if not isinstance(entities, list):
            entities = [entities]

        for person in entities:
            try:
                name = (person.get("name") or "").strip()
                if not name:
                    continue

                url = person.get("url") or person.get("@id") or ""
                addr = (
                    (person.get("workLocation") or {})
                    .get("address") or {}
                )
                city  = addr.get("addressLocality", "")
                state = addr.get("addressRegion", "")
                location = f"{city}, {state}" if city else zip_code
                phone = (person.get("telephone") or "").strip()
                cred  = cred_map.get(name, "")

                therapists.append({
                    "name":        name,
                    "credentials": cred,
                    "location":    location,
                    "phone":       phone,
                    "bio":         "",
                    "photo":       "",
                    "profile_url": url,
                    "specialties": [],
                    "source":      "psychology_today",
                })
            except Exception:
                continue

        break  # Only one SearchResultsPage block needed

    return therapists

    return therapists


async def _scrape_pt(zip_code: str, category: str) -> list[dict]:
    """Fetch Psychology Today search page and extract therapists via JSON-LD."""
    url = f"https://www.psychologytoday.com/us/therapists/{zip_code}"
    params = {"category": category, "new_code": "1"} if category else {"new_code": "1"}

    async with httpx.AsyncClient(headers=PT_HEADERS, follow_redirects=True, timeout=14) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        return []

    return _parse_pt_jsonld(resp.text, zip_code)


@app.get("/therapists")
@limiter.limit("20/minute")
async def find_therapists(
    request: Request,
    zip: str = Query(..., min_length=5, max_length=5, pattern=r"^\d{5}$"),
    topic: str = Query("general", max_length=30),
):
    """Return nearby therapists from Psychology Today for a given zip + topic."""
    category = TOPIC_TO_PT_CATEGORY.get(topic, "depression")
    therapists = await _scrape_pt(zip, category)

    # Build fallback PT search URL so frontend can always offer a direct link
    pt_url = (
        f"https://www.psychologytoday.com/us/therapists/{zip}"
        f"?category={category}&new_code=1"
    )

    return {
        "zip": zip,
        "topic": topic,
        "category": category,
        "therapists": therapists,
        "pt_search_url": pt_url,
        "count": len(therapists),
    }


@app.get("/session/{session_id}/outcome")
async def session_outcome(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_complete:
        raise HTTPException(status_code=409, detail="Session is not yet complete")
    outcome = get_outcome(session_id)
    if not outcome:
        raise HTTPException(status_code=500, detail="Outcome missing")
    return outcome
