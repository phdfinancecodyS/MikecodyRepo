// POST /api/quiz/topic-match
// Runs the topic matcher against the user's answers, resolves guide recommendations,
// and persists a topic_match_session row.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 2

import fs from 'fs';
import path from 'path';
import { createSupabaseServerClient } from '../../_lib/supabase';
import type { TopicMatchRequest, TopicMatchResponse, ProductId } from '../../_lib/types';

// ─────────────────────────────────────────────────────────────────────────────
// Load configs once at module initialisation
// ─────────────────────────────────────────────────────────────────────────────
const QUIZ_DIR = path.resolve(process.cwd(), 'quiz');

interface MatcherOption {
  id: string;
  label: string;
  weights?: Record<string, number>;
  topicHints?: string[];
  offerBias?: string;
}

interface MatcherQuestion {
  id: string;
  type: string;
  options: MatcherOption[];
}

interface MatcherFlow {
  questions: MatcherQuestion[];
}

interface TopicEntry {
  id: string;
  domain: string;
  title: string;
  tags: string[];
}

interface TopicCatalog {
  topics: TopicEntry[];
}

const matcherFlow: MatcherFlow = JSON.parse(
  fs.readFileSync(path.join(QUIZ_DIR, 'topic-matcher-flow.json'), 'utf8'),
);

const topicCatalog: TopicCatalog = JSON.parse(
  fs.readFileSync(path.join(QUIZ_DIR, 'topic-catalog.json'), 'utf8'),
);

// ─────────────────────────────────────────────────────────────────────────────
// Domain-to-offer defaults — used when no tm_q3 offerBias is present.
// Derived from quiz/recommendation-routing-config.json riskRules and
// the actual domain names in quiz/topic-catalog.json.
// ─────────────────────────────────────────────────────────────────────────────
const DOMAIN_OFFER_MAP: Record<string, ProductId> = {
  nervous_system_mood_cognition:          'kit',
  sleep_body_pain_substances:             'kit',
  relationships_family_parenting:         'guide',
  intimacy_sex_connection:                'guide',
  moral_injury_guilt_shame_spirituality:  'kit',
  work_identity_transition:               'guide',
  dopamine_habits_addictions:             'kit',
};

// ─────────────────────────────────────────────────────────────────────────────
// Config-driven topic matcher
//
// Scoring method: weighted_plus_topic_hints (topic-matcher-flow.json)
//   1. tm_q1 option.weights   → add weight values to each domain's score
//   2. tm_q2 option.topicHints → each hint's domain gets +1; hints are pinned
//      for topic selection (tieBreaker: prefer_topic_hints_from_tm_q2)
//   3. Winning domain = highest score; hint count used for tie-breaking
//   4. Top-3 topics: hinted topics in winning domain first, then fill remainder
//   5. offerType derived from tm_q3 offerBias; falls back to DOMAIN_OFFER_MAP
// ─────────────────────────────────────────────────────────────────────────────
function matchDomain(answers: TopicMatchRequest['answers']): {
  domain: string;
  guideIds: string[];
  whyMatched: string[];
  offerType: ProductId;
} {
  const q1 = matcherFlow.questions.find(q => q.id === 'tm_q1');
  const q2 = matcherFlow.questions.find(q => q.id === 'tm_q2');
  const q3 = matcherFlow.questions.find(q => q.id === 'tm_q3');

  // ── Step 1: domain scores from tm_q1 weights ──────────────────────────────
  const domainScores: Record<string, number> = {};
  const domainHintCount: Record<string, number> = {};

  if (answers.tm_q1 && q1) {
    const opt = q1.options.find(o => o.id === answers.tm_q1);
    if (opt?.weights) {
      for (const [domain, weight] of Object.entries(opt.weights)) {
        domainScores[domain] = (domainScores[domain] ?? 0) + weight;
      }
    }
  }

  // ── Step 2: domain boost + hint pinning from tm_q2 topicHints ────────────
  const hintedTopicIds: string[] = [];

  if (answers.tm_q2 && q2) {
    const opt = q2.options.find(o => o.id === answers.tm_q2);
    if (opt?.topicHints) {
      for (const topicId of opt.topicHints) {
        hintedTopicIds.push(topicId);
        const topic = topicCatalog.topics.find(t => t.id === topicId);
        if (topic) {
          domainScores[topic.domain] = (domainScores[topic.domain] ?? 0) + 1;
          domainHintCount[topic.domain] = (domainHintCount[topic.domain] ?? 0) + 1;
        }
      }
    }
  }

  // ── Step 3: select winning domain ────────────────────────────────────────
  const DEFAULT_DOMAIN = 'nervous_system_mood_cognition';
  let domain = DEFAULT_DOMAIN;
  let maxScore = -1;

  for (const [d, score] of Object.entries(domainScores)) {
    const effectiveScore = score + (domainHintCount[d] ?? 0) * 0.01; // hint tiebreaker
    if (effectiveScore > maxScore) {
      maxScore = effectiveScore;
      domain = d;
    }
  }

  // ── Step 4: top-3 topics — hinted first, then fill from domain ───────────
  const domainTopics = topicCatalog.topics.filter(t => t.domain === domain);
  const hinted    = domainTopics.filter(t =>  hintedTopicIds.includes(t.id));
  const nonHinted = domainTopics.filter(t => !hintedTopicIds.includes(t.id));
  const guideIds  = [...hinted, ...nonHinted].slice(0, 3).map(t => t.id);

  // ── Step 5: offer type from tm_q3 offerBias ──────────────────────────────
  let offerType: ProductId = DOMAIN_OFFER_MAP[domain] ?? 'guide';

  if (answers.tm_q3?.length && q3) {
    const biases = answers.tm_q3
      .map(id => q3.options.find(o => o.id === id)?.offerBias)
      .filter(Boolean) as string[];

    if (biases.length === 1) {
      offerType = biases[0] as ProductId;
    } else if (biases.length === 2) {
      if (biases[0] === biases[1]) {
        offerType = biases[0] as ProductId;
      } else if (biases.includes('bundle') || biases.includes('all_in_one')) {
        offerType = 'bundle';
      } else {
        // mismatched biases: prefer the more comprehensive option
        const priority: ProductId[] = ['bundle', 'sms', 'kit', 'guide'];
        offerType = priority.find(p => biases.includes(p)) ?? offerType;
      }
    }
  }

  // ── Step 6: human-readable whyMatched ────────────────────────────────────
  const whyMatched: string[] = [];

  if (answers.tm_q1 && q1) {
    const opt = q1.options.find(o => o.id === answers.tm_q1);
    if (opt) whyMatched.push(`You prioritised: ${opt.label}`);
  }
  if (answers.tm_q2 && q2) {
    const opt = q2.options.find(o => o.id === answers.tm_q2);
    if (opt) whyMatched.push(`Your week sounds like: ${opt.label}`);
  }
  if (answers.tm_q3?.length && q3) {
    const labels = answers.tm_q3
      .map(id => q3.options.find(o => o.id === id)?.label ?? id)
      .join(' and ');
    whyMatched.push(`You want: ${labels}`);
  }

  return { domain, guideIds, whyMatched, offerType };
}

export async function POST(req: Request): Promise<Response> {
  let body: TopicMatchRequest;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  if (!body.quizSessionId) {
    return Response.json({ error: 'quizSessionId is required' }, { status: 400 });
  }

  // Validate tm_q3 selection limit (max 2)
  if (body.answers?.tm_q3 && body.answers.tm_q3.length > 2) {
    return Response.json({ error: 'Maximum 2 selections allowed for tm_q3' }, { status: 400 });
  }

  const db = createSupabaseServerClient();

  // Verify quiz_session exists
  const { data: session, error: sessionErr } = await db
    .from('quiz_sessions')
    .select('id')
    .eq('id', body.quizSessionId)
    .single();

  if (sessionErr || !session) {
    return Response.json({ error: 'quiz_session not found' }, { status: 404 });
  }

  const { domain, guideIds, whyMatched, offerType } = matchDomain(body.answers ?? {});

  // Persist topic_match_session
  const { data: matchSession, error: insertErr } = await db
    .from('topic_match_sessions')
    .insert({
      quiz_session_id:           body.quizSessionId,
      matcher_version:           body.matcherVersion ?? '1',
      tm_q1_option_id:           body.answers?.tm_q1 ?? null,
      tm_q2_option_id:           body.answers?.tm_q2 ?? null,
      tm_q3_option_ids_json:     body.answers?.tm_q3 ?? [],
      matched_domain:            domain,
      recommended_guide_ids_json: guideIds,
      recommended_offer_type:    offerType,
    })
    .select('id')
    .single();

  if (insertErr) {
    console.error('topic_match_sessions insert error', insertErr);
    return Response.json({ error: 'Failed to save topic match' }, { status: 500 });
  }

  const response: TopicMatchResponse = {
    topicMatchSessionId: matchSession.id,
    matchedDomain:       domain,
    recommendedGuideIds: guideIds,
    recommendedOfferType: offerType,
    whyMatched,
  };

  return Response.json(response, { status: 200 });
}
