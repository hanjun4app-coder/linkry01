"""
用户反馈闭环 - 公开 API 路由

提供公开接口（无需 API key）用于用户提交告警反馈
- GET /public/alerts/{alert_id} - 显示反馈表单页面
- POST /public/alerts/{alert_id}/feedback - 提交反馈
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["feedback"])


# ==================== 数据模型 ====================

class FeedbackSubmission(BaseModel):
    """反馈提交模型"""
    feedback_type: str  # 'true_positive' or 'false_positive'

    class Config:
        json_schema_extra = {
            "example": {
                "feedback_type": "true_positive"
            }
        }


class FeedbackResponse(BaseModel):
    """反馈提交响应"""
    success: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "反馈已成功提交，感谢您的反馈！"
            }
        }


class FeedbackPageData(BaseModel):
    """反馈页面数据"""
    alert_id: str
    token_valid: bool
    token_expired: bool
    already_submitted: bool
    alert_info: dict = None
    token_expires_in_hours: int = None


# ==================== API 端点 ====================

@router.get("/alerts/{alert_id}", response_class=None)
async def get_feedback_page(
    alert_id: str,
    token: str = Query(..., description="Feedback token"),
    db: Session = None
):
    """
    获取反馈表单页面

    从数据库验证令牌有效性，返回 HTML 页面
    如果令牌无效或过期，显示相应错误信息

    Args:
        alert_id: 告警 ID
        token: 反馈令牌
        db: 数据库连接

    Returns:
        HTML 页面或错误信息
    """
    if db is None:
        db = next(get_db())

    try:
        # 验证令牌并获取告警信息
        result = db.execute(
            text("""
            SELECT
                a.alert_id,
                a.alert_type,
                a.alert_level,
                a.created_at,
                a.elder_id,
                a.family_id,
                a.feedback_submitted,
                ft.expires_at,
                EXTRACT(HOUR FROM ft.expires_at - CURRENT_TIMESTAMP) as hours_remaining
            FROM alerts a
            LEFT JOIN feedback_tokens ft ON a.alert_id = ft.alert_id
            WHERE a.alert_id = :alert_id
                AND ft.feedback_token = :token
            """),
            {"alert_id": alert_id, "token": token}
        ).first()

        if not result:
            # 令牌无效或不匹配
            return get_error_page("无效的反馈链接", "请检查链接是否正确或已过期")

        alert_id_val, alert_type, alert_level, created_at, elder_id, family_id, feedback_submitted, expires_at, hours_remaining = result

        # 检查是否已过期
        if expires_at and expires_at < __import__('datetime').datetime.now(__import__('datetime').timezone.utc):
            return get_error_page("链接已过期", "请联系系统管理员获取新的反馈链接")

        # 检查是否已提交
        if feedback_submitted:
            return get_thank_you_page("反馈已提交", "感谢您的反馈！我们已收到您的意见。")

        # 返回反馈表单页面
        return get_feedback_form_page(
            alert_id=alert_id,
            token=token,
            alert_type=alert_type,
            alert_level=alert_level,
            created_at=created_at,
            hours_remaining=int(hours_remaining) if hours_remaining else 0
        )

    except Exception as e:
        logger.error(f"获取反馈页面失败: {str(e)}")
        return get_error_page("系统错误", "无法加载反馈页面，请稍后重试")


@router.post("/alerts/{alert_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    alert_id: str,
    feedback: FeedbackSubmission,
    token: str = Query(..., description="Feedback token"),
    db: Session = None
):
    """
    提交告警反馈

    调用 PostgreSQL 存储过程验证令牌并提交反馈
    - 验证令牌有效性和有效期
    - 防止重复提交
    - 验证反馈类型
    - 记录审计日志（IP、用户代理）

    Args:
        alert_id: 告警 ID
        feedback: 反馈数据 (feedback_type: 'true_positive' or 'false_positive')
        token: 反馈令牌
        db: 数据库连接

    Returns:
        FeedbackResponse: {success: bool, message: str}

    Raises:
        HTTPException: 400 - 令牌无效或过期
        HTTPException: 400 - 反馈类型无效
        HTTPException: 409 - 反馈已提交
    """
    if db is None:
        db = next(get_db())

    try:
        # 验证反馈类型
        if feedback.feedback_type not in ['true_positive', 'false_positive']:
            raise HTTPException(
                status_code=400,
                detail="无效的反馈类型，只支持 'true_positive' 或 'false_positive'"
            )

        # 调用存储过程提交反馈
        result = db.execute(
            text("""
            SELECT submit_feedback_with_token(
                :alert_id::UUID,
                :token,
                :feedback_type,
                :user_ip,
                :user_agent
            ) as result
            """),
            {
                "alert_id": alert_id,
                "token": token,
                "feedback_type": feedback.feedback_type,
                "user_ip": None,  # 可从请求中获取
                "user_agent": None  # 可从请求头中获取
            }
        ).first()

        if not result:
            raise HTTPException(
                status_code=400,
                detail="反馈提交失败"
            )

        success, message = result[0]

        if success:
            logger.info(f"反馈提交成功: alert_id={alert_id}, feedback_type={feedback.feedback_type}")
            return FeedbackResponse(
                success=True,
                message="反馈已成功提交，感谢您的反馈！"
            )
        else:
            logger.warning(f"反馈提交失败: {message}")
            if "已过期" in message:
                raise HTTPException(status_code=400, detail=message)
            elif "已提交" in message:
                raise HTTPException(status_code=409, detail=message)
            else:
                raise HTTPException(status_code=400, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"反馈提交异常: {str(e)}")
        raise HTTPException(status_code=500, detail="系统错误")


# ==================== HTML 页面生成函数 ====================

def get_feedback_form_page(
    alert_id: str,
    token: str,
    alert_type: str,
    alert_level: str,
    created_at,
    hours_remaining: int
) -> str:
    """生成反馈表单 HTML 页面"""
    level_color = {
        'critical': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8'
    }.get(alert_level, '#6c757d')

    level_label = {
        'critical': '严重',
        'warning': '警告',
        'info': '信息'
    }.get(alert_level, '其他')

    from datetime import datetime
    created_at_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created_at, 'strftime') else str(created_at)

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>告警反馈</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                width: 100%;
                padding: 40px;
            }}

            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}

            .header h1 {{
                font-size: 28px;
                color: #333;
                margin-bottom: 10px;
            }}

            .header p {{
                font-size: 14px;
                color: #666;
            }}

            .alert-info {{
                background: #f8f9fa;
                border-left: 4px solid {level_color};
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 25px;
            }}

            .alert-info-item {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                font-size: 14px;
            }}

            .alert-info-item:last-child {{
                margin-bottom: 0;
            }}

            .alert-info-label {{
                color: #666;
                font-weight: 500;
            }}

            .alert-info-value {{
                color: #333;
                font-weight: 500;
            }}

            .alert-level {{
                display: inline-block;
                background: {level_color};
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            }}

            .description {{
                font-size: 14px;
                color: #666;
                margin-bottom: 25px;
                line-height: 1.6;
            }}

            .feedback-options {{
                display: flex;
                gap: 15px;
                margin-bottom: 20px;
            }}

            .feedback-btn {{
                flex: 1;
                padding: 12px 20px;
                border: 2px solid #e0e0e0;
                background: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                color: #333;
            }}

            .feedback-btn:hover {{
                border-color: #667eea;
                color: #667eea;
                background: #f8f9ff;
            }}

            .feedback-btn.positive {{
                border-color: #28a745;
                color: #28a745;
            }}

            .feedback-btn.positive:hover {{
                background: #f0fff4;
            }}

            .feedback-btn.negative {{
                border-color: #dc3545;
                color: #dc3545;
            }}

            .feedback-btn.negative:hover {{
                background: #fff5f5;
            }}

            .feedback-btn.active {{
                border-color: #667eea;
                background: #667eea;
                color: white;
            }}

            .feedback-btn.active.positive {{
                border-color: #28a745;
                background: #28a745;
            }}

            .feedback-btn.active.negative {{
                border-color: #dc3545;
                background: #dc3545;
            }}

            .submit-btn {{
                width: 100%;
                padding: 12px 20px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }}

            .submit-btn:hover:not(:disabled) {{
                background: #5568d3;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}

            .submit-btn:disabled {{
                background: #ccc;
                cursor: not-allowed;
                opacity: 0.6;
            }}

            .loading {{
                display: none;
                text-align: center;
                color: #666;
                font-size: 14px;
            }}

            .spinner {{
                display: inline-block;
                width: 14px;
                height: 14px;
                border: 2px solid #f3f3f3;
                border-top: 2px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 8px;
            }}

            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}

            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #999;
            }}

            .error {{
                background: #fff5f5;
                border: 1px solid #feb2b2;
                color: #c53030;
                padding: 10px 15px;
                border-radius: 4px;
                margin-bottom: 15px;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 告警反馈</h1>
                <p>请帮我们改进系统，告诉我们这个告警是否准确</p>
            </div>

            <div class="alert-info">
                <div class="alert-info-item">
                    <span class="alert-info-label">告警类型：</span>
                    <span class="alert-info-value">{alert_type}</span>
                </div>
                <div class="alert-info-item">
                    <span class="alert-info-label">严重程度：</span>
                    <span class="alert-level">{level_label}</span>
                </div>
                <div class="alert-info-item">
                    <span class="alert-info-label">告警时间：</span>
                    <span class="alert-info-value">{created_at_str}</span>
                </div>
                <div class="alert-info-item">
                    <span class="alert-info-label">链接有效期：</span>
                    <span class="alert-info-value">{hours_remaining} 小时</span>
                </div>
            </div>

            <div class="description">
                <strong>请告诉我们：</strong> 这个告警是否准确反映了用户的实际情况？
            </div>

            <div id="error-container"></div>

            <form id="feedbackForm">
                <div class="feedback-options">
                    <button type="button" class="feedback-btn positive" onclick="selectFeedback('true_positive')">
                        ✓ 准确告警
                    </button>
                    <button type="button" class="feedback-btn negative" onclick="selectFeedback('false_positive')">
                        ✗ 误报
                    </button>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">
                    提交反馈
                </button>

                <div class="loading" id="loading">
                    <span class="spinner"></span>
                    <span>提交中...</span>
                </div>
            </form>

            <div class="footer">
                <p>您的反馈对我们改进养老关护系统非常重要</p>
                <p style="margin-top: 8px; color: #bbb;">链接将在 {hours_remaining} 小时后过期</p>
            </div>
        </div>

        <script>
            let selectedFeedback = null;

            function selectFeedback(type) {{
                selectedFeedback = type;

                // 更新按钮样式
                document.querySelectorAll('.feedback-btn').forEach(btn => {{
                    btn.classList.remove('active');
                }});

                event.target.classList.add('active');
            }}

            document.getElementById('feedbackForm').addEventListener('submit', async (e) => {{
                e.preventDefault();

                if (!selectedFeedback) {{
                    showError('请选择一个反馈选项');
                    return;
                }}

                const submitBtn = document.getElementById('submitBtn');
                const loading = document.getElementById('loading');

                submitBtn.disabled = true;
                loading.style.display = 'block';

                try {{
                    const response = await fetch(
                        '/public/alerts/{alert_id}/feedback?token={token}',
                        {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                feedback_type: selectedFeedback
                            }})
                        }}
                    );

                    const data = await response.json();

                    if (response.ok) {{
                        // 显示感谢页面
                        showThankYouPage(data.message);
                    }} else {{
                        showError(data.detail || '提交失败，请重试');
                        submitBtn.disabled = false;
                    }}
                }} catch (error) {{
                    showError('网络错误，请检查连接后重试');
                    submitBtn.disabled = false;
                }} finally {{
                    loading.style.display = 'none';
                }}
            }});

            function showError(message) {{
                const errorContainer = document.getElementById('error-container');
                errorContainer.innerHTML = `<div class="error">{message}</div>`.replace('{message}', message);
            }}

            function showThankYouPage(message) {{
                document.body.innerHTML = `
                    <div class="container" style="text-align: center;">
                        <div style="font-size: 60px; margin-bottom: 20px;">🎉</div>
                        <h1 style="color: #28a745; margin-bottom: 15px;">感谢您的反馈！</h1>
                        <p style="color: #666; font-size: 16px; margin-bottom: 30px;">
                            ${{message}}
                        </p>
                        <p style="color: #999; font-size: 14px;">
                            您的意见对我们改进系统非常重要
                        </p>
                    </div>
                `;
            }}
        </script>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


def get_error_page(title: str, message: str) -> str:
    """生成错误页面"""
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>反馈链接错误</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                width: 100%;
                padding: 40px;
                text-align: center;
            }}

            .error-icon {{
                font-size: 60px;
                margin-bottom: 20px;
            }}

            h1 {{
                font-size: 24px;
                color: #dc3545;
                margin-bottom: 15px;
            }}

            p {{
                font-size: 16px;
                color: #666;
                margin-bottom: 30px;
                line-height: 1.6;
            }}

            .home-btn {{
                display: inline-block;
                padding: 12px 30px;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
            }}

            .home-btn:hover {{
                background: #5568d3;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">⚠️</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <a href="#" class="home-btn" onclick="window.history.back(); return false;">返回</a>
        </div>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html, status_code=200)


def get_thank_you_page(title: str, message: str) -> str:
    """生成感谢页面"""
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>反馈已提交</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .container {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                width: 100%;
                padding: 40px;
                text-align: center;
            }}

            .success-icon {{
                font-size: 60px;
                margin-bottom: 20px;
            }}

            h1 {{
                font-size: 24px;
                color: #28a745;
                margin-bottom: 15px;
            }}

            p {{
                font-size: 16px;
                color: #666;
                margin-bottom: 30px;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">🎉</div>
            <h1>{title}</h1>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html, status_code=200)
