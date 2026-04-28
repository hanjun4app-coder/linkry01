# Sensor Installation SOP (Standard Operating Procedure)

**Version**: 2.0 (Installation Mode Aware)  
**Effective Date**: April 2026  
**Last Updated**: April 2026

---

## Overview

This SOP defines how to install and configure sensors for elderly care monitoring. The critical principle is:

> **One FP2 should not be expected to do both behavior understanding and fall detection perfectly.**

- **Wall-mounted FP2** = Behavior understanding (presence, zones, duration, transitions, activity)
- **Ceiling-mounted FP2** = Fall detection assistance (fall_detected, post_fall_inactivity)

Each sensor mode has specific capabilities that are reliable. Installing a sensor in the wrong mode will degrade system accuracy.

---

## Room-by-Room Installation Guide

### Bedroom Setup

**Purpose**: Sleep tracking, night activity, bed occupancy, out-of-bed detection

**Primary Sensors**:
- **Bed Pressure Sensor** (Sleep tracker)
  - Installation: Under mattress or on bed frame
  - Purpose: Sleep/wake state, bed occupancy
  - Reliability: ✅ 98% - handles sleep detection
  
- **Wall-Mounted FP2 Radar** (Behavior understanding)
  - Installation: Wall mounted, 1-1.5m height, opposite foot of bed
  - Position: Far side of bed to detect out-of-bed movement
  - Purpose: Out-of-bed activity, hallway approach, movement intensity
  - Capabilities: presence, location, duration, activity_level
  - Reliability: ✅ 95%
  - Mode: `wall_behavior`

**Optional Ceiling FP2** (Only if fall risk is high):
- Installation: Ceiling mount near bed
- Purpose: Detect falls when getting in/out of bed
- Capabilities: fall_detected, post_fall_inactivity
- Reliability: ⚠️ 85% (secondary fall detection only)
- Mode: `ceiling_fall`
- **Important**: Do NOT expect ceiling FP2 to track bedroom behavior. Its only job is fall detection.

**Configuration Example**:
```json
{
  "bedroom_sensors": [
    {
      "device_id": "bed_pressure_001",
      "sensor_type": "bed_sensor",
      "installation_mode": "wall_behavior",
      "room": "bedroom",
      "mounting_height": "under_bed",
      "is_primary_for_room": true
    },
    {
      "device_id": "fp2_bedroom_wall",
      "sensor_type": "fp2_radar",
      "installation_mode": "wall_behavior",
      "room": "bedroom",
      "mounting_height": "wall",
      "is_primary_for_room": false
    },
    {
      "device_id": "fp2_bedroom_ceiling",
      "sensor_type": "fp2_radar",
      "installation_mode": "ceiling_fall",
      "room": "bedroom",
      "mounting_height": "ceiling",
      "is_primary_for_room": false,
      "is_active": true  // Only if fall risk warrants
    }
  ]
}
```

---

### Living Room Setup

**Purpose**: Daily activity tracking, safe-zone presence, activity intensity

**Primary Sensors**:
- **Wall-Mounted FP2 Radar** (Behavior understanding)
  - Installation: Wall mounted, 1.5m height, central position
  - Coverage: Full room visibility of seating area and main activity zones
  - Purpose: Presence, activity level, zone transitions (sofa → dining → kitchen)
  - Capabilities: presence, location, duration, transition, activity_level
  - Reliability: ✅ 95%
  - Mode: `wall_behavior`

**Supporting Sensors**:
- **Door Sensor** (Entry/exit)
  - Installation: Main entrance door frame
  - Purpose: Context - is person at home or away?
  - Reliability: ✅ 99%
  - Mode: Any (location independent)

**Configuration Example**:
```json
{
  "living_room_sensors": [
    {
      "device_id": "fp2_living_room_main",
      "sensor_type": "fp2_radar",
      "installation_mode": "wall_behavior",
      "room": "living_room",
      "mounting_height": "wall",
      "is_primary_for_room": true
    },
    {
      "device_id": "door_main_entrance",
      "sensor_type": "door_sensor",
      "installation_mode": "standalone",
      "room": "entrance",
      "mounting_height": "door_frame",
      "is_primary_for_room": true
    }
  ]
}
```

**Activity Zones** (Defined for wall FP2):
- Sofa: Primary rest area
- Dining: Eating/meals area
- Kitchen approach: Entering kitchen from living room
- Window: Natural light area

---

### Bathroom Setup

**Purpose**: Stay duration, activity intensity, frequent visits

**Primary Sensors**:
- **Wall-Mounted FP2 Radar** (Side/High-Wall Position)
  - Installation: High on wall (1.8-2.0m), side corner (not directly above toilet)
  - Purpose: Presence detection, duration, bathroom-specific activity
  - Capabilities: presence, duration, activity_level
  - Reliability: ✅ 90% (elevated position reduces privacy concern)
  - Mode: `wall_behavior`
  
  **Privacy Note**: Position high and to side. Do NOT mount to directly observe toilet or shower area.

**Alternative to FP2**:
- **Radar Sensor** (Ultrasonic or mmWave)
  - Purpose: Presence and duration only (simpler, privacy-first)
  - Reliability: ✅ 85%

**Configuration Example**:
```json
{
  "bathroom_sensors": [
    {
      "device_id": "fp2_bathroom_corner",
      "sensor_type": "fp2_radar",
      "installation_mode": "wall_behavior",
      "room": "bathroom",
      "mounting_height": "high_wall",
      "is_primary_for_room": true,
      "notes": "Mounted high corner, not above toilet"
    }
  ]
}
```

**Detection Rules**:
- Normal bathroom visit: 3-10 minutes
- Long bathroom visit: 15+ minutes (warrants check-in)
- Multiple quick visits: High-frequency short visits (potential diarrhea or incontinence)

---

### Hallway Setup

**Purpose**: Movement between rooms, fall risk zone, night navigation

**Primary Sensors**:
- **PIR Motion Sensor** (Passive Infrared)
  - Installation: Wall or ceiling at eye level, hallway center
  - Purpose: Movement detection, passage tracking
  - Capabilities: presence, room_entry_exit
  - Reliability: ✅ 85%
  - Mode: `wall_behavior`

**Alternative if Fall Risk is High**:
- **Ceiling-Mounted FP2** (Fall detection focus)
  - Installation: Ceiling center
  - Purpose: Fall detection during nighttime navigation
  - Capabilities: fall_detected, presence
  - Reliability: ⚠️ 80%
  - Mode: `ceiling_fall`
  - **Note**: Less reliable for movement tracking than wall PIR

**Configuration Example**:
```json
{
  "hallway_sensors": [
    {
      "device_id": "pir_hallway_main",
      "sensor_type": "pir",
      "installation_mode": "wall_behavior",
      "room": "hallway",
      "mounting_height": "wall",
      "is_primary_for_room": true
    }
  ]
}
```

---

### Entrance/Exit Setup

**Purpose**: Home/away context, arrival/departure tracking

**Primary Sensors**:
- **Door Sensor** (Contact sensor on main door)
  - Installation: Door frame of main entrance
  - Purpose: Provides context - elder left home or arrived home?
  - Capabilities: door_open_close, room_entry_exit
  - Reliability: ✅ 99%
  - Mode: Any (location independent)

**Supporting Sensor** (Optional):
- **PIR on Porch** (Exterior motion)
  - Installation: Porch/vestibule area
  - Purpose: Detect if elder is outside before entering
  - Reliability: ✅ 80% (weather dependent)

**Configuration Example**:
```json
{
  "entrance_sensors": [
    {
      "device_id": "door_sensor_main",
      "sensor_type": "door_sensor",
      "installation_mode": "standalone",
      "room": "entrance",
      "mounting_height": "door_frame",
      "is_primary_for_room": true
    }
  ]
}
```

---

### Medication Cabinet/Storage

**Purpose**: Medication adherence tracking

**Primary Sensors**:
- **Door Sensor** (Cabinet door contact)
  - Installation: Medication cabinet or drawer
  - Purpose: Cabinet open/close events (medication access?)
  - Capabilities: door_open_close
  - Reliability: ✅ 99%
  - Mode: Any (location independent)

**Configuration Example**:
```json
{
  "medication_sensors": [
    {
      "device_id": "door_med_cabinet",
      "sensor_type": "door_sensor",
      "installation_mode": "standalone",
      "room": "kitchen",
      "mounting_height": "cabinet",
      "is_primary_for_room": false,
      "notes": "Medication cabinet door sensor"
    }
  ]
}
```

---

## FP2 Installation Mode Decision Matrix

| Installation Mode | Best For | Avoid Using For | Typical Rooms |
|---|---|---|---|
| **wall_behavior** | Behavior understanding, zone tracking, activity detection | Fall detection (not primary) | Bedroom, Living room, Bathroom, Hallway |
| **ceiling_fall** | Fall detection, overhead coverage | Detailed behavior tracking, zone analysis | Bedroom (optional), High-risk areas |

**Decision Tree**:
1. Is the primary goal detailed behavior tracking (zones, transitions, activity)?
   → Use `wall_behavior` FP2
2. Is the primary goal fall detection?
   → Use `ceiling_fall` FP2 (or wearable accelerometer)
3. Do you need BOTH?
   → Install 2 FP2s: one in wall_behavior mode, one in ceiling_fall mode
   → **Do NOT expect one FP2 to do both perfectly**

---

## Installation Checklist

- [ ] Identify all rooms and determine sensor needs
- [ ] For each room, assign primary and secondary sensors
- [ ] Assign correct `installation_mode` to each sensor
- [ ] Verify wall_behavior devices are in wall/side positions
- [ ] Verify ceiling_fall devices are in ceiling positions
- [ ] Configure device database with `installation_mode` field
- [ ] Update sensorFusion logic to validate mode-capability pairs
- [ ] Test each sensor's reliable capabilities per mode
- [ ] Document placement with photos
- [ ] Create RoomSensorSetup configuration
- [ ] Run integration tests per room

### Test Each Sensor

For each installed sensor:
1. Verify power/connectivity
2. Confirm readings appear in system
3. Validate that readings match expected capabilities for installation_mode
4. Test anomaly detection (should flag unexpected capabilities)

**Example Test for wall_behavior FP2**:
```
✅ Presence detection works
✅ Zone transitions recorded
✅ Activity level changes detected
✅ Duration tracking accurate
❌ Ceiling_fall readings: Should NOT appear (flag if present)
```

**Example Test for ceiling_fall FP2**:
```
✅ Fall pattern recognized
✅ Post-fall inactivity detected
✅ Presence tracked
❌ Zone detail: Should NOT be used (flag in logs if used for behavior)
```

---

## Troubleshooting

### Problem: Wall FP2 Not Detecting Zones

**Possible Causes**:
- Wall FP2 mounted at ceiling height (should be 1-1.5m)
- FP2 pointed at wall instead of room
- Too far from activity areas
- Room is too large for single FP2

**Solution**:
- Lower mounting height
- Reorient to face main activity areas
- Add second wall FP2 for larger rooms
- Use combination of wall FP2 + PIR

### Problem: Ceiling FP2 Triggering False Fall Alerts

**Possible Causes**:
- Ceiling FP2 detecting normal activity as fall
- Sensitivity too high
- Mounted too close to moving obstacles

**Solution**:
- Adjust sensitivity setting (medium preferred)
- Mount in stable ceiling location away from fans/lights
- Increase confidence threshold before alerting
- Combine with post_fall_inactivity requirement

### Problem: Behavioral Analysis Missing Zone Details

**Possible Causes**:
- Using ceiling_fall FP2 for behavior analysis (wrong mode!)
- Wall FP2 blocked or at wrong angle
- No wall FP2 installed

**Solution**:
- Verify devices are in correct installation_mode
- Reposition wall FP2 to face activity areas
- Install wall FP2 if missing
- Check sensor fusion logs for capability mismatch warnings

---

## Maintenance Schedule

| Task | Frequency | Notes |
|---|---|---|
| Check battery levels | Weekly | Battery indicator in app |
| Verify connectivity | Weekly | All devices should show "connected" |
| Clean sensor lens | Monthly | Dust reduces detection accuracy |
| Recalibration | Quarterly | Or after major furniture rearrangement |
| Documentation review | Quarterly | Update photos/notes if changed |

---

## Safety Considerations

### Privacy

- Bathroom FP2 should be high-mounted, never pointed at toilet/shower
- Do NOT use cameras in private areas
- Document privacy settings in device configuration

### Reliability

- System assumes wall_behavior FP2 is reliable for detailed tracking
- System assumes ceiling_fall FP2 is fall-detection focused ONLY
- Mixing modes (using ceiling FP2 for behavior) degrades accuracy
- Always install in pairs for redundancy in critical areas

### Accessibility

- Ensure all sensors are accessible for maintenance
- Label all devices clearly
- Keep documentation current

---

## Device Configuration Template

```json
{
  "room_id": "bedroom_001",
  "room_name": "Master Bedroom",
  "primary_sensor": {
    "device_id": "bed_pressure_001",
    "sensor_type": "bed_sensor",
    "installation_mode": "wall_behavior",
    "room": "bedroom",
    "mounting_height": "under_bed",
    "is_active": true,
    "is_primary_for_room": true,
    "reliable_capabilities": ["bed_occupancy", "sleep_state"],
    "optional_capabilities": []
  },
  "secondary_sensors": [
    {
      "device_id": "fp2_bedroom_wall",
      "sensor_type": "fp2_radar",
      "installation_mode": "wall_behavior",
      "room": "bedroom",
      "mounting_height": "wall",
      "is_active": true,
      "is_primary_for_room": false,
      "reliable_capabilities": ["presence", "location", "duration", "transition", "activity_level"],
      "optional_capabilities": ["post_fall_inactivity"]
    }
  ],
  "expected_activities": ["sleep", "rest", "out_of_bed", "bathroom_approach"],
  "safe_zones": ["bed", "side_of_bed", "bedroom"]
}
```

---

## Sign-Off

This SOP defines installation standards for elderly care monitoring. Deviation from these guidelines may reduce system accuracy and reliability.

**Document Owner**: Engineering Team  
**Last Review**: April 2026  
**Next Review**: July 2026
