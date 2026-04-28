"""SQLAlchemy ORM 模型"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean,
    JSON, ForeignKey, Index, Text, func, UniqueConstraint  # ✅ 添加 UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Family(Base):
    """家庭信息"""
    __tablename__ = "families"

    id = Column(Integer, primary_key=True)
    family_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    elders = relationship("Elder", back_populates="family", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="family", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="family", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="family", cascade="all, delete-orphan")


class Elder(Base):
    """老人信息"""
    __tablename__ = "elders"

    id = Column(Integer, primary_key=True)
    # ✅ 修复 P0: 多租户约束 - elder_id 不再全局唯一，改为 (family_id, elder_id) 组合唯一
    elder_id = Column(String(50), nullable=False, index=True)
    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    name = Column(String(200), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))  # M/F/Other

    # 健康信息
    health_conditions = Column(JSON, default={})  # 健康状况（高血压、糖尿病等）
    emergency_contacts = Column(JSON, default=[])

    # 基线数据
    baseline_data = Column(JSON, default={})  # 存储最新的基线模式
    baseline_status = Column(String(20), default="collecting")  # collecting/active/needs_review
    baseline_days_collected = Column(Integer, default=0)
    baseline_last_updated = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    family = relationship("Family", back_populates="elders")
    devices = relationship("Device", back_populates="elder", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="elder", cascade="all, delete-orphan")
    patterns = relationship("Pattern", back_populates="elder", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="elder", cascade="all, delete-orphan")

    __table_args__ = (
        # ✅ 组合唯一约束：每个家庭内的 elder_id 唯一
        UniqueConstraint('family_id', 'elder_id', name='uq_family_elder'),
        Index("idx_elder_family", "elder_id", "family_id"),
    )


class Device(Base):
    """设备信息"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    # ✅ 修复 P0: 多租户约束 - device_id 不再全局唯一，改为 (family_id, device_id) 组合唯一
    device_id = Column(String(100), nullable=False, index=True)
    device_type = Column(String(50), nullable=False)  # aqara_fp2, door_sensor, etc.

    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    elder_id = Column(String(50), ForeignKey("elders.elder_id"), nullable=True)

    room = Column(String(100))  # 房间名称
    name = Column(String(200))
    description = Column(Text)

    # 设备状态
    is_online = Column(Boolean, default=True)
    last_seen = Column(DateTime)
    firmware_version = Column(String(50))

    # 元数据
    extra_data = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    family = relationship("Family", back_populates="devices")
    elder = relationship("Elder", back_populates="devices")
    events = relationship("Event", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        # ✅ 组合唯一约束：每个家庭内的 device_id 唯一
        UniqueConstraint('family_id', 'device_id', name='uq_family_device'),
        Index("idx_device_family_elder", "family_id", "elder_id"),
    )


class Event(Base):
    """事件记录"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String(50), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)

    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    elder_id = Column(String(50), ForeignKey("elders.elder_id"), nullable=False)
    device_id = Column(String(100), ForeignKey("devices.device_id"), nullable=False)

    event_type = Column(String(50), nullable=False)  # motion, presence, door, etc.
    event_value = Column(JSON, default={})

    room = Column(String(100))
    location_name = Column(String(200))

    confidence = Column(Float, default=1.0)
    extra_data = Column(JSON, default={})

    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    family = relationship("Family", back_populates="events")
    elder = relationship("Elder", back_populates="events")
    device = relationship("Device", back_populates="events")
    alert = relationship("Alert", uselist=False, back_populates="event")

    __table_args__ = (
        Index("idx_event_elder_timestamp", "elder_id", "timestamp"),
        Index("idx_event_family_timestamp", "family_id", "timestamp"),
        Index("idx_event_type_timestamp", "event_type", "timestamp"),
        Index("idx_event_room", "room"),
    )


class Pattern(Base):
    """行为模式（用户基线）"""
    __tablename__ = "patterns"

    id = Column(Integer, primary_key=True)

    elder_id = Column(String(50), ForeignKey("elders.elder_id"), nullable=False, index=True)
    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)

    pattern_type = Column(String(50), nullable=False)  # activity, sleep, bathroom, location

    # 具体数据
    average_daily_activity_minutes = Column(Integer)
    average_wake_time = Column(String(10))  # HH:MM
    average_sleep_time = Column(String(10))
    average_bathroom_count = Column(Integer)
    average_bathroom_duration_minutes = Column(Integer)
    usual_active_rooms = Column(JSON, default=[])

    confidence = Column(Float, default=0.7)
    status = Column(String(20), default="collecting")  # collecting/active/needs_review

    days_collected = Column(Integer, default=0)
    baseline_date = Column(DateTime, default=datetime.utcnow)

    extra_data = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    elder = relationship("Elder", back_populates="patterns")

    __table_args__ = (
        Index("idx_pattern_elder_type", "elder_id", "pattern_type"),
    )


class Alert(Base):
    """告警记录"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    alert_id = Column(String(50), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)

    family_id = Column(String(50), ForeignKey("families.family_id"), nullable=False)
    elder_id = Column(String(50), ForeignKey("elders.elder_id"), nullable=False)

    alert_type = Column(String(50), nullable=False, index=True)  # inactivity, bathroom_timeout, etc.
    alert_level = Column(String(20), nullable=False)  # info, warning, critical

    message = Column(Text, nullable=False)
    details = Column(JSON, default={})

    # 关联事件
    event_id = Column(String(50), ForeignKey("events.event_id"), nullable=True)

    # 状态
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    family = relationship("Family", back_populates="alerts")
    elder = relationship("Elder", back_populates="alerts")
    event = relationship("Event", back_populates="alert", uselist=False)

    __table_args__ = (
        Index("idx_alert_elder_timestamp", "elder_id", "created_at"),
        Index("idx_alert_family_timestamp", "family_id", "created_at"),
        Index("idx_alert_type_level", "alert_type", "alert_level"),
        # ✅ 新增索引：用于重复检测（防竞态条件）
        Index("idx_alert_dedup", "elder_id", "alert_type", "is_acknowledged"),
        # ✅ 新增索引：用于列出未确认告警
        Index("idx_alert_unacked", "family_id", "is_acknowledged", "created_at"),
    )


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))

    user_id = Column(String(100))
    details = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_audit_timestamp", "created_at"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )
