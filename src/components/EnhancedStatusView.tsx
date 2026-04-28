/**
 * Enhanced Status View Component
 *
 * Displays:
 * 1. Universal safety rules (always shown)
 * 2. Personalized risk signals (supplementary)
 * 3. Temporary condition status
 * 4. Baseline collection progress
 *
 * Design principle: Universal rules are the baseline minimum.
 * Personalized signals provide context and improve understanding.
 */

import React from 'react';
import { StatusViewModel } from '@/types/behavior';
import { PersonalizedRiskSignal, ElderBaseline } from '@/types/baseline';

interface EnhancedStatusViewProps {
  status: StatusViewModel;
  personalizedSignals?: PersonalizedRiskSignal[];
  baseline?: ElderBaseline;
  inTemporaryCondition?: boolean;
}

export const EnhancedStatusView: React.FC<EnhancedStatusViewProps> = ({
  status,
  personalizedSignals = [],
  baseline,
  inTemporaryCondition = false,
}) => {
  // Determine visual style based on risk level
  const riskStyles = {
    high: 'border-red-500 bg-red-50',
    attention: 'border-yellow-500 bg-yellow-50',
    normal: 'border-green-500 bg-green-50',
  };

  const riskIcons = {
    high: '🔴',
    attention: '🟡',
    normal: '🟢',
  };

  const baselineReady = baseline?.baseline_status === 'active';
  const baselineProgress =
    baseline?.baseline_days_collected &&
    baseline?.baseline_days_collected >= 7
      ? 100
      : ((baseline?.baseline_days_collected || 0) / 7) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto p-4 space-y-4">
      {/* ============ CRITICAL ALERT SECTION ============ */}
      {status.risk_level === 'high' && (
        <div className="border-2 border-red-500 bg-red-50 p-4 rounded-lg">
          <div className="text-xl font-bold text-red-700 mb-2">
            {riskIcons[status.risk_level]} {status.alert_message}
          </div>
          <div className="text-sm text-red-600 mb-3">
            通用安全规则已触发。这是系统的最小基准。
          </div>
          <div className="text-base font-semibold text-red-700">
            {status.recommendation}
          </div>
        </div>
      )}

      {/* ============ ATTENTION / NORMAL STATUS ============ */}
      {status.risk_level !== 'high' && (
        <div className={`border-2 p-4 rounded-lg ${riskStyles[status.risk_level]}`}>
          <div className="text-lg font-bold mb-2">
            {riskIcons[status.risk_level]} {status.alert_message}
          </div>

          {/* Temporary Condition Banner */}
          {inTemporaryCondition && (
            <div className="bg-yellow-100 border border-yellow-400 rounded p-2 mb-3 text-sm text-yellow-800">
              ⚠️ 检测到临时异常状态。系统已降低告警频率。但关键警报仍会显示。
            </div>
          )}

          {/* Context Information */}
          <div className="mb-4 space-y-2">
            <div className="text-sm text-gray-700 whitespace-pre-line">
              {status.context_message}
            </div>
          </div>

          {/* Recommendation */}
          <div className="text-sm font-semibold text-gray-800 bg-white bg-opacity-50 p-2 rounded">
            💡 {status.recommendation}
          </div>
        </div>
      )}

      {/* ============ PERSONALIZED SIGNALS SECTION ============ */}
      {baselineReady && personalizedSignals.length > 0 && (
        <div className="border border-blue-300 bg-blue-50 p-4 rounded-lg">
          <div className="mb-3">
            <div className="text-sm font-bold text-blue-900 mb-2">
              📊 个性化洞察（补充通用规则）
            </div>
            <div className="text-xs text-blue-700 mb-3">
              这些信号显示与 {baseline?.baseline_days_collected} 天个人基线的偏差。
              它们提供背景，但永远不会替代通用安全规则。
            </div>
          </div>

          <div className="space-y-3">
            {personalizedSignals.map((signal) => (
              <PersonalizedSignalCard key={signal.signal_id} signal={signal} />
            ))}
          </div>

          <div className="mt-3 text-xs text-blue-700">
            信心度: {Math.round((baseline?.baseline_days_collected || 7) / 14 * 100)}%
            {(baseline?.baseline_days_collected || 7) < 14 && ' (还在学习中)'}
          </div>
        </div>
      )}

      {/* ============ BASELINE COLLECTION PROGRESS ============ */}
      {baseline && baseline.baseline_status !== 'active' && (
        <div className="border border-gray-300 bg-gray-50 p-4 rounded-lg">
          <div className="mb-2 text-sm font-bold text-gray-800">
            📈 个性化学习进度
          </div>

          <div className="flex items-center gap-2 mb-2">
            <div className="flex-grow bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${baselineProgress}%` }}
              />
            </div>
            <span className="text-sm text-gray-700">
              {baseline.baseline_days_collected}/7 天
            </span>
          </div>

          <div className="text-xs text-gray-600">
            {baseline.baseline_days_collected === 0 && '开始收集...'}
            {baseline.baseline_days_collected > 0 && baseline.baseline_days_collected < 7
              ? `继续收集 (${7 - baseline.baseline_days_collected} 天剩余)`
              : ''}
            {baseline.baseline_status === 'active'
              ? '✅ 个性化学习已激活'
              : ''}
          </div>

          {baseline.baseline_status === 'needs_review' && (
            <div className="mt-2 text-xs text-orange-700 bg-orange-100 p-2 rounded">
              ⚠️ 基线需要审查: 检测到异常模式。
            </div>
          )}
        </div>
      )}

      {/* ============ SUMMARY STATS ============ */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <StatCard
          label="活动时间"
          value={`${status.activity_minutes}分钟`}
          color="blue"
        />
        <StatCard label="今日告警" value={status.alert_count} color="gray" />
        <StatCard
          label="个性化信号"
          value={personalizedSignals.length}
          color={baselineReady ? 'purple' : 'gray'}
        />
      </div>

      {/* ============ KEY MESSAGE ============ */}
      <div className="text-xs text-gray-600 italic border-l-4 border-gray-300 pl-3">
        💡 <strong>关键原则</strong>: 通用安全规则始终适用。个性化信号提供背景，帮助
        理解为什么某个人的行为对他们来说是异常的。系统永远不会因为个人基线
        过低而忽略明显的高风险情况。
      </div>
    </div>
  );
};

// ============ PERSONALIZED SIGNAL CARD ============

interface PersonalizedSignalCardProps {
  signal: PersonalizedRiskSignal;
}

const PersonalizedSignalCard: React.FC<PersonalizedSignalCardProps> = ({ signal }) => {
  const deviationPercent = Math.round(Math.abs(signal.deviation_ratio) * 100);
  const direction = signal.deviation_ratio > 0 ? '增加' : '下降';
  const signalColor =
    signal.risk_level === 'high'
      ? 'border-red-300 bg-red-50'
      : signal.risk_level === 'attention'
        ? 'border-yellow-300 bg-yellow-50'
        : 'border-blue-300 bg-blue-50';

  return (
    <div className={`border ${signalColor} p-3 rounded`}>
      <div className="font-semibold text-sm mb-1">
        {getSignalIcon(signal.signal_type)} {getSignalLabel(signal.signal_type)}
      </div>

      <div className="text-sm text-gray-800 mb-2">{signal.reason}</div>

      <div className="grid grid-cols-3 gap-2 text-xs text-gray-700">
        <div>
          <span className="text-gray-500">基线</span>
          <div className="font-semibold">{signal.baseline_value}</div>
        </div>
        <div>
          <span className="text-gray-500">今天</span>
          <div className="font-semibold">{Math.round(signal.current_value)}</div>
        </div>
        <div>
          <span className="text-gray-500">变化</span>
          <div className="font-semibold text-red-600">
            {direction} {deviationPercent}%
          </div>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <div className="flex-grow bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full"
            style={{
              width: `${Math.min(signal.confidence_score * 100, 100)}%`,
            }}
          />
        </div>
        <span className="text-xs text-gray-600">
          {Math.round(signal.confidence_score * 100)}% 信心度
        </span>
      </div>

      {signal.requires_manual_review && (
        <div className="mt-2 text-xs text-orange-700 bg-orange-50 p-1 rounded">
          🔍 建议手动审查
        </div>
      )}
    </div>
  );
};

// ============ STAT CARD ============

interface StatCardProps {
  label: string;
  value: string | number;
  color: 'blue' | 'gray' | 'purple' | 'red' | 'yellow' | 'green';
}

const StatCard: React.FC<StatCardProps> = ({ label, value, color }) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-800',
    gray: 'bg-gray-100 text-gray-800',
    purple: 'bg-purple-100 text-purple-800',
    red: 'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    green: 'bg-green-100 text-green-800',
  };

  return (
    <div className={`${colorClasses[color]} p-3 rounded-lg`}>
      <div className="text-xs text-opacity-75 mb-1">{label}</div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  );
};

// ============ HELPER FUNCTIONS ============

function getSignalIcon(signalType: string): string {
  const icons: Record<string, string> = {
    activity_deviation: '🏃',
    bathroom_duration_change: '🚿',
    night_activity_change: '🌙',
    sleep_pattern_change: '😴',
  };
  return icons[signalType] || '📊';
}

function getSignalLabel(signalType: string): string {
  const labels: Record<string, string> = {
    activity_deviation: '活动水平',
    bathroom_duration_change: '浴室停留时长',
    night_activity_change: '夜间活动',
    sleep_pattern_change: '睡眠模式',
  };
  return labels[signalType] || '个性化信号';
}

export default EnhancedStatusView;
