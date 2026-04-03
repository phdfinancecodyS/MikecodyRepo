import {
  api,
  type RiskLevel,
  type ProductId,
  type ScoreQuizResponse,
  type TopicMatchResponse,
  type AudienceMatchResponse,
  type RecommendationResponse,
} from './api';

export const CRISIS_RESOURCES = [
  { label: '988 Suicide & Crisis Lifeline', action: 'call', value: '988', description: 'Call or text 988 anytime, 24/7' },
  { label: 'Crisis Text Line', action: 'text', value: 'TEXT HOME TO 741741', description: 'Text HOME to 741741, free, 24/7' },
  { label: 'Emergency Services', action: 'call', value: '911', description: 'If you are in immediate danger, call 911' },
] as const;

export interface QuizFlowInput {
  lead?: { email?: string; phone?: string; firstName?: string };
  answersByQuestion: Record<string, number>;
  topicAnswers?: { tm_q1?: string; tm_q2?: string; tm_q3?: string[] };
  audienceIds?: { identityBucketIds?: string[]; contextBucketIds?: string[]; primaryBucketId?: string };
  utm?: { source?: string; medium?: string; campaign?: string; content?: string; term?: string };
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
  step: QuizFlowStep;
  riskLevel: RiskLevel;
  totalScore: number;
  leadId: string;
  quizSessionId: string;
  isCritical: boolean;
  crisisResources: typeof CRISIS_RESOURCES;
  topicMatch: TopicMatchResponse | null;
  audienceMatch: AudienceMatchResponse | null;
  recommendation: RecommendationResponse | null;
  guideTitle: string | null;
  primaryOfferId: ProductId | null;
  secondaryOfferId: ProductId | null;
  checkout: (productId: ProductId) => Promise<void>;
  errorMessage: string | null;
}

export async function runQuizFlow(input: QuizFlowInput): Promise<QuizFlowResult> {
  let scoreData: ScoreQuizResponse | null = null;
  let topicMatchData: TopicMatchResponse | null = null;
  let audienceData: AudienceMatchResponse | null = null;
  let recommendationData: RecommendationResponse | null = null;
  let errorMessage: string | null = null;
  let currentStep: QuizFlowStep = 'scoring';

  const buildResult = (): QuizFlowResult => {
    const riskLevel = scoreData?.riskLevel ?? 'low_risk';
    const isCritical = riskLevel === 'critical';
    const leadId = scoreData?.leadId ?? '';
    const quizSessionId = scoreData?.quizSessionId ?? '';

    return {
      step: currentStep,
      riskLevel,
      totalScore: scoreData?.totalScore ?? 0,
      leadId,
      quizSessionId,
      isCritical,
      crisisResources: CRISIS_RESOURCES,
      topicMatch: topicMatchData,
      audienceMatch: audienceData,
      recommendation: recommendationData,
      guideTitle: recommendationData?.baseGuideTitle ?? null,
      primaryOfferId: recommendationData?.primaryOfferId ?? null,
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
          guideId: recommendationData.baseGuideId,
          audienceBucketId: recommendationData.audienceBucketId,
          successUrl: input.successUrl,
          cancelUrl: input.cancelUrl,
        });

        window.location.href = stripeCheckoutUrl;
      },
    };
  };

  try {
    currentStep = 'scoring';
    scoreData = await api.scoreQuiz({
      lead: input.lead,
      answersByQuestion: input.answersByQuestion,
      utm: input.utm,
    });

    api.trackEvent({
      sessionId: scoreData.quizSessionId,
      eventName: 'quiz_scored',
      payload: {
        riskLevel: scoreData.riskLevel,
        totalScore: scoreData.totalScore,
        ...input.utm,
      },
    });
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : String(error);
    currentStep = 'error';
    return buildResult();
  }

  if (scoreData.riskLevel === 'critical') {
    api.recommendation({ quizSessionId: scoreData.quizSessionId }).catch(() => null);
    currentStep = 'complete';
    return buildResult();
  }

  if (scoreData.allowTopicMatcher && input.topicAnswers) {
    try {
      currentStep = 'topic_match';
      topicMatchData = await api.topicMatch({
        quizSessionId: scoreData.quizSessionId,
        answers: input.topicAnswers,
      });

      api.trackEvent({
        sessionId: scoreData.quizSessionId,
        eventName: 'topic_matcher_completed',
        payload: {
          matchedDomain: topicMatchData.matchedDomain,
          recommendedGuideIds: topicMatchData.recommendedGuideIds,
          recommendedOfferType: topicMatchData.recommendedOfferType,
        },
      });
    } catch (error) {
      console.warn('[quiz-flow] topic-match failed', error);
      topicMatchData = null;
    }
  }

  if (scoreData.allowAudienceMatcher && input.audienceIds) {
    try {
      currentStep = 'audience_match';
      audienceData = await api.audienceMatch({
        quizSessionId: scoreData.quizSessionId,
        identityBucketIds: input.audienceIds.identityBucketIds,
        contextBucketIds: input.audienceIds.contextBucketIds,
        primaryBucketId: input.audienceIds.primaryBucketId,
      });
    } catch (error) {
      console.warn('[quiz-flow] audience-match failed', error);
      audienceData = null;
    }
  }

  try {
    currentStep = 'recommendation';
    recommendationData = await api.recommendation({
      quizSessionId: scoreData.quizSessionId,
      topicMatchSessionId: topicMatchData?.topicMatchSessionId,
      audienceMatchSessionId: audienceData?.audienceMatchSessionId,
    });

    api.trackEvent({
      sessionId: scoreData.quizSessionId,
      eventName: 'recommendation_viewed',
      payload: {
        baseGuideId: recommendationData.baseGuideId,
        primaryOfferId: recommendationData.primaryOfferId,
        riskLevel: scoreData.riskLevel,
      },
    });
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : String(error);
    currentStep = 'error';
    return buildResult();
  }

  currentStep = 'complete';
  return buildResult();
}

export async function launchCheckout(
  result: QuizFlowResult,
  productId: ProductId,
): Promise<void> {
  return result.checkout(productId);
}