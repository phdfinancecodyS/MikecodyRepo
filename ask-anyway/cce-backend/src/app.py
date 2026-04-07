"""FastAPI application for the Clinical Conversation Engine."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the cce-backend root (parent of src/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import re
import json
import time
import random
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .engine import (
    TREES,
    create_session,
    get_outcome,
    get_session,
    process_response,
    _save_session,
)
from . import metrics
from . import alerting
from .config import (
    GUIDES_BY_ID, GUIDES_BY_DOMAIN, AUDIENCE_BUCKETS, AUDIENCE_QUESTIONS,
    PRODUCTS_BY_ID, PRICING_PROFILES, ACTIVE_PRICING, ETSY_LISTINGS,
    resolve_guide_path, get_guide_for_topic, get_offer_for_risk, get_offer_for_guide,
)
from .models import (
    HealthCheck,
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

_rl_session = os.environ.get("RL_SESSION", "30/minute")
_rl_respond = os.environ.get("RL_RESPOND", "60/minute")
_rl_recommend = os.environ.get("RL_RECOMMEND", "30/minute")

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


# ─── Static assets ─────────────────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"

if (_STATIC_DIR / "guides").is_dir():
    app.mount("/guides", StaticFiles(directory=str(_STATIC_DIR / "guides")), name="guides")


@app.get("/", response_class=HTMLResponse)
async def root():
    if _INDEX_HTML.exists():
        return HTMLResponse(_INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Ask Anyway</h1><p>Backend is running.</p>")


# ─── Routes ────────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health():
    checks = []
    all_ok = True

    # Check 1: conversation trees loaded
    tree_ok = len(TREES) > 0
    checks.append(HealthCheck(name="trees", status="ok" if tree_ok else "down"))
    if not tree_ok:
        all_ok = False

    # Check 2: LLM provider configured (if LLM mode enabled)
    response_engine = os.environ.get("CCE_RESPONSE_ENGINE", "template")
    if response_engine == "llm":
        api_key = os.environ.get("CCE_LLM_API_KEY", "")
        llm_ok = bool(api_key and len(api_key) > 8)
        checks.append(HealthCheck(name="llm", status="ok" if llm_ok else "degraded"))
        if not llm_ok:
            all_ok = False
    else:
        checks.append(HealthCheck(name="llm", status="ok"))

    # Check 3: config catalog loaded
    config_ok = len(GUIDES_BY_ID) > 0
    checks.append(HealthCheck(name="guides", status="ok" if config_ok else "degraded"))
    if not config_ok:
        all_ok = False

    status = "ok" if all_ok else "degraded"
    return HealthResponse(status=status, ready=all_ok, checks=checks)


@app.get("/trees", response_model=TreesResponse)
async def trees():
    tree_list = [
        {"id": tid, "name": tdata.get("name", tid), "description": tdata.get("description", "")}
        for tid, tdata in TREES.items()
    ]
    return TreesResponse(trees=tree_list)


@app.post("/session/start", response_model=SessionStartResponse)
@limiter.limit(_rl_session)
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
@limiter.limit(_rl_respond)
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


# ─── Guide Catalog & Delivery ─────────────────────────────────────────────────


@app.get("/guides/catalog")
async def guide_catalog():
    """Return the full guide catalog with domains and clusters."""
    return {
        "count": len(GUIDES_BY_ID),
        "guides": list(GUIDES_BY_ID.values()),
        "domains": {d: len(gs) for d, gs in GUIDES_BY_DOMAIN.items()},
    }


@app.get("/guides/{guide_id}")
async def get_guide(guide_id: str, audience: str = Query("general-mental-health", max_length=50)):
    """Serve a guide's markdown content, with optional audience-specific variant."""
    if guide_id not in GUIDES_BY_ID:
        raise HTTPException(status_code=404, detail=f"Guide not found: {guide_id}")

    path = resolve_guide_path(guide_id, audience)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Guide file not found on disk")

    content = path.read_text(encoding="utf-8")
    guide_meta = GUIDES_BY_ID[guide_id]
    return {
        "guide_id": guide_id,
        "title": guide_meta["title"],
        "domain": guide_meta["domain"],
        "cluster": guide_meta.get("cluster"),
        "audience": audience,
        "content": content,
    }


# ─── Audience Buckets ─────────────────────────────────────────────────────────


@app.get("/audience/buckets")
async def audience_buckets():
    """Return available audience buckets and matching questions."""
    return {
        "count": len(AUDIENCE_BUCKETS),
        "buckets": list(AUDIENCE_BUCKETS.values()),
        "questions": AUDIENCE_QUESTIONS,
    }


# ─── Products & Pricing ──────────────────────────────────────────────────────


@app.get("/products")
async def products():
    """Return the product catalog with active pricing."""
    profile = PRICING_PROFILES.get(ACTIVE_PRICING, {})
    enriched = []
    for pid, pdata in PRODUCTS_BY_ID.items():
        price_info = profile.get(pdata.get("pricingProfileKey", pid), {})
        enriched.append({
            **pdata,
            "price": price_info.get("price"),
            "billing": price_info.get("billing", "one_time"),
        })
    return {
        "pricing_profile": ACTIVE_PRICING,
        "products": enriched,
    }


# ─── Audience Resolution ─────────────────────────────────────────────────────


@app.post("/audience/resolve")
@limiter.limit(_rl_respond)
async def resolve_audience(request: Request):
    """Set the audience bucket for a completed session and return updated outcome."""
    body = await request.json()
    session_id = body.get("session_id")
    audience_bucket = body.get("audience_bucket", "general-mental-health")

    if not session_id:
        raise HTTPException(status_code=422, detail="session_id required")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update audience on the session and persist
    session.audience_bucket = audience_bucket
    _save_session(session)

    # Return the updated outcome with new audience-specific guide URL
    outcome = session.outcome
    if not outcome:
        raise HTTPException(status_code=409, detail="Session not complete")

    primary_topic = (outcome.matched_topics or ["general"])[0]
    guide = get_guide_for_topic(primary_topic)
    guide_id = guide["guide_id"] if guide else None
    offer = get_offer_for_guide(guide_id, outcome.band) if guide_id else get_offer_for_risk(outcome.band)

    return {
        "session_id": session_id,
        "audience_bucket": audience_bucket,
        "guide_url": f"/guides/{guide_id}?audience={audience_bucket}" if guide_id else None,
        "etsy_url": offer.get("etsy_url"),
        "offer": offer,
    }


# ─── Recommendation (config-driven) ──────────────────────────────────────────


@app.post("/recommend")
@limiter.limit(_rl_recommend)
async def recommend(request: Request):
    """Generate a config-driven recommendation from session outcome."""
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id required")

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_complete or not session.outcome:
        raise HTTPException(status_code=409, detail="Session not complete")

    outcome = session.outcome
    primary_topic = (outcome.matched_topics or ["general"])[0]
    audience = outcome.audience_bucket or "general-mental-health"

    guide = get_guide_for_topic(primary_topic)
    offer = get_offer_for_guide(guide["guide_id"], outcome.band) if guide else get_offer_for_risk(outcome.band)

    guide_path = None
    if guide:
        resolved = resolve_guide_path(guide["guide_id"], audience)
        guide_path = str(resolved) if resolved else None

    return {
        "session_id": session_id,
        "band": outcome.band,
        "topic": primary_topic,
        "audience_bucket": audience,
        "guide": {
            "guide_id": guide["guide_id"] if guide else None,
            "title": guide["title"] if guide else None,
            "domain": guide["domain"] if guide else None,
            "url": f"/guides/{guide['guide_id']}?audience={audience}" if guide else None,
            "file_exists": guide_path is not None,
        },
        "offer": offer,
        "crisis_resources": [r.dict() for r in outcome.crisis_resources] if outcome.crisis_resources else None,
    }


# ─── Therapist Finder ─────────────────────────────────────────────────────────

# Map chatbot topic → Psychology Today category slug
TOPIC_TO_PT_CATEGORY = {
    "relationship": "relationship-issues",
    "loneliness":   "depression",      # "loneliness" is sparse on PT; depression has broad coverage
    "anxiety":      "anxiety",
    "work":         "stress",
    "loss":         "grief",
    "family":       "depression",          # family-conflicts slug has no JSON-LD on PT
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
@limiter.limit(os.environ.get("RL_THERAPIST", "20/minute"))
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


@app.get("/session/{session_id}/recommendation")
async def session_recommendation(session_id: str):
    """Cody-compatible recommendation shape from a completed CCE session.

    Returns the exact fields expected by POST /api/quiz/recommendation
    so Cody's Stripe/fulfillment layer can consume it directly.
    """
    import uuid as _uuid

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_complete or not session.outcome:
        raise HTTPException(status_code=409, detail="Session not complete")

    outcome = session.outcome
    primary_topic = (outcome.matched_topics or ["general"])[0]
    audience = outcome.audience_bucket or "general-mental-health"

    guide = get_guide_for_topic(primary_topic)
    guide_id = guide["guide_id"] if guide else None
    guide_title = guide["title"] if guide else None

    offer = get_offer_for_guide(guide_id, outcome.band) if guide_id else get_offer_for_risk(outcome.band)

    variant_path = None
    if guide_id:
        resolved = resolve_guide_path(guide_id, audience)
        variant_path = str(resolved) if resolved else None

    return {
        "guideRecommendationId": str(_uuid.uuid4()),
        "baseGuideId": guide_id,
        "baseGuideTitle": guide_title,
        "audienceBucketId": audience,
        "audienceVariantPath": variant_path,
        "primaryOfferId": offer.get("product_id", "guide"),
        "secondaryOfferId": offer.get("secondary_offer", "sms"),
        "bundleRole": offer.get("bundle_role", "practical_support"),
        "showCrisisResources": outcome.band in ("high_risk", "critical"),
        "whyMatched": {
            "riskLevel": outcome.band,
            "topic": outcome.matched_topics or [],
            "audience": [audience],
            "offer": [offer.get("label", offer.get("product_id", "guide"))],
        },
    }


# ─── Admin: Metrics ────────────────────────────────────────────────────────────

_ADMIN_KEY = os.environ.get("CCE_ADMIN_KEY", "")


@app.get("/admin/metrics")
async def admin_metrics(request: Request):
    """Return internal usage metrics. Protected by CCE_ADMIN_KEY when set."""
    if _ADMIN_KEY:
        import hmac
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, _ADMIN_KEY):
            raise HTTPException(status_code=401, detail="Unauthorized")
    return metrics.snapshot()


@app.get("/admin/llm-usage")
async def admin_llm_usage(request: Request):
    """Return focused LLM token and cost telemetry."""
    if _ADMIN_KEY:
        import hmac
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, _ADMIN_KEY):
            raise HTTPException(status_code=401, detail="Unauthorized")
    return metrics.llm_usage_snapshot()


@app.get("/admin/llm-headroom")
async def admin_llm_headroom(request: Request):
    """Return current LLM budget headroom and warning levels."""
    if _ADMIN_KEY:
        import hmac
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, _ADMIN_KEY):
            raise HTTPException(status_code=401, detail="Unauthorized")
    return metrics.llm_headroom_snapshot()


@app.get("/admin/llm-alerts")
async def admin_llm_alerts(request: Request, min_level: str = "warning"):
    """Return actionable LLM budget alerts (warning/critical by default)."""
    if _ADMIN_KEY:
        import hmac
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, _ADMIN_KEY):
            raise HTTPException(status_code=401, detail="Unauthorized")
    return metrics.llm_alerts_snapshot(min_level=min_level)


@app.post("/admin/llm-alerts/sms")
async def admin_llm_alerts_sms(request: Request, min_level: str = "warning", force: bool = False):
    """Send actionable LLM budget alerts by SMS through Twilio."""
    if _ADMIN_KEY:
        import hmac
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, _ADMIN_KEY):
            raise HTTPException(status_code=401, detail="Unauthorized")

    result = alerting.send_llm_alerts_sms(min_level=min_level, force=force)
    if not result.get("ok", False):
        raise HTTPException(status_code=502, detail=result)
    return result


# ─── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _on_startup():
    alerting.start_sms_alert_scheduler()

@app.on_event("shutdown")
async def _on_shutdown():
    alerting.stop_sms_alert_scheduler()
    metrics.flush_to_disk()
