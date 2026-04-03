'use client';

import { useState, useEffect, useCallback, useTransition } from 'react';
import { runQuizFlow, CRISIS_RESOURCES, type QuizFlowResult } from '../../client/quiz-flow';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type AnswerValue = 0 | 1 | 2 | 3;

type QuizQuestion = {
  id: string;
  category: string;
  prompt: string;
  options: { label: string; score: AnswerValue }[];
};

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = 'ask-anyway-quiz-progress';

const riskQuestions: QuizQuestion[] = [
  {
    id: 'q1', category: 'Mood',
    prompt: 'Over the past two weeks, how would you describe your overall mood?',
    options: [
      { label: 'I feel good more days than not', score: 0 },
      { label: 'I feel okay, but flat or numb some days', score: 1 },
      { label: 'I feel down or empty most days', score: 2 },
      { label: 'I feel hopeless or dark almost all the time', score: 3 },
    ],
  },
  {
    id: 'q2', category: 'Sleep',
    prompt: 'How have your sleep patterns been lately?',
    options: [
      { label: 'I sleep pretty well and wake up rested', score: 0 },
      { label: 'I have some nights of bad sleep, but it evens out', score: 1 },
      { label: 'I am sleeping way less than usual or oversleeping most days', score: 2 },
      { label: 'My sleep is completely disrupted', score: 3 },
    ],
  },
  {
    id: 'q3', category: 'Stress',
    prompt: 'How stressed or overwhelmed do you feel about your daily life right now?',
    options: [
      { label: 'I am managing my stress okay', score: 0 },
      { label: 'I feel stressed, but I can usually handle it', score: 1 },
      { label: 'I feel overwhelmed a lot and struggling to cope', score: 2 },
      { label: 'I feel completely overwhelmed and can barely function', score: 3 },
    ],
  },
  {
    id: 'q4', category: 'Connection',
    prompt: 'How connected do you feel to the people in your life?',
    options: [
      { label: 'I have people I can talk to and I feel supported', score: 0 },
      { label: 'I have some close people, but sometimes feel lonely', score: 1 },
      { label: 'I feel pretty isolated and disconnected from others', score: 2 },
      { label: 'I feel completely alone', score: 3 },
    ],
  },
  {
    id: 'q5', category: 'Safety',
    prompt: 'In the past two weeks, have you had thoughts about hurting yourself or that you would be better off dead?',
    options: [
      { label: 'No, not at all', score: 0 },
      { label: 'I have had a fleeting thought, but it did not stick', score: 1 },
      { label: 'I have had these thoughts regularly and they are hard to shake', score: 2 },
      { label: 'I think about it constantly and have a plan', score: 3 },
    ],
  },
  {
    id: 'q6', category: 'Substance Use',
    prompt: 'How have you been using alcohol, drugs, or other substances to cope?',
    options: [
      { label: 'I do not use them, or I use them rarely and socially', score: 0 },
      { label: 'I use them occasionally to unwind', score: 1 },
      { label: 'I am using more than usual to numb or escape', score: 2 },
      { label: 'I am dependent on substances to get through the day', score: 3 },
    ],
  },
  {
    id: 'q7', category: 'Functioning',
    prompt: 'How are you functioning at work, school, or with daily responsibilities?',
    options: [
      { label: 'I am managing well and keeping up', score: 0 },
      { label: 'I am keeping up, but it takes more effort than usual', score: 1 },
      { label: 'I am falling behind or avoiding responsibilities', score: 2 },
      { label: 'I have basically stopped doing what I need to do', score: 3 },
    ],
  },
  {
    id: 'q8', category: 'Withdrawal',
    prompt: 'Have you been withdrawing from activities or people you normally enjoy?',
    options: [
      { label: 'I am doing things I enjoy and seeing people', score: 0 },
      { label: 'I am doing less than usual, but still getting out sometimes', score: 1 },
      { label: 'I have withdrawn quite a bit from activities and people', score: 2 },
      { label: 'I do not want to see anyone or do anything', score: 3 },
    ],
  },
  {
    id: 'q9', category: 'Energy',
    prompt: 'How is your energy and motivation been?',
    options: [
      { label: 'I have decent energy and feel motivated most days', score: 0 },
      { label: 'Some days I am tired, but I push through okay', score: 1 },
      { label: 'I feel exhausted a lot, even after rest', score: 2 },
      { label: 'I have no energy or motivation', score: 3 },
    ],
  },
  {
    id: 'q10', category: 'Hope',
    prompt: 'When you think about the future, how do you feel?',
    options: [
      { label: 'I feel hopeful or at least accepting about what is ahead', score: 0 },
      { label: 'I have some worry about the future, but mostly feel okay', score: 1 },
      { label: 'I feel uncertain or pessimistic about the future', score: 2 },
      { label: 'I feel hopeless and do not believe things will get better', score: 3 },
    ],
  },
];

const topicQuestionOne = [
  ['calm_nervous_system', 'Calm my mind/body and stop spiraling'],
  ['improve_relationships', 'Handle conflict at home and communicate better'],
  ['process_moral_pain', 'Work through guilt, shame, or moral injury'],
  ['rebuild_identity', 'Rebuild purpose, identity, and connection'],
  ['break_habit_loops', 'Break coping habits I feel stuck in'],
] as const;

const topicQuestionTwo = [
  ['short_fuse_numb', 'Short fuse, then shut down, then regret'],
  ['cant_sleep_overthink', 'Cannot switch off, bad sleep, wired and tired'],
  ['relationship_minefield', 'Home feels tense and conversations go sideways'],
  ['isolated_purpose', 'I feel alone and disconnected from purpose'],
  ['numbing_coping', 'I keep numbing out with habits or substances'],
] as const;

const topicQuestionThree = [
  ['better_conversations', 'Better conversations this week'],
  ['step_by_step_plan', 'A step-by-step plan for hard moments'],
  ['weekly_accountability', 'Weekly check-ins so I do not drift'],
  ['all_in_one', 'Give me the full stack and keep it simple'],
] as const;

const audienceOptions = [
  { id: 'christian', label: 'Christian', group: 'identity' },
  { id: 'military-veteran', label: 'Military / Veteran', group: 'identity' },
  { id: 'first-responder', label: 'First Responder', group: 'identity' },
  { id: 'lgbtq', label: 'LGBTQ+', group: 'identity' },
  { id: 'neurodivergent', label: 'Neurodivergent', group: 'identity' },
  { id: 'bipoc-racial-trauma', label: 'BIPOC / Racial Trauma', group: 'identity' },
  { id: 'young-adult-gen-z', label: 'Young Adult / Gen Z', group: 'identity' },
  { id: 'single-parent', label: 'Single Parent', group: 'context' },
  { id: 'healthcare-workers', label: 'Healthcare Workers', group: 'context' },
  { id: 'educators', label: 'Educators', group: 'context' },
  { id: 'social-workers-counselors', label: 'Social Workers / Counselors', group: 'context' },
  { id: 'high-stress-jobs', label: 'High Stress Jobs', group: 'context' },
  { id: 'addiction-recovery', label: 'Addiction / Recovery', group: 'context' },
  { id: 'grief-loss', label: 'Grief / Loss', group: 'context' },
  { id: 'chronic-illness-chronic-pain', label: 'Chronic Illness / Chronic Pain', group: 'context' },
  { id: 'faith-beyond-christian', label: 'Faith Beyond Christian', group: 'context' },
  { id: 'general-mental-health', label: 'Keep it general', group: 'fallback' },
] as const;

const offerLabels: Record<string, { label: string; description: string }> = {
  guide: { label: 'Get the Guide', description: 'Your matched topic guide ($9)' },
  kit: { label: 'Get the Kit', description: 'Guide + worksheets + audio ($19)' },
  sms: { label: 'Start Check On Me', description: 'Weekly SMS check-ins ($4.99/mo)' },
  bundle: { label: 'Get the Bundle', description: 'Guide + Kit + Check On Me ($34)' },
  free_crisis_resources: { label: 'View Crisis Resources', description: 'Free, immediate support' },
};

/* ------------------------------------------------------------------ */
/*  Wizard steps                                                       */
/* ------------------------------------------------------------------ */

type WizardStep =
  | { kind: 'risk'; index: number }
  | { kind: 'topic1' }
  | { kind: 'topic2' }
  | { kind: 'topic3' }
  | { kind: 'audience' }
  | { kind: 'contact' }
  | { kind: 'submitting' }
  | { kind: 'results' };

const TOTAL_RISK_QUESTIONS = riskQuestions.length;
const TOTAL_POST_QUIZ_STEPS = 4; // topic1, topic2, topic3, audience
const TOTAL_STEPS = TOTAL_RISK_QUESTIONS + TOTAL_POST_QUIZ_STEPS + 1; // +1 for contact

function stepNumber(step: WizardStep): number {
  switch (step.kind) {
    case 'risk': return step.index;
    case 'topic1': return TOTAL_RISK_QUESTIONS;
    case 'topic2': return TOTAL_RISK_QUESTIONS + 1;
    case 'topic3': return TOTAL_RISK_QUESTIONS + 2;
    case 'audience': return TOTAL_RISK_QUESTIONS + 3;
    case 'contact': return TOTAL_RISK_QUESTIONS + 4;
    case 'submitting':
    case 'results': return TOTAL_STEPS;
  }
}

/* ------------------------------------------------------------------ */
/*  Persistence helpers                                                */
/* ------------------------------------------------------------------ */

interface SavedProgress {
  answers: Record<string, AnswerValue | null>;
  topicQ1: string;
  topicQ2: string;
  topicQ3: string[];
  audienceBucket: string;
  firstName: string;
  email: string;
  phone: string;
  stepKind: string;
  stepIndex?: number;
}

function saveProgress(data: SavedProgress) {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch { /* quota */ }
}

function loadProgress(): SavedProgress | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) as SavedProgress : null;
  } catch { return null; }
}

function clearProgress() {
  try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
}

/* ------------------------------------------------------------------ */
/*  Audience payload builder                                           */
/* ------------------------------------------------------------------ */

function buildAudiencePayload(bucketId: string) {
  if (!bucketId || bucketId === 'general-mental-health') return undefined;
  const bucket = audienceOptions.find((o) => o.id === bucketId);
  if (!bucket) return undefined;
  return bucket.group === 'identity'
    ? { identityBucketIds: [bucketId] }
    : { contextBucketIds: [bucketId] };
}

/* ------------------------------------------------------------------ */
/*  CrisisBar (always visible)                                         */
/* ------------------------------------------------------------------ */

function CrisisBar() {
  return (
    <aside className="notice warning" style={{ marginBottom: 20 }}>
      <div className="section-label">Need immediate help?</div>
      <ul className="crisis-list">
        <li><a href="tel:988">Call or text 988</a> (24/7)</li>
        <li><a href="sms:741741&body=HOME">Text HOME to 741741</a> (24/7)</li>
        <li><a href="tel:911">Call 911</a> for emergencies</li>
      </ul>
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export default function QuizPage() {
  const [step, setStep] = useState<WizardStep>({ kind: 'risk', index: 0 });
  const [answers, setAnswers] = useState<Record<string, AnswerValue | null>>(
    Object.fromEntries(riskQuestions.map((q) => [q.id, null])),
  );
  const [topicQ1, setTopicQ1] = useState('');
  const [topicQ2, setTopicQ2] = useState('');
  const [topicQ3, setTopicQ3] = useState<string[]>([]);
  const [audienceBucket, setAudienceBucket] = useState('general-mental-health');
  const [firstName, setFirstName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [result, setResult] = useState<QuizFlowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  /* ---- Restore saved progress on mount ---- */
  useEffect(() => {
    const saved = loadProgress();
    if (!saved) return;
    setAnswers(saved.answers as Record<string, AnswerValue | null>);
    setTopicQ1(saved.topicQ1);
    setTopicQ2(saved.topicQ2);
    setTopicQ3(saved.topicQ3);
    setAudienceBucket(saved.audienceBucket);
    setFirstName(saved.firstName);
    setEmail(saved.email);
    setPhone(saved.phone);
    if (saved.stepKind === 'risk') {
      setStep({ kind: 'risk', index: saved.stepIndex ?? 0 });
    } else if (['topic1', 'topic2', 'topic3', 'audience', 'contact'].includes(saved.stepKind)) {
      setStep({ kind: saved.stepKind as 'topic1' | 'topic2' | 'topic3' | 'audience' | 'contact' });
    }
  }, []);

  /* ---- Persist on every state change ---- */
  useEffect(() => {
    if (step.kind === 'results' || step.kind === 'submitting') return;
    saveProgress({
      answers, topicQ1, topicQ2, topicQ3, audienceBucket,
      firstName, email, phone,
      stepKind: step.kind,
      stepIndex: step.kind === 'risk' ? step.index : undefined,
    });
  }, [step, answers, topicQ1, topicQ2, topicQ3, audienceBucket, firstName, email, phone]);

  const progress = step.kind === 'results' || step.kind === 'submitting'
    ? 100
    : (stepNumber(step) / TOTAL_STEPS) * 100;

  /* ---- Navigation ---- */
  const goBack = useCallback(() => {
    if (step.kind === 'risk' && step.index > 0) {
      setStep({ kind: 'risk', index: step.index - 1 });
    } else if (step.kind === 'topic1') {
      setStep({ kind: 'risk', index: TOTAL_RISK_QUESTIONS - 1 });
    } else if (step.kind === 'topic2') {
      setStep({ kind: 'topic1' });
    } else if (step.kind === 'topic3') {
      setStep({ kind: 'topic2' });
    } else if (step.kind === 'audience') {
      setStep({ kind: 'topic3' });
    } else if (step.kind === 'contact') {
      setStep({ kind: 'audience' });
    }
  }, [step]);

  const goNext = useCallback(() => {
    if (step.kind === 'risk' && step.index < TOTAL_RISK_QUESTIONS - 1) {
      setStep({ kind: 'risk', index: step.index + 1 });
    } else if (step.kind === 'risk' && step.index === TOTAL_RISK_QUESTIONS - 1) {
      setStep({ kind: 'topic1' });
    } else if (step.kind === 'topic1') {
      setStep({ kind: 'topic2' });
    } else if (step.kind === 'topic2') {
      setStep({ kind: 'topic3' });
    } else if (step.kind === 'topic3') {
      setStep({ kind: 'audience' });
    } else if (step.kind === 'audience') {
      setStep({ kind: 'contact' });
    }
  }, [step]);

  /* ---- Answer handler with auto-advance ---- */
  function selectRiskAnswer(questionId: string, value: AnswerValue) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
    setTimeout(() => {
      setStep((current) => {
        if (current.kind === 'risk' && current.index < TOTAL_RISK_QUESTIONS - 1) {
          return { kind: 'risk', index: current.index + 1 };
        }
        if (current.kind === 'risk' && current.index === TOTAL_RISK_QUESTIONS - 1) {
          return { kind: 'topic1' };
        }
        return current;
      });
    }, 350);
  }

  /* ---- Topic Q3 toggle ---- */
  function toggleOutcome(id: string) {
    setTopicQ3((cur) => {
      if (cur.includes(id)) return cur.filter((v) => v !== id);
      if (cur.length >= 2) return [cur[1], id];
      return [...cur, id];
    });
  }

  /* ---- Submit ---- */
  function submitQuiz() {
    setError(null);
    setStep({ kind: 'submitting' });

    const answersByQuestion = Object.fromEntries(
      Object.entries(answers).map(([k, v]) => [k, v ?? 0]),
    ) as Record<string, number>;

    startTransition(async () => {
      try {
        const flowResult = await runQuizFlow({
          lead: {
            email: email || undefined,
            phone: phone || undefined,
            firstName: firstName || undefined,
          },
          answersByQuestion,
          topicAnswers: topicQ1
            ? { tm_q1: topicQ1, tm_q2: topicQ2, tm_q3: topicQ3 }
            : undefined,
          audienceIds: buildAudiencePayload(audienceBucket),
          successUrl: `${window.location.origin}/quiz?checkout=success`,
          cancelUrl: `${window.location.origin}/quiz?checkout=cancelled`,
        });

        setResult(flowResult);
        if (flowResult.step === 'error') {
          setError(flowResult.errorMessage ?? 'Something went wrong.');
        }
        setStep({ kind: 'results' });
        clearProgress();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setStep({ kind: 'contact' });
      }
    });
  }

  /* ================================================================ */
  /*  Render                                                           */
  /* ================================================================ */

  return (
    <main className="shell">
      {/* ---- Progress bar ---- */}
      <div className="progress" style={{ marginBottom: 16 }}>
        <span style={{ width: `${progress}%`, transition: 'width 0.3s ease' }} />
      </div>

      <CrisisBar />

      {/* ================================================================ */}
      {/*  RISK QUESTIONS                                                   */}
      {/* ================================================================ */}
      {step.kind === 'risk' && (() => {
        const q = riskQuestions[step.index];
        return (
          <section className="question-card" style={{ maxWidth: 640, margin: '0 auto' }}>
            <div className="question-head">
              <div>
                <div className="pill">Question {step.index + 1} of {TOTAL_RISK_QUESTIONS}</div>
                <h3 style={{ marginTop: 12 }}>{q.prompt}</h3>
              </div>
              <div className="muted">{q.category}</div>
            </div>
            <div className="choice-list">
              {q.options.map((opt) => {
                const selected = answers[q.id] === opt.score;
                return (
                  <button
                    key={opt.label}
                    type="button"
                    className="choice"
                    onClick={() => selectRiskAnswer(q.id, opt.score)}
                    style={{
                      cursor: 'pointer',
                      border: selected ? '2px solid var(--accent)' : undefined,
                      background: selected ? 'var(--accent-soft)' : undefined,
                      textAlign: 'left',
                    }}
                  >
                    <span><strong>{opt.label}</strong></span>
                  </button>
                );
              })}
            </div>
            <div className="inline-actions" style={{ marginTop: 16, justifyContent: 'space-between' }}>
              <button className="btn secondary" type="button" disabled={step.index === 0} onClick={goBack}>
                Back
              </button>
              <button
                className="btn"
                type="button"
                disabled={answers[q.id] === null}
                onClick={goNext}
              >
                {step.index === TOTAL_RISK_QUESTIONS - 1 ? 'Next: topic matcher' : 'Next'}
              </button>
            </div>
          </section>
        );
      })()}

      {/* ================================================================ */}
      {/*  TOPIC MATCHER Q1                                                 */}
      {/* ================================================================ */}
      {step.kind === 'topic1' && (
        <section className="question-card" style={{ maxWidth: 640, margin: '0 auto' }}>
          <div className="question-head">
            <div>
              <div className="pill">Topic Matcher 1 of 3</div>
              <h3 style={{ marginTop: 12 }}>What do you need most right now?</h3>
            </div>
          </div>
          <div className="choice-list">
            {topicQuestionOne.map(([value, label]) => (
              <button
                key={value}
                type="button"
                className="choice"
                onClick={() => { setTopicQ1(value); setTimeout(() => setStep({ kind: 'topic2' }), 300); }}
                style={{
                  cursor: 'pointer', textAlign: 'left',
                  border: topicQ1 === value ? '2px solid var(--accent)' : undefined,
                  background: topicQ1 === value ? 'var(--accent-soft)' : undefined,
                }}
              >
                <span><strong>{label}</strong></span>
              </button>
            ))}
          </div>
          <div className="inline-actions" style={{ marginTop: 16, justifyContent: 'space-between' }}>
            <button className="btn secondary" type="button" onClick={goBack}>Back</button>
            <button className="btn" type="button" disabled={!topicQ1} onClick={goNext}>Next</button>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/*  TOPIC MATCHER Q2                                                 */}
      {/* ================================================================ */}
      {step.kind === 'topic2' && (
        <section className="question-card" style={{ maxWidth: 640, margin: '0 auto' }}>
          <div className="question-head">
            <div>
              <div className="pill">Topic Matcher 2 of 3</div>
              <h3 style={{ marginTop: 12 }}>Which situation sounds most like your week?</h3>
            </div>
          </div>
          <div className="choice-list">
            {topicQuestionTwo.map(([value, label]) => (
              <button
                key={value}
                type="button"
                className="choice"
                onClick={() => { setTopicQ2(value); setTimeout(() => setStep({ kind: 'topic3' }), 300); }}
                style={{
                  cursor: 'pointer', textAlign: 'left',
                  border: topicQ2 === value ? '2px solid var(--accent)' : undefined,
                  background: topicQ2 === value ? 'var(--accent-soft)' : undefined,
                }}
              >
                <span><strong>{label}</strong></span>
              </button>
            ))}
          </div>
          <div className="inline-actions" style={{ marginTop: 16, justifyContent: 'space-between' }}>
            <button className="btn secondary" type="button" onClick={goBack}>Back</button>
            <button className="btn" type="button" disabled={!topicQ2} onClick={goNext}>Next</button>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/*  TOPIC MATCHER Q3 (multi-select)                                  */}
      {/* ================================================================ */}
      {step.kind === 'topic3' && (
        <section className="question-card" style={{ maxWidth: 640, margin: '0 auto' }}>
          <div className="question-head">
            <div>
              <div className="pill">Topic Matcher 3 of 3</div>
              <h3 style={{ marginTop: 12 }}>Pick up to 2 outcomes you want next</h3>
            </div>
          </div>
          <div className="choice-list">
            {topicQuestionThree.map(([value, label]) => (
              <label className="choice" key={value} style={{
                cursor: 'pointer',
                border: topicQ3.includes(value) ? '2px solid var(--accent)' : undefined,
                background: topicQ3.includes(value) ? 'var(--accent-soft)' : undefined,
              }}>
                <input
                  type="checkbox"
                  checked={topicQ3.includes(value)}
                  onChange={() => toggleOutcome(value)}
                />
                <span><strong>{label}</strong></span>
              </label>
            ))}
          </div>
          <div className="inline-actions" style={{ marginTop: 16, justifyContent: 'space-between' }}>
            <button className="btn secondary" type="button" onClick={goBack}>Back</button>
            <button className="btn" type="button" disabled={topicQ3.length === 0} onClick={goNext}>Next</button>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/*  AUDIENCE PICKER                                                  */}
      {/* ================================================================ */}
      {step.kind === 'audience' && (
        <section className="question-card" style={{ maxWidth: 640, margin: '0 auto' }}>
          <div className="question-head">
            <div>
              <div className="pill">Audience Lens</div>
              <h3 style={{ marginTop: 12 }}>Which lens should your guide feel written for?</h3>
              <p className="muted" style={{ marginTop: 6 }}>Pick whichever fits best, or keep it general.</p>
            </div>
          </div>
          <div className="choice-list">
            {audienceOptions.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className="choice"
                onClick={() => { setAudienceBucket(opt.id); setTimeout(() => setStep({ kind: 'contact' }), 300); }}
                style={{
                  cursor: 'pointer', textAlign: 'left',
                  border: audienceBucket === opt.id ? '2px solid var(--accent)' : undefined,
                  background: audienceBucket === opt.id ? 'var(--accent-soft)' : undefined,
                }}
              >
                <span><strong>{opt.label}</strong></span>
              </button>
            ))}
          </div>
          <div className="inline-actions" style={{ marginTop: 16, justifyContent: 'space-between' }}>
            <button className="btn secondary" type="button" onClick={goBack}>Back</button>
            <button className="btn" type="button" onClick={goNext}>Next</button>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/*  CONTACT CAPTURE                                                  */}
      {/* ================================================================ */}
      {step.kind === 'contact' && (
        <section className="question-card" style={{ maxWidth: 480, margin: '0 auto' }}>
          <div className="question-head">
            <div>
              <div className="pill">Almost done</div>
              <h3 style={{ marginTop: 12 }}>Where should we send your results?</h3>
              <p className="muted" style={{ marginTop: 6 }}>
                Optional. We will never spam you. Skip if you prefer.
              </p>
            </div>
          </div>
          <div className="stack" style={{ marginTop: 12 }}>
            <div>
              <label className="field-label" htmlFor="firstName">First name</label>
              <input className="input" id="firstName" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div>
              <label className="field-label" htmlFor="email">Email</label>
              <input className="input" id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="field-label" htmlFor="phone">Phone (for Check On Me SMS)</label>
              <input className="input" id="phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>
          <div className="inline-actions" style={{ marginTop: 20, justifyContent: 'space-between' }}>
            <button className="btn secondary" type="button" onClick={goBack}>Back</button>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn secondary" type="button" onClick={submitQuiz}>Skip</button>
              <button className="btn" type="button" onClick={submitQuiz}>See My Results</button>
            </div>
          </div>
        </section>
      )}

      {/* ================================================================ */}
      {/*  SUBMITTING                                                       */}
      {/* ================================================================ */}
      {step.kind === 'submitting' && (
        <section className="question-card" style={{ maxWidth: 480, margin: '0 auto', textAlign: 'center', padding: 48 }}>
          <div className="pill">Scoring your check-in...</div>
          <p className="muted" style={{ marginTop: 16 }}>Finding your matched guide and building your recommendation.</p>
        </section>
      )}

      {/* ================================================================ */}
      {/*  RESULTS                                                          */}
      {/* ================================================================ */}
      {step.kind === 'results' && result && (
        <ResultsScreen result={result} error={error} onRestart={() => {
          clearProgress();
          setResult(null);
          setError(null);
          setAnswers(Object.fromEntries(riskQuestions.map((q) => [q.id, null])));
          setTopicQ1('');
          setTopicQ2('');
          setTopicQ3([]);
          setAudienceBucket('general-mental-health');
          setFirstName('');
          setEmail('');
          setPhone('');
          setStep({ kind: 'risk', index: 0 });
        }} />
      )}

      {/* ---- Error fallback (non-results) ---- */}
      {error && step.kind !== 'results' && (
        <div className="notice danger" style={{ maxWidth: 640, margin: '16px auto' }}>
          <p>{error}</p>
        </div>
      )}

      <p className="footer-note" style={{ textAlign: 'center' }}>
        This check-in is educational, not therapy or diagnosis. Crisis resources are always available above.
      </p>
    </main>
  );
}

/* ================================================================== */
/*  Results Screen                                                     */
/* ================================================================== */

function ResultsScreen({
  result,
  error,
  onRestart,
}: {
  result: QuizFlowResult;
  error: string | null;
  onRestart: () => void;
}) {
  const isCritical = result.isCritical;
  const isHigh = result.riskLevel === 'high_risk';

  return (
    <section className="result-grid" style={{ maxWidth: 640, margin: '0 auto' }}>
      {/* ---- CRITICAL: crisis resources FIRST ---- */}
      {isCritical && (
        <article className="notice danger" style={{ borderRadius: 'var(--radius)' }}>
          <div className="section-label" style={{ background: 'var(--danger-soft)', color: 'var(--danger)' }}>
            You are not alone
          </div>
          <p style={{ marginTop: 12, fontSize: '1.05rem', color: 'var(--ink)' }}>
            Your answers suggest you may be in crisis right now.
            Please reach out to someone who can help immediately.
          </p>
          <ul className="crisis-list" style={{ marginTop: 12 }}>
            {CRISIS_RESOURCES.map((r) => (
              <li key={r.label} style={{ marginBottom: 8 }}>
                <strong>
                  {r.action === 'call'
                    ? <a href={`tel:${r.value}`}>{r.label}</a>
                    : <a href="sms:741741&body=HOME">{r.label}</a>}
                </strong>
                : {r.description}
              </li>
            ))}
          </ul>
        </article>
      )}

      {/* ---- Score card ---- */}
      <article className="result-card">
        <div className="section-label">Your Check-In Results</div>
        <div className="score-box" style={{ marginTop: 12 }}>
          <div className="score-number">{result.totalScore}</div>
          <div>
            <strong>{result.riskLevel.replace(/_/g, ' ')}</strong>
            <p>Session: {result.quizSessionId || 'pending'}</p>
          </div>
        </div>
      </article>

      {/* ---- HIGH RISK: crisis resources before offers ---- */}
      {isHigh && !isCritical && (
        <article className="notice warning" style={{ borderRadius: 'var(--radius)' }}>
          <div className="section-label">Support is here</div>
          <p style={{ marginTop: 8 }}>
            Your score puts you in a higher-risk range. These resources are free and available right now.
          </p>
          <ul className="crisis-list">
            {CRISIS_RESOURCES.map((r) => (
              <li key={r.label}>
                <strong>
                  {r.action === 'call'
                    ? <a href={`tel:${r.value}`}>{r.label}</a>
                    : <a href="sms:741741&body=HOME">{r.label}</a>}
                </strong>
                : {r.description}
              </li>
            ))}
          </ul>
        </article>
      )}

      {/* ---- Guide match ---- */}
      {result.recommendation && (
        <article className="result-card">
          <div className="section-label">Your Matched Guide</div>
          <h2 style={{ marginTop: 8 }}>{result.recommendation.baseGuideTitle}</h2>
          <p>{result.recommendation.audienceBucketId.replace(/-/g, ' ')} edition</p>
        </article>
      )}

      {/* ---- Offers (never shown for critical) ---- */}
      {!isCritical && result.recommendation && (
        <article className="result-card">
          <div className="section-label">Your Options</div>
          <div className="offer-grid" style={{ marginTop: 12 }}>
            {[result.primaryOfferId, result.secondaryOfferId].filter(Boolean).map((offerId) => {
              const info = offerLabels[offerId as string] ?? { label: offerId, description: '' };
              return (
                <div className="offer-card" key={offerId}>
                  <div>
                    <h4>{info.label}</h4>
                    <p>{info.description}</p>
                  </div>
                  <button
                    className="btn"
                    type="button"
                    onClick={() => result.checkout(offerId as 'guide' | 'kit' | 'sms' | 'bundle' | 'free_crisis_resources')}
                  >
                    Choose
                  </button>
                </div>
              );
            })}
          </div>
        </article>
      )}

      {/* ---- LOW/MODERATE: crisis resources at bottom ---- */}
      {!isCritical && !isHigh && (
        <article className="notice" style={{ borderRadius: 'var(--radius)' }}>
          <div className="section-label">Crisis Resources</div>
          <p style={{ marginTop: 8 }}>These are always available if you or someone you know needs help.</p>
          <ul className="crisis-list">
            {CRISIS_RESOURCES.map((r) => (
              <li key={r.label}>
                {r.action === 'call'
                  ? <a href={`tel:${r.value}`}>{r.label}</a>
                  : <a href="sms:741741&body=HOME">{r.label}</a>}
                : {r.description}
              </li>
            ))}
          </ul>
        </article>
      )}

      {error && (
        <div className="notice danger" style={{ borderRadius: 'var(--radius)' }}>
          <p>{error}</p>
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: 12 }}>
        <button className="btn secondary" type="button" onClick={onRestart}>Start Over</button>
      </div>
    </section>
  );
}
