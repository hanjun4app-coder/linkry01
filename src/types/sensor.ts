/**
 * 传感器数据类型定义
 * 与实际硬件设备的数据结构对应
 *
 * 设备清单：
 * 1. FP2 - presence detection, location, duration tracking
 * 2. Sleep Tracker - bed presence, sleep state, bed exit/return time
 * 3. Door Sensor - entry door, medication cabinet
 * 4. Hallway PIR/Radar - passage detection, timing
 */

/**
 * FP2 传感器数据
 * 存在感检测器（Presence Detector）：检测人在家中的活动
 */
export interface FP2SensorData {
  /** 传感器ID */
  sensor_id: string;

  /** 是否检测到人的存在 */
  presence: boolean;

  /** 检测到的位置 */
  location?: 'bedroom' | 'living_room' | 'bathroom' | 'kitchen' | 'entrance' | 'hallway' | 'unknown';

  /** 在该位置的持续时间（秒） */
  duration_seconds?: number;

  /** 最后更新时间 */
  last_updated: string; // ISO timestamp

  /** 信号强度（0-100） */
  signal_strength?: number;

  /** 置信度（0-1） */
  confidence?: number;
}

/**
 * Sleep Tracker 传感器数据
 * 睡眠追踪器：监测床垫使用情况和睡眠状态
 */
export interface SleepTrackerData {
  /** 传感器ID */
  sensor_id: string;

  /** 是否有人在床上 */
  bed_presence: boolean;

  /** 睡眠状态 */
  sleep_state: 'sleeping' | 'awake' | 'light_sleep' | 'deep_sleep' | 'unknown';

  /** 离床时间戳（如果已离床） */
  bed_exit_time?: string; // ISO timestamp

  /** 回床时间戳（如果已回床） */
  bed_return_time?: string; // ISO timestamp

  /** 最后一次离床至今的持续时间（秒） */
  out_of_bed_duration_seconds?: number;

  /** 今天离床次数 */
  exit_count_today?: number;

  /** 最后更新时间 */
  last_updated: string; // ISO timestamp

  /** 睡眠质量评分（0-100，可选） */
  sleep_quality?: number;
}

/**
 * Door Sensor 传感器数据
 * 门传感器：监测出入和药柜使用
 */
export interface DoorSensorData {
  /** 传感器ID */
  sensor_id: string;

  /** 入户门状态 */
  entry_door_open: boolean;

  /** 入户门最后开启时间 */
  entry_door_open_time?: string; // ISO timestamp

  /** 入户门最后关闭时间 */
  entry_door_close_time?: string; // ISO timestamp

  /** 药柜是否打开 */
  medication_cabinet_open: boolean;

  /** 药柜最后打开时间 */
  medication_cabinet_open_time?: string; // ISO timestamp

  /** 药柜最后关闭时间 */
  medication_cabinet_close_time?: string; // ISO timestamp

  /** 今天药柜打开次数 */
  medication_cabinet_access_count_today?: number;

  /** 最后更新时间 */
  last_updated: string; // ISO timestamp
}

/**
 * Hallway PIR/Radar 传感器数据
 * 走廊运动传感器：检测走廊经过和移动
 */
export interface HallwaySensorData {
  /** 传感器ID */
  sensor_id: string;

  /** 是否检测到走廊经过 */
  passage_detected: boolean;

  /** 最后一次经过时间 */
  passage_time?: string; // ISO timestamp

  /** 经过方向（可选） */
  passage_direction?: 'towards_bedroom' | 'towards_living_room' | 'towards_bathroom' | 'unknown';

  /** 最近5分钟内的经过次数 */
  passage_count_5min?: number;

  /** 最近15分钟内的经过次数 */
  passage_count_15min?: number;

  /** 信号强度（0-100） */
  signal_strength?: number;

  /** 最后更新时间 */
  last_updated: string; // ISO timestamp
}

/**
 * 完整的传感器状态快照
 * 用于多传感器融合分析
 */
export interface SensorSnapshot {
  /** 时间戳 */
  timestamp: string; // ISO timestamp

  /** FP2 数据（可选，如果没有则认为无活动） */
  fp2?: FP2SensorData;

  /** 睡眠追踪器数据 */
  sleep_tracker?: SleepTrackerData;

  /** 门传感器数据 */
  door_sensor?: DoorSensorData;

  /** 走廊传感器数据 */
  hallway_sensor?: HallwaySensorData;

  /** 数据完整性标记 */
  data_completeness: {
    fp2_available: boolean;
    sleep_tracker_available: boolean;
    door_sensor_available: boolean;
    hallway_sensor_available: boolean;
  };
}

/**
 * 传感器历史数据
 * 用于趋势分析和多时间窗口判断
 */
export interface SensorHistory {
  /** 最近1小时的快照列表 */
  last_hour: SensorSnapshot[];

  /** 最近24小时的汇总统计 */
  last_24h_summary: {
    total_bed_exit_count: number;
    total_bed_exit_duration_minutes: number;
    total_hallway_passages: number;
    total_medication_cabinet_accesses: number;
    entry_door_open_count: number;
    average_fp2_presence_percentage: number;
  };

  /** 最近7天的模式 */
  last_7days_pattern: {
    typical_sleep_start_hour: number;
    typical_sleep_end_hour: number;
    typical_activity_hours: number[];
    typical_bed_exit_count: number;
    typical_medication_time_hours: number[];
  };
}

/**
 * 异常事件基础类型
 * 由传感器融合引擎生成
 */
export interface AnomalyEvent {
  /** 事件ID */
  id: string;

  /** 事件类型 */
  anomaly_type:
    | 'no_activity_confirmed'
    | 'night_bed_exit_no_return'
    | 'path_interrupted'
    | 'medication_cabinet_accessed'
    | 'medication_window_missed'
    | 'medication_access_without_followup'
    | 'bathroom_risk_elevated'
    | 'unknown_location';

  /** 发生时间 */
  timestamp: string; // ISO timestamp

  /** 风险等级 */
  risk_level: 'normal' | 'attention' | 'high';

  /** 置信度评分 (0-1) */
  confidence_score: number;

  /** 证据来源 */
  evidence_sources: string[];

  /** 涉及的传感器 */
  involved_sensors: string[];

  /** 事件详情 */
  detail: {
    [key: string]: any;
  };

  /** 建议操作 */
  suggestion?: string;
}
