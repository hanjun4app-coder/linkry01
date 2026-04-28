# Sensor Fusion Integration into Status Engine

## 📋 Overview

This document describes how to integrate the sensor fusion system (`sensorFusion.ts`, `sensorConfig.ts`) into the existing status engine pipeline. The integration happens **before** the existing BehaviorEvent processing, adding real-time anomaly detection from hardware sensors.

### Integration Flow

```
┌─────────────────────────────────────┐
│ Current Sensor Data Sources         │
│ (FP2, Sleep Tracker, Door, Hallway) │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Construct SensorSnapshot            │
│ (Combine all sensor readings)       │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ analyzeAllAnomalies()               │
│ (5 intelligent judgment rules)      │
│ → AnomalyEvent[] output             │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Alert Pipeline                      │
│ (Debounce → Multi-signal →          │
│  Cooldown → Quiet Mode)             │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Convert AnomalyEvent → BehaviorEvent│
│ (Compatibility layer)               │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Existing Status Engine              │
│ (generateStatusViewModel)           │
└─────────────────────────────────────┘
```

---

## 🔌 Step 1: Update imports in statusEngine.ts

```typescript
// Add these imports at the top of statusEngine.ts

import {
  analyzeAllAnomalies,
  analyzeNoActivityAnomalies,
  analyzeNightBedExitNoReturn,
  analyzePathInterrupted,
  analyzeMedicationAnomalies,
  analyzeBathroomRiskElevation,
} from '@/lib/sensorFusion';
import { SENSOR_CONFIG } from '@/config/sensorConfig';
import {
  SensorSnapshot,
  SensorHistory,
  AnomalyEvent,
  FP2SensorData,
  SleepTrackerData,
  DoorSensorData,
  HallwaySensorData,
} from '@/types/sensor';
import { shouldPushAlert, getAlertSuppressionReason } from '@/lib/alertPipeline';
import { calculateConfidenceScore, getConfidenceLabel } from '@/lib/confidenceScorer';
```

---

## 🔌 Step 2: Create helper functions to construct SensorSnapshot

Add these functions to statusEngine.ts:

```typescript
/**
 * Construct current sensor snapshot from data sources
 * In production, these would come from:
 * - FP2 API/MQTT feed
 * - Sleep Tracker API
 * - Door Sensor API
 * - Hallway PIR/Radar API
 */
function constructCurrentSensorSnapshot(
  currentFP2Data?: FP2SensorData,
  currentSleepTrackerData?: SleepTrackerData,
  currentDoorSensorData?: DoorSensorData,
  currentHallwaySensorData?: HallwaySensorData
): SensorSnapshot {
  return {
    timestamp: new Date().toISOString(),
    fp2: currentFP2Data,
    sleep_tracker: currentSleepTrackerData,
    door_sensor: currentDoorSensorData,
    hallway_sensor: currentHallwaySensorData,
    data_completeness: {
      fp2_available: !!currentFP2Data,
      sleep_tracker_available: !!currentSleepTrackerData,
      door_sensor_available: !!currentDoorSensorData,
      hallway_sensor_available: !!currentHallwaySensorData,
    },
  };
}

/**
 * Construct historical sensor data for pattern analysis
 * This would aggregate data from the past hour, day, and week
 */
function constructSensorHistory(): SensorHistory {
  // In production: fetch from time-series database
  // For now, return empty structure
  return {
    last_hour: [],
    last_24h_summary: {
      total_bed_exit_count: 0,
      total_bed_exit_duration_minutes: 0,
      total_hallway_passages: 0,
      total_medication_cabinet_accesses: 0,
      entry_door_open_count: 0,
      average_fp2_presence_percentage: 0,
    },
    last_7days_pattern: {
      typical_sleep_start_hour: 22,
      typical_sleep_end_hour: 7,
      typical_activity_hours: [8, 12, 18],
      typical_bed_exit_count: 3,
      typical_medication_time_hours: [8, 12, 18],
    },
  };
}

/**
 * Convert AnomalyEvent to BehaviorEvent for compatibility
 * with existing alert pipeline and UI
 */
function convertAnomalyEventToBehaviorEvent(
  anomaly: AnomalyEvent,
  language: 'en' | 'zh' = 'en'
): BehaviorEvent {
  // Map anomaly_type to event_type
  const eventTypeMap: Record<string, string> = {
    no_activity_confirmed: 'no_activity',
    night_bed_exit_no_return: 'night_wake',
    path_interrupted: 'path_interrupted', // New type
    medication_cabinet_accessed: 'medication_cabinet_accessed', // New type
    medication_window_missed: 'medication_missed', // New type
    medication_access_without_followup: 'medication_without_followup', // New type
    bathroom_risk_elevated: 'bathroom_long_stay',
    unknown_location: 'unknown_location',
  };

  const eventType = eventTypeMap[anomaly.anomaly_type] || 'unknown_location';

  // Convert risk_level to match BehaviorEvent format
  const riskLevel = anomaly.risk_level === 'high' ? 'high' : 
                    anomaly.risk_level === 'attention' ? 'attention' : 
                    'normal';

  return {
    event_id: anomaly.id,
    event_type: eventType,
    timestamp: anomaly.timestamp,
    start_time: anomaly.timestamp,
    end_time: anomaly.timestamp,
    location: anomaly.detail?.current_fp2_location || 'unknown',
    risk_level: riskLevel as RiskLevel,
    confidence_score: anomaly.confidence_score, // ✨ NEW
    source: 'sensor_fusion', // Mark as sensor fusion output
    detail: anomaly.detail,
    evidence_sources: anomaly.evidence_sources, // ✨ NEW - for transparency
  };
}
```

---

## 🔌 Step 3: Create sensor fusion analysis function

Add this function to statusEngine.ts:

```typescript
/**
 * Run sensor fusion analysis and generate BehaviorEvents
 * 
 * ✨ NEW: This is the main entry point for sensor data
 * - Constructs sensor snapshot
 * - Calls analyzeAllAnomalies()
 * - Runs through alert pipeline
 * - Converts to BehaviorEvents
 */
function analyzeSensorDataAndGenerateEvents(
  currentFP2?: FP2SensorData,
  currentSleepTracker?: SleepTrackerData,
  currentDoorSensor?: DoorSensorData,
  currentHallwaySensor?: HallwaySensorData,
  language: 'en' | 'zh' = 'en'
): BehaviorEvent[] {
  // Step 1: Construct snapshot and history
  const snapshot = constructCurrentSensorSnapshot(
    currentFP2,
    currentSleepTracker,
    currentDoorSensor,
    currentHallwaySensor
  );

  const history = constructSensorHistory();

  // Step 2: Run sensor fusion analysis
  const anomalies = analyzeAllAnomalies(snapshot, history, {
    fp2_inactivity_minutes: SENSOR_CONFIG.fp2.inactivity_threshold_minutes,
    night_bed_exit_minutes: SENSOR_CONFIG.sleep_tracker.night_bed_exit_threshold_minutes,
    path_interrupted_seconds: SENSOR_CONFIG.hallway.expected_transit_time_seconds,
    bathroom_extended_minutes: SENSOR_CONFIG.anomaly_detection.bathroom_long_stay_minutes,
    medication_hours: SENSOR_CONFIG.door_sensor.medication_typical_hours,
  });

  // Step 3: Process through alert pipeline and confidence scoring
  const generatedEvents: BehaviorEvent[] = [];

  for (const anomaly of anomalies) {
    // Calculate confidence score (if not already set)
    const confidence =
      anomaly.confidence_score ||
      calculateConfidenceScore(
        { risk_level: anomaly.risk_level } as any,
        anomaly.evidence_sources.length,
        isNightTime()
      );

    // Check if should push alert
    const { should_alert, suppression_reason } = shouldPushAlert(
      convertAnomalyEventToBehaviorEvent(anomaly, language),
      anomaly.evidence_sources.length
    );

    // If alert is suppressed, skip this anomaly
    if (!should_alert) {
      console.log(
        `[Sensor Fusion] Alert suppressed: ${anomaly.anomaly_type}, reason: ${suppression_reason}`
      );
      continue;
    }

    // Convert to BehaviorEvent
    const behaviorEvent = convertAnomalyEventToBehaviorEvent(anomaly, language);
    behaviorEvent.confidence_score = confidence;

    generatedEvents.push(behaviorEvent);
  }

  return generatedEvents;
}

/**
 * Helper to check if current time is night
 */
function isNightTime(): boolean {
  const hour = new Date().getHours();
  return hour >= SENSOR_CONFIG.sleep_tracker.night_start_hour || 
         hour < SENSOR_CONFIG.sleep_tracker.night_end_hour;
}
```

---

## 🔌 Step 4: Update generateStatusViewModel to include sensor fusion

Modify the existing `generateStatusViewModel` function:

```typescript
/**
 * 生成页面状态视图模型
 * ✨ ENHANCED: Now integrates sensor fusion data
 * 
 * @param events - 行为事件数组 (existing events)
 * @param dailySummary - 今日摘要数据
 * @param language - 语言（默认英文）
 * @param sensorData - ✨ NEW: Current sensor readings
 * @returns 页面需要展示的所有数据
 */
export function generateStatusViewModel(
  events: BehaviorEvent[],
  dailySummary: DailyBehaviorSummaryInput,
  language: 'en' | 'zh' = 'en',
  // ✨ NEW: Optional sensor data for real-time fusion
  sensorData?: {
    fp2?: FP2SensorData;
    sleepTracker?: SleepTrackerData;
    doorSensor?: DoorSensorData;
    hallwaySensor?: HallwaySensorData;
  }
): StatusViewModel {
  // ✨ NEW: If sensor data provided, generate anomaly events and merge
  let allEvents = [...events];
  if (sensorData) {
    const sensorGeneratedEvents = analyzeSensorDataAndGenerateEvents(
      sensorData.fp2,
      sensorData.sleepTracker,
      sensorData.doorSensor,
      sensorData.hallwaySensor,
      language
    );
    
    // Merge with existing events (sensor fusion events added at end for recency)
    allEvents = [...events, ...sensorGeneratedEvents];
  }

  // Rest of the existing logic remains the same, using allEvents instead of events
  // 1. 获取整体状态等级
  const overall_status = dailySummary.highest_risk;

  // 2. 生成今日摘要文案
  const daily_summary = generateDailySummaryText(dailySummary, language);

  // 3. 获取当前状态（基于最新事件）
  const latestEvent = allEvents.length > 0 ? allEvents[allEvents.length - 1] : null;
  const current_state = latestEvent
    ? {
        label: getCurrentStateLabel(latestEvent, language),
        summary: generateBehaviorText(latestEvent, language).summary,
      }
    : {
        label: language === 'en' ? 'Location unknown' : '位置未知',
        summary: language === 'en' ? 'No activity recorded.' : '暂无活动记录。',
      };

  // ✨ 4. 生成状态上下文（新增）
  const state_context = generateStateContext(allEvents, dailySummary);

  // ✨ 5. 计算是否显示提醒和提示（新增）
  const { primary_alert, show_state_notice, state_notice_text } =
    determineAlertAndNoticeDisplay(
      allEvents,
      state_context,
      language
    );

  // 6. 获取最近的行为记录（3-5 条）
  const recent_behavior_texts = getRecentBehaviorTexts(allEvents, 4, language);

  // 7. 构建视图模型
  const viewModel: StatusViewModel = {
    overall_status,
    headline: daily_summary.headline,
    current_state,
    primary_alert,
    recent_behavior_texts,
    daily_summary,
    state_context,
    trend_metrics: {
      recent_3day_avg: state_context.consecutive_anomaly_days > 0 ? 120 : 180,
      previous_3day_avg: 180,
      drop_ratio: state_context.activity_drop_ratio,
      trend: state_context.activity_trend,
    },
    evidence_sources: state_context.evidence,
    show_state_notice,
    state_notice_text,
    // ✨ NEW: Add sensor fusion indicators
    sensor_fusion_info: sensorData ? {
      enabled: true,
      sensor_count: Object.values(sensorData).filter(v => v).length,
      last_analysis: new Date().toISOString(),
    } : undefined,
    metadata: {
      total_events: allEvents.length,
      alert_count: dailySummary.alerts_count,
      last_update_time: new Date().toLocaleString(
        language === 'en' ? 'en-US' : 'zh-CN'
      ),
    },
  };

  return viewModel;
}
```

---

## 🔌 Step 5: Update StatusViewModel type (in types/status.ts)

Add these optional fields to the `StatusViewModel` interface:

```typescript
export interface StatusViewModel {
  // ... existing fields ...

  // ✨ NEW: Confidence scoring
  confidence_score?: number;

  // ✨ NEW: Evidence sources for transparency
  evidence_sources?: string[];

  // ✨ NEW: Sensor fusion info
  sensor_fusion_info?: {
    enabled: boolean;
    sensor_count: number;
    last_analysis: string; // ISO timestamp
  };

  // ... rest of existing fields ...
}
```

---

## 💡 Usage Example

### Example 1: Without Sensor Data (Backward Compatible)

```typescript
// Existing usage - still works
const viewModel = generateStatusViewModel(
  existingBehaviorEvents,
  dailySummaryData,
  'en'
);
```

### Example 2: With Real-Time Sensor Data (New)

```typescript
// New usage with sensor fusion
const currentSensorData = {
  fp2: {
    sensor_id: 'fp2_001',
    presence: true,
    location: 'bedroom',
    duration_seconds: 3600,
    last_updated: new Date().toISOString(),
    signal_strength: 85,
    confidence: 0.95,
  },
  sleepTracker: {
    sensor_id: 'sleep_001',
    bed_presence: true,
    sleep_state: 'sleeping',
    last_updated: new Date().toISOString(),
    exit_count_today: 2,
  },
  doorSensor: {
    sensor_id: 'door_001',
    entry_door_open: false,
    medication_cabinet_open: false,
    last_updated: new Date().toISOString(),
    medication_cabinet_access_count_today: 1,
  },
  hallwaySensor: {
    sensor_id: 'hallway_001',
    passage_detected: false,
    last_updated: new Date().toISOString(),
    passage_count_5min: 0,
  },
};

const viewModel = generateStatusViewModel(
  existingBehaviorEvents,
  dailySummaryData,
  'en',
  currentSensorData // ✨ NEW: Pass sensor data
);

// Access sensor fusion info in UI
if (viewModel.sensor_fusion_info?.enabled) {
  console.log(`Sensor fusion active with ${viewModel.sensor_fusion_info.sensor_count} sensors`);
}
```

### Example 3: Progressive Integration (Recommended)

```typescript
// Start with just one sensor
const viewModel = generateStatusViewModel(
  events,
  summary,
  'en',
  {
    fp2: getCurrentFP2Data(),
    // Add other sensors as they become available
  }
);
```

---

## 🎯 Data Flow Diagram

```
Input Data Sources
├── FP2 (presence_detection)
├── Sleep Tracker (bed_state)
├── Door Sensor (entry_door, medication_cabinet)
└── Hallway PIR/Radar (passage_detection)
        │
        ▼
constructCurrentSensorSnapshot()
        │
        ▼
analyzeAllAnomalies()
├── analyzeNoActivityAnomalies() → AnomalyEvent
├── analyzeNightBedExitNoReturn() → AnomalyEvent
├── analyzePathInterrupted() → AnomalyEvent
├── analyzeMedicationAnomalies() → AnomalyEvent[]
└── analyzeBathroomRiskElevation() → AnomalyEvent
        │
        ▼
shouldPushAlert() (Alert Pipeline)
├── Debounce (60s)
├── Multi-signal check (≥2)
├── Cooldown (30min)
└── Quiet Mode (22:00-07:00)
        │
        ▼
calculateConfidenceScore()
        │
        ▼
convertAnomalyEventToBehaviorEvent()
        │
        ▼
Merge with existing BehaviorEvent[]
        │
        ▼
generateStatusViewModel() (Existing logic)
        │
        ▼
StatusViewModel (UI display)
```

---

## 🔍 Confidence Score Integration

The system now returns `confidence_score` at multiple levels:

```typescript
// 1. From AnomalyEvent (generated by sensor fusion)
anomaly.confidence_score // 0-1 range

// 2. Re-calculated by confidence scorer
const confidence = calculateConfidenceScore(
  event,
  evidenceCount,
  hasTimeContext
);

// 3. Displayed in BehaviorEvent
behaviorEvent.confidence_score = confidence;

// 4. Available in StatusViewModel
viewModel.confidence_score = eventConfidence;

// 5. User-facing label
const label = getConfidenceLabel(confidence, language);
// Returns: "Very uncertain", "Something might be worth checking", etc.
```

---

## ✅ Backward Compatibility

This integration is **fully backward compatible**:

- Existing code without sensor data continues to work
- New sensor data is optional
- Alert pipeline and confidence scorer work independently
- Can be rolled out gradually (one sensor at a time)

---

## 🧪 Testing Integration

### Test Case 1: No Sensor Data (Baseline)
```typescript
const viewModel = generateStatusViewModel(events, summary);
assert(viewModel.sensor_fusion_info === undefined);
```

### Test Case 2: With Sensor Data
```typescript
const viewModel = generateStatusViewModel(events, summary, 'en', sensorData);
assert(viewModel.sensor_fusion_info?.enabled === true);
assert(viewModel.sensor_fusion_info?.sensor_count === 4);
```

### Test Case 3: Alert Pipeline Suppression
```typescript
// Anomaly should be suppressed by cooldown
const event1 = generateStatusViewModel(events, summary, 'en', sensor1);
const event2 = generateStatusViewModel(events, summary, 'en', sensor2); // Same anomaly 5 sec later
assert(event2.primary_alert === null); // Suppressed by cooldown
```

### Test Case 4: Confidence Scoring
```typescript
// Single signal should have lower confidence
const lowConfidence = calculateConfidenceScore(event, 1, false);
assert(lowConfidence < 0.6);

// Multi-signal should have higher confidence  
const highConfidence = calculateConfidenceScore(event, 3, true);
assert(highConfidence > 0.75);
```

---

## 📊 Next Steps

1. ✅ **Phase 1-5 Complete**: Core sensor fusion system, alert pipeline, confidence scoring
2. ✅ **Phase 6 Complete**: Integration guide (this document)
3. **Phase 7**: Modify statusEngine.ts with these integration changes
4. **Phase 8**: Update StatusDashboard.tsx to display confidence_score indicators
5. **Phase 9**: Testing and verification with real sensor data
6. **Phase 10**: Deploy and monitor system performance

---

## 📚 Files Involved

| File | Change | Priority |
|------|--------|----------|
| src/lib/statusEngine.ts | Add sensor fusion helper functions, update generateStatusViewModel | HIGH |
| src/types/status.ts | Add confidence_score, sensor_fusion_info fields | HIGH |
| src/types/behavior.ts | Ensure confidence_score field present | DONE |
| src/components/StatusDashboard.tsx | Display confidence indicators | MEDIUM |
| src/lib/sensorFusion.ts | Already complete | - |
| src/config/sensorConfig.ts | Already complete | - |
| src/lib/alertPipeline.ts | Already complete | - |
| src/lib/confidenceScorer.ts | Already complete | - |

---

## 💬 Summary

This integration adds **real-time anomaly detection** powered by multi-sensor fusion while maintaining 100% backward compatibility with the existing system. The alert pipeline (debounce, cooldown, quiet mode) and confidence scoring ensure that users only see relevant, high-confidence alerts.

The gradual rollout capability means you can start with one sensor (e.g., FP2) and progressively add more sensors as they become available, each time improving the system's accuracy without disrupting existing functionality.
