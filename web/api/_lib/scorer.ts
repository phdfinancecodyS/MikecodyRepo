// ─────────────────────────────────────────────────────────────────────────────
// Quiz scoring logic.
// Source of truth: planning/QUIZ-IMPLEMENTATION-CONTRACT.md
// ─────────────────────────────────────────────────────────────────────────────

import type { RiskLevel } from './types';

export interface ScoreResult {
  totalScore: number;
  riskLevel: RiskLevel;
  overrideTriggered: boolean;
}

/**
 * Score a 10-question quiz where every answer is 0–3.
 * Applies two special-case overrides for question 5 (self-harm indicator).
 */
export function scoreQuiz(answersByQuestion: Record<string, number>): ScoreResult {
  const keys = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10'];

  let total = 0;
  for (const key of keys) {
    total += answersByQuestion[key] ?? 0;
  }

  const q5 = answersByQuestion['q5'] ?? 0;

  // Override: q5 = 3 → automatic critical regardless of total
  if (q5 === 3) {
    return { totalScore: total, riskLevel: 'critical', overrideTriggered: true };
  }

  // Override: q5 = 2 → bump total to at least 21 (minimum high_risk threshold)
  if (q5 === 2) {
    total = Math.max(total, 21);
  }

  let riskLevel: RiskLevel;
  if (total >= 26) {
    riskLevel = 'critical';
  } else if (total >= 21) {
    riskLevel = 'high_risk';
  } else if (total >= 11) {
    riskLevel = 'moderate_risk';
  } else {
    riskLevel = 'low_risk';
  }

  return { totalScore: total, riskLevel, overrideTriggered: false };
}

/**
 * Validate that answersByQuestion contains exactly 10 integer answers in 0–3.
 * Returns null on success, or an error string that should be returned as HTTP 400.
 */
export function validateAnswers(answers: unknown): string | null {
  const keys = ['q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10'];

  if (!answers || typeof answers !== 'object') {
    return 'answersByQuestion must be an object';
  }

  for (const key of keys) {
    const val = (answers as Record<string, unknown>)[key];
    if (val === undefined || val === null) {
      return `Missing answer for ${key}`;
    }
    if (!Number.isInteger(val) || (val as number) < 0 || (val as number) > 3) {
      return `Answer for ${key} must be an integer 0–3`;
    }
  }

  return null;
}
