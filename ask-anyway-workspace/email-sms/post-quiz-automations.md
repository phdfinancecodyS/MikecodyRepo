# POST-QUIZ EMAIL & SMS AUTOMATION SEQUENCES
**Purpose:** Convert quiz takers into product buyers + SMS subscribers  
**Email Platform:** ConvertKit  
**SMS Platform:** Twilio + Supabase  
**Key:** Each sequence is tailored to risk level + product shown

---

## SEGMENT RULES

- Low Risk (0-10) -> Share/help-others path
- Moderate Risk (11-20) -> Support + early intervention path
- High Risk (21-25) -> Urgent support path
- Critical (26-30 or Q5=3) -> Crisis resource path

---

## EMAIL 1 BY SEGMENT

### Low Risk
**Subject:** Your quiz result: You're managing well. Here's what's next.

Core message:
- validate that they are doing okay
- remind them support is still allowed before crisis
- offer How to Help Guide + Check On Me

CTA buttons:
- Get the How to Help Guide
- Join Check On Me

### Moderate Risk
**Subject:** Your quiz result: This is real, and it's fixable. Here's what to do first.

Core message:
- validate stress, low mood, isolation, or overload
- recommend Check On Me as first step
- offer Crisis Kit as one-time support tool

CTA buttons:
- Start Check On Me
- Get the Crisis Kit

### High Risk
**Subject:** Your quiz result: You need support. Here's exactly where to go.

Core message:
- urgent and compassionate tone
- point to therapist directory + 988 + Crisis Text Line
- offer Crisis Kit only as a support tool, not as replacement for real help

CTA buttons:
- Find a therapist
- Call 988
- Text HOME to 741741
- Get the Crisis Kit

### Critical
**Subject:** URGENT: You need help right now

Core message:
- direct safety-first language
- no product-first framing
- immediate referral to 988 / 741741 / 911 / ER

CTA buttons:
- Call 988 now
- Text HOME to 741741
- Call 911

---

## SMS STARTER FLOW

### Moderate Risk
Week 1:
- quick mood check-in
- one grounding tool

Week 2:
- sleep check-in
- one sleep hygiene prompt

Week 3:
- connection prompt
- encourage reaching out to one person

Week 4:
- reflection + affirmation
- reminder to keep getting support

### High Risk
Week 1:
- safety + connection prompt
- ask if they have reached one trusted person

Week 2:
- therapist search prompt
- direct directory link

Week 3:
- ask whether they feel safer than last week

Week 4:
- maintain connection and reinforce professional support

### Critical
Day 1:
- call 988 / text 741741 prompt

Day 3:
- follow-up asking whether they reached out

Day 7:
- repeat crisis referral if no confirmation of support

---

## DELIVERY RULES

- Email 1 sends immediately after quiz completion if email opt-in is true
- Delay follow-up emails based on segment
- SMS only sends if explicit SMS opt-in is true
- No SMS outside 9 AM to 9 PM local time
- Every email includes unsubscribe
- Every result level includes free crisis resources
- Critical users should never see product-first messaging

---

## MINIMUM VIABLE AUTOMATION

For launch, Cody only needs:
- 1 immediate email per segment
- 1 weekly SMS cadence for opted-in users
- crisis override flow for Q5 score 3

Everything else can expand in v2.
