import {
  BehaviorEvent,
  DailyBehaviorSummaryInput,
} from '@/types/behavior';
import {
  ActivityState,
  StateContext,
  TrendMetrics,
  EvidenceSource,
} from '@/types/state';

/**
 * 状态引擎
 * 将事件流转换为状态理解
 *
 * 核心逻辑：
 * - 分析多天数据的活动趋势
 * - 识别活动状态变化
 * - 生成可解释的证据
 */

/**
 * 生成状态上下文
 * 从行为事件和每日摘要推导当前状态
 *
 * @param events - 行为事件数组
 * @param dailySummary - 今日摘要
 * @param historicalData - 历史数据（可选，用于多天分析）
 * @returns 状态上下文
 */
export function generateStateContext(
  events: BehaviorEvent[],
  dailySummary: DailyBehaviorSummaryInput,
  historicalData?: {
    yesterday_total_active_minutes?: number;
    day_before_yesterday_total_active_minutes?: number;
    consecutive_anomaly_days?: number;
  }
): StateContext {
  // 1. 计算趋势指标
  const trendMetrics = calculateTrendMetrics(
    dailySummary,
    historicalData
  );

  // 2. 计算活动下降比例
  const activity_drop_ratio = calculateActivityDropRatio(trendMetrics);

  // 3. 计算连续异常天数
  const consecutive_anomaly_days =
    historicalData?.consecutive_anomaly_days ?? 0;

  // 4. 确定活动状态
  const current_state = determineActivityState(
    dailySummary.highest_risk,
    consecutive_anomaly_days,
    activity_drop_ratio,
    trendMetrics.trend
  );

  // 5. 判断是否需要主动提醒
  const requires_proactive_notice =
    current_state === 'persistent_low_activity' ||
    current_state === 'recovery';

  // 6. 收集证据
  const evidence = collectEvidence(
    events,
    dailySummary,
    current_state,
    trendMetrics,
    activity_drop_ratio
  );

  return {
    current_state,
    consecutive_anomaly_days,
    activity_drop_ratio,
    activity_trend: trendMetrics.trend,
    requires_proactive_notice,
    evidence,
  };
}

/**
 * 计算趋势指标
 * 分析最近活动 vs 之前活动的对比
 */
function calculateTrendMetrics(
  dailySummary: DailyBehaviorSummaryInput,
  historicalData?: {
    yesterday_total_active_minutes?: number;
    day_before_yesterday_total_active_minutes?: number;
  }
): TrendMetrics {
  const today_active = dailySummary.total_active_minutes ?? 0;
  const yesterday_active = historicalData?.yesterday_total_active_minutes ?? today_active;
  const day_before_active = historicalData?.day_before_yesterday_total_active_minutes ?? today_active;

  // 计算平均值
  const recent_3day_avg = (today_active + yesterday_active + day_before_active) / 3;
  const previous_3day_avg = (yesterday_active + day_before_active) / 2;

  // 计算下降比例
  const drop_ratio = previous_3day_avg > 0
    ? Math.max(0, (previous_3day_avg - recent_3day_avg) / previous_3day_avg)
    : 0;

  // 判断趋势
  let trend: 'stable' | 'declining' | 'recovering' = 'stable';
  if (drop_ratio > 0.15) {
    // 下降超过 15% 认为是下降趋势
    trend = 'declining';
  } else if (drop_ratio < -0.15) {
    // 增加超过 15% 认为是恢复趋势
    trend = 'recovering';
  }

  return {
    recent_3day_avg,
    previous_3day_avg,
    drop_ratio: Math.round(drop_ratio * 100) / 100,
    trend,
  };
}

/**
 * 计算活动下降比例
 */
function calculateActivityDropRatio(trendMetrics: TrendMetrics): number {
  // 如果是恢复趋势，下降比例为 0
  if (trendMetrics.trend === 'recovering') {
    return 0;
  }
  // 否则返回实际下降比例
  return Math.max(0, trendMetrics.drop_ratio);
}

/**
 * 确定活动状态
 *
 * 规则：
 * 1. 如果异常连续 ≥ 4 天 → persistent_low_activity
 * 2. 如果异常连续 1-3 天 → reduced_activity
 * 3. 如果活动开始恢复 → recovery
 * 4. 否则 → normal
 */
function determineActivityState(
  risk_level: string,
  consecutive_anomaly_days: number,
  activity_drop_ratio: number,
  trend: 'stable' | 'declining' | 'recovering'
): ActivityState {
  // 如果在恢复趋势
  if (trend === 'recovering') {
    return 'recovery';
  }

  // 如果有持续异常
  if (risk_level === 'attention' || risk_level === 'high') {
    if (consecutive_anomaly_days >= 4) {
      return 'persistent_low_activity';
    } else if (consecutive_anomaly_days >= 1) {
      return 'reduced_activity';
    }
  }

  // 如果活动下降比例很大
  if (activity_drop_ratio >= 0.25 && trend === 'declining') {
    if (consecutive_anomaly_days >= 4) {
      return 'persistent_low_activity';
    } else if (consecutive_anomaly_days >= 1) {
      return 'reduced_activity';
    }
  }

  return 'normal';
}

/**
 * 收集证据
 * 用于解释为什么得出这个状态判断
 */
function collectEvidence(
  events: BehaviorEvent[],
  dailySummary: DailyBehaviorSummaryInput,
  current_state: ActivityState,
  trendMetrics: TrendMetrics,
  activity_drop_ratio: number
): EvidenceSource[] {
  const evidence: EvidenceSource[] = [];

  // 根据风险等级添加证据
  const riskRelatedEvents = events.filter(
    (e) => e.risk_level === 'attention' || e.risk_level === 'high'
  );

  // 安全规则证据
  if (riskRelatedEvents.some((e) => e.event_type === 'bathroom_long_stay')) {
    evidence.push('safety_rule:bathroom_duration');
  }
  if (riskRelatedEvents.some((e) => e.event_type === 'night_wake')) {
    evidence.push('safety_rule:night_activity');
  }
  if (riskRelatedEvents.some((e) => e.event_type === 'no_activity')) {
    evidence.push('safety_rule:long_inactivity');
  }

  // 时间上下文证据
  const hasNightEvents = events.some(
    (e) => e.start_time && isNightTime(e.start_time)
  );
  if (hasNightEvents) {
    evidence.push('time_context:night');
  }

  // 模式证据
  if (dailySummary.total_active_minutes < 120) {
    evidence.push('pattern:low_activity');
  }

  if (trendMetrics.trend === 'declining') {
    evidence.push('pattern:activity_decline');
  }

  if (trendMetrics.trend === 'recovering') {
    evidence.push('pattern:activity_recovery');
  }

  // 基线对比证据
  if (activity_drop_ratio > 0.2) {
    evidence.push('baseline:deviation');
  } else {
    evidence.push('baseline:normal');
  }

  // 状态证据
  if (current_state === 'persistent_low_activity') {
    evidence.push('state:persistent_anomaly');
  }

  if (current_state === 'recovery') {
    evidence.push('state:recovery');
  }

  // 多信号融合证据
  if (evidence.length > 3) {
    evidence.push('fusion:multi_signal');
  }

  return [...new Set(evidence)]; // 去重
}

/**
 * 判断是否是夜间时间
 */
function isNightTime(timeStr: string): boolean {
  const hour = new Date(timeStr).getHours();
  // 晚上 21:00 到早上 6:00
  return hour >= 21 || hour < 6;
}

/**
 * 判断是否需要更新状态（用于多天场景）
 */
export function shouldUpdateStateFlags(
  current_state: ActivityState,
  daily_risk: string
): boolean {
  // 如果当前是正常状态，但今天有异常 → 开始计数
  if (current_state === 'normal' && (daily_risk === 'attention' || daily_risk === 'high')) {
    return true;
  }

  // 如果当前在异常状态，但今天恢复正常 → 检查是否需要恢复
  if (
    (current_state === 'reduced_activity' || current_state === 'persistent_low_activity') &&
    daily_risk === 'normal'
  ) {
    return true;
  }

  return false;
}

/**
 * 获取状态转移的建议文案（英文）
 */
export function getStateNoticeText(state: ActivityState, language: 'en' | 'zh' = 'en'): string {
  const texts = {
    en: {
      normal: '',
      reduced_activity: 'Activity has been lower than usual for a few days. Keep an eye on things.',
      persistent_low_activity: 'Activity has been lower than usual for several days. Consider a check-in.',
      recovery: 'Activity levels are recovering. Good sign.',
    },
    zh: {
      normal: '',
      reduced_activity: '最近几天活动量偏低，建议持续关注。',
      persistent_low_activity: '活动量已连续多天低于平常，建议电话确认。',
      recovery: '活动量开始恢复，这是好信号。',
    },
  };

  return texts[language][state] || '';
}
