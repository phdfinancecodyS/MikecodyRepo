from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


# ─── Request Models ────────────────────────────────────────────────

class StartRequest(BaseModel):
    tree_id: str = "main-flow"


class RespondRequest(BaseModel):
    option_id: Optional[str] = None
    message: Optional[str] = None


# ─── Prompt / Response Pieces ──────────────────────────────────────

class PromptOption(BaseModel):
    id: str
    text: str


class Prompt(BaseModel):
    question: str
    type: str                           # "choice" | "free_text"
    options: Optional[List[PromptOption]] = None


# ─── Policy Notice ─────────────────────────────────────────────────

class PolicyNotice(BaseModel):
    message: str = (
        "I\u2019m here to offer psychoeducational support \u2014 information and resources "
        "to help you understand what you\u2019re going through. I\u2019m not able to provide "
        "a clinical diagnosis or treatment plan. For that, please connect with a "
        "licensed mental health professional."
    )


# ─── Clarification ─────────────────────────────────────────────────

class Clarification(BaseModel):
    text: str
    options: List[PromptOption]


# ─── Outcome ───────────────────────────────────────────────────────

class GuideItem(BaseModel):
    title: str
    price: Optional[float] = None
    url: Optional[str] = None
    description: Optional[str] = None


class CrisisResource(BaseModel):
    name: str
    contact: str
    available: str


class Outcome(BaseModel):
    band: str                                      # low_risk | moderate_risk | high_risk | critical
    summary: str
    disclaimer: str
    next_step: str
    matched_topics: List[str] = Field(default_factory=list)
    audience_bucket: Optional[str] = None
    matched_guide_id: Optional[str] = None
    free_resource: Optional[GuideItem] = None
    upsell: List[GuideItem] = Field(default_factory=list)
    crisis_resources: Optional[List[CrisisResource]] = None
    offer: Optional[Dict[str, Any]] = None


# ─── Session State (internal) ──────────────────────────────────────

class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tree_id: str = "main-flow"
    current_step: str = ""
    history: List[Dict[str, Any]] = Field(default_factory=list)
    scores: Dict[str, int] = Field(default_factory=dict)
    total_score: int = 0
    detected_topics: List[str] = Field(default_factory=list)
    sentiment: str = "neutral"           # positive | neutral | negative
    is_crisis: bool = False
    is_complete: bool = False
    outcome: Optional[Outcome] = None
    awaiting_clarification: bool = False
    clarification_options: Optional[List[PromptOption]] = None
    safety_screener_active: bool = False
    audience_bucket: Optional[str] = None
    audience_overlay_buckets: List[str] = Field(default_factory=list)
    audience_matching_active: bool = False
    meds_redirect_active: bool = False


# ─── API Responses ─────────────────────────────────────────────────

class SessionStartResponse(BaseModel):
    session_id: str
    current_prompt: Prompt
    status: str = "in_progress"


class RespondResponse(BaseModel):
    status: str                          # in_progress | needs_clarification | complete
    next_prompt: Optional[Prompt] = None
    clarification: Optional[Clarification] = None
    outcome: Optional[Outcome] = None
    policy_notice: Optional[PolicyNotice] = None


class HealthCheck(BaseModel):
    name: str
    status: str  # "ok" | "degraded" | "down"

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    ready: bool = True
    checks: List[HealthCheck] = []


class TreeInfo(BaseModel):
    id: str
    name: str
    description: str


class TreesResponse(BaseModel):
    trees: List[TreeInfo]
