"""告警 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from app.database import get_db
from app.schemas import (
    AlertQuery, AlertListResponse, AlertResponse, SuccessResponse, AlertType, AlertLevel
)
from app.services import AlertService
from app.config import settings
# ✅ 修复 P0: 使用 JWT 认证替代简单 API Key
from app.security import verify_token, TokenPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse, summary="查询告警")
async def query_alerts(
    elder_id: Optional[str] = Query(None),
    family_id: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    alert_level: Optional[str] = Query(None),
    is_acknowledged: Optional[bool] = Query(None),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    查询告警列表

    参数:
    - `elder_id`: 老人 ID（可选）
    - `family_id`: 家庭 ID（可选）
    - `alert_type`: 告警类型（可选）
    - `alert_level`: 告警级别（info/warning/critical）（可选）
    - `is_acknowledged`: 是否已确认（可选）
    - `days`: 查询天数（1-90，默认 7）
    - `limit`: 结果数量限制（默认 100）
    - `offset`: 分页偏移（默认 0）

    示例:
    ```
    GET /api/alerts?family_id=family_001&alert_level=critical&days=7&limit=50
    ```
    """
    try:
        # ✅ 验证 token 权限：如果指定了 family_id，必须与 token 匹配
        if family_id and family_id != token.family_id:
            logger.warning(f"Token family_id {token.family_id} does not match query family_id {family_id}")
            raise HTTPException(
                status_code=403,
                detail="Token not authorized for this family"
            )

        # 如果没有指定 family_id，使用 token 中的
        query_family_id = family_id or token.family_id

        query = AlertQuery(
            elder_id=elder_id,
            family_id=query_family_id,
            alert_type=AlertType(alert_type) if alert_type else None,
            alert_level=AlertLevel(alert_level) if alert_level else None,
            is_acknowledged=is_acknowledged,
            days=days,
            limit=limit,
            offset=offset
        )
        result = AlertService.get_alerts(db, query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Error querying alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unacknowledged", response_model=list, summary="获取未确认告警")
async def get_unacknowledged_alerts(
    elder_id: Optional[str] = Query(None),
    family_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    获取所有未确认的告警

    参数:
    - `elder_id`: 老人 ID（可选）
    - `family_id`: 家庭 ID（可选）
    """
    try:
        alerts = AlertService.get_unacknowledged_alerts(db, elder_id, family_id)
        return alerts
    except Exception as e:
        logger.error(f"Error fetching unacknowledged alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse, summary="确认告警")
async def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query(...),
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    确认一条告警

    参数:
    - `alert_id`: 告警 ID
    - `acknowledged_by`: 确认人（用户 ID）

    示例:
    ```
    POST /api/alerts/123/acknowledge?acknowledged_by=user_001
    ```
    """
    try:
        alert = AlertService.acknowledge_alert(db, alert_id, acknowledged_by)
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return alert
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{family_id}/statistics", response_model=dict, summary="获取告警统计")
async def get_alert_statistics(
    family_id: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    获取家庭的告警统计

    参数:
    - `family_id`: 家庭 ID
    - `days`: 统计时间范围（默认 7 天）

    返回:
    ```json
    {
        "total_alerts": 42,
        "unacknowledged": 5,
        "acknowledged": 37,
        "by_type": {
            "inactivity": 15,
            "bathroom_timeout": 10,
            ...
        },
        "by_level": {
            "critical": 5,
            "warning": 20,
            "info": 17
        }
    }
    ```
    """
    try:
        stats = AlertService.get_alert_statistics(db, family_id, days)
        return {
            "family_id": family_id,
            "time_range_days": days,
            **stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/elder/{elder_id}/unacknowledged-count", response_model=dict, summary="获取老人未确认告警数")
async def get_elder_unacknowledged_count(
    elder_id: str,
    family_id: str,
    db: Session = Depends(get_db),
    token: TokenPayload = Depends(verify_token)  # ✅ 使用 JWT
):
    """
    快速获取老人的未确认告警数量（用于面板展示）
    """
    try:
        alerts = AlertService.get_unacknowledged_alerts(db, elder_id, family_id)
        critical = sum(1 for a in alerts if a.alert_level == "critical")
        warning = sum(1 for a in alerts if a.alert_level == "warning")
        info = sum(1 for a in alerts if a.alert_level == "info")

        return {
            "elder_id": elder_id,
            "family_id": family_id,
            "total_unacknowledged": len(alerts),
            "critical": critical,
            "warning": warning,
            "info": info,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting unacknowledged count: {e}")
        raise HTTPException(status_code=500, detail=str(e))
