# Status Engine 快速参考

## 新增文件

### 1. `src/types/status.ts`
定义 StatusViewModel 类型，包含页面需要的所有数据。

**关键类型**：
- `OverallStatus` - "normal" | "attention" | "high"
- `CurrentState` - { label, summary }
- `StatusViewModel` - 页面需要的完整数据

---

### 2. `src/lib/statusEngine.ts`
核心聚合逻辑，将所有数据和文案聚合为页面需要的状态。

**关键函数**：
- `generateStatusViewModel(events, dailySummary)` - 主函数
- `getStatusBgColor(status)` - 背景色
- `getStatusTextColor(status)` - 文字色
- `getStatusBadgeColor(status)` - 徽章色
- `getStatusBadgeText(status)` - 徽章文本
- `hasAlert(viewModel)` - 判断是否有提醒

---

### 3. `src/components/StatusDashboard.tsx`（改造）
页面组件现在只负责展示，不处理业务逻辑。

**改变**：
```typescript
// 之前：页面组件处理所有逻辑
const latestEvent = mockBehaviorEvents[...];
const alertText = generateBehaviorText(alertEvent);

// 现在：从 StatusViewModel 获取数据
const viewModel = generateStatusViewModel(events, summary);
const headline = viewModel.headline;
const alertText = viewModel.primary_alert;
```

---

## 使用流程

### 页面加载时
```typescript
1. 读取 mockBehaviorEvents
2. 读取 mockDailySummaryInput
3. 调用 generateStatusViewModel()
4. 得到 StatusViewModel
5. 页面根据 StatusViewModel 渲染
```

### 数据修改时
```typescript
// 只需修改 mock 数据
mockDailySummaryInput.highest_risk = 'high'

// 页面自动更新（因为 useEffect 会重新调用生成函数）
```

---

## 3 层架构示意

```
数据层
┌─────────────────────────────┐
│ BehaviorEvent[]             │
│ DailyBehaviorSummaryInput   │
└──────────────┬──────────────┘
               │
文案层 (behaviorText.ts)
├─ generateBehaviorText()
└─ generateDailySummaryText()
               │
聚合层 (statusEngine.ts)
└─ generateStatusViewModel()  ← 唯一的业务逻辑点
               │
展示层 (StatusDashboard.tsx)
└─ 根据 StatusViewModel 渲染
               │
              用户
```

---

## StatusViewModel 内容

```typescript
{
  overall_status: "attention",        // 整体状态等级
  headline: "今日需关注",             // 大标题
  current_state: {
    label: "在卫生间",               // 当前位置
    summary: "老人卫生间停留..."      // 当前摘要
  },
  primary_alert: {                    // 主异常提醒
    title: "卫生间停留较长",
    summary: "...",
    detail: "...",
    suggestion: "...",
    display_level: "attention"
  },
  recent_behavior_texts: [            // 最近 4 条行为
    { title: "已起床", summary: "..." },
    // ...
  ],
  daily_summary: {                    // 今日摘要
    headline: "今日需关注",
    summary: "...",
    key_points: [...],
    suggestion: "..."
  },
  metadata: {
    total_events: 4,                  // 事件总数
    alert_count: 1,                   // 异常数
    last_update_time: "2026-04-25..." // 更新时间
  }
}
```

---

## 核心逻辑

### 主异常提醒选择规则

```
1. 过滤出所有 alert 事件（risk_level = attention 或 high）
2. 按风险等级排序：high > attention
3. 同级别按时间排序：最新优先
4. 返回第一个的文案
```

### 最近行为数据

```
1. 取最近 4 条事件
2. 为每条生成文案
3. 按时间顺序返回
```

---

## 常见修改

### 改变今日状态等级
```typescript
// src/data/mockData.ts
mockDailySummaryInput.highest_risk = 'high'
```
页面背景自动变红，不需要改其他代码。

### 改变最近行为数量
```typescript
// src/lib/statusEngine.ts
function getRecentBehaviorTexts(events, 5)  // 改成 5
```

### 改变主异常提醒规则
```typescript
// src/lib/statusEngine.ts
function getPrimaryAlert(events) {
  // 修改排序逻辑
}
```

### 添加新的辅助函数
```typescript
// src/lib/statusEngine.ts
export function shouldShowCriticalBanner(viewModel) {
  return viewModel.overall_status === 'high' 
    && viewModel.metadata.alert_count > 2;
}
```

---

## 测试清单

- [ ] 页面正常加载
- [ ] overall_status 正确反映 highest_risk
- [ ] headline 正确显示
- [ ] current_state 显示最新事件的位置
- [ ] primary_alert 选中最高风险事件
- [ ] recent_behavior_texts 显示最近 4 条
- [ ] daily_summary 内容完整
- [ ] 修改 mock 数据后，页面自动更新
- [ ] 颜色根据 overall_status 变化

---

## 代码量对比

### 之前（没有 Status Engine）
```typescript
// StatusDashboard.tsx 中混合了大量业务逻辑
const latestEvent = mockBehaviorEvents[...];
const alertEvent = [...mockBehaviorEvents].reverse().find(...);
const dailySummaryText = generateDailySummaryText(...);
// ...
// 总计：~150 行业务逻辑
```

### 现在（有 Status Engine）
```typescript
// StatusDashboard.tsx 只有展示逻辑
const viewModel = generateStatusViewModel(...);
// 然后直接使用 viewModel 的各个字段
// 总计：~100 行展示逻辑
```

**减少 ~50 行业务逻辑，代码更清晰！**

---

## 下一步

1. ✅ 测试 Status Engine 功能
2. ✅ 修改 mock 数据，观察页面变化
3. ✅ 阅读 STATUS_ENGINE.md 了解详细设计
4. ⬜ 接入后端 API（将来）
5. ⬜ 添加更多事件类型（将来）
6. ⬜ 支持多人监护（将来）

---

## 最重要的一点

```typescript
// 这是页面唯一需要调用的业务逻辑
const viewModel = generateStatusViewModel(
  mockBehaviorEvents, 
  mockDailySummaryInput
);

// 其他的都是展示！
// ✅ 页面组件职责清晰
// ✅ 业务逻辑集中管理
// ✅ 易于维护和扩展
```

---

**现在你有了一个真正的、生产级别的前端架构！** 🚀
