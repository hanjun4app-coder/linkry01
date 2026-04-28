/**
 * 状态驱动系统 - 类型定义
 * 从事件驱动升级为状态驱动
 *
 * ⚠️ 重要区分：
 * ActivityState 表示行为状态/趋势状态（normal, reduced_activity, persistent_low_activity, recovery）
 * 不等同于风险等级（normal, attention, high）
 *
 * 例如：
 * - persistent_low_activity 代表持续低活动状态（≥4天异常）
 *   但不必然等于 high risk
 *   可能只触发"状态提示"而不是"风险警报"
 *
 * - 卫生间停留过久可能是 high risk
 *   但活动状态可能仍是 normal（只是单次异常）
 *
 * 两个维度是独立的，用于不同的判断逻辑。
 */

/**
 * 活动状态枚举
 * 表示老人活动的趋势和模式状态
 */
export type ActivityState =
  | 'normal' // 正常活动模式
  | 'reduced_activity' // 活动减少（异常连续 1-3 天）
  | 'persistent_low_activity' // 持续低活动（异常连续 ≥4 天）
  | 'recovery'; // 恢复中（活动开始回升）

/**
 * 状态上下文
 * 包含当前活动状态和相关指标
 */
export interface StateContext {
  /** 当前活动状态 */
  current_state: ActivityState;

  /** 连续异常天数（0-N） */
  consecutive_anomaly_days: number;

  /** 活动下降比例（0-1，例如 0.3 = 活动减少30%）*/
  activity_drop_ratio: number;

  /** 活动趋势方向 */
  activity_trend: 'stable' | 'declining' | 'recovering';

  /** 是否需要主动提醒（不同于被动报警） */
  requires_proactive_notice: boolean;

  /** 状态变化的证据来源 */
  evidence: EvidenceSource[];
}

/**
 * 趋势指标
 */
export interface TrendMetrics {
  /** 最近 3 天平均活动时长（分钟） */
  recent_3day_avg: number;

  /** 之前 3 天平均活动时长（分钟） */
  previous_3day_avg: number;

  /** 活动下降比例（0-1，例如 0.3 = 下降 30%） */
  drop_ratio: number;

  /** 趋势方向 */
  trend: 'stable' | 'declining' | 'recovering';
}

/**
 * 证据来源标签
 * 用于解释系统为什么做出特定判断
 *
 * 分类：
 * - safety_rule:* 来自安全规则
 * - time_context:* 来自时间上下文
 * - pattern:* 来自行为模式
 * - baseline:* 来自与基线对比
 * - state:* 来自状态识别
 * - fusion:* 来自多信号融合
 */
export type EvidenceSource =
  // 安全规则
  | 'safety_rule:bathroom_duration' // 卫生间停留时间过长
  | 'safety_rule:night_activity' // 夜间异常活动
  | 'safety_rule:long_inactivity' // 长时间无活动
  // 时间上下文
  | 'time_context:night' // 夜间时段
  | 'time_context:early_morning' // 凌晨时段
  | 'time_context:unusual_time' // 非常规时段
  // 行为模式
  | 'pattern:low_activity' // 低活动量模式
  | 'pattern:activity_decline' // 活动下降趋势
  | 'pattern:activity_recovery' // 活动恢复趋势
  | 'pattern:irregular_schedule' // 不规律作息
  // 与基线对比
  | 'baseline:deviation' // 与个人基线偏离
  | 'baseline:normal' // 符合个人基线
  // 状态识别
  | 'state:persistent_anomaly' // 持续异常状态
  | 'state:recovery' // 恢复状态
  // 多信号融合 - 用于表示多个信号共同触发
  | 'fusion:multi_signal'; // 多个信号共同判断（例如：卫生间停留 + 低活动 + 夜间时间）

/**
 * 扩展的状态视图模型
 * 在原有 StatusViewModel 基础上补充状态信息
 */
export interface StateAwareViewModel {
  /** 状态上下文 - 活动状态和趋势 */
  state_context: StateContext;

  /** 趋势指标 - 具体的数值指标 */
  trend_metrics: TrendMetrics;

  /** 证据源列表 - 解释为什么做出这个判断 */
  evidence_sources: EvidenceSource[];

  /** 是否应该显示主提醒（单次异常警报） */
  show_primary_alert: boolean;

  /** 是否应该显示状态提示（多天异常趋势） */
  show_state_notice: boolean;

  /** 状态提示文案（如果 show_state_notice = true） */
  state_notice_text?: string;
}
