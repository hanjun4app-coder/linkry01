/**
 * Status Engine V2 - With Baseline Learning Integration
 *
 * Generates daily status view for elderly care monitoring.
 * Now integrates baseline learning and temporary condition detection.
 *
 * Pipeline:
 * 1. Detect temporary condition (≥3 anomalies)
 * 2. Decide if today's data should update baseline
 * 3. Update baseline (with exclusion flag)
 * 4. Generate personalized risk signals
 * 5. Combine with universal rules
 * 6. Return enhanced status
 */

import { BehaviorEvent, RiskLevel, DailyBehaviorSummaryInput, StatusViewModel } from '@/types/behavior';
import { ElderBaseline, PersonalizedRiskSignal, TemporaryCondition, BaselineComparison } from '@/types/baseline';
import { Device } from '@/types/device';

// Baseline integration
import { updateBaseline, compareToBaseline, createInitialBaseline, updateBaselineStatus } from '@/lib/baselineEngine';
import { detectTemporaryCondition, updateTemporaryCondition, shouldExcludeFromBaseline } from '@/lib/temporaryConditionDetector';

// Sensor fusion for anomaly detection
import { performSensorFusion } from '@/lib/sensorFusionV2';

/**
 * Main status generation function with baseline integration
 */
export async function generateStatusViewWithBaseline(
  elder_id: string,
  allEvents: BehaviorEvent[],
  dailyData: DailyBehaviorSummaryInput,
  devices: Device[],
  currentBaseline: ElderBaseline | null
): Promise<{
  statusView: StatusViewModel;
  baseline: ElderBaseline;
  temporaryCondition: TemporaryCondition | null;
  personalizedSignals: PersonalizedRiskSignal[];
}> {
  // ============ Step 1: Get or Initialize Baseline ============

  let baseline = currentBaseline || createInitialBaseline(elder_id);

  // ============ Step 2: Detect Temporary Condition ============

  const { has_condition, anomaly_days, recovery_trend } = detectTemporaryCondition(allEvents);

  let temporaryCondition: TemporaryCondition | null = null;

  if (has_condition) {
    // Either create new or update existing
    temporaryCondition = {
      elder_id,
      condition_id: `${elder_id}_${Date.now()}`,
      started_at: new Date().toISOString(),
      anomaly_type: inferAnomalyType(allEvents),
      consecutive_anomaly_days: anomaly_days,
      recovery_days: 0,
      status: 'active',
    };
    console.log(
      `[Baseline] Temporary condition detected: ${anomaly_days} anomaly days, status: active`
    );
  }

  // ============ Step 3: Decide if We Should Learn Today ============

  const shouldLearn = !has_condition && !hasHighRiskDay(allEvents);

  if (shouldLearn && baseline.baseline_days_collected < 365) {
    console.log(
      `[Baseline] Learning enabled for today (collecting day ${baseline.baseline_days_collected + 1})`
    );
  } else if (has_condition) {
    console.log(
      `[Baseline] Learning disabled: temporary condition active (${anomaly_days} anomaly days)`
    );
  } else if (hasHighRiskDay(allEvents)) {
    console.log(`[Baseline] Learning disabled: high-risk day detected`);
  }

  // ============ Step 4: Update Baseline ============

  const exclude_from_learning = !shouldLearn;

  // Convert daily data to baseline format
  const baselineData = {
    elder_id,
    date: new Date().toISOString().split('T')[0],
    wake_time: dailyData.wake_time || 7,
    sleep_time: dailyData.sleep_time || 22,
    total_activity_minutes: dailyData.total_activity_minutes || 0,
    bathroom_events: dailyData.bathroom_count || 0,
    bathroom_total_minutes: dailyData.bathroom_total_minutes || 0,
    night_wake_count: dailyData.night_activity_count || 0,
    daytime_bed_minutes: dailyData.daytime_bed_minutes || 0,
    active_zones: dailyData.active_zones || [],
    status: has_condition ? 'temporary_condition' : 'stable' as const,
    should_exclude_from_learning: exclude_from_learning,
  };

  baseline = updateBaseline(baseline, baselineData, exclude_from_learning);

  // ============ Step 5: Generate Personalized Risk Signals ============

  let personalizedSignals: PersonalizedRiskSignal[] = [];

  if (baseline.baseline_status === 'active') {
    const comparison = compareToBaseline(dailyData, baseline);
    personalizedSignals = comparison.signals;

    if (personalizedSignals.length > 0) {
      console.log(`[Baseline] Generated ${personalizedSignals.length} personalized risk signals`);
    }
  } else {
    console.log(
      `[Baseline] Status: ${baseline.baseline_status} - Personalized signals not yet available`
    );
  }

  // ============ Step 6: Perform Sensor Fusion for Anomalies ============

  // Get sensor data (would come from sensor readings in production)
  const sensorData = new Map<string, any[]>();
  // In production, populate from actual sensor readings

  const fusionResult = performSensorFusion({
    devices,
    raw_sensor_data: sensorData,
    recent_events: allEvents,
    daily_summary: dailyData,
  });

  // ============ Step 7: Build Universal Risk Assessment ============

  const universalRiskLevel = assessUniversalRiskLevel(allEvents, fusionResult);

  // ============ Step 8: Combine Universal Rules + Personalized Signals ============

  const combinedStatusView = generateEnhancedStatusView({
    elder_id,
    events: allEvents,
    daily_summary: dailyData,
    universal_risk: universalRiskLevel,
    personalized_signals: personalizedSignals,
    temporary_condition: temporaryCondition,
    baseline,
    fusion_anomalies: fusionResult.anomalies,
    fall_analysis: fusionResult.fall_analysis,
  });

  return {
    statusView: combinedStatusView,
    baseline,
    temporaryCondition,
    personalizedSignals,
  };
}

// ============ Helper Functions ============

/**
 * Check if today is a high-risk day (should not learn from)
 */
function hasHighRiskDay(events: BehaviorEvent[]): boolean {
  const highRiskEvents = events.filter(e => e.risk_level === 'high');
  return highRiskEvents.length > 0;
}

/**
 * Infer anomaly type from event patterns
 */
function inferAnomalyType(events: BehaviorEvent[]): string {
  const riskCounts = {
    high: 0,
    attention: 0,
    normal: 0,
  };

  for (const event of events) {
    riskCounts[event.risk_level]++;
  }

  if (riskCounts.high > 0) {
    return 'high_risk_activity';
  } else if (riskCounts.attention > 0) {
    return 'attention_needed';
  }

  return 'behavioral_anomaly';
}

/**
 * Assess overall risk using universal rules (not baseline)
 */
function assessUniversalRiskLevel(
  events: BehaviorEvent[],
  fusionResult: any
): RiskLevel {
  // Check for high-risk events
  const hasHighRisk = events.some(e => e.risk_level === 'high');
  if (hasHighRisk) {
    return 'high';
  }

  // Check for fall events
  if (fusionResult.fall_analysis.fall_detected) {
    return 'high';
  }

  // Check for attention-level events
  const hasAttention = events.some(e => e.risk_level === 'attention');
  if (hasAttention) {
    return 'attention';
  }

  return 'normal';
}

/**
 * Generate enhanced status view combining universal rules + personalized signals
 */
interface EnhancedStatusInput {
  elder_id: string;
  events: BehaviorEvent[];
  daily_summary: DailyBehaviorSummaryInput;
  universal_risk: RiskLevel;
  personalized_signals: PersonalizedRiskSignal[];
  temporary_condition: TemporaryCondition | null;
  baseline: ElderBaseline;
  fusion_anomalies: any[];
  fall_analysis: any;
}

function generateEnhancedStatusView(input: EnhancedStatusInput): StatusViewModel {
  const baselineActive = input.baseline.baseline_status === 'active';

  // Build alert message
  let alertMessage = buildAlertMessage(input);

  // Build context message with personalized signals
  let contextMessage = buildContextMessage(input, baselineActive);

  // Build recommendation
  let recommendation = buildRecommendation(input);

  return {
    elder_id: input.elder_id,
    timestamp: new Date().toISOString(),
    risk_level: input.universal_risk,
    alert_message: alertMessage,
    context_message: contextMessage,
    recommendation,
    // Additional details
    activity_minutes: input.daily_summary.total_activity_minutes || 0,
    alert_count: input.events.length,
    events: input.events.slice(-3), // Last 3 events
    baseline_status: input.baseline.baseline_status,
    in_temporary_condition: input.temporary_condition?.status === 'active',
    personalized_signals_count: input.personalized_signals.length,
  };
}

function buildAlertMessage(input: EnhancedStatusInput): string {
  const { universal_risk, fall_analysis, events, temporary_condition } = input;

  // CRITICAL: Never suppress universal safety rules
  if (fall_analysis.fall_detected) {
    return '⚠️ 跌倒警报: 检测到跌倒事件，老人已躺下。需要立即帮助。';
  }

  if (universal_risk === 'high') {
    const highRiskEvent = events.find(e => e.risk_level === 'high');
    if (highRiskEvent) {
      return `⚠️ 高风险警报: ${highRiskEvent.description}`;
    }
    return '⚠️ 高风险警报: 检测到高风险活动。';
  }

  if (universal_risk === 'attention') {
    if (temporary_condition?.status === 'active') {
      return `⚠️ 注意: 检测到${temporary_condition.anomaly_days}天异常状态，系统已降低告警频率。`;
    }
    const attentionEvent = events.find(e => e.risk_level === 'attention');
    if (attentionEvent) {
      return `ℹ️ 注意: ${attentionEvent.description}`;
    }
  }

  return '✅ 一切正常，今天没有异常检测。';
}

function buildContextMessage(input: EnhancedStatusInput, baselineActive: boolean): string {
  const { daily_summary, personalized_signals, baseline } = input;

  let messages: string[] = [];

  // Add universal context
  const activity = daily_summary.total_activity_minutes || 0;
  if (activity > 0) {
    messages.push(`活动时间: ${activity}分钟`);
  }

  const bathroom = daily_summary.bathroom_count || 0;
  if (bathroom > 0) {
    messages.push(`浴室访问: ${bathroom}次`);
  }

  // Add personalized signals (补充通用规则，不替代)
  if (baselineActive && personalized_signals.length > 0) {
    messages.push(''); // Blank line
    messages.push('📊 个性化洞察:');

    for (const signal of personalized_signals) {
      const deviation = Math.round(signal.deviation_ratio * 100);
      if (deviation > 0) {
        messages.push(
          `  • ${signal.reason} (基线: ${signal.baseline_value}, 今天: ${Math.round(signal.current_value)})`
        );
      } else {
        messages.push(
          `  • ${signal.reason} (基线: ${signal.baseline_value}, 今天: ${Math.round(signal.current_value)})`
        );
      }
    }

    messages.push(`  信心度: ${Math.round(baseline.baseline_days_collected / 14 * 100)}%`);
  } else if (!baselineActive) {
    messages.push(`收集进度: ${baseline.baseline_days_collected}天 (7天后提供个性化洞察)`);
  }

  return messages.join('\n');
}

function buildRecommendation(input: EnhancedStatusInput): string {
  const { universal_risk, temporary_condition, personalized_signals } = input;

  if (universal_risk === 'high') {
    return '立即检查老人。确保他们安全。';
  }

  if (temporary_condition?.status === 'active') {
    if (temporary_condition.recovery_days >= 2) {
      return `${temporary_condition.anomaly_type}状态正在恢复。继续监测。`;
    }
    return `检测到${temporary_condition.anomaly_type}。监测恢复进度。`;
  }

  if (personalized_signals.length > 0) {
    const highConfidence = personalized_signals.filter(s => s.confidence_score > 0.8);
    if (highConfidence.length > 0) {
      return '活动模式有所偏离。可以温和地询问一切是否安好。';
    }
  }

  return '一切正常。继续日常监测。';
}

// ============ Daily Update Integration ============

/**
 * Call this once per day to update baseline and generate new status
 */
export async function dailyStatusUpdate(
  elder_id: string,
  allEventsToday: BehaviorEvent[],
  dailySummary: DailyBehaviorSummaryInput,
  devices: Device[],
  currentBaseline: ElderBaseline | null
) {
  const result = await generateStatusViewWithBaseline(
    elder_id,
    allEventsToday,
    dailySummary,
    devices,
    currentBaseline
  );

  // Log the learning decision
  console.log(
    `[${new Date().toISOString()}] Daily Update Complete:`,
    {
      baseline_status: result.baseline.baseline_status,
      baseline_days: result.baseline.baseline_days_collected,
      in_temp_condition: !!result.temporaryCondition,
      personalized_signals: result.personalizedSignals.length,
      risk_level: result.statusView.risk_level,
    }
  );

  return result;
}

// ============ Export for Testing ============

export { assessUniversalRiskLevel, inferAnomalyType, hasHighRiskDay };
