"""Pydantic 数据模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ==================== 枚举定义 ====================

class EventType(str, Enum):
    """事件类型"""
    MOTION = "motion"              # 运动检测
    PRESENCE = "presence"          # 存在检测
    BATHROOM = "bathroom"          # 卫生间检测
    DOOR = "door"                  # 门磁
    TEMPERATURE = "temperature"    # 温度
    HUMIDITY = "humidity"          # 湿度
    FALL = "fall"                  # 跌倒
    SLEEP = "sleep"                # 睡眠
    ACTIVITY = "activity"          # 活动
    HEART_RATE = "heart_rate"      # 心率
    CUSTOM = "custom"              # 自定义


class DeviceType(str, Enum):
    """设备类型"""
    FP2 = "aqara_fp2"              # Aqara FP2 人体传感器
    DOOR_SENSOR = "door_sensor"    # 门磁
    TEMP_HUMIDITY = "temp_humidity"# 温湿度传感器
    MOTION = "motion_sensor"       # 运动传感器
    WEARABLE = "wearable"          # 可穿戴设备
    CUSTOM = "custom"


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """告警类型"""
    INACTIVITY = "inactivity"              # 长时间无活动
    BATHROOM_TIMEOUT = "bathroom_timeout"  # 卫生间停留过久
    ABNORMAL_WAKE = "abnormal_wake"        # 起床时间异常
    NIGHT_ACTIVITY = "night_activity"      # 夜间频繁活动
    ROOM_PATTERN_CHANGE = "room_pattern_change"  # 房间活动模式改变
    FALL = "fall"                          # 跌倒
    ABNORMAL_HEART_RATE = "abnormal_heart_rate"  # 异常心率
    CUSTOM = "custom"


class PatternType(str, Enum):
    """模式类型"""
    ACTIVITY = "activity"          # 活动模式
    SLEEP = "sleep"                # 睡眠模式
    BATHROOM = "bathroom"          # 卫生间使用模式
    LOCATION = "location"          # 位置模式
    VITAL = "vital_signs"          # 生命体征模式


# ==================== 事件相关 Schema ====================

class StandardEvent(BaseModel):
    """标准化事件格式（核心数据结构）"""

    # 标识
    elder_id: str = Field(..., description="老人 ID")
    family_id: str = Field(..., description="家庭 ID")
    device_id: str = Field(..., description="设备 ID")
    device_type: DeviceType = Field(..., description="设备类型")

    # 事件信息
    event_type: EventType = Field(..., description="事件类型")
    event_value: Dict[str, Any] = Field(default={}, description="事件数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间")

    # 位置信息
    room: Optional[str] = Field(None, description="房间")
    location_name: Optional[str] = Field(None, description="位置名称")

    # 质量指标
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度 (0-1)")
    metadata: Dict[str, Any] = Field(default={}, description="额外元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "elder_id": "elder_001",
                "family_id": "family_001",
                "device_id": "aqara_fp2_bedroom",
                "device_type": "aqara_fp2",
                "event_type": "presence",
                "event_value": {"detected": True, "distance": 2.5},
                "timestamp": "2024-01-15T10:30:00Z",
                "room": "bedroom",
                "confidence": 0.95
            }
        }


class EventCreate(StandardEvent):
    """创建事件请求"""
    pass


class EventResponse(StandardEvent):
    """事件响应"""
    id: int = Field(..., description="事件 ID")
    created_at: datetime = Field(..., description="创建时间")
    device_type: Optional[str] = None  # 覆盖父类的 device_type，使其可选

    class Config:
        from_attributes = True


class BulkEventCreate(BaseModel):
    """批量上传事件"""
    events: List[EventCreate]
    batch_id: Optional[str] = Field(None, description="批次 ID")


# ==================== 告警相关 Schema ====================

class AlertCreate(BaseModel):
    """创建告警"""
    elder_id: str
    family_id: str
    alert_type: AlertType
    alert_level: AlertLevel
    message: str
    details: Dict[str, Any] = {}
    triggered_event_ids: Optional[List[int]] = None


class AlertResponse(BaseModel):
    """告警响应"""
    id: int
    elder_id: str
    family_id: str
    alert_type: AlertType
    alert_level: AlertLevel
    message: str
    details: Dict[str, Any]
    is_acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertQuery(BaseModel):
    """查询告警条件"""
    elder_id: Optional[str] = None
    family_id: Optional[str] = None
    alert_type: Optional[AlertType] = None
    alert_level: Optional[AlertLevel] = None
    is_acknowledged: Optional[bool] = None
    days: int = Field(default=7, ge=1, le=90, description="查询天数")
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AlertListResponse(BaseModel):
    """告警列表响应"""
    total: int
    alerts: List[AlertResponse]
    has_more: bool


# 别名（为了兼容）
Alert = AlertResponse


# ==================== 模式相关 Schema ====================

class DailyPattern(BaseModel):
    """每日模式"""
    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    pattern_type: PatternType
    data: Dict[str, Any]
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ElderPattern(BaseModel):
    """老人行为模式"""
    elder_id: str
    family_id: str
    pattern_type: PatternType

    # 活动模式
    average_daily_activity_minutes: Optional[int] = None
    average_wake_time: Optional[str] = None  # HH:MM
    average_sleep_time: Optional[str] = None
    average_bathroom_count: Optional[int] = None
    average_bathroom_duration_minutes: Optional[int] = None

    # 房间活动
    usual_active_rooms: Optional[List[str]] = None

    # 时间相关
    baseline_date: datetime = Field(default_factory=datetime.utcnow)
    days_collected: int = 0

    # 置信度
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    # 状态
    status: str = Field(default="collecting", description="collecting | active | needs_review")


class PatternResponse(ElderPattern):
    """模式响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatternCreateRequest(BaseModel):
    """创建或更新模式请求"""
    elder_id: str
    family_id: str
    pattern_type: PatternType
    average_daily_activity_minutes: Optional[int] = None
    average_wake_time: Optional[str] = None
    average_sleep_time: Optional[str] = None
    average_bathroom_count: Optional[int] = None
    average_bathroom_duration_minutes: Optional[int] = None
    usual_active_rooms: Optional[List[str]] = None
    days_collected: int = 0


# ==================== 统计相关 Schema ====================

class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str
    database: str
    timestamp: datetime


class StatisticsResponse(BaseModel):
    """统计数据响应"""
    total_elders: int
    total_families: int
    total_devices: int
    total_events_today: int
    total_alerts_today: int
    avg_events_per_elder: float
    last_event_timestamp: Optional[datetime]


class DeviceInfo(BaseModel):
    """设备信息"""
    device_id: str
    device_type: DeviceType
    family_id: str
    elder_id: str
    room: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_online: bool = False
    metadata: Dict[str, Any] = {}


# ==================== Home Assistant 相关 ====================

class HomeAssistantEvent(BaseModel):
    """Home Assistant 事件（来自 HA Webhook）"""
    entity_id: str
    state: str
    old_state: Optional[str] = None
    attributes: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Optional[Dict[str, Any]] = None


# ==================== 通用响应 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
