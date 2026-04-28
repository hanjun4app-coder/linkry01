/**
 * Temporary Condition Detector
 *
 * Purpose:
 * - Identify when elder is in abnormal state (illness, medication change, travel, etc.)
 * - Exclude these days from baseline learning
 * - Reduce alert frequency during temporary conditions
 * - Automatically resolve when recovery trend detected
 *
 * State Machine:
 * normal → anomaly_detected → temporary_condition (active) → recovery → normal
 *
 * Rules:
 * 1. Enter temporary_condition when ≥3 consecutive anomaly days AND no recovery trend
 * 2. Stay in temporary_condition while anomalies continue
 * 3. Exit to recovery when ≥2 days of recovery trend detected
 * 4. Return to normal when baseline patterns resume
 */

import { TemporaryCondition } from '@/types/baseline';
import { BehaviorEvent, RiskLevel } from '@/types/behavior';

/**
 * Create new temporary condition
 */
export function createTemporaryCondition(
  elder_id: string,
  anomaly_type: string,
  notes?: string
): TemporaryCondition {
  return {
    elder_id,
    condition_id: `${elder_id}_${Date.now()}`,
    started_at: new Date().toISOString(),
    anomaly_type,
    consecutive_anomaly_days: 1,
    recovery_days: 0,
    status: 'active',
    notes,
  };
}

/**
 * Detect temporary condition from consecutive anomalies
 */
export function detectTemporaryCondition(
  events: BehaviorEvent[],
  threshold_days: number = 3,
  exclude_recovery: boolean = true
): { has_condition: boolean; anomaly_days: number; recovery_trend: boolean } {
  if (events.length === 0) {
    return {
      has_condition: false,
      anomaly_days: 0,
      recovery_trend: false,
    };
  }

  // Count consecutive days with high/attention level alerts
  let anomaly_days = 0;
  let recovery_trend = false;

  // Look at last 14 days
  const recentEvents = events.slice(-14);

  // Count high/attention risk days
  const riskDays = recentEvents.filter(e =>
    e.risk_level === 'high' || e.risk_level === 'attention'
  ).length;

  anomaly_days = riskDays;

  // Check for recovery trend (recent days improving)
  if (recentEvents.length >= 5) {
    const recent5 = recentEvents.slice(-5);
    const earlier5 = recentEvents.slice(-10, -5);

    const recentHighRisk = recent5.filter(e => e.risk_level === 'high').length;
    const earlierHighRisk = earlier5.filter(e => e.risk_level === 'high').length;

    recovery_trend = recentHighRisk < earlierHighRisk;
  }

  // Temporary condition triggered: ≥3 anomaly days AND NOT recovering
  const has_condition = anomaly_days >= threshold_days && !recovery_trend;

  return {
    has_condition,
    anomaly_days,
    recovery_trend,
  };
}

/**
 * Update temporary condition status
 */
export function updateTemporaryCondition(
  condition: TemporaryCondition,
  events: BehaviorEvent[],
  baseline_recovery_days_threshold: number = 2
): TemporaryCondition {
  // Analyze recent events for recovery
  const recentEvents = events.slice(-7);
  const normalDays = recentEvents.filter(
    e => e.risk_level === 'normal'
  ).length;

  // Check for recovery trend
  if (normalDays >= baseline_recovery_days_threshold) {
    if (condition.status === 'active') {
      // Transition to recovery
      return {
        ...condition,
        status: 'resolving',
        recovery_days: normalDays,
      };
    } else if (condition.status === 'resolving' && normalDays >= 3) {
      // Transition to resolved
      return {
        ...condition,
        status: 'resolved',
        ended_at: new Date().toISOString(),
        recovery_days: normalDays,
      };
    }
  }

  // Count consecutive high risk days
  const highRiskDays = recentEvents.filter(
    e => e.risk_level === 'high'
  ).length;

  return {
    ...condition,
    consecutive_anomaly_days: highRiskDays,
    recovery_days: normalDays,
  };
}

/**
 * Should day be excluded from baseline learning?
 */
export function shouldExcludeFromBaseline(
  day_risk_level: RiskLevel,
  is_in_temporary_condition: boolean,
  consecutive_high_risk_days: number
): boolean {
  // Exclude if in temporary condition
  if (is_in_temporary_condition) {
    return true;
  }

  // Exclude if high risk day
  if (day_risk_level === 'high') {
    return true;
  }

  // Exclude if part of consecutive high risk (≥3 days)
  if (consecutive_high_risk_days >= 3) {
    return true;
  }

  return false;
}

/**
 * Calculate alert suppression during temporary condition
 * CRITICAL: High-risk events are NEVER suppressed (safety first)
 * Returns multiplier: 1.0 = no suppression, 0.5 = 50% suppression
 */
export function getAlertSuppressionDuringTemporaryCondition(
  condition: TemporaryCondition,
  event_risk_level?: string
): number {
  // SAFETY GATE: High-risk events always show through (never suppress)
  if (event_risk_level === 'high') {
    return 1.0; // No suppression for critical events
  }

  if (condition.status === 'resolved') {
    return 1.0; // No suppression
  }

  // Active phase: 30% suppression (70% alert frequency)
  // Only applies to 'normal' and 'attention' level events
  if (condition.status === 'active') {
    return 0.7;
  }

  // Recovery phase: 50% suppression (50% alert frequency)
  // Only applies to 'normal' and 'attention' level events
  if (condition.status === 'resolving') {
    return 0.5;
  }

  return 1.0;
}

/**
 * Determine anomaly type from event patterns
 */
export function inferAnomalyType(events: BehaviorEvent[]): string {
  if (events.length === 0) return 'unknown';

  // Analyze event patterns
  const eventTypes = new Map<string, number>();
  events.forEach(e => {
    eventTypes.set(e.event_type, (eventTypes.get(e.event_type) || 0) + 1);
  });

  // Get most common anomaly
  const mostCommon = Array.from(eventTypes.entries()).sort(
    ([, a], [, b]) => b - a
  )[0];

  const eventType = mostCommon?.[0] || 'unknown';

  // Map to human-readable anomaly type
  const anomalyMap: Record<string, string> = {
    no_activity: 'potential_illness_or_inactivity',
    bathroom_long_stay: 'bathroom_issue',
    night_wake: 'sleep_disruption',
    medication_missed: 'medication_adherence_issue',
    unknown_location: 'unusual_location_access',
  };

  return anomalyMap[eventType] || 'behavioral_anomaly';
}

/**
 * Check if temporary condition should be auto-resolved
 */
export function shouldAutoResolveTemporaryCondition(
  condition: TemporaryCondition,
  days_elapsed: number
): boolean {
  // Auto-resolve if in recovery for ≥2 days
  if (condition.status === 'resolving' && condition.recovery_days >= 2) {
    return true;
  }

  // Auto-resolve if resolved status and been resolved for 24 hours
  if (condition.status === 'resolved') {
    const resolvedTime = condition.ended_at
      ? new Date(condition.ended_at).getTime()
      : 0;
    const now = Date.now();
    return now - resolvedTime > 24 * 60 * 60 * 1000;
  }

  return false;
}

/**
 * Generate human-friendly condition description
 */
export function getTemporaryConditionDescription(
  condition: TemporaryCondition,
  language: 'en' | 'zh' = 'en'
): string {
  const descriptions: Record<string, Record<string, string>> = {
    en: {
      active:
        `Temporary condition detected (${condition.anomaly_type}). System is in reduced-alert mode for ${condition.consecutive_anomaly_days} days.`,
      resolving:
        `Temporary condition resolving. Recovery detected. System returning to normal monitoring in ${3 - condition.recovery_days} days.`,
      resolved:
        'Temporary condition resolved. System has returned to normal baseline monitoring.',
    },
    zh: {
      active:
        `检测到临时状态(${condition.anomaly_type})。系统已${condition.consecutive_anomaly_days}天处于降低提示模式。`,
      resolving:
        `临时状态正在恢复。检测到恢复迹象。系统将在${3 - condition.recovery_days}天内恢复正常监测。`,
      resolved:
        '临时状态已解决。系统已恢复正常的基线监测。',
    },
  };

  const lang = language === 'zh' ? 'zh' : 'en';
  return descriptions[lang][condition.status] || 'Temporary condition detected';
}
