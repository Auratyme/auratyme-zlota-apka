# === File: scheduler-core/src/services/analytics.py ===

"""
Historical Data Analytics Service.

Analyzes aggregated historical data (schedules, feedback, wearable metrics)
over specified periods to identify trends, correlations, and actionable insights
for users and for adapting the scheduling system itself.
"""

import logging
import statistics
import random  # Added for mock data
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

# Application-specific imports (absolute paths)
# Attempt to import data models used in analysis
GeneratedSchedule = None
UserFeedback = None
HistoricalSleepData = None  # Define placeholder name
STATS_LIBS_AVAILABLE = False
DATA_MODELS_AVAILABLE = False
USER_FEEDBACK_AVAILABLE = False  # Track UserFeedback specifically

logger = logging.getLogger(__name__)  # Define logger early

try:
    from src.core.scheduler import GeneratedSchedule
    GENERATED_SCHEDULE_AVAILABLE = True
except ImportError:
    logger.warning("Could not import GeneratedSchedule. Analytics may be limited.")
    @dataclass
    class DummyGeneratedSchedule:
        user_id: UUID
        target_date: date
        metrics: Dict[str, Any] = field(default_factory=dict)
    GeneratedSchedule = DummyGeneratedSchedule
    GENERATED_SCHEDULE_AVAILABLE = False

try:
    # Assuming UserFeedback is defined in this path
    from feedback.collectors.user_input import UserFeedback
    USER_FEEDBACK_AVAILABLE = True
except ImportError:
    logger.warning("Could not import UserFeedback. Defining dummy.")
    @dataclass
    class DummyUserFeedback:
        user_id: UUID
        schedule_date: date
        rating: Optional[int] = None
    UserFeedback = DummyUserFeedback
    USER_FEEDBACK_AVAILABLE = False

# Define HistoricalSleepData structure (used internally or fetched)
@dataclass
class HistoricalSleepData:
    target_date: date
    actual_sleep_duration_minutes: Optional[float] = None
    sleep_quality_score: Optional[float] = None
    mid_sleep_hour_local: Optional[float] = None  # Example: hours past midnight local time

# Import statistical libraries if used for real analysis
try:
    import pandas as pd
    import numpy as np
    from scipy.stats import linregress
    STATS_LIBS_AVAILABLE = True
except ImportError:
    STATS_LIBS_AVAILABLE = False
    logger.warning("Pandas/NumPy/SciPy not installed. Analytics will use basic statistics.")

# Determine overall data model availability based on essential models
DATA_MODELS_AVAILABLE = GENERATED_SCHEDULE_AVAILABLE  # Add others if essential


# --- Data Structures ---

@dataclass(frozen=True)
class TrendAnalysisResult:
    """
    Represents the structured output of historical trend analysis.

    Attributes:
        user_id: The user for whom the analysis was performed.
        analysis_period_start_date: The start date of the analysis period.
        analysis_period_end_date: The end date of the analysis period.
        avg_sleep_duration_minutes: Average actual sleep duration over the period.
        avg_sleep_quality_score: Average calculated sleep quality score.
        sleep_timing_consistency_score: Score (0-1) indicating consistency of sleep timing.
        avg_feedback_rating: Average user feedback rating (1-5).
        avg_tasks_completed_per_day: Average number of completed tasks per day.
        avg_scheduled_task_minutes: Average total minutes scheduled for tasks per day.
        productivity_trend_slope: Estimated slope of scheduled task minutes over time.
        correlation_sleep_duration_vs_feedback: Correlation between sleep duration and feedback rating.
        insights: List of human-readable insights derived from the analysis.
        recommendations: Dictionary suggesting potential adjustments or actions.
    """
    user_id: UUID
    analysis_period_start_date: date
    analysis_period_end_date: date
    avg_sleep_duration_minutes: Optional[float] = None
    avg_sleep_quality_score: Optional[float] = None
    sleep_timing_consistency_score: Optional[float] = None
    avg_feedback_rating: Optional[float] = None
    avg_tasks_completed_per_day: Optional[float] = None
    avg_scheduled_task_minutes: Optional[float] = None
    productivity_trend_slope: Optional[float] = None
    correlation_sleep_duration_vs_feedback: Optional[float] = None
    insights: List[str] = field(default_factory=list)
    recommendations: Dict[str, Any] = field(default_factory=dict)


# --- Analytics Service Class ---

class AnalyticsService:
    """
    Performs analysis on historical user data stored in the system.

    Requires access to a data source (e.g., database, data warehouse) to fetch
    historical records for schedules, feedback, and wearable data summaries.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the AnalyticsService.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary.
        """
        self._config = config or {}
        default_analytics_params = {
            "min_data_points_for_trend": 5,
            "low_sleep_threshold_minutes": 420,  # 7 hours
            "low_feedback_threshold": 2.5,
            "consistency_stdev_scale": 2.0,
            "consistency_score_threshold": 0.5,
            "negative_trend_threshold": -5
        }
        self._analytics_params = default_analytics_params
        self._analytics_params.update(self._config.get("analytics_params", {}))

        db_uri = self._config.get("db_uri")
        if db_uri:
            self._db_client = "mock_db_client"  # Placeholder
            logger.info(f"AnalyticsService initialized with DB connection to: {db_uri[:10]}...")
        else:
            self._db_client = None
            logger.warning("AnalyticsService initialized WITHOUT database connection. Fetching will be mocked.")

        if not DATA_MODELS_AVAILABLE:
            logger.warning("AnalyticsService initialized with missing essential data models. Analysis capabilities may be limited.")
        if not STATS_LIBS_AVAILABLE:
            logger.warning("AnalyticsService initialized without Pandas/NumPy/SciPy. Trend analysis will be basic.")

    async def _fetch_historical_data(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Dict[str, List[Any]]:
        logger.info(f"Fetching historical data for user {user_id} from {start_date} to {end_date}.")
        if self._db_client is None:
            logger.warning("Database client not initialized. Returning mock historical data.")
            mock_data: Dict[str, List[Any]] = {"schedules": [], "feedback": [], "sleep_data": []}
            current_date = start_date
            base_sleep = random.uniform(400, 500)
            base_rating = random.uniform(2.5, 4.5)
            base_tasks_minutes = random.randint(200, 350)
            while current_date <= end_date:
                day_index = (current_date - start_date).days
                if GeneratedSchedule:
                    sched_minutes = base_tasks_minutes + day_index * random.uniform(-2, 3)
                    mock_data["schedules"].append(GeneratedSchedule(
                        user_id=user_id, target_date=current_date,
                        metrics={"total_scheduled_task_minutes": int(max(120, sched_minutes)),
                                 "scheduled_task_count": random.randint(3, 8),
                                 "unscheduled_task_count": random.randint(0, 2)}
                    ))
                if UserFeedback and random.random() < 0.7:
                    rating_noise = random.randint(-1, 1)
                    rating = base_rating + (base_sleep - 440) / 60 + rating_noise
                    mock_data["feedback"].append(UserFeedback(
                         user_id=user_id, schedule_date=current_date, rating=int(max(1, min(5, round(rating))))
                    ))
                if HistoricalSleepData:
                    sleep_minutes = base_sleep + day_index * random.uniform(-5, 10)
                    mock_data["sleep_data"].append(HistoricalSleepData(
                        target_date=current_date,
                        actual_sleep_duration_minutes=max(360, sleep_minutes),
                        sleep_quality_score=random.uniform(60, 95),
                        mid_sleep_hour_local=random.normalvariate(4.0, 0.8)
                    ))
                current_date += timedelta(days=1)
            return mock_data

        try:
            logger.warning("Actual database fetching not implemented. Returning empty lists.")
            return {"schedules": [], "feedback": [], "sleep_data": []}
        except Exception as e:
            logger.exception(f"Error fetching historical data for user {user_id}")
            return {"schedules": [], "feedback": [], "sleep_data": []}

    async def analyze_trends(
        self,
        user_id: UUID,
        period_days: int = 7,
    ) -> Optional[TrendAnalysisResult]:
        if period_days <= 1:
            logger.error(f"Analysis period must be greater than 1 day, got {period_days}.")
            return None

        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=period_days - 1)
        logger.info(f"Analyzing trends for user {user_id} from {start_date} to {end_date} ({period_days} days)")

        try:
            historical_data = await self._fetch_historical_data(user_id, start_date, end_date)
            schedules: List[GeneratedSchedule] = historical_data.get("schedules", []) #type: ignore
            feedback_list: List[UserFeedback] = historical_data.get("feedback", []) #type: ignore
            sleep_data_list: List[HistoricalSleepData] = historical_data.get("sleep_data", [])

            if not schedules and not feedback_list and not sleep_data_list:
                logger.warning(f"No historical data found for user {user_id} in the period {start_date} to {end_date}.")
                return TrendAnalysisResult(
                    user_id=user_id,
                    analysis_period_start_date=start_date,
                    analysis_period_end_date=end_date,
                    insights=["No historical data found for the selected period."]
                )

            # Initialize result object (immutable)
            analysis_result = TrendAnalysisResult(
                user_id=user_id,
                analysis_period_start_date=start_date,
                analysis_period_end_date=end_date,
            )

            min_points_trend = self._analytics_params.get("min_data_points_for_trend", 5)
            consistency_scale = self._analytics_params.get("consistency_stdev_scale", 2.0)

            # 1. Sleep Analysis
            if sleep_data_list:
                sleep_durations = [d.actual_sleep_duration_minutes for d in sleep_data_list if d.actual_sleep_duration_minutes is not None]
                sleep_scores = [d.sleep_quality_score for d in sleep_data_list if d.sleep_quality_score is not None]
                mid_sleep_hours = [d.mid_sleep_hour_local for d in sleep_data_list if d.mid_sleep_hour_local is not None]

                if sleep_durations:
                    object.__setattr__(analysis_result, 'avg_sleep_duration_minutes', statistics.mean(sleep_durations))
                if sleep_scores:
                    object.__setattr__(analysis_result, 'avg_sleep_quality_score', statistics.mean(sleep_scores))
                if len(mid_sleep_hours) > 1:
                    stdev_mid_sleep = statistics.stdev(mid_sleep_hours)
                    object.__setattr__(analysis_result, 'sleep_timing_consistency_score', max(0.0, 1.0 - (stdev_mid_sleep / max(0.1, consistency_scale))))
                elif len(mid_sleep_hours) == 1:
                    object.__setattr__(analysis_result, 'sleep_timing_consistency_score', 1.0)

            # 2. Feedback Analysis
            if feedback_list and USER_FEEDBACK_AVAILABLE:
                valid_ratings = [f.rating for f in feedback_list if f.rating is not None and 1 <= f.rating <= 5]
                if valid_ratings:
                    object.__setattr__(analysis_result, 'avg_feedback_rating', statistics.mean(valid_ratings))

            # 3. Productivity/Schedule Analysis
            if schedules and GENERATED_SCHEDULE_AVAILABLE:
                scheduled_minutes = [s.metrics.get("total_scheduled_task_minutes") for s in schedules if isinstance(s.metrics, dict) and s.metrics.get("total_scheduled_task_minutes") is not None]
                completed_tasks = [
                    s.metrics.get("scheduled_task_count", 0) - s.metrics.get("unscheduled_task_count", 0)
                    for s in schedules if isinstance(s.metrics, dict) and s.metrics.get("scheduled_task_count") is not None and s.metrics.get("unscheduled_task_count") is not None
                ]
                if scheduled_minutes:
                    object.__setattr__(analysis_result, 'avg_scheduled_task_minutes', statistics.mean(scheduled_minutes))
                if completed_tasks:
                    object.__setattr__(analysis_result, 'avg_tasks_completed_per_day', statistics.mean(completed_tasks))

                metric_values_for_trend = [(s.target_date, s.metrics.get("total_scheduled_task_minutes")) for s in schedules if isinstance(s.metrics, dict) and s.metrics.get("total_scheduled_task_minutes") is not None]
                if len(metric_values_for_trend) >= min_points_trend:
                    if STATS_LIBS_AVAILABLE:
                        try:
                            df = pd.DataFrame(metric_values_for_trend, columns=['date', 'minutes'])
                            df['date_ordinal'] = df['date'].apply(date.toordinal)
                            df = df.dropna()
                            if len(df) >= min_points_trend:
                                slope, intercept, r_value, p_value, std_err = linregress(df['date_ordinal'], df['minutes'])
                                object.__setattr__(analysis_result, 'productivity_trend_slope', slope)
                                logger.debug(f"Calculated productivity trend slope (linregress): {slope:.2f} min/day (p={p_value:.3f})")
                        except Exception as e:
                            logger.error(f"Error calculating trend with Pandas/SciPy: {e}")
                            object.__setattr__(analysis_result, 'productivity_trend_slope', None)
                    else:
                        metric_values_for_trend.sort()
                        days_diff = (metric_values_for_trend[-1][0] - metric_values_for_trend[0][0]).days
                        value_diff = metric_values_for_trend[-1][1] - metric_values_for_trend[0][1]
                        if days_diff > 0:
                            object.__setattr__(analysis_result, 'productivity_trend_slope', value_diff / days_diff)
                            logger.debug(f"Calculated productivity trend slope (basic): {analysis_result.productivity_trend_slope:.2f} min/day")

            # 4. Example Correlation (Sleep Duration vs Feedback)
            if STATS_LIBS_AVAILABLE and len(sleep_data_list) >= min_points_trend and len(feedback_list) >= min_points_trend and USER_FEEDBACK_AVAILABLE:
                try:
                    sleep_df = pd.DataFrame([{'date': d.target_date, 'sleep': d.actual_sleep_duration_minutes} for d in sleep_data_list if d.actual_sleep_duration_minutes])
                    feedback_df = pd.DataFrame([{'date': f.schedule_date, 'rating': f.rating} for f in feedback_list if f.rating])
                    if not sleep_df.empty and not feedback_df.empty:
                        merged_df = pd.merge(sleep_df, feedback_df, on='date').dropna()
                        if len(merged_df) >= min_points_trend:
                            correlation_matrix = np.corrcoef(merged_df['sleep'], merged_df['rating'])
                            correlation = correlation_matrix[0, 1]
                            if not np.isnan(correlation):
                                object.__setattr__(analysis_result, 'correlation_sleep_duration_vs_feedback', correlation)
                                logger.debug(f"Calculated Sleep Duration vs Feedback Correlation: {correlation:.2f}")
                except Exception as e:
                    logger.error(f"Error calculating correlation: {e}")

            # 5. Generate Insights & Recommendations
            low_sleep_threshold = self._analytics_params.get("low_sleep_threshold_minutes", 420)
            low_feedback_threshold = self._analytics_params.get("low_feedback_threshold", 2.5)
            consistency_threshold = self._analytics_params.get("consistency_score_threshold", 0.5)
            trend_threshold = self._analytics_params.get("negative_trend_threshold", -5)

            if analysis_result.avg_sleep_duration_minutes is not None and analysis_result.avg_sleep_duration_minutes < low_sleep_threshold:
                analysis_result.insights.append(
                    f"Average sleep duration ({analysis_result.avg_sleep_duration_minutes/60:.1f}h) is below the target threshold ({low_sleep_threshold/60:.1f}h)."
                )
                analysis_result.recommendations["consider_sleep_schedule_adjustment"] = True
            if analysis_result.sleep_timing_consistency_score is not None and analysis_result.sleep_timing_consistency_score < consistency_threshold:
                analysis_result.insights.append(
                    f"Sleep timing consistency score ({analysis_result.sleep_timing_consistency_score:.2f}) is low. Maintaining a regular sleep schedule can improve quality."
                )
                analysis_result.recommendations["focus_on_consistent_sleep_times"] = True
            if analysis_result.avg_feedback_rating is not None and analysis_result.avg_feedback_rating < low_feedback_threshold:
                analysis_result.insights.append(
                    f"Average schedule feedback rating ({analysis_result.avg_feedback_rating:.1f}) is below threshold ({low_feedback_threshold:.1f})."
                )
                analysis_result.recommendations["review_scheduling_preferences"] = True
            if analysis_result.productivity_trend_slope is not None and analysis_result.productivity_trend_slope < trend_threshold:
                analysis_result.insights.append(
                    f"Scheduled productive time shows a downward trend ({analysis_result.productivity_trend_slope:.1f} min/day)."
                )
                analysis_result.recommendations["investigate_productivity_factors"] = True
            if analysis_result.correlation_sleep_duration_vs_feedback is not None:
                if analysis_result.correlation_sleep_duration_vs_feedback > 0.3:
                    analysis_result.insights.append("Analysis suggests a positive correlation between longer sleep duration and higher schedule satisfaction.")
                elif analysis_result.correlation_sleep_duration_vs_feedback < -0.3:
                    analysis_result.insights.append("Analysis suggests longer sleep duration might correlate with lower schedule satisfaction (consider if oversleeping or schedule timing is an issue).")
            if not analysis_result.insights:
                analysis_result.insights.append("Data analysis did not reveal significant trends or issues in the analyzed period.")

            logger.info(f"Trend analysis complete for user {user_id}. Found {len(analysis_result.insights)} insights.")
            return analysis_result

        except Exception as e:
            logger.exception(f"Error during trend analysis for user {user_id}")
            return None


# --- Example Usage ---
async def run_example():
    """Runs a simple example demonstrating AnalyticsService usage."""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running AnalyticsService Example ---")
    example_config = {
        "analytics_params": {
            "min_data_points_for_trend": 3,
            "low_sleep_threshold_minutes": 400,
            "low_feedback_threshold": 3.0
        }
    }
    analytics_service = AnalyticsService(config=example_config)
    test_user_id = uuid4()

    print(f"\n--- Analyzing Trends for User {test_user_id} (Using Mock Data Fetch) ---")
    trends = await analytics_service.analyze_trends(user_id=test_user_id, period_days=14)

    if trends:
        print(f"Analysis Period: {trends.analysis_period_start_date} to {trends.analysis_period_end_date}")
        print(f"Avg Sleep Duration (min): {trends.avg_sleep_duration_minutes:.1f}" if trends.avg_sleep_duration_minutes else "N/A")
        print(f"Avg Sleep Quality Score: {trends.avg_sleep_quality_score:.1f}" if trends.avg_sleep_quality_score else "N/A")
        print(f"Sleep Consistency Score: {trends.sleep_timing_consistency_score:.2f}" if trends.sleep_timing_consistency_score else "N/A")
        print(f"Avg Feedback Rating: {trends.avg_feedback_rating:.1f}" if trends.avg_feedback_rating else "N/A")
        print(f"Avg Tasks Completed/Day: {trends.avg_tasks_completed_per_day:.1f}" if trends.avg_tasks_completed_per_day else "N/A")
        print(f"Avg Scheduled Task Min/Day: {trends.avg_scheduled_task_minutes:.1f}" if trends.avg_scheduled_task_minutes else "N/A")
        print(f"Productivity Trend Slope (min/day): {trends.productivity_trend_slope:.2f}" if trends.productivity_trend_slope else "N/A")
        print(f"Corr(Sleep Duration vs Feedback): {trends.correlation_sleep_duration_vs_feedback:.2f}" if trends.correlation_sleep_duration_vs_feedback else "N/A")
        print("Insights:")
        if trends.insights:
            for insight in trends.insights:
                print(f"- {insight}")
        else:
            print("- None")
        print(f"Recommendations: {trends.recommendations or 'None'}")
    else:
        print("Could not perform trend analysis (no historical data found or error occurred).")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_example())
