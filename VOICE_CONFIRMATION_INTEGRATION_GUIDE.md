# Voice Confirmation Integration Guide

## Overview

This guide documents the complete integration of voice confirmation into the elderly care monitoring system. Voice confirmation provides a safety gate to reduce false positives while maintaining strict safety guarantees.

**Safety Principle:** Voice confirmation reduces false positives, but NEVER proves safety unless response is explicit and matches exact expected phrases. If voice confirmation fails for any reason, the system defaults to notifying the family immediately.

---

## Architecture

```
Event → Rule Engine → Alert Created → Check Eligibility → Voice Eligible?
                                               │
                            ┌──────────────────┴──────────────────┐
                            │                                      │
                          YES                                      NO
                            │                                      │
                    Trigger Voice Async            Send SMS immediately
                    (non-blocking)                 Return alert
                            │
                    Voice Service                
                    Performs Confirmation
                            │
                    ┌───────┴────────────┐
                    │                    │
            Safe Response Matched    Response Unclear/No Match
                    │                    │
            Cancel Alert           Retry (if < max attempts)
            No SMS                  Then Send SMS if still unclear
```

---

## Files and Integration Points

### 1. Core Implementation

#### `app/services/voice_confirmation_interface.py`
- **What:** Abstract interface for voice platforms
- **Why:** Enables pluggable implementations (Google Home, Alexa, WebRTC, etc.)
- **Integration:** Inject concrete implementation into VoiceConfirmationService

#### `app/services/voice_confirmation_service.py`
- **What:** Main service with safety logic, pattern matching, state machine
- **Key Functions:**
  - `should_attempt_voice_confirmation()` - Eligibility check with 4 rules
  - `perform_voice_confirmation()` - Async state machine with retry logic
  - `_classify_response()` - Exact phrase matching (English + Chinese)

#### `003_add_voice_confirmation.sql`
- **What:** Database migration adding voice_confirmation fields
- **Fields Added:**
  - `alert.voice_confirmation_status`
  - `alert.voice_confirmation_attempted_at`
  - `alert.voice_confirmation_response_text`
  - `alert.voice_confirmation_confidence`
  - New table: `voice_confirmation_audit`

#### `app/models.py`
- **What:** Add VoiceConfirmationStatus enum and fields to Alert model
- **Fields:** See models_voice_confirmation_additions.py for exact definitions
- **Index:** Create on (elder_id, alert_type, attempted_at) for anti-loop check

#### `app/routes/events.py`
- **What:** Integrate voice confirmation into alert creation workflow
- **Flow:**
  1. Create event record
  2. Evaluate rules → get alerts
  3. Create alert record with voice_status=PENDING (if eligible)
  4. Trigger voice async via background task
  5. Return immediately (don't wait for voice result)
  6. Voice service updates alert and routes SMS independently

#### New Endpoint: `GET /api/alerts/{alert_id}/voice-status`
- **What:** Family-scoped endpoint to view voice confirmation details
- **Returns:** Status, attempts, confidence, transcribed response, family message
- **Access:** Only family members can view their own alerts

### 2. Safety Properties Implemented

#### Eligibility Rules (STRICT)

```python
1. Never for critical alerts
   - alert_level == "critical" → skip voice
   - alert_type in ["critical_immobility", "suspected_fall"] → skip voice

2. Only for eligible types
   - ALLOWED: bathroom_timeout, inactivity, pattern_deviation, night_activity
   - BLOCKED: Everything else

3. Anti-loop protection
   - No voice confirmation for same (elder_id, alert_type) within 30 minutes
   - Indexed query on (elder_id, alert_type, attempted_at)

4. Device availability
   - Check device online before triggering
   - If offline → send SMS immediately
```

#### Attempt Limits

```python
Regular alerts:
- Max 2 attempts
- 20 second timeout each
- 2 second pause between attempts

Critical alerts (when eligible):
- Max 1 attempt
- 10 second timeout
- No retry
```

#### Exact Phrase Matching

**English Safe Phrases:**
- "I'm okay"
- "I am okay"
- "I'm fine"
- "Yes, I'm okay"
- "Cancel alert"

**Chinese Safe Phrases:**
- "我没事" (I'm fine)
- "没关系" (It's okay)
- "我很好" (I'm very fine)

**Help Requests (escalate immediately):**
- "help", "emergency", "fall", "can't get up"
- "救命", "紧急", "摔倒"

#### Fallback Rules (MUST NOTIFY FAMILY)

```python
if voice_status in [
    "unclear",        # Didn't match safe phrases
    "no_response",    # No response after max attempts
    "help_requested", # Elder asked for help
    "failed",         # Speech-to-text error
    "device_error",   # Device offline/unavailable
]:
    send_sms_to_family()
```

---

## Integration Checklist

### Phase 1: Database & Models

- [ ] Run migration 003_add_voice_confirmation.sql
- [ ] Add VoiceConfirmationStatus enum to models.py
- [ ] Add voice_confirmation fields to Alert model
- [ ] Create VoiceConfirmationAudit model
- [ ] Create database indices for anti-loop check
- [ ] Test database constraints and relationships

### Phase 2: Service Implementation

- [ ] Create VoiceConfirmationInterface abstract class
- [ ] Implement VoiceConfirmationService with:
  - [ ] `should_attempt_voice_confirmation()` with 4 eligibility rules
  - [ ] `perform_voice_confirmation()` with state machine
  - [ ] `_classify_response()` with exact pattern matching
- [ ] Test pattern matching with sample audio transcripts
- [ ] Verify timeout and retry logic

### Phase 3: Platform Integration

- [ ] Implement concrete VoiceConfirmationInterface for your device:
  - [ ] Google Home integration (optional)
  - [ ] Alexa integration (optional)
  - [ ] Custom WebRTC/WebSocket (optional)
- [ ] Test device discovery and prompt triggering
- [ ] Test timeout handling when device is offline
- [ ] Implement fallback message delivery

### Phase 4: Alert Workflow Integration

- [ ] Update Alert creation flow in events.py to:
  - [ ] Check voice eligibility
  - [ ] Trigger voice async (don't block)
  - [ ] Create audit trail for all attempts
- [ ] Ensure SMS routing respects voice outcome
- [ ] Test async behavior (voice shouldn't delay alert creation)

### Phase 5: API Endpoints

- [ ] Create GET /api/alerts/{alert_id}/voice-status
- [ ] Create GET /api/alerts/voice-summary (optional)
- [ ] Add voice_confirmation to GET /api/alerts/{alert_id} response
- [ ] Test family-scoped access control
- [ ] Verify no family can see other families' voice attempts

### Phase 6: Testing

- [ ] Unit tests for exact phrase matching
- [ ] Unit tests for eligibility rules
- [ ] Unit tests for anti-loop cooldown
- [ ] Integration tests for full alert flow
- [ ] End-to-end tests with mock voice device
- [ ] Timeout and failure scenarios
- [ ] Concurrent alerts handling

---

## Testing Scenarios

### Scenario 1: Happy Path - Confirmed Safe

```
1. Bathroom timeout alert triggered
2. Voice eligible: type=bathroom_timeout, level=warning
3. System: "Mom, I detected extended bathroom duration. Are you okay?"
4. Elder: "I'm okay"
5. Result: CONFIRMED_SAFE, no SMS sent, alert cancelled
```

**Verify:**
- Alert has voice_confirmation_status = "confirmed_safe"
- SMS not sent to family
- Audit entry logged with response text and confidence=1.0

### Scenario 2: Unclear Response - Retry and Escalate

```
1. Inactivity alert triggered
2. Voice eligible: type=inactivity, level=warning
3. System: "Are you okay?"
4. Elder: "mm-hmm" (unclear)
5. System: 2 second pause, "Are you okay? (Didn't hear you - trying again)"
6. Elder: (no response - timeout)
7. Result: NO_RESPONSE, SMS sent
```

**Verify:**
- 2 audit entries (one per attempt)
- Second attempt has status=NO_RESPONSE
- SMS sent with message "Mom didn't respond to safety check"

### Scenario 3: Help Request - Escalate Immediately

```
1. Night activity alert triggered
2. Voice eligible: type=night_activity, level=warning
3. System: "Are you okay?"
4. Elder: "help me, I fell"
5. Result: HELP_REQUESTED, SMS sent immediately (no retry)
```

**Verify:**
- Status = "help_requested"
- Only 1 audit entry (no retry)
- SMS sent with escalation message
- No delay in notifying family

### Scenario 4: Critical Immobility - Skip Voice

```
1. Critical immobility alert triggered (elder hasn't moved in 8 hours)
2. Voice NOT eligible (critical alert)
3. SMS sent immediately
4. Voice confirmation skipped entirely
```

**Verify:**
- voice_confirmation_status remains NULL
- No audit entries created
- SMS sent immediately without voice attempt

### Scenario 5: Device Offline - SMS Immediately

```
1. Pattern deviation alert triggered
2. Voice eligible by type, but device offline check fails
3. SMS sent immediately
4. No voice attempt logged
```

**Verify:**
- voice_confirmation_status remains NULL
- should_attempt_voice_confirmation returns (False, "device_offline")
- SMS sent without voice attempt

### Scenario 6: Anti-Loop Protection

```
1. Bathroom timeout alert at 2:00 PM → voice triggered
2. Same elder, same alert type at 2:15 PM → voice NOT triggered
3. Same elder, same alert type at 2:35 PM → voice triggered (30 min passed)
```

**Verify:**
- Query for (elder_id, alert_type, attempted_at > 30min_ago)
- Second alert skips voice (anti-loop active)
- Third alert re-enables voice (cooldown expired)

---

## Response Classification Logic

### Pattern Matching with Confidence Scores

```python
Response: "I'm okay"
→ Match: SAFE_RESPONSE_PATTERNS[0] (^i\s*['\']m\s*okay$)
→ Status: CONFIRMED_SAFE, Confidence: 1.0
→ Action: Cancel alert, no SMS

Response: "yes, I'm okay"
→ Match: SAFE_RESPONSE_PATTERNS[3] (^yes\s*,?\s*i\s*['\']m\s*okay$)
→ Status: CONFIRMED_SAFE, Confidence: 1.0
→ Action: Cancel alert, no SMS

Response: "okay"
→ Partial Match: pattern "^okay" (confidence 0.6)
→ Status: UNCLEAR, Confidence: 0.6
→ Action: Retry if attempts < max, else SMS

Response: "help me!"
→ Match: HELP_REQUEST_PATTERNS (contains "help")
→ Status: HELP_REQUESTED, Confidence: 0.95
→ Action: SMS immediately, no retry

Response: "mmhmm"
→ No Match
→ Status: UNCLEAR, Confidence: 0.2
→ Action: Retry if attempts < max, else SMS

Response: (silence/timeout)
→ No Response
→ Status: NO_RESPONSE, Confidence: 0.0
→ Action: Retry if attempts < max, else SMS
```

---

## API Response Examples

### GET /api/alerts/12345/voice-status

**When confirmed safe:**
```json
{
  "alert_id": 12345,
  "alert_type": "bathroom_timeout",
  "alert_level": "warning",
  "alert_message": "Extended bathroom duration detected",
  "voice_status": "confirmed_safe",
  "voice_confirmed": true,
  "family_message": "Mom confirmed she is okay.",
  "first_attempt_at": "2026-04-27T12:32:00Z",
  "last_attempt_at": "2026-04-27T12:32:00Z",
  "total_attempts": 1,
  "attempts": [
    {
      "attempt_number": 1,
      "status": "confirmed_safe",
      "response_text": "I'm okay",
      "response_confidence": 1.0,
      "attempted_at": "2026-04-27T12:32:00Z"
    }
  ]
}
```

**When unclear after retries:**
```json
{
  "alert_id": 12346,
  "alert_type": "inactivity",
  "alert_level": "warning",
  "alert_message": "Extended inactivity detected",
  "voice_status": "no_response",
  "voice_confirmed": false,
  "family_message": "Mom didn't respond to the safety check. Please check on her.",
  "first_attempt_at": "2026-04-27T13:00:00Z",
  "last_attempt_at": "2026-04-27T13:00:05Z",
  "total_attempts": 2,
  "attempts": [
    {
      "attempt_number": 1,
      "status": "unclear",
      "response_text": "mm-hmm",
      "response_confidence": 0.3,
      "attempted_at": "2026-04-27T13:00:00Z"
    },
    {
      "attempt_number": 2,
      "status": "no_response",
      "response_text": null,
      "response_confidence": 0.0,
      "attempted_at": "2026-04-27T13:00:05Z"
    }
  ]
}
```

---

## Deployment Checklist

### Pre-Production

- [ ] All 6 integration phases complete
- [ ] All testing scenarios pass
- [ ] Pattern matching tested with real voice samples
- [ ] Anti-loop queries optimized and indexed
- [ ] Async task handling tested (no blocking)
- [ ] Voice device implementation complete
- [ ] Fallback SMS routing verified
- [ ] Audit trail complete for compliance

### Production Rollout

- [ ] Run database migration (with backup)
- [ ] Deploy voice_confirmation_service.py
- [ ] Deploy updated models.py
- [ ] Deploy updated events.py
- [ ] Deploy API endpoints
- [ ] Monitor for errors in first 24 hours
- [ ] Verify SMS fallback working
- [ ] Check audit trail population

### Post-Deployment Monitoring

- [ ] Track voice confirmation attempt rate
- [ ] Monitor confirmation success rate (should be >80% for working devices)
- [ ] Track SMS fallback rate (should be <20% if system working)
- [ ] Monitor device offline incidents
- [ ] Verify family satisfaction with experience
- [ ] Check for any false negatives (critical alerts with voice delays)

---

## Safety Guarantees

This implementation maintains these safety properties:

1. **No False Negatives from Voice:** If voice fails for ANY reason (unclear, no response, device offline, timeout), system defaults to SMS notification
2. **No Dangerous Delays:** Voice confirmation is async; original alert is created immediately
3. **Exact Matching Only:** Partial matches or ambiguous responses trigger retry/SMS, not alert cancellation
4. **Critical Alerts Skip Voice:** Immobility and fall alerts bypass voice entirely
5. **Anti-Loop Protection:** Same alert type won't attempt voice within 30 minutes
6. **Help Requests Escalate:** If elder mentions help-related words, immediate SMS (no retry)
7. **Audit Trail:** Every voice attempt logged for compliance and debugging
8. **Family Visibility:** Families can see exactly what happened with each alert

---

## Ongoing Risks and Mitigations

| Risk | Scenario | Mitigation |
|------|----------|-----------|
| Voice device offline | Device loses internet mid-alert | Check device availability before triggering; fallback to SMS |
| Elderly person can't reach device | Alert triggered but device out of reach | Can be addressed in future via wearable button or second device |
| Ambient noise causes misclassification | Background TV/radio interpreted as response | Require exact phrase matches, high confidence threshold |
| Device transcription errors | "I'm OK" → "I'm oak" | Pattern matching is loose on abbreviations but strict on full phrases |
| Multiple people in home | Child says "I'm okay" when elder is in trouble | Device must be calibrated to elder's voice, or add voice biometrics |

---

## Summary

Voice confirmation provides a valuable safety gate while maintaining strict safety guarantees. The system is designed to:

✅ Reduce false positives for non-critical alerts
✅ Default to family notification on any voice failure
✅ Keep implementation complexity manageable
✅ Provide full audit trail for compliance
✅ Support multiple platforms and voice devices
✅ Never delay critical alert detection

**Remember:** Voice confirmation is a convenience feature, not a safety feature. SMS notification is the safety mechanism. Voice just reduces unnecessary SMS for false positives.
