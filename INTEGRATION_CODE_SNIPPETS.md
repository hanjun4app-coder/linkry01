# 集成代码片段

**快速参考**: 将baseline和个性化信号集成到你的项目中

---

## 1️⃣ API 端点 - 日常状态

```typescript
// pages/api/elders/[elder_id]/status.ts

import { generateStatusViewWithBaseline } from '@/lib/statusEngineV2';
import { ElderBaseline } from '@/types/baseline';
import { db } from '@/db';

export default async function handler(req, res) {
  const { elder_id } = req.query;
  
  try {
    // 获取数据
    const [events, dailySummary, devices, baseline] = await Promise.all([
      db.getEventsForDate(elder_id, new Date()),
      db.getDailySummary(elder_id),
      db.getDevicesForElder(elder_id),
      db.getEldersBaseline(elder_id)
    ]);

    // 生成增强状态
    const result = await generateStatusViewWithBaseline(
      elder_id,
      events,
      dailySummary,
      devices,
      baseline
    );

    // 保存基线
    if (result.baseline !== baseline) {
      await db.updateEldersBaseline(elder_id, result.baseline);
    }

    // 返回
    res.status(200).json({
      status: result.statusView,
      baseline: result.baseline,
      personalizedSignals: result.personalizedSignals,
      temporaryCondition: result.temporaryCondition,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
```

---

## 2️⃣ React Component - 显示状态

```typescript
// pages/elders/[elder_id].tsx

import EnhancedStatusView from '@/components/EnhancedStatusView';
import { useQuery } from '@tanstack/react-query';

interface StatusData {
  status: StatusViewModel;
  baseline: ElderBaseline;
  personalizedSignals: PersonalizedRiskSignal[];
  temporaryCondition: TemporaryCondition | null;
}

export default function ElderPage({ elder_id }) {
  const { data, isLoading, error } = useQuery<StatusData>({
    queryKey: ['status', elder_id],
    queryFn: () => fetch(`/api/elders/${elder_id}/status`).then(r => r.json()),
    refetchInterval: 5 * 60 * 1000,  // 每5分钟
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error</div>;

  return (
    <div className="p-6">
      <h1>老人状态</h1>
      <EnhancedStatusView
        status={data!.status}
        personalizedSignals={data!.personalizedSignals}
        baseline={data!.baseline}
        inTemporaryCondition={!!data!.temporaryCondition}
      />
    </div>
  );
}
```

---

## 3️⃣ 日常基线更新 - Cron Job

```typescript
// services/baselineScheduler.ts

import { dailyStatusUpdate } from '@/lib/statusEngineV2';
import { db } from '@/db';
import cron from 'node-cron';

// 每晚11:59运行
export function setupBaselineScheduler() {
  cron.schedule('59 23 * * *', async () => {
    console.log('🌙 Starting daily baseline update...');
    
    const elders = await db.getAllActiveElders();
    const results = {
      success: 0,
      failed: 0,
      updated: 0,
    };

    for (const elder of elders) {
      try {
        const [events, summary, devices, baseline] = await Promise.all([
          db.getEventsForDate(elder.elder_id, new Date()),
          db.getDailySummary(elder.elder_id),
          db.getDevicesForElder(elder.elder_id),
          db.getEldersBaseline(elder.elder_id)
        ]);

        const result = await dailyStatusUpdate(
          elder.elder_id,
          events,
          summary,
          devices,
          baseline
        );

        // 保存基线
        if (result.baseline !== baseline) {
          await db.updateEldersBaseline(elder.elder_id, result.baseline);
          results.updated++;
        }

        results.success++;
      } catch (error) {
        console.error(`Failed for ${elder.elder_id}:`, error);
        results.failed++;
      }
    }

    console.log('✅ Baseline update complete:', results);
  });
}
```

---

## 4️⃣ 数据库迁移 - 添加Baseline字段

```typescript
// migrations/001_add_baseline_fields.ts

import { Pool } from 'pg';

export async function up(pool: Pool) {
  const client = await pool.connect();
  
  try {
    // 添加baseline和temporary_condition列
    await client.query(`
      ALTER TABLE elders 
      ADD COLUMN IF NOT EXISTS baseline JSONB,
      ADD COLUMN IF NOT EXISTS temporary_condition JSONB;
    `);

    // 为现有elders初始化baseline
    await client.query(`
      UPDATE elders 
      SET baseline = jsonb_build_object(
        'elder_id', elder_id,
        'baseline_status', 'collecting',
        'baseline_days_collected', 0,
        'average_wake_time', 7,
        'average_sleep_time', 22,
        'average_daily_activity_minutes', 180,
        'average_bathroom_duration_minutes', 15,
        'average_bathroom_count', 4,
        'average_night_wake_count', 1,
        'average_daytime_bed_minutes', 60,
        'usual_active_zones', '["living_room", "kitchen", "bathroom"]',
        'last_updated_at', NOW()::text,
        'created_at', NOW()::text,
        'days_in_temporary_condition', 0
      )
      WHERE baseline IS NULL;
    `);

    console.log('✅ Migration complete');
  } finally {
    client.release();
  }
}

export async function down(pool: Pool) {
  const client = await pool.connect();
  
  try {
    await client.query(`
      ALTER TABLE elders 
      DROP COLUMN IF EXISTS baseline,
      DROP COLUMN IF EXISTS temporary_condition;
    `);
  } finally {
    client.release();
  }
}
```

---

## 5️⃣ 数据库操作 - Baseline CRUD

```typescript
// db/elders.ts

import { ElderBaseline, TemporaryCondition } from '@/types/baseline';
import { db } from '@/db';

// 获取baseline
export async function getEldersBaseline(elder_id: string): Promise<ElderBaseline | null> {
  const result = await db.query(
    'SELECT baseline FROM elders WHERE elder_id = $1',
    [elder_id]
  );
  return result.rows[0]?.baseline || null;
}

// 更新baseline
export async function updateEldersBaseline(
  elder_id: string,
  baseline: ElderBaseline
): Promise<void> {
  await db.query(
    'UPDATE elders SET baseline = $1 WHERE elder_id = $2',
    [baseline, elder_id]
  );
}

// 获取临时状态
export async function getTemporaryCondition(
  elder_id: string
): Promise<TemporaryCondition | null> {
  const result = await db.query(
    'SELECT temporary_condition FROM elders WHERE elder_id = $1',
    [elder_id]
  );
  return result.rows[0]?.temporary_condition || null;
}

// 更新临时状态
export async function updateTemporaryCondition(
  elder_id: string,
  condition: TemporaryCondition | null
): Promise<void> {
  await db.query(
    'UPDATE elders SET temporary_condition = $1 WHERE elder_id = $2',
    [condition, elder_id]
  );
}
```

---

## 6️⃣ React Hook - 使用数据

```typescript
// hooks/useEnhancedStatus.ts

import { useQuery } from '@tanstack/react-query';
import { StatusViewModel } from '@/types/behavior';
import { ElderBaseline, PersonalizedRiskSignal, TemporaryCondition } from '@/types/baseline';

interface EnhancedStatusData {
  status: StatusViewModel;
  baseline: ElderBaseline;
  personalizedSignals: PersonalizedRiskSignal[];
  temporaryCondition: TemporaryCondition | null;
}

export function useEnhancedStatus(elder_id: string) {
  return useQuery<EnhancedStatusData>({
    queryKey: ['enhanced-status', elder_id],
    queryFn: async () => {
      const res = await fetch(`/api/elders/${elder_id}/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      return res.json();
    },
    refetchInterval: 5 * 60 * 1000,  // 5 minutes
    staleTime: 2 * 60 * 1000,        // 2 minutes
  });
}

// 使用示例
export function StatusDashboard({ elder_id }: { elder_id: string }) {
  const { data, isLoading, error } = useEnhancedStatus(elder_id);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!data) return <div>No data</div>;

  return (
    <EnhancedStatusView
      status={data.status}
      personalizedSignals={data.personalizedSignals}
      baseline={data.baseline}
      inTemporaryCondition={!!data.temporaryCondition}
    />
  );
}
```

---

## 7️⃣ 监控指标 - 仪表板

```typescript
// pages/admin/metrics.tsx

import { useQuery } from '@tanstack/react-query';

export function MetricsDashboard() {
  const { data: metrics } = useQuery({
    queryKey: ['baseline-metrics'],
    queryFn: () => fetch('/api/admin/metrics/baseline').then(r => r.json()),
    refetchInterval: 30 * 1000,  // 30 seconds
  });

  if (!metrics) return null;

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* 基线收集进度 */}
      <Card title="Baseline Collection">
        <div className="space-y-2">
          <Metric 
            label="Active (≥7 days)" 
            value={`${metrics.baselineActive}%`}
            target="≥95%"
          />
          <Metric 
            label="Collecting (0-6 days)" 
            value={`${metrics.baselineCollecting}%`}
          />
          <Metric 
            label="Needs Review" 
            value={`${metrics.baselineNeedsReview}`}
            color="warning"
          />
        </div>
      </Card>

      {/* 临时状态 */}
      <Card title="Temporary Conditions">
        <div className="space-y-2">
          <Metric 
            label="Active Conditions" 
            value={metrics.activeConditions}
          />
          <Metric 
            label="Avg Duration" 
            value={`${metrics.avgConditionDuration}h`}
          />
          <Metric 
            label="Recovery Rate" 
            value={`${metrics.autoRecoveryRate}%`}
            color="success"
          />
        </div>
      </Card>

      {/* 个性化信号 */}
      <Card title="Personalized Signals">
        <div className="space-y-2">
          <Metric 
            label="Generated Today" 
            value={metrics.signalsGenerated}
          />
          <Metric 
            label="Avg Deviation" 
            value={`${metrics.avgDeviation}%`}
          />
          <Metric 
            label="High Confidence" 
            value={`${metrics.highConfidenceSignals}%`}
          />
        </div>
      </Card>

      {/* 告警质量 */}
      <Card title="Alert Quality">
        <div className="space-y-2">
          <Metric 
            label="True Positives" 
            value={`${metrics.truePositiveRate}%`}
            target="≥90%"
            color={metrics.truePositiveRate >= 90 ? 'success' : 'warning'}
          />
          <Metric 
            label="False Positives" 
            value={`${metrics.falsePositiveRate}%`}
            target="<10%"
            color={metrics.falsePositiveRate < 10 ? 'success' : 'warning'}
          />
          <Metric 
            label="Missed Events" 
            value={`${metrics.missedEvents}`}
            color="error"
          />
        </div>
      </Card>
    </div>
  );
}

// API端点
// pages/api/admin/metrics/baseline.ts
export default async function handler(req, res) {
  const metrics = await db.getBaselineMetrics();
  res.status(200).json(metrics);
}
```

---

## 8️⃣ 测试 - 关键场景

```typescript
// __tests__/integration/baseline.test.ts

import { generateStatusViewWithBaseline, dailyStatusUpdate } from '@/lib/statusEngineV2';
import { createInitialBaseline, updateBaseline } from '@/lib/baselineEngine';
import { detectTemporaryCondition } from '@/lib/temporaryConditionDetector';

describe('Baseline Learning Integration', () => {
  it('should learn from stable days only', async () => {
    const baseline = createInitialBaseline('elder_1');
    
    // Day 1-3: 稳定
    for (let i = 0; i < 3; i++) {
      const updated = updateBaseline(baseline, {
        date: `2024-01-0${i+1}`,
        total_activity_minutes: 180,
        bathroom_events: 4,
        bathroom_total_minutes: 60,
        night_wake_count: 1,
        daytime_bed_minutes: 60,
        wake_time: 7,
        sleep_time: 22,
        active_zones: ['living_room'],
        status: 'stable',
        should_exclude_from_learning: false,
      }, false);  // 不排除
    }

    expect(baseline.baseline_days_collected).toBe(3);
    expect(baseline.average_daily_activity_minutes).toBeCloseTo(180, 0);
  });

  it('should not learn from high risk days', async () => {
    let baseline = createInitialBaseline('elder_1');
    
    const stableData = {
      total_activity_minutes: 180,
      bathroom_events: 4,
      bathroom_total_minutes: 60,
      night_wake_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room'],
      status: 'stable' as const,
      should_exclude_from_learning: false,
      date: '2024-01-01',
    };

    baseline = updateBaseline(baseline, stableData, false);
    
    // High risk day - should be excluded
    const beforeHighRisk = baseline.average_daily_activity_minutes;
    const highRiskData = { ...stableData, total_activity_minutes: 30 };
    baseline = updateBaseline(baseline, highRiskData, true);  // 排除!
    
    expect(baseline.average_daily_activity_minutes).toBe(beforeHighRisk);
  });

  it('should detect temporary condition and block learning', async () => {
    const events = [
      { risk_level: 'high', event_type: 'test' },
      { risk_level: 'high', event_type: 'test' },
      { risk_level: 'high', event_type: 'test' },
    ];

    const { has_condition } = detectTemporaryCondition(events);
    expect(has_condition).toBe(true);
  });

  it('should generate personalized signals', async () => {
    const baseline: ElderBaseline = {
      elder_id: 'elder_1',
      baseline_status: 'active',
      baseline_days_collected: 7,
      average_daily_activity_minutes: 180,
      average_bathroom_duration_minutes: 15,
      average_bathroom_count: 4,
      average_night_wake_count: 1,
      average_daytime_bed_minutes: 60,
      average_wake_time: 7,
      average_sleep_time: 22,
      usual_active_zones: ['living_room'],
      created_at: new Date().toISOString(),
      last_updated_at: new Date().toISOString(),
      days_in_temporary_condition: 0,
    };

    const summary = {
      total_activity_minutes: 90,  // 50% drop
      bathroom_count: 4,
      bathroom_total_minutes: 60,
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room'],
    };

    const { signals } = compareToBaseline(summary, baseline);
    
    expect(signals).toHaveLength(1);
    expect(signals[0].signal_type).toBe('activity_deviation');
    expect(Math.abs(signals[0].deviation_ratio + 0.5)).toBeLessThan(0.01);
  });
});
```

---

## 📋 集成清单

实施这些集成时:

- [ ] 创建statusEngineV2.ts
- [ ] 创建EnhancedStatusView.tsx
- [ ] 更新API端点 /api/elders/[id]/status
- [ ] 添加数据库字段 (baseline, temporary_condition)
- [ ] 为现有elders初始化baseline
- [ ] 设置daily baseline更新cron
- [ ] 创建监控指标页面
- [ ] 添加测试用例
- [ ] 部署并监控
- [ ] 更新用户文档

---

**快速检查**: 所有代码都已准备好复制粘贴。按照数字顺序 (1️⃣-8️⃣) 集成。
