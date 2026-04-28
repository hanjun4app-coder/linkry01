import { BehaviorText, DailySummaryText, RiskLevel } from './behavior';
import { StateContext, TrendMetrics, EvidenceSource } from './state';

/**
 * 整体状态
 * 页面顶部展示的综合状态
 */
export type OverallStatus = RiskLevel; // "normal" | "attention" | "high"

/**
 * 当前状态信息
 */
export interface CurrentState {
  label: string; // 例如："在卫生间"
  summary: string; // 例如："老人卫生间停留时间较长。"
}

/**
 * 页面状态视图模型
 * 这是页面组件需要的全部数据
 * 由 generateStatusViewModel 生成
 *
 * ✨ 状态驱动增强：
 * - 添加了 state_context（活动状态）
 * - 添加了 trend_metrics（趋势指标）
 * - 添加了 evidence_sources（证据来源）
 * - 添加了 show_state_notice（是否显示状态提示）
 */
export interface StatusViewModel {
  // 整体状态等级
  overall_status: OverallStatus;

  // 页面标题（大字体）
  headline: string;

  // 当前状态信息
  current_state: CurrentState;

  // 主异常提醒（优先展示最严重、最新的）
  primary_alert: BehaviorText | null;

  // 最近的行为记录文案（3-5 条）
  recent_behavior_texts: BehaviorText[];

  // 今日摘要（包括摘要、关键点、建议）
  daily_summary: DailySummaryText;

  // ✨ 新增：状态上下文（活动状态、趋势、异常天数）
  state_context: StateContext;

  // ✨ 新增：趋势指标（用于理解活动变化）
  trend_metrics: TrendMetrics;

  // ✨ 新增：证据来源（解释为什么得出这个判断）
  evidence_sources: EvidenceSource[];

  // ✨ 新增：是否显示状态提示（不同于主提醒）
  show_state_notice: boolean;

  // ✨ 新增：状态提示文案
  state_notice_text?: string;

  // ✨ NEW: Sensor fusion info (Phase 3 enhancement)
  sensor_fusion_info?: {
    enabled: boolean;
    sensor_count: number;
    last_analysis: string; // ISO timestamp
  };

  // 元数据
  metadata: {
    total_events: number;
    alert_count: number;
    last_update_time: string;
  };
}
