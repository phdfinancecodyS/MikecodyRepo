"""FastAPI application for the Clinical Conversation Engine."""
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
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
