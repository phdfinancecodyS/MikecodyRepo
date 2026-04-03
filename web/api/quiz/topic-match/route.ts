// POST /api/quiz/topic-match
// Runs the topic matcher against the user's answers, resolves guide recommendations,
// and persists a topic_match_session row.
// Contract: planning/API-ROUTE-SPECS.md § Endpoint 2

import fs from 'fs';
import path from 'path';
import { createSupabaseServerClient } from '../../_lib/supabase';
import type { TopicMatchRequest, TopicMatchResponse, ProductId } from '../../_lib/types';

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

interface GuideEntry {
  guide_id: string;
  chapter_id?: string;
  domain: string;
}

interface BaseGuideCatalog {
  guides: GuideEntry[];
}

function resolveQuizDir(): string {
  const cwd = process.cwd();
  const candidates = [
    path.resolve(cwd, 'quiz'),
    path.resolve(cwd, '..', 'quiz'),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  throw new Error('Quiz config directory not found');
}

const QUIZ_DIR = resolveQuizDir();

const matcherFlow: MatcherFlow = JSON.parse(
  fs.readFileSync(path.join(QUIZ_DIR, 'topic-matcher-flow.json'), 'utf8'),
);

const topicCatalog: TopicCatalog = JSON.parse(
  fs.readFileSync(path.join(QUIZ_DIR, 'topic-catalog.json'), 'utf8'),
);

const baseGuideCatalog: BaseGuideCatalog = JSON.parse(
  fs.readFileSync(path.join(QUIZ_DIR, 'base-guide-catalog.json'), 'utf8'),
);

const GUIDES_BY_CHAPTER_ID = new Map<string, GuideEntry[]>(
  baseGuideCatalog.guides.reduce<Map<string, GuideEntry[]>>((map, guide) => {
    if (!guide.chapter_id) {
      return map;
    }
    const existing = map.get(guide.chapter_id) ?? [];
    existing.push(guide);
    map.set(guide.chapter_id, existing);
    return map;
  }, new Map()),
);

const DOMAIN_OFFER_MAP: Record<string, ProductId> = {
  nervous_system_mood_cognition: 'kit',
  sleep_body_pain_substances: 'kit',
  relationships_family_parenting: 'guide',
  intimacy_sex_connection: 'guide',
  moral_injury_guilt_shame_spirituality: 'kit',
  work_identity_transition: 'guide',
  dopamine_habits_addictions: 'kit',
};

function getQuestion(id: string): MatcherQuestion | undefined {
  return matcherFlow.questions.find((question) => question.id === id);
}

function getOption(questionId: string, optionId?: string): MatcherOption | undefined {
  if (!optionId) {
    return undefined;
  }

  return getQuestion(questionId)?.options.find((option) => option.id === optionId);
}

function resolveGuideId(topicId: string): string | null {
  const guides = GUIDES_BY_CHAPTER_ID.get(topicId);
  return guides?.[0]?.guide_id ?? null;
}

function matchDomain(answers: TopicMatchRequest['answers']): {
  domain: string;
  guideIds: string[];
  whyMatched: string[];
  offerType: ProductId;
} {
  const domainScores: Record<string, number> = {};
  const hintCounts: Record<string, number> = {};
  const hintedTopicIds: string[] = [];

  const q1Option = getOption('tm_q1', answers.tm_q1);
  if (q1Option?.weights) {
    for (const [domain, weight] of Object.entries(q1Option.weights)) {
      domainScores[domain] = (domainScores[domain] ?? 0) + weight;
    }
  }

  const q2Option = getOption('tm_q2', answers.tm_q2);
  if (q2Option?.topicHints) {
    for (const topicId of q2Option.topicHints) {
      hintedTopicIds.push(topicId);
      const topic = topicCatalog.topics.find((entry) => entry.id === topicId);
      if (!topic) {
        continue;
      }

      domainScores[topic.domain] = (domainScores[topic.domain] ?? 0) + 1;
      hintCounts[topic.domain] = (hintCounts[topic.domain] ?? 0) + 1;
    }
  }

  const fallbackDomain = q1Option?.weights
    ? Object.entries(q1Option.weights).sort((left, right) => right[1] - left[1])[0]?.[0]
    : 'nervous_system_mood_cognition';

  let domain = fallbackDomain;
  let topScore = Number.NEGATIVE_INFINITY;

  for (const [candidateDomain, score] of Object.entries(domainScores)) {
    const effectiveScore = score + (hintCounts[candidateDomain] ?? 0) * 0.01;
    if (effectiveScore > topScore) {
      topScore = effectiveScore;
      domain = candidateDomain;
    }
  }

  const domainTopics = topicCatalog.topics.filter((topic) => topic.domain === domain);
  const preferredTopicIds = [
    ...hintedTopicIds.filter((topicId) => domainTopics.some((topic) => topic.id === topicId)),
    ...domainTopics.map((topic) => topic.id),
  ];

  const seenGuideIds = new Set<string>();
  const guideIds = preferredTopicIds
    .map(resolveGuideId)
    .filter((guideId): guideId is string => Boolean(guideId))
    .filter((guideId) => {
      if (seenGuideIds.has(guideId)) {
        return false;
      }
      seenGuideIds.add(guideId);
      return true;
    })
    .slice(0, 3);

  let offerType: ProductId = DOMAIN_OFFER_MAP[domain] ?? 'guide';

  const q3Question = getQuestion('tm_q3');
  if (answers.tm_q3?.length && q3Question) {
    const biases = answers.tm_q3
      .map((optionId) => q3Question.options.find((option) => option.id === optionId)?.offerBias)
      .filter((bias): bias is string => Boolean(bias));

    if (biases.length === 1) {
      offerType = biases[0] as ProductId;
    } else if (biases.length > 1) {
      if (biases.every((bias) => bias === biases[0])) {
        offerType = biases[0] as ProductId;
      } else if (biases.includes('bundle')) {
        offerType = 'bundle';
      } else {
        const priority: ProductId[] = ['bundle', 'sms', 'kit', 'guide'];
        offerType = priority.find((productId) => biases.includes(productId)) ?? offerType;
      }
    }
  }

  const whyMatched: string[] = [];
  if (q1Option) {
    whyMatched.push(`You prioritized: ${q1Option.label}`);
  }
  if (q2Option) {
    whyMatched.push(`Your week sounds like: ${q2Option.label}`);
  }
  if (answers.tm_q3?.length && q3Question) {
    const labels = answers.tm_q3
      .map((optionId) => q3Question.options.find((option) => option.id === optionId)?.label ?? optionId)
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

  if (!getOption('tm_q1', body.answers?.tm_q1)) {
    return Response.json({ error: 'tm_q1 must match quiz/topic-matcher-flow.json' }, { status: 400 });
  }

  if (!getOption('tm_q2', body.answers?.tm_q2)) {
    return Response.json({ error: 'tm_q2 must match quiz/topic-matcher-flow.json' }, { status: 400 });
  }

  // Validate tm_q3 selection limit (max 2)
  if (body.answers?.tm_q3 && body.answers.tm_q3.length > 2) {
    return Response.json({ error: 'Maximum 2 selections allowed for tm_q3' }, { status: 400 });
  }

  if (body.answers?.tm_q3?.some((optionId) => !getOption('tm_q3', optionId))) {
    return Response.json({ error: 'tm_q3 selections must match quiz/topic-matcher-flow.json' }, { status: 400 });
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
