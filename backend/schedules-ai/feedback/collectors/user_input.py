# === File: scheduler-core/feedback/collectors/user_input.py ===

"""
User Input Feedback Collector.

Handles the collection, validation, and preparation for storage of feedback
provided directly by the user (e.g., schedule ratings, comments).
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

# Application-specific imports (absolute paths)
try:
    # Assuming validators exist in src.utils
    from src.utils.validators import validate_feedback_rating
    VALIDATOR_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__) # Need logger early if import fails
    logger.warning("Validator 'validate_feedback_rating' not found in src.utils. Using basic validation.")
    VALIDATOR_AVAILABLE = False
    # Define a dummy validator function if needed for type checking elsewhere
    def validate_feedback_rating(rating: int) -> bool: return True


logger = logging.getLogger(__name__)

# --- Constants ---
MAX_COMMENT_LENGTH = 1000


# --- Data Structure for User Feedback ---

@dataclass
class UserFeedback:
    """
    Represents feedback submitted by a user for a specific schedule.

    Attributes:
        feedback_id: Unique identifier for this feedback record.
        user_id: The user who submitted the feedback.
        schedule_date: The date of the schedule this feedback pertains to.
        rating: The numerical rating provided (e.g., 1-5).
        comment: Optional textual comment from the user.
        submitted_at: Timestamp (UTC) when the feedback was received/recorded.
        schedule_version_id: Optional identifier linking to the specific version
                              of the schedule being rated.
    """
    # Fields without default values must come first
    user_id: UUID
    schedule_date: date
    rating: int
    # Fields with default values
    feedback_id: UUID = field(default_factory=uuid4)
    comment: Optional[str] = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc)) # Use UTC
    schedule_version_id: Optional[str] = None


# --- Collector Class ---

class UserInputCollector:
    """
    Collects, validates, and prepares user feedback for storage.

    Acts as an intermediary between the API layer (which receives the raw input)
    and the storage layer (e.g., database).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the UserInputCollector.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary, potentially
                                               containing database connection details
                                               or validation parameters.
        """
        self._config = config or {}
        # TODO: Initialize storage connection here (e.g., database client)
        # self._storage_client = connect_to_database(self._config.get("db_uri"))
        self._storage_client = None  # Placeholder for storage mechanism
        logger.info("UserInputCollector initialized.")

    def _validate_feedback(self, rating: int, comment: Optional[str]) -> bool:
        """
        Performs basic validation on feedback rating and comment.

        Args:
            rating (int): The user's rating.
            comment (Optional[str]): The user's comment.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        # 1. Validate Rating
        if VALIDATOR_AVAILABLE:
            if not validate_feedback_rating(rating):
                logger.warning(f"Invalid feedback rating (failed custom validator): {rating}")
                return False
        else:
            # Basic fallback validation if custom validator is unavailable
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                logger.warning(
                    f"Invalid feedback rating (basic check): {rating}. Must be int between 1-5."
                )
                return False

        # 2. Validate Comment Type
        if comment is not None and not isinstance(comment, str):
            logger.warning(
                f"Invalid feedback comment type: {type(comment)}. Must be string or None."
            )
            return False

        # 3. Validate Comment Length
        if comment is not None and len(comment) > MAX_COMMENT_LENGTH:
            logger.warning(
                f"Feedback comment exceeds length limit ({MAX_COMMENT_LENGTH} chars). Length: {len(comment)}"
            )
            # Depending on requirements, you might truncate here or reject. Rejecting for now.
            # comment = comment[:MAX_COMMENT_LENGTH] # Option to truncate
            return False

        return True

    async def collect_feedback(
        self,
        user_id: UUID,
        schedule_date: date,
        rating: int,
        comment: Optional[str] = None,
        schedule_version_id: Optional[str] = None,
    ) -> Optional[UserFeedback]:
        """
        Collects, validates, and stores user feedback asynchronously.

        Args:
            user_id (UUID): ID of the user providing feedback.
            schedule_date (date): The date of the schedule being reviewed.
            rating (int): The rating given by the user (e.g., 1-5).
            comment (Optional[str]): Optional textual comment.
            schedule_version_id (Optional[str]): Optional identifier for the specific
                                                 schedule version.

        Returns:
            Optional[UserFeedback]: A UserFeedback object if successfully collected
                                    and stored, otherwise None.
        """
        logger.info(
            f"Collecting feedback for user '{user_id}', schedule date '{schedule_date}' "
            f"(Rating: {rating})."
        )

        # 1. Validate Input
        if not self._validate_feedback(rating, comment):
            logger.warning(f"Feedback validation failed for user '{user_id}', date '{schedule_date}'.")
            return None # Return None if validation fails

        # 2. Create Feedback Object
        # Strip whitespace from comment if provided
        cleaned_comment = comment.strip() if comment else None
        feedback_entry = UserFeedback(
            user_id=user_id,
            schedule_date=schedule_date,
            rating=rating,
            comment=cleaned_comment,
            schedule_version_id=schedule_version_id,
            # feedback_id and submitted_at are set by default factory
        )

        # 3. Store Feedback
        # --- Placeholder for Asynchronous Storage Logic ---
        try:
            # In a real implementation, save to a database asynchronously:
            # await self._storage_client.save_feedback(asdict(feedback_entry))
            storage_successful = True  # Simulate success
            if storage_successful:
                logger.info(
                    f"Successfully collected and stored feedback ID {feedback_entry.feedback_id} "
                    f"for user '{user_id}', date '{schedule_date}'."
                )
                return feedback_entry
            else:
                # This case might be hit if the storage operation itself fails gracefully
                logger.error(
                    f"Failed to store user feedback for user '{user_id}', date '{schedule_date}' "
                    f"(storage operation returned failure)."
                )
                return None
        except Exception as e:
            logger.exception( # Use exception() to include stack trace
                f"Error storing user feedback for user '{user_id}', date '{schedule_date}'.",
            )
            return None
        # --- End Placeholder ---


# --- Example Usage (for testing/demonstration) ---
async def run_example():
    """Runs a simple example of the UserInputCollector."""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("--- Running UserInputCollector Example ---")

    collector = UserInputCollector()
    test_user_id = uuid4()
    test_schedule_date = date.today() - timedelta(days=1)

    print("\n--- Collecting Valid Feedback ---")
    feedback1 = await collector.collect_feedback(
        user_id=test_user_id,
        schedule_date=test_schedule_date,
        rating=4,
        comment=" Generally good, but the morning felt a bit rushed. ",
        schedule_version_id="v1.2"
    )
    if feedback1:
        print(f"Collected: {asdict(feedback1)}") # Print as dict for readability

    print("\n--- Collecting Feedback with High Rating (No Comment) ---")
    feedback2 = await collector.collect_feedback(
        user_id=test_user_id,
        schedule_date=test_schedule_date,
        rating=5
    )
    if feedback2:
        print(f"Collected: {asdict(feedback2)}")

    print("\n--- Collecting Invalid Feedback (Bad Rating) ---")
    feedback3 = await collector.collect_feedback(
        user_id=test_user_id,
        schedule_date=test_schedule_date,
        rating=6, # Invalid rating
        comment="This rating is wrong."
    )
    if not feedback3:
        print("Invalid feedback (rating=6) correctly rejected.")

    print("\n--- Collecting Invalid Feedback (Long Comment) ---")
    long_comment = "a" * (MAX_COMMENT_LENGTH + 1)
    feedback4 = await collector.collect_feedback(
        user_id=test_user_id,
        schedule_date=test_schedule_date,
        rating=3,
        comment=long_comment
    )
    if not feedback4:
        print(f"Invalid feedback (comment length > {MAX_COMMENT_LENGTH}) correctly rejected.")


if __name__ == "__main__":
    import asyncio
    # Use asyncio.run() for Python 3.7+ to run the async example function
    asyncio.run(run_example())
