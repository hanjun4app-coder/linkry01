# 反馈闭环 - 代码修改清单

本文档详细说明需要在现有代码中做出的修改。

---

## 修改 1: app/main.py

### 位置：导入部分

在现有的导入之后添加：

```python
# 现有导入
from app.routes import events, alerts, patterns, maintenance
from app.tasks import scheduled_tasks

# ===================== 新增导入 =====================
from app.routes import public  # 添加这一行
```

### 位置：应用初始化部分

在现有的路由注册之后添加：

```python
# 现有路由注册
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(patterns.router)
app.include_router(maintenance.router)

# ===================== 新增路由注册 =====================
app.include_router(public.router)  # 添加这一行
```

### 完整示例（app/main.py 关键部分）

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 现有导入
from app.routes import events, alerts, patterns, maintenance
from app.tasks import scheduled_tasks

# ===================== 新增导入 =====================
from app.routes import public

# ... 其他导入

# 定义生命周期事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    await scheduled_tasks.start()
    yield
    # 关闭
    await scheduled_tasks.stop()

# 创建应用
app = FastAPI(
    title="Elderly Care AI",
    description="AI-powered elderly care system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== 路由注册 =====================
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(patterns.router)
app.include_router(maintenance.router)
app.include_router(public.router)  # 新增：反馈闭环路由

# ... 其他端点定义
```

---

## 修改 2: app/routes/alerts.py

### 位置：导入部分

在现有导入之后添加：

```python
# 现有导入
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

# ... 其他导入

# ===================== 新增导入 =====================
from app.services_feedback import FeedbackTokenService
import logging

logger = logging.getLogger(__name__)
```

### 位置：告警创建端点

**场景 1**：如果使用事件创建告警（推荐）

```python
@router.post("/api/events")
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """
    创建事件并检测告警
    
    在规则引擎检测到告警后，自动生成反馈令牌
    """
    
    # ... 现有事件创建逻辑 ...
    
    # 规则检测后生成告警（假设告警已创建）
    # db.add(alert)
    # db.commit()
    # db.refresh(alert)
    
    # ===================== 新增：生成反馈令牌 =====================
    if alert:  # 如果生成了告警
        success, token, feedback_url = FeedbackTokenService.generate_feedback_token(
            db=db,
            alert_id=str(alert.alert_id),
            token_expiry_hours=72  # 72 小时后过期
        )
        
        if success:
            logger.info(f"反馈令牌已生成: alert_id={alert.alert_id}, url={feedback_url}")
            # 可选：将反馈 URL 包含在响应中
            # alert_response['feedback_url'] = feedback_url
        else:
            logger.warning(f"反馈令牌生成失败: alert_id={alert.alert_id}")
    
    # 返回响应
    return {
        "event_id": str(event.event_id),
        "alerts": [{"alert_id": str(alert.alert_id)} for alert in alerts],
        # 可选：如果需要在响应中包含反馈 URL
        # "feedback_urls": {str(alert.alert_id): ... for alert in alerts}
    }
```

**场景 2**：如果有专门的告警创建端点

```python
@router.post("/api/alerts")
async def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    """创建告警"""
    
    # ... 现有告警创建逻辑 ...
    
    alert = Alert(
        alert_id=uuid.uuid4(),
        alert_type=alert_data.alert_type,
        alert_level=alert_data.alert_level,
        elder_id=alert_data.elder_id,
        family_id=alert_data.family_id,
        created_at=datetime.utcnow()
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # ===================== 新增：生成反馈令牌 =====================
    success, token, feedback_url = FeedbackTokenService.generate_feedback_token(
        db=db,
        alert_id=str(alert.alert_id),
        token_expiry_hours=72
    )
    
    logger.info(f"告警已创建: {alert.alert_id}, 反馈 URL: {feedback_url}")
    
    # 返回响应（包含反馈 URL）
    return {
        "alert_id": str(alert.alert_id),
        "alert_type": alert.alert_type,
        "alert_level": alert.alert_level,
        "feedback_url": feedback_url if success else None,
        "created_at": alert.created_at
    }
```

---

## 修改 3: SMS/通知服务（可选但推荐）

如果系统有 SMS 通知服务，更新以包含反馈链接。

### 示例：Twilio 集成

```python
# 文件：app/services/notifications.py（或类似的通知服务文件）

from app.services_feedback import FeedbackTokenService
from sqlalchemy.orm import Session

class NotificationService:
    """通知服务"""
    
    @staticmethod
    async def send_alert_notification(
        alert_id: str,
        elder_name: str,
        phone_number: str,
        alert_type: str,
        db: Session,
        twilio_client
    ):
        """
        发送告警通知（包含反馈链接）
        
        Args:
            alert_id: 告警 ID
            elder_name: 老人名字
            phone_number: 联系电话
            alert_type: 告警类型
            db: 数据库连接
            twilio_client: Twilio 客户端
        """
        
        # 获取反馈 URL
        feedback_url = FeedbackTokenService.get_feedback_url(db, alert_id)
        
        # 构建短信内容
        if feedback_url:
            sms_body = f"""
            【养老助手】
            {elder_name}处检测到 {alert_type}。
            
            请点击链接反馈准确性:
            {feedback_url}
            
            链接72小时内有效
            """
        else:
            sms_body = f"""
            【养老助手】
            {elder_name}处检测到 {alert_type}。
            请及时查看。
            """
        
        # 发送 SMS
        try:
            message = twilio_client.messages.create(
                body=sms_body,
                from_=os.getenv('TWILIO_PHONE_NUMBER'),
                to=phone_number
            )
            logger.info(f"短信已发送: sid={message.sid}, alert_id={alert_id}")
            return True
        except Exception as e:
            logger.error(f"短信发送失败: {str(e)}")
            return False
```

### 示例：自定义通知服务

```python
# 文件：app/services/notifications.py

async def notify_alert(
    alert: Alert,
    db: Session,
    phone_number: str
):
    """发送告警通知"""
    
    from app.services_feedback import FeedbackTokenService
    
    # 获取反馈链接
    feedback_url = FeedbackTokenService.get_feedback_url(db, str(alert.alert_id))
    
    # 构建消息
    message = f"""
    【养老关护系统】
    
    检测到异常情况，请确认：
    
    告警类型: {alert.alert_type}
    严重程度: {alert.alert_level}
    时间: {alert.created_at.strftime('%H:%M')}
    
    反馈链接: {feedback_url}
    (72小时内有效)
    
    感谢您的配合！
    """
    
    # 使用您的短信服务发送
    # 例如：阿里云、腾讯云、运营商 API 等
    await your_sms_provider.send(phone_number, message)
```

---

## 修改 4: 定时任务（可选）

如果需要定期清理过期的令牌，在定时任务中添加。

### 位置：app/tasks.py

```python
from app.services_feedback import FeedbackTokenService

class ScheduledTasks:
    """定时任务管理"""
    
    async def daily_cleanup_tokens(self):
        """每天清理过期的反馈令牌"""
        db = SessionLocal()
        try:
            success, deleted_count = FeedbackTokenService.cleanup_expired_tokens(db)
            if success:
                logger.info(f"清理过期令牌成功: 删除 {deleted_count} 个令牌")
            else:
                logger.warning("清理过期令牌失败")
        except Exception as e:
            logger.error(f"清理令牌异常: {str(e)}")
        finally:
            db.close()
    
    async def start(self):
        """启动定时任务"""
        # 现有任务...
        
        # ===================== 新增：令牌清理任务 =====================
        # 每天 04:00 执行一次
        asyncio.create_task(self._schedule_cleanup_tokens())
    
    async def _schedule_cleanup_tokens(self):
        """定时执行清理任务"""
        while True:
            await self._wait_until_time(4, 0)  # 04:00
            await self.daily_cleanup_tokens()
            await asyncio.sleep(86400)  # 等待 24 小时
```

---

## 完整修改总结

### 需要修改的文件：2 个（必须）
1. ✅ `app/main.py` - 注册公开路由
2. ✅ `app/routes/alerts.py` - 集成令牌生成

### 可选修改：2 个
3. ⭕ 通知服务 - 在短信中包含反馈链接
4. ⭕ 定时任务 - 定期清理过期令牌

### 需要放置的新文件：3 个
1. ✅ `db/feedback_loop.sql` - 数据库脚本
2. ✅ `app/routes/public.py` - 公开 API 路由
3. ✅ `app/services_feedback.py` - 令牌管理服务

---

## 测试修改

### 测试 1：验证路由注册

```bash
# 查看 API 文档中是否有 /public 路由
curl http://localhost:8000/docs
```

### 测试 2：创建告警并获取反馈 URL

```bash
# 1. 创建事件或告警（如果有生成告警）
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "event_type": "fall",
    "elder_id": "elder_001",
    "family_id": "family_001"
  }'

# 响应中应该包含 feedback_url（如果配置了）
# {
#   "alert_id": "...",
#   "feedback_url": "/public/alerts/...?token=..."
# }

# 2. 访问反馈页面
curl "http://localhost:8000/public/alerts/ALERT_ID?token=TOKEN"

# 应该返回 HTML 页面

# 3. 提交反馈
curl -X POST "http://localhost:8000/public/alerts/ALERT_ID/feedback?token=TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"feedback_type": "true_positive"}'

# 应该返回成功消息
```

### 测试 3：检查数据库

```bash
# 检查 feedback_tokens 表
psql -U elderly_admin -d elderly_care -c "
  SELECT alert_id, is_used, expires_at 
  FROM feedback_tokens 
  ORDER BY created_at DESC 
  LIMIT 5;"

# 检查 alerts 表的新字段
psql -U elderly_admin -d elderly_care -c "
  SELECT alert_id, feedback_token, feedback_submitted, feedback_type 
  FROM alerts 
  WHERE feedback_token IS NOT NULL 
  LIMIT 5;"
```

---

## 验证清单

修改前：
- [ ] 已备份原始文件
- [ ] 已读取本指南

修改中：
- [ ] 修改 `app/main.py`
- [ ] 修改 `app/routes/alerts.py`
- [ ] 可选：修改通知服务
- [ ] 可选：修改定时任务

修改后：
- [ ] 应用成功启动（无错误）
- [ ] 日志中显示路由已注册
- [ ] 数据库脚本已执行
- [ ] API 端点可访问
- [ ] 反馈页面正常显示
- [ ] 反馈提交成功
- [ ] 数据库中有新的反馈记录

---

## 常见错误及解决方案

### 错误 1：ModuleNotFoundError: No module named 'app.routes.public'

**原因**：`public.py` 文件未放置

**解决**：确认 `app/routes/public.py` 文件已创建

### 错误 2：AttributeError: module 'app.services_feedback' has no attribute 'generate_feedback_token'

**原因**：`services_feedback.py` 文件未放置或路径错误

**解决**：确认 `app/services_feedback.py` 文件已创建

### 错误 3：404 Not Found 当访问 /public/alerts/{id}

**原因**：公开路由未注册

**解决**：检查 `main.py` 中是否添加了 `app.include_router(public.router)`

### 错误 4：ProgrammingError: relation "feedback_tokens" does not exist

**原因**：数据库脚本未执行

**解决**：执行 `psql -U elderly_admin -d elderly_care -f db/feedback_loop.sql`

### 错误 5：反馈提交返回 "Invalid token"

**原因**：令牌无效或过期

**解决**：检查令牌是否存在、是否过期、alert_id 是否正确

---

## 后续步骤

1. ✅ 执行本文档中的修改
2. ✅ 重启应用
3. ✅ 运行测试
4. ✅ 检查日志和数据库
5. ✅ 部署上线

完成！系统现在支持用户反馈闭环。
