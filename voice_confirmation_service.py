"""
Voice confirmation service for elderly care safety alerts.

Safety principle: Voice confirmation reduces false positives, but NEVER proves
safety unless response is explicit and matches exact expected phrases.

Flow:
1. Alert triggered and deemed eligible for voice confirmation
2. Voice prompt sent to elder's device: "Mom, I detected [alert type]. Are you okay?"
3. System waits for response (20s for regular alerts, 10s for critical)
4. Response analyzed for exact phrase matches (English + Chinese)
5. If match: alert cancelled, family notified of confirmation
6. If no match or unclear: re-prompt once (max 2 attempts for regular, 1 for critical)
7. If still no match: notify family immediately - voice confirmation is NOT proof of safety

Eligibility rules (STRICT):
- Only for: bathroom_timeout, inactivity, pattern_deviation, night_activity
- NEVER for: critical_immobility, suspected_fall
- Anti-loop: no voice confirmation for same alert type within 30 minutes
"""

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from voice_confirmation_interface import (
    VoiceConfirmationInterface,
    VoicePromptConfig,
)


class VoiceConfirmationStatus(str, Enum):
    """Status of voice confirmation attempt."""

    PENDING = "pending"  # Voice prompt triggered, waiting for response
    CONFIRMED_SAFE = "confirmed_safe"  # Elder responded with safe phrase
    UNCLEAR = "unclear"  # Response received but didn't match safe phrases
    NO_RESPONSE = "no_response"  # No response after max attempts
    HELP_REQUESTED = "help_requested"  # Elder said help-related words
    FAILED = "failed"  # Voice system error (transcription failed)
    DEVICE_ERROR = "device_error"  # Device offline or unavailable


@dataclass
class VoiceConfirmationResult:
    """Result of voice confirmation attempt."""

    status: VoiceConfirmationStatus
    response_text: Optional[str]
    confidence: float  # 0.0-1.0 confidence in response classification
    attempted_at: datetime
    attempts_made: int
    should_notify_family: bool
    family_message: str  # What to tell family about this alert


class VoiceConfirmationService:
    """
    Service for managing voice confirmation attempts on elderly alerts.

    Design constraints:
    - Regular alerts (bathroom, inactivity, pattern): max 2 voice attempts, 20s timeout
    - Critical alerts (immobility, fall): max 1 attempt, 10s timeout
    - CRITICAL alerts NEVER get voice confirmation - skip to SMS immediately
    - Help requests trigger SMS immediately, no retry
    - All attempts logged for audit trail
    - Anti-loop protection: 30 minute cooldown between same alert type
    """

    # Exact phrases that cancel an alert (case-insensitive)
    SAFE_RESPONSE_PATTERNS = [
        # English phrases
        r"^i\s*['\']m\s*okay$",  # "I'm okay"
        r"^i\s+am\s+okay$",  # "I am okay"
        r"^i\s*['\']m\s*fine$",  # "I'm fine"
        r"^yes\s*,?\s*i\s*['\']m\s*okay$",  # "Yes, I'm okay"
        r"^cancel\s+alert$",  # "Cancel alert"
        # Chinese phrases
        r"^我\s*没\s*事$",  # "我没事" (I'm fine)
        r"^没\s*关\s*系$",  # "没关系" (It's okay)
        r"^我\s*很\s*好$",  # "我很好" (I'm very fine)
    ]

    # Phrases indicating elder needs help (trigger SMS immediately)
    HELP_REQUEST_PATTERNS = [
        # English phrases
        r"help",
        r"emergency",
        r"call\s+(an\s+)?ambulance",
        r"fall",
        r"can\s*['\']t\s+get\s+(up|out)",
        # Chinese phrases
        r"救命",  # Help
        r"紧急",  # Emergency
        r"叫救护车",  # Call ambulance
        r"摔倒",  # Fell
    ]

    # Alert types eligible for voice confirmation
    ELIGIBLE_ALERT_TYPES = {
        "bathroom_timeout",
        "inactivity",
        "pattern_deviation",
        "night_activity",
    }

    # Alert types that NEVER get voice confirmation (critical only)
    CRITICAL_ALERT_TYPES = {
        "critical_immobility",
        "suspected_fall",
    }

    def __init__(self, voice_device: VoiceConfirmationInterface):
        """Initialize with voice device implementation."""
        self.voice_device = voice_device

    async def should_attempt_voice_confirmation(
        self,
        alert_type: str,
        alert_level: str,
        elder_id: str,
        db: AsyncSession,
    ) -> Tuple[bool, str]:
        """
        Determine if this alert is eligible for voice confirmation.

        Returns:
            Tuple of (should_attempt, reason)

        Rules:
        - Never for critical alerts
        - Only for eligible alert types
        - Never if same alert type attempted in last 30 minutes
        - Only if device is available
        """

        # Rule 1: Never for critical alerts
        if alert_level == "critical" or alert_type in self.CRITICAL_ALERT_TYPES:
            return False, "critical_alert_skips_voice"

        # Rule 2: Only for eligible types
        if alert_type not in self.ELIGIBLE_ALERT_TYPES:
            return False, f"ineligible_alert_type_{alert_type}"

        # Rule 3: Anti-loop check - 30 minute cooldown
        from models import Alert

        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        recent_voice_attempt = await db.execute(
            select(Alert).where(
                and_(
                    Alert.elder_id == elder_id,
                    Alert.alert_type == alert_type,
                    Alert.voice_confirmation_attempted_at >= thirty_min_ago,
                    Alert.voice_confirmation_attempted_at.isnot(None),
                )
            )
        )
        if recent_voice_attempt.scalars().first():
            return False, "anti_loop_cooldown_active"

        # Rule 4: Device availability
        device_available = await self.voice_device.is_device_available(elder_id)
        if not device_available:
            return False, "device_offline"

        return True, "eligible_for_voice_confirmation"

    async def perform_voice_confirmation(
        self,
        elder_id: str,
        alert_type: str,
        alert_level: str,
        alert_description: str,
    ) -> VoiceConfirmationResult:
        """
        Execute voice confirmation flow with retry logic.

        State machine:
        1. Determine attempt count (critical: 1, regular: 2)
        2. Trigger voice prompt
        3. Wait for response
        4. Analyze response:
           - Help request? → Return immediately, notify family
           - Safe phrase match? → Return confirmed_safe
           - Unclear or no match? → Retry if attempts remaining
           - Final attempt with no match? → Return no_response, notify family

        Args:
            elder_id: Elder's ID
            alert_type: Type of alert
            alert_level: Alert severity (critical, high, warning, etc.)
            alert_description: Human-readable alert description

        Returns:
            VoiceConfirmationResult with status and decision
        """

        is_critical = alert_level == "critical" or alert_type in self.CRITICAL_ALERT_TYPES
        max_attempts = 1 if is_critical else 2
        timeout_seconds = 10 if is_critical else 20
        attempts_made = 0
        last_response = None

        # Create voice prompt config
        prompt_config = VoicePromptConfig(
            elder_id=elder_id,
            alert_type=alert_type,
            alert_description=alert_description,
            max_attempts=max_attempts,
            timeout_seconds=timeout_seconds,
        )

        # Retry loop
        for attempt in range(1, max_attempts + 1):
            attempts_made = attempt

            try:
                # Trigger voice prompt
                voice_response = await asyncio.wait_for(
                    self.voice_device.trigger_prompt(prompt_config),
                    timeout=timeout_seconds + 5,  # 5s grace period for device latency
                )
                last_response = voice_response

                # Analyze response
                classification, confidence = self._classify_response(
                    voice_response.response_text
                )

                if classification == VoiceConfirmationStatus.HELP_REQUESTED:
                    # Help request - don't retry, notify immediately
                    return VoiceConfirmationResult(
                        status=VoiceConfirmationStatus.HELP_REQUESTED,
                        response_text=voice_response.response_text,
                        confidence=confidence,
                        attempted_at=datetime.fromisoformat(voice_response.timestamp),
                        attempts_made=attempts_made,
                        should_notify_family=True,
                        family_message=f"Mom said '{voice_response.response_text}' - possible help request. Alert: {alert_description}",
                    )

                if classification == VoiceConfirmationStatus.CONFIRMED_SAFE:
                    # Safe response - cancel alert
                    return VoiceConfirmationResult(
                        status=VoiceConfirmationStatus.CONFIRMED_SAFE,
                        response_text=voice_response.response_text,
                        confidence=confidence,
                        attempted_at=datetime.fromisoformat(voice_response.timestamp),
                        attempts_made=attempts_made,
                        should_notify_family=False,
                        family_message=f"Mom confirmed she is okay at {datetime.fromisoformat(voice_response.timestamp).strftime('%I:%M %p')}.",
                    )

                # Unclear response
                if attempt < max_attempts:
                    # Retry with follow-up prompt
                    await asyncio.sleep(2)  # 2 second pause before retry
                    prompt_config.alert_description = (
                        f"{alert_description} (Are you sure you're okay?)"
                    )
                    continue
                else:
                    # Final attempt with no match - notify family
                    return VoiceConfirmationResult(
                        status=VoiceConfirmationStatus.UNCLEAR,
                        response_text=voice_response.response_text,
                        confidence=confidence,
                        attempted_at=datetime.fromisoformat(voice_response.timestamp),
                        attempts_made=attempts_made,
                        should_notify_family=True,
                        family_message=f"Mom didn't clearly respond to safety check. Alert: {alert_description}",
                    )

            except asyncio.TimeoutError:
                # No response within timeout
                if attempt < max_attempts:
                    # Retry
                    await asyncio.sleep(2)
                    prompt_config.alert_description = (
                        f"{alert_description} (Didn't hear you - trying again)"
                    )
                    continue
                else:
                    # Final attempt with timeout - notify family
                    return VoiceConfirmationResult(
                        status=VoiceConfirmationStatus.NO_RESPONSE,
                        response_text=None,
                        confidence=0.0,
                        attempted_at=datetime.utcnow(),
                        attempts_made=attempts_made,
                        should_notify_family=True,
                        family_message=f"Mom didn't respond to safety check. Alert: {alert_description}",
                    )

            except Exception as e:
                # Voice device error
                return VoiceConfirmationResult(
                    status=VoiceConfirmationStatus.FAILED,
                    response_text=str(e),
                    confidence=0.0,
                    attempted_at=datetime.utcnow(),
                    attempts_made=attempts_made,
                    should_notify_family=True,
                    family_message=f"Voice check failed (device error). Alert: {alert_description}",
                )

        # Should not reach here, but fallback to no_response
        return VoiceConfirmationResult(
            status=VoiceConfirmationStatus.NO_RESPONSE,
            response_text=last_response.response_text if last_response else None,
            confidence=0.0 if not last_response else last_response.confidence,
            attempted_at=datetime.utcnow(),
            attempts_made=attempts_made,
            should_notify_family=True,
            family_message=f"Mom didn't respond to safety check. Alert: {alert_description}",
        )

    def _classify_response(
        self,
        response_text: str,
    ) -> Tuple[VoiceConfirmationStatus, float]:
        """
        Classify voice response as safe, help request, or unclear.

        Returns:
            Tuple of (status, confidence)

        Confidence interpretation:
            - 1.0: Exact match to known safe phrase
            - 0.7-0.9: Likely safe based on content (e.g., "OK" without full phrase)
            - 0.3-0.6: Ambiguous (could be acknowledgment or something else)
            - 0.0-0.2: Doesn't match known patterns
        """

        if not response_text or response_text.strip() == "":
            return VoiceConfirmationStatus.NO_RESPONSE, 0.0

        cleaned = response_text.strip().lower()

        # Check for help requests (highest priority)
        for pattern in self.HELP_REQUEST_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return VoiceConfirmationStatus.HELP_REQUESTED, 0.95

        # Check for exact safe phrase matches
        for pattern in self.SAFE_RESPONSE_PATTERNS:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return VoiceConfirmationStatus.CONFIRMED_SAFE, 1.0

        # Check for partial matches that suggest safety (but not exact)
        # These return UNCLEAR so voice system retries
        partial_matches = [
            (r"^okay", 0.6),
            (r"^fine", 0.6),
            (r"^yes", 0.4),
            (r"^ok", 0.5),
        ]
        for pattern, confidence in partial_matches:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return VoiceConfirmationStatus.UNCLEAR, confidence

        # No match found
        return VoiceConfirmationStatus.UNCLEAR, 0.2

    def get_family_message_for_status(
        self,
        result: VoiceConfirmationResult,
    ) -> str:
        """Get family-friendly message about voice confirmation result."""
        return result.family_message
