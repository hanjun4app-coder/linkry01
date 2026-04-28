import { BehaviorEvent, DailyBehaviorSummaryInput } from './behavior';

/**
 * API 响应类型
 */

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface ApiError {
  code: number;
  message: string;
}

/**
 * 获取行为事件的响应
 */
export interface GetBehaviorEventsResponse {
  events: BehaviorEvent[];
  home_id: string;
  timestamp: string;
}

/**
 * 获取今日摘要的响应
 */
export interface GetDailySummaryResponse {
  summary: DailyBehaviorSummaryInput;
  home_id: string;
  date: string;
}

/**
 * 反馈提交的请求和响应
 */
export interface SubmitFeedbackRequest {
  alert_id: string;
  action: 'confirmed' | 'need_help' | 'dismiss'; // 已确认 | 需要帮助 | 忽略
  timestamp: string;
  notes?: string;
}

export interface SubmitFeedbackResponse {
  success: boolean;
  message: string;
}

/**
 * API 客户端配置
 */
export interface ApiClientConfig {
  baseUrl?: string;
  timeout?: number;
  enableMockData?: boolean; // 是否启用 mock 数据
}

/**
 * API 状态类型
 */
export type ApiRequestState = 'idle' | 'loading' | 'success' | 'error';

export interface ApiRequestError {
  code: number;
  message: string;
  timestamp: string;
}
