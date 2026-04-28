/**
 * 传感器配置
 * 设备参数、阈值、检测策略
 */

export const SENSOR_CONFIG = {
  /**
   * FP2 传感器配置
   */
  fp2: {
    /** FP2 被视为"无活动"的持续时间（分钟） */
    inactivity_threshold_minutes: 120, // 2小时

    /** FP2 位置检测的置信度阈值 */
    location_confidence_threshold: 0.7,

    /** 传感器数据更新超时（秒） */
    data_timeout_seconds: 300, // 5分钟未更新认为故障
  },

  /**
   * Sleep Tracker 配置
   */
  sleep_tracker: {
    /** 夜间离床超过此时长未回床，触发报警（分钟） */
    night_bed_exit_threshold_minutes: 10,

    /** 夜间定义（开始小时） */
    night_start_hour: 22,

    /** 夜间定义（结束小时） */
    night_end_hour: 7,

    /** 连续卧床超过此时长且无活动，触发报警（分钟） */
    prolonged_bed_stay_minutes: 180, // 3小时

    /** 今天离床次数异常阈值 */
    abnormal_exit_count_per_day: 10,
  },

  /**
   * Door Sensor 配置
   */
  door_sensor: {
    /** 入户门打开的持续时间（秒） */
    entry_door_open_timeout: 300, // 5分钟

    /** 药柜打开的持续时间（秒） */
    medication_cabinet_open_timeout: 120, // 2分钟

    /** 预设用药时间（小时数组） */
    medication_typical_hours: [8, 12, 18], // 早8点、中午12点、晚6点

    /** 打开药柜后，应该有进食活动的时间窗口（秒） */
    medication_followup_window_seconds: 600, // 10分钟
  },

  /**
   * Hallway Sensor 配置
   */
  hallway: {
    /** 走廊经过后，应该在此时间内到达目的地（秒） */
    expected_transit_time_seconds: 90,

    /** 走廊经过的"最近"定义（秒） */
    recent_passage_window_seconds: 300, // 5分钟

    /** 短时间内过多的走廊经过认为异常 */
    excessive_passage_count_5min: 10,
  },

  /**
   * 异常检测策略
   */
  anomaly_detection: {
    /** 卫生间停留多久认为过久（分钟） */
    bathroom_long_stay_minutes: 20,

    /** 卫生间停留过久时，多久内未离开则提升风险（分钟） */
    bathroom_exit_timeout_minutes: 30,

    /** 多信号确认所需的最少信号数 */
    multi_signal_min_count: 2,

    /** 单一信号的默认置信度范围 */
    single_signal_confidence_range: [0.4, 0.6],

    /** 双信号的默认置信度范围 */
    dual_signal_confidence_range: [0.6, 0.8],

    /** 多信号+时间上下文的置信度范围 */
    multi_signal_confidence_range: [0.8, 0.95],
  },

  /**
   * 数据融合策略
   */
  fusion: {
    /** 等待所有传感器数据的超时时间（秒） */
    fusion_data_timeout_seconds: 10,

    /** 数据融合的时间窗口（秒） */
    fusion_window_seconds: 60,

    /** 是否进行自适应阈值学习 */
    adaptive_learning_enabled: true,

    /** 学习周期（天） */
    learning_period_days: 7,
  },

  /**
   * 数据完整性要求
   */
  data_completeness: {
    /** 不同场景下需要的最小传感器数量 */
    no_activity_detection_min_sensors: 2, // 需要至少2个传感器
    medication_detection_min_sensors: 1, // 药柜检测只需1个
    bathroom_detection_min_sensors: 1, // 卫生间检测只需1个
    night_monitoring_min_sensors: 2, // 夜间监测需要至少2个
  },
} as const;

/**
 * 风险等级映射
 * 根据置信度和信号数量确定最终风险等级
 */
export function determineRiskLevel(
  confidence: number,
  signalCount: number,
  anomalyType: string
): 'normal' | 'attention' | 'high' {
  // High risk 异常：high confidence 或 多信号
  if (
    anomalyType.includes('bed_exit_no_return') ||
    anomalyType.includes('no_activity')
  ) {
    if (confidence >= 0.75 || signalCount >= 3) {
      return 'high';
    }
    if (confidence >= 0.6 || signalCount >= 2) {
      return 'attention';
    }
  }

  // Medication 异常：通常是 attention
  if (anomalyType.includes('medication')) {
    if (confidence >= 0.8) {
      return 'attention';
    }
    return 'normal';
  }

  // Path interrupted：多信号才提升
  if (anomalyType.includes('path')) {
    if (confidence >= 0.75 && signalCount >= 2) {
      return 'high';
    }
    if (confidence >= 0.6) {
      return 'attention';
    }
  }

  // Bathroom risk：多信号才提升
  if (anomalyType.includes('bathroom')) {
    if (confidence >= 0.8 && signalCount >= 2) {
      return 'high';
    }
    if (confidence >= 0.6 || signalCount >= 2) {
      return 'attention';
    }
  }

  return 'normal';
}

/**
 * 检查数据完整性
 * 某些检测需要特定的传感器组合
 */
export function checkDataCompleteness(
  availableSensors: string[],
  checkType: string
): {
  is_complete: boolean;
  missing_sensors: string[];
} {
  const requirements = SENSOR_CONFIG.data_completeness;

  let required: string[] = [];

  if (checkType === 'no_activity') {
    required = ['fp2', 'door_sensor', 'sleep_tracker', 'hallway'];
  } else if (checkType === 'medication') {
    required = ['door_sensor'];
  } else if (checkType === 'bathroom') {
    required = ['fp2'];
  } else if (checkType === 'night_monitoring') {
    required = ['sleep_tracker', 'fp2'];
  }

  const missing = required.filter((s) => !availableSensors.includes(s));

  return {
    is_complete: missing.length === 0,
    missing_sensors: missing,
  };
}

/**
 * 获取传感器健康状态
 */
export interface SensorHealth {
  sensor_name: string;
  is_healthy: boolean;
  last_data_age_seconds: number;
  signal_strength?: number;
  status: 'healthy' | 'stale' | 'offline' | 'unknown';
}

export function checkSensorHealth(
  lastUpdateTimestamp: string | undefined,
  signalStrength?: number
): SensorHealth['status'] {
  if (!lastUpdateTimestamp) {
    return 'unknown';
  }

  const ageSeconds = Math.floor(
    (Date.now() - new Date(lastUpdateTimestamp).getTime()) / 1000
  );

  if (ageSeconds > SENSOR_CONFIG.fp2.data_timeout_seconds) {
    return 'offline';
  }

  if (ageSeconds > 60) {
    return 'stale';
  }

  if (signalStrength && signalStrength < 30) {
    return 'stale';
  }

  return 'healthy';
}
