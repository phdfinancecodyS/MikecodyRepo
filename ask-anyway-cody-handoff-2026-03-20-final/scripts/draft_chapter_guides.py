#!/usr/bin/env python3
"""
Draft all 33 chapter guides with profile-matched content
Maps chapter content to psychological profiles (crisis, reactivity, sleep, etc.)
"""
import re
from pathlib import Path

# Map of chapter guides to their refined content based on profile
chapter_drafts = {
    "ch-01": {
        "profile": "reactivity",
        "what_is_happening": "Your high-alert brain is scanning for threat constantly. Your threat system stays locked on even when you are not in danger. This is not paranoia—it is your nervous system doing what it learned to do. The problem is it does not turn off.",
        "what_to_do": [
            "Name three false alarms your brain has triggered this week.",
            "Practice one grounding action when you notice the scanning (5-4-3-2-1 senses, or feet-to-ground breathing).",
            "Set one anchor point in your day where you pause and check: am I actually in danger right now?"
        ],
        "what_to_say": [
            "My brain is in high-alert mode and I am not in danger right now.",
            "I am noticing I am scanning and I am going to pause and ground.",
            "This is an old pattern and I am practicing a new response."
        ]
    },
    "ch-03": {
        "profile": "reactivity",
        "what_is_happening": "Your home should be your safest place but your nervous system has learned it is not. You read threats in normal moments. Your partner breathing wrong, traffic outside, the phone ringing—all trigger threat response. Your job is to rebuild home as genuinely safer, not just believed-safe.",
        "what_to_do": [
            "Map three specific situations at home that trigger the most alarm.",
            "For each one, name what your nervous system thinks is happening vs. what is actually happening.",
            "Plan one small change in each situation (moving furniture, changing sounds, different timing)."
        ],
        "what_to_say": [
            "I am re-learning that this home is safe and I am not relaxing because of my trigger pattern.",
            "When I react to [specific thing], it does not mean it is actually dangerous.",
            "I am working to reset my home-threat association and I need your patience."
        ]
    },
    "ch-04": {
        "profile": "reactivity",
        "what_is_happening": "Your anger comes fast because your fuse is short. Small frustrations that others would brush off trigger a rage response. Your nervous system goes from 0 to rage in seconds. This is not character failure; it is nervous system hyperarousal. But you still have to manage it because rage creates damage.",
        "what_to_do": [
            "Identify your earliest warning sign before rage (jaw clench, heat, chest tightness).",
            "Practice your reset move the moment you notice the warning (cold water, walk outside, 60-second breathing).",
            "Call one person right after you reset, not to vent about anger but to break the isolation."
        ],
        "what_to_say": [
            "I feel anger coming and I am taking a reset before I respond.",
            "This reaction is not about you or the situation. My nervous system is flooded.",
            "I will come back when I have reset and we can talk about this then."
        ]
    },
    "ch-06": {
        "profile": "general",
        "what_is_happening": "Depression shows up as numbness more than sadness. Nothing feels important. Your body feels heavy. Motivation does not exist. The world looks gray. This is not laziness or weakness. This is your nervous system in low-arousal collapse after sustained high-alert.",
        "what_to_do": [
            "Do one tiny action that moves your body (walk, stretch, dance to one song).",
            "Eat one real meal today whether you are hungry or not.",
            "Text one person you trust and say: I am in a low place today."
        ],
        "what_to_say": [
            "I am in depression and numbness right now and everything feels stuck.",
            "I am not looking for motivation. I am just doing one small move.",
            "This is temporary and my brain is rebooting itself."
        ]
    },
    "ch-08": {
        "profile": "moral",
        "what_is_happening": "Shame does not feel like emotion. It feels like fact. You are the problem. You are bad at the core. Everything you did wrong proves it. Your brain runs the same three memories on loop, each one confirming you are fundamentally flawed. This is not truth; this is a thought-feeling trap.",
        "what_to_do": [
            "Write down the three shame memories that loop most.",
            "For each one, write what a person who loves you would say about what actually happened vs. what your shame tells you.",
            "When shame loops, say out loud: This is shame talking, not fact."
        ],
        "what_to_say": [
            "I am in a shame spiral and I need to break the loop.",
            "I know this feeling means I did something I regret, and I am not a bad person because of it.",
            "I am going to tell [trusted person] what happened because shame dies in isolation."
        ]
    },
    "ch-09": {
        "profile": "general",
        "what_is_happening": "Memory slips happen because your working memory is fried. Your brain is stressed-out and managing too many threats in the background. Details do not stick. You forget what you were going to say mid-sentence. You lose the thread in conversations. This is not Alzheimer's; this is attention displacement.",
        "what_to_do": [
            "Stop relying on memory for critical things. Write down anything that matters (conversations, commitments, ideas).",
            "Use phone voice notes right when the thought comes so you do not lose it.",
            "Schedule repeat conversations for complex topics (do not expect them to stick first pass)."
        ],
        "what_to_say": [
            "My working memory is overloaded so I am writing everything down.",
            "Can we talk about this again? I need to let it sit and then come back.",
            "I forgot not because I do not care, but because my brain is managing a lot right now."
        ]
    },
    "ch-11": {
        "profile": "general",
        "what_is_happening": "Decision fatigue hits after you have made too many choices and your brain's decision-making fuel is empty. That last small decision (what to eat, which shirt) feels impossible. Your nervous system shuts down the decision-making system to protect itself. You feel stuck and helpless because your brain literally cannot decide.",
        "what_to_do": [
            "Cut decisions. Have a default for recurring choices (same breakfast, uniform clothes).",
            "Make important decisions early in the day when your fuel is full.",
            "For the rest of the day, use a coin flip or ask someone else to choose for non-critical decisions."
        ],
        "what_to_say": [
            "I have hit decision fatigue and I cannot choose right now.",
            "Can you decide this one? I am out of mental fuel.",
            "I am moving this decision to tomorrow when my brain is fresher."
        ]
    },
    "ch-12": {
        "profile": "reactivity",
        "what_is_happening": "Your nervous system is so primed that small frustrations trigger huge overreactions. The coffee spills and you rage. Someone is a little late and you panic. The person disagrees with you and you shut down. Your reaction is 10x bigger than the situation calls for. This is not personality; this is nervous system calibration.",
        "what_to_do": [
            "Before you react, ask: On a 0-10 scale, how dangerous is this actually? Your answer will probably be 2-3.",
            "Do 30 seconds of grounding before you respond (feet on ground, cold water, shaking).",
            "Practice saying the proportional response: This is frustrating and I can handle this."
        ],
        "what_to_say": [
            "I am about to overreact because my threat system is primed.",
            "This is actually small and my response is bigger than the situation.",
            "Give me a minute to ground and then I can respond appropriately."
        ]
    },
    "ch-13": {
        "profile": "sleep",
        "what_is_happening": "Chronic sleep debt is not about missing sleep one night. It is the accumulated exhaustion of weeks or months of poor sleep. Your body cannot catch up with random long sleeps. Your brain is degraded. Your mood is wrecked. Recovery takes consistent repair, not heroic one-time catches.",
        "what_to_do": [
            "Pick one anchor point (7am wake or 11pm sleep) and protect it ruthlessly for 2 weeks.",
            "Use the same wind-down 30 minutes before bed every night (no negotiating).",
            "In week 2, add one more anchor point. Do not try to fix everything at once."
        ],
        "what_to_say": [
            "My sleep debt is real and catching up takes time, not one long sleep.",
            "I am protecting my sleep anchors because that is how I get out of this.",
            "I am going to feel worse before I feel better, and that is part of recovery."
        ]
    },
    "ch-14": {
        "profile": "body",
        "what_is_happening": "Sleep apnea disrupts sleep architecture so you never reach deep sleep. You wake dozens of times per night without knowing it. You feel like you slept but you are still exhausted. This exhaustion affects everything: mood, attention, reactivity. It is not something you can willpower through.",
        "what_to_do": [
            "If you snore, have gaps in breathing, or wake gasping: get a sleep study done.",
            "If diagnosed with apnea, get the CPAP machine and commit to using it. Your brain will not recover without it.",
            "Give the machine 3 weeks before judging it. Your body needs time to adjust."
        ],
        "what_to_say": [
            "My sleep disruption is medical, not behavioral.",
            "I got diagnosed with sleep apnea and I am treating it.",
            "Recovery happens gradually but my waking life will improve significantly once my sleep is fixed."
        ]
    },
    "ch-19": {
        "profile": "body",
        "what_is_happening": "Crowds and public spaces trigger your nervous system because you cannot predict threat from many directions at once. Loud noises startle you. Close bodies press against your defenses. You cannot see exits clearly. Your nervous system locks into threat-scan mode and exhausts you fast.",
        "what_to_do": [
            "Plan public outings with an exit route already known (aisle seat, door nearest you, clear path out).",
            "Go to the same places repeatedly so your nervous system can downregulate recognition.",
            "Wear noise-dampening headphones or earplugs to reduce sensory overload."
        ],
        "what_to_say": [
            "I need to be positioned where I can see an exit.",
            "Going to familiar places helps my nervous system feel safer.",
            "I will take breaks when sensory overload hits."
        ]
    },
    "ch-20": {
        "profile": "body",
        "what_is_happening": "Vision sensitivity, balance issues, and motion sensitivity all trace back to vestibular system dysregulation. Your balance and spatial awareness system is exhausted. Moving your head feels destabilizing. Scrolling makes you queasy. Driving is harder. This is physical, not anxiety.",
        "what_to_do": [
            "Stabilize your position (sit with back support, feet grounded, head level).",
            "Slow down head motion and look with your eyes first, move your head second.",
            "Take frequent sitting breaks. Your nervous system cannot sustain scanning and balancing under stress."
        ],
        "what_to_say": [
            "My balance and motion sensitivity are real symptoms, not weakness.",
            "I need to take visual processing breaks and reset my position.",
            "Moving slowly and deliberately helps my nervous system stay regulated."
        ]
    },
    "ch-21": {
        "profile": "reactivity",
        "what_is_happening": "Your home is a minefield because you are hypervigilant about everyone's emotional state, tone of voice, and energy. You are reading micro-expressions and anticipating conflict before it starts. You feel responsible for everyone's mood. Living here is exhausting.",
        "what_to_do": [
            "Pick one person or family member and practice: I do not control their emotional state.",
            "Set a boundary: If there is yelling or threat, I am leaving the room for 20 minutes.",
            "Create one safe zone in your home where you can go to reset without negotiating."
        ],
        "what_to_say": [
            "I am reading threat here and I need to pause and check reality.",
            "I am not responsible for managing everyone's emotions.",
            "When I feel the minefield response coming, I am taking 20 minutes in [safe space]."
        ]
    },
    "ch-22": {
        "profile": "relationship",
        "what_is_happening": "Red/yellow/green communication is mapping where people are emotionally and how safe they are to approach. Red means disconnected, dangerous, or shut down. Yellow means present but unstable. Green means engaged and accessible. Most people in relationships do not explicitly read and respond to these zones.",
        "what_to_do": [
            "Learn to notice your own and your partner's color (red/yellow/green) in real time.",
            "When someone is red, do not push conversation. Let them be red and stay safe yourself.",
            "Only have important conversations when both people are green."
        ],
        "what_to_say": [
            "I see that you are in red right now so I am not going to push conversation.",
            "I am in yellow today and I need some space before we talk about important stuff.",
            "When we are both green, we can talk about [topic]. Right now neither of us are ready."
        ]
    },
    "ch-23": {
        "profile": "relationship",
        "what_is_happening": "Repair is the skill of reconnecting after damage. You said something hurtful, you missed your commitment, you showed up angry. Now the relationship feels broken. Most people try to move on without repair. Repair means you own the damage, you name what happened, and you commit to different.",
        "what_to_do": [
            "Say specifically what you did: I was short and harsh when you came home.",
            "Say why you did it: I was overwhelmed and I did not have capacity.",
            "Say what you are going to do differently: Next time I feel overwhelmed, I am going to say that instead of being harsh."
        ],
        "what_to_say": [
            "I hurt you and I need to repair that.",
            "Here is what I did, why I did it, and what I am changing.",
            "I know this apology is words and you will trust it when you see the change."
        ]
    },
    "ch-24": {
        "profile": "relationship",
        "what_is_happening": "Parenting on empty means you are out of fuel. Patience is gone. Presence is impossible. You are in survival mode. Your kids read your absence and they act out more because they feel the disconnection. You feel guilt about not being the parent you want to be.",
        "what_to_do": [
            "Pick one non-negotiable parenting anchor (bedtime, one meal together, morning check-in) and protect only that.",
            "Release guilt about everything else. You cannot do all things when you are depleted.",
            "Get help with the non-anchors (school pickup, supper prep, bedtime on your off-nights)."
        ],
        "what_to_say": [
            "I am running on empty and I can only show up for [one specific thing].",
            "I need help with [specific tasks] so I can protect my presence for what matters most.",
            "When I come back to capacity, I will be more available. Right now, this is what I can do."
        ]
    },
    "ch-26": {
        "profile": "relationship",
        "what_is_happening": "Kids in the blast radius means your kids are reading your dysregulation, your conflict, your exhaustion. They may not understand it consciously, but they feel it. Their behavior, sleep, and emotional regulation are affected by your nervous system's output.",
        "what_to_do": [
            "Name for your kids what is happening: I am struggling right now and this is not your fault.",
            "Model one reset when they see you dysregulated (I am frustrated so I am taking a walk).",
            "Give them one thing they can do when they see you struggling (hug you, leave you alone, get you water)."
        ],
        "what_to_say": [
            "My struggle is real and you are not the cause.",
            "When I do [reset action], it helps me come back to okay.",
            "You are safe. My feelings are big, and I am taking care of them."
        ]
    },
    "ch-27": {
        "profile": "work",
        "what_is_happening": "Family life in transition is the shock of changing your family structure (separation, retirement, kids leaving, remarriage). The routines that held you are gone. New roles are confusing. Everyone is adjusting at different speeds. The family you knew is not the family you have now.",
        "what_to_do": [
            "Name the transition explicitly: We are in a new family structure and everyone is figuring out their role.",
            "Establish one new anchor that replaces the old routine (new breakfast time, new weekly check-in).",
            "Normalize that adjustment takes time and people will struggle during the transition."
        ],
        "what_to_say": [
            "This is a family transition and it does not have to feel normal right away.",
            "Our new rhythm is [new routine] and I am learning it too.",
            "Let us be patient with each other as we figure out how this family works now."
        ]
    },
    "ch-28": {
        "profile": "general",
        "what_is_happening": "Emotional numbness is disconnection from feeling. Nothing moves you. Good news, bad news, beautiful moments—all registered the same. You know you should feel something and you do not. This is not depression (though it can coexist). This is dissociation or emotional numbing as a protection.",
        "what_to_do": [
            "Do not try to feel. Instead, do one action that typically brings feeling (cold water, music, movement).",
            "Your feelings are not broken. They are protected. Trust that reconnection comes with nervous system regulation.",
            "Check in with your body: Where would you feel this if you could feel it?"
        ],
        "what_to_say": [
            "I am numb to most things right now and I am not pushing feeling.",
            "My system is protecting itself by disconnecting and that is okay.",
            "Feeling will come back as I regulate my nervous system."
        ]
    },
    "ch-29": {
        "profile": "intimacy",
        "what_is_happening": "Low desire and low drive often trace back to nervous system depletion and fear. Your body is not in safe-enough mode for pleasure and connection. You are touched-out, overstimulated, or carrying so much hypervigilance that surrender feels impossible.",
        "what_to_do": [
            "Start with non-sexual touch (hand-holding, back scratch, sitting close) with zero expectation of progress.",
            "Tell your partner: My low drive is not about you. I am dysregulated and reconnecting with my body.",
            "Take pressure off the 'should' and practice one small reconnection daily."
        ],
        "what_to_say": [
            "My desire is low because my nervous system is not in a safe-enough place for pleasure.",
            "I want connection and my body is taking time to trust.",
            "I am rebuilding my capacity for intimacy and I need your patience, not performance."
        ]
    },
    "ch-30": {
        "profile": "intimacy",
        "what_is_happening": "Stress shuts down sex because when your nervous system is in threat-mode, sexuality does not work. Your body needs safety to access arousal. Cortisol and adrenaline shut down sex hormones. You can be attracted to your partner and still unable to access sexuality because of the nervous system state.",
        "what_to_do": [
            "Decode the actual stress: What is keeping your nervous system activated?",
            "Address the stress (reduce workload, get help, treat sleep, regulate nervous system).",
            "Sexuality will return when safety returns. Do not try to force it while stressed."
        ],
        "what_to_say": [
            "I am not avoiding sex. My nervous system is in a threat state and sex is not available right now.",
            "When I can regulate my stress, sexuality comes back naturally.",
            "I want to be close to you and my body is asking me to address the stress first."
        ]
    },
    "ch-31": {
        "profile": "intimacy",
        "what_is_happening": "Sex becomes avoidant when past experiences created fear-association with sex and intimacy. Your body says no even when your brain wants to connect. Touch feels dangerous. Vulnerability feels risky. Avoidance builds without realizing you are doing it.",
        "what_to_do": [
            "Name what your body is protecting against: What past experience created this fear-sex link?",
            "Start outside the bedroom (rebuilding non-sexual touch, safety with physical closeness).",
            "Go slow. Your body's protective response is real. Forcing sexuality will retraumatize."
        ],
        "what_to_say": [
            "Sex became connected with feeling unsafe and my body is protecting me.",
            "I want to be intimate and I need to rebuild safety with physical closeness first.",
            "I am not rejecting you. I am healing what got hurt."
        ]
    },
    "ch-33": {
        "profile": "intimacy",
        "what_is_happening": "Touch without pressure means physical closeness without the demand for arousal or sex. Hypervigilant nervous systems need to rewire their relationship with touch. Touch can feel like threat (pressure, dominance) or like demand (leading to sex). Healing touch is choice-based and pressure-free.",
        "what_to_do": [
            "Practice one type of touch with clear consent and zero progression (hand-holding, shoulder massage, sitting close).",
            "Make it a choice: Am I asking my body to stay for this touch right now? (Not a binary yes/no, but a check-in).",
            "Build touch slowly. Duration and closeness can increase as your nervous system recalibrates."
        ],
        "what_to_say": [
            "I need touch that is just touch, not pressure toward something else.",
            "I am checking in with my body about what touch I can stay present for right now.",
            "Let us build closeness slowly and let my nervous system reset its touch association."
        ]
    },
    "ch-34": {
        "profile": "body",
        "what_is_happening": "Body image issues after trauma often trace to how your body was treated or how you survived. Scars, weight changes, asymmetry—your body carries the story. Sexual confidence gets tangled in appearance anxiety and safety fears mixed together.",
        "what_to_do": [
            "Separate body image (appearance) from body safety (does this body keep me safe?).",
            "Rebuild relationship with one body part that troubles you: What does it do? How did it help me survive?",
            "Practice one appearance-neutral intimacy action (shower together, manual stimulation, closeness without mirrors)."
        ],
        "what_to_say": [
            "My body image anxiety is mixed with safety anxiety and they are separate things.",
            "My body carries scars and they tell stories of survival, not failure.",
            "I can rebuild confidence in what my body does, separate from what it looks like."
        ]
    },
    "ch-35": {
        "profile": "body",
        "what_is_happening": "Sex after injury or health change requires renegotiating your body's capabilities and your sense of sexual identity. What used to work does not work now. You may have pain, limited movement, or changed sensation. Your body changed and your sexuality has to adapt.",
        "what_to_do": [
            "Experiment with what your body can do now (no performance pressure, just exploration).",
            "Talk to your partner about positions, movements, or timing that work with your body's new parameters.",
            "Your sexuality is not smaller, it is different. Adaptation is not loss."
        ],
        "what_to_say": [
            "My body has changed and my sexuality is adapting with it.",
            "Let us explore what works for this body now instead of trying to force what used to work.",
            "This is different, not diminished."
        ]
    },
    "ch-36": {
        "profile": "moral",
        "what_is_happening": "Moral injury is the wound that comes from doing or witnessing something that violates your core values. You might have killed in self-defense but it still violated your belief in not killing. You might have stayed silent when you should have spoken. You might have hurt someone in a way that goes against your values. The guilt and shame run deep because your soul feels it.",
        "what_to_do": [
            "Name what happened and what values it violated. Do not downplay or reframe.",
            "Understand the context (survival, threat, no good options) without using it to excuse the values violation.",
            "Begin repair with yourself: What would need to be true for you to move forward?"
        ],
        "what_to_say": [
            "I did something that violated my values and I am carrying that.",
            "The context explains why I did it and does not erase that it went against who I am.",
            "I am working on what repair and redemption look like for me."
        ]
    },
    "ch-37": {
        "profile": "moral",
        "what_is_happening": "Betrayed by the system means institutions or people you trusted to protect or help you failed you. The military, the family, the government, the church—they were supposed to have your back and instead they hurt you. This is not personal betrayal; this is structural. But it feels personal.",
        "what_to_do": [
            "Separate the people from the system: The system betrayed you. Not everyone in it.",
            "Grieve what you needed them to be and what they actually were.",
            "Rebuild your trust selectively: This person in this role is trustworthy. That person is not."
        ],
        "what_to_say": [
            "The system I trusted betrayed me and that wound is real.",
            "I am learning to separate the institution from individuals within it.",
            "I am being selective about who I trust now, based on their actual behavior, not their role."
        ]
    },
    "ch-38": {
        "profile": "moral",
        "what_is_happening": "Feeling like the villain comes from internalizing blame that should have been shared or shouldered by others. You might have made a mistake that had huge consequences. You might have set a boundary and someone framed you as the bad guy. You might have said no and feel like you hurt someone. Your brain has decided you are the villain of this story.",
        "what_to_do": [
            "Write the story from another character's perspective. What did they do? What were their options?",
            "Identify where you hold blame that belongs to circumstances, bad luck, or others' choices.",
            "Practice saying: I made a mistake. That does not make me a villain."
        ],
        "what_to_say": [
            "I am carrying villain narrative about myself and I need to fact-check it.",
            "I had limited options and I made the best choice I could with information I had.",
            "I can hold that I made a mistake and I am not fundamentally bad because of it."
        ]
    },
    "ch-39": {
        "profile": "moral",
        "what_is_happening": "Faith, God, and big questions become huge when you have seen things that violate your belief system. Why does God allow suffering? How do I reconcile faith with what I have seen? Is there meaning? Is there purpose? These are not abstract. They are about whether your life means anything.",
        "what_to_do": [
            "Sit with the questions without needing to answer them right now.",
            "Separate faith from theology: You can have faith questions without needing doctrine answers.",
            "Find community with others asking the same questions (not people with final answers, but people in the question with you)."
        ],
        "what_to_say": [
            "My faith is being shaken and I am sitting in the questions.",
            "I do not have answers about meaning and purpose right now and that is okay.",
            "I am finding community with others who are asking these questions too."
        ]
    },
    "ch-41": {
        "profile": "work",
        "what_is_happening": "Identity after role is the crisis of losing the role that organized your sense of self. You were a soldier, a cop, a firefighter, a healthcare worker. Now you are not. Your title is gone. Your mission is gone. Your sense of who you are got tangled in that role. Without it, you do not know who you are.",
        "what_to_do": [
            "Separate your identity from the role: You had values and skills before the role and they do not disappear with the title.",
            "Write down the parts of yourself that exist outside the role (as a friend, parent, partner, citizen).",
            "Find new structure that provides mission and meaning (not the same role, but something that matters)."
        ],
        "what_to_say": [
            "I have lost the role that organized my identity and I am rebuilding who I am.",
            "My values and skills do not disappear when I step out of uniform.",
            "I am finding new ways to contribute and new identity anchors."
        ]
    },
    "ch-42": {
        "profile": "work",
        "what_is_happening": "Rebuilding mission and meaning is reactivating your sense of purpose when your old purpose has been taken or has changed. You had clear mission (protect, serve, heal) and now you are looking for what drives you. Some people find new mission. Some people have to rebuild their sense that life means anything.",
        "what_to_do": [
            "List the values that drove your old mission (protect, serve, heal, justice, growth).",
            "Find one small way to live those values in your new life (mentor, volunteer, help a specific person).",
            "Start with a 30-day purpose sprint: One small meaningful action per day."
        ],
        "what_to_say": [
            "I am rebuilding my sense of what my life is for.",
            "The values that drove my main role can show up in smaller ways now.",
            "I am finding meaning through [one specific action] and seeing where that leads."
        ]
    },
    "ch-45": {
        "profile": "general",
        "what_is_happening": "Loneliness and loss of tribe happens when the community that held you is gone. The team you deployed with, the unit, the shift crew—you were bonded by shared knowing. Civilians do not get it. Family wants you to move on. You do not fit anywhere now and isolation cuts deep.",
        "what_to_do": [
            "Do not try to replace tribe with generic friendship. Find one or two people who have done similar things.",
            "Start a small group, online community, or meet up with one person who understands the work.",
            "Stay connected to the past community in smaller ways (coffee with one person, organized reunion, online group)."
        ],
        "what_to_say": [
            "I am grieving the loss of my operating community and I feel alone.",
            "I am finding people who understand without needing to explain everything.",
            "I am building a new tribe connection, not replacing the old one."
        ]
    },
    "ch-46": {
        "profile": "general",
        "what_is_happening": "Lone wolf to team member is learning to trust a team when your self-reliance has been your survival mechanism. Being part of something means vulnerability. It means depending on others. Your hypervigilance makes team trust feel impossible. But you are learning that operation is better with team.",
        "what_to_do": [
            "Start with one person on the team. Practice vulnerability in small doses (ask for help, admit you do not know, say you struggled).",
            "Notice what happens: The team usually responds with stronger connection, not judgment.",
            "Gradually expand: More people, more vulnerability, more trust."
        ],
        "what_to_say": [
            "I am a lone wolf and team trust does not come easy to me.",
            "I am practicing asking for help and admitting when I am struggling.",
            "I am learning that depending on a team does not make me weak."
        ]
    }
}

def get_profile(title):
    """Get profile for a chapter"""
    low = title.lower()
    if any(x in low for x in ["crisis", "suicid", "hopeless"]):
        return "crisis"
    elif any(x in low for x in ["anger", "rage", "blow", "short", "overreact"]):
        return "reactivity"
    elif any(x in low for x in ["sleep", "wake", "nightmare", "apnea", "fatigue", "debt"]):
        return "sleep"
    elif any(x in low for x in ["parent", "family", "kid", "home", "relation", "partner", "communication", "repair"]):
        return "relationship"
    elif any(x in low for x in ["moral", "shame", "guilt", "faith", "betrayal", "villain"]):
        return "moral"
    elif any(x in low for x in ["sex", "intimacy", "desire", "touch", "body image"]):
        return "intimacy"
    elif any(x in low for x in ["pain", "tension", "body", "migraine", "headache", "noise", "vision", "balance", "sense"]):
        return "body"
    elif any(x in low for x in ["scroll", "habit", "loop", "compul", "dopamine"]):
        return "habit"
    elif any(x in low for x in ["work", "identity", "job", "role", "meaning", "transition", "tribe"]):
        return "work"
    else:
        return "general"

def format_list(items):
    """Format list for markdown"""
    return "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])

def rebuild_guide(filepath, ch_num, title, content_map):
    """Rebuild chapter guide with drafted content"""
    with open(filepath, 'r', encoding='utf-8') as f:
        current = f.read()
    
    profile = get_profile(title)
    
    if f"ch-{ch_num:02d}" in content_map:
        draft = content_map[f"ch-{ch_num:02d}"]
        what_happening = draft["what_is_happening"]
        what_todo = format_list(draft["what_to_do"])
        what_say = "\n".join([f"- {item}" for item in draft["what_to_say"]])
    else:
        # Fallback for any missing entries
        return current
    
    # Extract existing sections
    mistakes_match = re.search(r"^## Common Mistakes To Avoid\n\n(.*?)(?=^##)", current, re.MULTILINE | re.DOTALL)
    mistakes = mistakes_match.group(1).strip() if mistakes_match else ""
    
    plan_match = re.search(r"^## 24-Hour Action Plan\n\n(.*?)(?=^##)", current, re.MULTILINE | re.DOTALL)
    plan = plan_match.group(1).strip() if plan_match else ""
    
    worksheet1_match = re.search(r"^## Worksheet 1:.*?\n\nGoal:[^\n]*\n\n(Prompts:.*?)(?=^##|\Z)", current, re.MULTILINE | re.DOTALL)
    worksheet1_content = worksheet1_match.group(1).strip() if worksheet1_match else ""
    
    worksheet2_match = re.search(r"^## Worksheet 2:.*?\n\nGoal:[^\n]*\n\n(Prompts:.*?)$", current, re.MULTILINE | re.DOTALL)
    worksheet2_content = worksheet2_match.group(1).strip() if worksheet2_match else ""
    
    # Extract metadata (title + status + guide info)
    metadata_match = re.match(r"(# .*?\nStatus:.*?\n.*?\n.*?\n.*?\n.*?\n)", current, re.MULTILINE)
    metadata = metadata_match.group(1) if metadata_match else "# [Title]\nStatus: draft_v1_complete\n"
    
    # Rebuild
    rebuilt = f"""{metadata}
## What This Helps With

This guide helps with "{title}" when it keeps showing up in your week and you need a practical response.
Use this when you want clear words and a clear next step, not theory.

## What Is Happening

{what_happening}

## What To Do Now

{what_todo}

## What To Say

{what_say}

## Common Mistakes To Avoid

{mistakes}

## 24-Hour Action Plan

{plan}

## Worksheet 1: Pattern Finder

Goal: Identify triggers, context, and early warning signs.

{worksheet1_content}

## Worksheet 2: Action Builder

Goal: Turn insight into one script and one 24-hour commitment.

{worksheet2_content}
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rebuilt)

def draft_all_chapters():
    """Draft all 33 chapter guides"""
    chapter_dir = Path("content/topic-guides/chapters")
    
    for guide_file in sorted(chapter_dir.glob("*.md")):
        filename_match = re.match(r"ch-(\d+)-(.*)", guide_file.stem)
        if filename_match:
            ch_num = int(filename_match.group(1))
            
            # Read to get title
            with open(guide_file, 'r', encoding='utf-8') as f:
                content = f.read()
            title_match = re.match(r"# (.*?)\n", content)
            if title_match:
                title = title_match.group(1)
                rebuild_guide(guide_file, ch_num, title, chapter_drafts)
                print(f"✓ Drafted: {guide_file.name}")
    
    print(f"\nDrafted all 33 chapter guides with profile-matched content.")

if __name__ == "__main__":
    draft_all_chapters()
