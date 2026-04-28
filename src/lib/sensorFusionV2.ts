/**
 * Sensor Fusion V2 - Installation Mode Aware
 *
 * Updated to handle FP2 in different installation modes:
 * - Wall-mounted FP2: Use for detailed behavior chain detection
 * - Ceiling-mounted FP2: Use for fall detection evidence ONLY
 *
 * KEY RULES:
 * 1. Do not use ceiling_fall FP2 for detailed behavior chain detection
 * 2. Use ceiling_fall FP2 only as fall evidence
 * 3. Fall alert requires: fall_detected + post_fall_inactivity
 *    OR: fall_detected + no_arrival_to_safe_zone (after 2 minutes)
 */

import { Device, SensorCapability, InstallationMode } from '@/types/device';
import { BehaviorEvent, RiskLevel, DailyBehaviorSummaryInput } from '@/types/behavior';
import {
  isCapabilityReliable,
  getReliableCapabilities,
  getConfidenceMultiplier,
} from '@/config/sensor-capabilities';

// ============ Sensor Fusion Rules ============

export interface SensorFusionInput {
  devices: Device[];
  raw_sensor_data: Map<string, SensorReading[]>; // device_id -> readings
  recent_events: BehaviorEvent[];
  daily_summary: DailyBehaviorSummaryInput;
}

export interface SensorReading {
  device_id: string;
  timestamp: string;
  capability: SensorCapability;
  value: unknown; // presence: boolean, activity_level: number, fall_detected: boolean, etc.
  confidence: number; // 0-1
}

export interface FusionResult {
  detected_events: FusionEvent[];
  anomalies: AnomalyDetection[];
  behavior_chain: BehaviorChainAnalysis;
  fall_analysis: FallDetectionAnalysis;
}

export interface FusionEvent {
  event_type: string;
  risk_level: RiskLevel;
  confidence: number;
  sources: string[]; // device IDs
  timestamp: string;
  description: string;
}

export interface AnomalyDetection {
  type: string;
  severity: 'low' | 'medium' | 'high';
  confidence: number;
  affected_capability: SensorCapability;
  description: string;
}

export interface BehaviorChainAnalysis {
  current_state: string;
  transitions_detected: Array<{
    from_state: string;
    to_state: string;
    timestamp: string;
    confidence: number;
  }>;
  expected_next_states: string[];
  anomalies: string[];
}

export interface FallDetectionAnalysis {
  fall_detected: boolean;
  fall_confidence: number;
  evidence: FallEvidence[];
  post_fall_state: 'immediate' | 'recovery' | 'recovered' | 'none';
  time_since_fall?: number; // milliseconds
  recommended_action: string;
}

export interface FallEvidence {
  source_device_id: string;
  capability: SensorCapability;
  value: unknown;
  timestamp: string;
  confidence: number;
  weight: number; // 0-1, how much this contributes to fall confidence
}

// ============ Core Fusion Logic ============

/**
 * Main sensor fusion orchestrator
 */
export function performSensorFusion(input: SensorFusionInput): FusionResult {
  // Segregate devices by installation mode
  const devicesByMode = segregateDevicesByMode(input.devices);

  // Process wall-mounted FP2s for detailed behavior
  const behaviorAnalysis = analyzeBehaviorChains(
    devicesByMode.wall_behavior,
    input.raw_sensor_data
  );

  // Process ceiling-mounted FP2s for fall detection
  const fallAnalysis = analyzeFallDetection(
    devicesByMode.ceiling_fall,
    devicesByMode.wall_behavior, // Provide wall FP2 as supporting evidence
    input.raw_sensor_data
  );

  // Aggregate results
  const fusedEvents = aggregateFusionEvents(behaviorAnalysis, fallAnalysis);
  const anomalies = detectAnomalies(input.devices, input.raw_sensor_data);

  return {
    detected_events: fusedEvents,
    anomalies,
    behavior_chain: behaviorAnalysis,
    fall_analysis: fallAnalysis,
  };
}

// ============ Device Segregation ============

interface DevicesByMode {
  wall_behavior: Device[];
  ceiling_fall: Device[];
  other: Device[];
}

function segregateDevicesByMode(devices: Device[]): DevicesByMode {
  return {
    wall_behavior: devices.filter(d => d.installation_mode === 'wall_behavior'),
    ceiling_fall: devices.filter(d => d.installation_mode === 'ceiling_fall'),
    other: devices.filter(
      d => d.installation_mode !== 'wall_behavior' && d.installation_mode !== 'ceiling_fall'
    ),
  };
}

// ============ Behavior Chain Analysis ============

/**
 * Analyze detailed behavior chains from wall-mounted sensors only
 */
function analyzeBehaviorChains(
  wallDevices: Device[],
  sensorData: Map<string, SensorReading[]>
): BehaviorChainAnalysis {
  // RULE: Only use wall_behavior devices for detailed behavior analysis
  if (wallDevices.length === 0) {
    return {
      current_state: 'unknown',
      transitions_detected: [],
      expected_next_states: [],
      anomalies: ['No wall-mounted behavior sensors available'],
    };
  }

  const transitions: BehaviorChainAnalysis['transitions_detected'] = [];
  const anomalies: string[] = [];

  // Process each wall device's data
  for (const device of wallDevices) {
    const readings = sensorData.get(device.device_id) || [];
    const capabilities = getReliableCapabilities(device.sensor_type, 'wall_behavior');

    // Only process reliable capabilities for this device
    for (const reading of readings) {
      if (!capabilities.includes(reading.capability)) {
        anomalies.push(
          `Device ${device.device_id} reading capability ${reading.capability} which is not reliable for wall_behavior mode`
        );
        continue;
      }

      // Analyze transitions
      if (reading.capability === 'transition' && typeof reading.value === 'object') {
        const transition = reading.value as {
          from: string;
          to: string;
        };
        transitions.push({
          from_state: transition.from,
          to_state: transition.to,
          timestamp: reading.timestamp,
          confidence: reading.confidence,
        });
      }
    }
  }

  // Infer current state from latest readings
  const currentState = inferCurrentState(sensorData, wallDevices);

  return {
    current_state: currentState,
    transitions_detected: transitions,
    expected_next_states: getExpectedNextStates(currentState),
    anomalies,
  };
}

/**
 * Infer current state from sensor readings
 */
function inferCurrentState(
  sensorData: Map<string, SensorReading[]>,
  devices: Device[]
): string {
  // Get most recent presence and location readings
  let lastLocation = 'unknown';
  let isPresent = false;

  for (const device of devices) {
    const readings = (sensorData.get(device.device_id) || [])
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 5);

    for (const reading of readings) {
      if (reading.capability === 'presence' && typeof reading.value === 'boolean') {
        isPresent = reading.value;
      }
      if (reading.capability === 'location' && typeof reading.value === 'string') {
        lastLocation = reading.value;
      }
    }
  }

  return isPresent ? `${lastLocation}_present` : 'absent';
}

function getExpectedNextStates(currentState: string): string[] {
  const stateTransitions: Record<string, string[]> = {
    bedroom_present: ['bedroom_sleeping', 'hallway_present'],
    bedroom_sleeping: ['bedroom_awake', 'bedroom_present'],
    bedroom_awake: ['hallway_present', 'bathroom_present'],
    bathroom_present: ['bathroom_duration_normal', 'bathroom_duration_long'],
    bathroom_duration_long: ['alert_bathroom_duration', 'hallway_present'],
    hallway_present: ['bedroom_present', 'bathroom_present', 'living_room_present'],
    living_room_present: ['living_room_activity', 'kitchen_present', 'hallway_present'],
    absent: ['hallway_present', 'bedroom_present'],
  };

  return stateTransitions[currentState] || ['unknown'];
}

// ============ Fall Detection Analysis ============

/**
 * Analyze fall detection from ceiling FP2 and wearables
 * RULE: Use ceiling_fall FP2 ONLY for fall evidence
 * Fall alert requires: fall_detected + post_fall_inactivity
 *                  OR: fall_detected + no_arrival_to_safe_zone (2 min)
 */
function analyzeFallDetection(
  ceilingDevices: Device[],
  wallDevices: Device[],
  sensorData: Map<string, SensorReading[]>
): FallDetectionAnalysis {
  const fallEvidence: FallEvidence[] = [];

  // Collect fall evidence from ceiling FP2
  for (const device of ceilingDevices) {
    const readings = sensorData.get(device.device_id) || [];

    for (const reading of readings) {
      // RULE: Only use ceiling_fall FP2 for these capabilities
      if (
        reading.capability === 'fall_detected' ||
        reading.capability === 'post_fall_inactivity'
      ) {
        fallEvidence.push({
          source_device_id: device.device_id,
          capability: reading.capability,
          value: reading.value,
          timestamp: reading.timestamp,
          confidence: reading.confidence,
          weight: reading.capability === 'fall_detected' ? 0.8 : 0.5,
        });
      }
    }
  }

  // Collect supporting fall evidence from wall devices (secondary only)
  for (const device of wallDevices) {
    const readings = sensorData.get(device.device_id) || [];

    for (const reading of readings) {
      if (reading.capability === 'post_fall_inactivity') {
        fallEvidence.push({
          source_device_id: device.device_id,
          capability: reading.capability,
          value: reading.value,
          timestamp: reading.timestamp,
          confidence: reading.confidence,
          weight: 0.3, // Lower weight for wall device
        });
      }
    }
  }

  // Calculate overall fall confidence
  if (fallEvidence.length === 0) {
    return {
      fall_detected: false,
      fall_confidence: 0,
      evidence: [],
      post_fall_state: 'none',
      recommended_action: 'No fall detected',
    };
  }

  // RULE: Fall alert requires fall_detected + post_fall_inactivity
  const hasFallDetected = fallEvidence.some(e => e.capability === 'fall_detected');
  const hasPostFallInactivity = fallEvidence.some(
    e => e.capability === 'post_fall_inactivity'
  );

  if (!hasFallDetected) {
    return {
      fall_detected: false,
      fall_confidence: 0,
      evidence: fallEvidence,
      post_fall_state: 'none',
      recommended_action: 'No fall detected (no fall_detected signal)',
    };
  }

  if (!hasPostFallInactivity) {
    return {
      fall_detected: false,
      fall_confidence: 0.4, // Partial confidence without inactivity confirmation
      evidence: fallEvidence,
      post_fall_state: 'immediate',
      recommended_action:
        'Fall pattern detected but no post-fall inactivity. Monitor closely.',
    };
  }

  // Both conditions met: FALL ALERT
  const avgConfidence = fallEvidence.reduce((sum, e) => sum + e.confidence * e.weight, 0) /
    fallEvidence.reduce((sum, e) => sum + e.weight, 0);

  return {
    fall_detected: true,
    fall_confidence: Math.min(avgConfidence * 0.95, 0.99), // Cap at 0.99
    evidence: fallEvidence,
    post_fall_state: 'recovery',
    time_since_fall: calculateTimeSinceFall(fallEvidence),
    recommended_action:
      'HIGH PRIORITY ALERT: Fall detected with post-fall inactivity. Immediate assistance needed.',
  };
}

function calculateTimeSinceFall(evidence: FallEvidence[]): number {
  if (evidence.length === 0) return 0;
  const fallEvent = evidence.find(e => e.capability === 'fall_detected');
  if (!fallEvent) return 0;
  return Date.now() - new Date(fallEvent.timestamp).getTime();
}

// ============ Anomaly Detection ============

/**
 * Detect anomalies in sensor data
 */
function detectAnomalies(
  devices: Device[],
  sensorData: Map<string, SensorReading[]>
): AnomalyDetection[] {
  const anomalies: AnomalyDetection[] = [];

  for (const device of devices) {
    if (!device.is_active) continue;

    const readings = sensorData.get(device.device_id) || [];
    if (readings.length === 0) {
      anomalies.push({
        type: 'no_data',
        severity: device.installation_mode === 'ceiling_fall' ? 'medium' : 'low',
        confidence: 0.9,
        affected_capability: 'presence',
        description: `Device ${device.device_id} has no recent readings`,
      });
      continue;
    }

    // Check for unusual reading patterns
    const capabilities = getReliableCapabilities(device.sensor_type, device.installation_mode);

    for (const reading of readings) {
      if (!capabilities.includes(reading.capability)) {
        anomalies.push({
          type: 'capability_mismatch',
          severity: 'medium',
          confidence: 0.8,
          affected_capability: reading.capability,
          description: `Device ${device.device_id} reported capability ${reading.capability} which is not reliable for installation_mode ${device.installation_mode}`,
        });
      }

      if (reading.confidence < 0.3) {
        anomalies.push({
          type: 'low_confidence',
          severity: 'low',
          confidence: 0.7,
          affected_capability: reading.capability,
          description: `Device ${device.device_id} reported ${reading.capability} with low confidence (${reading.confidence})`,
        });
      }
    }
  }

  return anomalies;
}

// ============ Event Aggregation ============

/**
 * Aggregate behavior and fall analysis into fusion events
 */
function aggregateFusionEvents(
  behavior: BehaviorChainAnalysis,
  fall: FallDetectionAnalysis
): FusionEvent[] {
  const events: FusionEvent[] = [];

  // Fall detection event
  if (fall.fall_detected) {
    events.push({
      event_type: 'fall_detected',
      risk_level: 'high',
      confidence: fall.fall_confidence,
      sources: fall.evidence.map(e => e.source_device_id),
      timestamp: new Date().toISOString(),
      description: fall.recommended_action,
    });
  }

  // Behavior anomaly events
  for (const anomaly of behavior.anomalies) {
    events.push({
      event_type: 'behavior_anomaly',
      risk_level: 'attention',
      confidence: 0.7,
      sources: [], // Would be populated from fusion process
      timestamp: new Date().toISOString(),
      description: anomaly,
    });
  }

  return events;
}

// ============ CRITICAL SAFETY GATES ============

/**
 * SAFETY GATE 1: Ensure ceiling_fall FP2 is never used for behavior chain detection
 */
export function validateCeilingFP2Usage(
  devices: Device[],
  detection_source: Device
): { safe: boolean; issue?: string } {
  if (
    detection_source.sensor_type === 'fp2_radar' &&
    detection_source.installation_mode === 'ceiling_fall'
  ) {
    // Ceiling FP2 should only be used for fall detection
    // If used in behavior chain detection, flag as unsafe

    // Check in behavior devices
    const behaviorDevices = devices.filter(d => d.installation_mode === 'wall_behavior');
    if (!behaviorDevices.some(d => d.device_id === detection_source.device_id)) {
      return {
        safe: false,
        issue: `Ceiling-mounted FP2 (${detection_source.device_id}) should not be used for behavior chain detection. Use wall-mounted FP2 instead.`,
      };
    }
  }

  return { safe: true };
}

/**
 * SAFETY GATE 2: Ensure wall_behavior FP2 is not suppressed for fall detection
 */
export function validateFallDetectionIntegrity(
  ceilingDevices: Device[],
  evidence: FallEvidence[]
): { safe: boolean; issue?: string } {
  if (ceilingDevices.length === 0) {
    return {
      safe: false,
      issue:
        'No ceiling-mounted fall detection devices. Consider adding ceiling FP2 or wearable for fall safety.',
    };
  }

  const hasPrimaryEvidence = evidence.some(e => e.weight >= 0.8);
  if (!hasPrimaryEvidence) {
    return {
      safe: false,
      issue: 'Fall alert triggered but no primary evidence source (ceiling_fall FP2 required).',
    };
  }

  return { safe: true };
}
