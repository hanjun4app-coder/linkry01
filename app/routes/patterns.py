"""行为模式 API 路由"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import logging

from app.database import get_db
from app.schemas import (
    PatternResponse, PatternCreateRequest, SuccessResponse, PatternType
)
from app.services import PatternService, ElderService
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/patterns", tags=["patterns"])


def verify_api_key(x_api_key: str = Header(...)) -> str:
    """验证 API Key"""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


@router.post("", response_model=PatternResponse, summary="创建或更新行为模式")
async def create_or_update_pattern(
    request: PatternCreateRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    创建或更新老人的行为模式（基线）

    模式类型:
    - `activity`: 活动模式
    - `sleep`: 睡眠模式
    - `bathroom`: 卫生间使用模式
    - `location`: 位置模式
    - `vital_signs`: 生命体征模式

    示例请求:
    ```json
    {
        "elder_id": "elder_001",
        "family_id": "family_001",
        "pattern_type": "activity",
        "average_daily_activity_minutes": 180,
        "average_wake_time": "07:00",
        "average_sleep_time": "22:00",
        "average_bathroom_count": 4,
        "average_bathroom_duration_minutes": 15,
        "usual_active_rooms": ["living_room", "kitchen", "bedroom"],
        "days_collected": 7
    }
    ```
    """
    try:
        # 确保老人存在
        ElderService.get_or_create_elder(db, request.elder_id, request.family_id)

        # 更新或创建模式
        pattern = PatternService.update_pattern(db, request)
        logger.info(f"Pattern updated for elder {request.elder_id}: {request.pattern_type}")
        return pattern
    except Exception as e:
        logger.error(f"Error creating/updating pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{elder_id}", response_model=List[PatternResponse], summary="获取老人所有模式")
async def get_elder_patterns(
    elder_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    获取老人的所有行为模式

    返回老人的所有已记录的模式（活动、睡眠、卫生间等）
    """
    try:
        from app.models import Pattern
        patterns = db.query(Pattern).filter(Pattern.elder_id == elder_id).all()
        return [PatternResponse.from_orm(p) for p in patterns]
    except Exception as e:
        logger.error(f"Error fetching patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{elder_id}/{pattern_type}", response_model=PatternResponse, summary="获取特定类型模式")
async def get_pattern(
    elder_id: str,
    pattern_type: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    获取老人的特定类型模式

    参数:
    - `elder_id`: 老人 ID
    - `pattern_type`: 模式类型（activity/sleep/bathroom/location/vital_signs）
    """
    try:
        pattern = PatternService.get_pattern(db, elder_id, pattern_type)
        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_type} not found for elder {elder_id}")
        return pattern
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{elder_id}/calculate", response_model=dict, summary="从事件数据计算模式")
async def calculate_pattern_from_events(
    elder_id: str,
    family_id: str = Query(...),
    pattern_type: str = Query("activity", description="要计算的模式类型"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    从过去7天的事件数据自动计算用户的行为模式

    这个端点会:
    1. 查询过去7天的所有事件
    2. 分析活动频率、时间分布、房间使用等
    3. 生成新的模式数据

    注意: 这是一个同步操作，如果数据量很大可能比较慢

    参数:
    - `elder_id`: 老人 ID
    - `family_id`: 家庭 ID
    - `pattern_type`: 要计算的模式类型（默认 "activity"）
    """
    try:
        # 计算模式
        pattern_data = PatternService.calculate_pattern_from_events(db, elder_id, family_id)

        if not pattern_data:
            return {
                "elder_id": elder_id,
                "family_id": family_id,
                "pattern_type": pattern_type,
                "status": "no_data",
                "message": "没有足够的事件数据来计算模式",
                "timestamp": datetime.utcnow().isoformat()
            }

        # 保存模式
        request = PatternCreateRequest(
            elder_id=elder_id,
            family_id=family_id,
            pattern_type=pattern_type,
            **pattern_data
        )
        pattern = PatternService.update_pattern(db, request)

        logger.info(f"Pattern calculated and saved for elder {elder_id}")
        return {
            "elder_id": elder_id,
            "family_id": family_id,
            "pattern_type": pattern_type,
            "status": "calculated",
            "data": {
                "average_daily_activity_minutes": pattern.average_daily_activity_minutes,
                "average_wake_time": pattern.average_wake_time,
                "average_sleep_time": pattern.average_sleep_time,
                "usual_active_rooms": pattern.usual_active_rooms,
                "confidence": pattern.confidence,
                "days_collected": pattern.days_collected
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error calculating pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{elder_id}/reset", response_model=SuccessResponse, summary="重置模式数据")
async def reset_pattern(
    elder_id: str,
    family_id: str = Query(...),
    pattern_type: Optional[str] = Query(None, description="特定模式类型，不指定则重置所有"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    重置老人的模式数据（回到 'collecting' 状态）

    参数:
    - `elder_id`: 老人 ID
    - `family_id`: 家庭 ID
    - `pattern_type`: 要重置的模式类型（可选，不指定则重置所有）

    这个操作适用于:
    - 用户被误诊（如假期出门导致基线错误）
    - 需要重新学习用户模式
    - 用户健康状况有重大变化
    """
    try:
        from app.models import Pattern
        from datetime import datetime

        if pattern_type:
            # 重置特定模式
            pattern = db.query(Pattern).filter(
                Pattern.elder_id == elder_id,
                Pattern.pattern_type == pattern_type
            ).first()
            if pattern:
                pattern.status = "collecting"
                pattern.days_collected = 0
                pattern.baseline_date = datetime.utcnow()
                db.commit()
                logger.info(f"Pattern {pattern_type} reset for elder {elder_id}")
        else:
            # 重置所有模式
            patterns = db.query(Pattern).filter(Pattern.elder_id == elder_id).all()
            for pattern in patterns:
                pattern.status = "collecting"
                pattern.days_collected = 0
                pattern.baseline_date = datetime.utcnow()
            db.commit()
            logger.info(f"All patterns reset for elder {elder_id}")

        return SuccessResponse(
            message=f"Pattern reset successfully for elder {elder_id}",
            data={
                "elder_id": elder_id,
                "pattern_type": pattern_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Error resetting pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=dict, summary="获取系统中所有模式统计")
async def get_patterns_statistics(
    family_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    获取系统中的模式统计信息

    参数:
    - `family_id`: 家庭 ID（可选，不指定则统计全系统）

    返回:
    ```json
    {
        "total_elders": 10,
        "elders_with_patterns": 8,
        "pattern_types": {
            "activity": 8,
            "sleep": 6,
            "bathroom": 5,
            "location": 3
        },
        "status_distribution": {
            "collecting": 3,
            "active": 5,
            "needs_review": 0
        }
    }
    ```
    """
    try:
        from app.models import Pattern, Elder
        from sqlalchemy import func

        query = db.query(Pattern)
        if family_id:
            query = query.filter(Pattern.family_id == family_id)

        total_patterns = query.count()

        # 按类型统计
        by_type = db.query(Pattern.pattern_type, func.count(Pattern.id)).group_by(
            Pattern.pattern_type
        ).all()

        # 按状态统计
        by_status = db.query(Pattern.status, func.count(Pattern.id)).group_by(
            Pattern.status
        ).all()

        # 统计有模式的老人数
        elders_with_patterns = db.query(func.count(func.distinct(Pattern.elder_id))).filter(
            query.statement
        ).scalar()

        return {
            "family_id": family_id,
            "total_patterns": total_patterns,
            "elders_with_patterns": elders_with_patterns,
            "pattern_types": {pt: count for pt, count in by_type},
            "status_distribution": {status: count for status, count in by_status},
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting patterns statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
