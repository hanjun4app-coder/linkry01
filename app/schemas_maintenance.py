"""
app/schemas_maintenance.py

数据维护模块的 Pydantic 数据模型
- 每日摘要数据模型
- 告警反馈数据模型
- 数据保留数据模型

这个文件应该被导入到 app/schemas.py 中
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==================== 每日摘要数据模型 ====================

class DailySummaryCreate(BaseModel):
    """创建每日摘要的请求"""
    elder_id: str
    family_id: str
    summary_date: Optional[date] = None


class DailySummaryResponse(BaseModel):
    """每日摘要响应"""
    summary_id: str
    elder_id: str
    family_id: str
    summary_date: date

    total_activity_minutes: int = 0
    active_rooms: List[str] = []
    room_activity_distribution: Optional[Dict[str, Any]] = None

    sleep_start_time: Optional[str] = None
    sleep_end_time: Optional[str] = None
    sleep_quality_score: float = 0

    bathroom_visits: int = 0
    avg_bathroom_duration_minutes: float = 0
    abnormal_bathroom_visits: int = 0

    total_alerts: int = 0
    critical_alerts: int = 0
    warning_alerts: int = 0

    activity_baseline_variance: float = 0
    pattern_deviation_count: int = 0

    data_quality_score: float = 0
    device_uptime_percent: float = 0

    notes: Optional[str] = None
    recommendations: List[str] = []

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DailySummaryListResponse(BaseModel):
    """每日摘要列表响应"""
    total_count: int
    summaries: List[DailySummaryResponse]


class DailySummaryStatsResponse(BaseModel):
    """每日摘要统计响应"""
    family_id: str
    summary_date: date
    elder_count: int
    avg_activity_minutes: float
    avg_sleep_quality: float
    total_alerts_today: int
    critical_alerts_today: int
    avg_data_quality: float


# ==================== 告警反馈数据模型 ====================

class AlertFeedbackCreate(BaseModel):
    """创建告警反馈的请求"""
    feedback_type: str = Field(..., description="true_positive, false_positive, delayed, missed")
    feedback_confidence: Optional[float] = Field(None, ge=0, le=1)
    severity_assessment: Optional[str] = None
    user_id: Optional[str] = None
    feedback_text: Optional[str] = None
    action_taken: Optional[str] = None
    outcome: Optional[str] = None


class AlertFeedbackResponse(BaseModel):
    """告警反馈响应"""
    feedback_id: str
    alert_id: str
    elder_id: str
    family_id: str

    feedback_type: str
    feedback_confidence: Optional[float] = None
    severity_assessment: Optional[str] = None

    user_id: Optional[str] = None
    feedback_text: Optional[str] = None
    action_taken: Optional[str] = None

    outcome: Optional[str] = None
    follow_up_date: Optional[date] = None
    follow_up_notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertFeedbackUpdateRequest(BaseModel):
    """更新告警反馈的请求"""
    outcome: str = Field(..., description="recovered, ongoing, hospitalized, resolved")
    follow_up_notes: Optional[str] = None


class AlertAccuracyStats(BaseModel):
    """告警准确率统计"""
    alert_type: str
    total_alerts: int
    true_positives: int
    false_positives: int
    accuracy_percent: float


class AlertFeedbackStatsResponse(BaseModel):
    """告警反馈统计响应"""
    period_days: int
    feedback_distribution: List[Dict[str, Any]]
    accuracy_stats: List[AlertAccuracyStats]


# ==================== 数据保留数据模型 ====================

class DataRetentionLogResponse(BaseModel):
    """数据保留操作日志响应"""
    log_id: str
    operation_type: str
    table_name: str
    retention_days: Optional[int] = None
    rows_affected: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    backup_file_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatabaseStatsResponse(BaseModel):
    """数据库统计信息响应"""
    schema: str
    table: str
    size: str
    row_count: int


class DatabaseStatsCollectionResponse(BaseModel):
    """数据库统计集合响应"""
    total_size: str
    tables: List[DatabaseStatsResponse]


class CleanupResultResponse(BaseModel):
    """数据清理结果响应"""
    success: bool
    table: Optional[str] = None
    rows_deleted: int = 0
    duration_seconds: int = 0
    message: Optional[str] = None


class CleanupBatchResultResponse(BaseModel):
    """批量清理结果响应"""
    success: bool
    cleanup_tasks: List[Dict[str, Any]]
    total_rows_deleted: int


# ==================== 定时任务数据模型 ====================

class ScheduledTaskLog(BaseModel):
    """定时任务执行日志"""
    task_id: str
    task_name: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: int = 0
    records_processed: int = 0
    records_created: int = 0
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskExecutionResponse(BaseModel):
    """定时任务执行响应"""
    task_name: str
    status: str
    message: Optional[str] = None
    duration_seconds: Optional[int] = None
    records_processed: int = 0
    records_created: int = 0


# ==================== 批量操作数据模型 ====================

class BatchSummaryGenerationResponse(BaseModel):
    """批量生成摘要响应"""
    success_count: int
    failed_count: int
    summary_date: date
    details: List[Dict[str, Any]]


class HealthCheckResponse(BaseModel):
    """健康检查响应（包含维护信息）"""
    status: str = "healthy"
    timestamp: datetime
    version: str
    maintenance: Optional[Dict[str, Any]] = None
