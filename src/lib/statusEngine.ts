import {
  BehaviorEvent,
  DailyBehaviorSummaryInput,
  RiskLevel,
} from '@/types/behavior';
import { StatusViewModel } from '@/types/status';
import {
  generateBehaviorText,
  generateDailySummaryText,
  getCurrentStateLabel,
  isAlertEvent,
} from './behaviorText';
import {
  generateStateContext,
  getStateNoticeText,
} from './stateEngine';

/**
 * 生成页面状态视图模型
 * 这是页面组件唯一需要的数据源
 *
 * ✨ 状态驱动增强：
 * - 集成 stateEngine 生成活动状态和趋势
 * - 根据状态决定是否显示主提醒或状态提示
 * - 收集证据来源用于解释判断
 *
 * @param events - 行为事件数组
 * @param dailySummary - 今日摘要数据
 * @param language - 语言（默认英文）
 * @returns 页面需要展示的所有数据
 */
export function generateStatusViewModel(
  events: BehaviorEvent[],
  dailySummary: DailyBehaviorSummaryInput,
  language: 'en' | 'zh' = 'en'
): StatusViewModel {
  // 1. 获取整体状态等级
  const overall_status = dailySummary.highest_risk;

  // 2. 生成今日摘要文案
  const daily_summary = generateDailySummaryText(dailySummary, language);

  // 3. 获取当前状态（基于最新事件）
  const latestEvent = events.length > 0 ? events[events.length - 1] : null;
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
  const state_context = generateStateContext(events, dailySummary);

  // ✨ 5. 计算是否显示提醒和提示（新增）
  const { primary_alert, show_state_notice, state_notice_text } =
    determineAlertAndNoticeDisplay(
      events,
      state_context,
      language
    );

  // 6. 获取最近的行为记录（3-5 条）
  const recent_behavior_texts = getRecentBehaviorTexts(events, 4, language);

  // 7. 构建视图模型
  const viewModel: StatusViewModel = {
    overall_status,
    headline: daily_summary.headline,
    current_state,
    primary_alert,
    recent_behavior_texts,
    daily_summary,
    // ✨ 新增状态信息
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
    metadata: {
      total_events: events.length,
      alert_count: dailySummary.alerts_count,
      last_update_time: new Date().toLocaleString(
        language === 'en' ? 'en-US' : 'zh-CN'
      ),
    },
  };

  return viewModel;
}

/**
 * 确定是否显示主提醒和状态提示
 * 核心规则：
 * - persistent_low_activity: 不显示主提醒，显示状态提示
 * - 其他异常状态：显示主提醒
 */
function determineAlertAndNoticeDisplay(
  events: BehaviorEvent[],
  state_context: any,
  language: 'en' | 'zh' = 'en'
) {
  // ✨ 修复规则：ActivityState 和 risk_level 分层
  // 获取主提醒（基于 risk_level）
  const primary_alert = getPrimaryAlert(events, language);

  // 检查是否有新的 high risk 事件
  const hasHighRiskAlert =
    primary_alert !== null &&
    events.some((e) => isAlertEvent(e) && e.risk_level === 'high');

  // 规则 1：有新的 high risk 事件 → 必须显示主提醒（无论状态如何）
  if (hasHighRiskAlert) {
    return {
      primary_alert,
      show_state_notice:
        state_context.current_state === 'persistent_low_activity' ||
        state_context.current_state === 'recovery',
      state_notice_text:
        state_context.current_state === 'persistent_low_activity'
          ? getStateNoticeText('persistent_low_activity', language)
          : state_context.current_state === 'recovery'
            ? getStateNoticeText('recovery', language)
            : undefined,
    };
  }

  // 规则 2：持续低活动但无 high risk → 不显示主提醒，显示状态提示
  if (state_context.current_state === 'persistent_low_activity') {
    return {
      primary_alert: null,
      show_state_notice: true,
      state_notice_text: getStateNoticeText(
        'persistent_low_activity',
        language
      ),
    };
  }

  // 规则 3：恢复状态 → 显示主提醒和恢复提示
  if (state_context.current_state === 'recovery') {
    return {
      primary_alert,
      show_state_notice: true,
      state_notice_text: getStateNoticeText('recovery', language),
    };
  }

  // 规则 4：其他情况 → 正常显示主提醒
  return {
    primary_alert,
    show_state_notice: false,
    state_notice_text: undefined,
  };
}

/**
 * 获取主要异常提醒
 * 规则：
 * 1. 只考虑 alert 事件（risk_level 为 attention 或 high）
 * 2. 优先选择 high，其次选择 attention
 * 3. 同级别中选择时间最近的
 *
 * @param events - 行为事件数组
 * @param language - 语言
 * @returns 主异常提醒或 null
 */
function getPrimaryAlert(
  events: BehaviorEvent[],
  language: 'en' | 'zh' = 'en'
) {
  // 过滤出所有 alert 事件
  const alertEvents = events.filter((event) => isAlertEvent(event));

  if (alertEvents.length === 0) {
    return null;
  }

  // 按风险等级排序（high > attention），然后按时间排序（最新优先）
  const sortedAlerts = [...alertEvents].sort((a, b) => {
    // 先按风险等级排序
    const riskOrder = { high: 3, attention: 2, normal: 1 };
    const riskCompare =
      (riskOrder[b.risk_level as RiskLevel] ?? 0) -
      (riskOrder[a.risk_level as RiskLevel] ?? 0);

    if (riskCompare !== 0) {
      return riskCompare;
    }

    // 同级别则按时间排序（最新优先）
    const aTime = new Date(a.start_time ?? 0).getTime();
    const bTime = new Date(b.start_time ?? 0).getTime();
    return bTime - aTime;
  });

  // 返回优先级最高的 alert 的文案
  const topAlert = sortedAlerts[0];
  return generateBehaviorText(topAlert, language);
}

/**
 * 获取最近的行为记录文案
 * 返回最近 N 条事件的文案
 *
 * @param events - 行为事件数组
 * @param count - 需要返回的数量（默认 4）
 * @param language - 语言
 * @returns 最近的行为文案数组
 */
function getRecentBehaviorTexts(
  events: BehaviorEvent[],
  count: number = 4,
  language: 'en' | 'zh' = 'en'
) {
  // 取最后 N 条事件
  const recentEvents = events.slice(Math.max(0, events.length - count));

  // 生成文案
  return recentEvents.map((event) => generateBehaviorText(event, language));
}

/**
 * 判断页面是否应该显示异常提醒卡片
 *
 * @param viewModel - 状态视图模型
 * @returns true 如果有异常提醒
 */
export function hasAlert(viewModel: StatusViewModel): boolean {
  return viewModel.primary_alert !== null;
}

/**
 * 获取页面背景色类（基于整体状态）
 *
 * @param overallStatus - 整体状态
 * @returns Tailwind CSS 类名
 */
export function getStatusBgColor(overallStatus: string): string {
  switch (overallStatus) {
    case 'normal':
      return 'bg-green-50 border-green-200';
    case 'attention':
      return 'bg-yellow-50 border-yellow-200';
    case 'high':
      return 'bg-red-50 border-red-200';
    default:
      return 'bg-gray-50 border-gray-200';
  }
}

/**
 * 获取状态文本色类（基于整体状态）
 *
 * @param overallStatus - 整体状态
 * @returns Tailwind CSS 类名
 */
export function getStatusTextColor(overallStatus: string): string {
  switch (overallStatus) {
    case 'normal':
      return 'text-green-700';
    case 'attention':
      return 'text-yellow-700';
    case 'high':
      return 'text-red-700';
    default:
      return 'text-gray-700';
  }
}

/**
 * 获取状态徽章色类（基于整体状态）
 *
 * @param overallStatus - 整体状态
 * @returns Tailwind CSS 类名
 */
export function getStatusBadgeColor(overallStatus: string): string {
  switch (overallStatus) {
    case 'normal':
      return 'bg-green-100 text-green-800';
    case 'attention':
      return 'bg-yellow-100 text-yellow-800';
    case 'high':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * 获取状态徽章文本（基于整体状态）
 *
 * @param overallStatus - 整体状态
 * @param language - 语言
 * @returns 徽章显示文本
 */
export function getStatusBadgeText(
  overallStatus: string,
  language: 'en' | 'zh' = 'en'
): string {
  const texts = {
    en: {
      normal: '✓ All good',
      attention: '⚠️ Needs attention',
      high: '🚨 Needs immediate care',
    },
    zh: {
      normal: '✓ 状态良好',
      attention: '⚠️ 需要关注',
      high: '🚨 高风险',
    },
  };

  return texts[language][overallStatus as keyof typeof texts['en']] || '○ Unknown';
}
