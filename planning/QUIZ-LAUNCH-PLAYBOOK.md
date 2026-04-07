# QUIZ LAUNCH PLAYBOOK
**Goal:** Get the Mental Health Quiz live and driving traffic within 14 days

---

## PHASE 1: CONTENT (Your Work  - Days 1-3)

### 1A. Write 10 Quiz Questions ⏱️ 2 hours
**Output:** `quiz/quiz-questions.md`
- 10 questions, scored 0-3 each (total 0-30 range)
- Topics: mood, sleep, stress, relationships, self-harm ideation, substance use, work functioning, social withdrawal, hopelessness, energy
- Tone: Hopeful, non-judgmental, non-diagnostic ("based on your answers...")
- Each question needs 4 response options with scoring values

### 1B. Create Results Logic & Routes ⏱️ 1 hour
**Output:** `quiz/quiz-results-logic.md`
```
Score 0-10 → Low risk
  Result page: "You're in a good place. Share these resources with someone who might need them."
  CTA: Buy Crisis Kit? Check On Me SMS?
  Products shown: How to Help Guide ($10), SMS ($4.99/mo)

Score 11-20 → Moderate risk  
  Result page: "You're managing, but take care of yourself. Here are 3 things to do this week."
  CTA: "Start my Check On Me check-ins" 
  Products shown: Crisis Kit ($5), SMS ($4.99/mo), How to Help Guide ($10)

Score 21-25 → High risk
  Result page: "You matter. Crisis support is available 24/7. Let's get you connected."
  CTA: "Get my safety plan" + therapist match
  Products shown: Crisis Kit ($5), Therapist Directory (FREE)
  FREE resources emphasized (988, Crisis Text Line, BetterHelp)

Score 26-30 → Critical
  Result page: RED ALERT layout  - "You're in crisis. Get help right now."
  CTA: "CALL 988" + Crisis Text Line + local crisis center
  Products hidden  - SAFETY FIRST
  All resources FREE, no paywall
```

### 1C. Write Landing Page Copy ⏱️ 2 hours
**Output:** `landing-page/quiz-landing.md`
- Headline: Speaks to pain point (not diagnosis, but relevance)
- Body: 3-4 punchy sections (why take it, what happens, social proof)
- CTA button: "Take the Quiz"
- Post-quiz opt-in: Email + phone for SMS
- Safety disclaimer: "Not a diagnosis, screens for support needs"

### 1D. Create Email/SMS Automation Sequences ⏱️ 2 hours
**Output:** `email-sms/post-quiz-automations.md`
- **Email Seq 1 (Low risk)**: "Thanks for taking action. Share this with someone."
- **Email Seq 2 (Moderate)**: "You're taking care of yourself. Here's Week 1 of Check On Me..."
- **Email Seq 3 (High/Critical)**: "We want you to know you're not alone. Here's what to do now..."
- **SMS Seq**: First 4 weeks of Check On Me content (already scheduled in business plan)

**Total Content Work: ~7 hours** ✅

---

## PHASE 2: TECH (Cody's Work  - Days 4-6)
*Assuming Cody has Supabase + Stripe ready:*
- Build quiz form (10 questions, validate responses)
- Create scoring algorithm (0-30 range)
- Set up results routing (4 different result pages based on score)
- Email capture + SMS opt-in
- Stripe integration for products shown on results pages
- Connected to Supabase user table + email/SMS system

**Dependency:** Your quiz questions + results logic + landing copy
**Deliverable:** Quiz URL live + results routing tested

---

## PHASE 3: GO-TO-MARKET (Days 7-14)

### 3A. TikTok Content Calendar (Your Job)
**Prep:** Use your 8 video templates + the quiz findings
- Week 1 (Days 7-9): Film 4 "myth-busting" videos introducing the quiz hook
  - Video 1: "I made a quiz that perfectly captures why people struggle..."
  - Video 2: "If you've ever felt alone in this, take this quiz"
  - Video 3: Credibility intro (co-author story)
  - Video 4: "Your score determines what help you actually need"
- Week 2 (Days 10-14): Upload 2x daily + monitor comments
  - Respond to top comments with stories/follow-ups
  - Link-in-bio → landing page → quiz

### 3B. Email Warm-up (Your Job)
- Day 7: Send to existing ConvertKit list: "I built a quiz. Take it."
- Day 10: Follow-up: "Here's what people are scoring..."
- Day 14: "Early results are revealing..."

### 3C. Affiliate Coordinator (Cody Leads, You Support)
- Day 7: Identify 10 nano/micro creators (1k-10k followers, mental health niche)
- Day 10: Outreach kit ready (your landing page copy + results screenshot examples)
- Day 12: First 3 affiliates testing + reporting back

---

## SUCCESS METRICS (Week 2)
```
Target by Day 14:
✅ 10k+ quiz starts
✅ 3k+ quiz completions
✅ 1.2k email opt-ins
✅ 300+ SMS sign-ups
✅ 5+ affiliate posts live
✅ 150k+ total TikTok impressions from your content

Revenue Target: $15-25k gross (first 2 weeks)
```

---

## LAUNCH CHECKLIST

**Content (YOU)  - Due Day 3:**
- [ ] Quiz questions written + scored (10 questions, 0-30 scale)
- [ ] Results pages copy + routing (4 risk levels)
- [ ] Landing page copy finalized
- [ ] Email/SMS automation sequences drafted
- [ ] Safety messaging compliance reviewed (AFSP-compliant)

**Tech (CODY)  - Due Day 6:**
- [ ] Quiz interface live + scoring works
- [ ] Results routing to 4 pages confirmed
- [ ] Email capture + SMS integration tested
- [ ] Stripe buttons on results pages working
- [ ] User data flowing to Supabase correctly

**Marketing (YOU + CODY)  - Days 7-14:**
- [ ] 4 TikTok videos filmed + queued
- [ ] Landing page live with UTM tracking
- [ ] Email warm-up sent (Day 7)
- [ ] Affiliate outreach kit ready (Day 9)
- [ ] First affiliates onboarded (Day 12)

---

## QUICK WINS FIRST
1. **This week:** Quiz + landing page live (doesn't need Crisis Kit or How to Help Guide copy yet)
2. **Week 2:** Run TikTok traffic to quiz, collect email/SMS
3. **Week 3+:** Build products based on actual user data (what risk level are people scoring?)

**Why this order:** The quiz IS the product for Week 1. Products are secondary conversions. Get volume first, then optimize.
