/**
 * 置信度评分系统
 * 为每个 alert 计算系统确定性分数 (0-1)
 *
 * 评分规则：
 * - 单一信号 → 0.4-0.6
 * - 双信号 → 0.6-0.8
 * - 多信号 + 时间上下文 → 0.8-0.95
 * - High risk → +15% 加成
 */

import { BehaviorEvent, RiskLevel } from '@/types/behavior';
import {
  CONFIDENCE_SCORE_CONFIG,
  getConfidenceScoreRange,
  isNormalActivityTime,
} from '@/config/defaultRules';

/**
 * 计算事件的置信度分数
 *
 * @param event - 行为事件
 * @param evidenceSourcesCount - 证据来源数量（例如 evidence_sources 数组长度）
 * @param hasTimeContext - 是否包含时间上下文（如夜间/正常时间）
 * @returns 置信度分数 (0-1)
 */
export function calculateConfidenceScore(
  event: BehaviorEvent,
  evidenceSourcesCount: number = 1,
  hasTimeContext: boolean = true
): number {
  // 基础分数范围
  const range = getConfidenceScoreRange(evidenceSourcesCount, hasTimeContext);
  let score = range.min + (range.max - range.min) * 0.5; // 取范围中点

  // 根据证据数量微调分数
  if (evidenceSourcesCount === 1) {
    score = range.min + (range.max - range.min) * 0.3; // 单信号偏低
  } else if (evidenceSourcesCount === 2) {
    score = range.min + (range.max - range.min) * 0.5; // 双信号中点
  } else if (evidenceSourcesCount >= 3) {
    score = range.min + (range.max - range.min) * 0.8; // 多信号偏高
  }

  // High risk 事件加成
  if (event.risk_level === 'high') {
    score = Math.min(
      1,
      score + CONFIDENCE_SCORE_CONFIG.high_risk_boost
    );
  }

  // 时间上下文加成
  if (hasTimeContext) {
    // 如果异常发生在非正常时间（例如夜间离床），置信度增加
    const isNormalTime = isNormalActivityTime();
    if (!isNormalTime && event.event_type === 'night_wake') {
      score = Math.min(1, score + 0.1);
    }
  }

  // 持续时长加成
  // 如果异常持续较长时间，置信度更高
  if (event.duration_minutes && event.duration_minutes > 30) {
    score = Math.min(1, score + 0.05);
  }

  // 确保分数在 0-1 范围内
  return Math.max(0, Math.min(1, score));
}

/**
 * 获取置信度描述文本
 * 用于向用户展示系统的确定性程度
 *
 * @param confidence - 置信度分数 (0-1)
 * @param language - 语言
 * @returns 用户友好的描述文本
 */
export function getConfidenceLabel(
  confidence: number,
  language: 'en' | 'zh' = 'en'
): string {
  const labels = {
    en: {
      very_low: 'Very uncertain',
      low: 'Somewhat uncertain',
      medium: 'Reasonably confident',
      high: 'Quite confident',
      very_high: 'Very confident',
    },
    zh: {
      very_low: '非常不确定',
      low: '较为不确定',
      medium: '较为确定',
      high: '比较有把握',
      very_high: '非常有把握',
    },
  };

  const labelMap = labels[language];

  if (confidence < 0.4) return labelMap.very_low;
  if (confidence < 0.6) return labelMap.low;
  if (confidence < 0.75) return labelMap.medium;
  if (confidence < 0.9) return labelMap.high;
  return labelMap.very_high;
}

/**
 * 根据置信度调整 alert 文案的严肃程度
 * 低置信度时使用更温和的表述
 *
 * @param confidence - 置信度分数 (0-1)
 * @param baseText - 原始文案
 * @returns 调整后的文案
 */
export function adjustTextByConfidence(
  confidence: number,
  baseText: {
    title: string;
    summary: string;
    suggestion: string;
  },
  language: 'en' | 'zh' = 'en'
): {
  title: string;
  summary: string;
  suggestion: string;
} {
  // 低置信度时，添加"可能"、"似乎"等限定词
  if (confidence < 0.6) {
    if (language === 'en') {
      return {
        title: `Possible: ${baseText.title}`,
        summary: `We noticed something that might be worth checking: ${baseText.summary}`,
        suggestion: `If this happens again, feel free to ${baseText.suggestion.toLowerCase()}`,
      };
    } else {
      return {
        title: `可能：${baseText.title}`,
        summary: `我们注意到可能值得关注的情况：${baseText.summary}`,
        suggestion: `如果再次发生，可以考虑${baseText.suggestion}`,
      };
    }
  }

  // 中等置信度时，使用原始文案
  if (confidence < 0.8) {
    return baseText;
  }

  // 高置信度时，添加强调
  if (language === 'en') {
    return {
      title: `⚠️ ${baseText.title}`,
      summary: baseText.summary,
      suggestion: baseText.suggestion,
    };
  } else {
    return {
      title: `⚠️ ${baseText.title}`,
      summary: baseText.summary,
      suggestion: baseText.suggestion,
    };
  }
}

/**
 * 计算事件列表的平均置信度
 * 用于判断整体系统信心
 *
 * @param events - 事件列表
 * @returns 平均置信度 (0-1)
 */
export function calculateAverageConfidence(
  events: BehaviorEvent[]
): number {
  if (events.length === 0) return 1; // 没有异常时置信度最高

  const total = events.reduce((sum, event) => {
    return sum + (event.confidence_score || 0.5);
  }, 0);

  return total / events.length;
}

/**
 * 判断置信度是否足够高以至于可以推送
 * 用于额外的过滤层
 *
 * @param confidence - 置信度分数 (0-1)
 * @param riskLevel - 风险等级
 * @returns 是否应该推送
 */
export function isConfidenceThresholdMet(
  confidence: number,
  riskLevel: RiskLevel
): boolean {
  // High risk 即使置信度较低也应该推送
  if (riskLevel === 'high') {
    return confidence >= 0.4;
  }

  // Attention 级别需要更高的置信度
  if (riskLevel === 'attention') {
    return confidence >= 0.6;
  }

  // Normal 级别不推送
  return false;
}
