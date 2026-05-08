"""Email service for password setup and notifications"""
import logging
from datetime import datetime
import smtplib
from html import escape
from email.utils import parseaddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _is_configured(value: str) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    return normalized not in {
        "your_email@gmail.com",
        "your_app_password",
        "your_mailgun_api_key",
        "mg.example.com",
        "safehome <support@example.com>",
        "alerts@elderly-care.com",
        "safehome <your_email@gmail.com>",
    }


def _smtp_config():
    host = settings.SMTP_HOST or settings.SMTP_SERVER
    user = settings.SMTP_USER or settings.SMTP_USERNAME
    password = settings.SMTP_APP_PASSWORD or settings.SMTP_PASSWORD
    from_header = settings.SMTP_FROM or user
    from_email = parseaddr(from_header)[1] or user
    is_ready = all([
        _is_configured(host),
        settings.SMTP_PORT,
        _is_configured(user),
        _is_configured(password),
        _is_configured(from_header),
    ])
    return {
        "host": host,
        "port": settings.SMTP_PORT,
        "user": user,
        "password": password,
        "from_header": from_header,
        "from_email": from_email,
        "is_ready": is_ready,
    }


def _mailgun_config():
    is_ready = all([
        _is_configured(settings.MAILGUN_API_KEY),
        _is_configured(settings.MAILGUN_DOMAIN),
        _is_configured(settings.MAILGUN_FROM),
    ])
    return {
        "api_key": settings.MAILGUN_API_KEY,
        "domain": settings.MAILGUN_DOMAIN,
        "from_email": settings.MAILGUN_FROM,
        "is_ready": is_ready,
    }


def _log_invitation_email(to_email: str, subject: str, text_body: str, setup_link: str):
    logger.info("[EMAIL INVITATION] To: %s", to_email)
    logger.info("[EMAIL INVITATION] Subject: %s", subject)
    logger.info("[EMAIL INVITATION] Body:\n%s", text_body.strip())
    return {
        "sent": False,
        "logged": True,
        "email_sent": False,
        "email_logged": True,
        "email": to_email,
        "setup_link": setup_link,
    }


def _send_mailgun_email(to_email: str, subject: str, text_body: str, html_body: str):
    mailgun = _mailgun_config()
    if not mailgun["is_ready"]:
        return None

    domain = mailgun["domain"].replace("https://", "").replace("http://", "").strip("/")
    url = f"https://api.mailgun.net/v3/{domain}/messages"
    try:
        response = httpx.post(
            url,
            auth=("api", mailgun["api_key"]),
            data={
                "from": mailgun["from_email"],
                "to": to_email,
                "subject": subject,
                "text": text_body,
                "html": html_body,
            },
            timeout=15,
        )
        response.raise_for_status()
        logger.info("[EMAIL] Sent message '%s' to %s via Mailgun domain %s", subject, to_email, domain)
        return {
            "sent": True,
            "logged": False,
            "email_sent": True,
            "email_logged": False,
            "email": to_email,
            "provider": "mailgun",
        }
    except Exception as exc:
        logger.error(
            "[EMAIL] Mailgun send failed for message '%s' to %s via domain %s: %s",
            subject,
            to_email,
            domain,
            exc.__class__.__name__,
        )
        return {
            "sent": False,
            "logged": False,
            "email_sent": False,
            "email_logged": False,
            "email": to_email,
            "provider": "mailgun",
        }


def send_account_invitation_email(to_email: str, setup_link: str):
    """Send SafeHome account invitation email.

    MVP behavior:
    - If SMTP settings are missing, log the email content and setup link.
    - Never includes or logs a plain text password.
    """

    subject = "Welcome to SafeHome"
    safe_to_email = escape(to_email)
    safe_setup_link = escape(setup_link, quote=True)
    text_body = f"""
Hi,

Thank you for signing up for SafeHome.

Your account has been created.

Login email:
{to_email}

Please set your password using the secure link below:
{setup_link}

This link expires in 24 hours.

After setting your password, you can sign in to view your loved one's home safety status.

Need help?
Contact support@linkrytech.com.
"""

    html_body = f"""
    <html>
        <body style="margin: 0; padding: 0; background: #f7f9fc; font-family: Arial, sans-serif; line-height: 1.6; color: #172033;">
            <div style="max-width: 560px; margin: 0 auto; padding: 32px 20px;">
            <div style="background: #ffffff; border: 1px solid #e3e8f0; border-radius: 12px; padding: 28px;">
            <h2 style="margin: 0 0 16px; color: #0b1220;">Welcome to SafeHome</h2>
            <p>Hi,</p>
            <p>Thank you for signing up for SafeHome.</p>
            <p>Your account has been created.</p>
            <p>Login email:<br><strong>{safe_to_email}</strong></p>
            <p>Set your password:</p>
            <p style="margin: 24px 0;">
                <a href="{safe_setup_link}"
                   style="background: #0a84ff; color: #ffffff; display: inline-block; font-weight: 700; padding: 12px 20px; text-decoration: none; border-radius: 8px;">
                    Set Password
                </a>
            </p>
            <p style="color: #566174; font-size: 14px;">If the button does not work, copy and paste this link into your browser:<br>
                <a href="{safe_setup_link}" style="color: #0066cc; word-break: break-all;">{safe_setup_link}</a>
            </p>
            <p>This link expires in 24 hours.</p>
            <p>After setting your password, you can sign in to view your loved one's home safety status.</p>
            <p>Need help?<br>Contact support@linkrytech.com.</p>
            </div>
            </div>
        </body>
    </html>
    """

    smtp = _smtp_config()
    mailgun_result = _send_mailgun_email(to_email, subject, text_body, html_body)
    if mailgun_result:
        if mailgun_result["sent"]:
            return mailgun_result
        return _log_invitation_email(to_email, subject, text_body, setup_link)

    if not smtp["is_ready"]:
        return _log_invitation_email(to_email, subject, text_body, setup_link)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = smtp["from_header"]
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp["host"], smtp["port"], timeout=15) as server:
            server.starttls()
            server.login(smtp["user"], smtp["password"])
            server.sendmail(smtp["from_email"], to_email, message.as_string())

        logger.info("[EMAIL INVITATION] Sent account invitation to %s via %s", to_email, smtp["host"])
        return {
            "sent": True,
            "logged": False,
            "email_sent": True,
            "email_logged": False,
            "email": to_email,
            "provider": "smtp",
        }
    except Exception as exc:
        logger.error(
            "[EMAIL INVITATION] SMTP send failed for %s via %s: %s",
            to_email,
            smtp["host"],
            exc.__class__.__name__,
        )
        return _log_invitation_email(to_email, subject, text_body, setup_link)


def send_internal_registration_completed_email(
    customer_email: str,
    user_id: str = "",
    family_id: str = "",
):
    """Notify the internal team after a customer completes password setup.

    This must never block registration. Callers should treat the result as
    best-effort operational visibility only.
    """

    to_email = settings.INTERNAL_NOTIFICATION_EMAIL
    if not _is_configured(to_email):
        logger.warning("[INTERNAL NOTIFICATION] INTERNAL_NOTIFICATION_EMAIL is not configured; skipping registration notice")
        return {
            "sent": False,
            "skipped": True,
            "reason": "missing_internal_notification_email",
        }

    completed_at = datetime.utcnow().isoformat() + "Z"
    subject = "New SafeHome registration completed"
    safe_customer_email = escape(customer_email or "Unavailable")
    safe_user_id = escape(str(user_id or "Unavailable"))
    safe_family_id = escape(str(family_id or "Unavailable"))
    safe_completed_at = escape(completed_at)

    text_body = f"""
New SafeHome registration completed

Customer email: {customer_email or "Unavailable"}
User ID: {user_id or "Unavailable"}
Family ID: {family_id or "Unavailable"}
Registration completion time: {completed_at}
Source: SafeHome onboarding
"""

    html_body = f"""
    <html>
        <body style="margin: 0; padding: 0; background: #f7f9fc; font-family: Arial, sans-serif; line-height: 1.6; color: #172033;">
            <div style="max-width: 560px; margin: 0 auto; padding: 32px 20px;">
                <div style="background: #ffffff; border: 1px solid #e3e8f0; border-radius: 12px; padding: 28px;">
                    <h2 style="margin: 0 0 16px; color: #0b1220;">New SafeHome registration completed</h2>
                    <p><strong>Customer email:</strong><br>{safe_customer_email}</p>
                    <p><strong>User ID:</strong><br>{safe_user_id}</p>
                    <p><strong>Family ID:</strong><br>{safe_family_id}</p>
                    <p><strong>Registration completion time:</strong><br>{safe_completed_at}</p>
                    <p><strong>Source:</strong><br>SafeHome onboarding</p>
                </div>
            </div>
        </body>
    </html>
    """

    mailgun = _mailgun_config()
    if not mailgun["is_ready"]:
        logger.warning("[INTERNAL NOTIFICATION] Mailgun is not configured; skipping registration notice")
        return {
            "sent": False,
            "skipped": True,
            "reason": "mailgun_not_configured",
        }

    result = _send_mailgun_email(to_email, subject, text_body, html_body)
    if result and result.get("sent"):
        logger.info("[INTERNAL NOTIFICATION] Registration completion notice sent for user_id=%s", user_id or "Unavailable")
        return result

    logger.error("[INTERNAL NOTIFICATION] Registration completion notice failed for user_id=%s", user_id or "Unavailable")
    return result or {
        "sent": False,
        "skipped": False,
        "reason": "mailgun_send_failed",
    }


async def send_password_setup_email(
    email: str,
    setup_url: str,
    elder_name: str,
    preferred_date: str
):
    """Send password setup email to family"""
    
    subject = f"Set Up Your Account for {elder_name}'s Care Monitor"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Welcome to {elder_name}'s Care Monitor</h2>
            
            <p>Hi there,</p>
            
            <p>Your installation is scheduled for <strong>{preferred_date}</strong>.</p>
            
            <p>To access the monitoring dashboard after installation, 
            please set up your account password by clicking the link below:</p>
            
            <p style="margin: 20px 0;">
                <a href="{setup_url}" 
                   style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                   text-decoration: none; border-radius: 4px; display: inline-block;">
                    Set Up Password
                </a>
            </p>
            
            <p>Or copy this link: <br/>
            <code style="background: #f0f0f0; padding: 5px;">{setup_url}</code>
            </p>
            
            <p>This link expires in 24 hours.</p>
            
            <p>Questions? Contact our support team.</p>
            
            <p>Best regards,<br/>
            Care Monitor Team</p>
        </body>
    </html>
    """
    
    # For development, log to console
    logger.info(f"[EMAIL] To: {email}")
    logger.info(f"[EMAIL] Subject: {subject}")
    logger.info(f"[EMAIL] Setup URL: {setup_url}")
    
    # TODO: Replace with actual SMTP service when email is enabled
    # For now, just log it
    
    return {"sent": True, "email": email}
