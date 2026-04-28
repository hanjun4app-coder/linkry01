# API 客户端快速指南

## 新增内容

### 1. `src/types/api.ts` - API 类型定义
定义了所有 API 相关的类型，包括请求、响应、错误等。

### 2. `src/lib/apiClient.ts` - API 客户端
单例实例 `apiClient`，提供 3 个核心方法：
- `getBehaviorEvents(homeId)` - 获取行为事件
- `getDailySummary(homeId)` - 获取今日摘要
- `submitFeedback(homeId, alertId, action)` - 提交反馈

### 3. `src/components/StatusDashboard.tsx` 改造
- 改为通过 `apiClient` 获取数据
- 添加 `loading` 状态（显示"正在加载…"）
- 添加 `error` 状态（显示"加载失败"）
- 使用 `useEffect` 初始化数据

---

## 数据流

```
┌─────────────────────────┐
│ StatusDashboard (页面)  │
└────────────┬────────────┘
             │ useEffect
             ↓
┌─────────────────────────┐
│ apiClient               │ ← 唯一的数据源
│ (当前返回 mock 数据)    │
└────────────┬────────────┘
             │ 返回数据
             ↓
┌─────────────────────────┐
│ generateStatusViewModel │ ← 生成视图模型
└────────────┬────────────┘
             │
             ↓
┌─────────────────────────┐
│ 页面展示 (loading/error │
│ /normal state)          │
└─────────────────────────┘
```

---

## 3 个核心 API 方法

### 获取行为事件
```typescript
const events = await apiClient.getBehaviorEvents('home-001');
// 返回 BehaviorEvent[]
```

### 获取今日摘要
```typescript
const summary = await apiClient.getDailySummary('home-001');
// 返回 DailyBehaviorSummaryInput
```

### 提交反馈
```typescript
await apiClient.submitFeedback(
  'home-001',           // homeId
  'alert-bathroom',     // alertId
  'confirmed',          // action: 'confirmed' | 'need_help' | 'dismiss'
  '老人确认无事'        // 可选的备注
);
// 返回 SubmitFeedbackResponse { success: true, message: '...' }
```

---

## 页面加载流程

```
页面挂载
    ↓
useEffect 触发
    ↓
setIsLoading(true)
显示："正在加载老人状态…"
    ↓
并行调用 3 个 API：
├─ getBehaviorEvents()
├─ getDailySummary()
└─ getElderlyInfo()
    ↓
生成 StatusViewModel
    ↓
setIsLoading(false)
显示正常页面
```

---

## 错误处理流程

```
API 调用发生错误
    ↓
catch 捕获异常
    ↓
setError(apiError)
    ↓
显示错误界面：
"状态加载失败"
"错误信息"
"重新加载"按钮
    ↓
用户点击"重新加载"
    ↓
window.location.reload()
```

---

## 页面状态机

```
[初始] 
   ↓
[加载中] → 显示旋转加载动画
   ↓
[成功] → 显示完整页面
   ↓
[用户交互] → 点击按钮提交反馈
   │
   └→ 反馈提交
       (不改变页面状态)
   
[初始] 
   ↓
[加载中] → 显示加载动画
   ↓
[失败] → 显示错误界面
   ↓
[用户点击重新加载]
   ↓
刷新整个页面
```

---

## 切换数据源：只需 2 步

### 当前：使用 Mock 数据
```typescript
// src/lib/apiClient.ts (第 ~160 行)
export const apiClient = new ApiClient({
  enableMockData: true,  // ← 启用 mock
});
```

### 切换到真实 API
```typescript
// 第 1 步：改配置
export const apiClient = new ApiClient({
  baseUrl: 'https://api.example.com',
  enableMockData: false,  // ← 禁用 mock
});

// 第 2 步：改实现
async getBehaviorEvents(homeId: string) {
  const response = await fetch(
    `${this.baseUrl}/homes/${homeId}/behavior-events`
  );
  const data = await response.json();
  return data.data.events;
}

// 页面代码完全不变！
```

---

## 加载状态 UI

页面显示：
```
┌─────────────────────────────┐
│                             │
│      ⟳ 旋转加载图标        │
│                             │
│    正在加载老人状态…        │
│         请稍候              │
│                             │
└─────────────────────────────┘
```

---

## 错误状态 UI

页面显示：
```
┌─────────────────────────────┐
│            ⚠️               │
│                             │
│       状态加载失败          │
│   [错误信息或网络提示]      │
│                             │
│    [重新加载按钮]           │
│                             │
│   错误代码: 500             │
└─────────────────────────────┘
```

---

## API 调用示例

### 在浏览器 Console 中测试

```javascript
// 导入 API 客户端
import { apiClient } from './src/lib/apiClient.js';

// 获取行为事件
const events = await apiClient.getBehaviorEvents('home-001');
console.log('事件数:', events.length);

// 获取今日摘要
const summary = await apiClient.getDailySummary('home-001');
console.log('最高风险:', summary.highest_risk);

// 提交反馈
const result = await apiClient.submitFeedback(
  'home-001',
  'alert-bathroom',
  'confirmed'
);
console.log('反馈结果:', result.message);
```

---

## 配置 API 客户端

### 在运行时修改配置

```typescript
import { apiClient } from '@/lib/apiClient';

// 查看当前配置
console.log(apiClient.getConfig());
// { baseUrl: "http://localhost:3000/api", timeout: 5000, enableMockData: true }

// 修改配置
apiClient.setConfig({
  baseUrl: 'https://api.example.com',
  enableMockData: false,
  timeout: 10000
});

// 再次查看
console.log(apiClient.getConfig());
```

---

## 关键代码片段

### 页面初始化（使用 apiClient）

```typescript
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
```

### 条件渲染

```typescript
// 加载中
if (isLoading) {
  return <LoadingScreen />;
}

// 出错
if (error || !viewModel) {
  return <ErrorScreen error={error} />;
}

// 正常
return <MainDashboard viewModel={viewModel} />;
```

---

## 调试技巧

### 1. 查看网络延迟

API 客户端默认延迟 300ms，可以看到加载状态。

### 2. 打印日志

所有 API 调用和错误都会打印到 Console。

### 3. 临时禁用 Mock

```javascript
// Console 中
import { apiClient } from './src/lib/apiClient.js';
apiClient.setConfig({ enableMockData: false });
// 之后调用会抛出错误，这样可以测试错误处理
```

### 4. 模拟慢网络

修改 `apiClient.ts` 中的延迟时间：
```typescript
// 改成 3 秒延迟
await this.delay(3000);
```

---

## 测试清单

- [ ] 页面正常加载（应该看到加载动画 ~300ms）
- [ ] 加载完成后显示老人状态
- [ ] 修改 mock 数据后，重新加载页面显示新数据
- [ ] 点击"确认正常"，Console 显示反馈日志
- [ ] 点击"需要帮助"，Console 显示反馈日志
- [ ] 临时禁用 mock 数据，观察错误界面
- [ ] 点击"重新加载"按钮，页面刷新

---

## 文件清单

**新增**：
- `src/types/api.ts` - API 类型
- `src/lib/apiClient.ts` - API 客户端

**改造**：
- `src/components/StatusDashboard.tsx` - 使用 apiClient

**配置无需改动**：
- `src/lib/statusEngine.ts` - 状态引擎（无改动）
- `src/lib/behaviorText.ts` - 文案生成（无改动）
- `src/data/mockData.ts` - Mock 数据（无改动）

---

## 架构升级总结

### 之前（直接使用 mock 数据）
```
StatusDashboard 
    ↓ import
mockData
```

### 现在（通过 API 客户端）
```
StatusDashboard 
    ↓ await
apiClient 
    ↓ 当前返回 mock 数据
    ↓ 未来可返回真实 API 数据
```

### 好处
✅ 页面与数据源解耦
✅ 支持加载和错误状态
✅ 未来无缝切换真实 API
✅ 可添加拦截器、缓存等功能

---

**现在你有了完整的前端数据接入层！** 🚀

---

## 快速命令

```bash
# 运行项目
npm run dev

# 查看 Console（F12）
# 观察 API 调用日志

# 修改 mock 数据
# 编辑 src/data/mockData.ts
# 刷新浏览器

# 测试错误状态
# Console: apiClient.setConfig({ enableMockData: false })
# 刷新页面，看错误界面
```

---

**祝使用愉快！** 👋
