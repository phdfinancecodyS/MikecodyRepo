// ─────────────────────────────────────────────────────────────────────────────
// web/client/api.ts
// Typed fetch wrappers for all 7 Ask Anyway API endpoints.
// Drop this file into your Next.js project's src/lib/ (or similar) folder.
// ─────────────────────────────────────────────────────────────────────────────

// ── Types (mirrored from web/api/_lib/types.ts) ───────────────────────────────

export type RiskLevel = 'low_risk' | 'moderate_risk' | 'high_risk' | 'critical';
export type ProductId = 'guide' | 'kit' | 'sms' | 'bundle' | 'free_crisis_resources';

export interface ScoreQuizRequest {
  lead?: { id?: string; email?: string; phone?: string; firstName?: string };
  answersByQuestion: Record<string, number>;
  quizVersion?: string;
  landingPath?: string;
  utm?: { source?: string; medium?: string; campaign?: string; content?: string; term?: string };
}

export interface ScoreQuizResponse {
  leadId: string;
  quizSessionId: string;
  totalScore: number;
  riskLevel: RiskLevel;
  overrideTriggered: boolean;
  resultScreenId: string;
  allowTopicMatcher: boolean;
  allowAudienceMatcher: boolean;
  showCrisisResources: boolean;
}

export interface TopicMatchRequest {
  quizSessionId: string;
  matcherVersion?: string;
  answers: { tm_q1?: string; tm_q2?: string; tm_q3?: string[] };
}

export interface TopicMatchResponse {
  topicMatchSessionId: string;
  matchedDomain: string;
  recommendedGuideIds: string[];
  recommendedOfferType: ProductId;
  whyMatched: string[];
}

export interface AudienceMatchRequest {
  quizSessionId: string;
  matcherVersion?: string;
  identityBucketIds?: string[];
  contextBucketIds?: string[];
  primaryBucketId?: string;
}

export interface AudienceMatchResponse {
  audienceMatchSessionId: string;
  selectedBucketIds: string[];
  primaryBucketId: string;
  overlayBucketIds: string[];
  fallbackUsed: boolean;
}

export interface RecommendationRequest {
  quizSessionId: string;
  topicMatchSessionId?: string;
  audienceMatchSessionId?: string;
}

export interface RecommendationResponse {
  guideRecommendationId: string;
  baseGuideId: string;
  baseGuideTitle: string;
  audienceBucketId: string;
  audienceVariantPath: string;
  primaryOfferId: ProductId;
  secondaryOfferId: ProductId | null;
  bundleRole: string | null;
  showCrisisResources: boolean;
  whyMatched: Record<string, unknown>;
}

export interface CheckoutSessionRequest {
  leadId: string;
  quizSessionId: string;
  guideRecommendationId: string;
  productId: ProductId;
  guideId: string;
  audienceBucketId: string;
  successUrl: string;
  cancelUrl: string;
}

export interface CheckoutSessionResponse {
  purchaseIntentId: string;
  stripeCheckoutUrl: string;
}

export interface AnalyticsEventRequest {
  sessionId: string;
  eventName: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
}

// ── Base fetch helper ─────────────────────────────────────────────────────────

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(path, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }

  return res.json() as Promise<TRes>;
}

// ── Endpoint wrappers ─────────────────────────────────────────────────────────

export const api = {
  /**
   * Score the 10-question quiz and persist a quiz_session.
   * Returns riskLevel + allowTopicMatcher + showCrisisResources.
   */
  scoreQuiz(req: ScoreQuizRequest): Promise<ScoreQuizResponse> {
    return post('/api/quiz/score', req);
  },

  /**
   * Run the 3-question post-quiz topic matcher.
   * Returns matchedDomain, recommendedGuideIds, recommendedOfferType.
   */
  topicMatch(req: TopicMatchRequest): Promise<TopicMatchResponse> {
    return post('/api/quiz/topic-match', req);
  },

  /**
   * Resolve the audience/identity bucket for personalised content.
   */
  audienceMatch(req: AudienceMatchRequest): Promise<AudienceMatchResponse> {
    return post('/api/quiz/audience-match', req);
  },

  /**
   * Combine topic + audience sessions into a final guide recommendation.
   */
  recommendation(req: RecommendationRequest): Promise<RecommendationResponse> {
    return post('/api/quiz/recommendation', req);
  },

  /**
   * Create a Stripe Checkout session for a specific product.
   * Returns the stripeCheckoutUrl to redirect or window.open.
   */
  checkoutSession(req: CheckoutSessionRequest): Promise<CheckoutSessionResponse> {
    return post('/api/checkout/session', req);
  },

  /**
   * Fire-and-forget analytics event. Never awaited in the UI critical path.
   */
  trackEvent(req: AnalyticsEventRequest): void {
    post('/api/analytics/event', req).catch((err) =>
      console.warn('[analytics] event failed', err),
    );
  },
};
