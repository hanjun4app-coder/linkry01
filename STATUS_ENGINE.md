# Status Engine 架构说明

## 概述

**Status Engine** 是一个状态聚合层，将所有的业务逻辑从页面组件中分离出来。

```
原始数据层
    ↓
BehaviorEvent[] + DailyBehaviorSummaryInput
    ↓
       生成函数（文案层）
    ├── generateBehaviorText()
    └── generateDailySummaryText()
    ↓
       状态引擎（聚合层）
    └── generateStatusViewModel()
    ↓
StatusViewModel（页面只需要这个）
    ↓
页面组件（纯展示，零业务逻辑）
    ↓
展示给家属
```

---

## 3 层架构

### 第 1 层：数据层
**Mock 数据** → `BehaviorEvent[]` + `DailyBehaviorSummaryInput`
- 系统识别的原始事件
- 不包含任何文案

### 第 2 层：文案层
**Behavior → Text Generator** → `BehaviorText` + `DailySummaryText`
- 单个事件转文案
- 今日摘要转文案
- 不涉及页面逻辑

### 第 3 层：聚合层
**Status Engine** → `StatusViewModel`
- 聚合所有数据和文案
- 做出业务逻辑决策
- 输出页面需要的完整状态

### 第 4 层：展示层
**页面组件** → StatusDashboard
- 纯粹的展示逻辑
- 不处理任何业务逻辑
- 只接收 StatusViewModel 渲染

---

## StatusViewModel 结构

```typescript
interface StatusViewModel {
  // 整体状态等级（决定颜色）
  overall_status: "normal" | "attention" | "high"

  // 页面标题（大字体）
  headline: string

  // 当前位置和状态
  current_state: {
    label: string       // "在卧室"
    summary: string     // "老人目前可能在休息。"
  }

  // 最严重、最新的异常提醒
  primary_alert: BehaviorText | null

  // 最近 3-5 条行为记录（已生成文案）
  recent_behavior_texts: BehaviorText[]

  // 今日摘要
  daily_summary: DailySummaryText

  // 元数据
  metadata: {
    total_events: number
    alert_count: number
    last_update_time: string
  }
}
```

---

## 核心函数

### `generateStatusViewModel(events, dailySummary)`

这是 Status Engine 的核心函数，做以下工作：

1. **获取整体状态**
   ```typescript
   overall_status = dailySummary.highest_risk
   ```

2. **生成今日摘要**
   ```typescript
   daily_summary = generateDailySummaryText(dailySummary)
   ```

3. **获取当前状态**
   ```typescript
   // 基于最新事件
   current_state.label = getCurrentStateLabel(latestEvent)
   current_state.summary = generateBehaviorText(latestEvent).summary
   ```

4. **获取主异常提醒**
   ```typescript
   // 取风险最高、时间最近的 alert event
   primary_alert = getPrimaryAlert(events)
   ```

5. **获取最近行为**
   ```typescript
   // 取最近 4 条事件，生成文案
   recent_behavior_texts = getRecentBehaviorTexts(events, 4)
   ```

---

## 异常提醒优先级规则

`getPrimaryAlert()` 函数使用以下规则：

1. **只考虑 alert 事件**
   - `risk_level` 为 `attention` 或 `high` 的事件
   - 忽略 `normal` 的事件

2. **按风险等级优先**
   - `high` > `attention`

3. **同级别按时间优先**
   - 时间最近的优先

**示例**：
```
事件列表：
1. wake_up (normal)        ← 忽略
2. bathroom_use (normal)   ← 忽略
3. bathroom_long_stay (attention) 时间: 09:05  ← 考虑
4. no_activity (high)      时间: 10:30  ← 优先选择（risk_level 更高）

结果：选择 no_activity (high)
```

---

## 文件结构

```
src/
├── types/
│   ├── behavior.ts           ← 行为和文案类型
│   └── status.ts             ✨ 新增 - 状态视图模型
│
├── lib/
│   ├── behaviorText.ts       ← 行为文案生成
│   └── statusEngine.ts       ✨ 新增 - 状态聚合逻辑
│
├── data/
│   └── mockData.ts           ← Mock 数据
│
└── components/
    └── StatusDashboard.tsx   ✏️ 改造 - 使用 StatusViewModel
```

---

## 使用示例

### 在页面中使用

```typescript
'use client';

import { generateStatusViewModel } from '@/lib/statusEngine';
import { mockBehaviorEvents, mockDailySummaryInput } from '@/data/mockData';

export default function StatusDashboard() {
  // ✅ 唯一的业务逻辑调用
  const viewModel = generateStatusViewModel(
    mockBehaviorEvents,
    mockDailySummaryInput
  );

  return (
    <div>
      {/* 展示 headline */}
      <h2>{viewModel.headline}</h2>

      {/* 展示当前状态 */}
      <p>{viewModel.current_state.label}</p>

      {/* 展示异常提醒 */}
      {viewModel.primary_alert && (
        <div>
          <h3>{viewModel.primary_alert.title}</h3>
          <p>{viewModel.primary_alert.suggestion}</p>
        </div>
      )}

      {/* 展示最近行为 */}
      {viewModel.recent_behavior_texts.map((text) => (
        <div key={text.title}>
          <h4>{text.title}</h4>
          <p>{text.summary}</p>
        </div>
      ))}

      {/* 展示今日摘要 */}
      <div>
        <h3>{viewModel.daily_summary.headline}</h3>
        <p>{viewModel.daily_summary.summary}</p>
      </div>
    </div>
  );
}
```

---

## 页面组件的职责

StatusDashboard 现在只做：

✅ **做这些**：
- 接收 StatusViewModel
- 根据数据渲染 UI
- 处理用户交互（按钮点击等）
- 应用样式和布局

❌ **不做这些**：
- 生成文案
- 计算状态
- 选择异常提醒
- 过滤事件
- 任何业务逻辑

---

## 辅助函数

Status Engine 还提供了几个辅助函数，方便在组件中使用：

### `getStatusBgColor(overallStatus)`
获取背景色 Tailwind 类名

```typescript
getStatusBgColor('normal')    // 'bg-green-50 border-green-200'
getStatusBgColor('attention') // 'bg-yellow-50 border-yellow-200'
getStatusBgColor('high')      // 'bg-red-50 border-red-200'
```

### `getStatusTextColor(overallStatus)`
获取文字色 Tailwind 类名

```typescript
getStatusTextColor('normal')    // 'text-green-700'
getStatusTextColor('attention') // 'text-yellow-700'
getStatusTextColor('high')      // 'text-red-700'
```

### `getStatusBadgeColor(overallStatus)`
获取徽章背景色 Tailwind 类名

```typescript
getStatusBadgeColor('normal')    // 'bg-green-100 text-green-800'
getStatusBadgeColor('attention') // 'bg-yellow-100 text-yellow-800'
getStatusBadgeColor('high')      // 'bg-red-100 text-red-800'
```

### `getStatusBadgeText(overallStatus)`
获取徽章显示文本

```typescript
getStatusBadgeText('normal')    // '✓ 状态良好'
getStatusBadgeText('attention') // '⚠️ 需要关注'
getStatusBadgeText('high')      // '🚨 高风险'
```

### `hasAlert(viewModel)`
判断是否有异常提醒

```typescript
if (hasAlert(viewModel)) {
  // 显示异常提醒卡片
}
```

---

## 测试 Status Engine

### 在浏览器 Console 中测试

```javascript
// 打开浏览器开发者工具 (F12)，在 Console 中运行：

const { generateStatusViewModel } = await import('./src/lib/statusEngine.ts');
const { mockBehaviorEvents, mockDailySummaryInput } = 
  await import('./src/data/mockData.ts');

const viewModel = generateStatusViewModel(
  mockBehaviorEvents,
  mockDailySummaryInput
);

console.log(viewModel);
console.log('Status:', viewModel.overall_status);
console.log('Alert:', viewModel.primary_alert);
```

### 修改数据测试

编辑 `src/data/mockData.ts`：

```typescript
// 测试 high 级别
export const mockDailySummaryInput = {
  highest_risk: 'high',  // ← 改成 high
  alerts_count: 1,
  // ...
};

// 添加高风险事件
{
  id: 'event-high-risk',
  event_type: 'no_activity',
  duration_minutes: 120,
  risk_level: 'high',
}
```

然后刷新浏览器，页面会自动更新为红色。

---

## 性能优化

所有函数都是同步的，性能极优：

```typescript
const startTime = performance.now();
for (let i = 0; i < 1000; i++) {
  generateStatusViewModel(mockBehaviorEvents, mockDailySummaryInput);
}
const endTime = performance.now();
console.log(`1000 次调用耗时: ${(endTime - startTime).toFixed(2)}ms`);
// 通常 < 50ms
```

---

## 扩展方向

### 未来可以做的事情

1. **接入后端 API**
   ```typescript
   // 只需改这里，其他代码不变
   const events = await fetchBehaviorEvents();
   const summary = await fetchDailySummary();
   const viewModel = generateStatusViewModel(events, summary);
   ```

2. **添加历史数据视图**
   ```typescript
   const yesterdayViewModel = generateStatusViewModel(
     yesterdayEvents,
     yesterdaySummary
   );
   ```

3. **支持多人监护**
   ```typescript
   const elderlyList = [
     { id: 1, name: '王奶奶', ... },
     { id: 2, name: '李爷爷', ... },
   ];

   const viewModels = elderlyList.map(elderly =>
     generateStatusViewModel(
       getEventsForElderly(elderly.id),
       getSummaryForElderly(elderly.id)
     )
   );
   ```

4. **智能告警**
   ```typescript
   // 在 Status Engine 中添加告警生成逻辑
   export function generateAlerts(viewModel: StatusViewModel) {
     if (viewModel.overall_status === 'high') {
       return {
         should_notify: true,
         notification_text: '...',
       };
     }
   }
   ```

---

## 关键设计决策

### 为什么分 3 层？

| 层级 | 职责 | 变化频率 |
|------|------|---------|
| 文案层 | 将事件转为家属理解的语言 | 低（修改文案） |
| 聚合层 | 决定页面展示什么内容 | 中（改业务规则） |
| 展示层 | 渲染数据到 UI | 高（改界面） |

分离这三层使得：
- 修改文案不影响页面逻辑
- 改业务规则不影响页面样式
- 改页面布局不影响业务逻辑

### 为什么 StatusViewModel 包含所有需要的数据？

这样做的好处：

1. **页面组件简单** - 只需遍历和展示
2. **性能好** - 所有逻辑在一个函数中处理
3. **易于理解** - 清晰的输入输出边界
4. **易于测试** - 可独立测试 generateStatusViewModel
5. **易于调试** - 打印 StatusViewModel 就能看到页面会显示什么

---

## 总结

✅ **架构优势**：
- 完全分离业务逻辑和展示逻辑
- 页面组件清晰简洁
- 易于测试和扩展
- 易于接入后端

✅ **开发体验**：
- 修改文案只需改 `behaviorText.ts`
- 改业务规则只需改 `statusEngine.ts`
- 改页面样式只需改 `StatusDashboard.tsx`
- 三者不互相影响

✅ **可维护性**：
- 代码职责清晰
- 改动范围小，风险低
- 新开发者易于理解

---

**这就是一个完整的、生产级别的前端架构！** 🚀
