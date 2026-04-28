"""
app/routes/maintenance.py

数据维护模块 API 路由
- 每日摘要 API
- 告警反馈 API
- 数据保留 API
- 定时任务日志 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional

from app.database import get_db
from app.services_maintenance import (
    DailySummaryService,
    AlertFeedbackService,
    DataRetentionService,
    ScheduledTaskService,
)
from app.schemas_maintenance import (
    DailySummaryCreate,
    DailySummaryResponse,
    AlertFeedbackCreate,
    AlertFeedbackResponse,
    AlertFeedbackUpdateRequest,
    AlertFeedbackStatsResponse,
    DataRetentionLogResponse,
    DatabaseStatsCollectionResponse,
    CleanupResultResponse,
    ScheduledTaskLog,
    BatchSummaryGenerationResponse,
)

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


# ==================== 每日摘要 API ====================

@router.get(
    "/summaries/{elder_id}",
    response_model=list[dict],
    summary="获取老人的每日摘要"
)
def get_elder_summaries(
    elder_id: str,
    family_id: str = Query(..., description="家庭ID"),
    days: int = Query(7, ge=1, le=90, description="天数范围"),
    db: Session = Depends(get_db)
):
    """
    获取指定老人最近 N 天的每日摘要

    - **elder_id**: 老人ID
    - **family_id**: 家庭ID
    - **days**: 天数范围（默认7天）
    """
    summaries = DailySummaryService.get_summaries(db, elder_id, days)
    if not summaries:
        raise HTTPException(status_code=404, detail="No summaries found")
    return summaries


@router.post(
    "/summaries/generate",
    response_model=dict,
    summary="生成每日摘要"
)
def generate_summary(
    request: DailySummaryCreate,
    db: Session = Depends(get_db)
):
    """
    为指定老人生成每日摘要

    - **elder_id**: 老人ID
    - **family_id**: 家庭ID
    - **summary_date**: 摘要日期（可选，默认为昨天）
    """
    result = DailySummaryService.generate_summary(
        db, request.elder_id, request.family_id, request.summary_date.isoformat() if request.summary_date else None
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post(
    "/summaries/batch-generate",
    response_model=BatchSummaryGenerationResponse,
    summary="批量生成每日摘要"
)
def batch_generate_summaries(
    family_id: str = Query(..., description="家庭ID"),
    summary_date: Optional[date] = Query(None, description="摘要日期"),
    db: Session = Depends(get_db)
):
    """
    为整个家庭生成每日摘要

    - **family_id**: 家庭ID
    - **summary_date**: 摘要日期（可选）
    """
    result = DailySummaryService.batch_generate_summaries(
        db, family_id, summary_date.isoformat() if summary_date else None
    )
    return result


# ==================== 告警反馈 API ====================

@router.post(
    "/alerts/{alert_id}/feedback",
    response_model=dict,
    summary="为告警添加反馈"
)
def create_alert_feedback(
    alert_id: str,
    elder_id: str = Query(..., description="老人ID"),
    family_id: str = Query(..., description="家庭ID"),
    feedback: AlertFeedbackCreate = None,
    db: Session = Depends(get_db)
):
    """
    为指定告警创建反馈

    - **alert_id**: 告警ID
    - **elder_id**: 老人ID
    - **family_id**: 家庭ID
    - **feedback**: 反馈数据
      - feedback_type: 'true_positive' | 'false_positive' | 'delayed' | 'missed'
      - feedback_confidence: 0.0 - 1.0
      - severity_assessment: 'correct' | 'overestimated' | 'underestimated'
      - user_id: 用户ID
      - feedback_text: 反馈文字说明
      - action_taken: 'none' | 'monitored' | 'contacted' | 'hospitalized'
      - outcome: 'recovered' | 'ongoing' | 'hospitalized' | 'resolved'
    """
    result = AlertFeedbackService.create_feedback(
        db, alert_id, elder_id, family_id, feedback
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.put(
    "/alerts/{alert_id}/feedback/{feedback_id}",
    response_model=dict,
    summary="更新告警反馈"
)
def update_alert_feedback(
    alert_id: str,
    feedback_id: str,
    update_data: AlertFeedbackUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    更新告警反馈的后续情况

    - **alert_id**: 告警ID
    - **feedback_id**: 反馈ID
    - **outcome**: 结果状态
    - **follow_up_notes**: 后续备注
    """
    result = AlertFeedbackService.update_feedback_outcome(
        db, feedback_id, update_data.outcome, update_data.follow_up_notes
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get(
    "/alerts/feedback-stats",
    response_model=AlertFeedbackStatsResponse,
    summary="获取告警反馈统计"
)
def get_feedback_stats(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    db: Session = Depends(get_db)
):
    """
    获取告警反馈统计信息

    包括：
    - 反馈分布（true_positive, false_positive 等比例）
    - 告警准确率（按告警类型）

    - **days**: 统计天数范围（默认30天）
    """
    stats = AlertFeedbackService.get_feedback_stats(db, days)
    if not stats:
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
    return stats


# ==================== 数据保留 API ====================

@router.post(
    "/cleanup",
    response_model=dict,
    summary="执行数据清理"
)
def execute_cleanup(
    table_name: Optional[str] = Query(None, description="指定要清理的表"),
    db: Session = Depends(get_db)
):
    """
    执行数据保留清理任务

    - **table_name**: 可选，指定表名 (events, alert_feedback, audit_logs)
      - 如果不指定，则执行所有清理任务

    清理规则：
    - events: 保留 90 天
    - daily_summaries: 保留 3 年
    - alerts: 保留 3 年
    - alert_feedback: 保留 3 年
    - audit_logs: 保留 1 年
    """
    result = DataRetentionService.cleanup_expired_data(db, table_name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get(
    "/cleanup-logs",
    response_model=list[dict],
    summary="获取清理日志"
)
def get_cleanup_logs(
    limit: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None, description="状态过滤: pending, completed, failed"),
    db: Session = Depends(get_db)
):
    """
    获取数据清理操作日志

    - **limit**: 返回记录数限制
    - **status**: 状态过滤（可选）
    """
    logs = DataRetentionService.get_retention_logs(db, limit, status)
    return logs


@router.get(
    "/database-stats",
    response_model=dict,
    summary="获取数据库统计"
)
def get_database_stats(
    db: Session = Depends(get_db)
):
    """
    获取数据库存储统计信息

    包括：
    - 各表大小
    - 各表行数
    - 总数据库大小
    """
    stats = DataRetentionService.get_database_stats(db)
    if "error" in stats:
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
    return stats


# ==================== 定时任务日志 API ====================

@router.get(
    "/tasks/logs",
    response_model=list[dict],
    summary="获取定时任务日志"
)
def get_task_logs(
    task_name: Optional[str] = Query(None, description="任务名称过滤"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    获取定时任务执行日志

    可用的任务名称：
    - generate_daily_summary: 生成每日摘要
    - update_patterns: 更新行为基线
    - cleanup_events: 清理过期事件

    - **task_name**: 可选，过滤指定任务
    - **limit**: 返回记录数限制
    """
    logs = ScheduledTaskService.get_task_logs(db, task_name, limit)
    return logs


# ==================== 维护统计 API ====================

@router.get(
    "/statistics",
    response_model=dict,
    summary="获取维护统计信息"
)
def get_maintenance_statistics(
    family_id: str = Query(..., description="家庭ID"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    获取维护模块的统计信息

    包括：
    - 每日摘要统计
    - 告警反馈统计
    - 数据清理情况
    - 定时任务执行情况

    - **family_id**: 家庭ID
    - **days**: 统计天数范围
    """
    try:
        # 获取反馈统计
        feedback_stats = AlertFeedbackService.get_feedback_stats(db, days)

        # 获取清理日志
        cleanup_logs = DataRetentionService.get_retention_logs(db, 100, "completed")

        # 获取数据库统计
        db_stats = DataRetentionService.get_database_stats(db)

        # 获取任务日志
        task_logs = ScheduledTaskService.get_task_logs(db, limit=100)

        return {
            "statistics_date": datetime.now(),
            "family_id": family_id,
            "days": days,
            "feedback": feedback_stats,
            "recent_cleanups": cleanup_logs[:10],
            "database": db_stats,
            "recent_tasks": task_logs[:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching statistics: {str(e)}")


# ==================== 健康检查 ====================

@router.get(
    "/health",
    response_model=dict,
    summary="维护模块健康检查"
)
def maintenance_health_check(
    db: Session = Depends(get_db)
):
    """
    检查维护模块是否正常运行

    包括：
    - 数据库连接状态
    - 维护表是否存在
    - 最后清理时间
    - 最后任务执行时间
    """
    try:
        # 检查维护表
        tables_check = db.execute(
            """
            SELECT EXISTS(SELECT 1 FROM information_schema.tables
                         WHERE table_name = 'daily_summaries')
            AND EXISTS(SELECT 1 FROM information_schema.tables
                      WHERE table_name = 'alert_feedback')
            """
        ).fetchone()[0]

        # 获取最后清理时间
        last_cleanup = db.execute(
            "SELECT MAX(executed_at) FROM data_retention_logs WHERE status = 'completed'"
        ).fetchone()[0]

        # 获取最后任务执行时间
        last_task = db.execute(
            "SELECT MAX(created_at) FROM scheduled_task_logs WHERE status = 'completed'"
        ).fetchone()[0]

        return {
            "status": "healthy" if tables_check else "degraded",
            "timestamp": datetime.now(),
            "tables_initialized": tables_check,
            "last_cleanup": last_cleanup,
            "last_task_execution": last_task
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(),
            "error": str(e)
        }
