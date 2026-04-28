"""规则引擎 - 异常检测和告警生成"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
# ✅ 修复 P1: 添加 case, func 用于数据库级计算
from sqlalchemy import and_, desc, func, case
import logging

from app.schemas import AlertCreate as AlertSchema, AlertType, AlertLevel, EventType
from app.models import Event, Pattern, Alert, Elder
from app.config import settings

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎 - 检测异常并生成告警"""

    def __init__(self, db: Session):
        self.db = db

    def check_all_rules(self, elder_id: str, family_id: str) -> List[AlertSchema]:
        """检查所有规则并返回告警列表"""
        alerts = []

        # 规则1: 长时间无活动
        inactivity_alert = self.check_inactivity(elder_id, family_id)
        if inactivity_alert:
            alerts.append(inactivity_alert)

        # 规则2: 卫生间停留过久
        bathroom_alert = self.check_bathroom_timeout(elder_id, family_id)
        if bathroom_alert:
            alerts.append(bathroom_alert)

        # 规则3: 起床时间异常
        wake_time_alert = self.check_abnormal_wake_time(elder_id, family_id)
        if wake_time_alert:
            alerts.append(wake_time_alert)

        # 规则4: 夜间频繁活动
        night_activity_alert = self.check_night_activity(elder_id, family_id)
        if night_activity_alert:
            alerts.append(night_activity_alert)

        # 规则5: 房间活动模式偏离
        room_pattern_alert = self.check_room_pattern_change(elder_id, family_id)
        if room_pattern_alert:
            alerts.append(room_pattern_alert)

        return alerts

    # ==================== 规则1: 长时间无活动 ====================
    def check_inactivity(self, elder_id: str, family_id: str) -> Optional[AlertSchema]:
        """
        检测长时间无活动
        规则: 在过去 INACTIVITY_THRESHOLD_MINUTES 分钟内没有任何活动事件
        """
        threshold = settings.INACTIVITY_THRESHOLD_MINUTES
        cutoff_time = datetime.utcnow() - timedelta(minutes=threshold)

        # 查询过去 threshold 分钟内的活动事件
        recent_activity = self.db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= cutoff_time,
                Event.event_type.in_([EventType.MOTION, EventType.PRESENCE, EventType.ACTIVITY])
            )
        ).order_by(desc(Event.timestamp)).first()

        if not recent_activity:
            logger.warning(f"Elder {elder_id} has no activity for {threshold} minutes")
            return AlertSchema(
                elder_id=elder_id,
                family_id=family_id,
                alert_type=AlertType.INACTIVITY,
                alert_level=AlertLevel.CRITICAL,
                message=f"长时间无活动：过去 {threshold} 分钟内未检测到活动",
                details={
                    "threshold_minutes": threshold,
                    "last_activity": None,
                    "detected_at": datetime.utcnow().isoformat()
                }
            )

        # 如果最后一次活动距今超过阈值
        last_activity_time = recent_activity.timestamp
        minutes_since_activity = (datetime.utcnow() - last_activity_time).total_seconds() / 60

        if minutes_since_activity > threshold:
            logger.warning(f"Elder {elder_id} inactivity: {minutes_since_activity:.0f} minutes")
            return AlertSchema(
                elder_id=elder_id,
                family_id=family_id,
                alert_type=AlertType.INACTIVITY,
                alert_level=AlertLevel.CRITICAL,
                message=f"长时间无活动：{minutes_since_activity:.0f} 分钟无活动记录",
                details={
                    "threshold_minutes": threshold,
                    "minutes_without_activity": minutes_since_activity,
                    "last_activity_time": last_activity_time.isoformat(),
                    "last_activity_location": recent_activity.room,
                    "detected_at": datetime.utcnow().isoformat()
                }
            )

        return None

    # ==================== 规则2: 卫生间停留过久 ====================
    def check_bathroom_timeout(self, elder_id: str, family_id: str) -> Optional[AlertSchema]:
        """
        检测卫生间停留过久
        规则: 在卫生间停留超过 BATHROOM_TIMEOUT_MINUTES 分钟
        """
        timeout = settings.BATHROOM_TIMEOUT_MINUTES

        # 查询最后进入卫生间的事件
        bathroom_entry = self.db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.room == "bathroom",
                Event.event_type.in_([EventType.PRESENCE, EventType.MOTION])
            )
        ).order_by(desc(Event.timestamp)).first()

        if not bathroom_entry:
            return None

        # 检查自进入卫生间后是否有离开信号
        bathroom_entry_time = bathroom_entry.timestamp
        time_in_bathroom = (datetime.utcnow() - bathroom_entry_time).total_seconds() / 60

        # 查询进入后是否有其他房间的活动（表示离开）
        exit_event = self.db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp > bathroom_entry_time,
                Event.room != "bathroom"
            )
        ).order_by(desc(Event.timestamp)).first()

        if not exit_event:
            # 仍在卫生间
            if time_in_bathroom > timeout:
                logger.warning(f"Elder {elder_id} bathroom timeout: {time_in_bathroom:.0f} minutes")
                return AlertSchema(
                    elder_id=elder_id,
                    family_id=family_id,
                    alert_type=AlertType.BATHROOM_TIMEOUT,
                    alert_level=AlertLevel.WARNING,
                    message=f"卫生间停留过久：已停留 {time_in_bathroom:.0f} 分钟",
                    details={
                        "timeout_threshold_minutes": timeout,
                        "time_in_bathroom_minutes": time_in_bathroom,
                        "entry_time": bathroom_entry_time.isoformat(),
                        "detected_at": datetime.utcnow().isoformat()
                    }
                )

        return None

    # ==================== 规则3: 起床时间异常 ====================
    def check_abnormal_wake_time(self, elder_id: str, family_id: str) -> Optional[AlertSchema]:
        """
        检测起床时间异常
        规则: 与基线相比，起床时间相差超过 WAKE_TIME_VARIANCE_HOURS 小时
        """
        variance = settings.WAKE_TIME_VARIANCE_HOURS

        # 获取老人的基线模式
        pattern = self.db.query(Pattern).filter(
            and_(
                Pattern.elder_id == elder_id,
                Pattern.pattern_type == "sleep"
            )
        ).first()

        if not pattern or not pattern.average_wake_time:
            return None  # 没有基线数据

        baseline_wake_time = pattern.average_wake_time  # HH:MM 格式

        # 获取今天的第一次活动
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_first_activity = self.db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= today_start,
                Event.event_type.in_([EventType.MOTION, EventType.PRESENCE])
            )
        ).order_by(Event.timestamp).first()

        if not today_first_activity:
            return None  # 今天还没有活动

        actual_wake_time = today_first_activity.timestamp

        # 比较时间
        baseline_hour, baseline_minute = map(int, baseline_wake_time.split(':'))
        actual_hour = actual_wake_time.hour
        actual_minute = actual_wake_time.minute

        baseline_minutes = baseline_hour * 60 + baseline_minute
        actual_minutes = actual_hour * 60 + actual_minute

        time_diff_minutes = abs(actual_minutes - baseline_minutes)
        time_diff_hours = time_diff_minutes / 60

        if time_diff_hours > variance:
            logger.warning(f"Elder {elder_id} abnormal wake time: {actual_hour:02d}:{actual_minute:02d} vs baseline {baseline_wake_time}")
            return AlertSchema(
                elder_id=elder_id,
                family_id=family_id,
                alert_type=AlertType.ABNORMAL_WAKE,
                alert_level=AlertLevel.WARNING,
                message=f"起床时间异常：{actual_hour:02d}:{actual_minute:02d} vs 基线 {baseline_wake_time}（偏差 {time_diff_hours:.1f} 小时）",
                details={
                    "variance_threshold_hours": variance,
                    "baseline_wake_time": baseline_wake_time,
                    "actual_wake_time": f"{actual_hour:02d}:{actual_minute:02d}",
                    "variance_hours": time_diff_hours,
                    "detected_at": datetime.utcnow().isoformat()
                }
            )

        return None

    # ==================== 规则4: 夜间频繁活动 ====================
    def check_night_activity(self, elder_id: str, family_id: str) -> Optional[AlertSchema]:
        """
        检测夜间频繁活动
        规则: 夜间（22:00-06:00）活动次数超过阈值
        """
        threshold = settings.NIGHT_ACTIVITY_THRESHOLD

        # 定义夜间时间段
        night_start_hour = 22
        night_end_hour = 6

        # 查询过去一晚的活动（昨晚22:00到今晨06:00）
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        # 夜间时间范围：昨晚22:00 到 今晨06:00
        night_start = datetime.combine(yesterday, datetime.min.time()).replace(hour=night_start_hour)
        night_end = datetime.combine(today, datetime.min.time()).replace(hour=night_end_hour)

        night_activities = self.db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= night_start,
                Event.timestamp <= night_end,
                Event.event_type.in_([EventType.MOTION, EventType.PRESENCE, EventType.ACTIVITY])
            )
        ).count()

        if night_activities > threshold:
            logger.warning(f"Elder {elder_id} night activity: {night_activities} events vs threshold {threshold}")
            return AlertSchema(
                elder_id=elder_id,
                family_id=family_id,
                alert_type=AlertType.NIGHT_ACTIVITY,
                alert_level=AlertLevel.WARNING,
                message=f"夜间频繁活动：检测到 {night_activities} 次活动（阈值 {threshold}）",
                details={
                    "activity_threshold": threshold,
                    "night_activity_count": night_activities,
                    "night_period": f"{night_start_hour:02d}:00 - {night_end_hour:02d}:00",
                    "detected_at": datetime.utcnow().isoformat()
                }
            )

        return None

    # ==================== 规则5: 房间活动模式偏离 ====================
    def check_room_pattern_change(self, elder_id: str, family_id: str) -> Optional[AlertSchema]:
        """
        ✅ 修复 P1: 检测房间活动模式是否偏离基线（已优化为数据库级计算，无 N+1 问题）
        规则: 在不常去的房间活动时间占比超过阈值
        """
        deviation_threshold = settings.ROOM_ACTIVITY_DEVIATION_PERCENT

        # 获取老人的位置基线
        pattern = self.db.query(Pattern).filter(
            and_(
                Pattern.elder_id == elder_id,
                Pattern.pattern_type == "location"
            )
        ).first()

        if not pattern or not pattern.usual_active_rooms:
            return None  # 没有基线数据

        usual_rooms = pattern.usual_active_rooms  # List[str]

        # ✅ 统计过去24小时的房间活动（在数据库层计算，不加载所有记录）
        yesterday = datetime.utcnow() - timedelta(hours=24)

        # 计算总事件数和异常房间事件数
        result = self.db.query(
            func.count(Event.id).label('total'),
            func.count(case((~Event.room.in_(usual_rooms), 1))).label('unusual')
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
            # ✅ 只在需要时才查询具体的异常房间名称
            unusual_rooms_result = self.db.query(
                func.distinct(Event.room).label('room')
            ).filter(
                and_(
                    Event.elder_id == elder_id,
                    Event.family_id == family_id,
                    Event.timestamp >= yesterday,
                    ~Event.room.in_(usual_rooms)
                )
            ).all()

            unusual_rooms_list = [r[0] for r in unusual_rooms_result if r[0]]

            logger.warning(f"Elder {elder_id} room pattern change: {unusual_activity_percent:.0f}% in unusual rooms {unusual_rooms_list}")
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

    # ==================== 辅助函数 ====================

    def get_today_activity_summary(self, elder_id: str, family_id: str) -> Dict[str, Any]:
        """获取今天的活动摘要"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        activities = self.db.query(Event).filter(
            and_(
                Event.elder_id == elder_id,
                Event.family_id == family_id,
                Event.timestamp >= today_start,
                Event.event_type.in_([EventType.MOTION, EventType.PRESENCE])
            )
        ).all()

        # 按房间统计
        room_activities = {}
        for activity in activities:
            room = activity.room or "unknown"
            room_activities[room] = room_activities.get(room, 0) + 1

        return {
            "total_activities": len(activities),
            "room_activities": room_activities,
            "first_activity_time": activities[0].timestamp.isoformat() if activities else None,
            "last_activity_time": activities[-1].timestamp.isoformat() if activities else None,
        }

    def get_baseline_status(self, elder_id: str) -> Dict[str, Any]:
        """获取基线状态"""
        elder = self.db.query(Elder).filter(Elder.elder_id == elder_id).first()
        if not elder:
            return {}

        return {
            "baseline_status": elder.baseline_status,
            "baseline_days_collected": elder.baseline_days_collected,
            "baseline_last_updated": elder.baseline_last_updated.isoformat() if elder.baseline_last_updated else None,
        }
