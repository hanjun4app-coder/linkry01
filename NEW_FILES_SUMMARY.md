# 新增文件汇总

## 📄 本次添加的文件

### 1. `src/types/behavior.ts` - 类型定义
**用途**：定义所有数据结构和接口

**包含内容**：
- `RiskLevel` - 风险等级类型 (normal | attention | high)
- `EventType` - 事件类型 (wake_up, bathroom_long_stay, 等 10 种)
- `BehaviorEvent` - 底层行为事件数据结构
- `BehaviorText` - 展示文案数据结构
- `DailyBehaviorSummaryInput` - 今日摘要输入数据
- `DailySummaryText` - 今日摘要展示文案

**关键作用**：
- 确保类型安全
- IDE 自动完成提示
- 防止拼写错误

---

### 2. `src/lib/behaviorText.ts` - 文案生成函数
**用途**：所有业务文案的唯一生成源

**包含函数**：
- `generateBehaviorText(event)` - 生成单个事件文案
- `generateDailySummaryText(input)` - 生成今日摘要文案
- `getCurrentStateLabel(event)` - 获取当前位置标签
- `isAlertEvent(event)` - 判断是否为异常事件

**关键作用**：
- 集中管理所有中文文案
- 逻辑与展示分离
- 便于维护和扩展

---

### 3. `src/data/mockData.ts` - Mock 数据（已改造）
**用途**：提供测试数据

**包含数据**：
- `mockBehaviorEvents[]` - 行为事件数组（4 个示例事件）
- `mockDailySummaryInput` - 今日摘要数据（attention 级别）
- `mockElderlyInfo` - 老人基本信息

**关键作用**：
- 无需后端即可运行
- 易于修改测试不同场景
- 事件会自动转为展示文案

---

### 4. `src/components/StatusDashboard.tsx` - 页面组件（已改造）
**用途**：展示层，调用生成函数

**关键改变**：
```typescript
// 之前：硬编码文案
const alert = {
  title: "卫生间停留较长",
  summary: "...",
};

// 现在：通过生成函数
const latestEvent = mockBehaviorEvents[mockBehaviorEvents.length - 1];
const latestBehaviorText = generateBehaviorText(latestEvent);
```

**包含部分**：
- 主状态卡片 - 使用 `generateDailySummaryText()`
- 当前状态 - 使用 `generateBehaviorText(latestEvent)`
- 行为记录 - 遍历事件数组，每条用 `generateBehaviorText()`
- 异常提醒 - 使用 `generateBehaviorText(alertEvent)`

---

### 5. `BEHAVIOR_TEXT_GENERATOR.md` - 新增文档
**用途**：详细说明新架构

**包含内容**：
- 架构设计原则
- 文件结构说明
- 10 种事件类型映射表
- 使用示例
- 文案修改方法
- 调试技巧

---

## 🔄 改造的文件

### 1. `src/data/mockData.ts`
**改变**：
```typescript
// 之前
export const mockData = {
  status: 'attention',
  statusLabel: '需要关注',
  alert: { title: '...', summary: '...', ... }
}

// 现在
export const mockBehaviorEvents: BehaviorEvent[] = [
  { id: '...', event_type: 'wake_up', risk_level: 'normal' },
  { id: '...', event_type: 'bathroom_long_stay', risk_level: 'attention' },
]

export const mockDailySummaryInput: DailyBehaviorSummaryInput = {
  wake_time: '07:30',
  total_active_minutes: 180,
  highest_risk: 'attention',
}
```

---

### 2. `src/components/StatusDashboard.tsx`
**改变**：
```typescript
// 之前
const statusLabel = mockData.statusLabel;
const alertText = mockData.alert;

// 现在
const latestEvent = mockBehaviorEvents[mockBehaviorEvents.length - 1];
const latestBehaviorText = generateBehaviorText(latestEvent);
const dailySummaryText = generateDailySummaryText(mockDailySummaryInput);
const alertText = alertEvent ? generateBehaviorText(alertEvent) : null;
```

---

## 📊 数据流

```
┌─────────────────────────────────────────────────────┐
│ mockBehaviorEvents[]                                │
│ - wake_up (normal)                                  │
│ - living_activity (normal)                          │
│ - bathroom_use (normal)                             │
│ - bathroom_long_stay (attention) ← 异常事件        │
└─────────────────────────────────────────────────────┘
                        ↓
            generateBehaviorText(event)
                        ↓
┌─────────────────────────────────────────────────────┐
│ BehaviorText[]                                      │
│ - title: "已起床"                                   │
│ - summary: "老人今天已开始活动。"                   │
│ - title: "卫生间停留较长"                          │
│ - suggestion: "建议电话确认老人状态。"             │
└─────────────────────────────────────────────────────┘
                        ↓
         StatusDashboard.tsx (页面组件)
                        ↓
                   展示给家属
```

---

## 🎯 快速开始

### 1. 查看新的文件结构
```bash
src/
├── types/
│   └── behavior.ts          ✨ 新增
├── lib/
│   └── behaviorText.ts      ✨ 新增
├── data/
│   └── mockData.ts          ✏️ 已改造
└── components/
    └── StatusDashboard.tsx  ✏️ 已改造
```

### 2. 运行项目
```bash
npm install && npm run dev
```

### 3. 打开浏览器
访问 http://localhost:3000，应该能看到和之前一样的页面，但现在文案都是动态生成的。

---

## 💡 常见任务

### 修改文案
编辑 `src/lib/behaviorText.ts` 中的 case 语句

### 添加新事件类型
1. 在 `types/behavior.ts` 中添加 EventType
2. 在 `lib/behaviorText.ts` 中添加 case
3. 在 `data/mockData.ts` 中添加测试数据

### 改变今日状态等级
编辑 `src/data/mockData.ts`：
```typescript
export const mockDailySummaryInput: DailyBehaviorSummaryInput = {
  highest_risk: 'high',  // ← 改这里 (normal | attention | high)
  alerts_count: 1,
}
```

### 添加/移除行为事件
编辑 `src/data/mockData.ts` 中的 `mockBehaviorEvents` 数组

---

## 📚 重要文档

- **BEHAVIOR_TEXT_GENERATOR.md** - 架构详解（必读）
- **README.md** - 项目概览
- **QUICK_START.md** - 快速启动

---

## ✨ 架构优势

| 优势 | 说明 |
|------|------|
| 📝 文案集中管理 | 所有中文都在 `behaviorText.ts`，易于维护 |
| 🔄 逻辑与展示分离 | 页面组件只管展示，文案逻辑独立 |
| 🆕 易于扩展 | 添加新事件类型只需改生成函数 |
| 🧪 易于测试 | 可以独立测试生成函数 |
| 🌍 多语言支持 | 未来可轻松支持其他语言 |
| 📱 性能优 | 生成函数同步执行，无网络延迟 |

---

## 🔍 验证清单

启动项目后，检查以下内容：

- [ ] 页面正常加载，没有错误
- [ ] 看到老人名字"王奶奶"
- [ ] 主状态显示"今日需关注"（黄色）
- [ ] 有"卫生间停留较长"的异常提醒
- [ ] 最近行为记录显示 4 条活动
- [ ] 每条行为都有标题和摘要
- [ ] 异常提醒有建议信息
- [ ] 打开 Console (F12)，点击"确认正常"有时间戳输出

---

## 🚀 下一步

现在你的 MVP 有了完整的文案生成层。你可以：

1. **修改 mock 数据** - 测试不同场景
2. **修改文案** - 调整语言风格
3. **添加新事件类型** - 扩展功能
4. **接入后端 API** - 替换 mock 数据（保持文案层不变）

---

**祝你开发愉快！** 🎉
