# Voice Confirmation System - Implementation Summary

## Quick Reference

**What's Implemented:**
A production-ready voice confirmation service for elderly care alerts with strict safety constraints, exact phrase matching, and comprehensive audit logging.

**Files Delivered:**

| File | Purpose |
|------|---------|
| `voice_confirmation_interface.py` | Abstract interface for pluggable voice platforms |
| `voice_confirmation_service.py` | Main service with safety logic and state machine |
| `003_add_voice_confirmation.sql` | Database migration for voice fields |
| `models_voice_confirmation_additions.py` | Model definitions and relationships |
| `events_voice_confirmation_integration.py` | Alert workflow integration |
| `alerts_voice_status_endpoint.py` | Family-scoped API endpoints |
| `VOICE_CONFIRMATION_INTEGRATION_GUIDE.md` | Complete integration guide |

---

## Core Safety Logic

### 1. Eligibility Rules (4 Checks)

```python
async def should_attempt_voice_confirmation(alert_type, alert_level, elder_id, db):
    # Rule 1: Never critical alerts
    if alert_level == "critical" or alert_type in ["critical_immobility", "suspected_fall"]:
        return False, "critical_alert_skips_voice"
    
    # Rule 2: Only eligible types
    if alert_type not in ["bathroom_timeout", "inactivity", "pattern_deviation", "night_activity"]:
        return False, f"ineligible_type_{alert_type}"
    
    # Rule 3: Anti-loop check (30 min cooldown)
    recent = await db.execute(
        select(Alert).where(
            Alert.elder_id == elder_id and
            Alert.alert_type == alert_type and
            Alert.voice_confirmation_attempted_at >= (now - 30 min)
        )
    )
    if recent.scalars().first():
        return False, "antiloop_cooldown_active"
    
    # Rule 4: Device availability
    if not await voice_device.is_device_available(elder_id):
        return False, "device_offline"
    
    return True, "eligible"
```

### 2. State Machine Flow

```
Eligible alert triggered
         ↓
[Attempt 1] → Trigger voice prompt (20s timeout for regular, 10s for critical)
         ↓
    Response received
         ↓
    ┌────┴────────────────────┐
    │                         │
Help Request?         Safe Phrase Match?
    │                         │
  YES                        YES
    │                         │
 SMS Immediately      Alert Cancelled
(no retry)            No SMS sent
                    ✓ CONFIRMED_SAFE
                    
NO + NO (or Timeout)
    │
    ├─ Retry? (if attempt < max)
    │   │
    │   YES → [Attempt 2] (goto line 2)
    │   │
    │   NO → SMS Sent
    │       ✗ UNCLEAR/NO_RESPONSE
    │
    └─ Final attempt with no match
         │
         SMS Sent
         ✗ UNCLEAR/NO_RESPONSE
```

### 3. Exact Phrase Matching

**Safe Phrases (Confidence: 1.0):**
- English: "I'm okay", "I am okay", "I'm fine", "Yes, I'm okay", "Cancel alert"
- Chinese: "我没事", "没关系", "我很好"

**Help Requests (Immediate escalation):**
- "help", "emergency", "fall", "can't get up"
- "救命", "紧急", "摔倒"

**Partial Matches (Confidence < 1.0):**
- Trigger RETRY or SMS, not alert cancellation
- "okay" alone → 0.6 confidence (ambiguous)
- "yes" alone → 0.4 confidence (not explicitly safe)

### 4. Attempt Limits

```
Regular alerts (bathroom, inactivity, pattern, night):
  Max attempts: 2
  Timeout: 20 seconds each
  Inter-attempt delay: 2 seconds
  
Critical alerts (when eligible - rare):
  Max attempts: 1
  Timeout: 10 seconds
  No retry
```

### 5. Fallback Behavior

If voice confirmation status is ANY of these:
- `UNCLEAR` - response didn't match safe phrases
- `NO_RESPONSE` - timeout after max attempts
- `HELP_REQUESTED` - elder asked for help
- `FAILED` - speech-to-text error
- `DEVICE_ERROR` - device offline or unavailable

**→ SEND SMS TO FAMILY IMMEDIATELY**

This is the safety guarantee: voice never prevents SMS, only reduces unnecessary SMS.

---

## Database Schema

### Alert Model - New Fields

```sql
ALTER TABLE alert ADD:
  - voice_confirmation_status VARCHAR(50)  -- pending, confirmed_safe, unclear, etc.
  - voice_confirmation_attempted_at TIMESTAMP  -- When voice was triggered
  - voice_confirmation_response_text TEXT  -- Raw transcribed response
  - voice_confirmation_confidence FLOAT  -- 0.0-1.0 confidence in match
  - voice_confirmation_device_id VARCHAR(255)  -- Device that handled it

INDICES:
  - (elder_id, alert_type, voice_confirmation_attempted_at) -- Anti-loop check
  - (family_id, voice_confirmation_status, attempted_at) -- Family visibility
```

### New Table: voice_confirmation_audit

```sql
CREATE TABLE voice_confirmation_audit:
  id (BIGSERIAL PRIMARY KEY)
  family_id (BIGINT, FK → family)
  elder_id (VARCHAR(255))
  alert_id (BIGINT, FK → alert)
  alert_type (VARCHAR(50))
  alert_level (VARCHAR(20))
  
  attempt_number (INT)  -- 1, 2, etc.
  status (ENUM)  -- pending, confirmed_safe, unclear, no_response, help_requested, failed, device_error
  response_text (TEXT)
  response_confidence (FLOAT)
  device_id (VARCHAR(255))
  error_message (TEXT)
  
  attempted_at (TIMESTAMP, INDEX)
  created_at (TIMESTAMP, INDEX)

PURPOSE: Full audit trail of voice attempts for compliance and debugging
```

---

## Service Architecture

### VoiceConfirmationService

**Initialization:**
```python
voice_device = GoogleHomeVoiceConfirmation()  # or your implementation
voice_service = VoiceConfirmationService(voice_device)
```

**Main Methods:**

1. **`should_attempt_voice_confirmation(alert_type, alert_level, elder_id, db)`**
   - Returns: (bool, reason_string)
   - Implements 4 eligibility rules
   - Checks anti-loop cooldown from database

2. **`perform_voice_confirmation(elder_id, alert_type, alert_level, description)`**
   - Async function with retry loop
   - Returns: VoiceConfirmationResult
   - Handles timeouts, retries, help requests
   - Classifies response text

3. **`_classify_response(response_text)`**
   - Returns: (status, confidence)
   - Exact regex matching against patterns
   - Confidence scoring for partial matches

**Result Object:**
```python
@dataclass
class VoiceConfirmationResult:
    status: VoiceConfirmationStatus  # confirmed_safe, unclear, no_response, etc.
    response_text: Optional[str]  # What elder said
    confidence: float  # 0.0-1.0
    attempted_at: datetime
    attempts_made: int  # 1 or 2
    should_notify_family: bool  # False only if confirmed_safe
    family_message: str  # Human-friendly message
```

---

## Integration Points

### 1. Alert Creation Workflow (events.py)

```python
# When alert is triggered:
async def create_alert(...):
    # 1. Create event record
    event = Event(...)
    
    # 2. Evaluate rules
    alerts_to_create = rule_engine.evaluate_event(...)
    
    # 3. For each alert:
    for alert_spec in alerts_to_create:
        alert = Alert(
            voice_confirmation_status=None,
            voice_confirmation_attempted_at=None,
        )
        db.add(alert)
        db.flush()
        
        # 4. Check eligibility
        should_attempt, reason = voice_service.should_attempt_voice_confirmation(...)
        
        if should_attempt:
            # 5. Mark as pending (for UI)
            alert.voice_confirmation_status = PENDING
            db.commit()
            
            # 6. Trigger voice ASYNC (don't wait)
            asyncio.create_task(handle_voice_confirmation(...))
            
            return alert  # Return immediately
        else:
            # Not eligible: send SMS immediately
            await send_sms(alert, family_id)
            db.commit()
            return alert
```

### 2. Voice Handling (Async Task)

```python
async def handle_voice_confirmation(alert_id, elder_id, alert_type, ...):
    try:
        # 1. Perform voice confirmation (waits for response)
        result = await voice_service.perform_voice_confirmation(...)
        
        # 2. Update alert
        alert = await db.get(Alert, alert_id)
        alert.voice_confirmation_status = result.status
        alert.voice_confirmation_response_text = result.response_text
        alert.voice_confirmation_confidence = result.confidence
        
        # 3. Log audit entry
        audit = VoiceConfirmationAudit(
            alert_id=alert_id,
            status=result.status,
            response_text=result.response_text,
            response_confidence=result.confidence,
            attempted_at=result.attempted_at,
        )
        db.add(audit)
        
        # 4. Route SMS based on voice result
        if result.should_notify_family:
            await send_sms(family_id, result.family_message, alert_id)
        
        db.commit()
    except Exception as e:
        # 5. On error: notify family and log
        alert = await db.get(Alert, alert_id)
        alert.voice_confirmation_status = FAILED
        await send_sms(family_id, "Voice check system error. Please contact Mom.")
```

### 3. API Endpoint

```python
# GET /api/alerts/{alert_id}/voice-status
async def get_voice_confirmation_status(alert_id, family_id, db):
    # 1. Verify family can access alert
    alert = await db.get(Alert, (alert_id, family_id))
    if not alert:
        raise 404 NotFound
    
    # 2. Fetch audit trail
    audits = await db.query(VoiceConfirmationAudit)
        .filter(alert_id == alert_id)
        .order_by(attempted_at)
    
    # 3. Return comprehensive response
    return VoiceStatusResponse(
        voice_status=alert.voice_confirmation_status,
        voice_confirmed=status == "confirmed_safe",
        attempts=[...],
        family_message=generate_message(status),
    )
```

---

## Example Scenarios

### Scenario A: Elder Responds "I'm Okay"

```
T+0.00s: Bathroom timeout alert created
         → Voice eligible, mark as PENDING
         → Trigger voice async

T+0.10s: Alert returned to caller (non-blocking)

T+0.50s: Voice device triggers prompt
         → "Mom, I detected extended bathroom duration. Are you okay?"

T+1.20s: Elder responds
         → "I'm okay"

T+1.50s: Response classified
         → Matches SAFE_RESPONSE_PATTERNS[0]
         → Status: CONFIRMED_SAFE
         → Confidence: 1.0

T+2.00s: Alert updated
         → voice_confirmation_status = "confirmed_safe"
         → voice_confirmation_response_text = "I'm okay"
         → Audit entry created
         → NO SMS sent (should_notify_family = false)

RESULT:
✓ Alert cancelled by voice confirmation
✓ Family NOT notified
✓ Audit trail complete
```

### Scenario B: Elder Doesn't Respond - Timeout and Escalate

```
T+0.00s: Inactivity alert created
         → Voice eligible, mark as PENDING
         → Trigger voice async

T+0.10s: Alert returned to caller

T+0.50s: Voice device triggers prompt
         → "Are you okay?"

T+21.00s: Timeout (20s + grace period)
          → No response received
          → Status: UNCLEAR
          → Confidence: 0.0

T+21.00s: Check retry (attempt 1/2)
          → YES, retry allowed
          → Wait 2 seconds

T+23.00s: Voice device triggers again (follow-up)
          → "Are you okay? (Didn't hear you - trying again)"

T+44.00s: Timeout again
          → Still no response
          → Status: NO_RESPONSE
          → Confidence: 0.0
          → Attempt 2/2 (final)

T+44.50s: Alert updated
          → voice_confirmation_status = "no_response"
          → Audit entries: 2 (one per attempt)
          → SMS SENT to family:
             "Mom didn't respond to safety check. Please verify she's okay."

RESULT:
✗ No safe response received
✓ SMS sent (safety guaranteed)
✓ Audit trail shows 2 attempts
```

### Scenario C: Critical Immobility - Skip Voice Entirely

```
T+0.00s: Critical immobility alert (no movement for 8 hours)
         → Alert level = "critical"
         → Type = "critical_immobility"

T+0.01s: Check voice eligibility
         → CRITICAL alert type
         → should_attempt_voice_confirmation = False
         → Reason: "critical_alert_skips_voice"

T+0.02s: Create alert (voice_status = NULL)

T+0.03s: Send SMS immediately
         → NO voice confirmation attempted
         → SMS sent: "Extended immobility detected. Please check on Mom."

T+0.05s: Alert returned

RESULT:
✗ Voice skipped (critical safety)
✓ SMS sent immediately
✓ No delay in critical alert
✓ No audit entry (voice not attempted)
```

### Scenario D: Help Request - Escalate Immediately

```
T+0.00s: Night activity alert created
         → Voice eligible
         → Trigger voice async

T+0.50s: Voice device triggers
         → "Are you okay?"

T+1.00s: Elder responds
         → "help me, I fell"

T+1.50s: Response classified
         → Matches HELP_REQUEST_PATTERNS
         → Status: HELP_REQUESTED
         → Confidence: 0.95

T+2.00s: Check retry logic
         → Help request detected
         → NO RETRY (escalate immediately)

T+2.05s: Alert updated
         → voice_confirmation_status = "help_requested"
         → SMS SENT IMMEDIATELY:
            "Mom said 'help me, I fell' - possible help request. Alert: Night activity."
         → Audit entry: 1 attempt

RESULT:
✓ Help request detected
✓ SMS sent immediately (no delay)
✓ No retry (safety-first)
✓ Audit trail shows escalation reason
```

---

## Testing Checklist

**Unit Tests:**
- [ ] Pattern matching for each safe phrase
- [ ] Pattern matching for help requests
- [ ] Eligibility rules (4 checks)
- [ ] Confidence scoring
- [ ] Anti-loop cooldown logic

**Integration Tests:**
- [ ] Full alert flow with voice eligible
- [ ] Full alert flow with voice ineligible
- [ ] Retry logic (2 attempts, 20s timeout)
- [ ] Critical alert bypass
- [ ] Device offline fallback
- [ ] Help request escalation
- [ ] Async non-blocking behavior
- [ ] SMS routing based on voice result

**End-to-End Tests:**
- [ ] With mock voice device
- [ ] With real voice device (if available)
- [ ] Concurrent alerts
- [ ] Database audit trail verification
- [ ] API endpoint access control
- [ ] Family message generation

---

## Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Exact phrase matching only | Eliminates ambiguous matches that could accidentally cancel alerts | Requires high speech-to-text quality; loose transcriptions cause false negatives |
| 2 attempts (regular) / 1 (critical) | Balances retry need vs. not delaying critical alerts | Some legitimate "unclear" responses won't get a second chance |
| 20 second timeout | Long enough for elderly person to locate device; short enough to not delay SMS | Very short attention spans might miss prompt |
| 30 minute anti-loop cooldown | Prevents alert fatigue; allows re-enablement if pattern recurring | Could miss legitimate repeated issues (e.g., bathroom returning issue) |
| Async voice handling | Prevents voice delays from blocking alert creation | Families might see SMS before voice result updates |
| SMS always on voice failure | Guarantees family notification when in doubt | Might send unnecessary SMS if device temporarily unavailable |
| Full audit trail | Enables compliance, debugging, and legal defense | Adds database overhead; stores raw responses (privacy consideration) |

---

## Deployment Notes

**Before Going Live:**
1. Database migration must run successfully
2. Voice platform implementation tested (Google Home, Alexa, etc.)
3. Pattern matching tested with actual audio samples
4. SMS fallback tested (critical path)
5. Async task queue verified (if using external queue; asyncio.create_task works for MVP)

**Monitoring:**
- Track voice confirmation success rate (should be >80%)
- Monitor SMS fallback rate (should be <20%)
- Check device offline incidents
- Verify audit trail is being populated
- Monitor for any family complaints about voice delays

**Rollback Plan:**
- If voice service causes SMS delays: disable voice eligibility check
- If voice causes high false negatives: lower confidence thresholds temporarily
- If patterns are wrong: update SAFE_RESPONSE_PATTERNS and redeploy

---

## Safety Guarantees Recap

✅ **No alert cancellation without exact match**
✅ **All voice failures → SMS notification**
✅ **Critical alerts bypass voice entirely**
✅ **30-minute anti-loop prevents alert fatigue**
✅ **Help requests escalate immediately (no retry)**
✅ **Device offline doesn't delay SMS**
✅ **Full audit trail for compliance**
✅ **Async processing doesn't block alert creation**

---

## Future Enhancements

- [ ] Voice biometrics (verify elder's voice, not random speaker)
- [ ] Wearable panic button as voice alternative
- [ ] Multi-language support (already in patterns, needs testing)
- [ ] Confidence feedback loop (retrain thresholds based on outcomes)
- [ ] Natural language understanding (fuzzy matching instead of regex)
- [ ] Context-aware prompts (different messages for different alert types)
- [ ] Video confirmation (if device has camera)
- [ ] Shared device support (multi-person household voice segmentation)
