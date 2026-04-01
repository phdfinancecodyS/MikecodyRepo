// POST /api/quiz/score
// Scores quiz answers, assigns risk level, persists lead and quiz_session.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 1

import { createSupabaseServerClient } from '../../_lib/supabase';
import { scoreQuiz, validateAnswers } from '../../_lib/scorer';
import type { ScoreQuizRequest, ScoreQuizResponse } from '../../_lib/types';

// Risk rules from quiz/recommendation-routing-config.json
const RISK_RULES: Record<
  string,
  { allowTopicMatcher: boolean; allowAudienceMatcher: boolean; showCrisisResources: boolean }
> = {
  low_risk:      { allowTopicMatcher: true,  allowAudienceMatcher: true,  showCrisisResources: true  },
  moderate_risk: { allowTopicMatcher: true,  allowAudienceMatcher: true,  showCrisisResources: true  },
  high_risk:     { allowTopicMatcher: true,  allowAudienceMatcher: true,  showCrisisResources: true  },
  critical:      { allowTopicMatcher: false, allowAudienceMatcher: false, showCrisisResources: true  },
};

export async function POST(req: Request): Promise<Response> {
  let body: ScoreQuizRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  // Validate answers
  const answerError = validateAnswers(body.answersByQuestion);
  if (answerError) {
    return Response.json({ error: answerError }, { status: 400 });
  }

  const { totalScore, riskLevel, overrideTriggered } = scoreQuiz(body.answersByQuestion);
  const rules = RISK_RULES[riskLevel];

  const db = createSupabaseServerClient();

  // ── Upsert lead ────────────────────────────────────────────────────────────
  let leadId: string = body.lead?.id ?? '';

  if (!leadId) {
    const leadUpsert = await db
      .from('leads')
      .upsert(
        {
          email:          body.lead?.email   ?? null,
          phone:          body.lead?.phone   ?? null,
          first_name:     body.lead?.firstName ?? null,
          utm_source:     body.utm?.source   ?? null,
          utm_medium:     body.utm?.medium   ?? null,
          utm_campaign:   body.utm?.campaign ?? null,
          utm_content:    body.utm?.content  ?? null,
          utm_term:       body.utm?.term     ?? null,
        },
        { onConflict: 'email', ignoreDuplicates: false }
      )
      .select('id')
      .single();

    if (leadUpsert.error) {
      console.error('leads upsert error', leadUpsert.error);
      return Response.json({ error: 'Failed to save lead' }, { status: 500 });
    }
    leadId = leadUpsert.data.id;
  }

  // ── Persist quiz_session ───────────────────────────────────────────────────
  const sessionInsert = await db
    .from('quiz_sessions')
    .insert({
      lead_id:                leadId || null,
      total_score:            totalScore,
      risk_level:             riskLevel,
      override_triggered:     overrideTriggered,
      answers_by_question_json: body.answersByQuestion,
      quiz_version:           body.quizVersion ?? null,
      landing_path:           body.landingPath ?? null,
      completed_at:           new Date().toISOString(),
    })
    .select('id')
    .single();

  if (sessionInsert.error) {
    console.error('quiz_sessions insert error', sessionInsert.error);
    return Response.json({ error: 'Failed to save session' }, { status: 500 });
  }

  const quizSessionId: string = sessionInsert.data.id;

  const response: ScoreQuizResponse = {
    leadId,
    quizSessionId,
    totalScore,
    riskLevel,
    overrideTriggered,
    resultScreenId: riskLevel,
    allowTopicMatcher:   rules.allowTopicMatcher,
    allowAudienceMatcher: rules.allowAudienceMatcher,
    showCrisisResources: rules.showCrisisResources,
  };

  return Response.json(response, { status: 200 });
}
