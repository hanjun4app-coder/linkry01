"""
Baseline Service with Learning Period Mode (Days 1-7).

Implementation of Fix #2: First 7 days uses conservative static thresholds,
day 8 onward uses learned baseline.

Safety principle: When we don't know the normal pattern, be very conservative
(raise thresholds, suppress non-critical alerts, reduce false positives).
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, Elder, Baseline


@dataclass
class BaselineMode:
    """State of baseline system."""

    mode: str  # "learning" (days 0-7) or "active" (day 8+)
    days_since_install: int  # 0-7+ days
    is_learning_period: bool  # True if days < 7
    baseline: Optional["Baseline"]  # None during learning period
    quality_score: float  # 0.0 if learning, else 0.0-1.0
    conservative_mode: bool  # True if learning OR baseline quality low
    messaging_context: str  # "learning" or "active"


class BaselineServiceWithLearningPeriod:
    """
    Baseline service that respects learning period.

    Days 0-7 (Learning Period):
    - No baseline used
    - Conservative static thresholds
    - Reduce false positives
    - Show "learning" messaging

    Days 8+ (Active Period):
    - Use learned baseline
    - Check baseline quality
    - If quality low: still use conservative thresholds
    - Normal alert logic
    """

    # Conservative thresholds during learning period
    LEARNING_INACTIVITY_THRESHOLD_HOURS = 6  # Not 4 hours
    LEARNING_BATHROOM_THRESHOLD_MINUTES = 45  # Not 30 minutes
    LEARNING_NIGHT_ACTIVITY_THRESHOLD = 10  # Not 5

    # Quality threshold for baseline confidence
    BASELINE_QUALITY_THRESHOLD = 0.5  # 0.0-1.0

    def __init__(self):
        """Initialize baseline service."""
        self.learning_period_days = 7

    async def get_baseline_mode(
        self,
        db: AsyncSession,
        family_id: int,
        elder_id: str,
    ) -> BaselineMode:
        """
        Get baseline state respecting learning period.

        Returns:
            BaselineMode with current state and thresholds to use
        """

        # Step 1: Calculate days since installation
        days_since_install = await self._get_days_since_install(
            db, family_id, elder_id
        )

        # Step 2: Determine if in learning period
        is_learning_period = days_since_install < self.learning_period_days

        if is_learning_period:
            # LEARNING PERIOD: No baseline, conservative thresholds
            return BaselineMode(
                mode="learning",
                days_since_install=days_since_install,
                is_learning_period=True,
                baseline=None,
                quality_score=0.0,
                conservative_mode=True,
                messaging_context="learning",
            )

        # Step 3: Active period - get baseline if available
        baseline = await self._calculate_baseline(db, family_id, elder_id)

        if baseline is None:
            # No baseline data yet (shouldn't happen on day 8+, but be safe)
            return BaselineMode(
                mode="active",
                days_since_install=days_since_install,
                is_learning_period=False,
                baseline=None,
                quality_score=0.0,
                conservative_mode=True,  # Default to conservative
                messaging_context="active_no_baseline",
            )

        # Step 4: Check baseline quality
        if baseline.quality_score < self.BASELINE_QUALITY_THRESHOLD:
            # Low quality baseline - still be conservative
            return BaselineMode(
                mode="active",
                days_since_install=days_since_install,
                is_learning_period=False,
                baseline=baseline,
                quality_score=baseline.quality_score,
                conservative_mode=True,  # Low quality = conservative
                messaging_context="active_low_quality",
            )

        # Step 5: High quality baseline - use normal rules
        return BaselineMode(
            mode="active",
            days_since_install=days_since_install,
            is_learning_period=False,
            baseline=baseline,
            quality_score=baseline.quality_score,
            conservative_mode=False,  # Good quality baseline
            messaging_context="active_normal",
        )

    def get_thresholds_for_mode(
        self,
        baseline_mode: BaselineMode,
    ) -> Dict[str, float]:
        """
        Get alert thresholds based on baseline mode.

        Args:
            baseline_mode: Current baseline state

        Returns:
            Dict with thresholds in minutes/hours
        """

        if baseline_mode.is_learning_period or baseline_mode.conservative_mode:
            # CONSERVATIVE MODE: High thresholds, fewer alerts
            return {
                "inactivity_minutes": self.LEARNING_INACTIVITY_THRESHOLD_HOURS * 60,  # 360 min
                "bathroom_minutes": self.LEARNING_BATHROOM_THRESHOLD_MINUTES,  # 45 min
                "night_activity_count": self.LEARNING_NIGHT_ACTIVITY_THRESHOLD,  # 10
                "wake_time_delta_minutes": 180,  # 3 hours (more lenient)
            }

        else:
            # NORMAL MODE: Use baseline-aware thresholds
            baseline = baseline_mode.baseline

            if not baseline:
                # Fallback to conservative
                return {
                    "inactivity_minutes": self.LEARNING_INACTIVITY_THRESHOLD_HOURS * 60,
                    "bathroom_minutes": self.LEARNING_BATHROOM_THRESHOLD_MINUTES,
                    "night_activity_count": self.LEARNING_NIGHT_ACTIVITY_THRESHOLD,
                    "wake_time_delta_minutes": 180,
                }

            # Baseline-aware: Scale from learned patterns
            return {
                "inactivity_minutes": max(
                    4 * 60,  # At least 4 hours
                    baseline.avg_inactivity_duration_minutes * 1.5,
                ),
                "bathroom_minutes": max(
                    30,
                    baseline.avg_bathroom_duration_minutes * 1.5,
                ),
                "night_activity_count": max(
                    5,
                    baseline.avg_night_activity_count * 2.0,
                ),
                "wake_time_delta_minutes": 120,  # 2 hours
            }

    def get_messaging_for_mode(
        self,
        baseline_mode: BaselineMode,
    ) -> Dict[str, str]:
        """
        Get appropriate messaging for current mode.

        Args:
            baseline_mode: Current baseline state

        Returns:
            Dict with status and user-visible message
        """

        if baseline_mode.is_learning_period:
            days_left = self.learning_period_days - baseline_mode.days_since_install
            return {
                "status": "learning",
                "mode_indicator": f"Learning mode (Day {baseline_mode.days_since_install + 1}/7)",
                "message": (
                    f"System is learning daily patterns. "
                    f"Check back in {days_left} days for personalized alerts. "
                    f"Basic monitoring is active."
                ),
                "alert_style": "informational",  # No alarming messages
            }

        elif baseline_mode.conservative_mode:
            return {
                "status": "active_conservative",
                "mode_indicator": "Cautious monitoring",
                "message": (
                    "System is monitoring with careful thresholds. "
                    "Fewer alerts until we better understand daily patterns."
                ),
                "alert_style": "informational",
            }

        else:
            return {
                "status": "active_normal",
                "mode_indicator": "Personalized monitoring",
                "message": "System monitoring active with personalized thresholds.",
                "alert_style": "normal",
            }

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    async def _get_days_since_install(
        self,
        db: AsyncSession,
        family_id: int,
        elder_id: str,
    ) -> int:
        """
        Calculate days since first event for this elder.

        Args:
            db: Database session
            family_id: Family ID
            elder_id: Elder ID

        Returns:
            Number of days since first event (0 on day 1)
        """

        # Query first event
        result = await db.execute(
            select(func.min(Event.created_at)).where(
                (Event.family_id == family_id) & (Event.elder_id == elder_id)
            )
        )
        first_event_date = result.scalar()

        if not first_event_date:
            # No events yet
            return 0

        # Calculate days since first event
        days = (datetime.utcnow() - first_event_date).days
        return max(0, days)  # Ensure non-negative

    async def _calculate_baseline(
        self,
        db: AsyncSession,
        family_id: int,
        elder_id: str,
    ) -> Optional["Baseline"]:
        """
        Calculate 7-day baseline if sufficient data exists.

        Returns:
            Baseline object with quality score, or None if insufficient data
        """

        # Count events in last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        result = await db.execute(
            select(func.count(Event.id)).where(
                (Event.family_id == family_id)
                & (Event.elder_id == elder_id)
                & (Event.created_at >= seven_days_ago)
            )
        )
        event_count = result.scalar() or 0

        # Need at least 50 events for reasonable baseline (avg 7 per day)
        if event_count < 50:
            # Insufficient data - return None (will use conservative thresholds)
            return None

        # Calculate baseline stats
        # (This would be your existing calculate_baseline logic)
        # For now, placeholder - integrate with actual calculation

        baseline = Baseline(
            avg_bathroom_duration_minutes=12.0,
            avg_daily_activity_minutes=180.0,
            avg_inactivity_duration_minutes=45.0,
            avg_wake_time_hour=7.5,
            avg_night_activity_count=3.5,
            quality_score=self._calculate_quality_score(event_count),
        )

        return baseline

    def _calculate_quality_score(self, event_count: int) -> float:
        """
        Calculate confidence score for baseline (0.0-1.0).

        Args:
            event_count: Number of events in last 7 days

        Returns:
            Quality score 0.0-1.0
            - <50 events: 0.0 (no baseline)
            - 50-200 events: 0.3-0.8 (marginal)
            - >200 events: 0.9+ (good)
        """

        if event_count < 50:
            return 0.0

        if event_count < 100:
            return 0.3

        if event_count < 200:
            return 0.6

        if event_count < 400:
            return 0.8

        return 0.95  # Excellent data


# ============================================================================
# Integration with Rule Engine
# ============================================================================

"""
Usage in rule engine:

from app.services.baseline_service_with_learning_period import (
    BaselineServiceWithLearningPeriod
)

baseline_service = BaselineServiceWithLearningPeriod()

# When evaluating event:
async def evaluate_event(event, db, family_id, elder_id):
    # Get baseline mode (respects learning period)
    baseline_mode = await baseline_service.get_baseline_mode(
        db, family_id, elder_id
    )

    # Get thresholds (conservative if learning)
    thresholds = baseline_service.get_thresholds_for_mode(baseline_mode)

    # Get messaging context
    messaging = baseline_service.get_messaging_for_mode(baseline_mode)

    # Pass to rule engine
    alerts = rule_engine.evaluate_event(
        event=event,
        baseline=baseline_mode.baseline,  # None if learning
        thresholds=thresholds,
        data_reliability=data_reliability_state,
        baseline_mode=baseline_mode,  # Include mode info
    )

    # Filter alerts based on learning mode
    for alert in alerts:
        if baseline_mode.is_learning_period:
            # During learning: Only alert on clear high-risk or extreme cases
            if alert.level not in ["critical", "high"]:
                continue  # Suppress low/info alerts

        # Create alert...
"""

# ============================================================================
# Database Migration Required
# ============================================================================

"""
ALTER TABLE elder ADD COLUMN first_event_date TIMESTAMP DEFAULT NULL;

-- This will be auto-set when first event is created:
UPDATE elder SET first_event_date = (
    SELECT MIN(created_at) FROM event
    WHERE event.elder_id = elder.id
) WHERE first_event_date IS NULL;

-- Index for quick lookup
CREATE INDEX idx_elder_first_event ON elder(first_event_date);
"""
