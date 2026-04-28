/**
 * Alert 管道（Pipeline）系统
 * 消费级产品的核心去重和验证逻辑
 *
 * 处理流程：
 * 1. 事件输入 → Debounce（等待60秒确认）
 * 2. Debounce 通过 → 多信号确认（需≥2个条件除非high risk）
 * 3. 确认通过 → Cooldown 检查（30分钟内同事件不重复）
 * 4. Cooldown 通过 → Quiet Mode 检查（夜间非high risk不推送）
 * 5. 最终通过 → 推送给用户
 */

import { BehaviorEvent, RiskLevel } from '@/types/behavior';
import {
  ALERT_DEDUP_RULES,
  QUIET_MODE_CONFIG,
  isInQuietMode,
} from '@/config/defaultRules';

/**
 * Alert 记录，用于 cooldown 去重
 */
interface AlertRecord {
  event_type: string;
  zone?: string;
  timestamp: number; // 毫秒时间戳
  risk_level: RiskLevel;
}

/**
 * Debounce 记录，用于等待异常持续确认
 */
interface DebounceRecord {
  event_type: string;
  zone?: string;
  start_time: number; // 毫秒时间戳
  signal_count: number; // 累计的确认次数
}

/**
 * Alert 管道管理器
 * 维护全局状态，处理所有去重和验证逻辑
 */
class AlertPipeline {
  // Cooldown 记录库：保存最近30分钟内的 alert
  private alertHistory: AlertRecord[] = [];

  // Debounce 记录库：保存正在等待确认的事件
  private debounceMap: Map<string, DebounceRecord> = new Map();

  constructor() {
    // 定期清理过期记录（可选，实际使用中应由后端管理）
    setInterval(() => this.cleanupExpiredRecords(), 60000);
  }

  /**
   * 生成事件的唯一标识符，用于去重
   */
  private getEventKey(event: BehaviorEvent): string {
    return `${event.event_type}:${event.zone || 'unknown'}`;
  }

  /**
   * 检查是否在 cooldown 期间
   * 返回 true 表示该 alert 应该被抑制（已在cooldown）
   */
  private isInCooldown(event: BehaviorEvent): boolean {
    const key = this.getEventKey(event);
    const now = Date.now();
    const cooldownMs = ALERT_DEDUP_RULES.cooldown_minutes * 60 * 1000;

    for (const record of this.alertHistory) {
      if (
        `${record.event_type}:${record.zone || 'unknown'}` === key &&
        now - record.timestamp < cooldownMs
      ) {
        return true; // 在 cooldown 期间
      }
    }

    return false;
  }

  /**
   * 检查是否需要 debounce（等待异常持续确认）
   * 返回 true 表示需要继续等待
   */
  private needsDebounce(
    event: BehaviorEvent,
    evidenceCount: number
  ): boolean {
    // High risk 事件不需要 debounce
    if (event.risk_level === 'high') {
      return false;
    }

    // 如果只有单一信号，必须等待 debounce 期间内再出现确认
    if (evidenceCount < ALERT_DEDUP_RULES.multi_signal_min_count) {
      return true;
    }

    return false;
  }

  /**
   * 更新或创建 debounce 记录
   */
  private updateDebounce(event: BehaviorEvent): DebounceRecord {
    const key = this.getEventKey(event);
    const existing = this.debounceMap.get(key);

    if (existing) {
      // 更新现有记录：增加信号计数
      existing.signal_count++;
      return existing;
    } else {
      // 创建新记录
      const record: DebounceRecord = {
        event_type: event.event_type,
        zone: event.zone,
        start_time: Date.now(),
        signal_count: 1,
      };
      this.debounceMap.set(key, record);
      return record;
    }
  }

  /**
   * 检查 debounce 是否已完成（达到时间阈值）
   */
  private isDebounceComplete(record: DebounceRecord): boolean {
    const debounceMs = ALERT_DEDUP_RULES.debounce_seconds * 1000;
    return Date.now() - record.start_time >= debounceMs;
  }

  /**
   * 检查是否在 Quiet Mode 应该被抑制
   * 返回 true 表示应该被抑制
   */
  private shouldSuppressInQuietMode(event: BehaviorEvent): boolean {
    if (!isInQuietMode()) {
      return false; // 不在 quiet mode，不抑制
    }

    // 在 quiet mode 中，只有 high risk 才推送
    return event.risk_level !== 'high';
  }

  /**
   * 记录一个已通过的 alert（用于后续 cooldown）
   */
  private recordAlert(event: BehaviorEvent): void {
    const record: AlertRecord = {
      event_type: event.event_type,
      zone: event.zone,
      timestamp: Date.now(),
      risk_level: event.risk_level,
    };

    this.alertHistory.push(record);
  }

  /**
   * 清理过期的记录
   * 删除超过 cooldown 时间的记录
   */
  private cleanupExpiredRecords(): void {
    const now = Date.now();
    const cooldownMs = ALERT_DEDUP_RULES.cooldown_minutes * 60 * 1000;
    const debounceMs = ALERT_DEDUP_RULES.debounce_seconds * 1000;

    // 清理 alertHistory
    this.alertHistory = this.alertHistory.filter(
      (record) => now - record.timestamp < cooldownMs
    );

    // 清理 debounceMap
    for (const [key, record] of this.debounceMap.entries()) {
      if (now - record.start_time > debounceMs) {
        this.debounceMap.delete(key);
      }
    }
  }

  /**
   * 主处理函数：判断 alert 是否应该推送
   *
   * @param event - 行为事件
   * @param evidenceCount - 证据信号数量（例如 evidence_sources 的长度）
   * @param signalSources - 信号来源（用于调试和可解释性）
   * @returns 是否应该推送 alert，以及推送原因
   */
  public shouldAlert(
    event: BehaviorEvent,
    evidenceCount: number = 1,
    signalSources: string[] = []
  ): {
    should_alert: boolean;
    reason: string;
    suppression_reason?: string;
  } {
    // 检查1：多信号确认（除非 high risk）
    if (event.risk_level !== 'high') {
      if (evidenceCount < ALERT_DEDUP_RULES.multi_signal_min_count) {
        return {
          should_alert: false,
          reason: 'insufficient_signals',
          suppression_reason: `只有 ${evidenceCount} 个信号，需要至少 ${ALERT_DEDUP_RULES.multi_signal_min_count} 个`,
        };
      }
    }

    // 检查2：Debounce（异常必须持续≥60秒）
    const debounceRecord = this.updateDebounce(event);
    if (this.needsDebounce(event, evidenceCount)) {
      if (!this.isDebounceComplete(debounceRecord)) {
        const elapsed = Math.floor(
          (Date.now() - debounceRecord.start_time) / 1000
        );
        return {
          should_alert: false,
          reason: 'debounce_pending',
          suppression_reason: `异常需要持续确认，已确认 ${elapsed}/${ALERT_DEDUP_RULES.debounce_seconds} 秒`,
        };
      }
    }

    // 检查3：Cooldown（30分钟内不重复）
    if (this.isInCooldown(event)) {
      return {
        should_alert: false,
        reason: 'cooldown_active',
        suppression_reason: '此事件在最近 30 分钟内已推送过，暂不重复推送',
      };
    }

    // 检查4：Quiet Mode（夜间策略）
    if (this.shouldSuppressInQuietMode(event)) {
      return {
        should_alert: false,
        reason: 'quiet_mode_active',
        suppression_reason: '当前处于夜间安静模式，非紧急事件不推送',
      };
    }

    // 所有检查通过，可以推送
    this.recordAlert(event);
    this.debounceMap.delete(this.getEventKey(event)); // 清理对应的 debounce 记录

    return {
      should_alert: true,
      reason: 'all_checks_passed',
    };
  }

  /**
   * 获取当前系统状态（用于调试）
   */
  public getSystemStatus() {
    return {
      alert_history_count: this.alertHistory.length,
      debounce_active_count: this.debounceMap.size,
      quiet_mode_active: isInQuietMode(),
      debounce_records: Array.from(this.debounceMap.values()).map((r) => ({
        event_type: r.event_type,
        zone: r.zone,
        signal_count: r.signal_count,
        elapsed_seconds: Math.floor((Date.now() - r.start_time) / 1000),
      })),
    };
  }
}

// 全局 alert pipeline 实例
export const globalAlertPipeline = new AlertPipeline();

/**
 * 便捷函数：判断 alert 是否应该推送
 * 用于在 statusEngine 中调用
 */
export function shouldPushAlert(
  event: BehaviorEvent,
  evidenceCount: number = 1
): boolean {
  const result = globalAlertPipeline.shouldAlert(event, evidenceCount);
  return result.should_alert;
}

/**
 * 便捷函数：获取 alert 被抑制的原因（用于调试和日志）
 */
export function getAlertSuppressionReason(
  event: BehaviorEvent,
  evidenceCount: number = 1
): string | undefined {
  const result = globalAlertPipeline.shouldAlert(event, evidenceCount);
  return result.suppression_reason;
}
