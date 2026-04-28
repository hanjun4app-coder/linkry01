"""
用户反馈闭环服务

处理反馈令牌生成、验证和管理
"""

import logging
from typing import Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FeedbackTokenService:
    """反馈令牌服务"""

    @staticmethod
    def generate_feedback_token(
        db: Session,
        alert_id: str,
        token_expiry_hours: int = 72
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成反馈令牌

        调用 PostgreSQL 存储过程生成反馈令牌和 URL

        Args:
            db: 数据库连接
            alert_id: 告警 ID
            token_expiry_hours: 令牌有效期（小时），默认 72 小时

        Returns:
            (success, token, feedback_url)
            - success: 是否成功
            - token: 生成的令牌（如果成功）
            - feedback_url: 反馈 URL（如果成功）
        """
        try:
            result = db.execute(
                text("""
                SELECT * FROM generate_feedback_token(
                    :alert_id::UUID,
                    :token_expiry_hours
                )
                """),
                {
                    "alert_id": alert_id,
                    "token_expiry_hours": token_expiry_hours
                }
            ).first()

            if result:
                success, token, feedback_url, expires_at, message = result
                if success:
                    logger.info(
                        f"反馈令牌生成成功: alert_id={alert_id}, "
                        f"token={token[:10]}..., expires_at={expires_at}"
                    )
                    return True, token, feedback_url
                else:
                    logger.warning(f"反馈令牌生成失败: {message}")
                    return False, None, None
            else:
                logger.error("反馈令牌生成返回无效结果")
                return False, None, None

        except Exception as e:
            logger.error(f"生成反馈令牌异常: {str(e)}")
            return False, None, None

    @staticmethod
    def get_feedback_url(
        db: Session,
        alert_id: str
    ) -> Optional[str]:
        """
        获取告警的反馈 URL

        Args:
            db: 数据库连接
            alert_id: 告警 ID

        Returns:
            反馈 URL 或 None
        """
        try:
            result = db.execute(
                text("""
                SELECT feedback_url
                FROM alerts
                WHERE alert_id = :alert_id
                """),
                {"alert_id": alert_id}
            ).first()

            if result and result[0]:
                return result[0]
            return None

        except Exception as e:
            logger.error(f"获取反馈 URL 失败: {str(e)}")
            return None

    @staticmethod
    def check_token_validity(
        db: Session,
        alert_id: str,
        token: str
    ) -> Tuple[bool, str]:
        """
        检查令牌有效性

        Args:
            db: 数据库连接
            alert_id: 告警 ID
            token: 令牌

        Returns:
            (is_valid, reason)
            - is_valid: 令牌是否有效
            - reason: 无效原因（如果无效）
        """
        try:
            result = db.execute(
                text("""
                SELECT
                    CASE
                        WHEN ft.feedback_token IS NULL THEN 'no_token'
                        WHEN a.feedback_submitted THEN 'already_submitted'
                        WHEN ft.is_used THEN 'token_used'
                        WHEN ft.expires_at < CURRENT_TIMESTAMP THEN 'token_expired'
                        ELSE 'valid'
                    END as status
                FROM alerts a
                LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
                WHERE a.alert_id = :alert_id
                    AND (ft.feedback_token = :token OR ft.feedback_token IS NULL)
                """),
                {"alert_id": alert_id, "token": token}
            ).first()

            if result:
                status = result[0]
                return (
                    status == 'valid',
                    {
                        'no_token': '令牌不存在',
                        'already_submitted': '反馈已提交',
                        'token_used': '令牌已使用',
                        'token_expired': '令牌已过期',
                        'valid': ''
                    }.get(status, '未知错误')
                )
            return False, '未知错误'

        except Exception as e:
            logger.error(f"检查令牌有效性异常: {str(e)}")
            return False, '系统错误'

    @staticmethod
    def get_token_info(
        db: Session,
        alert_id: str
    ) -> Optional[dict]:
        """
        获取令牌信息

        Args:
            db: 数据库连接
            alert_id: 告警 ID

        Returns:
            令牌信息字典或 None
        """
        try:
            result = db.execute(
                text("""
                SELECT
                    ft.feedback_token,
                    ft.created_at,
                    ft.expires_at,
                    ft.is_used,
                    ft.used_at,
                    a.feedback_submitted,
                    a.feedback_submitted_at,
                    EXTRACT(HOUR FROM ft.expires_at - CURRENT_TIMESTAMP) as hours_remaining
                FROM alerts a
                LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
                WHERE a.alert_id = :alert_id
                """),
                {"alert_id": alert_id}
            ).first()

            if result:
                token, created_at, expires_at, is_used, used_at, feedback_submitted, feedback_submitted_at, hours_remaining = result
                return {
                    'token': token,
                    'created_at': created_at,
                    'expires_at': expires_at,
                    'is_used': is_used,
                    'used_at': used_at,
                    'feedback_submitted': feedback_submitted,
                    'feedback_submitted_at': feedback_submitted_at,
                    'hours_remaining': int(hours_remaining) if hours_remaining else 0
                }
            return None

        except Exception as e:
            logger.error(f"获取令牌信息异常: {str(e)}")
            return None

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> Tuple[bool, int]:
        """
        清理过期的令牌

        Args:
            db: 数据库连接

        Returns:
            (success, deleted_count)
        """
        try:
            result = db.execute(
                text("SELECT cleanup_expired_feedback_tokens()")
            ).first()

            if result:
                deleted_count, message = result[0]
                logger.info(f"清理过期令牌: {message}")
                return True, deleted_count
            return False, 0

        except Exception as e:
            logger.error(f"清理过期令牌异常: {str(e)}")
            return False, 0
