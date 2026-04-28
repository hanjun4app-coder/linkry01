export type RiskLevel = 'normal' | 'attention' | 'high';

export type EventType =
  | 'wake_up'
  | 'living_activity'
  | 'bathroom_use'
  | 'bathroom_long_stay'
  | 'no_activity'
  | 'night_wake'
  | 'nap'
  | 'resting'
  | 'left_home'
  | 'returned_home'
  // ✨ NEW: Sensor fusion event types (Phase 3)
  | 'path_interrupted'
  | 'medication_cabinet_accessed'
  | 'medication_missed'
  | 'medication_without_followup';

export type Zone = 'bedroom' | 'living_room' | 'bathroom' | 'entrance' | 'unknown';

/**
 * 底层行为事件数据结构
 * 由传感器/系统识别生成
 *
 * ✨ ENHANCED: Supports sensor fusion output (Phase 3)
 */
export interface BehaviorEvent {
  id?: string;
  event_id?: string; // ✨ NEW: For sensor fusion compatibility
  home_id?: string;
  event_type: EventType;
  zone?: Zone;
  location?: string; // ✨ NEW: Sensor fusion location
  timestamp?: string; // ✨ NEW: Sensor fusion timestamp
  start_time?: string;
  end_time?: string;
  duration_minutes?: number;
  risk_level: RiskLevel;
  metadata?: Record<string, any>;
  source?: string; // ✨ NEW: Event source ('sensor_fusion', 'behavior_engine', etc.)
  detail?: Record<string, any>; // ✨ NEW: Event details
  evidence_sources?: string[]; // ✨ NEW: Evidence sources for transparency

  /**
   * 置信度评分 (0-1)
   * 表示系统对该事件判断的信心程度
   * - 0.4-0.6: 单一信号
   * - 0.6-0.8: 双信号
   * - 0.8-0.95: 多信号 + 时间上下文
   */
  confidence_score?: number;
}

/**
 * 给家属展示的文案
 * 由 generateBehaviorText 函数生成
 */
export interface BehaviorText {
  title: string;
  summary: string;
  detail: string;
  suggestion: string;
  display_level: RiskLevel;
  event_id?: string; // 源事件的 ID（用于提交反馈时识别）
  evidence_sources?: string[]; // 事件的证据来源标签（用于解释判断依据）
  confidence_score?: number; // 置信度评分 (0-1)，用于向用户表达系统确定性
}

/**
 * 今日行为摘要输入数据
 */
export interface DailyBehaviorSummaryInput {
  wake_time?: string;
  total_active_minutes: number;
  bathroom_count: number;
  longest_bathroom_minutes?: number;
  night_wake_count: number;
  alerts_count: number;
  highest_risk: RiskLevel;
}

/**
 * 今日摘要展示文案
 * 由 generateDailySummaryText 函数生成
 */
export interface DailySummaryText {
  headline: string;
  summary: string;
  key_points: string[];
  suggestion: string;
}
