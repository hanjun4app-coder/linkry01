"""
Abstract interface for voice confirmation systems.

This interface allows pluggable implementations for different voice platforms:
- Google Home
- Amazon Alexa
- Generic voice devices via WebRTC
- Custom voice systems

The interface separates safety logic (this service) from platform-specific
implementation details.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VoicePromptConfig:
    """Configuration for a voice prompt request."""

    elder_id: str
    alert_type: str
    alert_description: str
    max_attempts: int
    timeout_seconds: int
    confirmation_required: bool = True


@dataclass
class VoiceResponse:
    """Raw response from voice device."""

    response_text: str
    confidence: float  # 0.0-1.0 confidence in transcription accuracy
    duration_seconds: float
    device_id: str
    timestamp: str
    noise_level: Optional[str] = None  # "quiet", "moderate", "loud"


class VoiceConfirmationInterface(ABC):
    """
    Abstract base class for voice confirmation implementations.

    Implementations must:
    1. Reliably trigger voice prompts on elderly person's device
    2. Handle device offline scenarios
    3. Return accurate speech-to-text transcriptions
    4. Report confidence scores for speech recognition
    5. Support configurable timeouts and attempt limits
    """

    @abstractmethod
    async def trigger_prompt(
        self,
        config: VoicePromptConfig,
    ) -> VoiceResponse:
        """
        Trigger a voice prompt on the elderly person's device.

        Args:
            config: Prompt configuration including alert type and timeout

        Returns:
            VoiceResponse with transcribed text and confidence

        Raises:
            DeviceOfflineError: If device cannot be reached
            PromptTimeoutError: If no response within timeout
            TranscriptionError: If speech-to-text fails
        """
        pass

    @abstractmethod
    async def is_device_available(self, elder_id: str) -> bool:
        """
        Check if voice device is available and responding.

        Args:
            elder_id: Elder's ID to check device status

        Returns:
            True if device is reachable and online
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        elder_id: str,
        message: str,
    ) -> bool:
        """
        Send text-to-speech message to device (for follow-up after voice confirmation).

        Args:
            elder_id: Elder's ID
            message: Message to speak aloud

        Returns:
            True if message was delivered
        """
        pass


class MockVoiceConfirmation(VoiceConfirmationInterface):
    """
    Mock implementation for testing and development.

    In production, replace with actual device integration
    (Google Home, Alexa, etc.)
    """

    async def trigger_prompt(
        self,
        config: VoicePromptConfig,
    ) -> VoiceResponse:
        """Mock implementation returns simulated response."""
        # In testing: simulate user saying "I'm okay"
        return VoiceResponse(
            response_text="I'm okay",
            confidence=0.95,
            duration_seconds=1.2,
            device_id="mock-device-001",
            timestamp="2026-04-27T12:00:00Z",
            noise_level="quiet",
        )

    async def is_device_available(self, elder_id: str) -> bool:
        """Mock implementation always returns True."""
        return True

    async def send_message(self, elder_id: str, message: str) -> bool:
        """Mock implementation always succeeds."""
        return True
