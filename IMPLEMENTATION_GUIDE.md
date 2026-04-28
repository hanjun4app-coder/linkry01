# 修复实施指南
## 优先级顺序 & 具体代码修改

---

## 🔴 第一优先级：安全性 (4-6 小时)

### 修复 1: CORS 配置
**文件:** `app/config.py`

```python
# ❌ 改前
ALLOW_ORIGINS: List[str] = ["*"]

# ✅ 改后
ALLOW_ORIGINS: List[str] = Field(
    default=["http://localhost:3000"] if DEBUG else [],
    description="Allowed CORS origins"
)

@field_validator('ALLOW_ORIGINS')
def validate_origins(cls, v, info):
    if not v and not info.data.get('DEBUG'):
        raise ValueError("ALLOW_ORIGINS must be configured in production")
    return v
```

**docker-compose.yml 更新:**
```yaml
environment:
  # 添加环境变量覆盖
  ALLOW_ORIGINS: '["https://elderly-care.example.com"]'
```

---

### 修复 2: 密钥管理
**文件:** `app/config.py`

```python
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    # ❌ 改前
    # SECRET_KEY: str = "your-secret-key-change-in-production"
    # API_KEY: str = "your-api-key-change-in-production"
    
    # ✅ 改后 - 必须从环境变量加载
    SECRET_KEY: SecretStr = Field(..., description="Must be set from .env or environment")
    API_KEY: SecretStr = Field(..., description="Must be set from .env or environment")
    
    # 验证生产环境
    @model_validator(mode='after')
    def validate_production_secrets(self):
        if not self.DEBUG:
            # 生产环境，确保密钥被正确设置（不是默认值）
            if str(self.SECRET_KEY).startswith('your-'):
                raise ValueError("SECRET_KEY not properly configured for production")
            if str(self.API_KEY).startswith('your-'):
                raise ValueError("API_KEY not properly configured for production")
        return self
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # 防止密钥在日志中暴露
        json_encoders = {
            SecretStr: lambda v: "***" if v else None
        }
```

**创建 `.env` 文件 (需要在 .gitignore 中):**
```bash
# .env
DEBUG=False
SECRET_KEY=your-extremely-random-secret-key-min-32-chars-abcdefghijklmnopqrstuvwxyz1234567890
API_KEY=your-random-api-key-min-32-chars-change-in-production
```

**生成安全的密钥:**
```bash
# 在 Python 中
import secrets
import base64

secret_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
api_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

print(f"SECRET_KEY={secret_key}")
print(f"API_KEY={api_key}")
```

---

### 修复 3: JWT 认证实现
**创建文件:** `app/security.py`

```python
"""安全相关功能"""
from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthCredential
from pydantic import BaseModel
from app.config import settings

security = HTTPBearer()

class TokenPayload(BaseModel):
    """Token 载荷"""
    device_id: str
    family_id: str
    exp: int
    iat: int

def create_access_token(device_id: str, family_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    if expires_delta is None:
        expires_delta = timedelta(days=365)  # 可以改为更短期限
    
    expire = datetime.utcnow() + expires_delta
    payload = {
        "device_id": device_id,
        "family_id": family_id,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }
    
    encoded_jwt = jwt.encode(
        payload,
        str(settings.SECRET_KEY),
        algorithm="HS256"
    )
    return encoded_jwt

async def verify_token(credentials: HTTPAuthCredential = Depends(security)) -> TokenPayload:
    """验证 JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            str(settings.SECRET_KEY),
            algorithms=["HS256"]
        )
        
        # 检查过期
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        
        return TokenPayload(**payload)
    
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

# 向后兼容：简单 API Key 验证（逐步淘汰）
async def verify_api_key_deprecated(credentials: HTTPAuthCredential = Depends(security)) -> str:
    """已弃用：仅用于向后兼容"""
    if credentials.credentials != str(settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials
```

**修改 `app/routes/events.py`:**

```python
from app.security import verify_token

@router.post("", response_model=EventResponse, summary="创建单个事件")
async def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    # ✅ 改为 JWT 验证
    token: TokenPayload = Depends(verify_token)
):
    """
    创建单个事件（使用 JWT token 认证）
    
    请求头:
    ```
    Authorization: Bearer <jwt_token>
    ```
    """
    # ✅ 验证 token 中的 device_id 和 family_id 与请求匹配
    if event.family_id != token.family_id:
        raise HTTPException(
            status_code=403,
            detail="Token not authorized for this family"
        )
    
    try:
        # 确保老人存在
        ElderService.get_or_create_elder(db, event.elder_id, event.family_id)
        
        # 创建事件
        response = EventService.create_event(db, event)
        
        # 检查规则
        rule_engine = RuleEngine(db)
        rule_alerts = rule_engine.check_all_rules(event.elder_id, event.family_id)
        
        if rule_alerts:
            saved_alerts = save_alerts_to_db(db, rule_alerts, event.elder_id, event.family_id)
            logger.warning(f"Alerts generated: {len(saved_alerts)} for elder {event.elder_id}")
        
        return response
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

**同样修改 `app/routes/alerts.py`:**
```python
from app.security import verify_token

@router.get("", response_model=AlertListResponse)
async def query_alerts(
    # ... 其他参数 ...
    token: TokenPayload = Depends(verify_token)  # ✅ 添加认证
):
    # ✅ 确保用户只能查看其 family_id 的告警
    if family_id and family_id != token.family_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # ... 继续处理 ...
```

---

### 修复 4: Webhook 签名验证
**文件:** `app/main.py`

```python
import hashlib
from hmac import compare_digest
import json
from fastapi import Request

@app.post("/webhook/home_assistant", summary="Home Assistant Webhook")
async def home_assistant_webhook(request: Request):
    """验证签名的 Home Assistant Webhook"""
    
    # 获取签名头
    signature = request.headers.get("X-HA-Webhook-Signature", "")
    
    if not signature:
        logger.warning(f"Missing webhook signature from {request.client.host}")
        raise HTTPException(status_code=401, detail="Missing signature")
    
    # 读取请求体
    body = await request.body()
    
    # 计算签名 (SHA256)
    expected_signature = hashlib.sha256(
        f"{settings.HOME_ASSISTANT_WEBHOOK_SECRET}{body.decode()}".encode()
    ).hexdigest()
    
    # 安全对比签名
    provided_signature = signature.split("=")[-1] if "=" in signature else signature
    
    if not compare_digest(expected_signature, provided_signature):
        logger.warning(f"Invalid webhook signature from {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # ✅ 签名验证通过，处理数据
    try:
        data = json.loads(body)
        
        from app.database import SessionLocal
        from app.services import EventService
        from app.schemas import EventCreate, EventType, DeviceType
        
        db = SessionLocal()
        
        event = EventCreate(
            elder_id=data.get("elder_id", "unknown"),
            family_id=data.get("family_id", "unknown"),
            device_id=data.get("entity_id", "ha_device"),
            device_type=DeviceType.CUSTOM,
            event_type=EventType(data.get("event_type", "custom")),
            event_value=data.get("state", {}),
            room=data.get("room"),
            timestamp=datetime.utcnow()
        )
        
        response = EventService.create_event(db, event)
        db.close()
        
        return {
            "status": "success",
            "event_id": response.id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

**在 Home Assistant 中配置:**
```yaml
# configuration.yaml
automation:
  - alias: "Send events to elderly care API"
    trigger:
      platform: event
      event_type: any_event
    action:
      - service: rest_command.send_to_elderly_care_api
        data_template:
          elder_id: "{{ states('input_text.elder_id') }}"
          family_id: "{{ states('input_text.family_id') }}"
          event_type: "{{ trigger.event.event_type }}"

rest_command:
  send_to_elderly_care_api:
    url: "http://elderly-care-api:8000/webhook/home_assistant"
    method: POST
    payload: '{"elder_id": "{{ elder_id }}", "family_id": "{{ family_id }}", "event_type": "{{ event_type }}"}'
    headers:
      X-HA-Webhook-Signature: "sha256=<calculated_signature>"
```

---

## 🟠 第二优先级：性能 (2-3 小时)

### 修复 5: N+1 查询 - room_pattern_change
**文件:** `app/rules.py`

```python
def check_room_pattern_change(self, elder_id: str, family_id: str) -> Optional[AlertSchema]:
    """
    检测房间活动模式是否偏离基线
    ✅ 已优化为数据库级别计算
    """
    from sqlalchemy import func, case
    
    deviation_threshold = settings.ROOM_ACTIVITY_DEVIATION_PERCENT
    
    pattern = self.db.query(Pattern).filter(
        and_(
            Pattern.elder_id == elder_id,
            Pattern.pattern_type == "location"
        )
    ).first()
    
    if not pattern or not pattern.usual_active_rooms:
        return None
    
    usual_rooms = pattern.usual_active_rooms
    
    yesterday = datetime.utcnow() - timedelta(hours=24)
    
    # ✅ 在数据库层计算，不加载所有记录
    result = self.db.query(
        func.count(Event.id).label('total'),
        func.count(
            case(
                (Event.room.notin_(usual_rooms), 1)
            )
        ).label('unusual')
    ).filter(
        and_(
            Event.elder_id == elder_id,
            Event.family_id == family_id,
            Event.timestamp >= yesterday,
            Event.room != None
        )
    ).first()
    
    if not result or result.total == 0:
        return None
    
    total = result.total
    unusual = result.unusual or 0
    unusual_activity_percent = (unusual / total) * 100
    
    if unusual_activity_percent > deviation_threshold:
        # 只在需要时查询具体房间名称
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
        
        unusual_rooms_list = [r[0] for r in unusual_rooms]
        
        logger.warning(f"Elder {elder_id} room pattern change: {unusual_activity_percent:.0f}%")
        return AlertSchema(
            elder_id=elder_id,
            family_id=family_id,
            alert_type=AlertType.ROOM_PATTERN_CHANGE,
            alert_level=AlertLevel.WARNING,
            message=f"房间活动模式异常：{unusual_activity_percent:.0f}% 的活动在非常去房间 {unusual_rooms_list}",
            details={
                "deviation_threshold_percent": deviation_threshold,
                "unusual_activity_percent": unusual_activity_percent,
                "baseline_rooms": usual_rooms,
                "unusual_rooms": unusual_rooms_list,
                "time_window_hours": 24,
                "detected_at": datetime.utcnow().isoformat()
            }
        )
    
    return None
```

**测试性能提升:**
```bash
# 修复前（加载所有事件）
SELECT * FROM events WHERE elder_id='elder_001' AND family_id='family_001' AND timestamp >= '2026-04-26 00:00:00';
# Result: 1000 rows, 50ms

# 修复后（数据库计算）
SELECT COUNT(*), COUNT(CASE WHEN room NOT IN (...) THEN 1 END) FROM events...
# Result: 1 row, 5ms
```

---

### 修复 6: 添加数据库索引
**文件:** `app/models.py`

```python
class Alert(Base):
    __tablename__ = "alerts"
    # ... 其他字段 ...
    
    __table_args__ = (
        # 现有索引
        Index("idx_alert_elder_timestamp", "elder_id", "created_at"),
        Index("idx_alert_family_timestamp", "family_id", "created_at"),
        Index("idx_alert_type_level", "alert_type", "alert_level"),
        
        # ✅ 新增索引：用于重复检测
        Index("idx_alert_dedup", "elder_id", "alert_type", "is_acknowledged"),
        
        # ✅ 新增索引：用于列出未确认告警
        Index("idx_alert_unacked", "family_id", "is_acknowledged", "created_at"),
    )
```

**创建迁移脚本:** `db/migrations/001_add_indices.sql`

```sql
-- 添加缺失的索引
CREATE INDEX CONCURRENTLY idx_alert_dedup 
ON alerts(elder_id, alert_type, is_acknowledged) 
WHERE is_acknowledged = false;

CREATE INDEX CONCURRENTLY idx_alert_unacked 
ON alerts(family_id, is_acknowledged, created_at DESC) 
WHERE is_acknowledged = false;

-- 验证索引
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'alerts';
```

---

### 修复 7: 解决并发告警创建

**文件:** `app/routes/events.py` - 修改 `save_alerts_to_db()`

```python
def save_alerts_to_db(db: Session, rule_alerts: List, elder_id: str, family_id: str) -> List[Alert]:
    """保存规则生成的告警到数据库（支持并发）"""
    saved_alerts = []
    
    try:
        for alert in rule_alerts:
            try:
                alert_type_str = alert.alert_type.value if hasattr(alert.alert_type, 'value') else str(alert.alert_type)
                alert_level_str = alert.alert_level.value if hasattr(alert.alert_level, 'value') else str(alert.alert_level)
                message_str = str(alert.message) if alert.message else "Alert triggered"
                details_dict = alert.details if isinstance(alert.details, dict) else (dict(alert.details) if alert.details else {})
                
                logger.info(f"Processing alert: type={alert_type_str}, level={alert_level_str}")
                
                # ✅ 防重复：加锁并检查
                from sqlalchemy import and_
                from sqlalchemy.orm import Query
                
                # 使用行级锁防止竞态条件
                existing_alert = db.query(Alert).filter(
                    and_(
                        Alert.elder_id == elder_id,
                        Alert.family_id == family_id,
                        Alert.alert_type == alert_type_str,
                        Alert.is_acknowledged == False
                    )
                ).with_for_update().first()  # ✅ 加锁
                
                if not existing_alert:
                    # 创建新告警
                    db_alert = Alert(
                        alert_id=str(uuid.uuid4()),
                        family_id=family_id,
                        elder_id=elder_id,
                        alert_type=alert_type_str,
                        alert_level=alert_level_str,
                        message=message_str,
                        details=details_dict,
                        is_acknowledged=False
                    )
                    db.add(db_alert)
                    db.flush()
                    logger.info(f"Created new alert: id={db_alert.id}")
                    saved_alerts.append(db_alert)
                else:
                    logger.info(f"Alert already exists: {alert_type_str}")
                    saved_alerts.append(existing_alert)
            
            except Exception as e:
                logger.error(f"Error processing alert: {e}", exc_info=True)
                # 回滚当前告警，继续处理其他
                db.rollback()
                continue
        
        # 提交所有告警
        db.commit()
        
        # 刷新获取数据库字段
        for alert in saved_alerts:
            db.refresh(alert)
        
        return saved_alerts
    
    except Exception as e:
        logger.error(f"Critical error in save_alerts_to_db: {e}", exc_info=True)
        db.rollback()
        return []
```

---

## 🟡 第三优先级：数据库安全 (2 小时)

### 修复 8: 多租户约束修正
**文件:** `app/models.py`

```python
class Elder(Base):
    """老人信息"""
    __tablename__ = "elders"
    
    id = Column(Integer, primary_key=True)
    # ❌ 改前: elder_id = Column(String(50), unique=True, ...)
    # ✅ 改后: 组合唯一约束
    elder_id = Column(String(50), nullable=False, index=True)
    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    
    # ... 其他字段 ...
    
    __table_args__ = (
        # ✅ 每个家庭内的 elder_id 唯一
        UniqueConstraint('family_id', 'elder_id', name='uq_family_elder'),
        Index("idx_elder_family_id", "family_id"),
    )

class Device(Base):
    """设备信息"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True)
    # ❌ 改前: device_id = Column(String(100), unique=True, ...)
    # ✅ 改后: 组合唯一约束
    device_id = Column(String(100), nullable=False, index=True)
    device_type = Column(String(50), nullable=False)
    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    
    # ... 其他字段 ...
    
    __table_args__ = (
        # ✅ 每个家庭内的 device_id 唯一
        UniqueConstraint('family_id', 'device_id', name='uq_family_device'),
        Index("idx_device_family_id", "family_id"),
    )
```

**迁移脚本:** `db/migrations/002_fix_multitenancy.sql`

```sql
-- 删除现有的全局唯一约束
ALTER TABLE elders DROP CONSTRAINT elders_elder_id_key;
ALTER TABLE devices DROP CONSTRAINT devices_device_id_key;

-- 添加组合唯一约束
ALTER TABLE elders 
ADD CONSTRAINT uq_family_elder UNIQUE(family_id, elder_id);

ALTER TABLE devices 
ADD CONSTRAINT uq_family_device UNIQUE(family_id, device_id);

-- 验证
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name IN ('elders', 'devices');
```

---

## 📋 修复检查清单

执行顺序（推荐）：

```
Day 1 - 安全修复（6小时）:
  ✅ CORS 配置白名单
  ✅ 密钥从环境变量加载
  ✅ JWT 认证实现
  ✅ Webhook 签名验证
  ⏱️ 部署测试

Day 2 - 性能优化（4小时）:
  ✅ N+1 查询修复
  ✅ 数据库索引添加
  ✅ 并发竞态条件修复
  ⏱️ 压力测试

Day 3 - 数据库约束（2小时）:
  ✅ 多租户约束修正
  ⏱️ 迁移验证

Day 4 - 验收（4小时）:
  ⏱️ 代码审查
  ⏱️ 功能测试
  ⏱️ 安全扫描
  ⏱️ 部署前检查
```

---

## 🧪 测试命令

```bash
# 生成 JWT token
python -c "
from app.security import create_access_token
token = create_access_token('device_001', 'family_001')
print(f'Bearer {token}')
"

# 测试创建事件
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer <token_here>" \
  -H "Content-Type: application/json" \
  -d '{
    "elder_id": "elder_001",
    "family_id": "family_001",
    "device_id": "aqara_fp2_bedroom",
    "device_type": "aqara_fp2",
    "event_type": "presence",
    "event_value": {"detected": true},
    "room": "bedroom"
  }'

# 性能测试：并发创建100个事件
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/events \
    -H "Authorization: Bearer <token>" \
    -H "Content-Type: application/json" \
    -d "{...}" &
done
wait
```

---

## 📞 遇到问题？

| 问题 | 解决方案 |
|------|----------|
| JWT token 过期 | 刷新 token 或联系管理员重新生成 |
| 迁移失败 | 检查 `pg_migrations` 表，手动回滚 |
| 性能仍然慢 | 运行 `ANALYZE; VACUUM;` 更新统计信息 |
| Webhook 签名不匹配 | 检查 HOME_ASSISTANT_WEBHOOK_SECRET 环境变量 |

---

**预计总耗时:** 16-20 小时（根据团队规模和经验）  
**建议:** 按优先级逐个合并 PR，每个修复后运行完整测试套件
