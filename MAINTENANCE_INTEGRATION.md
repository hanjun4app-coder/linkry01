# 数据维护模块集成指南

本文档描述如何将数据维护模块集成到现有的养老 AI 云端系统中。

> **重要**：本模块是增量修改，不会破坏现有的核心系统。

---

## 📋 集成步骤

### 1. 数据库初始化

#### 步骤 1.1：创建维护表

在 PostgreSQL 中执行以下脚本（按顺序）：

```bash
# 创建新表和相关对象
psql -U elderly_admin -d elderly_care -f db/maintenance_tables.sql

# 创建保留策略和清理函数
psql -U elderly_admin -d elderly_care -f db/retention_policy.sql
```

或在 Docker 中：

```bash
docker-compose exec postgres psql -U elderly_admin -d elderly_care -f /docker-entrypoint-initdb.d/maintenance_tables.sql
docker-compose exec postgres psql -U elderly_admin -d elderly_care -f /docker-entrypoint-initdb.d/retention_policy.sql
```

#### 步骤 1.2：验证表创建

```sql
-- 检查新表是否创建成功
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN (
    'daily_summaries', 'alert_feedback', 'data_retention_logs', 'scheduled_task_logs'
);
```

---

### 2. Python 代码集成

#### 步骤 2.1：添加新的模型（修改 `app/models.py`）

在 `app/models.py` 底部添加以下导入和模型定义：

```python
# 在文件末尾添加
# ==================== 维护模块模型 ====================

from sqlalchemy import JSON

class DailySummary(Base):
    """每日摘要表"""
    __tablename__ = "daily_summaries"
    
    id = Column(Integer, primary_key=True)
    summary_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    elder_id = Column(String(50), ForeignKey("elders.elder_id"), nullable=False)
    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    summary_date = Column(Date, nullable=False)
    
    total_activity_minutes = Column(Integer, default=0)
    active_rooms = Column(JSON, default=[])
    sleep_quality_score = Column(Numeric(3, 2), default=0)
    bathroom_visits = Column(Integer, default=0)
    total_alerts = Column(Integer, default=0)
    critical_alerts = Column(Integer, default=0)
    
    data_quality_score = Column(Numeric(3, 2), default=0)
    notes = Column(Text)
    recommendations = Column(JSON, default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        ForeignKeyConstraint(['elder_id'], ['elders.elder_id']),
        ForeignKeyConstraint(['family_id'], ['families.family_id']),
        UniqueConstraint('elder_id', 'family_id', 'summary_date'),
        Index('idx_daily_summary_elder_date', 'elder_id', 'summary_date'),
    )


class AlertFeedback(Base):
    """告警反馈表"""
    __tablename__ = "alert_feedback"
    
    id = Column(Integer, primary_key=True)
    feedback_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.alert_id"), nullable=False)
    elder_id = Column(String(50), ForeignKey("elders.elder_id"), nullable=False)
    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    
    feedback_type = Column(String(50), nullable=False)  # true_positive, false_positive, etc
    feedback_confidence = Column(Numeric(3, 2))
    severity_assessment = Column(String(50))
    
    user_id = Column(String(100))
    feedback_text = Column(Text)
    action_taken = Column(String(50))
    
    outcome = Column(String(50))
    follow_up_date = Column(Date)
    follow_up_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_alert_feedback_alert_id', 'alert_id'),
        Index('idx_alert_feedback_elder_date', 'elder_id', 'created_at'),
    )
```

#### 步骤 2.2：添加 Pydantic 模型（修改 `app/schemas.py`）

在 `app/schemas.py` 末尾添加：

```python
# 在末尾添加
from app.schemas_maintenance import (
    DailySummaryCreate,
    DailySummaryResponse,
    AlertFeedbackCreate,
    AlertFeedbackResponse,
    AlertFeedbackUpdateRequest,
    AlertFeedbackStatsResponse,
    DataRetentionLogResponse,
    DatabaseStatsCollectionResponse,
    ScheduledTaskLog,
)

# 导出这些类
__all__ = [
    # ... 现有的导出
    "DailySummaryCreate",
    "DailySummaryResponse",
    "AlertFeedbackCreate",
    "AlertFeedbackResponse",
    "AlertFeedbackUpdateRequest",
    "AlertFeedbackStatsResponse",
    "DataRetentionLogResponse",
    "DatabaseStatsCollectionResponse",
    "ScheduledTaskLog",
]
```

#### 步骤 2.3：注册新路由（修改 `app/main.py`）

在 `app/main.py` 中的应用初始化部分添加：

```python
# 在路由注册部分添加
from app.routes import maintenance

app.include_router(maintenance.router)

# 在 lifespan 事件中启动定时任务
from app.tasks import scheduled_tasks

@app.on_event("startup")
async def startup_event():
    # ... 现有的启动代码
    await scheduled_tasks.start()

@app.on_event("shutdown")
async def shutdown_event():
    # ... 现有的关闭代码
    await scheduled_tasks.stop()
```

---

### 3. Docker 配置更新

#### 步骤 3.1：更新初始化脚本

将 SQL 脚本复制到 Docker 初始化目录：

```bash
# 假设使用 docker-compose
cp db/maintenance_tables.sql docker-entrypoint-initdb.d/
cp db/retention_policy.sql docker-entrypoint-initdb.d/
```

或在 `docker-compose.yml` 中：

```yaml
services:
  postgres:
    volumes:
      - ./db/init.sql:/docker-entrypoint-initdb.d/01_init.sql
      - ./db/maintenance_tables.sql:/docker-entrypoint-initdb.d/02_maintenance_tables.sql
      - ./db/retention_policy.sql:/docker-entrypoint-initdb.d/03_retention_policy.sql
```

#### 步骤 3.2：启动系统

```bash
# 重建并启动
docker-compose down
docker-compose up -d

# 验证初始化
docker-compose logs postgres | grep "maintenance_tables"
```

---

## 🔑 核心功能

### 每日摘要

```bash
# 生成单个摘要
curl -X POST http://localhost:8000/api/maintenance/summaries/generate \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "elder_id": "elder_001",
    "family_id": "family_001",
    "summary_date": "2024-01-15"
  }'

# 获取摘要
curl http://localhost:8000/api/maintenance/summaries/elder_001?family_id=family_001&days=7 \
  -H "x-api-key: YOUR_API_KEY"

# 批量生成
curl -X POST http://localhost:8000/api/maintenance/summaries/batch-generate \
  -H "x-api-key: YOUR_API_KEY" \
  -G --data-urlencode "family_id=family_001"
```

### 告警反馈

```bash
# 添加反馈
curl -X POST http://localhost:8000/api/maintenance/alerts/{alert_id}/feedback \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "feedback_type": "true_positive",
    "feedback_confidence": 0.95,
    "severity_assessment": "correct",
    "user_id": "user_001",
    "feedback_text": "确实是跌倒事件",
    "action_taken": "contacted",
    "outcome": "recovered"
  }'

# 获取反馈统计
curl http://localhost:8000/api/maintenance/alerts/feedback-stats?days=30 \
  -H "x-api-key: YOUR_API_KEY"
```

### 数据清理

```bash
# 执行所有清理任务
curl -X POST http://localhost:8000/api/maintenance/cleanup \
  -H "x-api-key: YOUR_API_KEY"

# 仅清理 events 表
curl -X POST http://localhost:8000/api/maintenance/cleanup \
  -H "x-api-key: YOUR_API_KEY" \
  -G --data-urlencode "table_name=events"

# 查看清理日志
curl http://localhost:8000/api/maintenance/cleanup-logs?limit=50 \
  -H "x-api-key: YOUR_API_KEY"
```

### 数据库统计

```bash
# 获取数据库统计
curl http://localhost:8000/api/maintenance/database-stats \
  -H "x-api-key: YOUR_API_KEY"

# 获取维护统计信息
curl http://localhost:8000/api/maintenance/statistics \
  -H "x-api-key: YOUR_API_KEY" \
  -G --data-urlencode "family_id=family_001&days=30"
```

### 定时任务日志

```bash
# 获取所有任务日志
curl http://localhost:8000/api/maintenance/tasks/logs \
  -H "x-api-key: YOUR_API_KEY"

# 获取特定任务日志
curl http://localhost:8000/api/maintenance/tasks/logs \
  -H "x-api-key: YOUR_API_KEY" \
  -G --data-urlencode "task_name=generate_daily_summary"
```

---

## 📊 数据保留政策

| 表 | 保留期 | 清理频率 | 归档 |
|---|--------|---------|------|
| events | 90 天 | 每周 | 是 |
| daily_summaries | 3 年 | 不清理 | 否 |
| alerts | 3 年 | 不清理 | 是 |
| alert_feedback | 3 年 | 不清理 | 否 |
| audit_logs | 1 年 | 每月 | 否 |

---

## 🕐 定时任务计划

| 任务 | 执行时间 | 频率 | 说明 |
|-----|---------|------|------|
| `generate_daily_summary` | 01:00 | 每天 | 生成所有老人的日摘要 |
| `update_patterns` | 03:00 | 每天 | 更新行为基线 |
| `cleanup_events` | 02:00 | 每周日 | 清理 90 天前的事件 |

---

## 💾 数据库备份

### 使用备份脚本

```bash
# 全量备份
bash scripts/backup_database.sh

# 仅备份表结构
bash scripts/backup_database.sh -t schemas

# 仅备份数据
bash scripts/backup_database.sh -t data_only

# 选择性备份
bash scripts/backup_database.sh -t tables

# 指定备份目录
bash scripts/backup_database.sh -b /var/backups/elderly_care
```

### 环境变量

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=elderly_admin
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=elderly_care
export BACKUP_DIR=./backups
```

---

## 🔍 监控和维护

### 健康检查

```bash
# 检查维护模块状态
curl http://localhost:8000/api/maintenance/health \
  -H "x-api-key: YOUR_API_KEY"
```

### 常见操作

```bash
# 1. 检查定时任务日志
SELECT * FROM scheduled_task_logs ORDER BY created_at DESC LIMIT 10;

# 2. 检查清理日志
SELECT * FROM data_retention_logs ORDER BY created_at DESC LIMIT 10;

# 3. 查看每日摘要统计
SELECT * FROM v_daily_summary_stats ORDER BY summary_date DESC LIMIT 10;

# 4. 查看告警准确率
SELECT * FROM v_alert_accuracy_rate;

# 5. 查看数据库大小
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## ⚠️ 故障排除

### 定时任务不执行

1. 检查应用日志
   ```bash
   docker-compose logs -f api | grep "scheduled"
   ```

2. 验证定时任务是否启动
   ```bash
   curl http://localhost:8000/api/maintenance/health
   ```

3. 检查 scheduled_task_logs 表
   ```sql
   SELECT * FROM scheduled_task_logs ORDER BY created_at DESC;
   ```

### 清理任务失败

1. 查看清理日志
   ```sql
   SELECT * FROM data_retention_logs WHERE status = 'failed';
   ```

2. 检查数据库权限
   ```sql
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO elderly_admin;
   ```

### 摘要未生成

1. 检查 daily_summaries 表
   ```sql
   SELECT COUNT(*) FROM daily_summaries WHERE summary_date = CURRENT_DATE - INTERVAL '1 day';
   ```

2. 检查事件数据
   ```sql
   SELECT COUNT(*) FROM events WHERE DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day';
   ```

---

## 📝 API 文档总结

### 新增 API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/maintenance/summaries/{elder_id}` | 获取老人的每日摘要 |
| POST | `/api/maintenance/summaries/generate` | 生成单个摘要 |
| POST | `/api/maintenance/summaries/batch-generate` | 批量生成摘要 |
| POST | `/api/maintenance/alerts/{alert_id}/feedback` | 添加告警反馈 |
| PUT | `/api/maintenance/alerts/{alert_id}/feedback/{feedback_id}` | 更新反馈 |
| GET | `/api/maintenance/alerts/feedback-stats` | 获取反馈统计 |
| POST | `/api/maintenance/cleanup` | 执行数据清理 |
| GET | `/api/maintenance/cleanup-logs` | 获取清理日志 |
| GET | `/api/maintenance/database-stats` | 获取数据库统计 |
| GET | `/api/maintenance/tasks/logs` | 获取任务日志 |
| GET | `/api/maintenance/statistics` | 获取维护统计 |
| GET | `/api/maintenance/health` | 健康检查 |

---

## 📞 支持

如有问题，请：
1. 检查本指南的故障排除部分
2. 查看应用日志
3. 查看数据库日志表
4. 联系开发团队

---

**完成日期**：2024年1月

**版本**：1.0

**状态**：生产就绪
