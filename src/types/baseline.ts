/**
 * AI Personalization Layer Types
 * Enables baseline learning, temporary condition detection, and personalized risk signals
 */

/**
 * Status of baseline collection
 * - "collecting": Still gathering data (< 7 days)
 * - "active": Baseline ready for comparison
 * - "needs_review": Anomaly detected, baseline should be reviewed manually
 */
export type BaselineStatus = 'collecting' | 'active' | 'needs_review';

/**
 * Elder's behavioral baseline
 * Used to personalize risk detection based on individual patterns
 */
export interface ElderBaseline {
  // Identity
  elder_id: string;

  // Baseline status
  baseline_status: BaselineStatus;
  baseline_days_collected: number;

  // Daily patterns (rolling averages)
  average_wake_time: number; // hour of day (0-23)
  average_sleep_time: number; // hour of day (0-23)
  average_daily_activity_minutes: number;
  average_bathroom_duration_minutes: number;
  average_bathroom_count: number;
  average_night_wake_count: number;
  average_daytime_bed_minutes: number;

  // Activity patterns
  usual_active_zones: string[]; // e.g., ['living_room', 'kitchen', 'bathroom']

  // Metadata
  last_updated_at: string; // ISO timestamp
  created_at: string; // ISO timestamp

  // Advanced tracking
  days_in_temporary_condition: number;
  last_anomaly_date?: string;
}

/**
 * Daily behavior summary for baseline updates
 */
export interface DailyBaselineData {
  elder_id: string;
  date: string; // YYYY-MM-DD

  // Activity metrics
  wake_time?: number; // hour (0-23)
  sleep_time?: number; // hour (0-23)
  total_activity_minutes: number;
  bathroom_events: number;
  bathroom_total_minutes: number;
  night_wake_count: number;
  daytime_bed_minutes: number;
  active_zones: string[];

  // Status
  status: 'stable' | 'temporary_condition' | 'anomaly' | 'recovery';
  should_exclude_from_learning: boolean; // High risk days, etc.
}

/**
 * Temporary condition state
 * Used to avoid learning abnormal patterns
 */
export interface TemporaryCondition {
  elder_id: string;
  condition_id: string;

  // Timeline
  started_at: string; // ISO timestamp
  ended_at?: string; // ISO timestamp

  // Metadata
  anomaly_type: string; // e.g., 'illness', 'medication_change', 'travel'
  consecutive_anomaly_days: number;
  recovery_days: number; // days since anomaly resolved

  // Status
  status: 'active' | 'resolving' | 'resolved';
  notes?: string;
}

/**
 * Personalized risk signal
 * Shows how current behavior differs from personal baseline
 */
export interface PersonalizedRiskSignal {
  signal_id: string;
  elder_id: string;

  // Signal details
  signal_type: string; // e.g., 'activity_drop', 'sleep_pattern_change'
  risk_level: 'normal' | 'attention' | 'high';
  reason: string; // Human-friendly explanation

  // Baseline comparison
  baseline_value: number;
  current_value: number;
  deviation_ratio: number; // e.g., 0.45 = 45% below baseline

  // Confidence
  confidence_score: number; // 0-1
  evidence_sources: string[];

  // Metadata
  timestamp: string; // ISO timestamp
  requires_manual_review: boolean;
}

/**
 * Baseline comparison result
 * Output when comparing daily data to baseline
 */
export interface BaselineComparison {
  elder_id: string;
  is_baseline_active: boolean;
  baseline_status: BaselineStatus;

  // Detected signals
  signals: PersonalizedRiskSignal[];

  // Overall assessment
  overall_deviation_ratio: number; // Average deviation across all metrics
  requires_attention: boolean;

  // Timeline
  analysis_timestamp: string;
}

/**
 * Learning control metadata
 * Tracks which days should contribute to baseline
 */
export interface LearningControlRecord {
  date: string; // YYYY-MM-DD
  should_learn: boolean; // Should this day update baseline?
  reason: string; // Why included/excluded

  // Day classification
  is_stable: boolean;
  is_temporary_condition: boolean;
  is_high_risk: boolean;
  is_recovery: boolean;

  confidence: number; // 0-1, how certain is this classification?
}
