/**
 * 默认行为规则系统
 * 消费级产品的标准阈值
 * 所有事件判断优先使用这些规则
 */

export const DEFAULT_RULES = {
  /**
   * 卫生间停留时长（分钟）
   * 超过此时长认为异常
   */
  bathroom_duration_threshold: {
    attention: 20, // 20分钟 → attention 级别
    high: 35, // 35分钟 → high 风险
  },

  /**
   * 无活动持续时长（分钟）
   * 超过此时长认为异常
   */
  no_activity_threshold: {
    attention: 60, // 1小时 → attention 级别
    high: 120, // 2小时 → high 风险
  },

  /**
   * 夜间离床时长（分钟）
   * 夜间（22:00-07:00）离开卧室超过此时长认为异常
   */
  night_bed_exit_threshold: {
    attention: 10, // 10分钟 → attention
    high: 30, // 30分钟 → high 风险
  },

  /**
   * 连续在床停留时长（分钟）
   * 超过此时长且无活动认为异常
   */
  long_bed_stay_threshold: {
    attention: 180, // 3小时 → attention
    high: 300, // 5小时 → high 风险
  },

  /**
   * 检测中断超时（秒）
   * 传感器信号丢失超过此时长认为异常
   */
  path_interrupted_threshold: {
    attention: 90, // 90秒 → attention
    high: 180, // 3分钟 → high 风险
  },

  /**
   * 夜间活动频率阈值
   * 22:00-07:00 期间频繁离床认为异常
   */
  night_wake_frequency: {
    attention: 3, // 3次以上 → attention
    high: 5, // 5次以上 → high 风险
  },
} as const;

/**
 * Alert 去重和优化参数
 */
export const ALERT_DEDUP_RULES = {
  /**
   * Cooldown 时长（分钟）
   * 同一事件/地点在此时间内不重复推送
   */
  cooldown_minutes: 30,

  /**
   * Debounce 时长（秒）
   * 异常必须持续此时长才触发 alert
   */
  debounce_seconds: 60,

  /**
   * 多信号确认阈值
   * 非 high risk 的 alert 必须满足至少此数量的条件
   */
  multi_signal_min_count: 2,
} as const;

/**
 * Quiet Mode（夜间策略）
 */
export const QUIET_MODE_CONFIG = {
  /**
   * Quiet Mode 开始时间（小时）
   */
  start_hour: 22, // 22:00

  /**
   * Quiet Mode 结束时间（小时）
   */
  end_hour: 7, // 07:00

  /**
   * Quiet Mode 下仍需推送的最低风险等级
   */
  minimum_risk_to_notify: 'high' as const,
} as const;

/**
 * 置信度评分配置
 */
export const CONFIDENCE_SCORE_CONFIG = {
  /**
   * 单一信号置信度范围
   */
  single_signal: {
    min: 0.4,
    max: 0.6,
  },

  /**
   * 双信号置信度范围
   */
  dual_signal: {
    min: 0.6,
    max: 0.8,
  },

  /**
   * 多信号 + 时间上下文置信度范围
   */
  multi_signal_with_context: {
    min: 0.8,
    max: 0.95,
  },

  /**
   * High risk 事件的置信度加成
   * 当有明确的高风险指标时，置信度加成
   */
  high_risk_boost: 0.15,
} as const;

/**
 * 行为模式学习阈值
 * 系统需要收集多少天的数据才能建立个人基线
 */
export const BASELINE_LEARNING = {
  /**
   * 学习期（天）
   * 前N天的数据用于建立个人活动基线
   */
  learning_period_days: 7,

  /**
   * 最少数据点
   * 至少需要此数量的数据点才能有效计算基线
   */
  minimum_data_points: 5,

  /**
   * 基线偏离阈值
   * 偏离基线超过此比例认为异常
   */
  deviation_threshold: 0.25, // 25% 偏离
} as const;

/**
 * 辅助函数：判断当前是否在 Quiet Mode
 */
export function isInQuietMode(hour: number = new Date().getHours()): boolean {
  const { start_hour, end_hour } = QUIET_MODE_CONFIG;

  if (start_hour > end_hour) {
    // 跨越午夜的情况 (例如 22:00-07:00)
    return hour >= start_hour || hour < end_hour;
  } else {
    // 正常情况
    return hour >= start_hour && hour < end_hour;
  }
}

/**
 * 辅助函数：根据信号数量获取置信度范围
 */
export function getConfidenceScoreRange(
  signalCount: number,
  hasTimeContext: boolean = false
): { min: number; max: number } {
  if (signalCount >= 3 && hasTimeContext) {
    return CONFIDENCE_SCORE_CONFIG.multi_signal_with_context;
  } else if (signalCount >= 2) {
    return CONFIDENCE_SCORE_CONFIG.dual_signal;
  } else {
    return CONFIDENCE_SCORE_CONFIG.single_signal;
  }
}

/**
 * 辅助函数：计算时间范围
 * 用于判断活动是否在正常时间内
 */
export const NORMAL_ACTIVITY_HOURS = {
  min: 7, // 07:00
  max: 23, // 23:00
};

/**
 * 辅助函数：判断时间是否在正常活动时间
 */
export function isNormalActivityTime(hour: number = new Date().getHours()): boolean {
  return hour >= NORMAL_ACTIVITY_HOURS.min && hour < NORMAL_ACTIVITY_HOURS.max;
}
