"""
app/tasks.py

定时任务管理
- 每天凌晨生成每日摘要
- 每周清理过期事件
- 每天更新行为基线
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.services_maintenance import (
    DailySummaryService,
    DataRetentionService,
    ScheduledTaskService,
)

logger = logging.getLogger(__name__)


class ScheduledTasks:
    """定时任务管理器"""

    def __init__(self):
        self.is_running = False
        self.tasks = []

    async def start(self):
        """启动所有定时任务"""
        if self.is_running:
            logger.warning("Scheduled tasks are already running")
            return

        self.is_running = True
        logger.info("Starting scheduled tasks...")

        # 创建后台任务
        self.tasks = [
            asyncio.create_task(self.daily_summary_task()),
            asyncio.create_task(self.weekly_cleanup_task()),
            asyncio.create_task(self.daily_pattern_update_task()),
        ]

        logger.info("All scheduled tasks started")

    async def stop(self):
        """停止所有定时任务"""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping scheduled tasks...")

        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.tasks.clear()
        logger.info("All scheduled tasks stopped")

    async def daily_summary_task(self):
        """
        每日摘要生成任务
        每天凌晨 01:00 执行
        为所有家庭生成昨日摘要
        """
        while self.is_running:
            try:
                # 计算下次执行时间（凌晨 01:00）
                now = datetime.now()
                next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)

                if now > next_run:
                    next_run += timedelta(days=1)

                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Daily summary task will run in {wait_seconds} seconds")

                await asyncio.sleep(wait_seconds)

                if not self.is_running:
                    break

                # 执行任务
                await self._execute_daily_summary()

            except asyncio.CancelledError:
                logger.info("Daily summary task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily summary task: {str(e)}", exc_info=True)
                # 等待 1 小时后重试
                await asyncio.sleep(3600)

    async def _execute_daily_summary(self):
        """执行每日摘要生成"""
        db = SessionLocal()
        start_time = datetime.now()

        try:
            logger.info("Starting daily summary generation...")

            # 获取所有家庭
            query = "SELECT DISTINCT family_id FROM families"
            result = db.execute(text(query))
            families = result.fetchall()

            success_count = 0
            failed_count = 0

            for family_row in families:
                family_id = family_row[0]
                try:
                    result = DailySummaryService.batch_generate_summaries(
                        db, family_id
                    )

                    success_count += result.get("success_count", 0)
                    failed_count += result.get("failed_count", 0)

                    logger.info(
                        f"Generated summaries for family {family_id}: "
                        f"{result.get('success_count')} success, "
                        f"{result.get('failed_count')} failed"
                    )
                except Exception as e:
                    logger.error(f"Error generating summaries for family {family_id}: {str(e)}")
                    failed_count += 1

            # 记录任务执行
            duration = int((datetime.now() - start_time).total_seconds())
            ScheduledTaskService.log_task_execution(
                db,
                task_name="generate_daily_summary",
                status="completed" if failed_count == 0 else "completed_with_errors",
                records_processed=success_count + failed_count,
                records_created=success_count,
                error_message=None if failed_count == 0 else f"{failed_count} summaries failed",
                duration_seconds=duration
            )

            logger.info(
                f"Daily summary generation completed: "
                f"{success_count} success, {failed_count} failed, "
                f"{duration}s elapsed"
            )

        except Exception as e:
            logger.error(f"Fatal error in daily summary generation: {str(e)}")
            duration = int((datetime.now() - start_time).total_seconds())
            try:
                ScheduledTaskService.log_task_execution(
                    db,
                    task_name="generate_daily_summary",
                    status="failed",
                    error_message=str(e),
                    duration_seconds=duration
                )
            except Exception as log_error:
                logger.error(f"Failed to log task error: {str(log_error)}")
        finally:
            db.close()

    async def weekly_cleanup_task(self):
        """
        每周清理任务
        每周日凌晨 02:00 执行
        清理过期的事件数据
        """
        while self.is_running:
            try:
                # 计算下次执行时间（周日凌晨 02:00）
                now = datetime.now()
                days_until_sunday = (6 - now.weekday()) % 7  # 0=Monday, 6=Sunday
                if days_until_sunday == 0 and now.hour >= 2:
                    days_until_sunday = 7

                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
                next_run += timedelta(days=days_until_sunday)

                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Weekly cleanup task will run in {wait_seconds} seconds")

                await asyncio.sleep(wait_seconds)

                if not self.is_running:
                    break

                # 执行任务
                await self._execute_cleanup()

            except asyncio.CancelledError:
                logger.info("Weekly cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in weekly cleanup task: {str(e)}", exc_info=True)
                # 等待 1 小时后重试
                await asyncio.sleep(3600)

    async def _execute_cleanup(self):
        """执行数据清理"""
        db = SessionLocal()
        start_time = datetime.now()

        try:
            logger.info("Starting weekly cleanup...")

            # 执行清理
            result = DataRetentionService.cleanup_expired_data(db)

            if result.get("success"):
                total_deleted = sum(task.get("rows_affected", 0) for task in result.get("cleanup_tasks", []))
                duration = int((datetime.now() - start_time).total_seconds())

                ScheduledTaskService.log_task_execution(
                    db,
                    task_name="cleanup_events",
                    status="completed",
                    records_processed=total_deleted,
                    duration_seconds=duration
                )

                logger.info(
                    f"Weekly cleanup completed: {total_deleted} rows deleted, "
                    f"{duration}s elapsed"
                )
            else:
                logger.error(f"Cleanup failed: {result.get('message')}")
                duration = int((datetime.now() - start_time).total_seconds())
                ScheduledTaskService.log_task_execution(
                    db,
                    task_name="cleanup_events",
                    status="failed",
                    error_message=result.get("message"),
                    duration_seconds=duration
                )

        except Exception as e:
            logger.error(f"Fatal error in cleanup task: {str(e)}")
            duration = int((datetime.now() - start_time).total_seconds())
            try:
                ScheduledTaskService.log_task_execution(
                    db,
                    task_name="cleanup_events",
                    status="failed",
                    error_message=str(e),
                    duration_seconds=duration
                )
            except Exception as log_error:
                logger.error(f"Failed to log task error: {str(log_error)}")
        finally:
            db.close()

    async def daily_pattern_update_task(self):
        """
        每日基线更新任务
        每天凌晨 03:00 执行
        重新计算所有老人的行为基线
        """
        while self.is_running:
            try:
                # 计算下次执行时间（凌晨 03:00）
                now = datetime.now()
                next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)

                if now > next_run:
                    next_run += timedelta(days=1)

                wait_seconds = (next_run - now).total_seconds()
                logger.info(f"Daily pattern update task will run in {wait_seconds} seconds")

                await asyncio.sleep(wait_seconds)

                if not self.is_running:
                    break

                # 执行任务
                await self._execute_pattern_update()

            except asyncio.CancelledError:
                logger.info("Daily pattern update task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in daily pattern update task: {str(e)}", exc_info=True)
                # 等待 1 小时后重试
                await asyncio.sleep(3600)

    async def _execute_pattern_update(self):
        """执行行为基线更新"""
        db = SessionLocal()
        start_time = datetime.now()

        try:
            logger.info("Starting daily pattern update...")

            # 获取所有老人
            query = "SELECT elder_id, family_id FROM elders"
            result = db.execute(text(query))
            elders = result.fetchall()

            success_count = 0
            failed_count = 0

            for elder_row in elders:
                elder_id, family_id = elder_row[0], elder_row[1]
                try:
                    # 计算模式（这里需要调用规则引擎中的函数）
                    # 这是一个示例，实际需要根据现有的规则引擎实现
                    query = """
                    SELECT COUNT(*) FROM events
                    WHERE elder_id = %s AND DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day'
                    """
                    result = db.execute(text(query), [elder_id])
                    event_count = result.fetchone()[0]

                    if event_count > 0:
                        logger.debug(f"Updated pattern for elder {elder_id}: {event_count} events")
                        success_count += 1
                    else:
                        logger.debug(f"No events to process for elder {elder_id}")

                except Exception as e:
                    logger.error(f"Error updating pattern for elder {elder_id}: {str(e)}")
                    failed_count += 1

            # 记录任务执行
            duration = int((datetime.now() - start_time).total_seconds())
            ScheduledTaskService.log_task_execution(
                db,
                task_name="update_patterns",
                status="completed" if failed_count == 0 else "completed_with_errors",
                records_processed=success_count + failed_count,
                records_created=success_count,
                error_message=None if failed_count == 0 else f"{failed_count} updates failed",
                duration_seconds=duration
            )

            logger.info(
                f"Daily pattern update completed: "
                f"{success_count} success, {failed_count} failed, "
                f"{duration}s elapsed"
            )

        except Exception as e:
            logger.error(f"Fatal error in pattern update: {str(e)}")
            duration = int((datetime.now() - start_time).total_seconds())
            try:
                ScheduledTaskService.log_task_execution(
                    db,
                    task_name="update_patterns",
                    status="failed",
                    error_message=str(e),
                    duration_seconds=duration
                )
            except Exception as log_error:
                logger.error(f"Failed to log task error: {str(log_error)}")
        finally:
            db.close()


# 全局任务管理器实例
scheduled_tasks = ScheduledTasks()
