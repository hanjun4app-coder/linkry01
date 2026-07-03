"""FastAPI 主应用"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import uuid
import hashlib
from hmac import compare_digest
import json

from app.config import settings
from app.database import init_db, verify_connection
from app.routes import events, alerts, patterns

# ✅ 修复 P0: 配置日志过滤器（PII 保护）
class PIIFilter(logging.Filter):
    """过滤日志中的敏感信息"""
    def filter(self, record):
        record.msg = self._sanitize(str(record.msg))
        if record.exc_text:
            record.exc_text = self._sanitize(record.exc_text)
        return True

    @staticmethod
    def _sanitize(msg):
        import re
        # 移除常见敏感信息
        msg = re.sub(r'\b(?:\d{1,5}[._-]?){3}\d{1,5}\b', 'PHONE_MASKED', msg)  # 电话
        msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', 'IP_MASKED', msg)  # IP
        msg = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'EMAIL_MASKED', msg)  # 邮箱
        return msg

# 配置日志
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.addFilter(PIIFilter())


# 应用启动和关闭事件
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的事件处理"""
    # 启动事件
    logger.info("Starting Elderly Care Cloud API...")

    # 初始化数据库
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # 验证数据库连接
    if not verify_connection():
        logger.error("Failed to connect to database")
        raise RuntimeError("Database connection failed")

    logger.info("✅ Elderly Care Cloud API started successfully")

    yield

    # 关闭事件
    logger.info("Shutting down Elderly Care Cloud API...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="养老AI系统云端 API - Aqara FP2 / Home Assistant → Cloud API → Rule Engine → Alert",
    lifespan=lifespan
)

# ✅ 修复 P0: CORS 配置（已在 config.py 中改为白名单）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,  # ✅ 不再允许 "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # ✅ 限制HTTP方法
    allow_headers=["Content-Type", "Authorization"],  # ✅ 限制请求头
)


# 包含路由
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(patterns.router)


# ==================== 基础端点 ====================

@app.get("/", summary="API 信息")
async def root():
    """获取 API 基本信息"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": "养老AI系统云端 API",
        "endpoints": {
            "events": "/api/events",
            "alerts": "/api/alerts",
            "patterns": "/api/patterns",
            "health": "/health",
            "docs": "/docs"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """健康检查端点（用于容器编排）"""
    return {"status": "ok"}


@app.get("/version", summary="获取版本信息")
async def get_version():
    """获取 API 版本信息"""
    return {
        "version": settings.API_VERSION,
        "api_title": settings.API_TITLE,
        "environment": "production" if not settings.DEBUG else "development",
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== Home Assistant 特殊端点 ====================

@app.post("/webhook/home_assistant", summary="Home Assistant Webhook")
async def home_assistant_webhook(request: Request):
    """
    ✅ 修复 P0: Home Assistant Webhook 接收端点 (添加签名验证)

    用于 Home Assistant 直接推送事件到本 API

    在 Home Assistant 中的配置示例:
    ```yaml
    automation:
      - alias: "Send events to elderly care API"
        trigger:
          platform: event
          event_type: any_event
        action:
          - service: rest_command.send_to_elderly_care_signed
            data_template:
              elder_id: "{{ states('input_text.elder_id') }}"
              event_type: "{{ trigger.event.event_type }}"

    rest_command:
      send_to_elderly_care_signed:
        url: "http://elderly-care-api:8000/webhook/home_assistant"
        method: POST
        payload: '{"elder_id": "{{ elder_id }}", "event_type": "{{ event_type }}"}'
        headers:
          X-HA-Webhook-Signature: "sha256=<computed_signature>"
    ```
    """
    # ✅ 验证 Webhook 签名
    signature = request.headers.get("X-HA-Webhook-Signature", "")

    if not signature:
        logger.warning(f"Missing webhook signature from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Missing signature")

    # 读取请求体
    body = await request.body()

    # ✅ 计算签名 (SHA256)
    expected_signature = hashlib.sha256(
        f"{settings.HOME_ASSISTANT_WEBHOOK_SECRET}{body.decode()}".encode()
    ).hexdigest()

    # ✅ 安全对比签名（防止时间攻击）
    provided_signature = signature.split("=")[-1] if "=" in signature else signature

    if not compare_digest(expected_signature, provided_signature):
        logger.warning(f"Invalid webhook signature from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # ✅ 签名验证通过，处理数据
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("Received valid Home Assistant webhook")

    # 这里可以添加将 HA 事件转换为标准事件的逻辑
    from app.database import SessionLocal
    from app.services import EventService
    from app.schemas import EventCreate, EventType, DeviceType

    db = SessionLocal()
    try:
        # 解析 Home Assistant 数据
        # 示例: {"entity_id": "binary_sensor.bedroom_motion", "state": "on", ...}
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

        return {
            "status": "success",
            "event_id": response.id,
            "message": "Event received and processed",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Home Assistant webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ==================== 错误处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    logger.warning(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "error_message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """✅ 修复 P0: 通用异常处理（不泄露堆栈跟踪）"""
    error_id = str(uuid.uuid4())
    # ❌ 不要记录完整异常堆栈
    logger.error(f"Internal error (ID: {error_id}): {type(exc).__name__}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": "Internal server error",
            "error_id": error_id,  # 用户可以用此ID向管理员报告
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        reload=settings.DEBUG
    )
