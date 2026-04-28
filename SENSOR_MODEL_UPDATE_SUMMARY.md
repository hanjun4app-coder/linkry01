# Sensor Capability Model Update: Summary

**Date**: April 2026  
**Status**: ✅ Complete  
**Scope**: Device configuration, capability model, sensor fusion logic, installation SOP

---

## What Changed

The sensor system now recognizes that sensors have **different roles based on installation mode**. One FP2 should not be expected to do both behavior understanding and fall detection perfectly.

### Before This Update

- All sensors were treated as general-purpose devices
- No distinction between wall-mounted and ceiling-mounted FP2
- Sensor fusion expected all capabilities from all devices
- Installation guidance was minimal

### After This Update

- Sensors have explicit `installation_mode` (wall_behavior, ceiling_fall, etc.)
- FP2 in wall_behavior mode is optimized for detailed behavior tracking
- FP2 in ceiling_fall mode is optimized for fall detection
- Sensor fusion validates that devices only use reliable capabilities for their mode
- Installation SOP provides room-specific, mode-aware guidance

---

## Files Created/Updated

### 1. **src/types/device.ts** - Device Configuration Types
Defines:
- `InstallationMode`: "wall_behavior" | "ceiling_fall" | "standalone" | "hidden"
- `Device` interface with installation_mode field
- `SensorCapability` types
- Device thresholds and calibration
- RoomSensorSetup for organizing devices by room

**Key Addition**:
```typescript
interface Device {
  installation_mode: InstallationMode;  // NEW
  reliable_capabilities: SensorCapability[];
  optional_capabilities?: SensorCapability[];
}
```

### 2. **src/config/sensor-capabilities.ts** - Capability Model
Defines what capabilities are reliable for each sensor + mode combination.

**Key Matrices**:
- `FP2_CAPABILITIES` - Defines wall_behavior vs ceiling_fall capabilities
- `BED_SENSOR_CAPABILITIES` - Sleep tracking (mode-independent)
- `PIR_CAPABILITIES` - Motion detection (mode-dependent)
- `SENSOR_CAPABILITY_REGISTRY` - Central lookup for all sensors

**Wall FP2 (wall_behavior)**:
- Reliable: presence, location, duration, transition, activity_level
- Optional: post_fall_inactivity
- Confidence: 0.95

**Ceiling FP2 (ceiling_fall)**:
- Reliable: fall_detected, presence, post_fall_inactivity
- Optional: none
- Confidence: 0.85

### 3. **src/lib/sensorFusionV2.ts** - Updated Sensor Fusion Logic
Implements mode-aware sensor fusion with safety gates.

**Key Functions**:
- `performSensorFusion()` - Main orchestrator
- `segregateDevicesByMode()` - Separate devices by installation mode
- `analyzeBehaviorChains()` - Use ONLY wall_behavior devices
- `analyzeFallDetection()` - Use ceiling_fall devices as primary evidence
- `validateCeilingFP2Usage()` - Safety gate: prevent ceiling FP2 from behavior detection
- `validateFallDetectionIntegrity()` - Safety gate: ensure fall detection uses proper devices

**Critical Rules**:
1. Do NOT use ceiling_fall FP2 for behavior chain detection
2. Use ceiling_fall FP2 ONLY as fall evidence
3. Fall alert requires: fall_detected + post_fall_inactivity

### 4. **docs/INSTALLATION_SOP.md** - Installation Standard Operating Procedure
Room-by-room installation guide with mode-specific placement.

**Rooms Covered**:
- **Bedroom**: Sleep tracker + wall FP2 (behavior) + ceiling FP2 optional (fall)
- **Living Room**: Wall FP2 (behavior) + door sensor (context)
- **Bathroom**: Wall FP2 high-mounted (behavior, privacy-first) or radar
- **Hallway**: PIR (movement) or ceiling FP2 if fall risk high
- **Entrance**: Door sensor (home/away context)
- **Medication Cabinet**: Door sensor (adherence tracking)

**Example Configuration**:
```json
{
  "device_id": "fp2_living_room_001",
  "sensor_type": "fp2_radar",
  "installation_mode": "wall_behavior",
  "reliable_capabilities": [
    "presence", "location", "duration", "transition", "activity_level"
  ],
  "mounting_height": "wall"
}
```

### 5. **docs/FP2_ROLE_CLARIFICATION.md** - FP2 Role Documentation
Explains why wall and ceiling FP2 have different roles.

**Key Points**:
- Wall FP2 excels at behavior understanding (zones, transitions, duration)
- Ceiling FP2 excels at fall detection (overhead view, rapid descent patterns)
- One FP2 cannot do both perfectly
- Common mistakes and solutions
- Validation checklist for installation

---

## Integration Steps

### Step 1: Update Device Configuration
Add `installation_mode` to all existing devices in database:

```typescript
// Before
{
  device_id: "fp2_living_room_001",
  sensor_type: "fp2_radar",
  room: "living_room",
  mounting_height: "wall"
}

// After
{
  device_id: "fp2_living_room_001",
  sensor_type: "fp2_radar",
  installation_mode: "wall_behavior",  // NEW
  room: "living_room",
  mounting_height: "wall",
  reliable_capabilities: [
    "presence", "location", "duration", "transition", "activity_level"
  ]
}
```

### Step 2: Update Sensor Fusion
Replace old sensorFusion logic with sensorFusionV2:

```typescript
// Import new utilities
import { segregateDevicesByMode } from '@/lib/sensorFusionV2';
import { getReliableCapabilities } from '@/config/sensor-capabilities';

// Use mode-aware fusion
const result = performSensorFusion({
  devices: allDevices,
  raw_sensor_data: sensorReadings,
  recent_events: behaviorEvents,
  daily_summary: dailyData
});
```

### Step 3: Add Validation
Implement capability validation:

```typescript
// Check that devices only report reliable capabilities for their mode
for (const reading of sensorData) {
  const device = devices.find(d => d.device_id === reading.device_id);
  const reliable = getReliableCapabilities(
    device.sensor_type,
    device.installation_mode
  );
  
  if (!reliable.includes(reading.capability)) {
    logger.warn(
      `Device ${device.device_id} reported unreliable capability ` +
      `${reading.capability} for mode ${device.installation_mode}`
    );
  }
}
```

### Step 4: Update Installation Documentation
Use INSTALLATION_SOP.md and FP2_ROLE_CLARIFICATION.md for:
- Training team on new modes
- Guiding device placement
- Validating installed systems

### Step 5: Test Each Room Configuration

**Test Behavior Tracking** (wall_behavior FP2):
```
Install: Wall FP2 at 1-1.5m height, facing activity area
Test:
  ✅ Presence detection working
  ✅ Zone/location accuracy
  ✅ Duration tracking
  ✅ Transition detection
  ❌ Fall detection signals (should not appear)
```

**Test Fall Detection** (ceiling_fall FP2):
```
Install: Ceiling FP2 at center, downward angle
Test:
  ✅ Fall pattern recognition
  ✅ Post-fall inactivity detection
  ❌ Zone details (overhead view won't work)
  ❌ Activity level classification
```

---

## Configuration Best Practices

### 1. Always Assign Explicit Mode
```typescript
// ✅ Good
const device = {
  installation_mode: "wall_behavior",
  reliable_capabilities: [...]
};

// ❌ Bad
const device = {
  // installation_mode not set, defaults to 'standalone'
  // Capabilities unclear
};
```

### 2. Room-Based Organization
```typescript
// ✅ Good
const bedroom = {
  room_id: "bedroom_001",
  room_name: "Master Bedroom",
  primary_sensor: bed_sensor,  // Sleep tracking
  secondary_sensors: [
    { device_id: "fp2_wall", mode: "wall_behavior" },
    { device_id: "fp2_ceiling", mode: "ceiling_fall" }  // Optional
  ]
};

// ❌ Bad
const devices = [
  { device_id: "fp2_wall", ... },
  { device_id: "fp2_ceiling", ... }
  // No room organization, modes unclear
];
```

### 3. Use Helper Functions
```typescript
// ✅ Good
const capabilities = getReliableCapabilities(
  'fp2_radar',
  'wall_behavior'
);

const isReliable = isCapabilityReliable(
  'fp2_radar',
  'ceiling_fall',
  'location'  // Returns false - not reliable
);

// ❌ Bad
if (device.name.includes("ceiling")) {
  // Unreliable text-based logic
}
```

---

## Safety Gates

The system includes 2 critical safety gates in sensorFusionV2:

### Safety Gate 1: Prevent Ceiling FP2 from Behavior Detection
```typescript
function validateCeilingFP2Usage(devices, detection_source) {
  if (
    detection_source.sensor_type === 'fp2_radar' &&
    detection_source.installation_mode === 'ceiling_fall'
  ) {
    return {
      safe: false,
      issue: 'Ceiling FP2 should not be used for behavior chain detection'
    };
  }
  return { safe: true };
}
```

### Safety Gate 2: Ensure Fall Detection Integrity
```typescript
function validateFallDetectionIntegrity(ceilingDevices, evidence) {
  if (ceilingDevices.length === 0) {
    return {
      safe: false,
      issue: 'No ceiling-mounted devices for fall detection'
    };
  }
  
  const hasPrimaryEvidence = evidence.some(e => e.weight >= 0.8);
  if (!hasPrimaryEvidence) {
    return {
      safe: false,
      issue: 'Fall alert triggered but no primary evidence'
    };
  }
  
  return { safe: true };
}
```

---

## Migration Checklist

- [ ] Create new device type definitions (src/types/device.ts)
- [ ] Create sensor capability model (src/config/sensor-capabilities.ts)
- [ ] Implement sensorFusionV2 logic
- [ ] Update device database schema with installation_mode
- [ ] Migrate existing devices to new model
  - [ ] Identify wall-mounted FP2s → assign "wall_behavior"
  - [ ] Identify ceiling-mounted FP2s → assign "ceiling_fall"
  - [ ] Verify other devices (PIR, door sensors, bed sensors)
- [ ] Add validation logic for capability mismatches
- [ ] Implement logging for anomalies (wrong capability from wrong mode)
- [ ] Train team on FP2_ROLE_CLARIFICATION.md
- [ ] Review INSTALLATION_SOP.md with installers
- [ ] Test 2-3 rooms end-to-end
  - [ ] Behavior tracking works correctly
  - [ ] Fall detection works correctly
  - [ ] No false positives from mode mismatches
- [ ] Document any custom configurations
- [ ] Deploy to production

---

## Backward Compatibility

The new system is backward compatible:

- Devices without explicit `installation_mode` default to "standalone"
- Default mode uses balanced capabilities (presence + activity_level)
- Existing API/UI unchanged - this is internal capability model only
- No breaking changes to behavior event types

However, **new installations should always specify installation_mode**.

---

## Monitoring & Validation

### Daily Monitoring
- Check for capability mismatch warnings in logs
- Verify fall detection uses primary evidence (ceiling_fall FP2)
- Confirm behavior analysis uses wall_behavior devices

### Weekly Validation
- Test each room's primary sensor
- Verify readings match expected capabilities for mode
- Check confidence scores are reasonable

### Monthly Review
- Review anomaly logs for pattern
- Validate room configurations match SOP
- Update documentation if changes made

---

## Expected Outcomes

After implementing this update:

✅ **Behavior Tracking**:
- More accurate zone and transition detection (wall FP2 purpose-built)
- Better activity pattern analysis
- Fewer false behavioral anomalies

✅ **Fall Detection**:
- Higher confidence in fall alerts (dedicated ceiling sensors)
- Fewer false positives (secondary evidence properly weighted)
- Clear requirements (fall_detected + post_fall_inactivity)

✅ **System Clarity**:
- Clear understanding of what each FP2 should do
- Predictable behavior when configured correctly
- Better troubleshooting when something doesn't work

---

## Support

**For Installation Questions**: Reference docs/INSTALLATION_SOP.md

**For FP2 Role Questions**: Reference docs/FP2_ROLE_CLARIFICATION.md

**For Integration Questions**: Reference src/lib/sensorFusionV2.ts and src/config/sensor-capabilities.ts

**For Configuration Issues**: Check device installation_mode and reliable_capabilities match actual usage

---

## Sign-Off

✅ **Sensor Capability Model Updated**: Installation mode aware  
✅ **Sensor Fusion Logic Updated**: Validates mode-capability pairs  
✅ **Installation SOP Created**: Room-specific guidance  
✅ **Documentation Complete**: FP2 roles clearly defined  
✅ **No API/UI Changes**: Backward compatible internal update  

**Status**: Ready for implementation
