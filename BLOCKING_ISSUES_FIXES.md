# CTO Audit Fixes: Unblocking Live Deployment

## Status: 🔴 CRITICAL - 4.5 Hours to Production Ready

---

## Fix #1: Data Reliability → Rules Integration ⚠️ CRITICAL

**Problem:** Rules engine ignores `data_reliability` flag → undefined behavior on napping

**File:** `baseline_aware_rule_engine_fixed.py` (PROVIDED)

**Key changes:**
```python
# OLD (broken)
def evaluate_event(event, baseline):
    alerts = rule_engine.check_inactivity(event)  # No consideration of data quality

# NEW (fixed)
def evaluate_event(event, baseline, data_reliability):
    # If degraded (60-120 min): Don't trigger inactivity alert
    if data_reliability == "degraded":
        inactivity_alert = None  # Suppress (likely napping)
    
    # Scale thresholds conservatively
    inactivity_threshold = max(6h, baseline * 2.0)  # Was max(4h, baseline * 1.5)
```

**Integration steps:**
1. Replace `app/rules.py` BaselineAwareRuleEngine with `baseline_aware_rule_engine_fixed.py`
2. Update `_check_inactivity()` to:
   - Accept `data_reliability` parameter
   - Return `AlertSpec(triggered_by_degraded_data=True)` when degraded
3. In `events.py`, when calling rule engine:
   ```python
   alerts = rule_engine.evaluate_event(
       event=event,
       baseline=baseline,
       data_reliability=data_reliability_state,  # NEW
   )
   ```
4. Filter alerts before SMS:
   ```python
   for alert in alerts:
       if alert.triggered_by_degraded_data:
           # Create alert for audit trail, don't send SMS
           continue
       else:
           # Normal alert—send SMS
   ```

**Testing:**
- Scenario 3 (napping 2 hours): Should NOT trigger alert ✓
- Scenario 2 (no activity 2 hours, daytime): Should show "limited monitoring" message, not SMS

**Time estimate:** 45 minutes

---

## Fix #2: Learning Period Mode (Days 1-7) ⚠️ CRITICAL

**Problem:** System switches from generic to learned baseline on day 8 without quality check

**File:** `baseline_service_with_learning_period.py` (NEEDS CREATION)

**Key changes:**
```python
# Calculate days since first event
days_since_start = (now - first_event_date).days

if days_since_start < 7:
    # LEARNING PERIOD: Use conservative generic thresholds
    inactivity_threshold = 6 * 60  # 6 hours (not 4)
    bathroom_threshold = 30  # minutes
    return {
        "is_learning_period": True,
        "baseline": None,  # Don't use learned baseline yet
        "quality_score": 0.0,
    }
else:
    # ACTIVE PERIOD: Use learned baseline
    # But validate quality first
    if baseline.quality_score < 0.5:
        # Low quality—still use conservative thresholds
        return {
            "is_learning_period": False,
            "baseline": baseline,
            "quality_score": baseline.quality_score,
            "conservative_mode": True,
        }
    else:
        return {
            "is_learning_period": False,
            "baseline": baseline,
            "quality_score": baseline.quality_score,
            "conservative_mode": False,
        }
```

**Integration steps:**
1. Add `first_event_date` column to Elder table
2. In `baseline_service.py`, wrap `calculate_baseline()`:
   ```python
   async def get_active_baseline(db, family_id, elder_id):
       # Check learning period
       if in_learning_period(elder_id):
           return None  # Force generic thresholds
       
       # Otherwise return baseline if good quality
       baseline = await calculate_baseline(...)
       if baseline.quality_score < 0.5:
           return None  # Force conservative thresholds
       return baseline
   ```
3. Update rule engine to use returned baseline
4. Add frontend message for learning period:
   ```
   "System is learning your routine. Check back in 7 days for better alerts."
   ```

**Testing:**
- Days 1-7: All rules use 6h inactivity threshold ✓
- Day 8: Rules switch to baseline (with quality check) ✓
- Scenario 1 (45 min bathroom): Should trigger ✓
- Scenario 3 (2 hour nap): Should NOT trigger ✓

**Time estimate:** 1 hour

---

## Fix #3: Single-Person Household Requirement ⚠️ CRITICAL

**Problem:** Motion sensors aggregate all motion → baseline learning fails with visitors

**File:** `DEPLOYMENT_REQUIREMENTS.md` (NEEDS CREATION)

**Key changes:**
- Document in deployment docs:
  ```
  MVP LIMITATION: Single-person households only
  
  Reason: Motion sensors see all movement (elder + family/pets/visitors)
  Result: Baseline learning includes other people's activity
  Impact: False positives when multiple people in home
  
  Workaround (future): Segment baseline by time-of-day or use ML to identify elder-specific motion
  ```

- Add deployment validation:
  ```python
  # In onboarding:
  def validate_single_person_household(elder_id):
      # Check: Is there a baseline with excessive variation?
      # If >50% variation between days → likely multi-person
      # Show warning to family
  ```

**Integration steps:**
1. Add to deployment checklist: "Confirm single-person household"
2. Add to frontend setup wizard: "Is [elder name] the only person usually in the home?"
3. If "No": Show warning and link to future multi-person update

**Testing:**
- Document why system fails with multiple people ✓

**Time estimate:** 15 minutes

---

## Fix #4: Voice Pattern Matching with Real Audio ⚠️ MEDIUM

**Problem:** Mock device always returns "I'm okay" → untested on real elderly speech

**File:** `test_voice_patterns_real_audio.py` (NEEDS CREATION)

**Key changes:**
```python
import librosa
import json

# Sample audio files needed:
test_samples = [
    ("elder1_okay.wav", "I'm okay"),
    ("elder2_fine.wav", "I'm fine"),
    ("elder3_slurred.wav", "Iiiii'm okay"), # speech impediment
    ("elder4_mumble.wav", "mmhm okay"),    # mumbling
    ("elder5_worried.wav", "yeah I'm okay but..."), # hedging
    # ... 10 total samples
]

# Test classification:
for audio_file, expected_phrase in test_samples:
    # 1. Convert audio to text (using real STT)
    transcribed = await speech_to_text(audio_file)
    
    # 2. Classify response
    status, confidence = voice_service._classify_response(transcribed)
    
    # 3. Check result
    if status != "confirmed_safe" or confidence < 0.8:
        print(f"FAIL: {audio_file} - got {status} (confidence {confidence})")
    else:
        print(f"PASS: {audio_file}")

# Acceptance criteria: >80% of real samples classified correctly
```

**Integration steps:**
1. Record 10 audio samples (from family members simulating elderly)
2. Run `test_voice_patterns_real_audio.py`
3. If <80% pass: Adjust confidence thresholds or add fuzzy matching
4. Document results: "Voice pattern matching tested on X samples, Y% success rate"

**Testing:**
- Must pass before live deployment ✓

**Time estimate:** 2 hours

---

## Fix #5: Make Voice SMS Routing Synchronous ⚠️ MEDIUM

**Problem:** Voice result and SMS might arrive out of order (async background task)

**File:** `events_voice_confirmation_integration_fixed.py` (needs update)

**Key changes:**
```python
# OLD (broken—async SMS)
async def create_alert():
    voice_eligible = check_eligibility()
    if voice_eligible:
        # Mark pending, return immediately
        alert.voice_confirmation_status = "pending"
        db.commit()
        
        # SMS happens later (in background task)
        asyncio.create_task(handle_voice_confirmation(...))
        return alert

# NEW (fixed—sync SMS)
async def create_alert():
    voice_eligible = check_eligibility()
    if voice_eligible:
        alert.voice_confirmation_status = "pending"
        db.commit()
        
        # Wait for voice result (NOT blocking—still async, just not fired-and-forgotten)
        result = await voice_service.perform_voice_confirmation(...)
        
        # Update alert + SMS in same transaction
        alert.voice_confirmation_status = result.status
        if result.should_notify_family:
            await send_sms(family_id, result.message)
        
        db.commit()
        return alert
```

**Integration steps:**
1. Change `asyncio.create_task()` to `await` (remove fire-and-forget)
2. Move SMS sending into same transaction
3. Update timeout: Give voice 30 seconds (20s timeout + grace)
4. Test: Alert creation takes 30s max

**Testing:**
- SMS and alert status update consistently ✓
- No out-of-order notifications ✓

**Time estimate:** 30 minutes

---

## Deployment Checklist

Before going live, verify:

- [ ] Fix #1: Data reliability handled (rules suppress degraded alerts)
- [ ] Fix #2: Learning period implemented (days 1-7 conservative thresholds)
- [ ] Fix #3: Single-person household documented
- [ ] Fix #4: Voice pattern matching tested on 10 real audio samples (>80% success)
- [ ] Fix #5: SMS routing synchronous (no out-of-order notifications)

- [ ] Scenario 1 tested (45 min bathroom → voice → confirmed safe)
- [ ] Scenario 2 tested (2 hours no activity daytime → suppressed or conservative)
- [ ] Scenario 3 tested (napping → NO FALSE ALARM)
- [ ] Scenario 4 tested (voice timeout → SMS sent)
- [ ] Scenario 5 tested (clear response → alert cancelled)
- [ ] Scenario 6 tested (device offline → SMS immediately)

---

## Timeline

| Fix | Effort | Critical Path |
|-----|--------|---|
| Fix #1: Data reliability | 45 min | YES |
| Fix #2: Learning period | 1 hour | YES |
| Fix #3: Document requirement | 15 min | YES |
| Fix #4: Test real audio | 2 hours | BEFORE LIVE |
| Fix #5: Sync SMS | 30 min | NICE-TO-HAVE |
| **Scenario testing** | **1 hour** | **YES** |
| **TOTAL** | **~4.5 hours** | — |

---

## Go-Live Decision

After fixes 1-3 + scenario testing: ✅ **READY FOR LIVE**

After fixes 4: ✅ **PRODUCTION READY** (add real device)

