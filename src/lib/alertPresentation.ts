/**
 * Alert Presentation Layer
 * Transforms internal anomaly detection outputs into calm, consumer-friendly alerts
 *
 * Phase 4: Product-Level Optimization
 * Goal: Transform from engineering-grade to consumer-grade experience
 *
 * Responsibilities:
 * 1. Select single primary alert (highest risk → highest confidence → most recent)
 * 2. Convert confidence scores to simple labels
 * 3. Apply soft, non-alarming language
 * 4. Group/suppress secondary alerts
 * 5. Enforce 30-minute cooldown per alert type
 */

import { BehaviorEvent, RiskLevel } from '@/types/behavior';

/**
 * Consumer-friendly alert level
 * Replaces internal risk_level for user display
 */
export type ConsumerAlertLevel = 'no_concern' | 'attention' | 'check_now';

/**
 * Confidence label (internal use only, not shown to users)
 */
export type ConfidenceLabel = 'very_low' | 'low' | 'moderate' | 'high' | 'very_high';

/**
 * Alert presentation format (what users see)
 */
export interface PresentedAlert {
  // What to show user
  headline: string; // e.g., "We noticed something unusual"
  description: string; // Calm, non-medical explanation
  suggestion: string; // Non-directive suggestion

  // Category for styling (not exposed to user)
  level: ConsumerAlertLevel; // 'no_concern' | 'attention' | 'check_now'

  // Internal metadata (not shown to user)
  internal_confidence: ConfidenceLabel; // For UI hints only
  internal_confidence_score: number; // 0-1, not shown to user
  internal_evidence_count: number; // For logging

  // Source event tracking
  source_event_id?: string;
  source_event_type?: string;
  triggered_at: string; // ISO timestamp
}

/**
 * Track alert history for cooldown enforcement
 */
interface AlertHistoryEntry {
  event_type: string;
  triggered_at: number; // timestamp
}

/**
 * Global alert history (30-minute cooldown)
 * In production: move to Redis or persistent store
 */
const alertHistory: Map<string, AlertHistoryEntry> = new Map();

const COOLDOWN_MINUTES = 30;
const COOLDOWN_MS = COOLDOWN_MINUTES * 60 * 1000;

/**
 * Step 1: Convert confidence_score to simple label
 * Internal use only - not shown to users
 */
export function getConfidenceLabel(score: number): ConfidenceLabel {
  if (score >= 0.9) return 'very_high';
  if (score >= 0.75) return 'high';
  if (score >= 0.6) return 'moderate';
  if (score >= 0.4) return 'low';
  return 'very_low';
}

/**
 * Step 2: Map risk_level to consumer alert level
 * This determines HOW to present, not WHETHER to present
 */
function mapToConsumerLevel(risk_level: RiskLevel, confidence: number): ConsumerAlertLevel {
  // high risk → always "check_now" (regardless of confidence)
  if (risk_level === 'high') {
    return 'check_now';
  }

  // attention risk → depends on confidence
  if (risk_level === 'attention') {
    // High confidence attention → "check_now"
    if (confidence >= 0.75) {
      return 'check_now';
    }
    // Medium confidence → "attention"
    if (confidence >= 0.6) {
      return 'attention';
    }
    // Low confidence → "no_concern"
    return 'no_concern';
  }

  // normal → always "no_concern"
  return 'no_concern';
}

/**
 * Step 3: Check if alert is within cooldown window
 * Same event_type cannot trigger more than once per 30 minutes
 */
function isWithinCooldown(eventType: string): boolean {
  const lastAlert = alertHistory.get(eventType);
  if (!lastAlert) {
    return false; // Not in cooldown
  }

  const timeSinceLastAlert = Date.now() - lastAlert.triggered_at;
  return timeSinceLastAlert < COOLDOWN_MS;
}

/**
 * Step 4: Record alert in history for cooldown tracking
 */
function recordAlertInHistory(eventType: string): void {
  alertHistory.set(eventType, {
    event_type: eventType,
    triggered_at: Date.now(),
  });

  // Clean up old entries (optional optimization)
  for (const [key, entry] of alertHistory.entries()) {
    if (Date.now() - entry.triggered_at > COOLDOWN_MS * 2) {
      alertHistory.delete(key);
    }
  }
}

/**
 * Step 5: Apply soft language transformation
 * Convert technical/medical language to calm, friendly tone
 */
function applySoftLanguage(
  eventType: string,
  confidence: ConfidenceLabel,
  language: 'en' | 'zh' = 'en'
): { headline: string; description: string; suggestion: string } {
  const softTexts = {
    en: {
      no_activity_confirmed: {
        headline: 'We noticed something unusual',
        description: 'There hasn\'t been much activity detected. It might be a good time to check in.',
        suggestion: 'A gentle call or text could be nice.',
      },
      night_bed_exit_no_return: {
        headline: 'Something unusual at night',
        description: 'We noticed an extended time out of bed during sleep hours.',
        suggestion: 'A quiet check-in might be good.',
      },
      path_interrupted: {
        headline: 'We noticed movement in the hallway',
        description: 'There was movement detected, but we\'re not sure where they ended up.',
        suggestion: 'A gentle check might help.',
      },
      medication_cabinet_accessed: {
        headline: 'Medication cabinet opened',
        description: 'The medication cabinet was just accessed.',
        suggestion: 'Nothing urgent - just a reminder for your records.',
      },
      medication_missed: {
        headline: 'Missed medication time',
        description: 'The usual medication time has passed.',
        suggestion: 'A gentle reminder might be helpful.',
      },
      medication_without_followup: {
        headline: 'Medication access noted',
        description: 'The medication cabinet was opened, but we didn\'t see eating activity after.',
        suggestion: 'This might be worth a quick check-in.',
      },
      bathroom_risk_elevated: {
        headline: 'Extended bathroom visit',
        description: 'There\'s been an extended time in the bathroom.',
        suggestion: 'A gentle check-in would be good.',
      },
      default: {
        headline: 'We noticed something',
        description: 'The system detected something worth being aware of.',
        suggestion: 'You might want to check in.',
      },
    },
    zh: {
      no_activity_confirmed: {
        headline: '我们注意到一些不寻常的情况',
        description: '检测到活动较少。现在可能是个很好的检查时机。',
        suggestion: '温柔的电话或短信可能很好。',
      },
      night_bed_exit_no_return: {
        headline: '夜间有些不寻常',
        description: '我们注意到睡眠时间内长时间离开床。',
        suggestion: '安静的检查可能很好。',
      },
      path_interrupted: {
        headline: '我们注意到走廊里有活动',
        description: '检测到活动，但我们不确定他们最后在哪里。',
        suggestion: '温柔的检查可能会有帮助。',
      },
      medication_cabinet_accessed: {
        headline: '药柜打开了',
        description: '刚刚打开了药柜。',
        suggestion: '没什么紧急的——只是提个醒。',
      },
      medication_missed: {
        headline: '错过了用药时间',
        description: '通常的用药时间已经过去了。',
        suggestion: '温柔的提醒可能会很有帮助。',
      },
      medication_without_followup: {
        headline: '用药访问已记录',
        description: '药柜已打开，但之后我们没有看到进食活动。',
        suggestion: '这可能值得快速检查一下。',
      },
      bathroom_risk_elevated: {
        headline: '卫生间访问时间较长',
        description: '在卫生间里的时间较长。',
        suggestion: '温柔的检查会很好。',
      },
      default: {
        headline: '我们注意到一些情况',
        description: '系统检测到值得关注的内容。',
        suggestion: '您可能想检查一下。',
      },
    },
  };

  const langTexts = softTexts[language];
  const eventTexts = langTexts[eventType as keyof typeof langTexts] || langTexts.default;

  return eventTexts;
}

/**
 * Main entry point: Transform single event into consumer-friendly alert
 * Returns null if alert should be suppressed (cooldown, low confidence, etc.)
 */
export function transformEventToAlert(
  event: BehaviorEvent,
  language: 'en' | 'zh' = 'en'
): PresentedAlert | null {
  // Extract needed data
  const confidence = event.confidence_score ?? 0.5;
  const riskLevel = event.risk_level;
  const eventType = event.event_type;
  const eventId = event.event_id || event.id;

  // Step 1: Check cooldown (suppress if within 30 minutes)
  if (isWithinCooldown(eventType)) {
    console.log(`[Alert] Suppressed: ${eventType} - within cooldown window`);
    return null;
  }

  // Step 2: Map to consumer level
  const consumerLevel = mapToConsumerLevel(riskLevel, confidence);

  // Step 3: Don't present "no_concern" alerts to user
  if (consumerLevel === 'no_concern') {
    return null;
  }

  // Step 4: Get confidence label (for internal UI hints only)
  const confidenceLabel = getConfidenceLabel(confidence);

  // Step 5: Apply soft language
  const softText = applySoftLanguage(eventType, confidenceLabel, language);

  // Step 6: Record in cooldown history
  recordAlertInHistory(eventType);

  // Step 7: Create presented alert (no raw scores/evidence shown)
  const presentedAlert: PresentedAlert = {
    headline: softText.headline,
    description: softText.description,
    suggestion: softText.suggestion,
    level: consumerLevel,
    internal_confidence: confidenceLabel,
    internal_confidence_score: confidence, // Stored but not shown
    internal_evidence_count: event.evidence_sources?.length ?? 0,
    source_event_id: eventId,
    source_event_type: eventType,
    triggered_at: new Date().toISOString(),
  };

  return presentedAlert;
}

/**
 * Select single primary alert from multiple events
 * Selection logic:
 * 1. Highest consumer level (check_now > attention > no_concern)
 * 2. If tie → highest confidence_score
 * 3. If tie → most recent timestamp
 */
export function selectPrimaryAlert(
  events: BehaviorEvent[],
  language: 'en' | 'zh' = 'en'
): PresentedAlert | null {
  if (events.length === 0) {
    return null;
  }

  // Transform all events to alerts (some may return null due to cooldown)
  const candidates: (PresentedAlert & { original_event: BehaviorEvent })[] = [];

  for (const event of events) {
    const alert = transformEventToAlert(event, language);
    if (alert) {
      candidates.push({
        ...alert,
        original_event: event,
      });
    }
  }

  if (candidates.length === 0) {
    return null;
  }

  // Sort by: level (check_now > attention) → confidence → recency
  const levelOrder = { check_now: 3, attention: 2, no_concern: 1 };

  candidates.sort((a, b) => {
    // 1. Compare alert level
    const levelDiff = (levelOrder[b.level] ?? 0) - (levelOrder[a.level] ?? 0);
    if (levelDiff !== 0) {
      return levelDiff;
    }

    // 2. Compare confidence
    const confidenceDiff = b.internal_confidence_score - a.internal_confidence_score;
    if (confidenceDiff !== 0.1) {
      return confidenceDiff;
    }

    // 3. Compare recency (most recent first)
    const timeA = new Date(a.triggered_at).getTime();
    const timeB = new Date(b.triggered_at).getTime();
    return timeB - timeA;
  });

  // Return highest priority alert
  const topAlert = candidates[0];

  console.log(
    `[Alert] Selected primary: ${topAlert.source_event_type} (level: ${topAlert.level}, confidence: ${topAlert.internal_confidence})`
  );

  // Remove internal fields before returning to user
  const { original_event, ...presentedAlert } = topAlert;
  return presentedAlert as PresentedAlert;
}

/**
 * Group secondary alerts (for logging/analytics, not shown to user)
 * Returns count of suppressed alerts
 */
export function countSuppressedAlerts(
  events: BehaviorEvent[],
  language: 'en' | 'zh' = 'en'
): { primary_count: 1; suppressed_count: number; suppression_reasons: string[] } {
  const allAlerts = events
    .map(e => transformEventToAlert(e, language))
    .filter(Boolean) as PresentedAlert[];

  const reasons: string[] = [];

  // Count events that didn't become alerts
  for (const event of events) {
    const alert = transformEventToAlert(event, language);
    if (!alert) {
      if (isWithinCooldown(event.event_type)) {
        reasons.push(`${event.event_type}: cooldown active`);
      } else if (event.risk_level === 'normal' || mapToConsumerLevel(event.risk_level, event.confidence_score ?? 0.5) === 'no_concern') {
        reasons.push(`${event.event_type}: low confidence/priority`);
      }
    }
  }

  return {
    primary_count: 1,
    suppressed_count: events.length - 1,
    suppression_reasons: reasons,
  };
}

/**
 * Helper: Clear cooldown for testing
 */
export function clearCooldownHistory(): void {
  alertHistory.clear();
}

/**
 * Helper: Get cooldown status (for debugging)
 */
export function getCooldownStatus(): Record<string, { minutes_remaining: number }> {
  const status: Record<string, { minutes_remaining: number }> = {};

  for (const [eventType, entry] of alertHistory.entries()) {
    const msRemaining = COOLDOWN_MS - (Date.now() - entry.triggered_at);
    const minutesRemaining = Math.ceil(msRemaining / 1000 / 60);

    if (minutesRemaining > 0) {
      status[eventType] = { minutes_remaining: minutesRemaining };
    }
  }

  return status;
}
