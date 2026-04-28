# Sensor System: Developer Quick Reference

**Quick lookups for implementing the new installation mode system**

---

## TL;DR

FP2 now has two modes:
- **wall_behavior** (1-1.5m height, wall mounted): Tracks zones, duration, transitions, activity
- **ceiling_fall** (ceiling mounted, down-facing): Detects falls and post-fall inactivity

Don't mix them. Use sensor fusion V2.

---

## Device Configuration Template

```typescript
// Wall-mounted FP2 for behavior
const wallFP2: Device = {
  device_id: 'fp2_living_room_001',
  sensor_type: 'fp2_radar',
  installation_mode: 'wall_behavior',
  room: 'living_room',
  mounting_height: 'wall',
  is_active: true,
  is_primary_for_room: true,
  reliable_capabilities: [
    'presence', 'location', 'duration', 'transition', 'activity_level'
  ]
};

// Ceiling-mounted FP2 for fall
const ceilingFP2: Device = {
  device_id: 'fp2_bedroom_ceiling_001',
  sensor_type: 'fp2_radar',
  installation_mode: 'ceiling_fall',
  room: 'bedroom',
  mounting_height: 'ceiling',
  is_active: true,
  is_primary_for_room: false,
  reliable_capabilities: [
    'fall_detected', 'presence', 'post_fall_inactivity'
  ]
};
```

---

## Capability Lookup

```typescript
import { getReliableCapabilities, isCapabilityReliable } from '@/config/sensor-capabilities';

// Get all reliable capabilities for a device
const wallCapabilities = getReliableCapabilities('fp2_radar', 'wall_behavior');
// Returns: ['presence', 'location', 'duration', 'transition', 'activity_level']

const ceilingCapabilities = getReliableCapabilities('fp2_radar', 'ceiling_fall');
// Returns: ['fall_detected', 'presence', 'post_fall_inactivity']

// Check if specific capability is reliable
const isPresenceReliable = isCapabilityReliable('fp2_radar', 'wall_behavior', 'presence');
// Returns: true

const isLocationReliable = isCapabilityReliable('fp2_radar', 'ceiling_fall', 'location');
// Returns: false (don't use ceiling FP2 for zone tracking!)
```

---

## Sensor Fusion Usage

```typescript
import { performSensorFusion } from '@/lib/sensorFusionV2';

const fusionResult = performSensorFusion({
  devices: elderDevices,
  raw_sensor_data: sensorReadings,
  recent_events: behaviorEvents,
  daily_summary: dailySummary
});

// Access results
const fallDetected = fusionResult.fall_analysis.fall_detected;
const behaviorAnomalies = fusionResult.behavior_chain.anomalies;
const detectedEvents = fusionResult.detected_events;
```

---

## Validation Pattern

```typescript
// Check for capability mismatch
for (const reading of sensorData) {
  const device = devices.find(d => d.device_id === reading.device_id);
  const reliable = getReliableCapabilities(
    device.sensor_type,
    device.installation_mode
  );
  
  if (!reliable.includes(reading.capability)) {
    logger.warn(
      `Capability mismatch: Device ${device.device_id} ` +
      `reported ${reading.capability} in ${device.installation_mode} mode`
    );
    // Flag this as anomaly
  }
}
```

---

## Fall Alert Logic

```typescript
// Fall alert requires: fall_detected + post_fall_inactivity
function shouldAlertFall(fallAnalysis: FallDetectionAnalysis): boolean {
  return (
    fallAnalysis.fall_detected &&
    fallAnalysis.fall_confidence >= 0.7 && // Adjust threshold as needed
    fallAnalysis.post_fall_state === 'recovery' // Inactivity confirmed
  );
}

// Never suppress high-risk events
function getAlertSuppression(
  condition: TemporaryCondition,
  event_risk_level: string
): number {
  // CRITICAL: High-risk events NEVER suppressed
  if (event_risk_level === 'high') {
    return 1.0; // 100% alert through
  }
  
  // Routine events can be suppressed during temp condition
  if (condition.status === 'active') {
    return 0.7; // 70% alert through (30% suppression)
  }
  
  return 1.0;
}
```

---

## Room Setup Patterns

### Bedroom (Sleep + Safety)
```typescript
{
  room_id: 'bedroom_001',
  primary_sensor: bed_pressure_sensor,    // Sleep tracking
  secondary_sensors: [
    wall_fp2_for_behavior,                // Out-of-bed detection
    ceiling_fp2_for_fall  // Optional      // Fall safety
  ]
}
```

### Living Room (Activity Tracking)
```typescript
{
  room_id: 'living_room_001',
  primary_sensor: wall_fp2_behavior,      // Zone tracking, activity
  secondary_sensors: [
    door_sensor_entry_exit               // Home/away context
  ]
}
```

### Bathroom (Duration Monitoring)
```typescript
{
  room_id: 'bathroom_001',
  primary_sensor: wall_fp2_high_mounted,  // Privacy-aware positioning
  secondary_sensors: []
}
```

### Hallway (Movement Detection)
```typescript
{
  room_id: 'hallway_001',
  primary_sensor: pir_motion,             // Movement between rooms
  secondary_sensors: [
    ceiling_fp2_fall_optional             // Optional if fall risk
  ]
}
```

---

## Common Pitfalls

### ❌ Using ceiling FP2 for zones
```typescript
// WRONG
const zones = ceiling_fp2.readCapability('location');
// Ceiling view has poor zone precision
```

### ✅ Using wall FP2 for zones
```typescript
// CORRECT
const zones = wall_fp2.readCapability('location');
// Wall view has good zone precision
```

---

### ❌ Missing post_fall_inactivity
```typescript
// WRONG
if (fallDetected) {
  alert('Fall!');
}
// Too many false positives
```

### ✅ Requiring both fall signals
```typescript
// CORRECT
if (fallDetected && postFallInactivity) {
  alert('Fall with inactivity - immediate assist needed');
}
// Much more reliable
```

---

### ❌ Treating all FP2s the same
```typescript
// WRONG
for (const fp2 of allFP2s) {
  analyzeDetailedBehavior(fp2);  // Fails for ceiling FP2
}
```

### ✅ Segregate by mode
```typescript
// CORRECT
const wallFP2s = devices.filter(d => d.installation_mode === 'wall_behavior');
const ceilingFP2s = devices.filter(d => d.installation_mode === 'ceiling_fall');

analyzeDetailedBehavior(wallFP2s);
analyzeFalls(ceilingFP2s);
```

---

## Confidence Multipliers

```typescript
const CONFIDENCE_MULTIPLIERS = {
  'wall_behavior': 0.95,      // Very reliable for what it does
  'ceiling_fall': 0.85,       // Good for fall detection
  'standalone': 0.75,         // Generic mode, moderate reliability
  'hidden': 0.65              // Limited visibility
};

// Apply multiplier to detection confidence
const adjusted_confidence = raw_confidence * CONFIDENCE_MULTIPLIERS[mode];
```

---

## Types Import

```typescript
// Device types
import {
  Device,
  InstallationMode,
  SensorType,
  SensorCapability,
  RoomSensorSetup
} from '@/types/device';

// Capability functions
import {
  getDeviceCapabilities,
  isCapabilityReliable,
  getReliableCapabilities,
  getConfidenceMultiplier
} from '@/config/sensor-capabilities';

// Sensor fusion
import {
  performSensorFusion,
  segregateDevicesByMode,
  validateCeilingFP2Usage,
  validateFallDetectionIntegrity
} from '@/lib/sensorFusionV2';
```

---

## Test Scenarios

### Scenario 1: Validate Installation
```typescript
function validateRoomInstallation(room: RoomSensorSetup): ValidationResult {
  const results = {
    errors: [],
    warnings: [],
    passed: []
  };
  
  // Check primary sensor
  if (room.primary_sensor.installation_mode === 'ceiling_fall') {
    results.errors.push('Primary sensor should not be ceiling_fall mode');
  }
  
  // Check secondary sensors
  for (const sensor of room.secondary_sensors || []) {
    if (sensor.installation_mode === 'ceiling_fall' && 
        !isFallRiskRoom(room.room_name)) {
      results.warnings.push(
        `Ceiling FP2 in ${room.room_name} - only needed for fall risk`
      );
    }
  }
  
  results.passed.push(`Room ${room.room_name} configuration valid`);
  return results;
}
```

### Scenario 2: Test Behavior Detection
```typescript
function testBehaviorDetection(devices: Device[], readings: SensorReading[]) {
  const wallFP2s = devices.filter(d => d.installation_mode === 'wall_behavior');
  
  if (wallFP2s.length === 0) {
    throw new Error('No wall_behavior FP2 for behavior detection');
  }
  
  // Verify readings include behavior capabilities
  const capabilities = new Set<SensorCapability>();
  for (const reading of readings) {
    if (wallFP2s.some(d => d.device_id === reading.device_id)) {
      capabilities.add(reading.capability);
    }
  }
  
  const required = ['presence', 'location', 'duration'];
  for (const req of required) {
    if (!capabilities.has(req as SensorCapability)) {
      throw new Error(`Missing required capability: ${req}`);
    }
  }
}
```

### Scenario 3: Test Fall Detection
```typescript
function testFallDetection(devices: Device[], readings: SensorReading[]) {
  const ceilingFP2s = devices.filter(d => d.installation_mode === 'ceiling_fall');
  
  if (ceilingFP2s.length === 0) {
    console.warn('No ceiling_fall FP2 - fall detection degraded');
    return;
  }
  
  // Verify fall readings come from ceiling FP2
  const fallReadings = readings.filter(r => r.capability === 'fall_detected');
  
  for (const reading of fallReadings) {
    if (!ceilingFP2s.some(d => d.device_id === reading.device_id)) {
      console.warn(
        `Fall reading from non-ceiling-FP2: ${reading.device_id}`
      );
    }
  }
}
```

---

## Files Reference

| File | Purpose | Key Export |
|---|---|---|
| src/types/device.ts | Device & installation mode definitions | Device, InstallationMode |
| src/config/sensor-capabilities.ts | Capability matrix by mode | getReliableCapabilities() |
| src/lib/sensorFusionV2.ts | Mode-aware sensor fusion | performSensorFusion() |
| docs/INSTALLATION_SOP.md | Room-by-room installation guide | Room configurations |
| docs/FP2_ROLE_CLARIFICATION.md | Why wall vs ceiling FP2 differ | Use case comparison |

---

## Key Numbers

- Wall FP2 confidence multiplier: **0.95**
- Ceiling FP2 confidence multiplier: **0.85**
- Fall detection weight (from ceiling FP2): **0.8**
- Fall detection weight (from wall FP2): **0.3**
- Wall FP2 optimal height: **1-1.5 meters**
- Ceiling FP2 coverage: **Full room**
- Fall alert requires confidence: **≥0.7**
- Normal bathroom visit: **3-10 minutes**
- Long bathroom visit: **15+ minutes**

---

## Still Confused?

1. Read: docs/FP2_ROLE_CLARIFICATION.md (explains the why)
2. Reference: docs/INSTALLATION_SOP.md (shows where to install)
3. Code: src/config/sensor-capabilities.ts (see capability matrix)
4. Integrate: src/lib/sensorFusionV2.ts (use this in your code)

---

**Version**: 1.0 | **Date**: April 2026 | **Status**: Ready
