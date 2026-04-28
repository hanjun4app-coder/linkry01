"""
app/services_maintenance.py

数据维护服务层
- 每日摘要生成
- 告警反馈处理
- 数据保留管理
- 定时任务支持
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import (
    DailySummaryCreate,
    DailySummaryResponse,
    AlertFeedbackCreate,
    AlertFeedbackResponse,
)


class DailySummaryService:
    """每日摘要服务"""

    @staticmethod
    def generate_summary(
        db: Session,
        elder_id: str,
        family_id: str,
        summary_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成指定老人的每日摘要

        Args:
            db: 数据库会话
            elder_id: 老人ID
            family_id: 家庭ID
            summary_date: 摘要日期（默认为昨天）

        Returns:
            包含摘要信息的字典
        """
        try:
            if summary_date is None:
                summary_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            # 调用 PostgreSQL 函数生成摘要
            query = """
            SELECT success, summary_id, message FROM generate_daily_summary(
                %s, %s, %s::DATE
            )
            """

            result = db.execute(text(query), [elder_id, family_id, summary_date])
            row = result.fetchone()

            if row and row[0]:  # success
                return {
                    "success": True,
                    "summary_id": str(row[1]),
                    "message": row[2],
                    "elder_id": elder_id,
                    "family_id": family_id,
                    "summary_date": summary_date
                }
            else:
                return {
                    "success": False,
                    "message": row[2] if row else "Unknown error",
                    "elder_id": elder_id
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error generating summary: {str(e)}",
                "elder_id": elder_id
            }

    @staticmethod
    def get_summaries(
        db: Session,
        elder_id: str,
        days: int = 7
    ) -> List[DailySummaryResponse]:
        """
        获取老人最近 N 天的摘要

        Args:
            db: 数据库会话
            elder_id: 老人ID
            days: 天数（默认7天）

        Returns:
            摘要列表
        """
        try:
            query = """
            SELECT * FROM get_elder_recent_summaries(%s, %s)
            """
            result = db.execute(text(query), [elder_id, days])
            rows = result.fetchall()

            summaries = []
            for row in rows:
                summaries.append({
                    "summary_date": row[0],
                    "total_activity_minutes": row[1],
                    "sleep_quality_score": float(row[2]) if row[2] else 0,
                    "total_alerts": row[3],
                    "critical_alerts": row[4],
                    "data_quality_score": float(row[5]) if row[5] else 0,
                })
            return summaries
        except Exception as e:
            print(f"Error fetching summaries: {str(e)}")
            return []

    @staticmethod
    def batch_generate_summaries(
        db: Session,
        family_id: str,
        summary_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        为整个家庭生成每日摘要

        Args:
            db: 数据库会话
            family_id: 家庭ID
            summary_date: 摘要日期

        Returns:
            生成结果统计
        """
        if summary_date is None:
            summary_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # 获取家庭下所有老人
        query = "SELECT elder_id FROM elders WHERE family_id = %s"
        result = db.execute(text(query), [family_id])
        elders = result.fetchall()

        results = {
            "success_count": 0,
            "failed_count": 0,
            "summary_date": summary_date,
            "details": []
        }

        for elder_row in elders:
            elder_id = elder_row[0]
            result = DailySummaryService.generate_summary(
                db, elder_id, family_id, summary_date
            )
            results["details"].append(result)

            if result["success"]:
                results["success_count"] += 1
            else:
                results["failed_count"] += 1

        return results


class AlertFeedbackService:
    """告警反馈服务"""

    @staticmethod
    def create_feedback(
        db: Session,
        alert_id: str,
        elder_id: str,
        family_id: str,
        feedback_data: AlertFeedbackCreate
    ) -> Dict[str, Any]:
        """
        创建告警反馈

        Args:
            db: 数据库会话
            alert_id: 告警ID
            elder_id: 老人ID
            family_id: 家庭ID
            feedback_data: 反馈数据

        Returns:
            创建结果
        """
        try:
            query = """
            INSERT INTO alert_feedback (
                alert_id, elder_id, family_id,
                feedback_type, feedback_confidence,
                severity_assessment, user_id, feedback_text,
                action_taken, outcome
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING feedback_id, created_at
            """

            result = db.execute(text(query), [
                alert_id, elder_id, family_id,
                feedback_data.feedback_type,
                feedback_data.feedback_confidence,
                feedback_data.severity_assessment,
                feedback_data.user_id,
                feedback_data.feedback_text,
                feedback_data.action_taken,
                feedback_data.outcome
            ])

            db.commit()
            row = result.fetchone()

            if row:
                return {
                    "success": True,
                    "feedback_id": str(row[0]),
                    "created_at": row[1],
                    "alert_id": alert_id
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to create feedback"
                }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error creating feedback: {str(e)}"
            }

    @staticmethod
    def get_feedback_stats(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取告警反馈统计

        Args:
            db: 数据库会话
            days: 天数范围

        Returns:
            反馈统计数据
        """
        try:
            query = """
            SELECT
                af.feedback_type,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
                ROUND(AVG(af.feedback_confidence), 2) as avg_confidence
            FROM alert_feedback af
            WHERE af.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * %s
            GROUP BY af.feedback_type
            """

            result = db.execute(text(query), [days])
            rows = result.fetchall()

            stats = {
                "period_days": days,
                "feedback_distribution": [],
                "summary": {}
            }

            for row in rows:
                stats["feedback_distribution"].append({
                    "feedback_type": row[0],
                    "count": row[1],
                    "percentage": float(row[2]),
                    "avg_confidence": float(row[3]) if row[3] else 0
                })

            # 获取准确率统计
            accuracy_query = """
            SELECT * FROM v_alert_accuracy_rate
            """
            accuracy_result = db.execute(text(accuracy_query))
            accuracy_rows = accuracy_result.fetchall()

            stats["accuracy_stats"] = []
            for row in accuracy_rows:
                stats["accuracy_stats"].append({
                    "alert_type": row[0],
                    "total_alerts": row[1],
                    "true_positives": row[2],
                    "false_positives": row[3],
                    "accuracy_percent": float(row[4]) if row[4] else 0
                })

            return stats
        except Exception as e:
            print(f"Error fetching feedback stats: {str(e)}")
            return {}

    @staticmethod
    def update_feedback_outcome(
        db: Session,
        feedback_id: str,
        outcome: str,
        follow_up_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新反馈的后续情况

        Args:
            db: 数据库会话
            feedback_id: 反馈ID
            outcome: 结果（recovered, ongoing, hospitalized, resolved）
            follow_up_notes: 后续备注

        Returns:
            更新结果
        """
        try:
            query = """
            UPDATE alert_feedback
            SET outcome = %s,
                follow_up_notes = %s,
                follow_up_date = CURRENT_DATE,
                updated_at = CURRENT_TIMESTAMP
            WHERE feedback_id = %s::UUID
            RETURNING feedback_id
            """

            result = db.execute(text(query), [
                outcome, follow_up_notes, feedback_id
            ])
            db.commit()

            if result.rowcount > 0:
                return {
                    "success": True,
                    "feedback_id": feedback_id,
                    "outcome": outcome
                }
            else:
                return {
                    "success": False,
                    "message": "Feedback not found"
                }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error updating feedback: {str(e)}"
            }


class DataRetentionService:
    """数据保留和清理服务"""

    @staticmethod
    def cleanup_expired_data(
        db: Session,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行数据清理任务

        Args:
            db: 数据库会话
            table_name: 指定表名（None则执行所有清理）

        Returns:
            清理结果
        """
        try:
            if table_name:
                # 清理指定表
                if table_name == "events":
                    query = "SELECT * FROM cleanup_expired_events(90)"
                elif table_name == "alert_feedback":
                    query = "SELECT * FROM cleanup_expired_alert_feedback(1095)"
                elif table_name == "audit_logs":
                    query = "SELECT * FROM cleanup_expired_audit_logs(365)"
                else:
                    return {
                        "success": False,
                        "message": f"Unknown table: {table_name}"
                    }

                result = db.execute(text(query))
                row = result.fetchone()

                return {
                    "success": row[0] == "success",
                    "table": table_name,
                    "rows_deleted": row[1],
                    "duration_seconds": row[2]
                }
            else:
                # 执行所有清理任务
                query = "SELECT * FROM execute_retention_cleanup()"
                result = db.execute(text(query))
                rows = result.fetchall()

                results = {
                    "success": True,
                    "cleanup_tasks": [],
                    "total_rows_deleted": 0
                }

                for row in rows:
                    results["cleanup_tasks"].append({
                        "task_name": row[0],
                        "status": row[1],
                        "rows_affected": row[2]
                    })
                    results["total_rows_deleted"] += row[2]

                return results
        except Exception as e:
            return {
                "success": False,
                "message": f"Error during cleanup: {str(e)}"
            }

    @staticmethod
    def get_retention_logs(
        db: Session,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取数据保留操作日志

        Args:
            db: 数据库会话
            limit: 限制数量
            status: 状态过滤（pending, completed, failed）

        Returns:
            日志列表
        """
        try:
            if status:
                query = """
                SELECT log_id, operation_type, table_name, rows_affected,
                       status, executed_at, duration_seconds
                FROM data_retention_logs
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
                """
                result = db.execute(text(query), [status, limit])
            else:
                query = """
                SELECT log_id, operation_type, table_name, rows_affected,
                       status, executed_at, duration_seconds
                FROM data_retention_logs
                ORDER BY created_at DESC
                LIMIT %s
                """
                result = db.execute(text(query), [limit])

            rows = result.fetchall()
            logs = []

            for row in rows:
                logs.append({
                    "log_id": str(row[0]),
                    "operation_type": row[1],
                    "table_name": row[2],
                    "rows_affected": row[3],
                    "status": row[4],
                    "executed_at": row[5],
                    "duration_seconds": row[6]
                })

            return logs
        except Exception as e:
            print(f"Error fetching retention logs: {str(e)}")
            return []

    @staticmethod
    def get_database_stats(db: Session) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Args:
            db: 数据库会话

        Returns:
            数据库统计数据
        """
        try:
            query = """
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                n_live_tup as row_count
            FROM pg_stat_user_tables
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """

            result = db.execute(text(query))
            rows = result.fetchall()

            stats = {
                "total_size": 0,
                "tables": []
            }

            for row in rows:
                stats["tables"].append({
                    "schema": row[0],
                    "table": row[1],
                    "size": row[2],
                    "row_count": row[3]
                })

            return stats
        except Exception as e:
            print(f"Error fetching database stats: {str(e)}")
            return {"error": str(e)}


class ScheduledTaskService:
    """定时任务服务"""

    @staticmethod
    def log_task_execution(
        db: Session,
        task_name: str,
        status: str,
        elder_id: Optional[str] = None,
        family_id: Optional[str] = None,
        records_processed: int = 0,
        records_created: int = 0,
        error_message: Optional[str] = None,
        duration_seconds: int = 0
    ) -> bool:
        """
        记录定时任务执行日志

        Args:
            db: 数据库会话
            task_name: 任务名称
            status: 状态
            elder_id: 老人ID（可选）
            family_id: 家庭ID（可选）
            records_processed: 处理记录数
            records_created: 创建记录数
            error_message: 错误信息
            duration_seconds: 执行时间（秒）

        Returns:
            是否成功
        """
        try:
            query = """
            INSERT INTO scheduled_task_logs (
                task_name, elder_id, family_id, status,
                started_at, completed_at, duration_seconds,
                records_processed, records_created, error_message
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            db.execute(text(query), [
                task_name, elder_id, family_id, status,
                datetime.now(), datetime.now(), duration_seconds,
                records_processed, records_created, error_message
            ])

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error logging task: {str(e)}")
            return False

    @staticmethod
    def get_task_logs(
        db: Session,
        task_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取定时任务执行日志

        Args:
            db: 数据库会话
            task_name: 任务名称过滤
            limit: 限制数量

        Returns:
            任务日志列表
        """
        try:
            if task_name:
                query = """
                SELECT task_id, task_name, status, started_at,
                       duration_seconds, records_processed, error_message
                FROM scheduled_task_logs
                WHERE task_name = %s
                ORDER BY created_at DESC
                LIMIT %s
                """
                result = db.execute(text(query), [task_name, limit])
            else:
                query = """
                SELECT task_id, task_name, status, started_at,
                       duration_seconds, records_processed, error_message
                FROM scheduled_task_logs
                ORDER BY created_at DESC
                LIMIT %s
                """
                result = db.execute(text(query), [limit])

            rows = result.fetchall()
            logs = []

            for row in rows:
                logs.append({
                    "task_id": str(row[0]),
                    "task_name": row[1],
                    "status": row[2],
                    "started_at": row[3],
                    "duration_seconds": row[4],
                    "records_processed": row[5],
                    "error_message": row[6]
                })

            return logs
        except Exception as e:
            print(f"Error fetching task logs: {str(e)}")
            return []
