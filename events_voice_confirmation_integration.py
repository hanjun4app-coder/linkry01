"""
Alert creation workflow with voice confirmation integration.

This module shows how to integrate voice confirmation into the existing
alert creation flow in app/routes/events.py

Key changes:
1. After rule evaluation, check eligibility for voice confirmation
2. Trigger voice confirmation asynchronously (don't block alert creation)
3. Update alert with voice result when ready
4. Route SMS based on voice outcome
5. Log all attempts in audit trail for compliance
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, Event, VoiceConfirmationAudit
from app.rules import BaselineAwareRuleEngine
from app.services.voice_confirmation_service import (
    VoiceConfirmationService,
    VoiceConfirmationStatus,
)
from app.services.alert_filter_service import AlertFilterService
from app.services.twilio_service import TwilioService
from app.services.baseline_service import BaselineService
from app.services.delta_service import DeltaCalculator


class AlertCreationWithVoiceConfirmation:
    """
    Alert creation flow with voice confirmation integration.

    Workflow:
    1. Create event from sensor data
    2. Evaluate rules using BaselineAwareRuleEngine
    3. Create initial Alert record
    4. Check eligibility for voice confirmation
    5. If eligible: trigger voice async, create placeholder, return immediately
    6. Voice service processes independently: updates alert, logs audit entry, decides SMS
    7. If not eligible: send SMS immediately
    """

    def __init__(
        self,
        rule_engine: BaselineAwareRuleEngine,
        voice_service: VoiceConfirmationService,
        twilio_service: TwilioService,
        alert_filter_service: AlertFilterService,
        baseline_service: BaselineService,
    ):
        self.rule_engine = rule_engine
        self.voice_service = voice_service
        self.twilio_service = twilio_service
        self.alert_filter_service = alert_filter_service
        self.baseline_service = baseline_service

    async def create_alert(
        self,
        db: AsyncSession,
        family_id: int,
        elder_id: str,
        event_type: str,
        event_value: float,
    ) -> Optional[Alert]:
        """
        Create alert with optional voice confirmation.

        Flow:
        1. Record event
        2. Calculate baseline and deltas
        3. Evaluate rules → get alerts
        4. For each alert:
           a. Create Alert record (voice_status=pending if eligible)
           b. Check voice eligibility
           c. If eligible: trigger voice async, return
           d. If not eligible: send SMS immediately
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

        # Step 2: Calculate baseline for decision logic
        baseline = await self.baseline_service.calculate_baseline(
            db, family_id, elder_id
        )

        # Step 3: Evaluate rules
        alerts_to_create = self.rule_engine.evaluate_event(
            event=event,
            baseline=baseline,
        )

        if not alerts_to_create:
            await db.commit()
            return None

        # Step 4: Process each alert
        for alert_spec in alerts_to_create:
            alert = Alert(
                family_id=family_id,
                elder_id=elder_id,
                alert_type=alert_spec["type"],
                alert_level=alert_spec["level"],
                message=alert_spec["message"],
                triggered_by_event_id=event.id,
                voice_confirmation_status=None,  # Will be set if eligible
                voice_confirmation_attempted_at=None,
            )
            db.add(alert)
            await db.flush()

            # Step 5: Check voice eligibility
            should_attempt_voice, reason = (
                await self.voice_service.should_attempt_voice_confirmation(
                    alert_type=alert_spec["type"],
                    alert_level=alert_spec["level"],
                    elder_id=elder_id,
                    db=db,
                )
            )

            if should_attempt_voice:
                # Step 6a: Trigger voice confirmation asynchronously
                # Don't wait for response - let it happen in background
                alert.voice_confirmation_status = VoiceConfirmationStatus.PENDING
                alert.voice_confirmation_attempted_at = datetime.utcnow()
                await db.commit()

                # Trigger async task (using background task queue or asyncio.create_task)
                asyncio.create_task(
                    self._handle_voice_confirmation(
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
                # Step 6b: Not eligible - send SMS immediately
                await self._send_alert_sms(
                    db=db,
                    family_id=family_id,
                    elder_id=elder_id,
                    alert=alert,
                    ineligibility_reason=reason,
                )
                await db.commit()
                return alert

        await db.commit()
        return None

    async def _handle_voice_confirmation(
        self,
        db: AsyncSession,
        alert_id: int,
        family_id: int,
        elder_id: str,
        alert_type: str,
        alert_level: str,
        alert_description: str,
    ) -> None:
        """
        Handle voice confirmation asynchronously.

        This runs in background after alert is created. It:
        1. Triggers voice confirmation flow
        2. Updates alert with result
        3. Logs audit entry
        4. Sends SMS if needed
        """

        try:
            # Perform voice confirmation
            result = await self.voice_service.perform_voice_confirmation(
                elder_id=elder_id,
                alert_type=alert_type,
                alert_level=alert_level,
                alert_description=alert_description,
            )

            # Update alert with result
            alert = await db.get(Alert, alert_id)
            if alert:
                alert.voice_confirmation_status = result.status
                alert.voice_confirmation_response_text = result.response_text
                alert.voice_confirmation_confidence = result.confidence

                # Log audit entry
                audit = VoiceConfirmationAudit(
                    family_id=family_id,
                    elder_id=elder_id,
                    alert_id=alert_id,
                    alert_type=alert_type,
                    alert_level=alert_level,
                    attempt_number=result.attempts_made,
                    status=result.status,
                    response_text=result.response_text,
                    response_confidence=result.confidence,
                    attempted_at=result.attempted_at,
                )
                db.add(audit)

                # Decide on SMS based on voice outcome
                if result.should_notify_family:
                    await self._send_alert_sms(
                        db=db,
                        family_id=family_id,
                        elder_id=elder_id,
                        alert=alert,
                        voice_message=result.family_message,
                    )

                await db.commit()

        except Exception as e:
            # Log error and still notify family
            print(f"Voice confirmation failed for alert {alert_id}: {e}")
            alert = await db.get(Alert, alert_id)
            if alert:
                alert.voice_confirmation_status = VoiceConfirmationStatus.FAILED
                await db.commit()
                await self._send_alert_sms(
                    db=db,
                    family_id=family_id,
                    elder_id=elder_id,
                    alert=alert,
                    voice_message="Voice check system error - please check on Mom",
                )

    async def _send_alert_sms(
        self,
        db: AsyncSession,
        family_id: int,
        elder_id: str,
        alert: Alert,
        ineligibility_reason: Optional[str] = None,
        voice_message: Optional[str] = None,
    ) -> None:
        """
        Send SMS notification based on alert and voice outcome.

        Args:
            db: Database session
            family_id: Family ID
            elder_id: Elder ID
            alert: Alert record
            ineligibility_reason: Why voice wasn't attempted (for logging)
            voice_message: Message from voice confirmation result
        """

        # Check if SMS should be sent based on sensitivity
        if not self.alert_filter_service.should_send_sms(
            alert_type=alert.alert_type,
            alert_level=alert.alert_level,
            family_id=family_id,
            db=db,
        ):
            return

        # Build SMS message
        if voice_message:
            message = voice_message
        else:
            message = self.twilio_service.get_alert_message(
                alert_type=alert.alert_type,
                elder_id=elder_id,
            )

        # Send SMS
        try:
            await self.twilio_service.send_sms(
                family_id=family_id,
                message=message,
                alert_id=alert.id,
            )
        except Exception as e:
            print(f"SMS send failed for alert {alert.id}: {e}")


# Example usage in FastAPI route:

example_route = """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db

router = APIRouter()

@router.post("/api/events")
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    # Initialize services
    voice_service = VoiceConfirmationService(voice_device)
    twilio_service = TwilioService()
    alert_filter_service = AlertFilterService()
    baseline_service = BaselineService()
    rule_engine = BaselineAwareRuleEngine()

    # Create alert with voice confirmation handling
    alert_creator = AlertCreationWithVoiceConfirmation(
        rule_engine=rule_engine,
        voice_service=voice_service,
        twilio_service=twilio_service,
        alert_filter_service=alert_filter_service,
        baseline_service=baseline_service,
    )

    alert = await alert_creator.create_alert(
        db=db,
        family_id=event_data.family_id,
        elder_id=event_data.elder_id,
        event_type=event_data.event_type,
        event_value=event_data.event_value,
    )

    if alert:
        return {
            "status": "alert_created",
            "alert_id": alert.id,
            "voice_confirmation": alert.voice_confirmation_status or "not_attempted",
        }
    else:
        return {"status": "no_alert_triggered"}
"""
