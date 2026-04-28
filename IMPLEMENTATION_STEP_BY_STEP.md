# 分步实现指南：基线学习集成

**版本**: 1.0 | **日期**: April 2026 | **目标**: 完整集成baseline学习和个性化信号到生产环境

---

## 概览

这个指南将引导你完成以下步骤：

1. ✅ 数据库迁移（添加baseline字段）
2. ✅ API端点更新（调用statusEngineV2）
3. ✅ 日常更新定时任务设置
4. ✅ React hooks和UI组件集成
5. ✅ 验证和测试

**预计时间**: 2-3小时（取决于项目复杂度）

---

## 第1步：数据库迁移

### 1a. 创建迁移文件

创建文件: `migrations/002_add_baseline_fields.ts`

```typescript
import { Pool } from 'pg';

export async function up(pool: Pool) {
  const client = await pool.connect();
  
  try {
    console.log('🔄 Starting migration: add_baseline_fields');
    
    // 添加新列
    await client.query(`
      ALTER TABLE elders 
      ADD COLUMN IF NOT EXISTS baseline JSONB DEFAULT NULL,
      ADD COLUMN IF NOT EXISTS temporary_condition JSONB DEFAULT NULL;
    `);
    console.log('✅ Added columns to elders table');
    
    // 为现有elders初始化baseline（collecting状态）
    const elders = await client.query('SELECT elder_id FROM elders WHERE baseline IS NULL');
    
    for (const elder of elders.rows) {
      await client.query(
        `UPDATE elders 
         SET baseline = $1 
         WHERE elder_id = $2`,
        [
          JSON.stringify({
            elder_id: elder.elder_id,
            baseline_status: 'collecting',
            baseline_days_collected: 0,
            average_wake_time: 7,
            average_sleep_time: 22,
            average_daily_activity_minutes: 180,
            average_bathroom_duration_minutes: 15,
            average_bathroom_count: 4,
            average_night_wake_count: 1,
            average_daytime_bed_minutes: 60,
            usual_active_zones: ['living_room', 'kitchen', 'bathroom'],
            last_updated_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            days_in_temporary_condition: 0,
          }),
          elder.elder_id
        ]
      );
    }
    
    console.log(`✅ Initialized baseline for ${elders.rows.length} existing elders`);
    
    // 添加索引以加快查询
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_elders_baseline_status 
      ON elders USING gin(baseline)
    `);
    console.log('✅ Created indexes');
    
    console.log('✅ Migration complete');
  } catch (error) {
    console.error('❌ Migration failed:', error);
    throw error;
  } finally {
    client.release();
  }
}

export async function down(pool: Pool) {
  const client = await pool.connect();
  
  try {
    console.log('🔄 Rolling back migration: add_baseline_fields');
    
    await client.query(`
      DROP INDEX IF EXISTS idx_elders_baseline_status;
      ALTER TABLE elders 
      DROP COLUMN IF EXISTS baseline,
      DROP COLUMN IF EXISTS temporary_condition;
    `);
    
    console.log('✅ Rollback complete');
  } catch (error) {
    console.error('❌ Rollback failed:', error);
    throw error;
  } finally {
    client.release();
  }
}
```

### 1b. 运行迁移

```bash
# 运行迁移
npm run migrate:up

# 验证（查询elders表结构）
psql -d your_db -c "\d elders"
# 应该显示新列: baseline | jsonb | NULL
#             temporary_condition | jsonb | NULL
```

✅ **验证点**: 登录数据库确认新列已添加且现有elder已初始化baseline

---

## 第2步：API端点更新

### 2a. 创建/更新状态API端点

更新或创建文件: `pages/api/elders/[elder_id]/status.ts`

```typescript
import { NextApiRequest, NextApiResponse } from 'next';
import { generateStatusViewWithBaseline } from '@/lib/statusEngineV2';
import { db } from '@/db';
import { logger } from '@/lib/logger';

interface StatusResponse {
  status: any;
  baseline: any;
  personalizedSignals: any[];
  temporaryCondition: any | null;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<StatusResponse | { error: string }>
) {
  // 只允许GET请求
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { elder_id } = req.query;

  // 验证elder_id
  if (!elder_id || typeof elder_id !== 'string') {
    return res.status(400).json({ error: 'Invalid elder_id' });
  }

  try {
    logger.info(`[API] Generating status for elder: ${elder_id}`);

    // 并行获取所有必需的数据
    const [events, dailySummary, devices, baseline] = await Promise.all([
      db.getEventsForDate(elder_id, new Date()),
      db.getDailySummary(elder_id),
      db.getDevicesForElder(elder_id),
      db.getEldersBaseline(elder_id),
    ]);

    // 生成增强的状态视图（包含baseline学习和个性化信号）
    const result = await generateStatusViewWithBaseline(
      elder_id,
      events,
      dailySummary,
      devices,
      baseline
    );

    // 如果baseline被更新，保存到数据库
    if (result.baseline && JSON.stringify(result.baseline) !== JSON.stringify(baseline)) {
      await db.updateEldersBaseline(elder_id, result.baseline);
      logger.info(`[API] Baseline updated for ${elder_id}: days=${result.baseline.baseline_days_collected}`);
    }

    // 如果有临时状态，保存
    if (result.temporaryCondition) {
      await db.updateTemporaryCondition(elder_id, result.temporaryCondition);
      logger.warn(`[API] Temporary condition detected for ${elder_id}: ${result.temporaryCondition.anomaly_type}`);
    }

    // 返回完整的增强数据
    res.status(200).json({
      status: result.statusView,
      baseline: result.baseline,
      personalizedSignals: result.personalizedSignals,
      temporaryCondition: result.temporaryCondition,
    });
  } catch (error) {
    logger.error(`[API] Error generating status for ${elder_id}:`, error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Internal server error',
    });
  }
}
```

### 2b. 测试API端点

```bash
# 测试请求
curl http://localhost:3000/api/elders/elder_123/status

# 应该返回类似：
# {
#   "status": {
#     "elder_id": "elder_123",
#     "risk_level": "normal",
#     "alert_message": "✅ 一切正常",
#     ...
#   },
#   "baseline": {
#     "elder_id": "elder_123",
#     "baseline_status": "collecting",
#     "baseline_days_collected": 1,
#     ...
#   },
#   "personalizedSignals": [],
#   "temporaryCondition": null
# }
```

✅ **验证点**: API返回200，包含status、baseline、personalizedSignals三个字段

---

## 第3步：设置日常更新定时任务

### 3a. 创建定时任务服务

创建文件: `services/baselineScheduler.ts`

```typescript
import cron from 'node-cron';
import { db } from '@/db';
import { generateStatusViewWithBaseline } from '@/lib/statusEngineV2';
import { logger } from '@/lib/logger';

interface UpdateResult {
  success: number;
  failed: number;
  updated: number;
  details: { elder_id: string; status: 'success' | 'error'; message: string }[];
}

export async function setupBaselineScheduler() {
  // 每晚11:59运行
  const job = cron.schedule('59 23 * * *', async () => {
    logger.info('🌙 [Scheduler] Starting daily baseline update...');
    const startTime = Date.now();

    const results: UpdateResult = {
      success: 0,
      failed: 0,
      updated: 0,
      details: [],
    };

    try {
      // 获取所有活跃的elder
      const elders = await db.getAllActiveElders();
      logger.info(`[Scheduler] Found ${elders.length} active elders to update`);

      // 逐个处理每个elder
      for (const elder of elders) {
        try {
          const [events, summary, devices, baseline] = await Promise.all([
            db.getEventsForDate(elder.elder_id, new Date()),
            db.getDailySummary(elder.elder_id),
            db.getDevicesForElder(elder.elder_id),
            db.getEldersBaseline(elder.elder_id),
          ]);

          // 生成增强状态
          const result = await generateStatusViewWithBaseline(
            elder.elder_id,
            events,
            summary,
            devices,
            baseline
          );

          // 保存更新后的baseline
          if (result.baseline && JSON.stringify(result.baseline) !== JSON.stringify(baseline)) {
            await db.updateEldersBaseline(elder.elder_id, result.baseline);
            results.updated++;

            logger.debug(
              `[Scheduler] Baseline updated for ${elder.elder_id}: days=${result.baseline.baseline_days_collected}, status=${result.baseline.baseline_status}`
            );
          }

          // 保存临时状态
          if (result.temporaryCondition) {
            await db.updateTemporaryCondition(elder.elder_id, result.temporaryCondition);
          }

          results.success++;
          results.details.push({
            elder_id: elder.elder_id,
            status: 'success',
            message: `Baseline days: ${result.baseline.baseline_days_collected}, Status: ${result.baseline.baseline_status}`,
          });
        } catch (error) {
          results.failed++;
          logger.error(`[Scheduler] Failed for ${elder.elder_id}:`, error);
          results.details.push({
            elder_id: elder.elder_id,
            status: 'error',
            message: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      }

      const duration = Date.now() - startTime;
      logger.info('✅ [Scheduler] Daily baseline update complete', {
        total: elders.length,
        success: results.success,
        failed: results.failed,
        updated: results.updated,
        duration: `${duration}ms`,
      });

      // 发送通知（可选）
      if (results.failed > 0) {
        logger.warn(`[Scheduler] ${results.failed} elders failed to update`);
        // 可以发送告警到监控系统
      }
    } catch (error) {
      logger.error('[Scheduler] Fatal error in baseline update:', error);
    }
  });

  logger.info('✅ Baseline scheduler initialized (runs daily at 23:59)');
  return job;
}

// 在服务器启动时调用
// 建议在 pages/api/_startup.ts 或 server.ts 中调用
```

### 3b. 在服务器启动时初始化

更新文件: `pages/_app.tsx` 或 `server.ts`

```typescript
// 在应用初始化时调用
import { setupBaselineScheduler } from '@/services/baselineScheduler';

// 在Next.js中，可以在pages/api/_startup.ts中调用
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    try {
      setupBaselineScheduler();
      res.status(200).json({ message: 'Scheduler initialized' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to initialize scheduler' });
    }
  }
}

// 或在Docker容器启动脚本中调用
// 或在Lambda/Cloud Function启动时调用
```

✅ **验证点**: 定时任务已启动，查看日志看是否在每晚11:59执行

---

## 第4步：更新React Hooks和UI组件

### 4a. 创建Enhanced Hook

创建或更新文件: `hooks/useEnhancedStatus.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { StatusViewModel } from '@/types/behavior';
import { PersonalizedRiskSignal, ElderBaseline, TemporaryCondition } from '@/types/baseline';

export interface EnhancedStatusData {
  status: StatusViewModel;
  baseline: ElderBaseline;
  personalizedSignals: PersonalizedRiskSignal[];
  temporaryCondition: TemporaryCondition | null;
}

/**
 * Hook for fetching enhanced status with baseline and personalized signals
 * Refetches every 5 minutes automatically
 */
export function useEnhancedStatus(elder_id: string) {
  return useQuery<EnhancedStatusData>({
    queryKey: ['enhanced-status', elder_id],
    queryFn: async () => {
      const res = await fetch(`/api/elders/${elder_id}/status`);
      if (!res.ok) {
        throw new Error(`Failed to fetch status: ${res.statusText}`);
      }
      return res.json();
    },
    refetchInterval: 5 * 60 * 1000, // 每5分钟刷新一次
    staleTime: 2 * 60 * 1000,       // 2分钟内认为数据未过期
    retry: 3,                        // 失败时重试3次
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
```

### 4b. 更新Dashboard组件

更新文件: `pages/elders/[elder_id]/index.tsx` 或 `components/ElderDashboard.tsx`

```typescript
import React from 'react';
import EnhancedStatusView from '@/components/EnhancedStatusView';
import { useEnhancedStatus } from '@/hooks/useEnhancedStatus';

interface ElderDashboardProps {
  elder_id: string;
}

export const ElderDashboard: React.FC<ElderDashboardProps> = ({ elder_id }) => {
  const { data, isLoading, error, refetch } = useEnhancedStatus(elder_id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-600">加载状态中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-red-600">
          <div className="font-semibold mb-2">⚠️ 加载失败</div>
          <div className="text-sm">{error instanceof Error ? error.message : '未知错误'}</div>
          <button
            onClick={() => refetch()}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return <div className="p-8 text-gray-600">无数据</div>;
  }

  return (
    <div className="space-y-4">
      {/* 标题 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">老人状态监测</h1>
        <p className="text-gray-600 mt-1">
          最后更新: {new Date(data.status.timestamp).toLocaleString('zh-CN')}
        </p>
      </div>

      {/* 核心组件：显示通用规则 + 个性化信号 */}
      <EnhancedStatusView
        status={data.status}
        personalizedSignals={data.personalizedSignals}
        baseline={data.baseline}
        inTemporaryCondition={!!data.temporaryCondition}
      />

      {/* 调试信息（仅在开发环境显示） */}
      {process.env.NODE_ENV === 'development' && (
        <div className="mt-8 p-4 bg-gray-100 rounded border border-gray-300">
          <details>
            <summary className="cursor-pointer font-semibold text-gray-800">
              🔧 调试信息
            </summary>
            <pre className="mt-2 text-xs bg-white p-3 rounded overflow-auto max-h-48">
              {JSON.stringify(data, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};

export default ElderDashboard;
```

✅ **验证点**: 
- 页面加载，显示EnhancedStatusView
- 每5分钟自动刷新数据
- 个性化信号在baseline激活后显示

---

## 第5步：验证和测试

### 5a. 数据库验证

```bash
# 1. 检查列是否存在
psql -d your_db -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='elders' AND column_name IN ('baseline', 'temporary_condition');"

# 预期输出：
#      column_name      | data_type
# ---------------------+-----------
#  baseline            | jsonb
#  temporary_condition | jsonb

# 2. 检查初始化数据
psql -d your_db -c "SELECT elder_id, baseline->>'baseline_status' as status, baseline->>'baseline_days_collected' as days FROM elders LIMIT 5;"

# 预期输出：
#  elder_id | status     | days
# ----------+------------+------
#  elder_1  | collecting | 0
#  elder_2  | collecting | 0
```

### 5b. API验证

```bash
# 1. 测试API端点
curl -X GET http://localhost:3000/api/elders/elder_1/status

# 2. 检查响应结构
# 应该包含：
# {
#   "status": { ... },
#   "baseline": { ... },
#   "personalizedSignals": [ ... ],
#   "temporaryCondition": null
# }

# 3. 验证HTTP状态
curl -i http://localhost:3000/api/elders/elder_1/status
# 应该是 200 OK
```

### 5c. UI验证

```typescript
// 在浏览器控制台测试
const elder_id = 'elder_1';
fetch(`/api/elders/${elder_id}/status`)
  .then(r => r.json())
  .then(data => {
    console.log('✅ Status:', data.status);
    console.log('✅ Baseline:', data.baseline);
    console.log('✅ Personalized Signals:', data.personalizedSignals);
    console.log('✅ Temporary Condition:', data.temporaryCondition);
  })
  .catch(error => console.error('❌ Error:', error));
```

### 5d. 完整集成测试清单

- [ ] 数据库迁移成功运行
- [ ] 现有elder的baseline已初始化为`collecting`状态
- [ ] API端点返回200和正确结构
- [ ] 页面加载并显示EnhancedStatusView
- [ ] 个性化信号在baseline状态为`active`时显示
- [ ] 临时状态被正确检测和保存
- [ ] 定时任务在指定时间执行
- [ ] 浏览器控制台没有错误
- [ ] 数据库中baseline字段被正确更新

---

## 第6步：监控和告警设置

### 6a. 添加监控指标端点

创建文件: `pages/api/admin/metrics/baseline.ts`

```typescript
import { db } from '@/db';
import { logger } from '@/lib/logger';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const allElders = await db.getAllElders();
    
    const metrics = {
      total_elders: allElders.length,
      baseline_collecting: 0,
      baseline_active: 0,
      baseline_needs_review: 0,
      active_conditions: 0,
      avg_baseline_days: 0,
      last_update: new Date().toISOString(),
    };

    let totalDays = 0;

    for (const elder of allElders) {
      if (!elder.baseline) continue;

      if (elder.baseline.baseline_status === 'collecting') {
        metrics.baseline_collecting++;
      } else if (elder.baseline.baseline_status === 'active') {
        metrics.baseline_active++;
      } else if (elder.baseline.baseline_status === 'needs_review') {
        metrics.baseline_needs_review++;
      }

      if (elder.temporary_condition?.status === 'active') {
        metrics.active_conditions++;
      }

      totalDays += elder.baseline.baseline_days_collected || 0;
    }

    metrics.avg_baseline_days = Math.round(totalDays / allElders.length);

    logger.info('[Metrics] Baseline metrics', metrics);
    res.status(200).json(metrics);
  } catch (error) {
    logger.error('[Metrics] Error:', error);
    res.status(500).json({ error: 'Failed to get metrics' });
  }
}
```

### 6b. 告警阈值

```typescript
// 监控目标
const ALERT_THRESHOLDS = {
  baseline_collecting_percentage: 0.1, // 不超过10%的elder在collecting状态
  baseline_active_percentage: 0.9,     // 至少90%的elder在active状态
  active_conditions_percentage: 0.05,  // 不超过5%的elder在临时状态
  high_risk_event_rate: 0.02,          // 高风险事件不超过2%
};
```

✅ **验证点**: 监控面板显示baseline收集进度，告警规则正确配置

---

## 故障排除

### 问题：定时任务没有执行

**解决方案**：
1. 检查日志中是否有`[Scheduler] Starting daily baseline update`
2. 确认时区设置正确
3. 在测试时使用`cron.schedule('*/5 * * * *')`（每5分钟）临时测试

```typescript
// 测试cron（临时）
cron.schedule('*/5 * * * *', async () => {
  console.log('✅ Cron executed at', new Date().toISOString());
});
```

### 问题：API返回500错误

**解决方案**：
1. 检查数据库连接是否正常
2. 检查baseline字段是否为NULL导致JSON解析失败
3. 运行迁移检查baseline已初始化

```bash
# 检查baseline初始化
psql -d your_db -c "SELECT elder_id, baseline IS NULL as is_null FROM elders;"
```

### 问题：个性化信号不显示

**解决方案**：
1. 确认baseline状态为`active`（需要7天数据）
2. 对于测试，可以手动更新baseline状态为`active`：

```typescript
// 仅用于测试
await db.query(
  `UPDATE elders SET baseline = jsonb_set(baseline, '{baseline_status}', '"active"') WHERE elder_id = $1`,
  [elder_id]
);
```

---

## 部署检查清单

- [ ] ✅ 数据库迁移已执行
- [ ] ✅ statusEngineV2.ts已部署
- [ ] ✅ EnhancedStatusView.tsx已部署
- [ ] ✅ API端点已创建
- [ ] ✅ 定时任务已初始化
- [ ] ✅ React hooks已更新
- [ ] ✅ 页面组件已更新
- [ ] ✅ 监控指标已配置
- [ ] ✅ 错误告警已配置
- [ ] ✅ 文档已更新
- [ ] ✅ 用户培训已完成

---

## 后续优化

1. **实时基线更新**: 从每晚一次改为准实时（每小时）
2. **机器学习**: 集成更高级的异常检测算法
3. **可视化**: 添加基线学习曲线图表
4. **用户控制**: 允许护理人员手动调整基线
5. **多个基线**: 支持周末vs工作日的不同基线

---

**状态**: ✅ 就绪部署  
**最后更新**: April 2026  
**维护者**: 系统团队
