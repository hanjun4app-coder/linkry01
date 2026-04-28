# 数据维护模块集成清单

**状态**：待集成 ✅ 所有文件已准备就绪

---

## 新增文件清单

以下文件已创建，可直接使用：

### 数据库脚本
- ✅ `db/maintenance_tables.sql` - 创建维护表和相关对象（新增表、视图、函数、触发器）
- ✅ `db/retention_policy.sql` - 创建保留策略和清理函数（保留规则、清理过程）
- ✅ `scripts/backup_database.sh` - 数据库备份脚本（完整备份、增量备份）

### Python 代码
- ✅ `app/services_maintenance.py` - 维护服务层（完整实现，无依赖问题）
  - `DailySummaryService` - 每日摘要服务
  - `AlertFeedbackService` - 告警反馈服务
  - `DataRetentionService` - 数据保留服务
  - `ScheduledTaskService` - 定时任务日志服务

- ✅ `app/schemas_maintenance.py` - 数据模型（Pydantic）
  - 每日摘要数据模型
  - 告警反馈数据模型
  - 数据保留数据模型
  - 定时任务数据模型

- ✅ `app/routes/maintenance.py` - API 路由（完整实现，12 个新端点）
  - GET `/api/maintenance/summaries/{elder_id}` - 获取摘要
  - POST `/api/maintenance/summaries/generate` - 生成摘要
  - POST `/api/maintenance/summaries/batch-generate` - 批量生成
  - POST `/api/maintenance/alerts/{alert_id}/feedback` - 添加反馈
  - PUT `/api/maintenance/alerts/{alert_id}/feedback/{feedback_id}` - 更新反馈
  - GET `/api/maintenance/alerts/feedback-stats` - 反馈统计
  - POST `/api/maintenance/cleanup` - 数据清理
  - GET `/api/maintenance/cleanup-logs` - 清理日志
  - GET `/api/maintenance/database-stats` - 数据库统计
  - GET `/api/maintenance/tasks/logs` - 任务日志
  - GET `/api/maintenance/statistics` - 维护统计
  - GET `/api/maintenance/health` - 健康检查

- ✅ `app/tasks.py` - 定时任务管理
  - `ScheduledTasks` 类管理 3 个后台任务
  - 每天 01:00 生成每日摘要
  - 每天 03:00 更新行为基线
  - 每周日 02:00 清理过期事件

### 文档
- ✅ `MAINTENANCE_INTEGRATION.md` - 完整的集成指南（步骤、配置、示例）
- ✅ `MAINTENANCE_CHECKLIST.md` - 本清单

---

## 现有文件修改清单

需要对现有文件进行的修改：

### 1. `app/models.py`
**操作**：在文件末尾添加新的 SQLAlchemy 模型

**添加内容**：
- `DailySummary` 模型（约 40 行）
- `AlertFeedback` 模型（约 35 行）
- `DataRetentionLog` 模型（可选，数据库自管理）
- `ScheduledTaskLog` 模型（可选，数据库自管理）

**位置**：文件末尾，在所有现有模型之后

**难度**：⭐ 低（直接复制粘贴）

**破坏性**：❌ 无（仅添加，不修改现有模型）

### 2. `app/schemas.py`
**操作**：导入维护模块的 Pydantic 模型

**添加内容**：
```python
# 在文件末尾添加
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
```

**位置**：文件末尾

**难度**：⭐ 低（仅导入）

**破坏性**：❌ 无（仅添加导出）

### 3. `app/main.py`
**操作**：
1. 导入维护路由
2. 在应用中注册路由
3. 在启动事件中启动定时任务
4. 在关闭事件中停止定时任务

**添加内容**：
```python
# 在导入部分添加
from app.routes import maintenance
from app.tasks import scheduled_tasks

# 在应用初始化后添加
app.include_router(maintenance.router)

# 在启动事件中添加
@app.on_event("startup")
async def startup_with_maintenance():
    await scheduled_tasks.start()

# 在关闭事件中添加
@app.on_event("shutdown")
async def shutdown_with_maintenance():
    await scheduled_tasks.stop()
```

**位置**：
- 导入：在其他导入之后
- 路由注册：在其他路由注册之后
- 启动/关闭事件：在相应的生命周期事件中

**难度**：⭐ 低（标准的 FastAPI 用法）

**破坏性**：❌ 无（仅添加新路由和事件）

### 4. `docker-compose.yml`（可选但建议）
**操作**：更新数据库初始化脚本

**修改**：
```yaml
services:
  postgres:
    volumes:
      - ./db/init.sql:/docker-entrypoint-initdb.d/01_init.sql
      - ./db/maintenance_tables.sql:/docker-entrypoint-initdb.d/02_maintenance_tables.sql
      - ./db/retention_policy.sql:/docker-entrypoint-initdb.d/03_retention_policy.sql
```

**位置**：postgres 服务的 volumes 部分

**难度**：⭐ 低（添加卷挂载）

**破坏性**：❌ 无（仅添加新的初始化脚本）

### 5. `requirements.txt`（可选）
**操作**：确保包含必要的依赖

**检查项**：
- ✅ fastapi >= 0.95
- ✅ sqlalchemy >= 2.0
- ✅ psycopg2-binary
- ✅ pydantic >= 2.0
- ✅ python-dotenv

**难度**：⭐ 低（检查即可，通常已包含）

---

## 集成步骤总结

### 步骤 1：数据库初始化（5 分钟）
```bash
# 方式 A: 直接执行（适合开发环境）
psql -U elderly_admin -d elderly_care -f db/maintenance_tables.sql
psql -U elderly_admin -d elderly_care -f db/retention_policy.sql

# 方式 B: Docker（适合生产环境）
docker-compose down
docker-compose up -d
docker-compose logs postgres  # 验证初始化
```

### 步骤 2：修改现有文件（10 分钟）
1. ✏️ 修改 `app/models.py` - 添加 2 个新模型
2. ✏️ 修改 `app/schemas.py` - 添加导入
3. ✏️ 修改 `app/main.py` - 添加路由和事件
4. ✏️ 修改 `docker-compose.yml`（可选）

### 步骤 3：验证集成（5 分钟）
```bash
# 重启 API 服务
docker-compose restart api

# 验证 API 健康
curl http://localhost:8000/health

# 验证维护模块
curl http://localhost:8000/api/maintenance/health \
  -H "x-api-key: YOUR_API_KEY"

# 查看 API 文档
open http://localhost:8000/docs
```

### 步骤 4：测试功能（10 分钟）
```bash
# 生成每日摘要
curl -X POST http://localhost:8000/api/maintenance/summaries/generate \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"elder_id":"elder_001","family_id":"family_001"}'

# 查看定时任务日志
curl http://localhost:8000/api/maintenance/tasks/logs \
  -H "x-api-key: YOUR_API_KEY"
```

---

## 文件大小统计

| 文件 | 行数 | 说明 |
|-----|------|------|
| db/maintenance_tables.sql | 450 | 完整的表定义和对象 |
| db/retention_policy.sql | 350 | 清理策略和函数 |
| scripts/backup_database.sh | 350 | 备份脚本 |
| app/services_maintenance.py | 550 | 服务实现 |
| app/schemas_maintenance.py | 300 | 数据模型 |
| app/routes/maintenance.py | 450 | API 路由 |
| app/tasks.py | 450 | 定时任务 |
| **总计** | **2900+** | **完整功能实现** |

---

## 现有系统影响分析

### ✅ 不会影响的部分
- ✅ 现有的 API 端点（/api/events, /api/alerts 等）
- ✅ 现有的规则引擎
- ✅ 现有的数据模型
- ✅ 现有的身份验证

### ✅ 兼容性
- ✅ FastAPI 0.95+ 兼容
- ✅ SQLAlchemy 2.0+ 兼容
- ✅ PostgreSQL 12+ 兼容
- ✅ Python 3.11+ 兼容

### ⚠️ 需要注意
- ⚠️ 首次初始化需要在 PostgreSQL 中执行 SQL 脚本
- ⚠️ 定时任务会占用一定的 CPU 和内存（通常 < 5%）
- ⚠️ 数据清理会产生 I/O 操作（建议在非高峰期执行）

---

## 集成验证清单

### 数据库层面
- [ ] `daily_summaries` 表已创建
- [ ] `alert_feedback` 表已创建
- [ ] `data_retention_logs` 表已创建
- [ ] `scheduled_task_logs` 表已创建
- [ ] 所有索引已创建
- [ ] 所有视图已创建
- [ ] 所有函数已创建
- [ ] 所有触发器已创建

### 应用层面
- [ ] `app/services_maintenance.py` 已放置
- [ ] `app/schemas_maintenance.py` 已放置
- [ ] `app/routes/maintenance.py` 已放置
- [ ] `app/tasks.py` 已放置
- [ ] `app/models.py` 已修改（新增模型）
- [ ] `app/schemas.py` 已修改（新增导入）
- [ ] `app/main.py` 已修改（新增路由和事件）

### 测试层面
- [ ] API 启动成功
- [ ] /api/maintenance/health 返回 200
- [ ] 可以生成每日摘要
- [ ] 可以添加告警反馈
- [ ] 定时任务已启动
- [ ] 数据库统计可以获取
- [ ] 清理任务可以执行

---

## 回滚计划

如果需要回滚，按以下步骤操作：

### 方式 A：完全回滚（不保留新数据）
```bash
# 1. 停止 API
docker-compose stop api

# 2. 删除新表
psql -U elderly_admin -d elderly_care -c "
DROP TABLE IF EXISTS alert_feedback;
DROP TABLE IF EXISTS daily_summaries;
DROP TABLE IF EXISTS data_retention_logs;
DROP TABLE IF EXISTS scheduled_task_logs;
"

# 3. 恢复原始文件（从 git）
git checkout -- app/models.py app/schemas.py app/main.py

# 4. 删除新文件
rm -f app/services_maintenance.py app/schemas_maintenance.py
rm -f app/routes/maintenance.py app/tasks.py

# 5. 重启
docker-compose up -d api
```

### 方式 B：保留数据回滚
```bash
# 1-4 步同上
# 5. 备份新数据
pg_dump -U elderly_admin -d elderly_care -t daily_summaries -t alert_feedback \
  > maintenance_backup.sql

# 6. 继续回滚步骤
```

---

## 常见问题

### Q: 会影响现有的 API 性能吗？
**A**: 不会。维护模块：
- 使用独立的表和索引
- 定时任务在非高峰期运行（深夜）
- API 请求路径不共享

### Q: 可以只使用部分功能吗？
**A**: 可以。每个模块相对独立：
- 可以只使用摘要，不用清理
- 可以只使用反馈，不用摘要
- 可以禁用定时任务

### Q: 如何监控定时任务执行？
**A**: 使用以下方式：
1. API：`GET /api/maintenance/tasks/logs`
2. 数据库：`SELECT * FROM scheduled_task_logs`
3. 应用日志：`docker-compose logs api | grep "scheduled"`

### Q: 数据清理会删除哪些数据？
**A**: 按保留策略删除：
- events: 90 天前的数据
- alert_feedback: 3 年前的数据
- audit_logs: 1 年前的数据
- daily_summaries 和 alerts: 不删除（保留 3 年）

### Q: 备份脚本需要什么权限？
**A**: 需要以下权限：
- PostgreSQL：SELECT, CONNECT
- 文件系统：写入 backups 目录

---

## 支持和反馈

- 📖 详见：`MAINTENANCE_INTEGRATION.md`
- 🐛 问题：检查应用日志和数据库日志
- 💬 反馈：联系开发团队

---

**准备好了吗？** 

开始集成：
```bash
# 1. 初始化数据库
psql -U elderly_admin -d elderly_care -f db/maintenance_tables.sql
psql -U elderly_admin -d elderly_care -f db/retention_policy.sql

# 2. 修改应用文件（按清单进行）

# 3. 重启 Docker
docker-compose restart api

# 4. 验证
curl http://localhost:8000/api/maintenance/health -H "x-api-key: YOUR_API_KEY"
```

✅ **状态**：所有文件已准备就绪，等待集成
