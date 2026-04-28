# 🎬 MVP Demo 快速启动指南

## 一句话总结
这是一个为家属设计的**老人状态监护面板**，用一个页面快速显示老人是否正常。

---

## 🚀 快速启动（3 分钟）

### 前提条件
- Node.js 18+ 已安装
- 网络连接正常

### 启动步骤

#### 步骤 1️⃣: 进入项目目录
```bash
cd /Users/han1331/Library/Application\ Support/Claude/local-agent-mode-sessions/de38644d-fff6-4075-9e5c-0fcda63fa72e/4dd91277-f42d-4876-aff7-d1e72903f8a5/local_75952224-595d-439e-9fc5-721b63ef76e4/outputs
```

#### 步骤 2️⃣: 安装依赖
```bash
npm install
```

**如果遇到 npm 错误:**
```bash
# 清除 npm 缓存
npm cache clean --force

# 重新尝试
npm install
```

#### 步骤 3️⃣: 启动开发服务器
```bash
npm run dev
```

**预期输出:**
```
  ▲ Next.js 15.0.0
  - Local:        http://localhost:3000
  - Environments: .env.local

✓ Ready in 1234ms
```

#### 步骤 4️⃣: 打开浏览器
访问: **http://localhost:3000**

---

## 📱 页面功能演示

### 场景 1️⃣: 正常状态（绿色）

**你会看到:**
```
┌─────────────────────────────┐
│                             │
│    王奶奶 的状态仪表板      │
│                             │
│  ✓ 状态良好                │
│  "今日状态正常"             │
│                             │
│  当前状态: 在卧室           │
│  今日活动: 正常             │
│  行为记录: 已起床/活动/... │
│                             │
│  [确认正常] [需要帮助]      │
│                             │
└─────────────────────────────┘
```

**点击"确认正常"按钮：**
- ✅ 按钮变成绿色，显示"✓ 已确认正常"
- 📊 后端收到反馈（在浏览器 Console 可以看到日志）
- ⏱️ 2 秒后按钮恢复原样

---

### 场景 2️⃣: 需要关注状态（黄色）

**修改方式:**
1. 打开 `src/data/mockData.ts`
2. 找到第 55 行：`highest_risk: 'attention',`
3. 刷新浏览器

**你会看到:**
```
┌─────────────────────────────┐
│                             │
│    王奶奶 的状态仪表板      │
│                             │
│  ⚠️ 需要关注               │
│  "老人今天出现部分与日常    │
│   不同的行为，建议家属关注"  │
│                             │
│  [异常提醒卡片]             │
│  卫生间停留较长             │
│  已在卫生间停留约 25 分钟。  │
│  建议电话确认老人状态。      │
│                             │
│  [确认正常] [需要帮助]      │
│                             │
└─────────────────────────────┘
```

---

### 场景 3️⃣: 高风险状态（红色）

**修改方式:**
1. 打开 `src/data/mockData.ts`
2. 将 `highest_risk: 'attention'` 改为 `highest_risk: 'high'`
3. 刷新浏览器

**你会看到:**
```
┌─────────────────────────────┐
│                             │
│    王奶奶 的状态仪表板      │
│                             │
│  🚨 高风险                 │
│  "系统检测到可能需要立即    │
│   确认的异常行为"            │
│                             │
│  [异常提醒卡片 - 红色边框]  │
│  卫生间停留过久              │
│  老人已在卫生间停留较长      │
│  时间，可能需要关注。        │
│  建议立即联系老人或...       │
│                             │
│  [确认正常] [需要帮助]      │
│                             │
└─────────────────────────────┘
```

---

## 🧪 高级测试

### 测试 1️⃣: 查看 Loading 状态

**方法:**
1. 打开浏览器开发者工具（F12）
2. 刷新页面（Ctrl+R）
3. 快速看到旋转加载动画（持续约 300ms）

**预期:**
```
        ⟳ 旋转加载图标

    正在加载老人状态…
         请稍候
```

---

### 测试 2️⃣: 查看 Error 状态

**方法:**
1. 打开浏览器 Console（F12）
2. 输入以下命令：
```javascript
import { apiClient } from './src/lib/apiClient.js';
apiClient.setConfig({ enableMockData: false });
```
3. 刷新页面

**预期:**
```
┌────────────────────────┐
│        ⚠️              │
│                        │
│   状态加载失败         │
│   Mock 数据已禁用       │
│                        │
│  [重新加载按钮]        │
│                        │
│  错误代码: 500         │
└────────────────────────┘
```

**恢复方法:**
```javascript
apiClient.setConfig({ enableMockData: true });
```
然后刷新页面。

---

### 测试 3️⃣: 查看 Console 日志

**操作:**
1. 打开浏览器 Console（F12）
2. 点击"需要帮助"按钮

**预期在 Console 看到:**
```
提交反馈: {
  alert_id: "event-004",
  action: "need_help",
  timestamp: "2026-04-25T10:30:45.123Z",
  notes: "家属表示需要帮助"
}
```

---

### 测试 4️⃣: 修改 Mock 数据

**修改老人名字:**
1. 打开 `src/data/mockData.ts`
2. 找到 `name: '王奶奶'`
3. 改成其他名字，比如 `name: '李爷爷'`
4. 刷新浏览器

**预期:**
页面标题从"王奶奶"变成"李爷爷"

**修改行为事件数量:**
1. 在 `mockBehaviorEvents` 中添加更多事件对象
2. 刷新页面会显示更多的行为记录

**修改今日摘要:**
1. 改变 `mockDailySummaryInput` 中的值
2. 刷新页面显示新数据

---

## 🎯 演示流程（5 分钟完整演示）

### 第 1 分钟：基础展示
```
1. 打开 http://localhost:3000
2. 展示页面自动加载老人状态
3. 说明："这是一个为家属设计的一页式状态面板"
```

### 第 2 分钟：功能演示
```
1. 点击"确认正常"按钮 → 显示成功反馈
2. 点击"需要帮助"按钮 → 可以添加备注
3. 展示 Console 日志中的反馈数据
```

### 第 3 分钟：状态变化
```
1. 打开 mockData.ts，改变 highest_risk
2. 刷新页面
3. 演示状态从绿→黄→红的变化
```

### 第 4-5 分钟：问答
```
- "老人状态如何识别？" → 通过智能设备传感器
- "如何集成真实数据？" → 修改 apiClient.ts 中的实现
- "可以支持多个老人吗？" → 是的，修改 MOCK_HOME_ID 即可
- "是否支持移动端？" → 完全响应式设计
```

---

## 🔍 常见问题

### Q1: 如何修改老人的信息？
**A:** 编辑 `src/data/mockData.ts` 中的 `mockElderlyInfo` 对象。

### Q2: 如何添加新的行为事件？
**A:** 在 `src/data/mockData.ts` 的 `mockBehaviorEvents` 数组中添加新对象。

### Q3: 真实数据如何接入？
**A:** 修改 `src/lib/apiClient.ts` 中的三个方法：
- `getBehaviorEvents()` - 改为真实 API 调用
- `getDailySummary()` - 改为真实 API 调用
- `submitFeedback()` - 改为真实 API 调用

### Q4: 页面为什么响应缓慢？
**A:** 这是正常的！apiClient 内置了 300ms 网络延迟模拟。移除 `await this.delay(300)` 可以加速。

### Q5: 如何修改颜色主题？
**A:** 编辑 `src/lib/statusEngine.ts` 中的 `getStatusBgColor()` 等函数中的 Tailwind 类名。

---

## 📊 架构一览

```
用户界面 (StatusDashboard.tsx)
    ↓
数据获取 (apiClient.getBehaviorEvents/getDailySummary)
    ↓
业务逻辑 (generateStatusViewModel)
    ↓ 包含 3 层：
    ├─ 文本生成 (generateBehaviorText)
    ├─ 聚合引擎 (getPrimaryAlert)
    └─ 样式映射 (getStatusBgColor)
    ↓
页面渲染 (3 种状态：loading/error/normal)
    ↓
用户交互 (handleConfirm/handleNeedHelp)
    ↓
反馈提交 (apiClient.submitFeedback)
```

---

## 📝 文件结构速查

```
src/
├── app/
│   ├── layout.tsx       ← 页面框架
│   ├── page.tsx         ← 首页入口
│   └── globals.css      ← 全局样式
├── components/
│   └── StatusDashboard.tsx  ← 主页面组件
├── lib/
│   ├── apiClient.ts     ← API 数据接入层
│   ├── behaviorText.ts  ← 文本生成
│   └── statusEngine.ts  ← 状态聚合引擎
├── types/
│   ├── api.ts          ← API 类型
│   ├── behavior.ts     ← 行为类型
│   └── status.ts       ← 状态类型
└── data/
    └── mockData.ts     ← Mock 数据（修改这里测试）
```

---

## 🎨 UI 界面一览

| 区域 | 说明 |
|-----|------|
| 顶部标题 | 显示老人名字 + "家属监护面板" |
| 主状态卡片 | 显示整体状态（绿/黄/红背景） |
| 今日摘要 | 展示今日活动总结 + 建议 |
| 当前状态 | 老人当前所在位置和行为 |
| 行为记录 | 最近 4 条行为事件 |
| 异常提醒 | 仅在有 alert 时显示（黄/红卡片）|
| 操作按钮 | "确认正常" 和 "需要帮助" |
| 元数据 | 最后更新时间和事件统计 |

---

## 🚨 故障排除

| 问题 | 解决方案 |
|-----|---------|
| npm install 失败 | 清除缓存：`npm cache clean --force` 后重试 |
| 访问 localhost:3000 失败 | 确保开发服务器正在运行，检查终端输出 |
| 页面空白 | 打开 Console（F12），查看是否有 JavaScript 错误 |
| 样式不对 | 刷新浏览器缓存：Ctrl+Shift+R（Chrome）|
| 数据没有更新 | 检查是否启用了浏览器缓存，尝试硬刷新 |

---

## 💡 额外提示

1. **开发模式特性**:
   - Hot Reload: 修改代码自动刷新
   - TypeScript 类型检查实时进行
   - Tailwind CSS 自动编译

2. **性能**:
   - 首次加载：~2-3 秒（包括 300ms 模拟延迟）
   - 后续加载：<1 秒

3. **浏览器兼容性**:
   - ✅ Chrome 90+
   - ✅ Firefox 88+
   - ✅ Safari 14+
   - ✅ Edge 90+

4. **移动端**:
   - 完全响应式设计
   - 移动端字体已优化（16px 最小）
   - 支持移动 Web App 模式

---

**祝演示顺利！如有任何问题，请查看对应的技术文档。** 🚀

