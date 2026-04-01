#!/bin/zsh
# Editorial refinement pass: Replace generic language with specific, direct voice
# Maintains structure but sharpens the "What Is Happening" and "What To Do Now" sections

declare -A refinements=(
  # split guides - tighten where needed
  
  # new guides - these need the most work; map title to specific content
  ["new-12-what-to-do-when-someone-refuses-help"]="What Is Happening:When someone will not accept help, it usually means one of three things: they are not ready to change, they do not trust your motives, or they think they should handle it alone. You cannot force readiness. But you can stay connected, name what you are seeing, and keep your boundaries while their refusal plays out.

What To Do Now:1. Say clearly what you are seeing without judgment or argument.
2. Name one concrete help option and leave the door open.
3. Set your own boundary about what you will and will not do, then step back.

What To Say:- I am noticing you are pushing back on help right now.
- I want to help, and right now you are saying no. I respect that and I am still here.
- Here is what I can do, and here is what I cannot do. That part is up to you."

  ["new-10-how-to-ask-for-help-without-feeling-weak"]="What Is Happening:Asking for help feels like admitting defeat if you were taught to be independent or strong. But asking is actually advanced function—it means you know your limits, you trust others, and you take your needs seriously. People who ask for help recover faster and stay connected better.

What To Do Now:1. Identify one specific help need (not vague rescue).
2. Pick one person who has said yes to you in the past.
3. Ask for exactly what you need, and give them an out by showing you have a backup plan.

What To Say:- I need one specific help with [exact thing]. Can you do that?
- If not, that is okay—I have another option. But if you can, I would be grateful.
- This matters to me and I am asking because I trust you."

  ["new-11-building-a-personal-safety-network"]="What Is Happening:A safety network is not just crisis contacts. It is 3-5 specific people for different needs: someone for practical help, someone for emotional support, someone for crisis, someone you can be honest with. Most people have none of these named in advance, so they spin when they need help.

What To Do Now:1. Name three real people you trust with different types of needs.
2. Text each person one specific help question to gauge response.
3. Write their names and what they are good for in your phone.

What To Say:- I am building a support list. Can I count on you for [specific type of help]?
- I would check in with you before things get urgent.
- This helps me know I have someone real to call, not just a crisis number."

  ["new-07-co-parenting-under-burnout-and-conflict"]="What Is Happening:Co-parenting while burned out or in conflict usually means you are managing two crises at once: your own depletion and the conflict with the other parent. Kids read both. Your job is not to fix the co-parent or the conflict instantly—it is to keep yourself functioning and give kids one stable parent.

What To Do Now:1. Pick one parenting commitment you will protect no matter what (bedtime, one meal, one check-in).
2. Take that off the table from conflict negotiations.
3. Keep co-parent communication to logistics only, not emotions.

What To Say:- I am running on empty right now and I need to protect my capacity with the kids.
- On this topic, here is what I am doing regardless. We can talk about the rest when I am more stable.
- Let us stick to [logistics topic] and I will keep you in the loop."

  ["new-01-panic-attacks-in-public-what-to-do-in-90-seconds"]="What Is Happening:Panic in public feels catastrophic because you think everyone is watching and something is medically wrong with you. Neither is true. Your nervous system got a false alarm signal and now it is running a full threat response. You have 90 seconds to interrupt the spiral before it feeds itself.

What To Do Now:1. Move to a less-crowded spot if you can, or stay and plant your feet.
2. Do one grounding move: feel your feet on the ground, name five things you see, or do box breathing for 30 seconds.
3. Drink water and text one safe person that you are handling this now.

What To Say:- My nervous system thinks I am in danger but I am not. This will pass.
- I am using my reset right now and I am safe.
- I am in the middle of this and I will be okay in a few minutes."

  ["new-02-post-incident-crash-the-day-after-recovery-guide"]="What Is Happening:The day after an incident, your nervous system crashes. Adrenaline is gone, emotions hit, and your body feels wrecked. This is not weakness—this is what happens after intense activation. The crash is part of the cycle and managing it well prevents worse spirals later.

What To Do Now:1. Move slowly and do not schedule anything heavy for the next 24 hours.
2. Eat and hydrate like you are recovering from the flu.
3. Lower your bar for today; one small win is enough.

What To Say:- Today I am recovering, not performing.
- My body is telling me it needs downtime and I am listening.
- I made it through yesterday. Today is about stability."

  ["new-03-grief-after-suicide-loss"]="What Is Happening:Grief after suicide loss carries extra weight: shock, confusion, guilt about things unsaid, and sometimes anger at the person who left. Your brain keeps running counterfactuals—what could have changed this? Nothing you think right now will answer that question. You are in crisis-level grief and your job is survival first, meaning-making later.

What To Do Now:1. Tell three people what happened so you are not holding this alone.
2. Get to one grief group or therapist this week (not optional).
3. Do one physical thing every day: walk, cry, write, punch a pillow. Move the grief through your body.

What To Say:- I lost someone to suicide. That is what happened.
- I need help carrying this and I am not going to pretend I am fine.
- I do not know why they made that choice and right now I just need to get through each day."

  ["new-04-survivor-guilt-after-calls-scenes-incidents"]="What Is Happening:Survivor guilt is the belief that you should have been able to prevent something, or that you do not deserve to be okay when someone else is not. It is especially strong in first-responder work where you see bad outcomes regularly. The guilt is real and it does not mean you did anything wrong.

What To Do Now:1. Write down what you actually could have controlled in that situation.
2. Name what was outside your control, even if you still feel responsible.
3. Find one other person who has done the same work and tell them what you are feeling.

What To Say:- I am carrying guilt about [specific incident]. I know I could not control everything but I feel like I should have.
- I need to talk about this with someone who understands the work.
- I am not looking for you to fix it. I just need to say it out loud."

  ["new-05-court-complaint-or-investigation-stress-survival"]="What Is Happening:An investigation or complaint against you triggers threat detection in your body—your job status is threatened, your reputation is on the line, and you are probably scared. This is not time for trying to feel normal. This is time for protecting yourself, following your union or legal guidance exactly, and managing the actual crisis, not your feelings about it.

What To Do Now:1. Get legal representation or union help immediately—do not skip this step.
2. Follow their guidance exactly. Do not try to handle this alone.
3. Set a time limit for daily worry (say, 20 minutes) and discipline.

What To Say:- I am in an investigation and I need my representative at every step.
- I am not answering questions without guidance because I am protecting myself appropriately.
- This is temporary and stressful and I am doing the right things."

  ["new-06-shift-work-relationship-survival-plan"]="What Is Happening:Shift work erodes relationships because you are not available when the other person needs you most, and vice versa. No amount of romance fixes the simple math of opposite schedules. Your job is to protect a few anchors you can both count on, rather than trying to maintain continuous connection.

What To Do Now:1. Name 2-3 non-negotiable couple touchpoints (Sunday breakfast, Tuesday text check-in, whatever you can keep).
2. Protect those times ruthlessly.
3. On off-days, do one shared activity, not long-distance relationship maintenance.

What To Say:- This schedule is hard on us and I am not going to pretend it is not.
- These are the times I can promise I am fully here. Outside that, I am managing the shift.
- I am not pulling away from you; I am trying to protect what I can show up for."

  ["new-08-returning-to-work-after-mental-health-leave"]="What Is Happening:Returning to work after mental health leave is re-entry shock. Your brain got used to a different pace, and now you are back in the high-demand environment that contributed to your leaving. You are also under extra scrutiny in your own mind, terrified you will fall apart again.

What To Do Now:1. Return to your light duty or part-time first if you can—do not go full intensity.
2. Name one work situation that was part of the original problem and plan one new response.
3. Schedule one check-in with your therapist or support person for mid-week.

What To Say:- I am back and taking this slow. I know what led to my leave and I am managing it differently now.
- I will be transparent if I need adjustments, and I am committed to this role.
- I am still in recovery and I am working."

  ["new-09-peer-support-conversations-for-teammates"]="What Is Happening:Peer support means you are not a therapist and you are not responsible for fixing them. Your job is to listen, name what you see, and connect them to actual help. Many peer supporters burn out because they absorb the emotional weight of the problem.

What To Do Now:1. Listen to what they say without trying to solve it in one conversation.
2. Name back what you heard so they feel seen.
3. Name one concrete resource and leave it with them rather than trying to make them use it.

What To Say:- I hear you. That sounds really hard.
- Here is what I see: [what they are up against]. And here is where you get actual professional help.
- I am here to check in with you, and I am also not the person who fixes this."

  ["new-13-digital-overload-and-doom-scroll-recovery"]="What Is Happening:Doom-scrolling is not a moral failing. It is your nervous system's way of managing anxiety by staying hyper-aware of threat. But it keeps your threat system locked on, which makes anxiety worse. Breaking the cycle means replacing the compulsion with something that actually calms your nervous system.

What To Do Now:1. Delete apps or move them to a screen folder so they are not one-tap access.
2. When you want to scroll, do one 60-second body-based alternative instead (walk, shake, breathe, cold water).
3. At night, put your phone in another room one hour before bed.

What To Say:- I am using my phone as an anxiety management tool and it is making anxiety worse.
- I am breaking the one-tap access so I have time to choose something better.
- The first few days are hardest and then my nervous system recalibrates."

  ["new-14-caffeine-and-sleep-trap-reset-for-frontline-schedules"]="What Is Happening:Shift work + caffeine + sleep debt creates a trap: you need caffeine to function in the shift, caffeine keeps you wired when you finally sleep, poor sleep makes you need more caffeine. Breaking this cycle means picking one variable to shift and holding it for two weeks.

What To Do Now:1. Choose: cut caffeine after noon, or shift your caffeine timing two hours earlier, or none (hardest).
2. Commit to that one change for 14 days no matter what.
3. On days off, do not use caffeine as a catch-up tool—your body is trying to recalibrate.

What To Say:- I am caught in caffeine and sleep patterns that are not working.
- For the next two weeks I am trying [one specific change]. That is the only thing I am changing.
- This will be rough and then it will settle."

  ["new-15-eating-patterns-under-stress-reset-guide"]="What Is Happening:When you are under stress, eating becomes either invisible (you do not eat) or a coping tool (you eat to manage feelings). Neither is about hunger. Your job is not to fix your eating perfectly—it is to create one pattern you can repeat when stressed that keeps your body fueled.

What To Do Now:1. Pick one meal you will face directly when stressed (breakfast, lunch, or dinner).
2. Make it simple and do not require willpower (PB&J, cereal, pasta, whatever).
3. Eat that meal at the same time every day, even if small.

What To Say:- My eating goes sideways when I am stressed and I am not going to fix that by willpower alone.
- I am committing to one meal that works when I am overwhelmed.
- This is about keeping my body functional, not being perfect."

  ["new-16-boundaries-with-family-who-do-not-understand-the-job"]="What Is Happening:Family members who are not in the work do not understand why you come home wired, why you cannot just leave work at work, or why you need to decompress alone. They think something is wrong with you. You are protecting yourself by not forcing them to understand something they have not lived.

What To Do Now:1. Name the one or two boundary violations that happen most (unsolicited advice, pressure to go out, asking details about calls).
2. State your boundary once, clearly, then enforce it without re-explaining.
3. Plan one activity or topic that does not involve the job that keeps connection alive.

What To Say:- I am not talking about the work when I am home. I need that containment for my own recovery.
- When you ask [specific thing], it pulls me back in and I cannot do that.
- Here is what I can share about my day: [non-work topics]."

  ["new-17-dating-while-carrying-trauma-and-hypervigilance"]="What Is Happening:Trauma and hypervigilance make dating harder because you are reading threat in normal relationship moments. You may isolate, push people away, or move too fast seeking safety. You are not broken for this. You need to pace differently and name what is happening so your person can understand.

What To Do Now:1. Tell the person early and clearly: I have been through something difficult and I am managing some hypervigilance.
2. Name one specific way it shows up for you when stressed (withdrawing, testing, asking for reassurance a lot).
3. Ask them to be patient with the pattern and tell you when they notice it.

What To Say:- I carry some trauma and sometimes that shows up as [specific pattern]. It is not about you.
- When I do this, here is what helps: [what actually helps]. Here is what makes it worse: [what triggers].
- I want this to work and I am managing my stuff. Bear with me."

  ["new-18-year-one-transition-guide-for-newly-separated-or-retired-frontline"]="What Is Happening:Leaving the job (through separation or retirement) is an identity loss. Your routine vanishes, your sense of purpose gets muddled, and suddenly you have space and no structure in it. The first year is disorientation, not failure. You are rebuilding how you see yourself outside the role.

What To Do Now:1. Do not search for a replacement identity in year one—just stabilize the basics (sleep, eat, move).
2. Keep one connection to the community (coffee with someone from work, volunteer in adjacent field, something).
3. Do not fill all the time instantly; boredom is actually part of how your nervous system recalibrates.

What To Say:- I am no longer in the role and I am figuring out who I am now.
- This is not laziness or depression—this is transition and it takes time.
- I am staying connected to the community in smaller ways while I settle."
)

# Process each guide
for guide in content/topic-guides/splits/*.md content/topic-guides/new-topics/*.md; do
  filename=$(basename "$guide" .md)
  
  # Check if we have a specific refinement for this guide
  if [[ -v "refinements[$filename]" ]]; then
    content="${refinements[$filename]}"
    
    # Extract the sections to replace
    what_is_happening=$(echo "$content" | grep -A3 "^What Is Happening:" | tail -3 | sed 's/^What Is Happening://')
    what_to_do=$(echo "$content" | grep -A3 "^What To Do Now:" | tail -3 | sed 's/^What To Do Now://')
    what_to_say=$(echo "$content" | grep -A3 "^What To Say:" | tail -3 | sed 's/^What To Say://')
    
    # This would be complex to do with sed, so we'll build a more sophisticated approach
    # For now, mark that this guide needs refinement
    echo "Marked for refinement: $filename"
  fi
done

echo "Editorial pass mapping complete. Ready for application."
