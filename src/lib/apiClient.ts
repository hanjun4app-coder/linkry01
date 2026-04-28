import {
  BehaviorEvent,
  DailyBehaviorSummaryInput,
} from '@/types/behavior';
import {
  ApiClientConfig,
  GetBehaviorEventsResponse,
  GetDailySummaryResponse,
  SubmitFeedbackRequest,
  SubmitFeedbackResponse,
  ApiRequestError,
} from '@/types/api';
import {
  mockBehaviorEvents,
  mockDailySummaryInput,
} from '@/data/mockData';

/**
 * API 客户端
 * 目前返回 mock 数据，未来可接入真实后端
 *
 * 使用方式：
 * const client = new ApiClient();
 * const events = await client.getBehaviorEvents('home-001');
 */
export class ApiClient {
  private baseUrl: string;
  private timeout: number;
  private enableMockData: boolean;

  constructor(config: ApiClientConfig = {}) {
    this.baseUrl = config.baseUrl || 'http://localhost:3000/api';
    this.timeout = config.timeout || 5000;
    this.enableMockData = config.enableMockData !== false; // 默认启用 mock
  }

  /**
   * 获取行为事件列表
   *
   * @param homeId - 家庭 ID
   * @returns 行为事件列表
   * @throws ApiRequestError 如果请求失败
   */
  async getBehaviorEvents(homeId: string): Promise<BehaviorEvent[]> {
    try {
      // 目前返回 mock 数据，模拟网络延迟
      await this.delay(300);

      if (this.enableMockData) {
        return mockBehaviorEvents;
      }

      // 未来接入真实后端时，改为这样：
      // const response = await fetch(`${this.baseUrl}/homes/${homeId}/behavior-events`);
      // const data = await response.json();
      // return data.data.events;

      throw new Error('Mock 数据已禁用');
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch behavior events');
    }
  }

  /**
   * 获取今日摘要
   *
   * @param homeId - 家庭 ID
   * @returns 今日摘要数据
   * @throws ApiRequestError 如果请求失败
   */
  async getDailySummary(homeId: string): Promise<DailyBehaviorSummaryInput> {
    try {
      // 目前返回 mock 数据，模拟网络延迟
      await this.delay(300);

      if (this.enableMockData) {
        return mockDailySummaryInput;
      }

      // 未来接入真实后端时，改为这样：
      // const response = await fetch(`${this.baseUrl}/homes/${homeId}/daily-summary`);
      // const data = await response.json();
      // return data.data.summary;

      throw new Error('Mock 数据已禁用');
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch daily summary');
    }
  }

  /**
   * 提交用户反馈
   *
   * @param homeId - 家庭 ID
   * @param alertId - 异常提醒 ID
   * @param action - 用户操作（confirmed/need_help/dismiss）
   * @param notes - 可选的备注
   * @returns 提交结果
   * @throws ApiRequestError 如果请求失败
   */
  async submitFeedback(
    homeId: string,
    alertId: string,
    action: 'confirmed' | 'need_help' | 'dismiss',
    notes?: string
  ): Promise<SubmitFeedbackResponse> {
    try {
      // 目前返回 mock 响应，模拟网络延迟
      await this.delay(200);

      const request: SubmitFeedbackRequest = {
        alert_id: alertId,
        action,
        timestamp: new Date().toISOString(),
        notes,
      };

      // 打印日志（便于调试）
      console.log('提交反馈:', request);

      if (this.enableMockData) {
        return {
          success: true,
          message: `反馈已提交：${action}`,
        };
      }

      // 未来接入真实后端时，改为这样：
      // const response = await fetch(
      //   `${this.baseUrl}/homes/${homeId}/feedback`,
      //   {
      //     method: 'POST',
      //     headers: { 'Content-Type': 'application/json' },
      //     body: JSON.stringify(request),
      //   }
      // );
      // const data = await response.json();
      // return data.data;

      throw new Error('Mock 数据已禁用');
    } catch (error) {
      throw this.handleError(error, 'Failed to submit feedback');
    }
  }

  /**
   * 获取老人信息
   *
   * @param homeId - 家庭 ID
   * @returns 老人基本信息
   */
  async getElderlyInfo(homeId: string) {
    try {
      await this.delay(200);

      if (this.enableMockData) {
        return {
          id: 'elderly-001',
          name: '王奶奶',
          home_id: homeId,
          age: 78,
        };
      }

      throw new Error('Mock 数据已禁用');
    } catch (error) {
      throw this.handleError(error, 'Failed to fetch elderly info');
    }
  }

  /**
   * 健康检查
   * 用于验证 API 连接
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.delay(100);
      console.log('API 健康检查：通过');
      return true;
    } catch {
      console.error('API 健康检查：失败');
      return false;
    }
  }

  /**
   * 模拟网络延迟
   * @private
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * 处理错误
   * @private
   */
  private handleError(error: unknown, defaultMessage: string): ApiRequestError {
    let message = defaultMessage;
    let code = 500;

    if (error instanceof Error) {
      message = error.message;
    } else if (typeof error === 'string') {
      message = error;
    }

    const apiError: ApiRequestError = {
      code,
      message,
      timestamp: new Date().toISOString(),
    };

    console.error('API 错误:', apiError);
    return apiError;
  }

  /**
   * 更新配置
   */
  setConfig(config: Partial<ApiClientConfig>) {
    if (config.baseUrl) {
      this.baseUrl = config.baseUrl;
    }
    if (config.timeout) {
      this.timeout = config.timeout;
    }
    if (config.enableMockData !== undefined) {
      this.enableMockData = config.enableMockData;
    }
  }

  /**
   * 获取当前配置
   */
  getConfig() {
    return {
      baseUrl: this.baseUrl,
      timeout: this.timeout,
      enableMockData: this.enableMockData,
    };
  }
}

/**
 * 创建默认的 API 客户端实例
 * 这样应用中只需要一个单例实例
 */
export const apiClient = new ApiClient({
  enableMockData: true, // 开发环境使用 mock 数据
});

// 为了方便测试，导出工厂函数
export function createApiClient(config?: ApiClientConfig) {
  return new ApiClient(config);
}
