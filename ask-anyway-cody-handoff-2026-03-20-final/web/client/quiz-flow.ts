// ─────────────────────────────────────────────────────────────────────────────
// web/client/quiz-flow.ts
// Sequential quiz flow orchestrator.
// Calls all 7 endpoints in the correct order and surfaces a typed result
// that frontend pages can render directly.
//
// Usage (React example):
//
//   import { runQuizFlow, QuizFlowResult } from '@/lib/quiz-flow';
//
//   const result = await runQuizFlow({
//     lead:             { email, phone, firstName },
//     answersByQuestion: { q1: 2, q2: 1, … q10: 0 },
//     topicAnswers:     { tm_q1: 'calm_nervous_system', tm_q2: 'cant_sleep_overthink', tm_q3: ['step_by_step_plan'] },
//     audienceIds:      { identityBucketIds: ['veteran'], contextBucketIds: ['parent'] },
//     utm:              { source: 'tiktok', medium: 'social' },
//     successUrl:       window.location.origin + '/thank-you',
//     cancelUrl:        window.location.origin + '/quiz',
//   });
//
// ─────────────────────────────────────────────────────────────────────────────

import {
  api,
  type RiskLevel,
  type ProductId,
  type ScoreQuizResponse,
  type TopicMatchResponse,
  type AudienceMatchResponse,
  type RecommendationResponse,
} from './api';

// ─────────────────────────────────────────────────────────────────────────────
// Crisis resources — shown immediately for 'critical' results.
// Review with Mike (LCSW) before launch.
// ─────────────────────────────────────────────────────────────────────────────
export const CRISIS_RESOURCES = [
  { label: '988 Suicide & Crisis Lifeline', action: 'call', value: '988', description: 'Call or text 988 anytime, 24/7' },
  { label: 'Crisis Text Line', action: 'text', value: 'TEXT HOME TO 741741', description: 'Text HOME to 741741 — free, 24/7' },
  { label: 'Emergency Services', action: 'call', value: '911', description: 'If you are in immediate danger, call 911' },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Input / output types
// ─────────────────────────────────────────────────────────────────────────────

export interface QuizFlowInput {
  /** Lead contact info — only email/phone are stored; never required upfront. */
  lead?: { email?: string; phone?: string; firstName?: string };
  /** Answers to all 10 quiz questions. Keys: 'q1'…'q10', values: 0–3. */
  answersByQuestion: Record<string, number>;
  /** Answers to the 3 post-quiz topic matcher questions. */
  topicAnswers?: { tm_q1?: string; tm_q2?: string; tm_q3?: string[] };
  /** Audience/identity bucket selections from the audience matcher. */
  audienceIds?: { identityBucketIds?: string[]; contextBucketIds?: string[]; primaryBucketId?: string };
  /** UTM params passed from the landing URL. */
  utm?: { source?: string; medium?: string; campaign?: string; content?: string; term?: string };
  /** Stripe success/cancel return URLs. */
  successUrl: string;
  cancelUrl: string;
}

export type QuizFlowStep =
  | 'scoring'
  | 'topic_match'
  | 'audience_match'
  | 'recommendation'
  | 'complete'
  | 'error';

export interface QuizFlowResult {
  /** Current pipeline step — 'complete' on success, 'error' on failure. */
  step: QuizFlowStep;

  // ── Always present ──────────────────────────────────────────────────────
  riskLevel: RiskLevel;
  totalScore: number;
  leadId: string;
  quizSessionId: string;

  // ── Critical fast-path — populated when riskLevel === 'critical' ────────
  isCritical: boolean;
  /** Show these resources immediately. Never gate behind purchase. */
  crisisResources: typeof CRISIS_RESOURCES;

  // ── Standard path — populated for non-critical results ─────────────────
  topicMatch:    TopicMatchResponse   | null;
  audienceMatch: AudienceMatchResponse | null;
  recommendation: RecommendationResponse | null;

  // ── Convenience fields resolved from recommendation ─────────────────────
  guideTitle:      string | null;
  primaryOfferId:  ProductId | null;
  secondaryOfferId: ProductId | null;

  // ── Pre-built checkout launcher ─────────────────────────────────────────
  /**
   * Call this to redirect the user to Stripe Checkout for a given product.
   * Fires the checkout/session route and redirects to stripeCheckoutUrl.
   */
  checkout: (productId: ProductId) => Promise<void>;

  // ── Error info ──────────────────────────────────────────────────────────
  errorMessage: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Main orchestrator
// ─────────────────────────────────────────────────────────────────────────────

export async function runQuizFlow(input: QuizFlowInput): Promise<QuizFlowResult> {
  // Shared mutable state across steps
  let scoreData: ScoreQuizResponse | null = null;
  let topicMatchData: TopicMatchResponse | null = null;
  let audienceData: AudienceMatchResponse | null = null;
  let recommendationData: RecommendationResponse | null = null;
  let errorMessage: string | null = null;
  let currentStep: QuizFlowStep = 'scoring';

  // Helper to build the final result object from current state
  const buildResult = (): QuizFlowResult => {
    const riskLevel  = scoreData?.riskLevel ?? 'low_risk';
    const isCritical = riskLevel === 'critical';
    const leadId     = scoreData?.leadId ?? '';
    const quizSessionId = scoreData?.quizSessionId ?? '';

    return {
      step:          currentStep,
      riskLevel,
      totalScore:    scoreData?.totalScore ?? 0,
      leadId,
      quizSessionId,
      isCritical,
      crisisResources: CRISIS_RESOURCES,
      topicMatch:      topicMatchData,
      audienceMatch:   audienceData,
      recommendation:  recommendationData,
      guideTitle:      recommendationData?.baseGuideTitle ?? null,
      primaryOfferId:  recommendationData?.primaryOfferId ?? null,
      secondaryOfferId: recommendationData?.secondaryOfferId ?? null,
      errorMessage,

      checkout: async (productId: ProductId) => {
        if (!recommendationData || !leadId || !quizSessionId) {
          throw new Error('Cannot open checkout before recommendation is resolved');
        }
        api.trackEvent({
          sessionId: quizSessionId,
          eventName: 'product_cta_clicked',
          payload: { productId, location: 'results_screen' },
        });
        const { stripeCheckoutUrl } = await api.checkoutSession({
          leadId,
          quizSessionId,
          guideRecommendationId: recommendationData.guideRecommendationId,
          productId,
          guideId:         recommendationData.baseGuideId,
          audienceBucketId: recommendationData.audienceBucketId,
          successUrl: input.successUrl,
          cancelUrl:  input.cancelUrl,
        });
        window.location.href = stripeCheckoutUrl;
      },
    };
  };

  // ── Step 1: Score the quiz ───────────────────────────────────────────────
  try {
    currentStep = 'scoring';
    scoreData = await api.scoreQuiz({
      lead:             input.lead,
      answersByQuestion: input.answersByQuestion,
      utm:              input.utm,
    });

    api.trackEvent({
      sessionId: scoreData.quizSessionId,
      eventName:  'quiz_scored',
      payload: {
        riskLevel:  scoreData.riskLevel,
        totalScore: scoreData.totalScore,
        ...input.utm,
      },
    });
  } catch (err) {
    errorMessage = err instanceof Error ? err.message : String(err);
    currentStep  = 'error';
    return buildResult();
  }

  // ── Critical fast-path ───────────────────────────────────────────────────
  // For critical results: show crisis resources immediately.
  // Still call /recommendation so a DB record is persisted — but never
  // show paid offers above the fold or block crisis resources behind capture.
  if (scoreData.riskLevel === 'critical') {
    // Persist a recommendation record in the background (no await)
    api.recommendation({ quizSessionId: scoreData.quizSessionId }).catch(() => null);

    currentStep = 'complete';
    return buildResult();
  }

  // ── Step 2: Topic matcher (if allowed) ──────────────────────────────────
  if (scoreData.allowTopicMatcher && input.topicAnswers) {
    try {
      currentStep = 'topic_match';
      topicMatchData = await api.topicMatch({
        quizSessionId: scoreData.quizSessionId,
        answers:       input.topicAnswers,
      });

      api.trackEvent({
        sessionId: scoreData.quizSessionId,
        eventName:  'topic_matcher_completed',
        payload: {
          matchedDomain:       topicMatchData.matchedDomain,
          recommendedGuideIds: topicMatchData.recommendedGuideIds,
          recommendedOfferType: topicMatchData.recommendedOfferType,
        },
      });
    } catch (err) {
      // Non-fatal: log and continue without topic match
      console.warn('[quiz-flow] topic-match failed', err);
      topicMatchData = null;
    }
  }

  // ── Step 3: Audience matcher (if allowed) ────────────────────────────────
  if (scoreData.allowAudienceMatcher && input.audienceIds) {
    try {
      currentStep = 'audience_match';
      audienceData = await api.audienceMatch({
        quizSessionId:    scoreData.quizSessionId,
        identityBucketIds: input.audienceIds.identityBucketIds,
        contextBucketIds:  input.audienceIds.contextBucketIds,
        primaryBucketId:   input.audienceIds.primaryBucketId,
      });
    } catch (err) {
      console.warn('[quiz-flow] audience-match failed', err);
      audienceData = null;
    }
  }

  // ── Step 4: Final recommendation ─────────────────────────────────────────
  try {
    currentStep = 'recommendation';
    recommendationData = await api.recommendation({
      quizSessionId:         scoreData.quizSessionId,
      topicMatchSessionId:   topicMatchData?.topicMatchSessionId,
      audienceMatchSessionId: audienceData?.audienceMatchSessionId,
    });

    api.trackEvent({
      sessionId: scoreData.quizSessionId,
      eventName:  'recommendation_viewed',
      payload: {
        baseGuideId:    recommendationData.baseGuideId,
        primaryOfferId: recommendationData.primaryOfferId,
        riskLevel:      scoreData.riskLevel,
      },
    });
  } catch (err) {
    errorMessage = err instanceof Error ? err.message : String(err);
    currentStep  = 'error';
    return buildResult();
  }

  currentStep = 'complete';
  return buildResult();
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience helper — call after user makes an explicit offer selection
// without going through the full flow again.
// ─────────────────────────────────────────────────────────────────────────────
export async function launchCheckout(
  result: QuizFlowResult,
  productId: ProductId,
): Promise<void> {
  return result.checkout(productId);
}
