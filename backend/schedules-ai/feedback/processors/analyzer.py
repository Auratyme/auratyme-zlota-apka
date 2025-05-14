# === File: scheduler-core/feedback/processors/analyzer.py ===

"""
Feedback Analysis Processor.

Analyzes collected user feedback (ratings, comments) potentially in conjunction
with device data and schedule information to extract insights, identify patterns,
and detect potential issues for adaptive learning or reporting.
"""

import logging
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

# Application-specific imports (absolute paths)
UserFeedback = None
StoredDeviceData = None
GeneratedSchedule = None
NLP_AVAILABLE = False

logger = logging.getLogger(__name__)  # Define logger early

try:
    from feedback.collectors.user_input import UserFeedback
    USER_FEEDBACK_AVAILABLE = True
except ImportError:
    logger.warning("Could not import UserFeedback. Defining dummy.")

    @dataclass
    class DummyUserFeedback:
        user_id: UUID
        schedule_date: date
        rating: Optional[int] = None
        comment: Optional[str] = None

    UserFeedback = DummyUserFeedback
    USER_FEEDBACK_AVAILABLE = False

try:
    # Assuming StoredDeviceData is defined here for type hinting
    from feedback.collectors.device_data import StoredDeviceData
    STORED_DEVICE_DATA_AVAILABLE = True
except ImportError:
    logger.warning("Could not import StoredDeviceData. Defining dummy.")

    @dataclass
    class DummyStoredDeviceData:
        user_id: UUID
        target_date: date
        sleep_quality_score: Optional[float] = None
        steps: Optional[int] = None
        sleep_deficit_minutes: Optional[float] = None
        record_id: UUID = field(default_factory=uuid4)
    StoredDeviceData = DummyStoredDeviceData
    STORED_DEVICE_DATA_AVAILABLE = False

try:
    from src.core.scheduler import GeneratedSchedule
    GENERATED_SCHEDULE_AVAILABLE = True
except ImportError:
    logger.warning("Could not import GeneratedSchedule. Defining dummy.")

    @dataclass
    class DummyGeneratedSchedule:
        user_id: UUID
        target_date: date
        schedule_id: UUID = field(default_factory=uuid4)
        metrics: Dict[str, Any] = field(default_factory=dict)
    GeneratedSchedule = DummyGeneratedSchedule
    GENERATED_SCHEDULE_AVAILABLE = False


# Import NLP libraries if used
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    # Ensure VADER lexicon is downloaded (should have been done via command)
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        logger.warning("NLTK VADER lexicon not found. Please run: python -m nltk.downloader vader_lexicon")
        try:
            nltk.download('vader_lexicon')
        except Exception as download_err:
            logger.error(f"Failed to download NLTK VADER lexicon: {download_err}")
            NLP_AVAILABLE = False
        else:
            NLP_AVAILABLE = True
    else:
        NLP_AVAILABLE = True

    if NLP_AVAILABLE:
        _vader_analyzer = SentimentIntensityAnalyzer()
        logger.info("NLTK VADER sentiment analyzer initialized.")
except ImportError:
    logger.warning("NLTK library not found. NLP features will be disabled. Install with: poetry add nltk")
    NLP_AVAILABLE = False
    _vader_analyzer = None


# --- Default Constants (can be overridden by config) ---
DEFAULT_POSITIVE_KEYWORDS = {"good", "great", "perfect", "liked", "helpful", "better", "productive", "energetic", "easy", "well", "smoothly"}
DEFAULT_NEGATIVE_KEYWORDS = {"bad", "poor", "rushed", "late", "missed", "difficult", "tired", "sleepy", "stressful", "busy", "hard", "off", "wrong", "unproductive"}
DEFAULT_ISSUE_KEYWORDS = {
    "timing": {"late", "early", "rushed", "slow", "timing", "off"},
    "density": {"busy", "packed", "dense", "overwhelmed", "rushed", "too much"},
    "sleep": {"tired", "sleepy", "exhausted", "nap", "wake", "bedtime"},
    "adherence": {"missed", "skipped", "late", "didn't finish", "couldn't do"},
    "energy": {"energetic", "tired", "low energy", "peak", "dip"},
}


# --- Data Structure for Analysis Results ---

@dataclass
class FeedbackAnalysis:
    """
    Structured output of feedback analysis for a given target date.

    Attributes:
        user_id: The user whose feedback is being analyzed.
        target_date: The date the feedback pertains to.
        analysis_id: Unique identifier for this analysis instance.
        rating: The user's numerical rating (if provided).
        comment_sentiment_score: Estimated sentiment score of the comment (-1.0 to 1.0).
                                 Uses VADER compound score if available, otherwise basic keyword analysis.
        comment_keywords: List of potentially relevant keywords extracted from the comment.
        issues_identified: List of potential issues flagged based on comment keywords.
        analysis_timestamp: Timestamp (UTC) when the analysis was performed.
    """
    user_id: UUID
    target_date: date
    analysis_id: UUID = field(default_factory=uuid4)
    rating: Optional[int] = None
    comment_sentiment_score: Optional[float] = None
    comment_keywords: List[str] = field(default_factory=list)
    issues_identified: List[str] = field(default_factory=list)
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# --- Analyzer Class ---

class FeedbackAnalyzer:
    """
    Processes and analyzes user feedback, potentially combining it with
    objective data (device metrics, schedule details) to extract insights.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the FeedbackAnalyzer.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary, potentially
                                               containing custom keyword sets.
        """
        self._config = config or {}
        keywords_config = self._config.get("feedback_keywords", {})

        self._positive_keywords = set(keywords_config.get("positive", DEFAULT_POSITIVE_KEYWORDS))
        self._negative_keywords = set(keywords_config.get("negative", DEFAULT_NEGATIVE_KEYWORDS))
        self._issue_keywords = keywords_config.get("issues", DEFAULT_ISSUE_KEYWORDS)
        for issue_type in self._issue_keywords:
            self._issue_keywords[issue_type] = set(self._issue_keywords[issue_type])

        self._nlp_pipeline = None  # Placeholder for future enhancements
        self._vader_analyzer = _vader_analyzer if NLP_AVAILABLE else None

        logger.info(f"FeedbackAnalyzer initialized (NLTK VADER Available: {NLP_AVAILABLE}).")
        logger.debug(f"Using positive keywords: {len(self._positive_keywords)}")
        logger.debug(f"Using negative keywords: {len(self._negative_keywords)}")
        logger.debug(f"Using issue keyword categories: {list(self._issue_keywords.keys())}")

    def _analyze_comment_sentiment_vader(self, comment: str) -> Optional[float]:
        """Analyzes sentiment using NLTK VADER."""
        if not self._vader_analyzer:
            return None
        try:
            vs = self._vader_analyzer.polarity_scores(comment)
            return vs['compound']
        except Exception as e:
            logger.error(f"Error during VADER sentiment analysis: {e}")
            return None

    def _extract_keywords_basic(self, comment: str) -> List[str]:
        """Extracts keywords using basic regex and filtering."""
        comment_lower = comment.lower()
        words = re.findall(r'\b\w{4,}\b', comment_lower)
        stopwords = {"the", "and", "but", "was", "for", "with", "this", "that", "felt", "like", "just", "very", "really"}
        keywords = [word for word in words if word not in stopwords]
        return list(set(keywords))[:15]

    async def analyze_daily_feedback(
        self,
        user_feedback: UserFeedback, #type: ignore
    ) -> Optional[FeedbackAnalysis]:
        """
        Analyzes feedback for a single day, focusing on comment sentiment and keywords.

        Args:
            user_feedback (UserFeedback): The UserFeedback object for the day.

        Returns:
            Optional[FeedbackAnalysis]: A FeedbackAnalysis object containing the results,
                                        or None if the input feedback is invalid.
        """
        # If the real UserFeedback class was not available, assume the object is dummy.
        is_dummy_feedback = not USER_FEEDBACK_AVAILABLE
        if is_dummy_feedback or not hasattr(user_feedback, 'user_id') or not hasattr(user_feedback, 'schedule_date'):
            logger.warning("Invalid or dummy user_feedback object provided to analyzer.")
            return None

        logger.info(
            f"Analyzing feedback for user '{user_feedback.user_id}', date '{user_feedback.schedule_date}' "
            f"(Rating: {getattr(user_feedback, 'rating', 'N/A')})."
        )

        sentiment_score: Optional[float] = None
        keywords: List[str] = []
        comment = getattr(user_feedback, 'comment', None)

        if comment:
            if NLP_AVAILABLE and self._vader_analyzer:
                sentiment_score = self._analyze_comment_sentiment_vader(comment)
                logger.debug(f"VADER Sentiment Score: {sentiment_score}")
            else:
                pos_count = sum(1 for word in self._positive_keywords if word in comment.lower())
                neg_count = sum(1 for word in self._negative_keywords if word in comment.lower())
                if pos_count > neg_count:
                    sentiment_score = 0.6
                elif neg_count > pos_count:
                    sentiment_score = -0.6
                logger.debug(f"Basic Sentiment Score: {sentiment_score}")

            keywords = self._extract_keywords_basic(comment)
            logger.debug(f"Extracted Keywords: {keywords}")

        analysis = FeedbackAnalysis(
            user_id=user_feedback.user_id,
            target_date=user_feedback.schedule_date,
            rating=getattr(user_feedback, 'rating', None),
            comment_sentiment_score=sentiment_score,
            comment_keywords=keywords,
        )

        identified_issues_set = set()
        if keywords:
            for issue_type, issue_words in self._issue_keywords.items():
                if any(kw in issue_words for kw in keywords):
                    identified_issues_set.add(issue_type)
        analysis.issues_identified = sorted(list(identified_issues_set))

        logger.info(
            f"Feedback analysis complete for user '{analysis.user_id}', date '{analysis.target_date}'. "
            f"Issues identified: {analysis.issues_identified or 'None'}"
        )

        return analysis


# --- Example Usage (for testing/demonstration) ---
async def run_example():
    """Runs a simple example of the FeedbackAnalyzer."""
    import asyncio
    from uuid import uuid4
    from datetime import timedelta
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running FeedbackAnalyzer Example ---")

    if UserFeedback is None:
        logger.error("UserFeedback class is not defined. Cannot run example.")
        return

    analyzer = FeedbackAnalyzer()
    test_user_id = uuid4()
    test_date = date.today() - timedelta(days=1)

    print("\n--- Scenario 1: Good Feedback ---")
    feedback1 = UserFeedback(user_id=test_user_id, schedule_date=test_date, rating=5, comment="Felt great today, very productive and energetic!")
    analysis1 = await analyzer.analyze_daily_feedback(feedback1)
    if analysis1:
        from dataclasses import asdict
        print(json.dumps(asdict(analysis1), indent=2, default=str))

    print("\n--- Scenario 2: Bad Feedback ---")
    feedback2 = UserFeedback(user_id=test_user_id, schedule_date=test_date, rating=2, comment="Really tired and rushed all day. Missed the last task because I was exhausted.")
    analysis2 = await analyzer.analyze_daily_feedback(feedback2)
    if analysis2:
        from dataclasses import asdict
        print(json.dumps(asdict(analysis2), indent=2, default=str))

    print("\n--- Scenario 3: Neutral Feedback, Timing Issue ---")
    feedback3 = UserFeedback(user_id=test_user_id, schedule_date=test_date, rating=3, comment="It was okay. The timing felt a bit off.")
    analysis3 = await analyzer.analyze_daily_feedback(feedback3)
    if analysis3:
        from dataclasses import asdict
        print(json.dumps(asdict(analysis3), indent=2, default=str))

    print("\n--- Scenario 4: No Comment ---")
    feedback4 = UserFeedback(user_id=test_user_id, schedule_date=test_date, rating=4)
    analysis4 = await analyzer.analyze_daily_feedback(feedback4)
    if analysis4:
        from dataclasses import asdict
        print(json.dumps(asdict(analysis4), indent=2, default=str))


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_example())
