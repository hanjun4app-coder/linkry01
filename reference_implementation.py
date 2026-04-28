"""
Reference Implementation: Voice Confirmation for Elderly Care Monitoring

This file shows a complete, working example of how to use the voice
confirmation service in an actual FastAPI application.

Key components:
1. Service initialization and dependency injection
2. Alert creation with voice confirmation integration
3. Background task handling
4. SMS routing based on voice outcome
5. API endpoint for viewing voice status
"""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import (
    Alert,
    Event,
    Family,
    VoiceConfirmationAudit,
    VoiceConfirmationStatus,
)
from app.services.voice_confirmation_service import (
    VoiceConfirmationService,
)
from app.services.voice_confirmation_interface import (
    VoiceConfirmationInterface,
    MockVoiceConfirmation,
)
from app.services.alert_filter_service import AlertFilterService
from app.services.twilio_service import TwilioService
from app.services.baseline_service import BaselineService
from app.services.delta_service import DeltaCalculator
from app.rules import BaselineAwareRuleEngine
from app.dependencies import get_db


# ============================================================================
# INITIALIZATION (Do this once at app startup)
# ============================================================================

class AppServices:
    """Singleton container for all services."""

    voice_device: Optional[VoiceConfirmationInterface] = None
    voice_service: Optional[VoiceConfirmationService] = None
    twilio_service: Optional[TwilioService] = None
    alert_filter_service: Optional[AlertFilterService] = None
    baseline_service: Optional[BaselineService] = None
    rule_engine: Optional[BaselineAwareRuleEngine] = None


def init_services():
    """Initialize all services at app startup."""

    # 1. Create voice device implementation
    # In production, replace with actual device:
    # from services.google_home_voice import GoogleHomeVoiceConfirmation
    # AppServices.voice_device = GoogleHomeVoiceConfirmation()
    AppServices.voice_device = MockVoiceConfirmation()

    # 2. Create voice confirmation service
    AppServices.voice_service = VoiceConfirmationService(AppServices.voice_device)

    # 3. Create other services
    AppServices.twilio_service = TwilioService()
    AppServices.alert_filter_service = AlertFilterService()
    AppServices.baseline_service = BaselineService()
    AppServices.rule_engine = BaselineAwareRuleEngine()


# ============================================================================
# ALERT CREATION WITH VOICE CONFIRMATION
# ============================================================================

async def create_alert_with_voice(
    db: AsyncSession,
    family_id: int,
    elder_id: str,
    event_type: str,
    event_value: float,
) -> Optional[Alert]:
    """
    Create an alert and optionally trigger voice confirmation.

    This is the main integration point. Call this instead of creating
    alerts directly.

    Flow:
    1. Create event record
    2. Calculate baseline
    3. Evaluate rules
    4. For each alert:
       - Create alert record
       - Check voice eligibility
       - If eligible: trigger voice async, return
       - If not eligible: send SMS, return
    """

    # Step 1: Create event
    event = Event(
        family_id=family_id,
        elder_id=elder_id,
        event_type=event_type,
        event_value=event_value,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    await db.flush()

    # Step 2: Calculate baseline
    baseline = await AppServices.baseline_service.calculate_baseline(
        db, family_id, elder_id
    )

    # Step 3: Evaluate rules
    alerts_to_create = AppServices.rule_engine.evaluate_event(
        event=event,
        baseline=baseline,
    )

    if not alerts_to_create:
        await db.commit()
        return None

    # Step 4: Process first alert (can modify to handle multiple)
    alert_spec = alerts_to_create[0]

    alert = Alert(
        family_id=family_id,
        elder_id=elder_id,
        alert_type=alert_spec["type"],
        alert_level=alert_spec["level"],
        message=alert_spec["message"],
        triggered_by_event_id=event.id,
    )
    db.add(alert)
    await db.flush()

    # Step 5: Determine voice eligibility
    should_attempt, reason = (
        await AppServices.voice_service.should_attempt_voice_confirmation(
            alert_type=alert_spec["type"],
            alert_level=alert_spec["level"],
            elder_id=elder_id,
            db=db,
        )
    )

    if should_attempt:
        # Voice eligible: mark as pending and trigger async
        alert.voice_confirmation_status = VoiceConfirmationStatus.PENDING
        alert.voice_confirmation_attempted_at = datetime.utcnow()
        await db.commit()

        # Trigger background task (don't wait)
        asyncio.create_task(
            _handle_voice_confirmation_background(
                db=db,
                alert_id=alert.id,
                family_id=family_id,
                elder_id=elder_id,
                alert_type=alert_spec["type"],
                alert_level=alert_spec["level"],
                alert_description=alert_spec["message"],
            )
        )
        return alert

    else:
        # Voice not eligible: send SMS immediately
        await _send_alert_sms(
            db=db,
            family_id=family_id,
            alert=alert,
            reason=f"voice_ineligible: {reason}",
        )
        await db.commit()
        return alert


# ============================================================================
# BACKGROUND VOICE CONFIRMATION HANDLER
# ============================================================================

async def _handle_voice_confirmation_background(
    db: AsyncSession,
    alert_id: int,
    family_id: int,
    elder_id: str,
    alert_type: str,
    alert_level: str,
    alert_description: str,
) -> None:
    """
    Handle voice confirmation in background (async, non-blocking).

    This function is called via asyncio.create_task() so it doesn't
    block the alert creation. It:
    1. Performs voice confirmation
    2. Updates alert with result
    3. Logs audit entry
    4. Sends SMS if needed
    """

    try:
        # Perform voice confirmation
        result = await AppServices.voice_service.perform_voice_confirmation(
            elder_id=elder_id,
            alert_type=alert_type,
            alert_level=alert_level,
            alert_description=alert_description,
        )

        # Get fresh database session for background task
        # (original db session may have closed)
        from app.dependencies import get_async_session

        async with get_async_session() as db:
            # Update alert
            alert = await db.get(Alert, alert_id)
            if not alert:
                return

            alert.voice_confirmation_status = result.status
            alert.voice_confirmation_response_text = result.response_text
            alert.voice_confirmation_confidence = result.confidence

            # Create audit entry
            audit = VoiceConfirmationAudit(
                family_id=family_id,
                elder_id=elder_id,
                alert_id=alert_id,
                alert_type=alert_type,
                alert_level=alert_level,
                attempt_number=result.attempts_made,
                status=result.status.value,
                response_text=result.response_text,
                response_confidence=result.confidence,
                attempted_at=result.attempted_at,
            )
            db.add(audit)

            # Route SMS based on voice result
            if result.should_notify_family:
                await _send_alert_sms(
                    db=db,
                    family_id=family_id,
                    alert=alert,
                    voice_message=result.family_message,
                )

            await db.commit()

    except Exception as e:
        # Log error and notify family
        print(f"Voice confirmation error for alert {alert_id}: {e}")

        async with get_async_session() as db:
            alert = await db.get(Alert, alert_id)
            if alert:
                alert.voice_confirmation_status = VoiceConfirmationStatus.FAILED

                audit = VoiceConfirmationAudit(
                    family_id=family_id,
                    elder_id=elder_id,
                    alert_id=alert_id,
                    alert_type=alert.alert_type,
                    alert_level=alert.alert_level,
                    attempt_number=1,
                    status=VoiceConfirmationStatus.FAILED.value,
                    error_message=str(e),
                    attempted_at=datetime.utcnow(),
                )
                db.add(audit)

                await _send_alert_sms(
                    db=db,
                    family_id=family_id,
                    alert=alert,
                    reason="voice_system_error",
                )

                await db.commit()


# ============================================================================
# SMS ROUTING
# ============================================================================

async def _send_alert_sms(
    db: AsyncSession,
    family_id: int,
    alert: Alert,
    reason: Optional[str] = None,
    voice_message: Optional[str] = None,
) -> None:
    """
    Send SMS notification based on alert and voice outcome.

    Args:
        db: Database session
        family_id: Family to notify
        alert: Alert record
        reason: Why we're sending (for logging)
        voice_message: Custom message from voice service
    """

    # Check if SMS should be sent based on family sensitivity
    if not AppServices.alert_filter_service.should_send_sms(
        alert_type=alert.alert_type,
        alert_level=alert.alert_level,
        family_id=family_id,
        db=db,
    ):
        return

    # Determine message
    if voice_message:
        message = voice_message
    else:
        message = AppServices.twilio_service.get_alert_message(
            alert_type=alert.alert_type,
            elder_id=alert.elder_id,
        )

    # Send SMS
    try:
        await AppServices.twilio_service.send_sms(
            family_id=family_id,
            message=message,
            alert_id=alert.id,
        )
    except Exception as e:
        print(f"SMS send failed for alert {alert.id}: {e}")


# ============================================================================
# FASTAPI ROUTES
# ============================================================================

router = APIRouter()


@router.post("/api/events")
async def create_event(
    event_data: dict,  # Replace with your EventCreate pydantic model
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Create event and trigger alert workflow with voice confirmation.

    Request body:
    {
        "event_type": "motion" | "door" | "bathroom" | "activity",
        "event_value": 0.0-1.0,
    }

    Response:
    {
        "status": "alert_created" | "no_alert",
        "alert_id": 12345,
        "voice_confirmation": "pending" | "not_attempted",
    }
    """

    # Verify API key and get family
    family = await db.execute(
        select(Family).where(Family.api_key == x_api_key)
    )
    family = family.scalars().first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Create alert (may trigger voice)
    alert = await create_alert_with_voice(
        db=db,
        family_id=family.id,
        elder_id=family.elder_ids[0],  # For now, single elder
        event_type=event_data["event_type"],
        event_value=event_data["event_value"],
    )

    if alert:
        return {
            "status": "alert_created",
            "alert_id": alert.id,
            "voice_confirmation": alert.voice_confirmation_status or "not_attempted",
        }
    else:
        return {"status": "no_alert"}


@router.get("/api/alerts/{alert_id}/voice-status")
async def get_voice_status(
    alert_id: int,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Get voice confirmation status for an alert.

    Returns details about voice confirmation attempts, responses,
    and outcome.
    """

    # Verify API key
    family = await db.execute(
        select(Family).where(Family.api_key == x_api_key)
    )
    family = family.scalars().first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Get alert with access control
    alert = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.family_id == family.id,
            )
        )
    )
    alert = alert.scalars().first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    # Get audit trail
    audits = await db.execute(
        select(VoiceConfirmationAudit)
        .where(VoiceConfirmationAudit.alert_id == alert_id)
        .order_by(VoiceConfirmationAudit.attempted_at.asc())
    )
    audits = audits.scalars().all()

    # Generate family message
    voice_confirmed = (
        alert.voice_confirmation_status == VoiceConfirmationStatus.CONFIRMED_SAFE
        if alert.voice_confirmation_status
        else False
    )

    status_messages = {
        VoiceConfirmationStatus.PENDING: "Voice confirmation in progress...",
        VoiceConfirmationStatus.CONFIRMED_SAFE: "Mom confirmed she is okay.",
        VoiceConfirmationStatus.UNCLEAR: "Mom didn't clearly respond. Please verify.",
        VoiceConfirmationStatus.NO_RESPONSE: "Mom didn't respond. Please check.",
        VoiceConfirmationStatus.HELP_REQUESTED: "Mom may need help. Call her now.",
        VoiceConfirmationStatus.FAILED: "Voice system error. Contact mom.",
        VoiceConfirmationStatus.DEVICE_ERROR: "Voice device offline.",
    }

    family_message = status_messages.get(
        alert.voice_confirmation_status,
        "Voice confirmation not attempted.",
    )

    return {
        "alert_id": alert.id,
        "alert_type": alert.alert_type,
        "alert_level": alert.alert_level,
        "voice_status": alert.voice_confirmation_status.value
        if alert.voice_confirmation_status
        else None,
        "voice_confirmed": voice_confirmed,
        "family_message": family_message,
        "attempts": [
            {
                "attempt_number": a.attempt_number,
                "status": a.status,
                "response": a.response_text,
                "confidence": a.response_confidence,
                "timestamp": a.attempted_at.isoformat(),
            }
            for a in audits
        ],
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
Usage in main FastAPI app:

from fastapi import FastAPI

app = FastAPI()

# Initialize services on startup
@app.on_event("startup")
async def startup():
    init_services()

# Include routes
app.include_router(router)

# Now when an event is posted:
#
# POST /api/events
# x-api-key: family-api-key-123
# {
#     "event_type": "bathroom",
#     "event_value": 0.95
# }
#
# Response 1 (immediate):
# {
#     "status": "alert_created",
#     "alert_id": 12345,
#     "voice_confirmation": "pending"
# }
#
# Meanwhile, background task is running voice confirmation...
# After 20-30 seconds, voice result is available at:
#
# GET /api/alerts/12345/voice-status
# x-api-key: family-api-key-123
#
# Response 2 (voice completed):
# {
#     "alert_id": 12345,
#     "alert_type": "bathroom_timeout",
#     "voice_status": "confirmed_safe",
#     "voice_confirmed": true,
#     "family_message": "Mom confirmed she is okay.",
#     "attempts": [
#         {
#             "attempt_number": 1,
#             "status": "confirmed_safe",
#             "response": "I'm okay",
#             "confidence": 1.0,
#             "timestamp": "2026-04-27T12:32:15Z"
#         }
#     ]
# }
"""
