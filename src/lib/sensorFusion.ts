/**
 * 多传感器融合引擎
 * 综合来自 FP2、Sleep Tracker、Door、Hallway 的数据
 * 实现智能异常检测
 *
 * 核心原则：
 * - 单一信号默认不触发高风险（需多信号组合）
 * - 每个判断都返回 confidence_score 和 evidence_sources
 * - 只做风险提示，不做医疗诊断
 */

import {
  SensorSnapshot,
  SensorHistory,
  AnomalyEvent,
  FP2SensorData,
  SleepTrackerData,
  DoorSensorData,
  HallwaySensorData,
} from '@/types/sensor';
import { DEFAULT_RULES } from '@/config/defaultRules';

/**
 * 时间工具函数
 */
function getMinutesSince(timestamp: string | undefined): number | null {
  if (!timestamp) return null;
  return Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000 / 60);
}

function getSecondsSince(timestamp: string | undefined): number | null {
  if (!timestamp) return null;
  return Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
}

function getHourOfDay(timestamp: string = new Date().toISOString()): number {
  return new Date(timestamp).getHours();
}

function isNightTime(hour: number = getHourOfDay()): boolean {
  // 夜间定义：22:00-07:00
  return hour >= 22 || hour < 7;
}

/**
 * 判断1: NO_ACTIVITY 智能判断
 *
 * 逻辑：不只根据 FP2 无活动报警，必须结合多个传感器确认
 * - 入户门关闭 ✓
 * - 床垫上有人 ✓
 * - 无近期走廊经过 ✓
 * → 才确认真正无活动
 *
 * 否则可能是：老人在室外、在其他区域、传感器故障
 */
export function analyzeNoActivityAnomalies(
  snapshot: SensorSnapshot,
  history: SensorHistory,
  fp2_inactivity_minutes: number = 120 // FP2 检测到无活动的时长
): AnomalyEvent[] {
  const anomalies: AnomalyEvent[] = [];

  // 前置条件：FP2 确实检测到无活动
  if (!snapshot.fp2 || snapshot.fp2.presence) {
    return anomalies; // FP2 检测到活动，不处理
  }

  const evidences: string[] = [];
  let confidence = 0;

  // 检查1：入户门是否关闭？
  const entryDoorClosed =
    snapshot.door_sensor && !snapshot.door_sensor.entry_door_open;
  if (entryDoorClosed) {
    evidences.push('sensor:door_closed');
  }

  // 检查2：老人是否在床上？
  const inBed = snapshot.sleep_tracker && snapshot.sleep_tracker.bed_presence;
  if (inBed) {
    evidences.push('sensor:bed_presence');
  }

  // 检查3：最近有走廊经过吗？（最近5分钟）
  const recentPassage =
    snapshot.hallway_sensor &&
    snapshot.hallway_sensor.passage_detected &&
    getSecondsSince(snapshot.hallway_sensor.passage_time) &&
    getSecondsSince(snapshot.hallway_sensor.passage_time)! < 300;

  if (!recentPassage) {
    evidences.push('sensor:no_recent_passage');
  }

  // 风险评估
  if (entryDoorClosed && inBed) {
    // 多信号确认：门关+床垫有人 → 正常睡眠，无风险
    confidence = 0; // 无异常
  } else if (entryDoorClosed && !recentPassage) {
    // 多信号确认：门关+无走廊经过 → 可能睡眠或安静休息
    confidence = 0.3; // 低风险
    evidences.push('inference:likely_resting');
  } else if (!entryDoorClosed && !recentPassage && inBed) {
    // 门打开但无passage且在床上 → 可疑，但概率低
    confidence = 0.4;
    evidences.push('inference:door_open_bed_occupied');
  } else if (!entryDoorClosed && !recentPassage && !inBed) {
    // 最高风险：门打开+无活动+无passage+不在床上 → 真实异常
    confidence = 0.85; // 高度可信
    evidences.push('inference:confirmed_no_activity');

    // 创建异常事件
    anomalies.push({
      id: `no_activity_${Date.now()}`,
      anomaly_type: 'no_activity_confirmed',
      timestamp: new Date().toISOString(),
      risk_level: confidence > 0.7 ? 'high' : 'attention',
      confidence_score: confidence,
      evidence_sources: evidences,
      involved_sensors: [
        'fp2',
        ...(snapshot.door_sensor ? ['door'] : []),
        ...(snapshot.sleep_tracker ? ['sleep_tracker'] : []),
        ...(snapshot.hallway_sensor ? ['hallway'] : []),
      ],
      detail: {
        fp2_inactivity_minutes,
        door_closed: entryDoorClosed,
        in_bed: inBed,
        recent_passage: recentPassage,
        time_of_day: getHourOfDay(),
        is_night: isNightTime(),
      },
      suggestion:
        confidence > 0.7
          ? 'Please check on your loved one with a phone call.'
          : 'Consider checking in if this continues.',
    });
  }

  return anomalies;
}

/**
 * 判断2: NIGHT_BED_EXIT_NO_RETURN
 *
 * 逻辑：
 * - 当前是夜间（22:00-07:00）
 * - Sleep tracker 检测到离床
 * - 超过设定时间未回床
 * - 没有 FP2 活动检测（仍在卧室区域）
 * → 可能跌倒或需要帮助
 */
export function analyzeNightBedExitNoReturn(
  snapshot: SensorSnapshot,
  max_out_of_bed_minutes: number = 10 // 超过10分钟未回床报警
): AnomalyEvent[] {
  const anomalies: AnomalyEvent[] = [];

  // 前置条件：当前是夜间且 sleep tracker 可用
  if (!snapshot.sleep_tracker || snapshot.sleep_tracker.bed_presence) {
    return anomalies; // 在床上，无问题
  }

  if (!isNightTime()) {
    return anomalies; // 不是夜间，不适用此规则
  }

  // 检查离床时长
  const outOfBedMinutes = snapshot.sleep_tracker.out_of_bed_duration_seconds
    ? Math.floor(snapshot.sleep_tracker.out_of_bed_duration_seconds / 60)
    : null;

  if (!outOfBedMinutes || outOfBedMinutes < max_out_of_bed_minutes) {
    return anomalies; // 离床时间还不够长
  }

  const evidences: string[] = [
    'sensor:bed_exit_detected',
    'sensor:extended_out_of_bed',
    'context:nighttime',
  ];

  // 检查是否有 FP2 活动（表示在移动，不是跌倒）
  const hasActivity = snapshot.fp2 && snapshot.fp2.presence;
  if (!hasActivity) {
    evidences.push('sensor:no_fp2_activity');
  }

  // 风险评分：离床越久，风险越高
  let confidence = Math.min(0.95, 0.6 + (outOfBedMinutes - max_out_of_bed_minutes) / 30 * 0.3);

  // 如果没有FP2活动，风险提高
  if (!hasActivity) {
    confidence = Math.min(1, confidence + 0.2);
    evidences.push('inference:possible_fall_risk');
  } else {
    evidences.push('inference:out_of_bed_but_moving');
  }

  // 创建异常事件
  anomalies.push({
    id: `night_bed_exit_${Date.now()}`,
    anomaly_type: 'night_bed_exit_no_return',
    timestamp: new Date().toISOString(),
    risk_level:
      confidence > 0.75 || !hasActivity
        ? 'high'
        : confidence > 0.6
          ? 'attention'
          : 'normal',
    confidence_score: confidence,
    evidence_sources: evidences,
    involved_sensors: [
      'sleep_tracker',
      ...(snapshot.fp2 ? ['fp2'] : []),
    ],
    detail: {
      out_of_bed_minutes: outOfBedMinutes,
      threshold_minutes: max_out_of_bed_minutes,
      has_activity: hasActivity,
      bed_exit_time: snapshot.sleep_tracker.bed_exit_time,
      time: getHourOfDay(),
    },
    suggestion:
      !hasActivity
        ? 'Please check on your loved one immediately.'
        : 'Your loved one is up at night. A gentle check-in is recommended.',
  });

  return anomalies;
}

/**
 * 判断3: PATH_INTERRUPTED
 *
 * 逻辑：
 * - Hallway sensor 检测到经过
 * - 但在 90 秒内，老人没有在目的地区域（卧室/客厅/卫生间）出现
 * → 可能：停留在走廊、卡住、或传感器故障
 */
export function analyzePathInterrupted(
  snapshot: SensorSnapshot,
  max_transit_seconds: number = 90 // 90秒内应该到达目的地
): AnomalyEvent[] {
  const anomalies: AnomalyEvent[] = [];

  // 前置条件：hallway sensor 检测到经过
  if (!snapshot.hallway_sensor || !snapshot.hallway_sensor.passage_detected) {
    return anomalies;
  }

  const passageSeconds = getSecondsSince(
    snapshot.hallway_sensor.passage_time
  );
  if (!passageSeconds || passageSeconds < max_transit_seconds) {
    return anomalies; // 还在 transit 时间窗口内
  }

  // 检查 FP2 是否在预期区域
  const hasArrivedAtDestination =
    snapshot.fp2 &&
    snapshot.fp2.presence &&
    snapshot.fp2.location &&
    ['bedroom', 'living_room', 'bathroom'].includes(snapshot.fp2.location);

  if (hasArrivedAtDestination) {
    return anomalies; // 已到达目的地，无问题
  }

  const evidences: string[] = [
    'sensor:hallway_passage',
    'sensor:no_destination_arrival',
    'inference:path_interrupted',
  ];

  // 确定风险等级
  let confidence = 0.5;
  let risk_level: 'attention' | 'high' = 'attention';

  // 如果走廊经过后很长时间未到达（>3分钟）且 FP2 无活动
  if (passageSeconds > 180 && (!snapshot.fp2 || !snapshot.fp2.presence)) {
    confidence = 0.8;
    risk_level = 'high';
    evidences.push('inference:prolonged_no_arrival');
  } else if (passageSeconds > max_transit_seconds * 2) {
    confidence = 0.65;
    risk_level = 'attention';
    evidences.push('inference:delayed_arrival');
  }

  // 创建异常事件
  anomalies.push({
    id: `path_interrupted_${Date.now()}`,
    anomaly_type: 'path_interrupted',
    timestamp: new Date().toISOString(),
    risk_level,
    confidence_score: confidence,
    evidence_sources: evidences,
    involved_sensors: ['hallway', ...(snapshot.fp2 ? ['fp2'] : [])],
    detail: {
      seconds_since_passage: passageSeconds,
      threshold_seconds: max_transit_seconds,
      passage_direction: snapshot.hallway_sensor.passage_direction,
      current_fp2_location: snapshot.fp2?.location,
      current_fp2_presence: snapshot.fp2?.presence,
    },
    suggestion:
      risk_level === 'high'
        ? 'Please check if everything is okay.'
        : 'Your loved one may still be moving. Monitor the situation.',
  });

  return anomalies;
}

/**
 * 判断4: MEDICATION 相关异常
 *
 * 三种类型：
 * 1. medication_cabinet_accessed - 药柜被打开
 * 2. medication_window_missed - 常规用药时间未打开药柜
 * 3. medication_access_without_followup - 打开药柜后无进食活动
 */
export function analyzeMedicationAnomalies(
  snapshot: SensorSnapshot,
  history: SensorHistory,
  typical_medication_hours: number[] = [8, 12, 18] // 预设用药时间
): AnomalyEvent[] {
  const anomalies: AnomalyEvent[] = [];

  const currentHour = getHourOfDay();
  const evidences: string[] = [];

  // 检查1: 药柜是否刚被打开
  if (snapshot.door_sensor && snapshot.door_sensor.medication_cabinet_open) {
    const timeSinceOpen = getSecondsSince(
      snapshot.door_sensor.medication_cabinet_open_time
    );

    if (timeSinceOpen && timeSinceOpen < 60) {
      // 刚打开
      anomalies.push({
        id: `med_accessed_${Date.now()}`,
        anomaly_type: 'medication_cabinet_accessed',
        timestamp: new Date().toISOString(),
        risk_level: 'normal',
        confidence_score: 0.95,
        evidence_sources: [
          'sensor:medication_cabinet_open',
          'context:just_accessed',
        ],
        involved_sensors: ['door'],
        detail: {
          opened_at: snapshot.door_sensor.medication_cabinet_open_time,
          seconds_since_open: timeSinceOpen,
        },
        suggestion:
          'Your loved one has accessed the medication cabinet.',
      });

      // 检查2: 打开药柜后是否有活动（跟进）
      const hasFollowupActivity =
        snapshot.fp2 &&
        snapshot.fp2.presence &&
        (snapshot.fp2.location === 'kitchen' ||
          snapshot.fp2.location === 'living_room');

      if (!hasFollowupActivity) {
        // 打开药柜但无进食活动
        anomalies.push({
          id: `med_no_followup_${Date.now()}`,
          anomaly_type: 'medication_access_without_followup',
          timestamp: new Date().toISOString(),
          risk_level: 'attention',
          confidence_score: 0.6, // 低置信度，因为只是单一信号
          evidence_sources: [
            'sensor:medication_cabinet_open',
            'sensor:no_eating_activity',
          ],
          involved_sensors: ['door', ...(snapshot.fp2 ? ['fp2'] : [])],
          detail: {
            accessed: true,
            has_eating_activity: hasFollowupActivity,
          },
          suggestion:
            'Medication accessed but no eating activity detected. Might want to check in.',
        });
      }
    }
  }

  // 检查3: 常规用药时间检查
  if (typical_medication_hours.includes(currentHour)) {
    const todayAccesses =
      snapshot.door_sensor?.medication_cabinet_access_count_today || 0;
    const expectedAccessesPerDay = typical_medication_hours.length;

    // 从历史数据获取今天到目前为止应该的打开次数
    const expectedAccessesAtThisHour = typical_medication_hours.filter(
      (h) => h <= currentHour
    ).length;

    if (todayAccesses < expectedAccessesAtThisHour) {
      // 用药时间窗口但未打开药柜
      anomalies.push({
        id: `med_missed_${Date.now()}`,
        anomaly_type: 'medication_window_missed',
        timestamp: new Date().toISOString(),
        risk_level: 'attention',
        confidence_score: 0.65, // 中等置信度，取决于其他上下文
        evidence_sources: [
          'context:medication_time',
          'sensor:cabinet_not_accessed',
        ],
        involved_sensors: ['door', 'clock'],
        detail: {
          current_hour: currentHour,
          is_medication_hour: true,
          expected_accesses_by_now: expectedAccessesAtThisHour,
          actual_accesses_today: todayAccesses,
          typical_times: typical_medication_hours,
        },
        suggestion:
          'It's time to take medication, but the cabinet hasn't been opened. Gentle reminder?',
      });
    }
  }

  return anomalies;
}

/**
 * 判断5: BATHROOM_RISK 提升
 *
 * 逻辑：
 * - 卫生间停留过久（20+分钟）
 * - 但之后没有进入安全区域（卧室/客厅）
 * - 且无 hallway passage 记录
 * → 风险提升
 */
export function analyzeBathroomRiskElevation(
  snapshot: SensorSnapshot,
  history: SensorHistory,
  extended_bathroom_minutes: number = 20
): AnomalyEvent[] {
  const anomalies: AnomalyEvent[] = [];

  // 前置条件：FP2 检测到在卫生间且停留过久
  if (!snapshot.fp2 || snapshot.fp2.location !== 'bathroom') {
    return anomalies;
  }

  const bathroomDurationMinutes = snapshot.fp2.duration_seconds
    ? Math.floor(snapshot.fp2.duration_seconds / 60)
    : 0;

  if (bathroomDurationMinutes < extended_bathroom_minutes) {
    return anomalies; // 停留时间未到阈值
  }

  const evidences: string[] = [
    'sensor:bathroom_long_stay',
    `duration:${bathroomDurationMinutes}_minutes`,
  ];

  // 检查是否有离开计划（走廊经过）
  const recentHallwayPassage =
    snapshot.hallway_sensor &&
    snapshot.hallway_sensor.passage_detected &&
    getSecondsSince(snapshot.hallway_sensor.passage_time) &&
    getSecondsSince(snapshot.hallway_sensor.passage_time)! < 120; // 最近2分钟内

  let baseConfidence = 0.6;
  let baseRiskLevel: 'attention' | 'high' = 'attention';

  // 如果有走廊经过，表示在移动，风险降低
  if (recentHallwayPassage) {
    evidences.push('sensor:movement_detected');
    baseConfidence = 0.4;
    baseRiskLevel = 'attention';
  } else {
    // 无走廊经过，可能卡住了
    evidences.push('sensor:no_movement_detected');
    baseConfidence = 0.75;
    baseRiskLevel = 'high';
  }

  // 检查是否在夜间（夜间风险更高）
  if (isNightTime()) {
    baseConfidence = Math.min(1, baseConfidence + 0.15);
    evidences.push('context:nighttime');
    if (baseRiskLevel === 'attention') baseRiskLevel = 'high';
  }

  // 单一信号不直接触发高风险，需要多信号确认
  if (recentHallwayPassage || isNightTime()) {
    // 至少两个条件
    anomalies.push({
      id: `bathroom_risk_${Date.now()}`,
      anomaly_type: 'bathroom_risk_elevated',
      timestamp: new Date().toISOString(),
      risk_level: baseRiskLevel,
      confidence_score: baseConfidence,
      evidence_sources: evidences,
      involved_sensors: [
        'fp2',
        ...(snapshot.hallway_sensor ? ['hallway'] : []),
      ],
      detail: {
        bathroom_duration_minutes: bathroomDurationMinutes,
        has_hallway_movement: recentHallwayPassage,
        is_nighttime: isNightTime(),
        threshold_minutes: extended_bathroom_minutes,
      },
      suggestion:
        baseRiskLevel === 'high'
          ? 'Extended bathroom stay without movement. A gentle check-in would be good.'
          : 'Your loved one has been in the bathroom for a while but seems to be moving. Monitor the situation.',
    });
  }

  return anomalies;
}

/**
 * 主入口：综合分析所有异常
 */
export function analyzeAllAnomalies(
  snapshot: SensorSnapshot,
  history: SensorHistory,
  config?: {
    fp2_inactivity_minutes?: number;
    night_bed_exit_minutes?: number;
    path_interrupted_seconds?: number;
    bathroom_extended_minutes?: number;
    medication_hours?: number[];
  }
): AnomalyEvent[] {
  const allAnomalies: AnomalyEvent[] = [];

  // 运行所有检测
  allAnomalies.push(
    ...analyzeNoActivityAnomalies(snapshot, history, config?.fp2_inactivity_minutes)
  );
  allAnomalies.push(
    ...analyzeNightBedExitNoReturn(snapshot, config?.night_bed_exit_minutes)
  );
  allAnomalies.push(
    ...analyzePathInterrupted(snapshot, config?.path_interrupted_seconds)
  );
  allAnomalies.push(
    ...analyzeMedicationAnomalies(snapshot, history, config?.medication_hours)
  );
  allAnomalies.push(
    ...analyzeBathroomRiskElevation(snapshot, history, config?.bathroom_extended_minutes)
  );

  return allAnomalies;
}
