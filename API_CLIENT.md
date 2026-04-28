# API 客户端层架构说明

## 概述

**API 客户端层** 是前端与数据源的抽象接口，使得前端代码无需关心数据来自何处（mock 或真实 API）。

```
页面组件
    ↓
useEffect 调用 apiClient.getBehaviorEvents()
    ↓
API 客户端（当前返回 mock 数据）
    ↓
StatusViewModel 生成
    ↓
页面展示
    ↓
用户

---未来切换到真实后端时---
只需修改 apiClient.ts 中的实现
页面代码完全不变
```

---

## 为什么需要 API 客户端层？

### 问题：没有 API 客户端层

```typescript
// 页面直接依赖 mock 数据
import { mockBehaviorEvents, mockDailySummaryInput } from '@/data/mockData';

const events = mockBehaviorEvents;
const summary = mockDailySummaryInput;
```

**问题**：
- 页面与数据源紧密耦合
- 无法处理加载状态
- 无法处理错误状态
- 切换到真实 API 需要改页面代码

### 解决：有 API 客户端层

```typescript
// 页面通过 apiClient 获取数据
const events = await apiClient.getBehaviorEvents(homeId);
const summary = await apiClient.getDailySummary(homeId);
```

**优势**：
- 页面与数据源解耦
- 可以处理加载和错误状态
- 切换数据源只需改 apiClient.ts
- 易于添加拦截器、日志等功能

---

## 文件结构

```
src/
├── types/
│   └── api.ts                      ✨ 新增 - API 类型定义
│
├── lib/
│   └── apiClient.ts                ✨ 新增 - API 客户端实现
│
└── components/
    └── StatusDashboard.tsx         ✏️ 改造 - 通过 apiClient 获取数据
```

---

## API 客户端接口

### `getBehaviorEvents(homeId: string)`

获取行为事件列表。

```typescript
// 使用
const events = await apiClient.getBehaviorEvents('home-001');

// 返回值
BehaviorEvent[] = [
  { id: 'event-001', event_type: 'wake_up', risk_level: 'normal', ... },
  { id: 'event-002', event_type: 'bathroom_long_stay', risk_level: 'attention', ... },
  // ...
]
```

**未来真实 API 对应**：
```
GET /api/homes/{homeId}/behavior-events
```

---

### `getDailySummary(homeId: string)`

获取今日摘要数据。

```typescript
// 使用
const summary = await apiClient.getDailySummary('home-001');

// 返回值
DailyBehaviorSummaryInput = {
  wake_time: '07:30',
  total_active_minutes: 180,
  bathroom_count: 2,
  longest_bathroom_minutes: 25,
  night_wake_count: 0,
  alerts_count: 1,
  highest_risk: 'attention'
}
```

**未来真实 API 对应**：
```
GET /api/homes/{homeId}/daily-summary
```

---

### `submitFeedback(homeId, alertId, action, notes?)`

提交用户反馈。

```typescript
// 使用
await apiClient.submitFeedback(
  'home-001',
  'alert-bathroom-long',
  'confirmed',
  '老人确认无事'
);

// 返回值
SubmitFeedbackResponse = {
  success: true,
  message: '反馈已提交：confirmed'
}
```

**支持的操作**：
- `'confirmed'` - 已确认正常
- `'need_help'` - 需要帮助
- `'dismiss'` - 忽略提醒

**未来真实 API 对应**：
```
POST /api/homes/{homeId}/feedback
Body: {
  alert_id: string,
  action: 'confirmed' | 'need_help' | 'dismiss',
  timestamp: ISO 8601,
  notes?: string
}
```

---

## 使用示例

### 在页面中使用

```typescript
'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/apiClient';
import { generateStatusViewModel } from '@/lib/statusEngine';

export default function StatusDashboard() {
  const [viewModel, setViewModel] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        
        // 通过 API 客户端获取数据
        const events = await apiClient.getBehaviorEvents('home-001');
        const summary = await apiClient.getDailySummary('home-001');
        
        // 生成视图模型
        const model = generateStatusViewModel(events, summary);
        setViewModel(model);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // 显示加载状态
  if (isLoading) {
    return <div>正在加载老人状态…</div>;
  }

  // 显示错误状态
  if (error) {
    return <div>状态加载失败：{error.message}</div>;
  }

  // 显示正常状态
  return <div>{viewModel.headline}</div>;
}
```

---

## 切换数据源

### 当前状态：使用 Mock 数据

```typescript
// src/lib/apiClient.ts
const apiClient = new ApiClient({
  enableMockData: true,  // ← 启用 mock 数据
});
```

### 切换到真实 API：3 步

#### 第 1 步：修改配置

```typescript
// src/lib/apiClient.ts
const apiClient = new ApiClient({
  baseUrl: 'https://api.example.com',
  enableMockData: false,  // ← 禁用 mock 数据
});
```

#### 第 2 步：实现真实请求

```typescript
// src/lib/apiClient.ts
async getBehaviorEvents(homeId: string): Promise<BehaviorEvent[]> {
  try {
    // 移除 mock 数据返回，改为真实请求
    const response = await fetch(
      `${this.baseUrl}/homes/${homeId}/behavior-events`
    );
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    return data.data.events;  // 根据实际 API 响应格式调整
  } catch (error) {
    throw this.handleError(error, 'Failed to fetch behavior events');
  }
}
```

#### 第 3 步：页面代码无需改动

```typescript
// 页面代码完全不变
const events = await apiClient.getBehaviorEvents('home-001');
// 现在会自动使用真实 API
```

---

## 加载和错误状态

### 加载状态

```typescript
if (isLoading) {
  return (
    <div className="flex items-center justify-center">
      <div className="spinner"></div>
      <p>正在加载老人状态…</p>
    </div>
  );
}
```

### 错误状态

```typescript
if (error) {
  return (
    <div className="error-container">
      <h1>状态加载失败</h1>
      <p>{error.message}</p>
      <button onClick={() => window.location.reload()}>
        重新加载
      </button>
    </div>
  );
}
```

---

## 错误处理

### API 错误类型

```typescript
// ApiRequestError
{
  code: 500,                                    // 错误代码
  message: "Failed to fetch behavior events",   // 错误信息
  timestamp: "2026-04-25T10:30:45.123Z"         // 发生时间
}
```

### 处理错误

```typescript
try {
  const events = await apiClient.getBehaviorEvents('home-001');
} catch (err) {
  if (err.code === 401) {
    // 未授权，需要重新登录
  } else if (err.code === 404) {
    // 找不到数据
  } else if (err.code === 500) {
    // 服务器错误
  }
}
```

---

## 调试和日志

### 打开控制台查看日志

```javascript
// 浏览器 Console 中
// 看到的日志
// 提交反馈: { alert_id: "...", action: "confirmed", ... }
// API 健康检查：通过
```

### 检查 API 客户端配置

```javascript
// 浏览器 Console 中
import { apiClient } from '@/lib/apiClient';
console.log(apiClient.getConfig());

// 输出
// {
//   baseUrl: "http://localhost:3000/api",
//   timeout: 5000,
//   enableMockData: true
// }
```

### 动态切换配置

```javascript
// 浏览器 Console 中
import { apiClient } from '@/lib/apiClient';

// 禁用 mock 数据
apiClient.setConfig({ enableMockData: false });

// 修改 base URL
apiClient.setConfig({ 
  baseUrl: 'https://api.example.com',
  enableMockData: false 
});
```

---

## 模拟网络延迟

API 客户端会模拟 300ms 的网络延迟，这样可以：

1. **测试加载状态** - 看到加载动画
2. **测试错误处理** - 有时间观察错误界面
3. **更接近真实场景** - 真实 API 也会有延迟

如果想修改延迟时间：

```typescript
// src/lib/apiClient.ts
private delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// 在需要的地方改成：
await this.delay(1000);  // 改成 1 秒
```

---

## 测试 API 客户端

### 单元测试示例

```typescript
import { createApiClient } from '@/lib/apiClient';

test('getBehaviorEvents 返回正确数据', async () => {
  const client = createApiClient({ enableMockData: true });
  const events = await client.getBehaviorEvents('home-001');
  
  expect(events.length).toBeGreaterThan(0);
  expect(events[0].event_type).toBeDefined();
});

test('submitFeedback 成功提交', async () => {
  const client = createApiClient({ enableMockData: true });
  const result = await client.submitFeedback(
    'home-001',
    'alert-1',
    'confirmed'
  );
  
  expect(result.success).toBe(true);
});
```

---

## 扩展功能（未来可以添加）

### 1. 请求拦截器

```typescript
// 在所有请求前添加认证 token
async getBehaviorEvents(homeId: string) {
  const token = localStorage.getItem('auth_token');
  const headers = {
    'Authorization': `Bearer ${token}`
  };
  // ...
}
```

### 2. 响应缓存

```typescript
private cache = new Map();

async getBehaviorEvents(homeId: string) {
  const cacheKey = `events-${homeId}`;
  
  if (this.cache.has(cacheKey)) {
    return this.cache.get(cacheKey);
  }
  
  const events = await this.fetchEvents(homeId);
  this.cache.set(cacheKey, events);
  return events;
}
```

### 3. 重试机制

```typescript
async getBehaviorEvents(homeId: string, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await this.fetchEvents(homeId);
    } catch (err) {
      if (i === retries - 1) throw err;
      await this.delay(Math.pow(2, i) * 1000);  // 指数退避
    }
  }
}
```

### 4. 请求超时

```typescript
async getBehaviorEvents(homeId: string) {
  return Promise.race([
    this.fetchEvents(homeId),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Timeout')), this.timeout)
    )
  ]);
}
```

---

## 文件对比

### 改造前后对比

**改造前（紧耦合）**：
```typescript
import { mockBehaviorEvents, mockDailySummaryInput } from '@/data/mockData';

export default function StatusDashboard() {
  const viewModel = generateStatusViewModel(
    mockBehaviorEvents,
    mockDailySummaryInput
  );
  // ...
}
```

**改造后（解耦）**：
```typescript
import { apiClient } from '@/lib/apiClient';

export default function StatusDashboard() {
  const [viewModel, setViewModel] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const events = await apiClient.getBehaviorEvents('home-001');
        const summary = await apiClient.getDailySummary('home-001');
        const model = generateStatusViewModel(events, summary);
        setViewModel(model);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, []);
  // ...
}
```

**改变**：
- 添加了加载状态处理
- 添加了错误状态处理
- 数据通过 API 客户端获取
- 页面更加健壮

---

## 总结

✅ **API 客户端层的优势**：
- 解耦页面和数据源
- 支持 mock 和真实 API 无缝切换
- 可以处理加载和错误状态
- 易于添加拦截器、缓存等功能
- 易于测试

✅ **切换到真实 API**：
- 只需修改 apiClient.ts
- 页面代码无需改动
- 类型完全兼容

✅ **生产级别**：
- 完整的错误处理
- 模拟网络延迟
- 日志记录
- 健康检查
- 可扩展的配置

---

**这就是一个标准的前端 API 层设计！** 🚀
