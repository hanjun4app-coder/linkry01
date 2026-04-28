# 🏥 养老AI系统MVP云端部署

> **Aqara FP2 / Home Assistant → Cloud API → PostgreSQL → Rule Engine → Alert Notification**

完整的、可立即部署的养老监护系统，使用规则引擎进行异常检测（无深度学习依赖）。

---

## 📋 目录

- [快速开始](#快速开始)
- [系统架构](#系统架构)
- [API 文档](#api-文档)
- [部署指南](#部署指南)
- [Home Assistant 集成](#home-assistant-集成)
- [配置说明](#配置说明)
- [故障排除](#故障排除)

---

## ⚡ 快速开始

### 本地开发环境（5 分钟）

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/elderly-care-cloud.git
cd elderly-care-cloud

# 2. 复制环境配置
cp .env.example .env

# 3. 启动服务（Docker Compose）
docker-compose up -d

# 4. 验证 API
curl http://localhost:8000/health

# 5. 查看 API 文档
open http://localhost:8000/docs
```

### 云端生产部署（10 分钟）

见下方[部署指南](#部署指南)。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Aqara FP2 设备                        │
│              （运动、温湿度、距离检测）                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Home Assistant                         │
│              （本地网关、事件分发）                      │
└────────────────────────┬────────────────────────────────┘
                         │
                    Webhook
                         │
┌────────────────────────▼────────────────────────────────┐
│              FastAPI 云端 API                           │
│        - /api/events       (事件接收)                    │
│        - /api/alerts       (告警查询)                    │
│        - /api/patterns     (基线模式)                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ├──────────────────┐
                         ▼                  ▼
                  ┌──────────────┐   ┌─────────────┐
                  │ Rule Engine  │   │ PostgreSQL  │
                  │  (5条规则)   │   │  (数据库)   │
                  └──────────────┘   └─────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ 告警生成     │
                  │ - Email      │
                  │ - 钉钉/企业微信 │
                  │ - Mobile App │
                  └──────────────┘
```

### 核心规则引擎（5 条规则）

| # | 规则 | 触发条件 | 告警级别 |
|---|------|---------|--------|
| 1 | **长时间无活动** | 过去 4 小时无任何运动 | 🔴 Critical |
| 2 | **卫生间停留过久** | 卫生间停留 > 30 分钟 | 🟡 Warning |
| 3 | **起床时间异常** | 起床时间与基线差异 > 2 小时 | 🟡 Warning |
| 4 | **夜间频繁活动** | 22:00-06:00 活动 > 5 次 | 🟡 Warning |
| 5 | **房间活动模式偏离** | 不常去的房间活动 > 50% | 🟡 Warning |

---

## 📡 API 文档

### 基础信息

- **基础 URL**: `https://api.elderly-care.com` (或本地 `http://localhost:8000`)
- **认证**: 请求头 `x-api-key: YOUR_API_KEY`
- **内容类型**: `application/json`

### 端点概览

#### 1. 事件接收 - `/api/events`

创建和查询事件（传感器数据）。

```bash
# 创建单个事件
POST /api/events
{
  "elder_id": "elder_001",
  "family_id": "family_001",
  "device_id": "aqara_fp2_bedroom",
  "device_type": "aqara_fp2",
  "event_type": "presence",
  "event_value": {"detected": true, "distance": 2.5},
  "room": "bedroom",
  "confidence": 0.95
}

# 批量创建事件（推荐）
POST /api/events/bulk
{
  "batch_id": "batch_20240115_001",
  "events": [...]
}

# 获取最近事件
GET /api/events/{elder_id}?family_id=family_001&hours=24

# 按房间获取事件
GET /api/events/{elder_id}/by_room?family_id=family_001&room=bedroom

# 获取事件摘要（今日活动统计）
GET /api/events/{elder_id}/summary?family_id=family_001

# 检查规则并生成告警
POST /api/events/{elder_id}/check-rules?family_id=family_001
```

#### 2. 告警查询 - `/api/alerts`

查询和管理告警。

```bash
# 查询告警列表
GET /api/alerts?family_id=family_001&alert_level=critical&days=7&limit=100

# 获取未确认告警
GET /api/alerts/unacknowledged?elder_id=elder_001

# 确认告警
POST /api/alerts/{alert_id}/acknowledge?acknowledged_by=user_001

# 获取告警统计
GET /api/alerts/{family_id}/statistics?days=7

# 获取老人的未确认告警数
GET /api/alerts/elder/{elder_id}/unacknowledged-count?family_id=family_001
```

#### 3. 行为模式 - `/api/patterns`

管理老人的行为基线和模式。

```bash
# 创建/更新模式
POST /api/patterns
{
  "elder_id": "elder_001",
  "family_id": "family_001",
  "pattern_type": "activity",
  "average_daily_activity_minutes": 180,
  "average_wake_time": "07:00",
  "average_sleep_time": "22:00",
  "usual_active_rooms": ["living_room", "kitchen", "bedroom"],
  "days_collected": 7
}

# 获取老人所有模式
GET /api/patterns/{elder_id}

# 获取特定模式
GET /api/patterns/{elder_id}/{pattern_type}

# 从事件数据自动计算模式
POST /api/patterns/{elder_id}/calculate?family_id=family_001

# 重置模式（回到学习状态）
POST /api/patterns/{elder_id}/reset?family_id=family_001

# 获取模式统计
GET /api/patterns?family_id=family_001
```

### 标准事件格式

```json
{
  "elder_id": "elder_001",        // 必填：老人 ID
  "family_id": "family_001",      // 必填：家庭 ID
  "device_id": "aqara_fp2_br",    // 必填：设备 ID
  "device_type": "aqara_fp2",     // 必填：设备类型
  "event_type": "presence",       // 必填：事件类型
  "event_value": {...},           // 必填：事件数据（任意格式）
  "timestamp": "2024-01-15T...",  // 可选：事件时间（默认当前时间）
  "room": "bedroom",              // 可选：房间名称
  "location_name": "Bedroom",     // 可选：位置名称
  "confidence": 0.95,             // 可选：置信度 (0-1)
  "metadata": {...}               // 可选：额外元数据
}
```

### 错误响应

```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "error_message": "Invalid API key",
  "details": {...}
}
```

---

## 🚀 部署指南

### 前置条件

- Docker & Docker Compose (推荐)
- 或: Python 3.11+, PostgreSQL 12+
- 互联网连接

### 方式 A: Docker Compose（推荐）

```bash
# 1. 复制环境配置
cp .env.example .env

# 2. 编辑 .env 文件，改变以下内容:
#    - POSTGRES_PASSWORD (改为强密码)
#    - API_KEY (改为强密码)
#    - SECRET_KEY (生成: python -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. 启动所有服务
docker-compose up -d

# 4. 检查状态
docker-compose ps
docker-compose logs -f api

# 5. 初始化数据库
docker-compose exec api python -m app.database.init_db

# 6. 验证
curl -H "x-api-key: YOUR_API_KEY" http://localhost:8000/health
```

### 方式 B: 手动部署

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=elderly_admin
export POSTGRES_PASSWORD=your_password
export API_KEY=your_api_key

# 3. 启动 PostgreSQL
# macOS: brew install postgresql@15 && brew services start postgresql@15
# Ubuntu: sudo apt install postgresql-15 && sudo systemctl start postgresql

# 4. 创建数据库
createdb elderly_care

# 5. 初始化数据库表
python -c "from app.database import init_db; init_db()"

# 6. 启动 API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 7. 查看 API 文档
open http://localhost:8000/docs
```

### 部署到云服务（AWS/Azure/GCP）

#### AWS ECS

```bash
# 1. 构建镜像
docker build -t elderly-care-api:latest .

# 2. 推送到 ECR
aws ecr get-login-password --region us-east-1 | docker login ...
docker tag elderly-care-api:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/elderly-care:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/elderly-care:latest

# 3. 在 AWS RDS 创建 PostgreSQL 数据库
# 4. 创建 ECS 任务和服务
# 5. 配置 ALB 和安全组
```

#### Kubernetes

```bash
# 使用提供的 k8s 配置文件（待生成）
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## 🏠 Home Assistant 集成

### 安装和配置

1. **添加到 Home Assistant**

   ```yaml
   # 在 configuration.yaml 中添加
   homeassistant:
     customize:
       input_text.elder_id:
         friendly_name: "老人 ID"

   input_text:
     elder_id:
       name: Elder ID
       initial: "elder_001"
     api_key:
       name: API Key
       initial: "your_api_key_here"

   rest_command:
     send_to_elderly_care_api:
       url: "http://elderly-care-api:8000/api/events"
       method: POST
       content_type: "application/json"
       headers:
         x-api-key: "{{ states('input_text.api_key') }}"
       payload: |
         {...}
   ```

2. **配置自动化**

   见 `examples/home_assistant_webhook.yaml`

3. **测试集成**

   ```bash
   # 在 Home Assistant 中手动触发自动化，检查云端 API 是否收到事件
   curl -H "x-api-key: YOUR_API_KEY" \
     http://localhost:8000/api/events/elder_001?family_id=family_001
   ```

---

## ⚙️ 配置说明

### 环境变量

见 `.env.example` 中的详细说明。关键变量：

```bash
# 数据库
POSTGRES_HOST=postgres           # 数据库主机
POSTGRES_PASSWORD=***           # 数据库密码（生产必改！）

# API
API_KEY=***                     # API 密钥（生产必改！）
SECRET_KEY=***                  # 加密密钥

# 告警规则阈值
INACTIVITY_THRESHOLD_MINUTES=240        # 无活动告警（分钟）
BATHROOM_TIMEOUT_MINUTES=30              # 卫生间超时（分钟）
WAKE_TIME_VARIANCE_HOURS=2                # 起床时间偏差（小时）
NIGHT_ACTIVITY_THRESHOLD=5                # 夜间活动阈值（次）
ROOM_ACTIVITY_DEVIATION_PERCENT=50        # 房间偏离阈值（%）
```

### 数据库初始化

系统启动时自动创建表。手动初始化：

```bash
docker-compose exec api python
>>> from app.database import init_db
>>> init_db()
```

---

## 🧪 测试

### 快速测试

```bash
# 运行测试脚本
bash examples/test_events.sh

# 或用 curl
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -H "x-api-key: your_api_key_change_in_production" \
  -d '{"elder_id":"elder_001","family_id":"family_001","device_id":"test","device_type":"custom","event_type":"custom","event_value":{}}'
```

### 单元测试

```bash
pytest tests/
pytest tests/test_rules.py -v
```

---

## 🔧 故障排除

### 常见问题

#### 1. `Connection refused` - 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker-compose ps postgres

# 检查日志
docker-compose logs postgres

# 重启数据库
docker-compose restart postgres
```

#### 2. `Invalid API key`

```bash
# 确保使用正确的 API_KEY
curl -H "x-api-key: $(grep API_KEY .env | cut -d= -f2)" \
  http://localhost:8000/health
```

#### 3. `Events not generating alerts`

```bash
# 检查规则是否正常工作
curl -X POST http://localhost:8000/api/events/elder_001/check-rules \
  -H "x-api-key: YOUR_KEY" \
  -H "family_id: family_001"

# 查看日志
docker-compose logs api | grep -i "alert\|rule"
```

#### 4. `Port already in use`

```bash
# 改变端口
PORT=8001 docker-compose up -d

# 或杀死占用端口的进程
lsof -i :8000
kill -9 <PID>
```

### 调试模式

```bash
# 启用调试日志
DEBUG=True LOG_LEVEL=DEBUG docker-compose up -d api

# 查看详细日志
docker-compose logs -f api
```

---

## 📊 监控

### 日志和指标

```bash
# 实时日志
docker-compose logs -f api

# 查看最近 100 行
docker-compose logs --tail=100 api

# 导出日志
docker-compose logs api > logs.txt
```

### 性能监控

```bash
# 检查 API 响应时间
time curl http://localhost:8000/health

# 使用 Apache Bench 进行压力测试
ab -n 1000 -c 10 http://localhost:8000/health
```

---

## 📚 额外资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [Home Assistant 自动化](https://www.home-assistant.io/getting-started/automation/)

---

## 📄 许可证

内部使用

---

## 👥 支持

遇到问题？

1. 检查 [故障排除](#故障排除) 部分
2. 查看 API 日志：`docker-compose logs api`
3. 联系开发团队

---

**准备好部署了吗？** 🚀

```bash
git clone <repo> && cd elderly-care-cloud
cp .env.example .env
# 编辑 .env
docker-compose up -d
curl http://localhost:8000/docs  # 打开 API 文档
```
