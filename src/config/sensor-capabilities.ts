/**
 * Sensor Capability Model
 *
 * Defines what capabilities are reliable for each sensor type + installation mode combination.
 *
 * KEY PRINCIPLE:
 * One FP2 should not be expected to do both behavior understanding and fall detection perfectly.
 * Wall-mounted FP2 = behavior understanding (presence, zones, duration, transitions, activity)
 * Ceiling-mounted FP2 = fall detection assistance (fall_detected, post_fall_inactivity)
 */

import { SensorType, SensorCapability, InstallationMode } from '@/types/device';

// ============ Capability Definitions ============

type CapabilitySet = {
  reliable: SensorCapability[];      // What this device is good at
  optional?: SensorCapability[];     // Secondary capabilities
  confidence_multiplier: number;     // 0-1, overall reliability for detection
  description: string;
};

type CapabilityMatrix = Record<InstallationMode, CapabilitySet>;

// ============ FP2 Radar (Aqara FP2) ============

export const FP2_CAPABILITIES: CapabilityMatrix = {
  wall_behavior: {
    reliable: [
      'presence',           // Is someone in the room?
      'location',           // Which zone/area of room?
      'duration',           // How long in that location?
      'transition',         // Moving between zones?
      'activity_level',     // High/medium/low activity intensity?
    ],
    optional: [
      'post_fall_inactivity', // Can detect prolonged inactivity (secondary)
    ],
    confidence_multiplier: 0.95,
    description: 'Wall/side-mounted FP2 optimized for behavior understanding. Provides reliable presence, zone tracking, duration analysis, and activity detection.',
  },

  ceiling_fall: {
    reliable: [
      'fall_detected',      // Radar detects sudden fall pattern
      'presence',           // Is someone in the room?
      'post_fall_inactivity', // Inactivity after fall event
    ],
    optional: [],
    confidence_multiplier: 0.85,
    description: 'Ceiling-mounted FP2 optimized for fall detection. Do NOT use for detailed zone behavior tracking. Provides fall events and presence only.',
  },

  standalone: {
    reliable: [
      'presence',
      'activity_level',
    ],
    optional: [
      'location',
      'duration',
      'transition',
    ],
    confidence_multiplier: 0.75,
    description: 'Generic FP2 configuration. Mode not explicitly set. Backward compatibility mode.',
  },

  hidden: {
    reliable: [
      'presence',
      'activity_level',
    ],
    optional: [],
    confidence_multiplier: 0.65,
    description: 'Hidden/embedded FP2 with reduced reliability. Limited visibility of activity patterns.',
  },
};

// ============ Bed Sensor ============

export const BED_SENSOR_CAPABILITIES: CapabilityMatrix = {
  wall_behavior: {
    reliable: ['bed_occupancy', 'sleep_state'],
    optional: [],
    confidence_multiplier: 0.98,
    description: 'Bed pressure sensor for sleep tracking.',
  },
  ceiling_fall: {
    reliable: ['bed_occupancy', 'sleep_state'],
    optional: [],
    confidence_multiplier: 0.98,
    description: 'Bed pressure sensor for sleep tracking.',
  },
  standalone: {
    reliable: ['bed_occupancy', 'sleep_state'],
    optional: [],
    confidence_multiplier: 0.98,
    description: 'Bed pressure sensor for sleep tracking.',
  },
  hidden: {
    reliable: ['bed_occupancy', 'sleep_state'],
    optional: [],
    confidence_multiplier: 0.98,
    description: 'Bed pressure sensor for sleep tracking.',
  },
};

// ============ PIR Motion Sensor ============

export const PIR_CAPABILITIES: CapabilityMatrix = {
  wall_behavior: {
    reliable: ['presence', 'room_entry_exit'],
    optional: ['activity_level'],
    confidence_multiplier: 0.85,
    description: 'Wall-mounted PIR for presence and entry/exit detection.',
  },
  ceiling_fall: {
    reliable: ['presence'],
    optional: [],
    confidence_multiplier: 0.80,
    description: 'Ceiling PIR for presence detection only.',
  },
  standalone: {
    reliable: ['presence', 'room_entry_exit'],
    optional: ['activity_level'],
    confidence_multiplier: 0.85,
    description: 'Standard PIR motion detection.',
  },
  hidden: {
    reliable: ['presence'],
    optional: [],
    confidence_multiplier: 0.70,
    description: 'Hidden PIR with reduced visibility.',
  },
};

// ============ Door Sensor ============

export const DOOR_SENSOR_CAPABILITIES: CapabilityMatrix = {
  wall_behavior: {
    reliable: ['door_open_close', 'room_entry_exit'],
    optional: [],
    confidence_multiplier: 0.99,
    description: 'Door contact sensor for entry/exit and room context.',
  },
  ceiling_fall: {
    reliable: ['door_open_close', 'room_entry_exit'],
    optional: [],
    confidence_multiplier: 0.99,
    description: 'Door contact sensor for entry/exit detection.',
  },
  standalone: {
    reliable: ['door_open_close', 'room_entry_exit'],
    optional: [],
    confidence_multiplier: 0.99,
    description: 'Door contact sensor.',
  },
  hidden: {
    reliable: ['door_open_close'],
    optional: [],
    confidence_multiplier: 0.99,
    description: 'Door contact sensor.',
  },
};

// ============ Wearable ============

export const WEARABLE_CAPABILITIES: CapabilityMatrix = {
  wall_behavior: {
    reliable: ['heart_rate', 'respiration'],
    optional: ['activity_level', 'fall_detected'],
    confidence_multiplier: 0.90,
    description: 'Wearable watch/band for vital signs and activity.',
  },
  ceiling_fall: {
    reliable: ['activity_level', 'fall_detected'],
    optional: ['heart_rate'],
    confidence_multiplier: 0.85,
    description: 'Wearable for activity and fall detection.',
  },
  standalone: {
    reliable: ['heart_rate', 'respiration', 'activity_level'],
    optional: ['fall_detected'],
    confidence_multiplier: 0.88,
    description: 'Wearable multi-sensor device.',
  },
  hidden: {
    reliable: ['heart_rate', 'respiration'],
    optional: [],
    confidence_multiplier: 0.85,
    description: 'Wearable vital signs tracking.',
  },
};

// ============ Central Registry ============

export const SENSOR_CAPABILITY_REGISTRY: Record<
  SensorType,
  CapabilityMatrix
> = {
  fp2_radar: FP2_CAPABILITIES,
  bed_sensor: BED_SENSOR_CAPABILITIES,
  pir: PIR_CAPABILITIES,
  door_sensor: DOOR_SENSOR_CAPABILITIES,
  wearable: WEARABLE_CAPABILITIES,
  accelerometer: {
    wall_behavior: {
      reliable: ['activity_level', 'fall_detected'],
      optional: ['duration'],
      confidence_multiplier: 0.80,
      description: 'Wearable accelerometer for activity and fall detection.',
    },
    ceiling_fall: {
      reliable: ['activity_level', 'fall_detected'],
      optional: [],
      confidence_multiplier: 0.80,
      description: 'Accelerometer for activity and fall detection.',
    },
    standalone: {
      reliable: ['activity_level', 'fall_detected'],
      optional: [],
      confidence_multiplier: 0.80,
      description: 'Accelerometer activity tracking.',
    },
    hidden: {
      reliable: ['fall_detected'],
      optional: [],
      confidence_multiplier: 0.75,
      description: 'Hidden accelerometer for fall detection.',
    },
  },
  camera: {
    wall_behavior: {
      reliable: ['presence', 'activity_level'],
      optional: ['location', 'transition'],
      confidence_multiplier: 0.99,
      description: 'Video for presence and activity (privacy-first approach).',
    },
    ceiling_fall: {
      reliable: ['presence', 'fall_detected'],
      optional: [],
      confidence_multiplier: 0.99,
      description: 'Ceiling camera for fall detection.',
    },
    standalone: {
      reliable: ['presence', 'activity_level'],
      optional: [],
      confidence_multiplier: 0.95,
      description: 'Video surveillance.',
    },
    hidden: {
      reliable: ['presence'],
      optional: [],
      confidence_multiplier: 0.85,
      description: 'Hidden camera with limited visibility.',
    },
  },
};

// ============ Helper Functions ============

/**
 * Get capabilities for a specific device
 */
export function getDeviceCapabilities(
  sensorType: SensorType,
  installationMode: InstallationMode
): CapabilitySet {
  const matrix = SENSOR_CAPABILITY_REGISTRY[sensorType];
  if (!matrix) {
    throw new Error(`Unknown sensor type: ${sensorType}`);
  }

  return (
    matrix[installationMode] ||
    matrix.standalone ||
    {
      reliable: [],
      optional: [],
      confidence_multiplier: 0.5,
      description: 'Unknown configuration',
    }
  );
}

/**
 * Check if a capability is reliable for a device
 */
export function isCapabilityReliable(
  sensorType: SensorType,
  installationMode: InstallationMode,
  capability: SensorCapability
): boolean {
  const capabilities = getDeviceCapabilities(sensorType, installationMode);
  return capabilities.reliable.includes(capability);
}

/**
 * Get confidence multiplier for a device's detections
 */
export function getConfidenceMultiplier(
  sensorType: SensorType,
  installationMode: InstallationMode
): number {
  const capabilities = getDeviceCapabilities(sensorType, installationMode);
  return capabilities.confidence_multiplier;
}

/**
 * Get all reliable capabilities for a device
 */
export function getReliableCapabilities(
  sensorType: SensorType,
  installationMode: InstallationMode
): SensorCapability[] {
  const capabilities = getDeviceCapabilities(sensorType, installationMode);
  return capabilities.reliable;
}

/**
 * Create device capability configuration from registry
 */
export function createDeviceConfig(
  sensorType: SensorType,
  installationMode: InstallationMode
) {
  const capabilities = getDeviceCapabilities(sensorType, installationMode);
  return {
    reliable_capabilities: capabilities.reliable,
    optional_capabilities: capabilities.optional,
    confidence_multiplier: capabilities.confidence_multiplier,
    description: capabilities.description,
  };
}
