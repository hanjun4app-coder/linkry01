# SENSOR_TRUST_MODEL.md

# SafeHome Sensor Trust & Multi-Sensor Fusion Model

Version: v1.0
Phase: Multi-Sensor AI Foundation

Purpose:
Define sensor reliability, trust weighting, fusion principles, and sensor conflict handling for SafeHome behavioral AI systems.

These rules apply to:
- Aqara FP2
- bed sensors
- door sensors
- environmental sensors
- future mmWave systems
- future multi-sensor AI systems

---

# CORE PRINCIPLE

No single sensor should be treated as absolute truth.

Behavioral confidence should emerge from:
- correlation
- duration
- consistency
- multi-sensor agreement

NOT:
single isolated events.

---

# SENSOR TRUST PHILOSOPHY

Sensors provide:
signals,
NOT certainty.

AI systems should interpret:
patterns,
NOT isolated sensor noise.

---

# SENSOR TRUST LEVELS

## HIGH TRUST SENSORS

Typically:
- bed occupancy sensors
- sustained presence sensors
- multi-point mmWave tracking

Useful for:
- sleep confirmation
- room occupancy
- prolonged inactivity validation

Still NOT definitive alone.

---

## MEDIUM TRUST SENSORS

Typically:
- FP2 room tracking
- motion sensors
- room transitions
- door sensors

Useful for:
- movement patterns
- activity timing
- behavioral baselines

May suffer:
- occlusion
- temporary loss
- multi-person confusion

---

## LOW TRUST SIGNALS

Typically:
- isolated motion loss
- temporary disconnects
- weak environmental anomalies

Should rarely trigger:
major escalation alone.

---

# SINGLE SENSOR LIMITATION RULE

Single sensors MUST NOT:
- confirm medical events
- confirm falls
- trigger aggressive escalation
- claim certainty

Single sensor events should generally remain:
LOW or MEDIUM confidence.

---

# MULTI-SENSOR FUSION PRINCIPLE

Confidence increases when:
multiple sensors support the same interpretation.

Examples:

FP2 inactivity
+
bed absence
+
bathroom occupancy
=
higher confidence event.

---

# SENSOR CORRELATION RULE

AI systems should prioritize:
cross-sensor consistency.

Example:
FP2 lost tracking
BUT
bed sensor confirms presence
=
likely tracking interruption,
NOT disappearance.

---

# SENSOR CONFLICT RULE

When sensors disagree:
AI should prefer:
- lower confidence
- human confirmation
- observation continuation

NOT:
aggressive escalation.

---

# TEMPORARY SENSOR FAILURE RULE

Temporary signal loss is common.

AI systems MUST:
- tolerate temporary disconnects
- avoid panic escalation
- retry observation
- maintain uncertainty awareness

Short disconnects should NOT:
trigger emergency assumptions.

---

# ROOM-LEVEL TRUST MODEL

Different rooms may require:
different trust weighting.

Examples:

Bathroom:
higher sensitivity

Bedroom:
higher inactivity tolerance

Living room:
more movement variability

Kitchen:
short-duration movement expected

---

# MULTI-PERSON ENVIRONMENT RULE

FP2 and similar sensors may struggle with:
- overlapping occupants
- guests
- caregivers
- pets

AI systems MUST:
- reduce confidence in ambiguous environments
- avoid identity assumptions
- avoid overconfidence

---

# PET INTERFERENCE RULE

Future systems should consider:
- pets
- robotic vacuums
- environmental movement

Small movement anomalies should NOT:
trigger human-risk escalation automatically.

---

# SENSOR HEALTH MONITORING RULE

Future systems should monitor:
- disconnect frequency
- signal stability
- unusual silence
- abnormal sensor behavior

Sensor reliability should influence:
AI confidence scoring.

---

# SENSOR PLACEMENT PRINCIPLE

Sensor placement strongly affects:
- reliability
- confidence
- false positive rate

Future installer guidance should define:
- room placement standards
- angle recommendations
- coverage limitations

---

# AI LEARNING LIMITATIONS

AI learning MUST account for:
- sensor noise
- incomplete observations
- environmental variability

AI MUST NEVER:
assume perfect sensing.

---

# ESCALATION SAFETY RULE

Aggressive escalation should require:
- multiple supporting signals
- sustained abnormality
- confidence thresholds

Single weak anomalies should favor:
continued observation.

---

# SENSOR PRIORITY EXAMPLES

Examples only:

Bed occupancy
>
temporary motion loss

Sustained inactivity
+
multiple sensors
>
single isolated event

Human confirmation
>
sensor assumptions

---

# HUMAN CONFIRMATION PRINCIPLE

When uncertainty exists:
prefer human confirmation.

AI should recommend:
checking,
NOT declaring certainty.

---

# FUTURE SENSOR TYPES

Future SafeHome systems may support:
- bed pressure sensors
- door sensors
- environmental sensors
- voice confirmation systems
- wearable integrations
- advanced mmWave systems

However:
all future sensors must follow:
bounded-confidence principles.

---

# SAFEHOME SENSOR PHILOSOPHY

Sensors exist to:
support family awareness.

NOT:
create surveillance certainty.

The system should remain:
- careful
- explainable
- confidence-aware
- human-centered

---

# FINAL PRINCIPLE

Sensor data is evidence,
NOT truth.

Trust should emerge from:
correlation,
consistency,
and careful interpretation.
