# 基线学习与UI集成指南

**版本**: 1.0  
**日期**: April 2026  
**目的**: 将baseline学习和个性化信号集成到statusEngine和UI中

---

## 架构概览

```
原始数据 (传感器事件)
    ↓
statusEngineV2 (日常更新)
    ├─ 检测临时状态
    ├─ 更新基线
    ├─ 生成个性化信号
    └─ 结合通用规则
    ↓
EnhancedStatusView (UI)
    ├─ 显示通用风险 (最小基准)
    ├─ 显示个性化信号 (补充)
    ├─ 显示基线进度 (学习状态)
    └─ 显示临时状态 (异常模式)
```

---

## 新增文件清单

| 文件 | 目的 | 关键导出 |
|---|---|---|
| src/lib/statusEngineV2.ts | 日常基线更新逻辑 | generateStatusViewWithBaseline() |
| src/components/EnhancedStatusView.tsx | UI组件显示通用+个性化 | EnhancedStatusView |

---

## 集成步骤

### Step 1: 替换statusEngine调用

**之前** (使用旧statusEngine):
```typescript
// 旧方式
const statusView = generateStatusViewModel(
  elder_id,
  events,
  dailyData,
  devices
);

return statusView;
```

**之后** (使用statusEngineV2):
```typescript
// 新方式
import { generateStatusViewWithBaseline, dailyStatusUpdate } from '@/lib/statusEngineV2';
import { ElderBaseline } from '@/types/baseline';

// 从数据库获取当前基线
let baseline = await db.getEldersBaseline(elder_id);

const result = await generateStatusViewWithBaseline(
  elder_id,
  eventsToday,       // 所有事件
  dailySummary,      // 每日汇总
  devices,           // 房间中的传感器
  baseline           // 现有基线(可能为null)
);

// 保存更新后的基线到数据库
await db.updateEldersBaseline(elder_id, result.baseline);

return result.statusView;
```

### Step 2: 替换UI组件

**之前** (显示通用风险):
```typescript
import { StatusView } from '@/components/StatusView';

export const ElderDashboard = ({ elder_id }) => {
  const [status] = useStatus(elder_id);
  
  return <StatusView status={status} />;
};
```

**之后** (显示通用+个性化):
```typescript
import EnhancedStatusView from '@/components/EnhancedStatusView';
import { useStatus, useBaseline } from '@/hooks';

export const ElderDashboard = ({ elder_id }) => {
  const { status, temporaryCondition, personalizedSignals } = useStatus(elder_id);
  const { baseline } = useBaseline(elder_id);
  
  return (
    <EnhancedStatusView 
      status={status}
      personalizedSignals={personalizedSignals}
      baseline={baseline}
      inTemporaryCondition={!!temporaryCondition}
    />
  );
};
```

### Step 3: 创建日常更新任务

每天运行一次基线更新(建议晚上11:59):

```typescript
// 创建定时任务
import { createScheduledTask } from '@/lib/scheduler';

createScheduledTask({
  taskId: 'daily-baseline-update',
  schedule: '59 23 * * *',  // 每晚11:59
  description: 'Update baseline for all active elders',
  handler: async () => {
    const allElders = await db.getAllActiveElders();
    
    for (const elder of allElders) {
      try {
        const events = await db.getEventsForDate(elder.elder_id, new Date());
        const summary = await db.getDailySummary(elder.elder_id, new Date());
        const devices = await db.getDevicesForElder(elder.elder_id);
        const baseline = await db.getEldersBaseline(elder.elder_id);
        
        const result = await dailyStatusUpdate(
          elder.elder_id,
          events,
          summary,
          devices,
          baseline
        );
        
        // 保存基线
        await db.updateEldersBaseline(elder.elder_id, result.baseline);
        
        // 日志
        console.log(`✅ Updated baseline for ${elder.elder_id}`);
      } catch (error) {
        console.error(`❌ Failed to update baseline for ${elder.elder_id}:`, error);
      }
    }
  }
});
```

### Step 4: 更新数据库schema

确保elder记录包含baseline字段:

```typescript
// 数据库迁移
ALTER TABLE elders ADD COLUMN baseline JSON;
ALTER TABLE elders ADD COLUMN temporary_condition JSON;
```

**TypeScript接口**:
```typescript
interface ElderRecord {
  elder_id: string;
  name: string;
  // ... 其他字段
  baseline?: ElderBaseline;          // NEW
  temporary_condition?: TemporaryCondition;  // NEW
}
```

---

## 使用示例

### 完整集成示例

```typescript
// pages/api/elders/[elder_id]/status.ts

import { generateStatusViewWithBaseline } from '@/lib/statusEngineV2';
import { db } from '@/db';

export default async function handler(req, res) {
  const { elder_id } = req.query;
  
  try {
    // 1. 获取今日所有事件
    const events = await db.getEventsForDate(
      elder_id,
      new Date(new Date().setHours(0, 0, 0, 0))
    );
    
    // 2. 获取今日汇总
    const dailySummary = await db.getDailySummary(elder_id);
    
    // 3. 获取传感器设置
    const devices = await db.getDevicesForElder(elder_id);
    
    // 4. 获取基线
    const baseline = await db.getEldersBaseline(elder_id);
    
    // 5. 生成增强的状态
    const result = await generateStatusViewWithBaseline(
      elder_id,
      events,
      dailySummary,
      devices,
      baseline
    );
    
    // 6. 保存更新后的基线
    if (result.baseline !== baseline) {
      await db.updateEldersBaseline(elder_id, result.baseline);
      console.log(`✅ Baseline updated for ${elder_id}`);
    }
    
    // 7. 返回结果
    res.status(200).json({
      status: result.statusView,
      baseline: result.baseline,
      personalizedSignals: result.personalizedSignals,
      temporaryCondition: result.temporaryCondition,
    });
  } catch (error) {
    console.error('Error generating status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}
```

### React Hook示例

```typescript
// hooks/useEnhancedStatus.ts

import { useQuery } from '@tanstack/react-query';
import { StatusViewModel } from '@/types/behavior';
import { PersonalizedRiskSignal, ElderBaseline, TemporaryCondition } from '@/types/baseline';

interface EnhancedStatusData {
  status: StatusViewModel;
  baseline: ElderBaseline;
  personalizedSignals: PersonalizedRiskSignal[];
  temporaryCondition: TemporaryCondition | null;
}

export function useEnhancedStatus(elder_id: string) {
  return useQuery<EnhancedStatusData>({
    queryKey: ['status', elder_id],
    queryFn: async () => {
      const res = await fetch(`/api/elders/${elder_id}/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      return res.json();
    },
    // 每5分钟刷新一次
    refetchInterval: 5 * 60 * 1000,
  });
}

// 使用
export const Dashboard = ({ elder_id }) => {
  const { data, isLoading, error } = useEnhancedStatus(elder_id);
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <EnhancedStatusView
      status={data!.status}
      personalizedSignals={data!.personalizedSignals}
      baseline={data!.baseline}
      inTemporaryCondition={!!data!.temporaryCondition}
    />
  );
};
```

---

## 关键设计决策

### 1. 通用规则 > 个性化信号

```typescript
// ✅ CORRECT: 通用规则是最小基准
if (universalRisk === 'high') {
  return '⚠️ 高风险警报: 需要立即帮助';
  // 个性化信号永远不会改变这个结果
}

// ❌ WRONG: 不要用个人基线来削弱警报
if (personBaseline.average_activity < 50 && activity < 40) {
  // 即使是"低"的个人基线,也不要忽略明显的低活动
  return 'normal';  // 错误!
}
```

### 2. 学习排除列表

```typescript
// 永远不从这些情况学习:
const exclude_from_learning = (
  has_temporary_condition ||        // ≥3天异常
  has_high_risk_day ||              // 任何高风险日期
  baseline_status === 'needs_review' // 需要人工审查
);
```

### 3. 临时状态处理

```typescript
// 临时状态降低例行告警,但不影响关键告警
if (inTemporaryCondition) {
  // 例行告警: 70-50% 通过率 (概率抑制)
  if (event.risk_level === 'normal' || event.risk_level === 'attention') {
    const suppression = getAlertSuppression(condition);
    if (Math.random() > suppression) return null; // 抑制此告警
  }
  
  // 关键告警: 100% 通过 (永不抑制)
  if (event.risk_level === 'high') {
    return showAlert(event);  // 总是显示
  }
}
```

---

## UI显示示例

### 场景 1: 高风险 (跌倒)

```
🔴 跌倒警报: 检测到跌倒事件，老人已躺下。需要立即帮助。
   通用安全规则已触发。这是系统的最小基准。

   立即检查老人。确保他们安全。

[活动时间: 0分钟] [今日告警: 1] [个性化信号: 0]
```

### 场景 2: 注意 + 个性化信号

```
🟡 注意: 浴室停留超过20分钟。

   浴室访问: 1次

📊 个性化洞察（补充通用规则）
   这些信号显示与 12 天个人基线的偏差。

   🚿 浴室停留时长
   停留时间明显长于平时
   
   基线: 8分钟 | 今天: 22分钟 | 变化 ↑ 175%
   [=========o] 95% 信心度

💡 建议: 活动模式有所偏离。可以温和地询问一切是否安好。

[活动时间: 45分钟] [今日告警: 2] [个性化信号: 1]
```

### 场景 3: 学习中

```
🟢 一切正常，今天没有异常检测。

   活动时间: 180分钟
   浴室访问: 3次

📈 个性化学习进度
   [=====>      ] 4/7 天
   继续收集 (3 天剩余)

[活动时间: 180分钟] [今日告警: 0] [个性化信号: 0]
```

---

## 测试用例

### Test 1: 基线学习

```typescript
test('Baseline learns from stable days only', async () => {
  const baseline = createInitialBaseline('elder_1');
  
  // Day 1-3: 稳定日期
  for (let i = 0; i < 3; i++) {
    const updated = updateBaseline(baseline, {
      date: `day_${i}`,
      total_activity_minutes: 180,
      // ... 其他字段
    }, false);  // 不排除
    baseline = updated;
  }
  
  // Day 4: 高风险日期
  const afterHighRisk = updateBaseline(baseline, {
    date: 'day_4',
    total_activity_minutes: 50,  // 异常低
    // ...
  }, true);  // 排除学习
  
  // 基线应该忽略高风险日期
  expect(afterHighRisk.average_daily_activity_minutes).toEqual(
    baseline.average_daily_activity_minutes
  );
});
```

### Test 2: 个性化信号

```typescript
test('Personalized signals show baseline comparison', async () => {
  const baseline: ElderBaseline = {
    average_daily_activity_minutes: 180,
    // ...
  };
  
  const todaySummary = {
    total_activity_minutes: 90,  // 50% 下降
  };
  
  const comparison = compareToBaseline(todaySummary, baseline);
  
  expect(comparison.signals).toHaveLength(1);
  expect(comparison.signals[0].signal_type).toBe('activity_deviation');
  expect(comparison.signals[0].deviation_ratio).toBeCloseTo(-0.5, 1);
  expect(comparison.signals[0].risk_level).toBe('high');
});
```

### Test 3: 临时状态

```typescript
test('Temporary condition blocks learning', async () => {
  const events = [
    { risk_level: 'high' },
    { risk_level: 'high' },
    { risk_level: 'high' },  // ≥3 days
  ];
  
  const { has_condition } = detectTemporaryCondition(events);
  expect(has_condition).toBe(true);
  
  // 在临时状态下不应该学习
  const baseline = createInitialBaseline('elder_1');
  const result = await generateStatusViewWithBaseline(
    'elder_1',
    events,
    dailyData,
    devices,
    baseline
  );
  
  // 应该返回相同的基线(未更新)
  expect(result.baseline.baseline_days_collected).toBe(
    baseline.baseline_days_collected
  );
});
```

---

## 监控检查清单

部署后监控:

- [ ] ✅ Baseline 收集率 (目标: 95% 在第7天达到active)
- [ ] ✅ 个性化信号生成 (目标: >50% 的日期有信号)
- [ ] ✅ 临时状态检测 (目标: 3+ 天异常内24小时检测)
- [ ] ✅ 告警准确率 (目标: >90% 真阳性)
- [ ] ✅ UI 显示 (个性化信号是否正确显示)
- [ ] ✅ 数据库更新 (baseline 是否每日更新)
- [ ] ✅ 没有学习污染 (高风险日期是否被排除)

---

## 常见问题

**Q: 基线学习多快?**  
A: 7天后变为活跃。新数据获得15%权重,滚动平均85%。所以看到显著变化需要2-3周。

**Q: 如果基线错了怎么办?**  
A: 如果连续异常≥3天,系统将标记为"需_审查"并停止学习。可以手动重置。

**Q: 个性化信号会替代通用规则吗?**  
A: 绝不。通用规则是最小基准。个性化信号只提供背景。高风险告警总是显示。

**Q: 临时状态时间多长?**  
A: 通常2-3天。需要≥2天恢复进入"恢复",≥3天进入"已解决",然后清除。

**Q: 如果我想禁用个性化?**  
A: 在EnhancedStatusView中,if (!baseline || baseline.baseline_status !== 'active') 时就不显示。

---

## 部署清单

在生产环境中:

- [ ] 数据库 schema 更新 (baseline + temporary_condition 字段)
- [ ] statusEngineV2 导入
- [ ] EnhancedStatusView 导入
- [ ] 日常更新定时任务配置
- [ ] API 端点更新 (/api/elders/[id]/status)
- [ ] React hooks 更新
- [ ] 现有elders 初始化 baseline (如果尚未存在)
- [ ] UI 测试 (确保显示正确)
- [ ] 监控仪表板配置
- [ ] 用户文档更新

---

**版本**: 1.0 | **日期**: April 2026 | **状态**: 就绪集成
