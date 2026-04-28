"""业务逻辑服务层"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import logging
from decimal import Decimal

from app.models import Event, Pattern, Alert, Elder, Family, Device
from app.schemas import (
    StandardEvent, EventCreate, EventResponse, AlertResponse, PatternResponse,
    PatternCreateRequest, AlertQuery, AlertListResponse
)
from app.rules import RuleEngine

logger = logging.getLogger(__name__)


class EventService:
    """事件服务"""

    @staticmethod
    def create_event(db: Session, event: EventCreate) -> EventResponse:
        """创建事件"""
        db_event = Event(
            event_id=str(__import__('uuid').uuid4()),
            family_id=event.family_id,
            elder_id=event.elder_id,
            device_id=event.device_id,
            event_type=event.event_type.value,
            event_value=event.event_value,
            room=event.room,
            location_name=event.location_name,
            confidence=event.confidence,
            metadata=event.metadata,
            timestamp=event.timestamp
        )
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return EventResponse.from_orm(db_event)

    @staticmethod
    def create_bulk_events(db: Session, events: List[EventCreate]) -> List[EventResponse]:
        """批量创建事件"""
        db_events = []
        for event in events:
            db_event = Event(
                event_id=str(__import__('uuid').uuid4()),
                family_id=event.family_id,
                elder_id=event.elder_id,
                device_id=event.device_id,
                event_type=event.event_type.value,
                event_value=event.event_value,
                room=event.room,
                location_name=event.location_name,
                confidence=event.confidence,
                metadata=event.metadata,
                timestamp=event.timestamp
            )
            db_events.append(db_event)

        db.add_all(db_events)
        db.commit()

        for db_event in db_events:
            db.refresh(db_event)

        return [EventResponse.from_orm(e) for e in db_events]

    @staticmethod
    def get_recent_events(db: Session, elder_id: str, family_id: str, hours: int = 24) -> List[EventResponse]:
        """获取最近的事件"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        events = db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= cutoff_time
            )
        ).order_by(desc(Event.timestamp)).all()
        return [EventResponse.from_orm(e) for e in events]

    @staticmethod
    def get_events_by_room(db: Session, elder_id: str, family_id: str, room: str, hours: int = 24) -> List[EventResponse]:
        """按房间获取事件"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        events = db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.room == room,
                Event.timestamp >= cutoff_time
            )
        ).order_by(desc(Event.timestamp)).all()
        return [EventResponse.from_orm(e) for e in events]


class AlertService:
    """告警服务"""

    @staticmethod
    def create_alert(db: Session, alert: AlertResponse) -> AlertResponse:
        """创建告警"""
        db_alert = Alert(
            alert_id=str(__import__('uuid').uuid4()),
            family_id=alert.family_id,
            elder_id=alert.elder_id,
            alert_type=alert.alert_type.value,
            alert_level=alert.alert_level.value,
            message=alert.message,
            details=alert.details
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        return AlertResponse.from_orm(db_alert)

    @staticmethod
    def get_unacknowledged_alerts(db: Session, elder_id: Optional[str] = None,
                                  family_id: Optional[str] = None) -> List[AlertResponse]:
        """获取未确认的告警"""
        query = db.query(Alert).filter(Alert.is_acknowledged == False)

        if elder_id:
            query = query.filter(Alert.elder_id == elder_id)
        if family_id:
            query = query.filter(Alert.family_id == family_id)

        alerts = query.order_by(desc(Alert.created_at)).all()
        return [AlertResponse.from_orm(a) for a in alerts]

    @staticmethod
    def get_alerts(db: Session, query_param: AlertQuery) -> AlertListResponse:
        """查询告警（支持多种过滤条件）"""
        cutoff_time = datetime.utcnow() - timedelta(days=query_param.days)

        query = db.query(Alert).filter(Alert.created_at >= cutoff_time)

        if query_param.elder_id:
            query = query.filter(Alert.elder_id == query_param.elder_id)
        if query_param.family_id:
            query = query.filter(Alert.family_id == query_param.family_id)
        if query_param.alert_type:
            query = query.filter(Alert.alert_type == query_param.alert_type.value)
        if query_param.alert_level:
            query = query.filter(Alert.alert_level == query_param.alert_level.value)
        if query_param.is_acknowledged is not None:
            query = query.filter(Alert.is_acknowledged == query_param.is_acknowledged)

        total = query.count()
        alerts = query.order_by(desc(Alert.created_at)).offset(query_param.offset).limit(query_param.limit).all()

        return AlertListResponse(
            total=total,
            alerts=[AlertResponse.from_orm(a) for a in alerts],
            has_more=(query_param.offset + query_param.limit) < total
        )

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: int, acknowledged_by: str) -> AlertResponse:
        """确认告警"""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        db.commit()
        db.refresh(alert)
        return AlertResponse.from_orm(alert)

    @staticmethod
    def get_alert_statistics(db: Session, family_id: str, days: int = 7) -> Dict[str, Any]:
        """获取告警统计"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        total_alerts = db.query(Alert).filter(
            and_(Alert.family_id == family_id, Alert.created_at >= cutoff_time)
        ).count()

        unacknowledged = db.query(Alert).filter(
            and_(
                Alert.family_id == family_id,
                Alert.is_acknowledged == False,
                Alert.created_at >= cutoff_time
            )
        ).count()

        by_type = db.query(Alert.alert_type, func.count(Alert.id)).filter(
            and_(Alert.family_id == family_id, Alert.created_at >= cutoff_time)
        ).group_by(Alert.alert_type).all()

        by_level = db.query(Alert.alert_level, func.count(Alert.id)).filter(
            and_(Alert.family_id == family_id, Alert.created_at >= cutoff_time)
        ).group_by(Alert.alert_level).all()

        return {
            "total_alerts": total_alerts,
            "unacknowledged": unacknowledged,
            "acknowledged": total_alerts - unacknowledged,
            "by_type": {alert_type: count for alert_type, count in by_type},
            "by_level": {alert_level: count for alert_level, count in by_level},
        }


class PatternService:
    """模式（基线）服务"""

    @staticmethod
    def get_or_create_pattern(db: Session, elder_id: str, family_id: str, pattern_type: str) -> Pattern:
        """获取或创建模式"""
        pattern = db.query(Pattern).filter(
            and_(
                Pattern.elder_id == elder_id,
                Pattern.pattern_type == pattern_type
            )
        ).first()

        if not pattern:
            pattern = Pattern(
                elder_id=elder_id,
                family_id=family_id,
                pattern_type=pattern_type,
                baseline_date=datetime.utcnow(),
                status="collecting"
            )
            db.add(pattern)
            db.commit()
            db.refresh(pattern)

        return pattern

    @staticmethod
    def update_pattern(db: Session, request: PatternCreateRequest) -> PatternResponse:
        """更新模式数据"""
        pattern = PatternService.get_or_create_pattern(
            db, request.elder_id, request.family_id, request.pattern_type.value
        )

        # 更新数据
        if request.average_daily_activity_minutes is not None:
            pattern.average_daily_activity_minutes = request.average_daily_activity_minutes
        if request.average_wake_time:
            pattern.average_wake_time = request.average_wake_time
        if request.average_sleep_time:
            pattern.average_sleep_time = request.average_sleep_time
        if request.average_bathroom_count is not None:
            pattern.average_bathroom_count = request.average_bathroom_count
        if request.average_bathroom_duration_minutes is not None:
            pattern.average_bathroom_duration_minutes = request.average_bathroom_duration_minutes
        if request.usual_active_rooms:
            pattern.usual_active_rooms = request.usual_active_rooms

        pattern.days_collected = request.days_collected
        if request.days_collected >= 7:
            pattern.status = "active"

        db.commit()
        db.refresh(pattern)
        return PatternResponse.from_orm(pattern)

    @staticmethod
    def calculate_pattern_from_events(db: Session, elder_id: str, family_id: str) -> Dict[str, Any]:
        """从事件数据计算模式"""
        # 获取过去7天的事件
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        events = db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= cutoff_time,
                Event.event_type.in_(["motion", "presence", "activity"])
            )
        ).all()

        if not events:
            return {}

        # 计算平均每日活动分钟数
        daily_activities = {}
        for event in events:
            date = event.timestamp.date()
            if date not in daily_activities:
                daily_activities[date] = 0
            daily_activities[date] += 1

        avg_daily_activity = int(sum(daily_activities.values()) / len(daily_activities)) if daily_activities else 0

        # 统计房间使用
        room_counts = {}
        for event in events:
            room = event.room or "unknown"
            room_counts[room] = room_counts.get(room, 0) + 1

        usual_rooms = sorted(room_counts.keys(), key=lambda x: room_counts[x], reverse=True)[:3]

        # 计算起床时间（第一次活动）
        daily_first_activities = {}
        for event in sorted(events, key=lambda x: x.timestamp):
            date = event.timestamp.date()
            if date not in daily_first_activities:
                daily_first_activities[date] = event.timestamp.hour

        if daily_first_activities:
            avg_wake_hour = int(sum(daily_first_activities.values()) / len(daily_first_activities))
            avg_wake_time = f"{avg_wake_hour:02d}:00"
        else:
            avg_wake_time = "07:00"

        return {
            "average_daily_activity_minutes": avg_daily_activity,
            "average_wake_time": avg_wake_time,
            "average_bathroom_count": None,  # 需要更复杂的计算
            "usual_active_rooms": usual_rooms,
            "days_collected": 7,
            "confidence": 0.8
        }

    @staticmethod
    def get_pattern(db: Session, elder_id: str, pattern_type: str) -> Optional[PatternResponse]:
        """获取模式"""
        pattern = db.query(Pattern).filter(
            and_(
                Pattern.elder_id == elder_id,
                Pattern.pattern_type == pattern_type
            )
        ).first()
        return PatternResponse.from_orm(pattern) if pattern else None


class ElderService:
    """老人服务"""

    @staticmethod
    def get_or_create_elder(db: Session, elder_id: str, family_id: str, name: str = None) -> Elder:
        """获取或创建老人"""
        elder = db.query(Elder).filter(Elder.elder_id == elder_id).first()

        if not elder:
            elder = Elder(
                elder_id=elder_id,
                family_id=family_id,
                name=name or elder_id,
                baseline_status="collecting"
            )
            db.add(elder)
            db.commit()
            db.refresh(elder)

        return elder

    @staticmethod
    def get_elder_status(db: Session, elder_id: str) -> Dict[str, Any]:
        """获取老人的综合状态"""
        elder = db.query(Elder).filter(Elder.elder_id == elder_id).first()
        if not elder:
            return {}

        rule_engine = RuleEngine(db)

        # 检查所有规则
        alerts = rule_engine.check_all_rules(elder_id, elder.family_id)

        # 获取今天的活动摘要
        activity_summary = rule_engine.get_today_activity_summary(elder_id, elder.family_id)

        # 获取基线状态
        baseline_status = rule_engine.get_baseline_status(elder_id)

        return {
            "elder_id": elder_id,
            "name": elder.name,
            "family_id": elder.family_id,
            "potential_alerts": [
                {
                    "alert_type": alert.alert_type.value,
                    "alert_level": alert.alert_level.value,
                    "message": alert.message,
                    "details": alert.details
                }
                for alert in alerts
            ],
            "activity_summary": activity_summary,
            "baseline_status": baseline_status,
            "timestamp": datetime.utcnow().isoformat()
        }
