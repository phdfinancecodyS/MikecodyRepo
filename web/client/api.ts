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

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(`API ${path} failed (${response.status}): ${text}`);
  }

  return response.json() as Promise<TRes>;
}

export const api = {
  scoreQuiz(request: ScoreQuizRequest): Promise<ScoreQuizResponse> {
    return post('/api/quiz/score', request);
  },

  topicMatch(request: TopicMatchRequest): Promise<TopicMatchResponse> {
    return post('/api/quiz/topic-match', request);
  },

  audienceMatch(request: AudienceMatchRequest): Promise<AudienceMatchResponse> {
    return post('/api/quiz/audience-match', request);
  },

  recommendation(request: RecommendationRequest): Promise<RecommendationResponse> {
    return post('/api/quiz/recommendation', request);
  },

  checkoutSession(request: CheckoutSessionRequest): Promise<CheckoutSessionResponse> {
    return post('/api/checkout/session', request);
  },

  trackEvent(request: AnalyticsEventRequest): void {
    post('/api/analytics/event', request).catch((error) =>
      console.warn('[analytics] event failed', error),
    );
  },
};