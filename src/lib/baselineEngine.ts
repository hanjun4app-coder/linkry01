/**
 * Baseline Engine: Learn individual behavior patterns
 *
 * Purpose:
 * - Build personalized baseline from first 7 days of data
 * - Update baseline with rolling average (recent days weighted slightly higher)
 * - Only learn from "stable" days (exclude anomalies, temporary conditions)
 * - Enable personalized risk detection based on individual patterns
 *
 * Key Rules:
 * 1. Baseline activates only after ≥7 days of collection
 * 2. Use rolling average (all days equally weighted, but recent days slightly higher)
 * 3. Exclude high-risk days and temporary condition days from learning
 * 4. Update baseline status to "needs_review" when consecutive anomalies detected
 */

import {
  ElderBaseline,
  DailyBaselineData,
  BaselineStatus,
  BaselineComparison,
  PersonalizedRiskSignal,
  LearningControlRecord,
} from '@/types/baseline';
import { DailyBehaviorSummaryInput } from '@/types/behavior';

// ============ Core Baseline Operations ============

/**
 * Create initial baseline (empty, collecting state)
 */
export function createInitialBaseline(elder_id: string): ElderBaseline {
  return {
    elder_id,
    baseline_status: 'collecting',
    baseline_days_collected: 0,

    // Default values (will be updated)
    average_wake_time: 7,
    average_sleep_time: 22,
    average_daily_activity_minutes: 180,
    average_bathroom_duration_minutes: 15,
    average_bathroom_count: 4,
    average_night_wake_count: 1,
    average_daytime_bed_minutes: 60,
    usual_active_zones: ['living_room', 'kitchen', 'bathroom'],

    last_updated_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    days_in_temporary_condition: 0,
  };
}

/**
 * Build baseline from historical events
 * Used when elder already has sufficient data (≥7 days)
 */
export function buildBaseline(
  dailyDataPoints: DailyBaselineData[],
  stable_days_only: boolean = true
): Partial<ElderBaseline> {
  // Filter to only stable days if requested
  const dataTouse = stable_days_only
    ? dailyDataPoints.filter(d => d.status === 'stable')
    : dailyDataPoints;

  if (dataTouse.length === 0) {
    return {};
  }

  // Calculate rolling averages
  const avgWakeTime = calculateWeightedAverage(
    dataTouse.map(d => d.wake_time || 7)
  );
  const avgSleepTime = calculateWeightedAverage(
    dataTouse.map(d => d.sleep_time || 22)
  );
  const avgActivityMinutes = calculateWeightedAverage(
    dataTouse.map(d => d.total_activity_minutes)
  );
  const avgBathroomDuration = calculateWeightedAverage(
    dataTouse.map(d => d.bathroom_total_minutes / Math.max(d.bathroom_events, 1))
  );
  const avgBathroomCount = calculateWeightedAverage(
    dataTouse.map(d => d.bathroom_events)
  );
  const avgNightWakes = calculateWeightedAverage(
    dataTouse.map(d => d.night_wake_count)
  );
  const avgDaytimeBed = calculateWeightedAverage(
    dataTouse.map(d => d.daytime_bed_minutes)
  );

  // Extract usual active zones (most common)
  const zoneFrequency: Record<string, number> = {};
  dataTouse.forEach(d => {
    d.active_zones.forEach(z => {
      zoneFrequency[z] = (zoneFrequency[z] || 0) + 1;
    });
  });
  const usualZones = Object.entries(zoneFrequency)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([zone]) => zone);

  return {
    average_wake_time: Math.round(avgWakeTime),
    average_sleep_time: Math.round(avgSleepTime),
    average_daily_activity_minutes: Math.round(avgActivityMinutes),
    average_bathroom_duration_minutes: Math.round(avgBathroomDuration),
    average_bathroom_count: Math.round(avgBathroomCount * 10) / 10,
    average_night_wake_count: Math.round(avgNightWakes * 10) / 10,
    average_daytime_bed_minutes: Math.round(avgDaytimeBed),
    usual_active_zones: usualZones,
    baseline_days_collected: dataTouse.length,
  };
}

/**
 * Update existing baseline with new daily data
 * Uses weighted rolling average (recent days weighted slightly higher)
 */
export function updateBaseline(
  existingBaseline: ElderBaseline,
  newDailyData: DailyBaselineData,
  exclude_from_learning: boolean = false
): ElderBaseline {
  // If data should be excluded, return baseline unchanged
  if (exclude_from_learning) {
    console.log(
      `[Baseline] Day excluded from learning: ${newDailyData.date} (reason: ${newDailyData.status})`
    );
    return existingBaseline;
  }

  // Weight for the new data point (most recent)
  // Formula: new_weight = 0.15 (15% of new value, 85% of rolling average)
  const NEW_WEIGHT = 0.15;
  const EXISTING_WEIGHT = 1 - NEW_WEIGHT;

  // Update rolling averages
  const updated: ElderBaseline = {
    ...existingBaseline,
    average_wake_time:
      existingBaseline.average_wake_time * EXISTING_WEIGHT +
      (newDailyData.wake_time || existingBaseline.average_wake_time) * NEW_WEIGHT,

    average_sleep_time:
      existingBaseline.average_sleep_time * EXISTING_WEIGHT +
      (newDailyData.sleep_time || existingBaseline.average_sleep_time) *
        NEW_WEIGHT,

    average_daily_activity_minutes:
      existingBaseline.average_daily_activity_minutes * EXISTING_WEIGHT +
      newDailyData.total_activity_minutes * NEW_WEIGHT,

    average_bathroom_count:
      existingBaseline.average_bathroom_count * EXISTING_WEIGHT +
      newDailyData.bathroom_events * NEW_WEIGHT,

    average_bathroom_duration_minutes:
      existingBaseline.average_bathroom_duration_minutes * EXISTING_WEIGHT +
      (newDailyData.bathroom_total_minutes / Math.max(newDailyData.bathroom_events, 1)) * NEW_WEIGHT,

    average_night_wake_count:
      existingBaseline.average_night_wake_count * EXISTING_WEIGHT +
      newDailyData.night_wake_count * NEW_WEIGHT,

    average_daytime_bed_minutes:
      existingBaseline.average_daytime_bed_minutes * EXISTING_WEIGHT +
      newDailyData.daytime_bed_minutes * NEW_WEIGHT,

    baseline_days_collected: Math.min(
      existingBaseline.baseline_days_collected + 1,
      365
    ),
    last_updated_at: new Date().toISOString(),
  };

  // Update baseline status if not already "needs_review"
  if (updated.baseline_status !== 'needs_review') {
    updated.baseline_status = updated.baseline_days_collected >= 7 ? 'active' : 'collecting';
  }

  return updated;
}

/**
 * Compare today's behavior to baseline
 * Returns PersonalizedRiskSignals for deviations
 */
export function compareToBaseline(
  todaySummary: DailyBehaviorSummaryInput,
  baseline: ElderBaseline
): BaselineComparison {
  // If baseline not active, return empty comparison
  if (baseline.baseline_status !== 'active') {
    return {
      elder_id: baseline.elder_id,
      is_baseline_active: false,
      baseline_status: baseline.baseline_status,
      signals: [],
      overall_deviation_ratio: 0,
      requires_attention: false,
      analysis_timestamp: new Date().toISOString(),
    };
  }

  const signals: PersonalizedRiskSignal[] = [];
  const deviationRatios: number[] = [];

  // Compare activity level
  const activityDeviation = calculateDeviation(
    todaySummary.total_activity_minutes || 0,
    baseline.average_daily_activity_minutes
  );
  deviationRatios.push(Math.abs(activityDeviation));

  if (Math.abs(activityDeviation) > 0.35) {
    // 35% deviation threshold
    signals.push({
      signal_id: `${baseline.elder_id}_activity_${Date.now()}`,
      elder_id: baseline.elder_id,
      signal_type: 'activity_deviation',
      risk_level: activityDeviation < -0.5 ? 'high' : 'attention',
      reason:
        activityDeviation < 0
          ? `Activity dropped ${Math.round(Math.abs(activityDeviation) * 100)}% compared to usual pattern`
          : `Activity increased ${Math.round(activityDeviation * 100)}% above usual pattern`,
      baseline_value: baseline.average_daily_activity_minutes,
      current_value: todaySummary.total_activity_minutes || 0,
      deviation_ratio: activityDeviation,
      confidence_score: Math.min(baseline.baseline_days_collected / 14, 1.0),
      evidence_sources: ['baseline:activity_minutes'],
      timestamp: new Date().toISOString(),
      requires_manual_review: Math.abs(activityDeviation) > 0.5,
    });
  }

  // Compare bathroom duration
  const avgBathroomDuration =
    (todaySummary.bathroom_total_minutes || 0) /
    Math.max(todaySummary.bathroom_count || 1, 1);
  const bathroomDeviation = calculateDeviation(
    avgBathroomDuration,
    baseline.average_bathroom_duration_minutes
  );
  deviationRatios.push(Math.abs(bathroomDeviation));

  if (Math.abs(bathroomDeviation) > 0.4) {
    // 40% deviation threshold
    signals.push({
      signal_id: `${baseline.elder_id}_bathroom_${Date.now()}`,
      elder_id: baseline.elder_id,
      signal_type: 'bathroom_duration_change',
      risk_level: bathroomDeviation > 0.5 ? 'high' : 'attention',
      reason:
        bathroomDeviation > 0
          ? `Average bathroom visit ${Math.round(bathroomDeviation * 100)}% longer than usual`
          : `Average bathroom visit ${Math.round(Math.abs(bathroomDeviation) * 100)}% shorter than usual`,
      baseline_value: baseline.average_bathroom_duration_minutes,
      current_value: avgBathroomDuration,
      deviation_ratio: bathroomDeviation,
      confidence_score: baseline.baseline_days_collected / 14,
      evidence_sources: ['baseline:bathroom_duration'],
      timestamp: new Date().toISOString(),
      requires_manual_review: false,
    });
  }

  // Compare night activity
  const nightActivityDeviation = calculateDeviation(
    todaySummary.night_activity_count || 0,
    baseline.average_night_wake_count
  );
  deviationRatios.push(Math.abs(nightActivityDeviation));

  if (Math.abs(nightActivityDeviation) > 0.5) {
    signals.push({
      signal_id: `${baseline.elder_id}_night_${Date.now()}`,
      elder_id: baseline.elder_id,
      signal_type: 'night_activity_change',
      risk_level: nightActivityDeviation > 0 ? 'attention' : 'normal',
      reason:
        nightActivityDeviation > 0
          ? `More nighttime activity than usual (${Math.round(nightActivityDeviation * 100)}% increase)`
          : `Less nighttime activity than usual`,
      baseline_value: baseline.average_night_wake_count,
      current_value: todaySummary.night_activity_count || 0,
      deviation_ratio: nightActivityDeviation,
      confidence_score: baseline.baseline_days_collected / 14,
      evidence_sources: ['baseline:night_activity'],
      timestamp: new Date().toISOString(),
      requires_manual_review: false,
    });
  }

  // Calculate overall deviation
  const overallDeviation =
    deviationRatios.length > 0 ? deviationRatios.reduce((a, b) => a + b) / deviationRatios.length : 0;

  return {
    elder_id: baseline.elder_id,
    is_baseline_active: true,
    baseline_status: baseline.baseline_status,
    signals,
    overall_deviation_ratio: overallDeviation,
    requires_attention: signals.some(s => s.risk_level !== 'normal'),
    analysis_timestamp: new Date().toISOString(),
  };
}

// ============ Helper Functions ============

/**
 * Calculate weighted average (recent values weighted slightly higher)
 */
function calculateWeightedAverage(values: number[]): number {
  if (values.length === 0) return 0;

  let sum = 0;
  let weights = 0;

  values.forEach((value, index) => {
    // Weight increases slightly for more recent values
    const weight = 1 + (index / values.length) * 0.2; // +20% for most recent
    sum += value * weight;
    weights += weight;
  });

  return sum / weights;
}

/**
 * Calculate deviation ratio
 * Returns: (current - baseline) / baseline
 * Positive = above baseline, Negative = below baseline
 */
function calculateDeviation(current: number, baseline: number): number {
  if (baseline === 0) return current > 0 ? 1 : 0;
  return (current - baseline) / baseline;
}

/**
 * Determine if baseline status should be updated
 */
export function updateBaselineStatus(
  baseline: ElderBaseline,
  consecutive_anomalies: number,
  days_in_temporary_condition: number
): BaselineStatus {
  // If consecutive anomalies detected, mark for review
  if (consecutive_anomalies >= 3) {
    return 'needs_review';
  }

  // If days collected < 7, still collecting
  if (baseline.baseline_days_collected < 7) {
    return 'collecting';
  }

  // Otherwise, active
  return 'active';
}

/**
 * Create learning control record
 */
export function createLearningControlRecord(
  date: string,
  dayStatus: 'stable' | 'temporary_condition' | 'anomaly' | 'recovery',
  confidence: number = 0.9
): LearningControlRecord {
  const should_learn = dayStatus === 'stable' || dayStatus === 'recovery';
  const reason = {
    stable: 'Normal day, suitable for learning',
    temporary_condition: 'Temporary condition active, excluded from learning',
    anomaly: 'High risk day, excluded from learning',
    recovery: 'Recovery period, suitable for learning',
  }[dayStatus];

  return {
    date,
    should_learn,
    reason,
    is_stable: dayStatus === 'stable',
    is_temporary_condition: dayStatus === 'temporary_condition',
    is_high_risk: dayStatus === 'anomaly',
    is_recovery: dayStatus === 'recovery',
    confidence,
  };
}
