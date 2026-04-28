# Aqara FP2: Role Clarification

**Version**: 1.0  
**Date**: April 2026  
**Purpose**: Clarify the different roles of FP2 based on installation mode

---

## The Core Problem

> The Aqara FP2 is an excellent millimeter-wave radar sensor, but it cannot be expected to excel at both detailed behavior tracking AND fall detection simultaneously.

Attempting to use a single FP2 for both purposes leads to:
- Missed behavioral nuances (if tuned for fall detection)
- False fall positives (if tuned for behavior tracking)
- Overall accuracy degradation
- Confusion about what the system is actually detecting

**Solution**: Assign FP2 to one role per installation mode.

---

## Role 1: Wall-Mounted FP2 = Behavior Understanding

### What It Does

A **wall-mounted FP2** excels at understanding daily behavior patterns and patterns.

**Capabilities** (✅ Reliable):
- **Presence**: Is someone in the room?
- **Location**: Which zone/area of the room are they in?
- **Duration**: How long have they been in that location?
- **Transition**: Are they moving between zones?
- **Activity Level**: What intensity of movement? (static, low motion, high motion)

**Capabilities** (⚠️ Secondary):
- Post-fall inactivity (can detect prolonged stillness)

### Installation

- **Position**: Wall-mounted, 1-1.5m height
- **Angle**: Facing main activity area
- **Typical Rooms**: Bedroom, living room, bathroom, hallway
- **Mode**: `installation_mode: "wall_behavior"`

### Use Cases

✅ **Primary Detection**:
- Elderly person has been sitting in bedroom for 4 hours (activity drop)
- Bathroom visit was 20 minutes (long stay, check if okay)
- Night time wandering detected (unusual nighttime transitions)
- Living room activity is normal vs. abnormally low
- Out-of-bed activity vs. sleeping

✅ **Secondary Detection**:
- Detecting lack of activity after a detected fall
- Monitoring activity trends across the day

### What NOT to Use It For

❌ **Do NOT use for**:
- Fall detection as PRIMARY mechanism
- Height estimation during fall
- Precise impact analysis
- Catching all types of falls (e.g., gradual slides have different signature)

### Example Data Output

```json
{
  "timestamp": "2026-04-26T14:32:00Z",
  "device_id": "fp2_living_room_001",
  "installation_mode": "wall_behavior",
  "readings": [
    {
      "capability": "presence",
      "value": true,
      "confidence": 0.98
    },
    {
      "capability": "location",
      "value": "sofa_area",
      "confidence": 0.92
    },
    {
      "capability": "duration",
      "value": 3600,  // seconds
      "confidence": 0.95
    },
    {
      "capability": "activity_level",
      "value": "low",  // low, medium, high
      "confidence": 0.88
    }
  ]
}
```

---

## Role 2: Ceiling-Mounted FP2 = Fall Detection Assistance

### What It Does

A **ceiling-mounted FP2** provides overhead fall detection and presence monitoring.

**Capabilities** (✅ Reliable):
- **Fall Detected**: Radar pattern matches fall signature (rapid descent + impact)
- **Presence**: Is someone in the room?
- **Post-Fall Inactivity**: No motion after fall event detected

**Capabilities** (❌ NOT Reliable):
- Zone details (overhead view loses spatial precision)
- Activity type classification
- Duration in specific zones
- Behavior chain analysis

### Installation

- **Position**: Ceiling-mounted, central location
- **Angle**: Downward, full room coverage
- **Typical Rooms**: Bedroom (optional if fall risk), living room (if high fall risk)
- **Mode**: `installation_mode: "ceiling_fall"`

### Use Cases

✅ **Primary Detection**:
- Fall event detected (radar shows characteristic fall pattern)
- Person falls and remains on ground (post-fall inactivity)
- Fall during bathroom visit (high-risk area)
- Fall during nighttime (movement to bed/bathroom)

### Fall Alert Decision Tree

```
Fall Alert Triggered When:
├─ fall_detected = true
│  └─ AND post_fall_inactivity = true (person not moving after fall)
│     └─ OR no_arrival_to_safe_zone (2+ minutes without movement)
│
└─ ALERT: "Fall detected. Person on ground. Check immediately."
```

### What NOT to Use It For

❌ **Do NOT use for**:
- Detailed zone/location tracking
- Activity classification
- Duration analysis in specific zones
- Behavioral pattern understanding
- Night movement tracking (can't distinguish zones)
- Detecting subtle behavioral changes

### Example Data Output

```json
{
  "timestamp": "2026-04-26T07:42:15Z",
  "device_id": "fp2_bedroom_ceiling_001",
  "installation_mode": "ceiling_fall",
  "readings": [
    {
      "capability": "fall_detected",
      "value": true,
      "confidence": 0.94,
      "metadata": {
        "pattern": "rapid_descent_impact",
        "duration_ms": 450
      }
    },
    {
      "capability": "post_fall_inactivity",
      "value": true,
      "confidence": 0.88,
      "metadata": {
        "inactivity_duration_ms": 12000
      }
    },
    {
      "capability": "presence",
      "value": true,
      "confidence": 0.99
    }
  ],
  "alert_triggered": true,
  "alert_message": "Fall detected with post-fall inactivity. Check immediately."
}
```

---

## Side-by-Side Comparison

| Dimension | Wall FP2 | Ceiling FP2 |
|---|---|---|
| **Primary Purpose** | Behavior understanding | Fall detection |
| **Presence** | ✅ Excellent | ✅ Good |
| **Location/Zone** | ✅ Excellent | ❌ Poor |
| **Duration** | ✅ Excellent | ❌ N/A |
| **Transitions** | ✅ Good | ❌ Limited |
| **Activity Level** | ✅ Good | ❌ Limited |
| **Fall Detection** | ⚠️ Secondary | ✅ Excellent |
| **Post-Fall Inactivity** | ⚠️ Can detect | ✅ Primary |
| **Privacy** | ⚠️ Medium (side view) | ⚠️ Higher concern (overhead) |
| **Confidence Multiplier** | 0.95 | 0.85 |
| **Common Rooms** | Bedroom, living room, bathroom | Bedroom (optional), hallway (if fall risk) |

---

## System Integration

### Sensor Fusion Rules

The sensorFusion engine enforces these rules:

**Rule 1: Behavior Chain Detection**
```typescript
// ONLY use wall_behavior FP2 for behavior chains
if (device.installation_mode === 'ceiling_fall') {
  // ERROR: Do not use ceiling FP2 for behavior detection
  anomaly.severity = 'high';
  anomaly.message = 'Ceiling FP2 cannot be used for behavior chain analysis';
}
```

**Rule 2: Fall Detection Evidence**
```typescript
// Ceiling FP2 is PRIMARY for fall detection
if (device.installation_mode === 'ceiling_fall' && reading.capability === 'fall_detected') {
  weight = 0.8; // Primary evidence
}

// Wall FP2 provides secondary fall evidence
if (device.installation_mode === 'wall_behavior' && reading.capability === 'post_fall_inactivity') {
  weight = 0.3; // Supporting evidence only
}
```

**Rule 3: Alert Generation**
```typescript
// Fall alert requires: fall_detected (from ceiling_fall FP2)
// AND post_fall_inactivity (from any FP2, prefer ceiling)
if (
  fallDetected && 
  postFallInactivity && 
  primary_source === 'ceiling_fall'
) {
  alert_level = 'high';
}
```

---

## Common Mistakes

### ❌ Mistake 1: Using Ceiling FP2 for Behavior Tracking

**Problem**:
```
"I installed a ceiling FP2. I want it to track when the elderly person
is in the bedroom vs. living room."
```

**Why It Doesn't Work**:
- Ceiling overhead view doesn't distinguish zones well
- Activity intensity looks the same from above
- You lose spatial awareness of movement

**Solution**:
- Install wall-mounted FP2 for behavior tracking
- Use ceiling FP2 ONLY for fall detection

### ❌ Mistake 2: Expecting One FP2 to Do Both

**Problem**:
```
"I want one FP2 that can detect both daily behavior AND falls."
```

**Why It Doesn't Work**:
- Settings for fall detection (high sensitivity) cause false positives in behavior
- Settings for behavior tracking miss subtle falls
- System can't prioritize both simultaneously

**Solution**:
- Install two FP2s if you need both capabilities
- One in wall_behavior mode (for daily tracking)
- One in ceiling_fall mode (for fall detection)
- This is recommended for high-risk elderly with both issues

### ❌ Mistake 3: Using Wall FP2 as Primary Fall Detection

**Problem**:
```
"I only have a wall-mounted FP2. Can it detect falls?"
```

**Why It's Unreliable**:
- Side/wall position has poor vertical fall detection
- Can't distinguish between falls and other rapid movements
- May miss falls at edge of field of view

**Solution**:
- Use wall FP2 as SECONDARY fall evidence
- Add wearable accelerometer or ceiling FP2 for PRIMARY fall detection
- Never rely on wall FP2 alone for fall alerts

### ❌ Mistake 4: Installing Ceiling FP2 and Ignoring Behavior

**Problem**:
```
"I installed ceiling FP2 for fall detection.
Now the system has no behavior data."
```

**Why This Happens**:
- Ceiling FP2 provides fall detection only
- No wall sensor to track daily patterns
- Behavior analysis is blind

**Solution**:
- Add wall-mounted FP2 or PIR for behavior tracking
- Ceiling FP2 and wall-mounted FP2 are COMPLEMENTARY

---

## Validation Checklist

When installing FP2 sensors, verify:

### Wall-Mounted FP2:
- [ ] Installed at wall, 1-1.5m height
- [ ] Pointing at main activity areas
- [ ] Receiving presence readings
- [ ] Zone/location data is accurate
- [ ] Transition detection works
- [ ] Activity level changes are detected
- [ ] NO fall-only capabilities being used for behavior

### Ceiling-Mounted FP2:
- [ ] Installed at ceiling, central location
- [ ] Covering room uniformly
- [ ] Fall patterns recognized
- [ ] Post-fall inactivity detected
- [ ] NO detailed zone tracking expected
- [ ] NO behavior chains being analyzed from this device

### Both Together (if applicable):
- [ ] Fall alerts use ceiling_fall FP2 as primary source
- [ ] Behavior analysis uses wall_behavior FP2 as primary source
- [ ] No capability mismatches in logs
- [ ] Confidence multipliers applied correctly
  - Wall FP2: 0.95
  - Ceiling FP2: 0.85

---

## For Integration Teams

When updating sensorFusion logic:

1. **Verify installation_mode** on all devices
2. **Check capability mismatch** - log warnings if devices report unreliable capabilities for their mode
3. **Separate behavior and fall logic** - don't mix detection paths
4. **Apply weights** - fall_detected from ceiling FP2 gets weight 0.8, from wall gets 0.3
5. **Test both scenarios**:
   - Ceiling FP2 present: Fall alerts work
   - Only wall FP2: Fall alerts use secondary evidence, less confident
   - Both present: Redundancy and higher confidence

---

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | April 2026 | Initial release: Clarify wall_behavior vs ceiling_fall roles |

---

## Questions?

**Q: Can I use wall FP2 as backup for fall detection?**  
A: Yes, as secondary evidence only. Weight its contribution at 0.3. Never rely on it as primary.

**Q: What if I only have budget for one FP2?**  
A: Choose wall_behavior. Daily behavior tracking is more critical than fall detection alone. Add a wearable accelerometer for fall backup.

**Q: Can ceiling FP2 detect zone changes?**  
A: Technically it can detect presence/absence, but not zone details. Use wall FP2 for zone tracking.

**Q: Does this mean ceiling FP2 is "bad"?**  
A: No! It's excellent for what it does (fall detection). Don't expect it to do something else equally well.

**Q: What if my room has both ceiling and wall FP2?**  
A: Perfect! Each provides what it's good at. Use both—behavior from wall, fall detection from ceiling.
