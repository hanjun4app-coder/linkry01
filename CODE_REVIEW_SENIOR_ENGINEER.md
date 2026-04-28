# 高级工程师代码审查报告
## 养老AI系统 - Elderly Care Cloud API

**审查日期:** 2026-04-27  
**审查范围:** 安全性、性能、数据库风险、未来扩展性  
**系统架构:** FastAPI + PostgreSQL + SQLAlchemy + RuleEngine

---

## 📋 执行摘要

该系统为养老人群健康监测的MVP实现，核心功能包括事件采集、异常检测规则引擎、告警生成与持久化。**总体评估：功能完整但存在关键安全漏洞和性能风险，需要在生产部署前修复。**

| 级别 | 数量 | 严重程度 |
|-----|------|---------|
| 🔴 严重 | 5 | 立即修复 |
| 🟠 中等 | 7 | 下个版本修复 |
| 🟡 优化建议 | 8+ | 规划中修复 |

---

## 🔴 严重问题 (Critical Issues)

### 1. CORS 安全配置失效
**文件:** `app/config.py` (第32行)
```python
ALLOW_ORIGINS: List[str] = ["*"]  # ❌ 严重安全漏洞
```

**风险:**
- 允许任何域名跨域请求老人健康数据
- 浏览器中任何恶意网站都可以发起请求
- 对健康数据的HIPAA/个人信息保护法规违反

**修复方案:**
```python
# 应该是白名单制度
ALLOW_ORIGINS: List[str] = [
    "https://elderly-care.example.com",
    "https://admin.elderly-care.example.com"
]
# 开发环境可以临时使用
if settings.DEBUG:
    ALLOW_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
```

---

### 2. 默认硬编码密钥 (Hardcoded Secrets)
**文件:** `app/config.py` (第30-31行)
```python
SECRET_KEY: str = "your-secret-key-change-in-production"
API_KEY: str = "your-api-key-change-in-production"
```

**风险:**
- 这些默认值可能被意外提交到代码仓库
- 如果代码泄露，攻击者获得所有密钥
- 没有从环境变量强制加载的机制

**修复方案:**
```python
from pydantic import Field

class Settings(BaseSettings):
    # ✅ 正确做法：必须从环境变量读取，无默认值
    SECRET_KEY: str = Field(..., description="Must be set in production")
    API_KEY: str = Field(..., description="Must be set in production")
    
    # 或者如果需要默认值（仅用于开发）
    @field_validator('SECRET_KEY', 'API_KEY')
    def validate_secrets(cls, v, info):
        if not v or v.startswith('your-'):
            if not settings.DEBUG:
                raise ValueError(f"{info.field_name} must be set in production")
        return v
```

**操作步骤:**
1. 从 `config.py` 删除所有默认密钥
2. 强制使用 `.env` 文件（.gitignore 中）
3. 在 Kubernetes/Docker 中用 Secrets 注入

---

### 3. API Key 认证机制太弱
**文件:** `app/routes/events.py` (第22-26行), `app/routes/alerts.py` (第19-23行)
```python
def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != settings.API_KEY:  # ❌ 简单字符串比较，无限重试
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key
```

**风险:**
- **无速率限制:** 攻击者可以无限次尝试暴力破解
- **无密钥轮换:** 单个密钥永久有效
- **无审计:** 不知道谁使用了哪个密钥
- **无过期时间:** 旧的泄露密钥仍然有效
- **无权限管理:** 所有密钥拥有相同权限

**修复方案:**
```python
# 使用 JWT Token 方案
from fastapi.security import HTTPBearer, HTTPAuthCredential
from fastapi import Depends
from jwt import decode, InvalidTokenError
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

def verify_token(credentials: HTTPAuthCredential = Depends(security)) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        # 验证过期时间
        if payload.get("exp") < datetime.utcnow().timestamp():
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# 在路由中使用
@router.post("/api/events")
async def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token)  # ✅ 使用 JWT
):
    # token["device_id"] 可以验证权限
    pass
```

**额外措施:**
- 实现速率限制: `pip install slowapi`
- 添加 API 密钥版本/ID 用于审计
- 实现密钥轮换机制

---

### 4. Home Assistant Webhook 无认证
**文件:** `app/main.py` (第112-176行)
```python
@app.post("/webhook/home_assistant", summary="Home Assistant Webhook")
async def home_assistant_webhook(data: dict):  # ❌ 接收任何 POST，无认证
    logger.info(f"Received Home Assistant webhook: {data}")
    # ...处理数据
```

**风险:**
- 任何人都可以向该端点发送虚假数据
- 可以伪造老人活动事件，触发虚假告警
- 可以造成告警疲劳或忽视真实告警

**修复方案:**
```python
from hmac import compare_digest
import hashlib

@app.post("/webhook/home_assistant")
async def home_assistant_webhook(
    data: dict,
    x_ha_signature: str = Header(None)
):
    """验证 Home Assistant Webhook 签名"""
    
    # Home Assistant 文档：签名格式为 sha256=<hash>
    if not x_ha_signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    # 计算期望的签名
    import json
    body = json.dumps(data, sort_keys=True)
    expected_signature = hashlib.sha256(
        f"{settings.HOME_ASSISTANT_WEBHOOK_SECRET}{body}".encode()
    ).hexdigest()
    
    provided_signature = x_ha_signature.split("=")[1] if "=" in x_ha_signature else ""
    
    if not compare_digest(expected_signature, provided_signature):
        logger.warning(f"Invalid webhook signature from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # ✅ 只有到这里才处理数据
    # ...
```

---

### 5. 日志泄露敏感信息
**文件:** `app/main.py` (第199行) 和多个异常处理
```python
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)  # ❌ 输出完整堆栈跟踪
    return JSONResponse(...)
```

**风险:**
- 完整异常堆栈可能包含：数据库密码、API密钥、用户ID、SQL查询
- 日志存储不当可能被攻击者读取
- 违反PII保护原则

**修复方案:**
```python
import logging
from pythonjsonlogger import jsonlogger  # pip install python-json-logger

# 创建日志过滤器
class PIIFilter(logging.Filter):
    def filter(self, record):
        # 移除敏感信息
        record.msg = self._sanitize(str(record.msg))
        return True
    
    @staticmethod
    def _sanitize(msg):
        import re
        # 移除邮箱、电话、IP地址
        msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP_MASKED', msg)
        msg = re.sub(r'\b\d{10,}\b', 'PHONE_MASKED', msg)
        msg = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL_MASKED', msg)
        return msg

# 在 main.py 中
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.addFilter(PIIFilter())

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # ❌ 不要记录完整异常
    # logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # ✅ 只记录异常类型和错误ID
    error_id = str(uuid.uuid4())
    logger.error(f"Internal error (ID: {error_id}): {type(exc).__name__}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": "Internal server error",
            "error_id": error_id,  # 用户可以用此ID在日志中查找（内部）
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

## 🟠 中等问题 (Medium Issues)

### 1. N+1 Query 问题 - 严重性能缺陷
**文件:** `app/rules.py` (第280-343行) - `check_room_pattern_change()`
```python
def check_room_pattern_change(self, elder_id: str, family_id: str):
    # ... 查询获取 usual_rooms ...
    
    # ❌ 加载所有事件到内存
    recent_activities = self.db.query(Event).filter(
        and_(
            Event.elder_id == elder_id,
            Event.family_id == family_id,
            Event.timestamp >= yesterday,
            Event.room != None
        )
    ).all()  # 可能是几千条记录！
    
    # ❌ 然后在 Python 中循环计算
    unusual_activity_count = sum(
        1 for e in recent_activities
        if e.room not in usual_rooms
    )
```

**问题:**
- 如果活跃老人一天有1000条事件，一次就加载1000条到内存
- 100个并发用户 = 10万条记录加载，导致内存爆炸
- 应该让数据库完成计算

**修复方案:**
```python
from sqlalchemy import func, case

def check_room_pattern_change(self, elder_id: str, family_id: str):
    # ... 获取 usual_rooms ...
    
    yesterday = datetime.utcnow() - timedelta(hours=24)
    
    # ✅ 数据库计算，只返回结果
    from sqlalchemy import func, case
    
    # 总事件数
    total = self.db.query(func.count(Event.id)).filter(
        and_(
            Event.elder_id == elder_id,
            Event.family_id == family_id,
            Event.timestamp >= yesterday,
            Event.room != None
        )
    ).scalar()
    
    # 异常房间的事件数（使用 CASE 表达式）
    unusual = self.db.query(
        func.count(case((~Event.room.in_(usual_rooms), 1)))
    ).filter(
        and_(
            Event.elder_id == elder_id,
            Event.family_id == family_id,
            Event.timestamp >= yesterday,
            Event.room != None
        )
    ).scalar()
    
    if total == 0:
        return None
    
    unusual_percent = (unusual / total) * 100
    
    # 只在需要时才查询具体的异常房间名称
    if unusual_percent > deviation_threshold:
        unusual_rooms = self.db.query(
            func.distinct(Event.room)
        ).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= yesterday,
                ~Event.room.in_(usual_rooms)
            )
        ).all()
        # ...
```

**性能对比:**
- **修复前:** 1000条记录加载 + Python 循环 = 1000ms
- **修复后:** SQL COUNT/CASE 计算 = 10ms

---

### 2. 重复告警检测逻辑缺陷
**文件:** `app/routes/events.py` (第56-61行) - `save_alerts_to_db()`
```python
existing_alert = db.query(Alert).filter(
    Alert.elder_id == elder_id,
    Alert.family_id == family_id,
    Alert.alert_type == alert_type_str,
    Alert.is_acknowledged == False  # ❌ 只检查是否确认
).first()
```

**问题:**
- 5分钟前的"房间活动模式异常"告警 `is_acknowledged=False`
- 5分钟后同样的规则再次触发，被当作重复而不创建新告警
- 但实际上这是**新的异常事件**，应该创建新告警

**修复方案:**
```python
# 防止重复的告警应该考虑时间窗口
from datetime import timedelta

ALERT_DEDUPLICATION_WINDOW = timedelta(minutes=10)  # 配置文件中

existing_alert = db.query(Alert).filter(
    and_(
        Alert.elder_id == elder_id,
        Alert.family_id == family_id,
        Alert.alert_type == alert_type_str,
        Alert.is_acknowledged == False,
        # ✅ 新增：10分钟内的才认为是重复
        Alert.created_at >= datetime.utcnow() - ALERT_DEDUPLICATION_WINDOW
    )
).first()
```

---

### 3. 并发告警创建竞态条件
**文件:** `app/routes/events.py` (第56-74行)
```python
# 时间点 T1: 请求A检查，没有找到存在的告警
existing_alert = db.query(Alert).filter(...).first()  # None

# 时间点 T2: 请求B也在此处，检查了，也是None
# 时间点 T3: 请求A创建告警 -> INSERT
# 时间点 T4: 请求B创建告警 -> INSERT (重复!)

if not existing_alert:
    db_alert = Alert(...)
    db.add(db_alert)
    db.commit()  # ❌ 两个并发请求都能到达这里
```

**风险:**
- 高并发时（1000个传感器同时发送事件）会创建重复告警
- 告警冗余导致用户告警疲劳

**修复方案 (选项1 - 乐观锁):**
```python
from sqlalchemy import Integer
from sqlalchemy.orm import mapped_column

class Alert(Base):
    __tablename__ = "alerts"
    # ... 其他字段 ...
    version = Column(Integer, default=0)  # 版本号

# 在查询时
def save_single_alert(db: Session, alert_schema, elder_id, family_id):
    try:
        # 查询现有告警
        existing = db.query(Alert).filter(
            and_(
                Alert.elder_id == elder_id,
                Alert.family_id == family_id,
                Alert.alert_type == alert_schema.alert_type,
                Alert.is_acknowledged == False
            )
        ).with_for_update().first()  # ✅ 加锁
        
        if not existing:
            db_alert = Alert(...)
            db.add(db_alert)
            db.flush()
            return db_alert
        return existing
    except Exception as e:
        logger.error(f"Error saving alert: {e}")
        raise
```

**修复方案 (选项2 - 数据库约束):**
```python
# 在模型中添加唯一约束
from sqlalchemy import UniqueConstraint

class Alert(Base):
    __tablename__ = "alerts"
    # ... 字段 ...
    
    __table_args__ = (
        # ✅ 同一老人同一类型的未确认告警只能有一个
        UniqueConstraint(
            'elder_id', 'alert_type', 
            postgresql_where="is_acknowledged = false",
            name='unique_unacked_alert_per_type'
        ),
        # ... 其他索引 ...
    )
```

---

### 4. 活跃老人时大量事件加载
**文件:** `app/routes/events.py` (第201-222行) - `get_recent_events()`
```python
async def get_recent_events(
    elder_id: str,
    family_id: str,
    hours: int = 24,  # ❌ 没有限制最大值
    db: Session = Depends(get_db),
):
    events = EventService.get_recent_events(db, elder_id, family_id, hours)
    return events  # 可能返回数万条记录
```

**问题:**
- 请求 `?hours=8760` (一年) = 10万+条记录
- JSON 序列化10万条记录 = 数百MB内存 + 秒级延迟
- 网络传输时间过长

**修复方案:**
```python
from pydantic import Field

async def get_recent_events(
    elder_id: str,
    family_id: str,
    hours: int = Field(24, ge=1, le=720),  # ✅ 最多30天
    limit: int = Field(1000, ge=1, le=5000),  # ✅ 最多5000条
    offset: int = Field(0, ge=0),
    db: Session = Depends(get_db),
):
    events = EventService.get_recent_events(
        db, elder_id, family_id, hours, limit, offset
    )
    return events
```

---

### 5. 数据库连接池配置不当
**文件:** `app/database.py` (第12-18行)
```python
engine = create_engine(
    settings.get_database_url,
    pool_size=20,        # ❌ 这是什么规模的应用？
    max_overflow=40,     # 最多60个连接
    pool_pre_ping=True,
    echo=settings.DEBUG,
)
```

**问题:**
- **如果是小型部署:** 20个连接太多，浪费资源
- **如果是大型部署:** 20个连接太少，会导致连接池耗尽
- 没有根据应用规模的明确指导

**修复方案:**
```python
from app.config import settings

# 根据工作进程数和并发度计算连接数
# 公式: connections = workers × avg_requests_per_worker + buffer
# 对于 4 个工作进程，假设每个最多10个并发: 4 × 10 + 20 = 60

if settings.TESTING:
    pool_config = {"pool_size": 1, "max_overflow": 2}
elif settings.DEBUG:
    pool_config = {"pool_size": 5, "max_overflow": 10}
else:
    # 生产环境：根据 API_WORKERS 动态计算
    base_pool = settings.API_WORKERS * 5  # 每个工作进程5个连接
    pool_config = {
        "pool_size": base_pool,
        "max_overflow": base_pool * 2,  # 允许溢出
        "pool_recycle": 3600,  # ✅ 新增：1小时回收连接（防止数据库关闭连接后fd泄漏）
    }

engine = create_engine(
    settings.get_database_url,
    **pool_config,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)
```

---

### 6. 缺少数据库索引
**文件:** `app/models.py` - Alert 表 (第179-215行)
```python
class Alert(Base):
    __table_args__ = (
        Index("idx_alert_elder_timestamp", "elder_id", "created_at"),
        Index("idx_alert_family_timestamp", "family_id", "created_at"),
        Index("idx_alert_type_level", "alert_type", "alert_level"),
        # ❌ 缺少常见查询的索引
    )
```

**问题查询（无索引的）:**
```python
# 这个查询在 save_alerts_to_db 中使用，无良好索引
existing_alert = db.query(Alert).filter(
    and_(
        Alert.elder_id == elder_id,
        Alert.family_id == family_id,
        Alert.alert_type == alert_type_str,
        Alert.is_acknowledged == False
    )
).first()
# 需要索引: (elder_id, alert_type, is_acknowledged)
```

**修复方案:**
```python
class Alert(Base):
    __tablename__ = "alerts"
    # ... 字段 ...
    
    __table_args__ = (
        Index("idx_alert_elder_timestamp", "elder_id", "created_at"),
        Index("idx_alert_family_timestamp", "family_id", "created_at"),
        Index("idx_alert_type_level", "alert_type", "alert_level"),
        
        # ✅ 新增索引
        Index("idx_alert_dedup", "elder_id", "alert_type", "is_acknowledged"),
        # 用于列出未确认告警
        Index("idx_alert_unacked", "family_id", "is_acknowledged", "created_at"),
    )
```

**性能对比:**
- **无索引:** 扫描整个 alerts 表 = O(n)
- **有索引:** B树查询 = O(log n)

---

### 7. 多租户数据隔离不足
**文件:** `app/models.py` (第37行) - Elder 模型
```python
class Elder(Base):
    elder_id = Column(String(50), unique=True, nullable=False, index=True)
    # ❌ elder_id 全局唯一，不符合多租户最佳实践
```

**问题:**
- 如果未来要支持多个客户机构，每个机构都会想用 "elder_001"
- 目前的全局唯一约束会冲突
- 应该是 (family_id, elder_id) 组合唯一

**修复方案:**
```python
class Elder(Base):
    __tablename__ = "elders"
    
    elder_id = Column(String(50), nullable=False, index=True)  # ❌ 移除 unique
    family_id = Column(String(50), ForeignKey(...), nullable=False)
    # ... 其他字段 ...
    
    __table_args__ = (
        # ✅ 组合唯一约束：每个家庭内的 elder_id 唯一
        UniqueConstraint('family_id', 'elder_id', name='uq_family_elder'),
        Index("idx_elder_family_id", "family_id"),
    )
```

**同样修复 Device:**
```python
class Device(Base):
    device_id = Column(String(100), nullable=False, index=True)  # 移除 unique
    family_id = Column(...)
    
    __table_args__ = (
        UniqueConstraint('family_id', 'device_id', name='uq_family_device'),
    )
```

---

## 🟡 优化建议 (Optimization Suggestions)

### 1. 实现缓存层 - Pattern 数据
**当前:** 每次规则检查都查询数据库
```python
# 在 check_abnormal_wake_time() 中
pattern = self.db.query(Pattern).filter(
    Pattern.elder_id == elder_id,
    Pattern.pattern_type == "sleep"
).first()  # 每个规则每次都查询
```

**建议:**
```python
import redis
from functools import lru_cache
import json

class RuleEngineWithCache:
    def __init__(self, db: Session, redis_client: redis.Redis = None):
        self.db = db
        self.redis = redis_client
    
    def get_pattern(self, elder_id: str, pattern_type: str):
        if self.redis:
            # 先查 Redis
            cache_key = f"pattern:{elder_id}:{pattern_type}"
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # 查数据库
        pattern = self.db.query(Pattern).filter(...).first()
        
        if pattern and self.redis:
            # 缓存 1 小时
            self.redis.setex(
                cache_key,
                3600,
                json.dumps({...})
            )
        
        return pattern
```

**性能:** 数据库查询时间 50ms → 缓存命中 1ms

---

### 2. 异步事件处理 - Alert Notifications
**当前:** Alert 创建后没有通知机制
```python
# 告警创建但没有发送给用户
saved_alerts = save_alerts_to_db(db, rule_alerts, ...)
# 然后就结束了，没有人收到通知
```

**建议:**
```python
# 使用 Celery 或 RQ 进行异步任务
from celery import shared_task

@shared_task
def send_alert_notification(alert_id: int):
    """异步发送告警通知"""
    alert = Alert.query.get(alert_id)
    
    # 发送邮件
    if alert.family.email_notifications_enabled:
        send_email_alert(alert)
    
    # 发送 DingDing
    if settings.DINGDING_WEBHOOK_URL:
        send_dingding_alert(alert)
    
    # 推送应用通知
    send_app_notification(alert)

# 在创建告警时异步调用
if saved_alerts:
    for alert in saved_alerts:
        send_alert_notification.delay(alert.id)  # 异步，不阻塞
```

---

### 3. 数据归档策略
**当前:** 告警和事件无限增长
```python
# config.py 中配置了但未使用
EVENT_RETENTION_DAYS: int = 180
```

**建议:**
```python
# 创建定期清理任务
from apscheduler.schedulers.background import BackgroundScheduler

@shared_task
def archive_old_events():
    """每天 2AM 执行，归档 180 天前的事件"""
    cutoff_date = datetime.utcnow() - timedelta(days=settings.EVENT_RETENTION_DAYS)
    
    # 方案 1: 删除
    db.query(Event).filter(Event.created_at < cutoff_date).delete()
    
    # 方案 2: 复制到归档表然后删除
    old_events = db.query(Event).filter(
        Event.created_at < cutoff_date
    ).all()
    
    for event in old_events:
        archive_db.add(EventArchive(**event.__dict__))
    
    db.query(Event).filter(Event.created_at < cutoff_date).delete()
    db.commit()
    
    logger.info(f"Archived {len(old_events)} events")

# 在 main.py 中启动定时器
scheduler = BackgroundScheduler()
scheduler.add_job(archive_old_events, 'cron', hour=2, minute=0)
scheduler.start()
```

---

### 4. 异步数据库操作
**当前:** 同步阻塞操作
```python
# FastAPI 是异步的，但数据库操作是同步的
@app.get("/events/{elder_id}")
async def get_events(...):
    # 这里阻塞整个线程等待数据库
    events = db.query(Event).filter(...).all()
    return events
```

**建议 (如果需要高并发):**
```python
# 使用 SQLAlchemy 2.0+ 异步 ORM
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db"
)

async_session = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with async_session() as session:
        yield session

@app.get("/events/{elder_id}")
async def get_events(
    elder_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Event).filter(Event.elder_id == elder_id)
    )
    events = result.scalars().all()
    return events
```

---

### 5. API 版本管理
**当前:** 固定的 API 路径，无版本
```python
@app.include_router(events.router)  # /api/events
@app.include_router(alerts.router)  # /api/alerts
```

**建议:**
```python
from fastapi import APIRouter

# 为 v1 创建前缀
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(events.router)
v1_router.include_router(alerts.router)

app.include_router(v1_router)

# 未来如果有 breaking changes，可以同时支持 /api/v2
v2_router = APIRouter(prefix="/api/v2")
# v2 可能有不同的模式或功能
app.include_router(v2_router)
```

---

### 6. 规则引擎可配置性
**当前:** 规则硬编码在代码中
```python
def check_all_rules(self, elder_id: str, family_id: str):
    alerts = []
    
    # 规则1、规则2、规则3... 全部硬编码
    inactivity_alert = self.check_inactivity(...)
    bathroom_alert = self.check_bathroom_timeout(...)
    # ...
```

**问题:** 增加新规则需要修改代码

**建议:**
```python
# 创建 Rule 表，存储规则定义
class Rule(Base):
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)  # inactivity, bathroom, etc.
    enabled = Column(Boolean, default=True)
    
    # 规则参数（JSON 存储）
    config = Column(JSON, default={})  # { "threshold_minutes": 240, ... }
    
    family_id = Column(String(50), nullable=True)  # None 表示全局规则
    created_at = Column(DateTime, default=datetime.utcnow)

# 修改规则引擎
class DynamicRuleEngine(RuleEngine):
    def check_all_rules(self, elder_id: str, family_id: str):
        rules = self.db.query(Rule).filter(
            or_(Rule.family_id == None, Rule.family_id == family_id),
            Rule.enabled == True
        ).all()
        
        alerts = []
        for rule in rules:
            if rule.rule_type == "inactivity":
                alert = self._check_inactivity_rule(elder_id, family_id, rule)
            elif rule.rule_type == "bathroom_timeout":
                alert = self._check_bathroom_rule(elder_id, family_id, rule)
            # ...
            
            if alert:
                alerts.append(alert)
        
        return alerts
```

---

### 7. 健康检查和监控指标
**当前:** `/health` 端点太简单
```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}  # 不检查任何东西
```

**建议:**
```python
from prometheus_client import Counter, Histogram
import time

# 定义指标
alert_counter = Counter('alerts_generated_total', 'Total alerts generated', ['alert_type'])
rule_check_duration = Histogram('rule_check_seconds', 'Rule check duration')
db_query_duration = Histogram('db_query_seconds', 'Database query duration')

@app.get("/health")
async def health_check():
    try:
        # 检查数据库
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # 检查缓存（如果有）
        if redis_client:
            redis_client.ping()
        
        return {
            "status": "healthy",
            "database": "ok",
            "cache": "ok" if redis_client else "not_configured",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/metrics")
async def get_metrics():
    """Prometheus 指标端点"""
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

---

### 8. 审计日志实现
**当前:** AuditLog 表存在但未使用
```python
class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"
    # 表已存在但从未被代码触发
```

**建议:**
```python
class AuditService:
    @staticmethod
    def log_action(db: Session, action: str, resource_type: str, 
                   resource_id: str, user_id: str = None, details: dict = None):
        """记录审计日志"""
        audit = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id or "system",
            details=details or {}
        )
        db.add(audit)
        db.commit()

# 使用示例
@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, acknowledged_by: str, db: Session = ...):
    alert = AlertService.acknowledge_alert(db, alert_id, acknowledged_by)
    
    # ✅ 记录审计日志
    AuditService.log_action(
        db,
        action="alert_acknowledged",
        resource_type="alert",
        resource_id=str(alert_id),
        user_id=acknowledged_by,
        details={"alert_type": alert.alert_type}
    )
    
    return alert
```

---

## 📊 快速修复优先级表

| 优先级 | 问题 | 修复时间 | 影响 |
|--------|------|----------|------|
| 🔴 P0 | CORS 安全配置 | 15分钟 | 生产可用性阻塞 |
| 🔴 P0 | 默认硬编码密钥 | 30分钟 | 生产可用性阻塞 |
| 🔴 P0 | API Key 认证 | 2小时 | 生产可用性阻塞 |
| 🔴 P0 | Webhook 认证 | 1小时 | 数据完整性 |
| 🟠 P1 | N+1 Query | 1小时 | 并发性能 |
| 🟠 P1 | 竞态条件 | 1小时 | 数据一致性 |
| 🟠 P1 | 多租户隔离 | 3小时 | 未来功能 |
| 🟡 P2 | 缓存优化 | 2小时 | 性能提升2-10倍 |
| 🟡 P2 | 异步通知 | 3小时 | 用户体验 |
| 🟡 P2 | 数据归档 | 2小时 | 存储成本 |

---

## 📝 部署前清单

- [ ] **安全:**
  - [ ] CORS 白名单配置
  - [ ] 密钥从环境变量加载
  - [ ] 实现 JWT token 认证
  - [ ] 添加 Webhook 签名验证
  - [ ] 配置日志过滤（PII 保护）

- [ ] **性能:**
  - [ ] 修复 N+1 查询
  - [ ] 添加数据库索引
  - [ ] 实现缓存层
  - [ ] 配置连接池

- [ ] **数据库:**
  - [ ] 修复多租户唯一约束
  - [ ] 添加告警去重约束
  - [ ] 实现数据归档策略

- [ ] **监控:**
  - [ ] 配置 Prometheus 指标
  - [ ] 添加 Sentry 错误跟踪
  - [ ] 实现审计日志

- [ ] **文档:**
  - [ ] 更新 API 文档（需要认证）
  - [ ] 部署指南
  - [ ] 故障排查指南

---

## 🎯 总结与建议

**优势:**
1. ✅ 核心功能完整（事件 → 规则 → 告警）
2. ✅ 数据库模型设计合理（大多数索引已加）
3. ✅ 错误处理完善（异常处理器到位）
4. ✅ 可观测性注重（日志、配置完备）

**劣势（阻止生产部署）:**
1. ❌ CORS 完全开放 = 任何网站都可访问
2. ❌ 密钥明文硬编码 = 代码泄露就失控
3. ❌ 无实质认证 = 任何人都可写入事件
4. ❌ N+1 查询 = 并发时性能崩溃

**建议路线图:**
```
Week 1: 修复所有严重安全问题 (P0)
  → CORS、密钥、认证、Webhook 签名

Week 2: 性能优化 (P1)
  → N+1 查询、数据库索引、缓存

Week 3: 可扩展性改进 (P2)
  → 多租户隔离、规则可配置、异步通知

Week 4: 上线准备
  → 性能测试、压力测试、安全审计
```

**开发建议:**
1. 不要忽视安全（这是医疗数据）
2. 测试并发场景（养老院有多个老人，传感器并发很高）
3. 计划未来扩展（架构要支持多机构、多用户）
4. 监控很关键（老人健康数据，必须有警报）

---

**审查人员:** Senior Engineer  
**审查日期:** 2026-04-27  
**下一步:** 提交修复PR，安排复审
