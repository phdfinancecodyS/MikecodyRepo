# QUIZ LAUNCH: HANDOFF TO CODY + TECH CHECKLIST
**Prepared for:** Cody Sullivan (Tech + Business)  
**Prepared by:** [Your name] (Content + Mental Health)  
**Timeline:** Ready to hand off immediately

---

## WHAT'S READY FOR YOU (Your Content Input)

**All in:** `/planning/` and `/quiz/` folders on shared workspace

1. ✅ **Quiz Questions** (`quiz/quiz-questions.md`)
   - 10 questions, 0-3 scoring each
   - Total range: 0-30 points
   - Override logic included (if Q5=3, jump to CRITICAL)
   - Results routing (4 risk level pages defined)

2. ✅ **Landing Page Copy** (`landing-page/quiz-landing-page.md`)
   - Hero section + 8 conversion sections
   - Risk-segmented traffic versions
   - Email opt-in (optional pre-quiz)
   - Safety messaging, trust badges, A/B test versions

3. ✅ **Email + SMS Automation** (`email-sms/post-quiz-automations.md`)
   - 5 email sequences (one per risk level)
   - SMS check-in content (4 weeks + recurring)
   - Triggered on quiz score + SMS opt-in
   - All sequences prevent duplicates + include unsubscribe

4. ✅ **TikTok Promotion Calendar** (`marketing/tiktok-launch-calendar.md`)
   - 28-day Month 1 calendar (2 posts/day)
   - 8 video templates mapped to dates
   - Hashtag strategy + posting times
   - Week 5-8 (Month 2) growth strategy included

5. ✅ **Launch Playbook** (`planning/QUIZ-LAUNCH-PLAYBOOK.md`)
   - 14-day timeline to launch
   - Interdependencies between your work + tech work
   - Success metrics + launch checklist

6. ✅ **Audience + Backend Architecture Backbone**
  - `planning/AUDIENCE-SLANT-BACKBONE.md`
  - `planning/PLATFORM-ARCHITECTURE-BLUEPRINT.md`
  - `planning/BACKEND-SYSTEM-CONTRACT.md`
  - `planning/API-ROUTE-SPECS.md`
  - `supabase/migrations/20260320153000_backend_architecture.sql`
  - `supabase/migrations/20260320160000_rls_policies.sql`
  - `quiz/fulfillment-config.json`
  - `web/api/` (API handler scaffold  - Next.js App Router)
  - `web/api/README.md` (integration guide for the scaffold)
  - `quiz/audience-bucket-flow.json`
  - `quiz/base-guide-catalog.json`
  - `quiz/product-catalog.json`
  - `quiz/recommendation-routing-config.json`
  - `quiz/api-contracts.json`
  - `planning/GUIDE-OFFER-MAPPING.csv`
  - `planning/AUDIENCE-SLANT-MANIFEST.csv`

---

## WHAT YOU NEED TO BUILD (Tech Implementation Checklist)

### PHASE A: Quiz Infrastructure (Days 1-4)

Architecture update:
- The quiz is no longer only a score-to-result router.
- It now supports three backend stages after scoring: topic matching, audience matching, and recommendation resolution.
- Use `quiz/recommendation-routing-config.json` as the source of truth for routing decisions.

**Database Schema (Supabase):**

Do not build from the old MVP `users` table pattern.

Use these files as the only schema source of truth:
- `supabase/migrations/20260320153000_backend_architecture.sql`
- `planning/BACKEND-SYSTEM-CONTRACT.md`

Current core tables:
- `leads`
- `quiz_sessions`
- `topic_match_sessions`
- `audience_match_sessions`
- `guide_recommendations`
- `product_clicks`
- `purchases`
- `fulfillment_events`

Implementation rule:
- Apply the migration as written.
- Do not recreate parallel `users` or `quiz_responses` tables.
- Keep the API layer aligned to the persisted entities above.

**Backend API Surface:**

Use these files as the only route-contract source of truth:
- `planning/API-ROUTE-SPECS.md`
- `quiz/api-contracts.json`

Required routes:
- `POST /api/quiz/score`
- `POST /api/quiz/topic-match`
- `POST /api/quiz/audience-match`
- `POST /api/quiz/recommendation`
- `POST /api/checkout/session`
- `POST /api/webhooks/stripe`
- `POST /api/analytics/event`

Implementation rule:
- Do not ship a legacy single-step `POST /api/quiz` endpoint as the primary contract.
- The scoring route persists the quiz session first, then downstream matchers and recommendation routes resolve the rest of the stack.

**Scoring Logic (Backend):**

```javascript
function calculateQuizScore(responses) {
  let total = responses.reduce((sum, r) => sum + r.score, 0);
  
  // Override: If Q5 (self-harm) scored 3
  if (responses[4].score === 3) {
    return { total, riskLevel: 'critical', override: true };
  }
  
  // Override: If Q5 scored 2
  if (responses[4].score === 2) {
    total = Math.max(total, 21); // Minimum high_risk
  }
  
  if (total >= 26) return { total, riskLevel: 'critical' };
  if (total >= 21) return { total, riskLevel: 'high_risk' };
  if (total >= 11) return { total, riskLevel: 'moderate_risk' };
  return { total, riskLevel: 'low_risk' };
}
```

---

### PHASE B: Results Page Routing (Days 5-6)

Results page architecture update:
- Use `quiz/base-guide-catalog.json` as the source of truth for the 79 base guides.
- Use `planning/GUIDE-OFFER-MAPPING.csv` to resolve primary and secondary offer lanes.
- Use `planning/AUDIENCE-SLANT-MANIFEST.csv` to resolve audience-specific guide asset paths.
- Use `quiz/audience-bucket-flow.json` to power the audience lens selector after topic recommendations.

**4 Results Page Templates (React/Next.js components):**

1. **LowRiskResults** → Shows How to Help Guide + SMS promo
2. **ModerateRiskResults** → Shows Crisis Kit + SMS + Therapist Directory
3. **HighRiskResults** → Shows Crisis Kit (highlighted) + Therapist Directory + 988
4. **CriticalRiskResults** → Shows 988 (HUGE RED), Crisis Text Line, 911, Hide products

**Each page includes:**
- Risk level headline (copy from `quiz-questions.md`)
- Body explanation
- Buttons to products (Stripe integration)
- Email + SMS opt-in checkboxes (pre-filled if they entered before quiz)
- Crisis resources footer (always visible, never paywalled)

Recommendation stack now includes:
- matched base guide id
- matched audience bucket
- audience-specific guide variant path
- primary offer
- secondary offer
- reason for match

**Stripe Integration:**
- Product buttons redirect to checkout
- Pass `user_id` as metadata (to track which user completed which purchase)
- Post-purchase: webhook triggers email sequence (via SendGrid/ConvertKit)

---

### PHASE C: Email + SMS Automation (Days 6-8)

**Email Integration (ConvertKit API or SendGrid):**

- Trigger system: `if quiz_score > 20 AND email_opted_in → send Email 1 immediately`
- Use email template variables for risk level personalization
- Schedule delays: Email 2 send at +1 day, Email 3 at +7 days, etc.
- Track opens/clicks back to user table

**Sample: Email Trigger Logic (Node.js + Supabase)**

```javascript
async function triggerPostQuizEmails(userId, quizScore, email) {
  const sequence = getEmailSequenceByRiskLevel(quizScore);
  
  // Email 1: Send immediately
  await sendEmailViaAPI({
    to: email,
    template: sequence.email1,
    variables: { firstName, riskLevel: getRiskLevel(quizScore) }
  });
  
  // Email 2: Schedule for +1 day
  schedule({
    type: 'email',
    userId,
    emailTemplate: sequence.email2,
    sendAt: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000)
  });
  
  // Email 3: Schedule for +7 days
  schedule({
    type: 'email',
    userId,
    emailTemplate: sequence.email3,
    sendAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
  });
}
```

**SMS Integration (Twilio):**

- Check `sms_opted_in` flag before sending
- Send SMS in user's time zone (store in profile)
- Avoid 9 PM - 9 AM window
- Sample SMS delivery time: 9 AM first text, then 6 PM follow-up

```javascript
async function sendCheckOnMeSMS(userId, weekNumber, riskLevel) {
  const user = await getUser(userId);
  const message = getCheckOnMeMessage(weekNumber, riskLevel);
  
  await twilio.messages.create({
    body: message,
    to: user.phone,
    from: TWILIO_PHONE
  });
  
  await updateSMSSentLog(userId, weekNumber, now());
}

// Cron job runs daily at 9 AM EST
schedule('0 9 * * *', async () => {
  const subscribers = await getCheckOnMeSubscribers();
  for (let user of subscribers) {
    if (isTimeForWeeklyCheck(user)) {
      await sendCheckOnMeSMS(user.id, user.weekNumber, user.riskLevel);
    }
  }
});
```

---

### PHASE D: Landing Page (Days 1-3, parallel)

**Next.js Page: `/pages/quiz.js`**

- Copy from `landing-page/quiz-landing-page.md`
- Hero section with video/image
- Email pre-capture (optional)
- "Take Quiz" button → `/quiz/start`
- UTM parameter passthrough (preserve all utm_ from incoming traffic)

**Quiz Flow Page: `/pages/quiz/[id].js`**

- Shows one question at a time
- Multi-step form (Question 1 → Prev/Next → Question 10)
- Auto-advance or manual next button
- Progress bar (Q1/Q10, Q2/Q10, etc.)
- Save progress to avoid data loss if they close browser

---

### PHASE E: Analytics + Retargeting (Days 7-8)

**Pixel Events to Track:**
```javascript
// When landing page loads
fbq('track', 'ViewContent', { content_name: 'quiz_landing' });

// When quiz starts
fbq('track', 'ViewContent', { content_name: 'quiz_started' });

// When quiz completes
fbq('track', 'Purchase', { value: 0, currency: 'USD' }); // Track for retargeting

// When product clicked
fbq('track', 'ViewContent', { content_name: 'product_clicked', content_id: product_id });

// When product purchased
fbq('track', 'Purchase', { value: price_cents/100, currency: 'USD' });
```

**Google Analytics 4:**
- Event: `quiz_started` (at page load)
- Event: `quiz_completed` (at results page)
- Event: `product_clicked` (with product_name param)
- Event: `sms_signup` (if checked)

---

### PHASE F: Deployment Checklist (Days 9-10)

**Before going live:**

- [ ] Quiz scoring algorithm works correctly (test with edge cases)
- [ ] Results routing works (all 4 risk levels show correct page)
- [ ] Email sequences trigger automatically (test with test mailbox)
- [ ] SMS integration works (if using Twilio, test one message)
- [ ] Stripe payment buttons work (test charge + refund)
- [ ] Crisis resources display on EVERY results page
- [ ] No sensitive data logs to console
- [ ] Email/SMS can be unsubscribed
- [ ] Landing page loads fast on mobile
- [ ] Analytics pixels fire correctly (test with GTM debug)
- [ ] Database backups configured
- [ ] Error monitoring set up (Sentry or similar)

**Security:**
- [ ] HTTPS enabled everywhere
- [ ] Input validation on all user inputs
- [ ] SQL injection prevention (use parameterized queries)
- [ ] Rate limiting on API endpoints (prevent abuse)
- [ ] No hardcoded API keys (use environment variables)
- [ ] HIPAA compliance for health data (PII encryption)

---

## LAUNCH TIMELINE COORDINATION

```
PRE-LAUNCH (Week 1):
Days 1-3:   You write quiz + landing copy (DONE ✅)
Days 1-3:   Cody builds landing page + quiz interface  
Days 4-6:   Cody builds results routing + email triggers
Days 7-8:   Cody tests everything + fixes bugs

GO-LIVE (Day 9):
Morning:    Cody: Final deploy + health checks
Afternoon:  You: Start TikTok posting (2x/day starting Day 9)
            You: Monitor landing page + quiz funnel
            Cody: Monitor backend errors + database

MONTH 1 (Days 10-28):
Week 2:     Cody helps optimize based on click data
Week 3:     Cody prepares affiliate tech (Stripe fees, track affiliate clicks)
Week 4:     Begin affiliate onboarding (you provide outreach copy, Cody manages tech)

MONTH 2 (Days 29-60):
Ongoing:    You create testimonial videos + new content
Ongoing:    Cody optimizes funnel based on data
Week 6:     Scale to Phase 2 (More affiliates, paid TikTok ads if needed)
```

---

## DELIVERABLES FROM YOU (Content) → CODY (Tech)

**By Day 9 (Launch Day):**

Folder: `/quiz/`
- ✅ `quiz-questions.md` (10 questions with scoring)
- ✅ Results copy for all 4 risk levels

Folder: `/landing-page/`
- ✅ `quiz-landing-page.md` (all copy, laid out by section)

Folder: `/email-sms/`
- ✅ `post-quiz-automations.md` (all email subject lines + body + SMS content)

Folder: `/marketing/`
- ✅ `tiktok-launch-calendar.md` (content calendar for first 28 days)

---

## TECH DELIVERABLES → CODY PROVIDES TO YOU

**By Day 9 (Launch Day):**

1. **Landing page URL live**
   - Accepts UTM parameters
   - Email pre-capture (optional)
   - "Take Quiz" button works

2. **Quiz interface live**
   - 10 questions display one at a time
   - Scoring works backend
   - Results routing works (all 4 pages visible)

3. **Email automation active**
   - Test email sends to you immediately after quiz
   - Schedule delays work (follow-up emails queue correctly)

4. **SMS system ready** (if starting in Month 1)
   - Test SMS sends from Twilio
   - Cron job scheduled for daily sends

5. **Analytics pixel active**
   - Facebook pixel fires on quiz events
   - Google Analytics events logging
   - UTM parameters preserved end-to-end

6. **Stripe integration live**
   - Product buttons work
   - Charge successful + webhook triggers email
   - Refund processing works

---

## POTENTIAL BLOCKERS + SOLUTIONS

**Blocker 1: Email service rate limit**
- Solution: Start with ConvertKit free tier (1,000 subscribers), upgrade at 1k+

**Blocker 2: Twilio SMS cost**
- Solution: At $0.01/text, 5k texts/month = ~$50. Budget acceptable.

**Blocker 3: Stripe payment failures**
- Solution: Have retry logic + error messaging on results page ("Please try again")

**Blocker 4: Quiz abandonment (people don't finish)**
- Solution: Test with friends first. If >20% abandon mid-quiz, trim to 8 questions.

**Blocker 5: Crisis resources not showing on critical page**
- Solution: QA this specifically. CRITICAL. Never hide 988.

---

## SUCCESS = LAUNCH METRICS

By end of Day 28 (Week 4):

```
🎯 5k+ quiz completions
🎯 1.5k+ email opt-ins
🎯 300+ SMS subscribers
🎯 350+ product purchases = $7.5k - $15k gross revenue
🎯 Landing page CTR > 30% (clicks to quiz / page views)
🎯 Quiz completion rate > 50% (completions / starts)
```

If you hit these: You're on track for $127M Year 1 per the business plan.

---

## QUESTIONS FOR CODY

1. Is Supabase up + ready, or do you need DB setup help?
2. ConvertKit API vs SendGrid? (User can provide ConvertKit credentials)
3. Twilio account ready, or should user set up + share credentials?
4. Can you have quiz live for testing by Day 4?
5. Do you want me to handle TikTok posting or you?
6. What's your backup if Stripe fails in first week?

---

## NEXT STEPS

**TODAY:**
1. You: Review all docs in `/quiz/` and `/landing-page/`
2. You: Start filming first week of TikTok videos
3. Cody: Start building landing page + quiz interface
4. Both: Confirm timeline + answer the questions above

**This week:**
- Cody: Have quiz running by end of week (even if not live)
- You: Have first 3 days of TikTok videos filmed

**Week 2:**
- Cody: Deploy to production
- You: Go live with TikTok posting (2x/day)

**GO.**
