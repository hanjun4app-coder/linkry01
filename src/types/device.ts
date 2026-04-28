/**
 * Device Configuration Types
 *
 * Defines sensor devices with their capabilities, installation mode, and metadata.
 * Installation mode determines what capabilities are reliable for that device instance.
 */

import { RiskLevel } from './behavior';

// ============ Installation Modes ============

export type InstallationMode =
  | 'wall_behavior'      // Wall/side-mounted: behavior understanding focus
  | 'ceiling_fall'       // Ceiling-mounted: fall detection focus
  | 'standalone'         // Generic mode (backward compatibility)
  | 'hidden';            // Hidden/embedded sensor

// ============ Sensor Types ============

export type SensorType =
  | 'fp2_radar'          // Aqara FP2
  | 'bed_sensor'         // Pressure mat, accelerometer
  | 'pir'                // Passive infrared motion
  | 'door_sensor'        // Contact sensor
  | 'wearable'           // Smartwatch, fitness band
  | 'accelerometer'      // Wearable accelerometer
  | 'camera';            // Video (for privacy, minimal use)

// ============ Core Device Definition ============

export interface Device {
  // Identity
  device_id: string;
  elder_id: string;
  sensor_type: SensorType;
  device_name: string;                    // "Bedroom FP2", "Living Room PIR", etc.

  // Installation
  installation_mode: InstallationMode;    // Determines capability set
  room: string;                           // "bedroom", "living_room", "bathroom", "hallway", etc.
  mounting_height?: string;               // "wall", "ceiling", "side", "under_bed", "wrist", etc.

  // Capabilities
  reliable_capabilities: SensorCapability[]; // What this device is good at detecting
  optional_capabilities?: SensorCapability[]; // Secondary data this device can provide

  // Configuration
  thresholds?: DeviceThresholds;
  calibration?: DeviceCalibration;

  // Metadata
  installed_at: string;                   // ISO timestamp
  last_calibrated?: string;
  battery_level?: number;                 // 0-100, if applicable
  connection_status: 'connected' | 'disconnected' | 'error';

  // Flags
  is_active: boolean;
  is_primary_for_room?: boolean;          // Is this the primary sensor for this room
  notes?: string;
}

// ============ Sensor Capabilities ============

export type SensorCapability =
  | 'presence'                // Person in room
  | 'location'                // Which zone/area of room
  | 'duration'                // How long in location
  | 'transition'              // Movement between zones
  | 'activity_level'          // High/medium/low activity
  | 'fall_detected'            // Fall event detected
  | 'post_fall_inactivity'    // Inactivity after fall event
  | 'sleep_state'             // Sleeping vs awake
  | 'bed_occupancy'           // In bed vs out of bed
  | 'heart_rate'              // Pulse data
  | 'respiration'             // Breathing rate
  | 'door_open_close'         // Door open/close events
  | 'room_entry_exit'         // Entering/leaving room
  | 'zone_entry_exit';        // Entering/leaving specific zone

// ============ Device Thresholds ============

export interface DeviceThresholds {
  presence_timeout_minutes?: number;      // How long no motion = not present
  fall_sensitivity?: 'low' | 'medium' | 'high';
  motion_sensitivity?: 'low' | 'medium' | 'high';
  detection_confidence_min?: number;      // 0-1, minimum confidence to report
}

// ============ Device Calibration ============

export interface DeviceCalibration {
  baseline_motion_level?: number;         // Expected ambient motion for this location
  sensitivity_offset?: number;            // Device-specific sensitivity adjustment
  zone_mapping?: Record<string, string>;  // Zone IDs to room areas
  last_adjusted_at?: string;
  notes?: string;
}

// ============ Room Configuration ============

export interface RoomSensorSetup {
  room_id: string;
  room_name: string;
  primary_sensor: Device;                 // Main sensor for this room
  secondary_sensors?: Device[];           // Supporting sensors
  expected_activities: string[];          // What happens in this room
  safe_zones?: string[];                  // Safe areas defined for this room
}

// ============ System-Wide Sensor Configuration ============

export interface SensorConfiguration {
  devices: Device[];
  rooms: RoomSensorSetup[];
  installation_sop_version: string;       // Version of SOP used for this setup
  calibration_date: string;               // When system was last calibrated
  notes?: string;
}
