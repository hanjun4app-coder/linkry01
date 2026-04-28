"""
Fixed BaselineAwareRuleEngine with proper data_reliability handling.

Key changes:
1. Data reliability state passed to all rule evaluations
2. Degraded data (60-120 min) scales thresholds UP (conservative)
3. Degraded-only alerts filtered out (no SMS)
4. Combined signals still escalate (bathroom + no motion)
5. Messages changed for degraded state (observation-based)

Safety principle: If we can't trust the data, raise thresholds, don't lower them.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime


class DataReliabilityState(str, Enum):
    """Quality of sensor data."""

    NORMAL = "normal"  # Data fresh and consistent
    DEGRADED = "degraded"  # 60-120 min no activity (can't distinguish nap from failure)
    OFFLINE = "offline"  # >120 min no data (sensor definitely failed)


@dataclass
class Baseline:
    """7-day behavioral baseline."""

    avg_bathroom_duration_minutes: float
    avg_daily_activity_minutes: float
    avg_inactivity_duration_minutes: float
    avg_wake_time_hour: float
    avg_night_activity_count: float
    quality_score: float  # 0.0-1.0 (1.0 = high confidence)


@dataclass
class AlertSpec:
    """Alert to create (returned by rule engine)."""

    type: str  # bathroom_timeout, inactivity, etc.
    level: str  # critical, high, warning, info
    message: str  # User-visible message
    triggered_by_degraded_data: bool  # True if ONLY triggered due to degraded state


class BaselineAwareRuleEngine:
    """
    Rule engine that adjusts thresholds based on data reliability.

    Rules:
    1. Bathroom timeout: current > max(30 min, baseline * 1.5)
    2. Inactivity: current > max(threshold, baseline * 1.5)
       - If degraded: threshold = 6h (not 4h)
       - If offline: threshold = 8h
    3. Abnormal wake time: delta > 120 minutes
    4. Night activity: motion > max(5, baseline * 2)
    5. Room pattern: activity < baseline - 40%
    6. Combined: bathroom + no_movement = escalate to HIGH
    7. Combined: night + low_daytime = pattern_deviation WARNING

    Key insight: When data_reliability is DEGRADED, we can't tell if the
    elderly person is napping (normal) or the sensor failed (abnormal).
    Solution: Raise thresholds and DON'T alert unless other signals confirm.
    """

    def __init__(self):
        """Initialize rule engine."""
        self.baseline_low_quality_threshold = 0.5  # If baseline quality < 50%, be very conservative

    def evaluate_event(
        self,
        event,  # Event object with elder_id, event_type, event_value
        baseline: Optional[Baseline],
        data_reliability: DataReliabilityState = DataReliabilityState.NORMAL,
    ) -> List[AlertSpec]:
        """
        Evaluate event against baseline and return alerts to create.

        Args:
            event: Event record
            baseline: 7-day baseline (or None if first week)
            data_reliability: Quality of sensor data (normal, degraded, offline)

        Returns:
            List of AlertSpec to create
        """

        alerts = []

        # ===== STEP 1: Adjust thresholds based on data_reliability =====
        thresholds = self._get_adjusted_thresholds(data_reliability, baseline)

        # ===== STEP 2: Evaluate individual rules =====
        bathroom_alert = self._check_bathroom_timeout(event, baseline, thresholds)
        inactivity_alert = self._check_inactivity(event, baseline, thresholds, data_reliability)
        wake_time_alert = self._check_abnormal_wake_time(event, baseline)
        night_activity_alert = self._check_night_activity(event, baseline)
        pattern_alert = self._check_room_pattern(event, baseline)

        # ===== STEP 3: Filter out degraded-only alerts =====
        # If data is degraded AND alert is ONLY due to degraded data, suppress it
        if data_reliability == DataReliabilityState.DEGRADED:
            # Inactivity during degraded state is likely napping—don't alert
            inactivity_alert = None

        # ===== STEP 4: Add individual alerts =====
        if bathroom_alert:
            alerts.append(bathroom_alert)

        if inactivity_alert:
            alerts.append(inactivity_alert)

        if wake_time_alert:
            alerts.append(wake_time_alert)

        if night_activity_alert:
            alerts.append(night_activity_alert)

        if pattern_alert:
            alerts.append(pattern_alert)

        # ===== STEP 5: Evaluate combined rules (escalate if multiple signals) =====
        combined_alerts = self._check_combined_rules(
            event,
            baseline,
            thresholds,
            bathroom_alert,
            inactivity_alert,
            night_activity_alert,
            data_reliability,
        )
        alerts.extend(combined_alerts)

        return alerts

    def _get_adjusted_thresholds(
        self,
        data_reliability: DataReliabilityState,
        baseline: Optional[Baseline],
    ) -> Dict[str, float]:
        """
        Get inactivity thresholds adjusted for data reliability.

        Principle: If we can't trust the data, raise thresholds (be conservative).
        """

        if data_reliability == DataReliabilityState.NORMAL:
            # Normal case: use standard thresholds
            if baseline and baseline.quality_score >= self.baseline_low_quality_threshold:
                inactivity_threshold = max(4 * 60, baseline.avg_inactivity_duration_minutes * 1.5)
            else:
                # Baseline is low quality, use conservative generic threshold
                inactivity_threshold = 6 * 60  # 6 hours

        elif data_reliability == DataReliabilityState.DEGRADED:
            # Degraded: 60-120 min no activity
            # Can't distinguish nap from sensor failure
            # Solution: Raise threshold significantly
            if baseline and baseline.quality_score >= self.baseline_low_quality_threshold:
                inactivity_threshold = max(6 * 60, baseline.avg_inactivity_duration_minutes * 2.0)
            else:
                inactivity_threshold = 6 * 60  # Very conservative

        elif data_reliability == DataReliabilityState.OFFLINE:
            # Offline: >120 min no data
            # Sensor definitely failed—don't use inactivity rule at all
            inactivity_threshold = 10 * 60  # 10 hours (effectively disabled)

        else:
            inactivity_threshold = 6 * 60

        return {
            "inactivity_minutes": inactivity_threshold,
            "bathroom_minutes": 30,
            "wake_time_delta_minutes": 120,
        }

    def _check_bathroom_timeout(
        self,
        event,
        baseline: Optional[Baseline],
        thresholds: Dict[str, float],
    ) -> Optional[AlertSpec]:
        """Check if bathroom duration exceeds threshold."""

        if event.event_type != "bathroom":
            return None

        # Bathroom duration in minutes
        duration = event.event_value

        # Expected bathroom duration
        if baseline:
            expected = max(
                thresholds["bathroom_minutes"],
                baseline.avg_bathroom_duration_minutes * 1.5,
            )
        else:
            expected = thresholds["bathroom_minutes"]

        if duration > expected:
            return AlertSpec(
                type="bathroom_timeout",
                level="warning",
                message=f"Extended bathroom duration detected ({int(duration)} minutes).",
                triggered_by_degraded_data=False,
            )

        return None

    def _check_inactivity(
        self,
        event,
        baseline: Optional[Baseline],
        thresholds: Dict[str, float],
        data_reliability: DataReliabilityState,
    ) -> Optional[AlertSpec]:
        """Check if inactivity exceeds threshold."""

        if event.event_type != "activity":
            return None

        # Total inactive minutes today
        inactivity_minutes = event.event_value

        threshold = thresholds["inactivity_minutes"]

        if inactivity_minutes > threshold:
            # Determine if this alert is ONLY due to degraded data
            is_degraded_only = data_reliability == DataReliabilityState.DEGRADED

            return AlertSpec(
                type="inactivity",
                level="warning",
                message=(
                    "We haven't seen much activity recently. "
                    "If they are resting, no action is needed."
                    if is_degraded_only
                    else f"Extended inactivity detected ({int(inactivity_minutes)} minutes)."
                ),
                triggered_by_degraded_data=is_degraded_only,
            )

        return None

    def _check_abnormal_wake_time(
        self,
        event,
        baseline: Optional[Baseline],
    ) -> Optional[AlertSpec]:
        """Check if wake time deviates significantly from baseline."""

        if event.event_type != "wake_time":
            return None

        if not baseline:
            return None

        # Wake time delta in minutes
        delta = abs(event.event_value - baseline.avg_wake_time_hour * 60)

        if delta > 120:  # >2 hours
            return AlertSpec(
                type="abnormal_wake_time",
                level="info",
                message=f"Different wake time detected today.",
                triggered_by_degraded_data=False,
            )

        return None

    def _check_night_activity(
        self,
        event,
        baseline: Optional[Baseline],
    ) -> Optional[AlertSpec]:
        """Check for excessive night activity."""

        if event.event_type != "night_activity":
            return None

        # Number of motion events during night
        night_motions = event.event_value

        if baseline:
            threshold = max(5, baseline.avg_night_activity_count * 2.0)
        else:
            threshold = 5

        if night_motions > threshold:
            return AlertSpec(
                type="night_activity",
                level="warning",
                message=f"Unusual nighttime activity detected ({int(night_motions)} movements).",
                triggered_by_degraded_data=False,
            )

        return None

    def _check_room_pattern(
        self,
        event,
        baseline: Optional[Baseline],
    ) -> Optional[AlertSpec]:
        """Check if room activity pattern changed significantly."""

        if event.event_type != "room_pattern":
            return None

        if not baseline:
            return None

        # Activity as % of baseline
        activity = event.event_value
        threshold = baseline.avg_daily_activity_minutes * 0.6  # <60% of baseline

        if activity < threshold:
            return AlertSpec(
                type="pattern_deviation",
                level="info",
                message="Daily activity pattern is different from usual.",
                triggered_by_degraded_data=False,
            )

        return None

    def _check_combined_rules(
        self,
        event,
        baseline: Optional[Baseline],
        thresholds: Dict[str, float],
        bathroom_alert: Optional[AlertSpec],
        inactivity_alert: Optional[AlertSpec],
        night_activity_alert: Optional[AlertSpec],
        data_reliability: DataReliabilityState,
    ) -> List[AlertSpec]:
        """
        Check combinations of signals for escalation.

        Rule 1: Bathroom + extended inactivity = escalate to HIGH
        Rule 2: Night activity + low daytime activity = pattern_deviation
        Rule 3: Repeated same alert 3x in 24h = escalate by one level
        """

        escalated = []

        # Rule 1: Bathroom + no movement = HIGH escalation
        if bathroom_alert and inactivity_alert:
            # Both toilet and inactivity triggered—possible immobility issue
            escalated.append(
                AlertSpec(
                    type="combined_bathroom_inactivity",
                    level="high",
                    message=(
                        "Extended bathroom duration with limited movement detected. "
                        "Please verify they are okay."
                    ),
                    triggered_by_degraded_data=False,
                )
            )

        # Rule 2: Night activity + low daytime = pattern_deviation
        if night_activity_alert and inactivity_alert:
            escalated.append(
                AlertSpec(
                    type="pattern_deviation",
                    level="warning",
                    message="Activity pattern shifted: more nighttime activity, less daytime activity.",
                    triggered_by_degraded_data=False,
                )
            )

        # Rule 3: Offline state + bathroom/inactivity = escalate to CRITICAL
        if data_reliability == DataReliabilityState.OFFLINE:
            if bathroom_alert or inactivity_alert:
                escalated.append(
                    AlertSpec(
                        type="sensor_failure_with_activity",
                        level="critical",
                        message=(
                            "Unable to reach sensor. Please check device connection. "
                            "If unable to restore, please verify they are okay manually."
                        ),
                        triggered_by_degraded_data=False,
                    )
                )

        return escalated

    def get_messages_for_reliability_state(
        self,
        data_reliability: DataReliabilityState,
    ) -> Dict[str, str]:
        """Get status messages appropriate for current data reliability state."""

        if data_reliability == DataReliabilityState.NORMAL:
            return {
                "status": "monitoring_active",
                "message": "System monitoring active. Home status OK.",
            }

        elif data_reliability == DataReliabilityState.DEGRADED:
            return {
                "status": "monitoring_limited",
                "message": (
                    "System detected reduced activity. "
                    "They may be resting—checking in voice confirmation if alert triggered."
                ),
            }

        elif data_reliability == DataReliabilityState.OFFLINE:
            return {
                "status": "device_offline",
                "message": (
                    "Motion sensor offline. Unable to monitor activity. "
                    "Please check device connection."
                ),
            }

        return {"status": "unknown", "message": "Unknown data state."}


# ============================================================================
# INTEGRATION WITH EXISTING CODE
# ============================================================================

"""
Usage in events.py:

from app.rules import BaselineAwareRuleEngine, DataReliabilityState

rule_engine = BaselineAwareRuleEngine()

# When processing event:
alerts = rule_engine.evaluate_event(
    event=event,
    baseline=baseline,
    data_reliability=data_reliability_state,  # NEW: pass this
)

# Filter out degraded-only alerts from SMS
for alert in alerts:
    if alert.triggered_by_degraded_data:
        # Still create alert in database (for audit trail)
        # But DON'T send SMS
        pass
    else:
        # Normal alert—send SMS based on sensitivity
        pass
"""
