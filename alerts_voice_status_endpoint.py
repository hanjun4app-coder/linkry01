"""
API endpoint for viewing voice confirmation status.

Route: GET /api/alerts/{alert_id}/voice-status

Allows family members to see details about voice confirmation attempts
for a specific alert, including:
- Overall status (confirmed_safe, unclear, no_response, failed, etc.)
- Number of attempts made
- Confidence score
- Raw transcribed response (for transparency)
- Timestamp of attempts
- Human-friendly message about what happened

This endpoint is family-scoped (can only view own family's alerts).
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.dependencies import get_db, get_family_from_header
from app.models import Alert, VoiceConfirmationAudit


class VoiceConfirmationAttempt(BaseModel):
    """Single voice confirmation attempt details."""

    attempt_number: int
    status: str  # "pending", "confirmed_safe", "unclear", etc.
    response_text: Optional[str]  # What elder actually said
    response_confidence: Optional[float]  # 0.0-1.0 confidence in match
    attempted_at: datetime


class VoiceStatusResponse(BaseModel):
    """Response for voice confirmation status query."""

    alert_id: int
    alert_type: str
    alert_level: str
    alert_message: str

    # Voice confirmation outcome
    voice_status: str  # Status enum
    voice_confirmed: bool  # True only if status == "confirmed_safe"
    family_message: str  # What to show family

    # Timing
    first_attempt_at: Optional[datetime]
    last_attempt_at: Optional[datetime]
    total_attempts: int

    # Attempts history
    attempts: List[VoiceConfirmationAttempt]

    class Config:
        from_attributes = True


router = APIRouter()


@router.get("/api/alerts/{alert_id}/voice-status", response_model=VoiceStatusResponse)
async def get_voice_confirmation_status(
    alert_id: int,
    family_id: int = Depends(get_family_from_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Get voice confirmation status for an alert.

    Args:
        alert_id: Alert ID to query
        family_id: Family ID from x-api-key header
        db: Database session

    Returns:
        VoiceStatusResponse with all voice confirmation details

    Raises:
        404: Alert not found or family doesn't have access
        401: Invalid family_id
    """

    # Fetch alert with access control
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.family_id == family_id,
            )
        )
    )
    alert = result.scalars().first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or access denied",
        )

    # Fetch all voice confirmation attempts for this alert
    audit_result = await db.execute(
        select(VoiceConfirmationAudit)
        .where(VoiceConfirmationAudit.alert_id == alert_id)
        .order_by(VoiceConfirmationAudit.attempted_at.asc())
    )
    audit_entries = audit_result.scalars().all()

    # Build response
    voice_confirmed = (
        alert.voice_confirmation_status == "confirmed_safe"
        if alert.voice_confirmation_status
        else False
    )

    # Generate family-friendly message
    family_message = _get_family_message(
        alert.voice_confirmation_status,
        alert_id,
        alert.alert_type,
        len(audit_entries),
    )

    return VoiceStatusResponse(
        alert_id=alert.id,
        alert_type=alert.alert_type,
        alert_level=alert.alert_level,
        alert_message=alert.message,
        voice_status=alert.voice_confirmation_status or "not_attempted",
        voice_confirmed=voice_confirmed,
        family_message=family_message,
        first_attempt_at=audit_entries[0].attempted_at if audit_entries else None,
        last_attempt_at=audit_entries[-1].attempted_at if audit_entries else None,
        total_attempts=len(audit_entries),
        attempts=[
            VoiceConfirmationAttempt(
                attempt_number=entry.attempt_number,
                status=entry.status,
                response_text=entry.response_text,
                response_confidence=entry.response_confidence,
                attempted_at=entry.attempted_at,
            )
            for entry in audit_entries
        ],
    )


@router.get("/api/alerts/voice-summary")
async def get_voice_summary_for_elder(
    elder_id: str,
    family_id: int = Depends(get_family_from_header),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary of recent voice confirmations for an elder.

    Returns:
    - Total voice confirmations attempted
    - Successful confirmations (elder confirmed safe)
    - Failed confirmations (unclear/no_response)
    - Recent attempts (last 24 hours)

    Useful for dashboard or family summary view.
    """

    from sqlalchemy import func
    from datetime import timedelta

    # Get summary stats
    result = await db.execute(
        select(
            Alert.voice_confirmation_status,
            func.count(Alert.id),
        )
        .where(
            and_(
                Alert.elder_id == elder_id,
                Alert.family_id == family_id,
                Alert.voice_confirmation_status.isnot(None),
            )
        )
        .group_by(Alert.voice_confirmation_status)
    )

    status_counts = dict(result.all())

    # Get recent attempts (last 24 hours)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_result = await db.execute(
        select(
            Alert.alert_type,
            Alert.voice_confirmation_status,
            Alert.voice_confirmation_attempted_at,
        )
        .where(
            and_(
                Alert.elder_id == elder_id,
                Alert.family_id == family_id,
                Alert.voice_confirmation_attempted_at >= twenty_four_hours_ago,
            )
        )
        .order_by(Alert.voice_confirmation_attempted_at.desc())
    )
    recent_attempts = recent_result.all()

    return {
        "elder_id": elder_id,
        "summary": {
            "total_attempted": sum(status_counts.values()),
            "confirmed_safe": status_counts.get("confirmed_safe", 0),
            "unclear": status_counts.get("unclear", 0),
            "no_response": status_counts.get("no_response", 0),
            "failed": status_counts.get("failed", 0),
            "device_error": status_counts.get("device_error", 0),
        },
        "recent_attempts_24h": [
            {
                "alert_type": attempt[0],
                "status": attempt[1],
                "attempted_at": attempt[2].isoformat() if attempt[2] else None,
            }
            for attempt in recent_attempts
        ],
    }


def _get_family_message(
    voice_status: Optional[str],
    alert_id: int,
    alert_type: str,
    attempt_count: int,
) -> str:
    """Generate family-friendly message about voice confirmation outcome."""

    if not voice_status:
        return "Voice confirmation not attempted for this alert."

    status_messages = {
        "pending": "Voice confirmation in progress...",
        "confirmed_safe": f"Mom confirmed she is okay.",
        "unclear": f"Mom didn't clearly respond to the safety check. Please verify she's okay.",
        "no_response": f"Mom didn't respond to the safety check. Please check on her.",
        "help_requested": f"Mom may have requested help. Please call her immediately.",
        "failed": f"Voice check system error. Please contact Mom directly.",
        "device_error": f"Voice device offline. Please contact Mom or emergency services.",
    }

    base_message = status_messages.get(voice_status, "Unknown voice confirmation status")

    # Add context
    if attempt_count > 1:
        base_message += f" (System tried {attempt_count} times)"

    return base_message


# Integration with existing alerts endpoint
# Add this to GET /api/alerts/{alert_id}:

example_enhanced_alert = """
GET /api/alerts/12345

Response now includes:
{
    "id": 12345,
    "alert_type": "bathroom_timeout",
    "alert_level": "warning",
    "message": "Extended bathroom duration detected",
    "triggered_at": "2026-04-27T12:30:00Z",

    // NEW: Voice confirmation details
    "voice_confirmation": {
        "status": "confirmed_safe",
        "confirmed": true,
        "family_message": "Mom confirmed she is okay.",
        "attempts": 1,
        "attempted_at": "2026-04-27T12:32:00Z",
        "response": "I'm okay",
        "confidence": 1.0
    }
}
"""
