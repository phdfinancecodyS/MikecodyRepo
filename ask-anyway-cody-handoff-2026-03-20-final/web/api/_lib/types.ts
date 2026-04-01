// ─────────────────────────────────────────────────────────────────────────────
// Shared TypeScript types for the quiz platform API handlers.
// Derived from: planning/BACKEND-SYSTEM-CONTRACT.md
//               supabase/migrations/20260320153000_backend_architecture.sql
//               quiz/api-contracts.json
// ─────────────────────────────────────────────────────────────────────────────

// ── Risk levels ───────────────────────────────────────────────────────────────

export type RiskLevel = 'low_risk' | 'moderate_risk' | 'high_risk' | 'critical';

// ── Product / offer ids ───────────────────────────────────────────────────────

export type ProductId =
  | 'guide'
  | 'kit'
  | 'sms'
  | 'bundle'
  | 'free_crisis_resources';

// ── Fulfillment states ────────────────────────────────────────────────────────

export type FulfillmentStatus =
  | 'pending'
  | 'processing'
  | 'fulfilled'
  | 'failed'
  | 'canceled';

// ── POST /api/quiz/score ──────────────────────────────────────────────────────

export interface ScoreQuizRequest {
  lead?: {
    id?: string;
    email?: string;
    phone?: string;
    firstName?: string;
  };
  answersByQuestion: Record<string, number>; // { q1: 0-3, q2: 0-3, … q10: 0-3 }
  quizVersion?: string;
  landingPath?: string;
  utm?: {
    source?: string;
    medium?: string;
    campaign?: string;
    content?: string;
    term?: string;
  };
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

// ── POST /api/quiz/topic-match ────────────────────────────────────────────────

export interface TopicMatchRequest {
  quizSessionId: string;
  matcherVersion?: string;
  answers: {
    tm_q1?: string;
    tm_q2?: string;
    tm_q3?: string[];
  };
}

export interface TopicMatchResponse {
  topicMatchSessionId: string;
  matchedDomain: string;
  recommendedGuideIds: string[];
  recommendedOfferType: ProductId;
  whyMatched: string[];
}

// ── POST /api/quiz/audience-match ─────────────────────────────────────────────

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

// ── POST /api/quiz/recommendation ─────────────────────────────────────────────

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

// ── POST /api/checkout/session ────────────────────────────────────────────────

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

// ── POST /api/analytics/event ─────────────────────────────────────────────────

export interface AnalyticsEventRequest {
  sessionId: string;
  eventName: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
}
