# Behavior → Text Generator 架构说明

## 概述

**Behavior → Text Generator** 是一个中间层，将系统识别的低级行为事件（BehaviorEvent）转换为家属能理解的高级展示文案（BehaviorText）。

```
系统传感器识别
    ↓
BehaviorEvent (底层数据)
    ↓
generateBehaviorText() (转换函数)
    ↓
BehaviorText (家属友好的文案)
    ↓
页面展示给家属
```

---

## 核心设计原则

### 1. 数据与文案分离
- **BehaviorEvent** - 纯数据，由系统生成
- **BehaviorText** - 纯文案，由生成函数产出
- **页面组件** - 不直接写业务文案，只调用生成函数

### 2. 集中管理文案
所有业务文案都在 `lib/behaviorText.ts` 中维护，便于：
- 统一修改文案风格
- 新增事件类型时，只需在生成函数中扩展
- 避免重复和不一致

### 3. 类型安全
使用 TypeScript 确保：
- 事件类型完整（所有case都要处理）
- 文案字段齐全（title, summary, detail, suggestion, display_level）
- 风险等级准确（normal, attention, high）

---

## 文件结构

```
src/
├── types/
│   └── behavior.ts              # 类型定义
│       ├── RiskLevel            # 风险等级
│       ├── EventType            # 事件类型
│       ├── BehaviorEvent        # 底层数据
│       ├── BehaviorText         # 展示文案
│       └── DailyBehaviorSummaryInput / DailySummaryText  # 今日摘要
│
├── lib/
│   └── behaviorText.ts          # 文案生成函数
│       ├── generateBehaviorText(event) → BehaviorText
│       ├── generateDailySummaryText(input) → DailySummaryText
│       ├── getCurrentStateLabel(event) → string
│       └── isAlertEvent(event) → boolean
│
├── data/
│   └── mockData.ts              # Mock 数据
│       ├── mockBehaviorEvents[] # 行为事件数组
│       ├── mockDailySummaryInput # 今日摘要数据
│       └── mockElderlyInfo      # 老人基本信息
│
└── components/
    └── StatusDashboard.tsx      # 页面组件
        ├── 读取 mockBehaviorEvents
        ├── 调用 generateBehaviorText()
        ├── 调用 generateDailySummaryText()
        └── 展示文案给家属
```

---

## 10 种事件类型及文案映射

| event_type | 中文 | risk_level | 用途 |
|-----------|------|-----------|------|
| `wake_up` | 起床 | normal | 老人开始活动的信号 |
| `living_activity` | 活动 | normal | 在活动区域的日常行为 |
| `bathroom_use` | 卫生间使用 | normal | 普通的卫生间使用 |
| `bathroom_long_stay` | 卫生间停留过久 | attention/high | ⚠️ 异常 |
| `no_activity` | 长时间无活动 | attention/high | ⚠️ 异常 |
| `night_wake` | 夜间起床 | attention | 异常活动 |
| `nap` | 午休 | normal | 日常作息 |
| `resting` | 休息 | normal | 日常作息 |
| `left_home` | 离家 | normal | 门窗事件 |
| `returned_home` | 回家 | normal | 门窗事件 |

---

## 使用示例

### 示例 1：显示一个行为事件

```typescript
import { mockBehaviorEvents } from '@/data/mockData';
import { generateBehaviorText } from '@/lib/behaviorText';

const event = mockBehaviorEvents[0];
const text = generateBehaviorText(event);

console.log(text.title);       // "已起床"
console.log(text.summary);     // "老人今天已开始活动。"
console.log(text.detail);      // "系统检测到老人从卧室进入活动区域。"
console.log(text.suggestion);  // "当前无需处理。"
console.log(text.display_level); // "normal"
```

### 示例 2：生成今日摘要

```typescript
import { mockDailySummaryInput } from '@/data/mockData';
import { generateDailySummaryText } from '@/lib/behaviorText';

const summary = generateDailySummaryText(mockDailySummaryInput);

console.log(summary.headline);      // "今日需关注"
console.log(summary.summary);       // "老人今天出现部分与日常不同的行为..."
console.log(summary.key_points);    // ["出现一次需要关注的行为", ...]
console.log(summary.suggestion);    // "建议电话确认老人状态。"
```

### 示例 3：找出需要提醒的异常事件

```typescript
import { mockBehaviorEvents } from '@/data/mockData';
import { isAlertEvent, generateBehaviorText } from '@/lib/behaviorText';

// 找出所有异常事件
const alertEvents = mockBehaviorEvents.filter(event => isAlertEvent(event));

// 获取最新的异常事件
const latestAlert = [...mockBehaviorEvents].reverse().find(isAlertEvent);

if (latestAlert) {
  const alertText = generateBehaviorText(latestAlert);
  console.log(alertText.title);       // "卫生间停留较长"
  console.log(alertText.suggestion);  // "建议电话确认老人状态。"
}
```

### 示例 4：在页面中使用

```typescript
// StatusDashboard.tsx
const latestEvent = mockBehaviorEvents[mockBehaviorEvents.length - 1];
const behaviorText = generateBehaviorText(latestEvent);

return (
  <div>
    <h2>{behaviorText.title}</h2>
    <p>{behaviorText.summary}</p>
    <p>{behaviorText.detail}</p>
    <p>💡 {behaviorText.suggestion}</p>
  </div>
);
```

---

## 如何修改文案

### 修改现有事件的文案

在 `lib/behaviorText.ts` 中找到对应的 case，修改文案内容：

```typescript
case 'bathroom_long_stay':
  if (event.risk_level === 'high') {
    return {
      title: '卫生间停留过久',
      summary: '老人已在卫生间停留较长时间，可能需要关注。',
      detail: `卫生间停留已持续约 ${duration} 分钟。`,
      suggestion: '建议立即联系老人或附近联系人确认情况。',  // ← 修改这里
      display_level: 'high',
    };
  }
  // ...
```

### 添加新的事件类型

1. 在 `types/behavior.ts` 中添加新的 EventType：
```typescript
export type EventType =
  | 'wake_up'
  | 'living_activity'
  | 'bathroom_use'
  | '...existing types...'
  | 'new_event_type';  // ← 添加
```

2. 在 `lib/behaviorText.ts` 中添加新的 case：
```typescript
case 'new_event_type':
  return {
    title: '新事件标题',
    summary: '新事件摘要。',
    detail: '新事件详情。',
    suggestion: '建议：...',
    display_level: 'normal',
  };
```

3. 在 `data/mockData.ts` 中创建测试数据：
```typescript
{
  id: 'event-xxx',
  home_id: 'home-001',
  event_type: 'new_event_type',
  risk_level: 'normal',
}
```

---

## 风险等级说明

### normal（正常）
- 日常活动，无需特别关注
- 绿色界面，显示 ✓ 状态良好
- suggestion 通常是"当前无需处理"

### attention（需要关注）
- 异常行为，但不紧急
- 黄色界面，显示 ⚠️ 需要关注
- suggestion 通常是"建议电话确认"

### high（高风险）
- 严重异常，需要立即处理
- 红色界面，显示 🚨 高风险
- suggestion 通常是"建议立即联系"

---

## 文案设计规范

所有文案都遵循以下规范：

### 语气要求
- ✅ 平静、专业、不耸人听闻
- ✅ 准确描述现象
- ❌ 不写医疗诊断
- ❌ 不做出医学建议

### 文案四要素
1. **title** - 简短标题（2-6字）
2. **summary** - 一句话摘要（8-15字）
3. **detail** - 详细说明（包含数据如时长）
4. **suggestion** - 建议行动

### 示例对比

❌ **不好的例子**：
```
title: "紧急！老人可能跌倒"
summary: "老人可能脑溢血了"
suggestion: "请立即送医院"
```

✅ **好的例子**：
```
title: "长时间未活动"
summary: "系统长时间未检测到活动。"
suggestion: "建议立即电话联系老人确认状态。"
```

---

## 性能考虑

生成函数都是同步的，性能极高：
- 没有网络请求
- 没有数据库查询
- 只是字符串和对象操作

```typescript
// 性能测试
const startTime = performance.now();
for (let i = 0; i < 10000; i++) {
  generateBehaviorText(mockBehaviorEvents[0]);
}
const endTime = performance.now();
console.log(`10000 次调用耗时: ${endTime - startTime}ms`); // 通常 < 10ms
```

---

## 测试 Mock 数据

### 改为正常状态
编辑 `src/data/mockData.ts`：
```typescript
export const mockDailySummaryInput: DailyBehaviorSummaryInput = {
  // ...
  highest_risk: 'normal',  // ← 改成 normal
  alerts_count: 0,          // ← 改成 0
};
```

### 改为高风险状态
```typescript
export const mockDailySummaryInput: DailyBehaviorSummaryInput = {
  // ...
  highest_risk: 'high',     // ← 改成 high
  alerts_count: 1,          // ← 改成 1
};

// 添加一个高风险事件
{
  id: 'event-high-risk',
  home_id: 'home-001',
  event_type: 'no_activity',
  duration_minutes: 120,
  risk_level: 'high',  // ← 设置为 high
}
```

---

## 调试技巧

### 在浏览器 Console 中测试
```javascript
// 打开浏览器开发者工具 (F12)，在 Console 中运行：

// 获取第一个事件的文案
const event = window.__mockBehaviorEvents[0];
const text = window.__generateBehaviorText(event);
console.log(text);

// 生成今日摘要
const summary = window.__generateDailySummaryText(window.__mockDailySummaryInput);
console.log(summary);
```

### 查看事件堆栈
```typescript
// 在 StatusDashboard.tsx 中打印
console.log('所有行为事件:', mockBehaviorEvents);
console.log('今日摘要:', mockDailySummaryInput);
mockBehaviorEvents.forEach(event => {
  console.log(event.event_type, generateBehaviorText(event));
});
```

---

## 总结

✅ **架构优势**：
- 数据与文案完全分离
- 所有文案集中管理
- 易于扩展和修改
- 类型安全
- 性能极优

✅ **页面开发**：
- 组件只关心展示逻辑
- 不需要硬编码文案
- 修改文案时不需要改代码

✅ **未来扩展**：
- 轻松支持多种语言（只需提供不同的生成函数）
- 可以接入后端 API 替换 mock 数据
- 可以添加新的事件类型而不改现有代码

---

**祝开发愉快！** 🚀
