# 数据维护模块 - 快速参考卡片

## 📁 新增文件一览

| 文件 | 行数 | 用途 |
|-----|------|------|
| `db/maintenance_tables.sql` | 450 | 创建表、视图、函数、触发器 |
| `db/retention_policy.sql` | 350 | 数据清理策略和过程 |
| `scripts/backup_database.sh` | 350 | 数据库备份脚本 |
| `app/services_maintenance.py` | 550 | 业务逻辑服务 |
| `app/schemas_maintenance.py` | 300 | 数据模型定义 |
| `app/routes/maintenance.py` | 450 | API 路由 |
| `app/tasks.py` | 450 | 定时任务管理 |

## ⚙️ 必需修改

| 文件 | 操作 | 难度 |
|-----|------|------|
| `app/models.py` | 添加 2 个模型 | ⭐ 低 |
| `app/schemas.py` | 添加导入 | ⭐ 低 |
| `app/main.py` | 添加路由+事件 | ⭐ 低 |

## 🚀 快速启动

### 第一步：初始化数据库（5 分钟）
```bash
psql -U elderly_admin -d elderly_care -f db/maintenance_tables.sql
psql -U elderly_admin -d elderly_care -f db/retention_policy.sql
```

### 第二步：修改应用文件（10 分钟）
参考 `MAINTENANCE_CHECKLIST.md` 中的修改清单

### 第三步：重启并验证（3 分钟）
```bash
docker-compose restart api
curl http://localhost:8000/api/maintenance/health -H "x-api-key: YOUR_KEY"
```

## 📡 API 端点速查

### 摘要查询
```bash
# 获取摘要
GET /api/maintenance/summaries/{elder_id}?family_id=XXX&days=7

# 生成摘要
POST /api/maintenance/summaries/generate
Body: {"elder_id": "elder_001", "family_id": "family_001"}

# 批量生成
POST /api/maintenance/summaries/batch-generate?family_id=XXX
```

### 反馈管理
```bash
# 添加反馈
POST /api/maintenance/alerts/{alert_id}/feedback?elder_id=XXX&family_id=XXX
Body: {"feedback_type": "true_positive", "outcome": "recovered"}

# 反馈统计
GET /api/maintenance/alerts/feedback-stats?days=30
```

### 数据管理
```bash
# 执行清理
POST /api/maintenance/cleanup

# 查看日志
GET /api/maintenance/cleanup-logs?limit=50

# 数据库统计
GET /api/maintenance/database-stats
```

### 监控
```bash
# 任务日志
GET /api/maintenance/tasks/logs?task_name=generate_daily_summary

# 整体统计
GET /api/maintenance/statistics?family_id=XXX&days=30

# 健康检查
GET /api/maintenance/health
```

## 🕐 定时任务时间表

| 时间 | 任务 | 频率 |
|------|------|------|
| 01:00 | 生成每日摘要 | 每天 |
| 02:00 | 清理过期事件 | 每周日 |
| 03:00 | 更新行为基线 | 每天 |

## 📊 数据保留规则

| 表 | 保留期 | 清理条件 |
|----|--------|--------|
| events | 90 天 | timestamp < 90 days ago |
| daily_summaries | 3 年 | 永久保留 |
| alerts | 3 年 | 永久保留 |
| alert_feedback | 3 年 | 永久保留 |
| audit_logs | 1 年 | created_at < 1 year ago |

## 💾 备份命令

```bash
# 全量备份
bash scripts/backup_database.sh

# 仅结构
bash scripts/backup_database.sh -t schemas

# 仅数据
bash scripts/backup_database.sh -t data_only

# 指定目录
bash scripts/backup_database.sh -b /var/backups/elderly_care

# 自定义位置
BACKUP_DIR=/backups bash scripts/backup_database.sh
```

## 🔍 查询常用命令

### 检查每日摘要
```sql
SELECT elder_id, summary_date, total_activity_minutes, total_alerts
FROM daily_summaries
WHERE family_id = 'family_001'
ORDER BY summary_date DESC
LIMIT 10;
```

### 检查告警反馈
```sql
SELECT feedback_type, COUNT(*) as count, 
       ROUND(AVG(feedback_confidence), 2) as avg_confidence
FROM alert_feedback
WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
GROUP BY feedback_type;
```

### 检查清理历史
```sql
SELECT operation_type, table_name, rows_affected, status, executed_at
FROM data_retention_logs
ORDER BY created_at DESC
LIMIT 10;
```

### 检查任务执行
```sql
SELECT task_name, status, COUNT(*) as count,
       AVG(duration_seconds) as avg_duration
FROM scheduled_task_logs
WHERE created_at > CURRENT_DATE - INTERVAL '7 days'
GROUP BY task_name, status;
```

### 检查数据库大小
```sql
SELECT
    schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_live_tup as rows
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## ⚡ 性能检查

### API 响应时间
```bash
# 摘要查询（应 < 100ms）
time curl -s http://localhost:8000/api/maintenance/summaries/elder_001 \
  -H "x-api-key: YOUR_KEY" | jq .

# 统计查询（应 < 500ms）
time curl -s http://localhost:8000/api/maintenance/statistics?family_id=family_001 \
  -H "x-api-key: YOUR_KEY" | jq .
```

## 🛠️ 故障排除速查

| 症状 | 解决方案 |
|------|---------|
| 摘要表不存在 | 执行 maintenance_tables.sql |
| 定时任务不执行 | 重启 API 或检查日志 |
| 清理失败 | 检查数据库权限或磁盘空间 |
| 备份出错 | 检查 POSTGRES_PASSWORD 环境变量 |
| API 返回 404 | 确认路由已导入 app/main.py |

## 📖 详细文档位置

| 需求 | 文档 |
|------|------|
| 集成步骤 | `MAINTENANCE_INTEGRATION.md` |
| 集成清单 | `MAINTENANCE_CHECKLIST.md` |
| 项目总结 | `MAINTENANCE_SUMMARY.md` |
| 本速查表 | `MAINTENANCE_QUICK_REFERENCE.md` |

## ✅ 验证清单

启动前检查：
- [ ] 所有 SQL 脚本已执行
- [ ] app/models.py 已修改
- [ ] app/schemas.py 已修改
- [ ] app/main.py 已修改
- [ ] 所有新文件已放置在正确位置

启动后检查：
- [ ] API 启动成功（无错误）
- [ ] 健康检查返回 200
- [ ] 摘要可以生成
- [ ] 反馈可以记录
- [ ] 清理可以执行

## 🎯 常见场景

### 场景 1：想要查看老人最近 7 天的摘要
```bash
curl 'http://localhost:8000/api/maintenance/summaries/elder_001?family_id=family_001&days=7' \
  -H "x-api-key: YOUR_KEY" | jq '.[] | {date: .summary_date, activity: .total_activity_minutes, alerts: .total_alerts}'
```

### 场景 2：要为某个告警添加反馈
```bash
curl -X POST 'http://localhost:8000/api/maintenance/alerts/ALERT_UUID/feedback?elder_id=elder_001&family_id=family_001' \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_KEY" \
  -d '{
    "feedback_type": "true_positive",
    "feedback_confidence": 0.95,
    "outcome": "recovered"
  }'
```

### 场景 3：想要进行完整的数据备份
```bash
# 设置环境变量
export POSTGRES_PASSWORD=your_password
export BACKUP_DIR=/var/backups/elderly_care

# 执行备份
bash scripts/backup_database.sh

# 查看备份文件
ls -lh /var/backups/elderly_care/
```

### 场景 4：想要查看这周执行的定时任务
```bash
curl 'http://localhost:8000/api/maintenance/tasks/logs?limit=100' \
  -H "x-api-key: YOUR_KEY" | jq '.[] | select(.created_at | startswith("2024-04")) | {task: .task_name, status: .status, duration: .duration_seconds}'
```

### 场景 5：想要理解告警准确率如何计算
```bash
curl 'http://localhost:8000/api/maintenance/alerts/feedback-stats?days=30' \
  -H "x-api-key: YOUR_KEY" | jq '.accuracy_stats[] | {type: .alert_type, total: .total_alerts, accuracy: .accuracy_percent}'
```

## 📞 快速帮助

**问**：如何禁用定时任务？
**答**：编辑 `app/main.py`，注释掉 `await scheduled_tasks.start()`

**问**：如何修改清理周期？
**答**：编辑 `db/retention_policy.sql` 中的 retention_days 值

**问**：如何查看某个任务是否运行？
**答**：`SELECT * FROM scheduled_task_logs WHERE task_name='generate_daily_summary' ORDER BY created_at DESC LIMIT 1;`

**问**：备份文件在哪里？
**答**：默认 `./backups/`，可通过 `BACKUP_DIR` 环境变量修改

**问**：如何手动触发清理？
**答**：`curl -X POST http://localhost:8000/api/maintenance/cleanup -H "x-api-key: YOUR_KEY"`

---

**打印本页以便快速参考！** 📄

