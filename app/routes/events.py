"""事件 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import uuid

from app.database import get_db
from app.schemas import (
    EventCreate, EventResponse, BulkEventCreate, SuccessResponse, ErrorResponse
)
from app.services import EventService, ElderService
from app.rules import RuleEngine
from app.config import settings
from app.models import Alert
# ✅ 修复 P0: 使用 JWT 认证替代简单 API Key
from app.security import verify_token, TokenPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


def save_alerts_to_db(db: Session, rule_alerts: List, elder_id: str, family_id: str) -> List[Alert]:
    """
    保存规则生成的告警到数据库（✅ 支持并发，防止竞态条件）

    参数:
    - db: 数据库会话
    - rule_alerts: RuleEngine 生成的告警列表
    - elder_id: 老人 ID
    - family_id: 家庭 ID

    返回:
    - 保存后的 Alert ORM 对象列表
    """
    from sqlalchemy import and_

    saved_alerts = []

    try:
        for alert in rule_alerts:
            try:
                # 安全地获取告警类型和级别
                alert_type_str = alert.alert_type.value if hasattr(alert.alert_type, 'value') else str(alert.alert_type)
                alert_level_str = alert.alert_level.value if hasattr(alert.alert_level, 'value') else str(alert.alert_level)
                message_str = str(alert.message) if alert.message else "Alert triggered"
                details_dict = alert.details if isinstance(alert.details, dict) else (dict(alert.details) if alert.details else {})

                logger.info(f"Processing alert: type={alert_type_str}, level={alert_level_str}, message={message_str}")

                # ✅ 修复 P0: 使用行级锁防止并发竞态条件
                existing_alert = db.query(Alert).filter(
                    and_(
                        Alert.elder_id == elder_id,
                        Alert.family_id == family_id,
                        Alert.alert_type == alert_type_str,
                        Alert.is_acknowledged == False
                    )
                ).with_for_update().first()  # ✅ 添加行级锁

                if not existing_alert:
                    # 创建新的 Alert ORM 对象
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
                    db.flush()  # 获取自动分配的 id
                    logger.info(f"Created new alert: id={db_alert.id}")
                    saved_alerts.append(db_alert)
                else:
                    logger.info(f"Alert already exists: {alert_type_str}")
                    saved_alerts.append(existing_alert)
            except Exception as e:
                logger.error(f"Error processing individual alert: {e}", exc_info=True)
                continue

        # 提交事务
        db.commit()
        logger.info(f"Committed {len(saved_alerts)} alerts to database")

        # 刷新所有对象以获取 id、created_at、updated_at
        for alert in saved_alerts:
            db.refresh(alert)
            logger.info(f"Refreshed alert: id={alert.id}, created_at={alert.created_at}")

        return saved_alerts

    except Exception as e:
        logger.error(f"Error in save_alerts_to_db: {e}", exc_info=True)
        db.rollback()
        return []


@router.post("", response_model=EventResponse, summary="创建单个事件")
async def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT 认证替代 API Key
):
    """
    创建单个事件

    事件格式:
    ```json
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
    ```
    """
    try:
        # ✅ 验证 token 中的 family_id 与事件的 family_id 匹配
        if event.family_id != token.family_id:
            logger.warning(f"Token family_id {token.family_id} does not match event family_id {event.family_id}")
            raise HTTPException(
                status_code=403,
                detail="Token not authorized for this family"
            )

        # 确保老人存在
        ElderService.get_or_create_elder(db, event.elder_id, event.family_id)

        # 创建事件
        response = EventService.create_event(db, event)

        # 检查规则并保存生成的告警
        rule_engine = RuleEngine(db)
        rule_alerts = rule_engine.check_all_rules(event.elder_id, event.family_id)

        if rule_alerts:
            saved_alerts = save_alerts_to_db(db, rule_alerts, event.elder_id, event.family_id)
            logger.warning(f"Alerts generated and saved for elder {event.elder_id}: {len(saved_alerts)}")

        return response
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=SuccessResponse, summary="批量创建事件")
async def create_bulk_events(
    bulk_events: BulkEventCreate,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    批量创建事件（推荐用于高频数据）

    请求体:
    ```json
    {
        "batch_id": "batch_20240115_001",
        "events": [
            {
                "elder_id": "elder_001",
                "family_id": "family_001",
                ...
            },
            ...
        ]
    }
    ```
    """
    try:
        if not bulk_events.events:
            raise HTTPException(status_code=400, detail="Events list cannot be empty")

        # 创建所有事件
        created = EventService.create_bulk_events(db, bulk_events.events)

        # 为每个老人检查规则并保存告警
        unique_elders = set((e.elder_id, e.family_id) for e in bulk_events.events)
        rule_engine = RuleEngine(db)

        for elder_id, family_id in unique_elders:
            rule_alerts = rule_engine.check_all_rules(elder_id, family_id)
            if rule_alerts:
                saved_alerts = save_alerts_to_db(db, rule_alerts, elder_id, family_id)
                logger.warning(f"Alerts generated and saved for elder {elder_id}: {len(saved_alerts)}")

        return SuccessResponse(
            message=f"Successfully created {len(created)} events",
            data={
                "batch_id": bulk_events.batch_id,
                "count": len(created),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error creating bulk events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{elder_id}", response_model=List[EventResponse], summary="获取老人最近事件")
async def get_recent_events(
    elder_id: str,
    family_id: str,
    hours: int = 24,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    获取老人过去 N 小时的事件

    参数:
    - `elder_id`: 老人 ID
    - `family_id`: 家庭 ID
    - `hours`: 查询时间范围（默认 24 小时）
    """
    try:
        events = EventService.get_recent_events(db, elder_id, family_id, hours)
        return events
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{elder_id}/by_room", response_model=List[EventResponse], summary="按房间获取事件")
async def get_events_by_room(
    elder_id: str,
    family_id: str,
    room: str,
    hours: int = 24,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    按房间获取老人的事件

    参数:
    - `elder_id`: 老人 ID
    - `family_id`: 家庭 ID
    - `room`: 房间名称（如 "bedroom", "kitchen", "bathroom"）
    - `hours`: 查询时间范围（默认 24 小时）
    """
    try:
        events = EventService.get_events_by_room(db, elder_id, family_id, room, hours)
        return events
    except Exception as e:
        logger.error(f"Error fetching room events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{elder_id}/summary", response_model=dict, summary="获取老人事件摘要")
async def get_event_summary(
    elder_id: str,
    family_id: str,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    获取老人的事件摘要（今日活动统计）
    """
    try:
        rule_engine = RuleEngine(db)
        summary = rule_engine.get_today_activity_summary(elder_id, family_id)
        return {
            "elder_id": elder_id,
            "family_id": family_id,
            **summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting event summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{elder_id}/check-rules", response_model=dict, summary="检查老人所有规则")
async def check_elder_rules(
    elder_id: str,
    family_id: str,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    手动检查老人是否触发任何规则

    返回生成的告警列表（已保存到数据库）
    """
    try:
        rule_engine = RuleEngine(db)
        rule_alerts = rule_engine.check_all_rules(elder_id, family_id)

        # 保存告警到数据库
        saved_alerts = save_alerts_to_db(db, rule_alerts, elder_id, family_id)

        logger.info(f"check-rules: Found {len(rule_alerts)} alerts for elder {elder_id}, saved {len(saved_alerts)}")

        return {
            "elder_id": elder_id,
            "family_id": family_id,
            "alert_count": len(saved_alerts),
            "alerts": [
                {
                    "id": alert.id,
                    "alert_id": alert.alert_id,
                    "alert_type": alert.alert_type,
                    "alert_level": alert.alert_level,
                    "message": alert.message,
                    "details": alert.details,
                    "is_acknowledged": alert.is_acknowledged,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                    "updated_at": alert.updated_at.isoformat() if alert.updated_at else None
                }
                for alert in saved_alerts
            ],
            "checked_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error checking rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=SuccessResponse, summary="检查 API 健康状态")
async def health_check():
    """
    检查 API 是否正常运行
    """
    return SuccessResponse(
        message="API is healthy",
        data={"timestamp": datetime.utcnow().isoformat()}
    )
