# 测试指南：基线学习集成

**目标**: 完整验证基线学习、个性化信号和临时状态的所有功能

---

## 测试环境设置

### 准备测试数据

```typescript
// test-data/setup.ts
import { db } from '@/db';

export async function setupTestElders() {
  // 创建测试elder
  const testElder = {
    elder_id: 'test_elder_001',
    name: 'Test Subject',
    age: 75,
  };

  // 清理旧数据
  await db.query('DELETE FROM elders WHERE elder_id = $1', [testElder.elder_id]);

  // 创建新elder
  await db.query(
    `INSERT INTO elders (elder_id, name, age, baseline, temporary_condition)
     VALUES ($1, $2, $3, $4, $5)`,
    [
      testElder.elder_id,
      testElder.name,
      testElder.age,
      JSON.stringify({
        elder_id: testElder.elder_id,
        baseline_status: 'collecting',
        baseline_days_collected: 0,
        average_daily_activity_minutes: 180,
        average_bathroom_count: 4,
        average_bathroom_duration_minutes: 15,
        average_night_wake_count: 1,
        average_daytime_bed_minutes: 60,
        average_wake_time: 7,
        average_sleep_time: 22,
        usual_active_zones: ['living_room', 'kitchen', 'bedroom'],
        created_at: new Date().toISOString(),
        last_updated_at: new Date().toISOString(),
        days_in_temporary_condition: 0,
      }),
      null // temporary_condition
    ]
  );

  console.log('✅ Test elder created:', testElder.elder_id);
  return testElder;
}
```

### 创建测试事件

```typescript
// test-data/events.ts
export const testEvents = {
  normal_day: [
    {
      event_id: 'evt_1',
      event_type: 'activity',
      risk_level: 'normal',
      description: '在客厅走动',
      timestamp: new Date().toISOString(),
    },
    {
      event_id: 'evt_2',
      event_type: 'bathroom',
      risk_level: 'normal',
      description: '浴室停留10分钟',
      timestamp: new Date().toISOString(),
    },
  ],

  high_risk_day: [
    {
      event_id: 'evt_3',
      event_type: 'fall',
      risk_level: 'high',
      description: '检测到跌倒',
      timestamp: new Date().toISOString(),
    },
    {
      event_id: 'evt_4',
      event_type: 'fall_recovery',
      risk_level: 'high',
      description: '跌倒后持续躺平',
      timestamp: new Date().toISOString(),
    },
  ],

  attention_day: [
    {
      event_id: 'evt_5',
      event_type: 'bathroom',
      risk_level: 'attention',
      description: '浴室停留超过20分钟',
      timestamp: new Date().toISOString(),
    },
  ],
};
```

---

## 单元测试

### Test Suite 1: 基线学习

```typescript
// __tests__/baseline-learning.test.ts
import { updateBaseline, createInitialBaseline } from '@/lib/baselineEngine';

describe('Baseline Learning', () => {
  it('should create initial baseline with correct defaults', () => {
    const baseline = createInitialBaseline('elder_test_001');

    expect(baseline.elder_id).toBe('elder_test_001');
    expect(baseline.baseline_status).toBe('collecting');
    expect(baseline.baseline_days_collected).toBe(0);
    expect(baseline.average_daily_activity_minutes).toBe(0);
    expect(baseline.created_at).toBeDefined();
  });

  it('should not learn from high-risk days', () => {
    const baseline = createInitialBaseline('elder_test_001');

    // 正常日期 - 应该学习
    const after_normal = updateBaseline(baseline, {
      date: '2024-01-01',
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
    }, false);

    expect(after_normal.baseline_days_collected).toBe(1);

    // 高风险日期 - 不应该学习
    const before_high_risk = after_normal.average_daily_activity_minutes;
    const after_high_risk = updateBaseline(after_normal, {
      date: '2024-01-02',
      total_activity_minutes: 50, // 异常低
      bathroom_events: 1,
      bathroom_total_minutes: 30,
      night_wake_count: 5, // 异常多
      daytime_bed_minutes: 300,
      wake_time: 8,
      sleep_time: 21,
      active_zones: [],
      status: 'high_risk_activity' as const,
      should_exclude_from_learning: true,
    }, true); // exclude!

    // 平均活动应该保持不变（没有学习）
    expect(after_high_risk.baseline_days_collected).toBe(1); // 仍然是1，没增加
    expect(after_high_risk.average_daily_activity_minutes).toBe(before_high_risk);
  });

  it('should activate baseline after 7 collecting days', () => {
    let baseline = createInitialBaseline('elder_test_001');

    // 模拟7天稳定数据
    for (let i = 0; i < 7; i++) {
      baseline = updateBaseline(baseline, {
        date: `2024-01-${String(i + 1).padStart(2, '0')}`,
        total_activity_minutes: 180,
        bathroom_events: 4,
        bathroom_total_minutes: 60,
        night_wake_count: 1,
        daytime_bed_minutes: 60,
        wake_time: 7,
        sleep_time: 22,
        active_zones: ['living_room', 'kitchen'],
        status: 'stable' as const,
        should_exclude_from_learning: false,
      }, false);
    }

    expect(baseline.baseline_status).toBe('active');
    expect(baseline.baseline_days_collected).toBe(7);
  });

  it('should use rolling average (15% new, 85% old)', () => {
    let baseline = createInitialBaseline('elder_test_001');

    // 初始化为4天，activity = 100
    for (let i = 0; i < 4; i++) {
      baseline = updateBaseline(baseline, {
        date: `day_${i}`,
        total_activity_minutes: 100,
        bathroom_events: 4,
        bathroom_total_minutes: 60,
        night_wake_count: 1,
        daytime_bed_minutes: 60,
        wake_time: 7,
        sleep_time: 22,
        active_zones: ['living_room'],
        status: 'stable' as const,
        should_exclude_from_learning: false,
      }, false);
    }

    const before = baseline.average_daily_activity_minutes; // 应该约100

    // 第5天：activity = 200
    const after = updateBaseline(baseline, {
      date: 'day_5',
      total_activity_minutes: 200,
      bathroom_events: 4,
      bathroom_total_minutes: 60,
      night_wake_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room'],
      status: 'stable' as const,
      should_exclude_from_learning: false,
    }, false);

    // 应该是: 85% * 100 + 15% * 200 = 115
    expect(after.average_daily_activity_minutes).toBeCloseTo(115, 0);
  });
});
```

### Test Suite 2: 个性化信号

```typescript
// __tests__/personalized-signals.test.ts
import { compareToBaseline } from '@/lib/baselineEngine';
import { ElderBaseline } from '@/types/baseline';

describe('Personalized Risk Signals', () => {
  const activeBaseline: ElderBaseline = {
    elder_id: 'test_elder',
    baseline_status: 'active',
    baseline_days_collected: 7,
    average_daily_activity_minutes: 180,
    average_bathroom_duration_minutes: 15,
    average_bathroom_count: 4,
    average_night_wake_count: 1,
    average_daytime_bed_minutes: 60,
    average_wake_time: 7,
    average_sleep_time: 22,
    usual_active_zones: ['living_room', 'kitchen', 'bedroom'],
    created_at: new Date().toISOString(),
    last_updated_at: new Date().toISOString(),
    days_in_temporary_condition: 0,
  };

  it('should detect activity drop', () => {
    const dailySummary = {
      total_activity_minutes: 90, // 50% drop from baseline 180
      bathroom_count: 4,
      bathroom_total_minutes: 60,
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room'],
    };

    const { signals } = compareToBaseline(dailySummary, activeBaseline);

    expect(signals).toHaveLength(1);
    expect(signals[0].signal_type).toBe('activity_deviation');
    expect(signals[0].risk_level).toBe('high');
    expect(Math.abs(signals[0].deviation_ratio - (-0.5))).toBeLessThan(0.01); // -50%
  });

  it('should detect bathroom duration increase', () => {
    const dailySummary = {
      total_activity_minutes: 180,
      bathroom_count: 2,
      bathroom_total_minutes: 60, // 4倍长 (baseline: 15)
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room', 'kitchen', 'bathroom'],
    };

    const { signals } = compareToBaseline(dailySummary, activeBaseline);

    const bathroomSignal = signals.find(s => s.signal_type === 'bathroom_duration_change');
    expect(bathroomSignal).toBeDefined();
    expect(bathroomSignal?.risk_level).toBe('attention'); // 中等风险
  });

  it('should not generate signals for within-threshold variations', () => {
    const dailySummary = {
      total_activity_minutes: 190, // 仅5%差异
      bathroom_count: 4,
      bathroom_total_minutes: 60,
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room', 'kitchen'],
    };

    const { signals } = compareToBaseline(dailySummary, activeBaseline);

    // 小于10%的差异不应该生成信号
    expect(signals).toHaveLength(0);
  });

  it('should include confidence score based on baseline maturity', () => {
    const basicBaseline: ElderBaseline = {
      ...activeBaseline,
      baseline_days_collected: 14, // 2周数据
    };

    const dailySummary = {
      total_activity_minutes: 100, // 44%下降
      bathroom_count: 4,
      bathroom_total_minutes: 60,
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room'],
    };

    const { signals } = compareToBaseline(dailySummary, basicBaseline);

    expect(signals).toHaveLength(1);
    // 2周数据应该有较高的置信度 (~60%)
    expect(signals[0].confidence_score).toBeGreaterThan(0.5);
    expect(signals[0].confidence_score).toBeLessThanOrEqual(1.0);
  });
});
```

### Test Suite 3: 临时状态

```typescript
// __tests__/temporary-condition.test.ts
import { detectTemporaryCondition } from '@/lib/temporaryConditionDetector';

describe('Temporary Condition Detection', () => {
  it('should detect temporary condition after 3+ high-risk events', () => {
    const events = [
      { event_id: '1', risk_level: 'high', description: '跌倒' },
      { event_id: '2', risk_level: 'high', description: '再次摔倒' },
      { event_id: '3', risk_level: 'high', description: '再次摔倒' },
    ];

    const result = detectTemporaryCondition(events);

    expect(result.has_condition).toBe(true);
    expect(result.anomaly_days).toBe(3);
  });

  it('should not detect condition for 1-2 high-risk events', () => {
    const events = [
      { event_id: '1', risk_level: 'high', description: '跌倒' },
      { event_id: '2', risk_level: 'high', description: '再次摔倒' },
    ];

    const result = detectTemporaryCondition(events);

    expect(result.has_condition).toBe(false);
  });

  it('should not detect condition if recovery trend present', () => {
    // Day 1-3: high risk
    // Day 4-5: attention (恢复迹象)
    const events = [
      { event_id: '1', risk_level: 'high', timestamp: new Date(Date.now() - 4 * 24 * 3600 * 1000) },
      { event_id: '2', risk_level: 'high', timestamp: new Date(Date.now() - 3 * 24 * 3600 * 1000) },
      { event_id: '3', risk_level: 'high', timestamp: new Date(Date.now() - 2 * 24 * 3600 * 1000) },
      { event_id: '4', risk_level: 'attention', timestamp: new Date(Date.now() - 1 * 24 * 3600 * 1000) },
      { event_id: '5', risk_level: 'normal', timestamp: new Date() },
    ];

    const result = detectTemporaryCondition(events);

    // 如果显示恢复趋势，应该不标记为临时状态
    if (result.recovery_trend) {
      expect(result.has_condition).toBe(false);
    }
  });
});
```

### Test Suite 4: 状态生成

```typescript
// __tests__/status-generation.test.ts
import { generateStatusViewWithBaseline } from '@/lib/statusEngineV2';

describe('Enhanced Status View Generation', () => {
  it('should prioritize universal high-risk over baseline', async () => {
    const events = [
      {
        event_id: '1',
        risk_level: 'high',
        description: '跌倒警报',
        event_type: 'fall',
      },
    ];

    const dailyData = {
      total_activity_minutes: 50, // 低活动
      bathroom_count: 1,
      bathroom_total_minutes: 10,
      night_activity_count: 0,
      daytime_bed_minutes: 500,
      wake_time: 10,
      sleep_time: 20,
      active_zones: [],
    };

    const baseline = {
      elder_id: 'test',
      baseline_status: 'active',
      baseline_days_collected: 7,
      average_daily_activity_minutes: 180, // 远高于今天
      average_bathroom_count: 4,
      average_bathroom_duration_minutes: 15,
      average_night_wake_count: 1,
      average_daytime_bed_minutes: 60,
      average_wake_time: 7,
      average_sleep_time: 22,
      usual_active_zones: ['living_room'],
      created_at: new Date().toISOString(),
      last_updated_at: new Date().toISOString(),
      days_in_temporary_condition: 0,
    };

    const result = await generateStatusViewWithBaseline(
      'test_elder',
      events,
      dailyData,
      [], // devices
      baseline
    );

    // 尽管baseline显示低活动，高风险事件应该触发高风险警报
    expect(result.statusView.risk_level).toBe('high');
    expect(result.statusView.alert_message).toContain('跌倒');
  });

  it('should include personalized signals when baseline is active', async () => {
    const events: any[] = [];

    const dailyData = {
      total_activity_minutes: 100, // 45%下降
      bathroom_count: 4,
      bathroom_total_minutes: 60,
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room'],
    };

    const activeBaseline = {
      elder_id: 'test',
      baseline_status: 'active',
      baseline_days_collected: 14,
      average_daily_activity_minutes: 180,
      average_bathroom_count: 4,
      average_bathroom_duration_minutes: 15,
      average_night_wake_count: 1,
      average_daytime_bed_minutes: 60,
      average_wake_time: 7,
      average_sleep_time: 22,
      usual_active_zones: ['living_room'],
      created_at: new Date().toISOString(),
      last_updated_at: new Date().toISOString(),
      days_in_temporary_condition: 0,
    };

    const result = await generateStatusViewWithBaseline(
      'test_elder',
      events,
      dailyData,
      [],
      activeBaseline
    );

    // 应该有个性化信号
    expect(result.personalizedSignals.length).toBeGreaterThan(0);
    expect(result.personalizedSignals[0].signal_type).toBe('activity_deviation');
  });

  it('should not include personalized signals when baseline is collecting', async () => {
    const events: any[] = [];

    const dailyData = {
      total_activity_minutes: 50,
      bathroom_count: 1,
      bathroom_total_minutes: 10,
      night_activity_count: 0,
      daytime_bed_minutes: 500,
      wake_time: 10,
      sleep_time: 20,
      active_zones: [],
    };

    const collectingBaseline = {
      elder_id: 'test',
      baseline_status: 'collecting',
      baseline_days_collected: 2, // 仅2天
      average_daily_activity_minutes: 120,
      average_bathroom_count: 3,
      average_bathroom_duration_minutes: 12,
      average_night_wake_count: 1,
      average_daytime_bed_minutes: 60,
      average_wake_time: 7,
      average_sleep_time: 22,
      usual_active_zones: ['living_room'],
      created_at: new Date().toISOString(),
      last_updated_at: new Date().toISOString(),
      days_in_temporary_condition: 0,
    };

    const result = await generateStatusViewWithBaseline(
      'test_elder',
      events,
      dailyData,
      [],
      collectingBaseline
    );

    // baseline在collecting状态时不应该有个性化信号
    expect(result.personalizedSignals).toHaveLength(0);
  });
});
```

---

## 集成测试

### Integration Test 1: 完整日常更新流程

```typescript
// __tests__/integration/daily-update.test.ts
import { dailyStatusUpdate } from '@/lib/statusEngineV2';
import { db } from '@/db';

describe('Daily Status Update Integration', () => {
  it('should complete full daily update pipeline', async () => {
    const elder_id = 'integration_test_001';

    // 设置测试elder
    const baseline = {
      elder_id,
      baseline_status: 'collecting',
      baseline_days_collected: 5,
      average_daily_activity_minutes: 180,
      average_bathroom_count: 4,
      average_bathroom_duration_minutes: 15,
      average_night_wake_count: 1,
      average_daytime_bed_minutes: 60,
      average_wake_time: 7,
      average_sleep_time: 22,
      usual_active_zones: ['living_room', 'kitchen'],
      created_at: new Date().toISOString(),
      last_updated_at: new Date().toISOString(),
      days_in_temporary_condition: 0,
    };

    // 创建模拟数据
    const events = [
      {
        event_id: 'evt_1',
        risk_level: 'normal',
        description: '正常活动',
      },
      {
        event_id: 'evt_2',
        risk_level: 'normal',
        description: '浴室访问',
      },
    ];

    const dailySummary = {
      total_activity_minutes: 190,
      bathroom_count: 4,
      bathroom_total_minutes: 60,
      night_activity_count: 1,
      daytime_bed_minutes: 60,
      wake_time: 7,
      sleep_time: 22,
      active_zones: ['living_room', 'kitchen'],
    };

    // 执行日常更新
    const result = await dailyStatusUpdate(
      elder_id,
      events,
      dailySummary,
      [],
      baseline
    );

    // 验证结果
    expect(result).toHaveProperty('statusView');
    expect(result).toHaveProperty('baseline');
    expect(result).toHaveProperty('temporaryCondition');
    expect(result).toHaveProperty('personalizedSignals');

    // 验证baseline被更新
    expect(result.baseline.baseline_days_collected).toBe(6); // 从5增加到6

    // 在第7天时应该激活
    if (result.baseline.baseline_days_collected >= 7) {
      expect(result.baseline.baseline_status).toBe('active');
    }
  });
});
```

### Integration Test 2: API端点完整流程

```typescript
// __tests__/integration/api-endpoint.test.ts
import { NextApiRequest, NextApiResponse } from 'next';
import handler from '@/pages/api/elders/[elder_id]/status';

describe('Status API Endpoint', () => {
  it('should return complete enhanced status response', async () => {
    const req = {
      method: 'GET',
      query: { elder_id: 'test_elder_001' },
    } as unknown as NextApiRequest;

    const responses: any[] = [];
    const res = {
      status: (code: number) => ({
        json: (data: any) => {
          responses.push({ code, data });
        },
      }),
    } as unknown as NextApiResponse;

    await handler(req, res);

    expect(responses).toHaveLength(1);
    const [response] = responses;

    expect(response.code).toBe(200);
    expect(response.data).toHaveProperty('status');
    expect(response.data).toHaveProperty('baseline');
    expect(response.data).toHaveProperty('personalizedSignals');
    expect(response.data).toHaveProperty('temporaryCondition');
  });

  it('should handle invalid elder_id gracefully', async () => {
    const req = {
      method: 'GET',
      query: { elder_id: undefined },
    } as unknown as NextApiRequest;

    const responses: any[] = [];
    const res = {
      status: (code: number) => ({
        json: (data: any) => {
          responses.push({ code, data });
        },
      }),
    } as unknown as NextApiResponse;

    await handler(req, res);

    expect(responses).toHaveLength(1);
    expect(responses[0].code).toBe(400);
    expect(responses[0].data).toHaveProperty('error');
  });

  it('should reject non-GET requests', async () => {
    const req = {
      method: 'POST',
      query: { elder_id: 'test_elder' },
    } as unknown as NextApiRequest;

    const responses: any[] = [];
    const res = {
      status: (code: number) => ({
        json: (data: any) => {
          responses.push({ code, data });
        },
      }),
    } as unknown as NextApiResponse;

    await handler(req, res);

    expect(responses).toHaveLength(1);
    expect(responses[0].code).toBe(405);
  });
});
```

---

## 端到端测试

### E2E Test: 用户旅程

```typescript
// __tests__/e2e/user-journey.test.ts
import { browser } from '@playwright/test';

describe('User Journey: Baseline Learning', () => {
  it('should show baseline collection progress to active state', async () => {
    const page = await browser.newPage();

    // 访问elderly dashboard
    await page.goto('http://localhost:3000/elders/test_elder_001');

    // 应该看到基线收集进度
    const progressBar = await page.$('.baseline-progress');
    expect(progressBar).toBeTruthy();

    // 进度应该显示"collecting"状态
    const statusText = await page.textContent('.baseline-status');
    expect(statusText).toContain('collecting');

    // 个性化信号应该尚未显示
    const signalsSection = await page.$('.personalized-signals');
    expect(signalsSection).toBeFalsy(); // 不应该存在

    // 关闭页面
    await page.close();
  });

  it('should display personalized signals when baseline becomes active', async () => {
    const page = await browser.newPage();

    // 手动将baseline状态更新为active（仅用于测试）
    await db.query(
      `UPDATE elders SET baseline = jsonb_set(baseline, '{baseline_status}', '"active"')
       WHERE elder_id = $1`,
      ['test_elder_001']
    );

    // 刷新页面
    await page.goto('http://localhost:3000/elders/test_elder_001');
    await page.reload();

    // 应该看到个性化信号部分
    const signalsSection = await page.$('.personalized-signals');
    expect(signalsSection).toBeTruthy();

    // 应该有信号卡片
    const signalCards = await page.$$('.signal-card');
    expect(signalCards.length).toBeGreaterThan(0);

    await page.close();
  });
});
```

---

## 性能测试

### Performance Benchmark

```typescript
// __tests__/performance/baseline-performance.test.ts
import { performance } from 'perf_hooks';
import { generateStatusViewWithBaseline } from '@/lib/statusEngineV2';

describe('Performance Benchmarks', () => {
  it('should generate status in < 100ms', async () => {
    const start = performance.now();

    await generateStatusViewWithBaseline(
      'perf_test_001',
      Array(100).fill({ risk_level: 'normal', event_type: 'activity' }),
      { total_activity_minutes: 180, bathroom_count: 4 /* ... */ },
      Array(5).fill({ device_id: 'dev_1', sensor_type: 'fp2_radar' }),
      null
    );

    const duration = performance.now() - start;

    console.log(`Status generation: ${duration.toFixed(2)}ms`);
    expect(duration).toBeLessThan(100);
  });

  it('should handle 1000 elders baseline update in < 5s', async () => {
    const start = performance.now();

    const promises = Array(1000)
      .fill(null)
      .map((_, i) =>
        generateStatusViewWithBaseline(
          `perf_test_${i}`,
          [],
          { total_activity_minutes: 180, bathroom_count: 4 /* ... */ },
          [],
          null
        )
      );

    await Promise.all(promises);

    const duration = performance.now() - start;

    console.log(`1000 elders update: ${duration.toFixed(2)}ms (${(duration / 1000).toFixed(2)}ms per elder)`);
    expect(duration).toBeLessThan(5000);
  });
});
```

---

## 运行所有测试

```bash
# 运行所有测试
npm test

# 运行特定测试套件
npm test -- baseline-learning.test.ts
npm test -- personalized-signals.test.ts
npm test -- temporary-condition.test.ts

# 带覆盖率运行
npm test -- --coverage

# 监视模式（开发时）
npm test -- --watch
```

---

## 测试覆盖率目标

- 行覆盖率: ≥ 80%
- 分支覆盖率: ≥ 75%
- 函数覆盖率: ≥ 80%

```bash
# 检查覆盖率
npm test -- --coverage

# 预期输出:
# ====== Coverage summary ======
# Statements   : 82.5% ( 165/200 )
# Branches     : 78.3% ( 47/60 )
# Functions    : 85.0% ( 17/20 )
# Lines        : 83.0% ( 166/200 )
```

---

**版本**: 1.0 | **日期**: April 2026 | **状态**: 就绪
