'use client';

import { useState, useEffect } from 'react';
import { BehaviorEvent, DailyBehaviorSummaryInput } from '@/types/behavior';
import { StatusViewModel } from '@/types/status';
import { ApiRequestError } from '@/types/api';
import { apiClient } from '@/lib/apiClient';
import {
  generateStatusViewModel,
  getStatusBgColor,
  getStatusTextColor,
  getStatusBadgeColor,
  getStatusBadgeText,
  hasAlert,
} from '@/lib/statusEngine';

const MOCK_HOME_ID = 'home-001'; // Mock 家庭 ID

export default function StatusDashboard() {
  // 数据状态
  const [behaviorEvents, setBehaviorEvents] = useState<BehaviorEvent[]>([]);
  const [dailySummary, setDailySummary] = useState<DailyBehaviorSummaryInput | null>(null);
  const [elderlyInfo, setElderlyInfo] = useState<{ name: string } | null>(null);

  // 视图状态
  const [viewModel, setViewModel] = useState<StatusViewModel | null>(null);

  // 加载和错误状态
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiRequestError | null>(null);

  // 用户交互状态
  const [isConfirmed, setIsConfirmed] = useState(false);

  /**
   * 初始化数据
   */
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // 并行获取所有数据
        const [events, summary, elderly] = await Promise.all([
          apiClient.getBehaviorEvents(MOCK_HOME_ID),
          apiClient.getDailySummary(MOCK_HOME_ID),
          apiClient.getElderlyInfo(MOCK_HOME_ID),
        ]);

        // 设置数据
        setBehaviorEvents(events);
        setDailySummary(summary);
        setElderlyInfo(elderly);

        // 生成视图模型
        if (summary) {
          const model = generateStatusViewModel(events, summary);
          setViewModel(model);
        }
      } catch (err) {
        // 处理错误
        if (err && typeof err === 'object' && 'message' in err) {
          setError(err as ApiRequestError);
        } else {
          setError({
            code: 500,
            message: '未知错误',
            timestamp: new Date().toISOString(),
          });
        }
        console.error('数据加载失败:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  /**
   * 处理确认按钮
   */
  const handleConfirm = async () => {
    if (!viewModel?.primary_alert) {
      console.log('已确认正常 - 时间:', new Date().toLocaleString());
    } else {
      try {
        // 提交反馈（如果有异常提醒）
        await apiClient.submitFeedback(
          MOCK_HOME_ID,
          viewModel.primary_alert.event_id || 'unknown-alert',
          'confirmed'
        );
      } catch (err) {
        console.error('提交反馈失败:', err);
      }
    }

    // 显示确认反馈
    setIsConfirmed(true);
    setTimeout(() => setIsConfirmed(false), 2000);
  };

  /**
   * 处理需要帮助按钮
   */
  const handleNeedHelp = async () => {
    if (viewModel?.primary_alert) {
      try {
        await apiClient.submitFeedback(
          MOCK_HOME_ID,
          viewModel.primary_alert.event_id || 'unknown-alert',
          'need_help',
          '家属表示需要帮助'
        );
      } catch (err) {
        console.error('提交反馈失败:', err);
      }
    }
    console.log('需要帮助 - 时间:', new Date().toLocaleString());
  };

  /**
   * 加载状态 - 显示加载提示
   */
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-4 md:p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block">
            <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          </div>
          <p className="text-gray-700 text-lg font-semibold">正在加载老人状态…</p>
          <p className="text-gray-500 text-sm mt-2">请稍候</p>
        </div>
      </div>
    );
  }

  /**
   * 错误状态 - 显示错误提示
   */
  if (error || !viewModel) {
    return (
      <div className="min-h-screen bg-red-50 p-4 md:p-6 flex items-center justify-center">
        <div className="bg-white border-2 border-red-200 rounded-xl p-8 max-w-md text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="text-xl font-bold text-red-700 mb-2">状态加载失败</h1>
          <p className="text-gray-600 mb-4">
            {error?.message || '无法获取老人状态，请检查网络连接。'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-semibold transition-all"
          >
            重新加载
          </button>
          {error && (
            <p className="text-gray-400 text-xs mt-4">
              错误代码: {error.code}
            </p>
          )}
        </div>
      </div>
    );
  }

  /**
   * 正常状态 - 显示完整的状态仪表板
   */
  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-2xl mx-auto">
        {/* 标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800">
            {elderlyInfo?.name || '老人'}
          </h1>
          <p className="text-gray-500 text-sm mt-1">家属监护面板</p>
        </div>

        {/* 主状态卡片 - 最重要 */}
        <div
          className={`border-2 rounded-2xl p-8 mb-6 ${getStatusBgColor(
            viewModel.overall_status
          )}`}
        >
          <div className="text-center">
            <p className="text-gray-600 text-lg mb-2">今日状态</p>
            <div
              className={`text-5xl md:text-6xl font-bold mb-4 ${getStatusTextColor(
                viewModel.overall_status
              )}`}
            >
              {viewModel.headline}
            </div>
            <div
              className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${getStatusBadgeColor(
                viewModel.overall_status
              )}`}
            >
              {getStatusBadgeText(viewModel.overall_status)}
            </div>
          </div>
        </div>

        {/* 今日摘要 */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <p className="text-gray-700 text-base mb-4">
            {viewModel.daily_summary.summary}
          </p>
          <div className="space-y-2 mb-4">
            {viewModel.daily_summary.key_points.map((point, index) => (
              <div key={index} className="flex items-start gap-3">
                <span className="text-blue-600 font-bold mt-0.5">•</span>
                <p className="text-gray-700 text-sm">{point}</p>
              </div>
            ))}
          </div>
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900">
              <strong>建议：</strong> {viewModel.daily_summary.suggestion}
            </p>
          </div>
        </div>

        {/* 当前状态卡片 */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="text-gray-500 text-sm font-semibold mb-2">当前状态</h2>
          <p className="text-2xl font-semibold text-gray-800">
            {viewModel.current_state.label}
          </p>
          <p className="text-gray-500 text-sm mt-2">
            {viewModel.current_state.summary}
          </p>
        </div>

        {/* 最近行为卡片 */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <h2 className="text-gray-500 text-sm font-semibold mb-4">
            今日行为记录
          </h2>
          <div className="space-y-3">
            {behaviorEvents.map((event) => {
              // 使用 viewModel 中的文案
              const behaviorText = viewModel.recent_behavior_texts.find(
                (text) => text.display_level === event.risk_level
              ) || {
                title: event.event_type,
                summary: '活动记录',
              };

              return (
                <div
                  key={event.id}
                  className="flex items-start justify-between pb-3 border-b border-gray-100 last:border-b-0"
                >
                  <div className="flex-1">
                    <p className="text-gray-700 font-medium">
                      {behaviorText.title}
                    </p>
                    <p className="text-gray-500 text-sm mt-1">
                      {behaviorText.summary}
                    </p>
                  </div>
                  <span className="text-gray-500 text-sm bg-gray-100 px-3 py-1 rounded-full whitespace-nowrap ml-3">
                    {event.start_time
                      ? new Date(event.start_time).toLocaleTimeString('zh-CN', {
                          hour: '2-digit',
                          minute: '2-digit',
                          hour12: false,
                        })
                      : '--:--'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* 异常提醒卡片 */}
        {hasAlert(viewModel) && viewModel.primary_alert && (
          <div className="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-6 mb-6">
            <h2 className="text-lg font-bold text-yellow-800 mb-3">
              {viewModel.primary_alert.title}
            </h2>
            <div className="space-y-2 text-yellow-900">
              <p className="text-base">{viewModel.primary_alert.summary}</p>
              <p className="text-sm">{viewModel.primary_alert.detail}</p>
            </div>
            <div className="mt-4 p-3 bg-white border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-900">
                💡 <strong>建议：</strong> {viewModel.primary_alert.suggestion}
              </p>
            </div>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-3">
          <button
            onClick={handleConfirm}
            className={`flex-1 py-4 px-6 rounded-xl text-lg font-semibold transition-all duration-300 ${
              isConfirmed
                ? 'bg-green-600 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white active:scale-95'
            }`}
          >
            {isConfirmed ? '✓ 已确认正常' : '确认正常'}
          </button>
          <button
            onClick={handleNeedHelp}
            className="py-4 px-6 rounded-xl text-lg font-semibold bg-gray-200 text-gray-800 hover:bg-gray-300 transition-all duration-300 active:scale-95"
          >
            需要帮助
          </button>
        </div>

        {/* 底部元数据 */}
        <div className="mt-8 text-center text-gray-500 text-xs">
          <p>最后更新：{viewModel.metadata.last_update_time}</p>
          <p className="mt-1 text-gray-400">
            事件总数: {viewModel.metadata.total_events} | 异常提醒:{' '}
            {viewModel.metadata.alert_count}
          </p>
        </div>
      </div>
    </div>
  );
}
