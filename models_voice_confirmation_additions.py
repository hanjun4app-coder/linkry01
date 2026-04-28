"""
Voice confirmation field additions to Alert model.

These fields are added to the existing Alert model to support voice-based
safety confirmations for elderly care alerts.

Add these imports to models.py:
    from enum import Enum
    from datetime import datetime
    from sqlalchemy import DateTime, Float, VARCHAR, ENUM
"""

from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, VARCHAR, ENUM as SqlEnum, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import ENUM as PostgreSQLEnum

Base = declarative_base()


class VoiceConfirmationStatus(PyEnum):
    """Status of voice confirmation attempt."""

    PENDING = "pending"  # Voice prompt triggered, waiting for response
    CONFIRMED_SAFE = "confirmed_safe"  # Elder responded with safe phrase
    UNCLEAR = "unclear"  # Response received but didn't match safe phrases
    NO_RESPONSE = "no_response"  # No response after max attempts
    HELP_REQUESTED = "help_requested"  # Elder said help-related words
    FAILED = "failed"  # Voice system error (transcription failed)
    DEVICE_ERROR = "device_error"  # Device offline or unavailable


# Add these columns to the existing Alert model:

# For SQLAlchemy model definition, add to Alert class:
"""
class Alert(Base):
    __tablename__ = 'alert'

    # ... existing columns ...

    # Voice confirmation fields
    voice_confirmation_status: Mapped[Optional[VoiceConfirmationStatus]] = mapped_column(
        PostgreSQLEnum(
            "pending",
            "confirmed_safe",
            "unclear",
            "no_response",
            "help_requested",
            "failed",
            "device_error",
            name="voice_confirmation_status",
        ),
        nullable=True,
        default=None,
        doc="Status of voice confirmation attempt",
    )

    voice_confirmation_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Timestamp when voice confirmation was triggered",
    )

    voice_confirmation_response_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Raw transcribed response from speech-to-text (for audit trail)",
    )

    voice_confirmation_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
        doc="Confidence score 0.0-1.0 for response classification",
    )

    voice_confirmation_device_id: Mapped[Optional[str]] = mapped_column(
        VARCHAR(255),
        nullable=True,
        default=None,
        doc="ID of voice device that handled confirmation",
    )
"""


# New model for voice confirmation audit trail:

"""
class VoiceConfirmationAudit(Base):
    '''Detailed audit trail of voice confirmation attempts.'''

    __tablename__ = 'voice_confirmation_audit'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    family_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('family.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    elder_id: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, index=True)
    alert_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey('alert.id', ondelete='CASCADE'),
        nullable=False,
    )
    alert_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    alert_level: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    attempt_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[VoiceConfirmationStatus] = mapped_column(
        PostgreSQLEnum(
            "pending",
            "confirmed_safe",
            "unclear",
            "no_response",
            "help_requested",
            "failed",
            "device_error",
            name="voice_confirmation_status",
        ),
        nullable=False,
    )

    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationships
    family = relationship('Family', back_populates='voice_audits')
    elder = relationship('Elder', back_populates='voice_audits')
    alert = relationship('Alert', back_populates='voice_audits')
"""


# Example usage in alerts view:

example_query = """
# Get all voice confirmation attempts for an alert
from sqlalchemy import select

alert = await db.get(Alert, alert_id)

# Show all voice attempts for this alert
for audit_entry in alert.voice_audits:
    print(f"Attempt {audit_entry.attempt_number}: {audit_entry.status}")
    print(f"Response: {audit_entry.response_text}")
    print(f"Confidence: {audit_entry.response_confidence}")
    print(f"Time: {audit_entry.attempted_at}")
"""
