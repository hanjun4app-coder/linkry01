# AI_CONFIDENCE_RULES.md

# SafeHome AI Confidence & Decision Rules

Version: MVP Production Phase

Purpose:
Define confidence scoring, uncertainty handling, escalation logic, and behavioral interpretation boundaries for SafeHome AI systems.

These rules apply to:
- behavior learning agents
- risk scoring agents
- runtime AI systems
- alert systems
- notification routing systems
- future multi-sensor AI systems

---

# CORE PRINCIPLE

SafeHome AI must communicate uncertainty honestly.

The system should assist families with awareness,
NOT pretend certainty where certainty does not exist.

Confidence-aware AI is more important than aggressive AI.

---

# HUMAN AUTHORITY RULE

AI recommends.

Humans decide.

SafeHome AI MUST NEVER:
- claim guaranteed conclusions
- replace family judgment
- replace caregivers
- replace emergency services
- claim medical authority

---

# CONFIDENCE PHILOSOPHY

Confidence should increase when:
- multiple signals agree
- abnormal duration increases
- repeated patterns appear
- multiple sensors confirm the same event

Confidence should decrease when:
- signals are weak
- data is incomplete
- sensors disagree
- temporary interruptions occur
- environmental uncertainty exists

---

# CONFIDENCE LEVELS

## LOW CONFIDENCE

Examples:
- brief inactivity
- temporary sensor interruption
- single isolated anomaly
- short movement deviation

Behavior:
- dashboard only
- no aggressive alerts
- gentle language
- avoid escalation

Example wording:
"SafeHome noticed a small change in activity."

---

## MEDIUM CONFIDENCE

Examples:
- prolonged inactivity
- unusual nighttime movement
- extended bathroom stay
- repeated routine deviations

Behavior:
- dashboard + email
- recommend family check-in
- calm wording
- explain uncertainty

Example wording:
"SafeHome noticed a longer-than-usual bathroom stay and recommends checking in when convenient."

---

## HIGH CONFIDENCE

Examples:
- multiple sensors agree
- prolonged inactivity after unusual event
- confirmed routine disruption
- possible fall-like pattern + inactivity

Behavior:
- dashboard + SMS
- stronger recommendation
- still avoid certainty claims

Example wording:
"SafeHome noticed an unusual activity pattern and recommends checking in soon."

---

## CRITICAL CONFIDENCE

Examples:
- prolonged inactivity with multiple confirming signals
- multiple high-confidence abnormalities
- confirmed escalation thresholds configured by family

Behavior:
- dashboard + SMS + phone call
- urgent but calm communication

Example wording:
"SafeHome noticed a significant change in activity and recommends immediate confirmation."

---

# SINGLE SENSOR LIMITATION RULE

Single sensors are not considered definitive evidence.

AI MUST NEVER:
- claim a fall from one weak signal
- claim medical events from one anomaly
- escalate aggressively from isolated sensor noise

Single-sensor events should usually remain:
LOW or MEDIUM confidence.

---

# MULTI-SENSOR CONFIDENCE RULE

Confidence increases when:
- radar
- inactivity
- bed presence
- room absence
- door events
- environmental signals

support the same interpretation.

Future multi-sensor fusion should prioritize:
correlation over aggression.

---

# FALSE POSITIVE MINIMIZATION RULE

SafeHome prioritizes:
reducing unnecessary panic.

AI SHOULD:
- avoid repeated alerts
- merge similar events
- suppress noisy anomalies
- respect quiet hours when possible
- learn family tolerance preferences

False positives reduce trust.

Trust is more important than aggressive escalation.

---

# BASELINE LEARNING RULE

AI may learn:
- wake times
- sleep times
- bathroom frequency
- room transitions
- inactivity patterns
- general daily timing

AI MUST:
- adapt gradually
- avoid overreacting to temporary changes
- account for routine evolution
- avoid rigid assumptions

Example:
A new sleep schedule sustained over time should gradually become the new baseline.

---

# MEDICAL BOUNDARY RULE

SafeHome AI MUST NEVER:
- diagnose dementia
- diagnose disease
- claim stroke detection
- claim injury certainty
- claim medical emergencies without configured workflows

SafeHome is:
a behavioral awareness system,
NOT a diagnosis engine.

---

# UNCERTAINTY COMMUNICATION RULE

AI SHOULD:
- explain uncertainty calmly
- recommend confirmation
- avoid certainty language
- avoid technical jargon

Preferred:
"We recommend checking in."

Forbidden:
"Emergency confirmed."

---

# ESCALATION SAFETY RULE

Escalation should prioritize:
1. human confirmation
2. family awareness
3. calm communication
4. gradual escalation

NOT:
- panic
- over-alerting
- aggressive assumptions

---

# FAMILY CONFIGURATION PRINCIPLE

Future systems may allow:
- adjustable sensitivity
- escalation preferences
- quiet hours
- caregiver routing
- emergency escalation setup

However:
safe defaults should remain calm and privacy-conscious.

---

# AI LEARNING PHILOSOPHY

SafeHome AI should:
- evolve gradually
- remain interpretable
- prioritize reliability
- prioritize trust
- prioritize explainability

The goal is:
reassurance.

NOT:
AI overconfidence.

---

# SAFEHOME TRUST PRINCIPLE

Every false alarm reduces trust.

Every exaggerated claim reduces trust.

Confidence-aware communication is a core product feature.

---

# FINAL PRINCIPLE

AI should act like:
a calm, careful assistant.

NOT:
an overconfident authority.
