# src/pages/credit_checker.py
from datetime import datetime, timezone
from flask import current_app, session
from src.googleauth import GoogleAuth
from src.mongoio import MongoIO # Although GoogleAuth handles MongoDB, MongoIO is already setup for other pages

class CreditChecker:
    def __init__(self):
        # GoogleAuth requires 'app' context, which is available via current_app in a Flask request context.
        # It's important that this CreditChecker is instantiated and used within a Flask request context.
        self.google_auth = GoogleAuth(current_app)

    def has_sufficient_and_active_credits(self, user_id, required_cost: int) -> tuple[bool, str]:
        """
        Checks if a user has enough active credits for a given cost.

        Args:
            user_id: The unique ID of the user.
            required_cost: The number of credits required for the operation.

        Returns:
            A tuple (bool, str) where:
            - bool is True if credits are sufficient and active.
            - str is an error message if not, or an empty string if successful.
        """
        if not user_id:
            # This scenario should ideally be handled by login checks,
            # but as a safety, we include it here.
            return False, "User not logged in or user ID not found in session."

        credit_info = self.google_auth.get_credit_info()

        # If credit_info is None, it means the user doc or credits_info sub-doc wasn't found
        if not credit_info:
            return False, "Credit information could not be retrieved. Please ensure you are logged in and your account is active."

        remaining_credits = credit_info.get('remaining', 0)
        expiry_date = credit_info.get('expired_date')

        # 1. Check for sufficient credits
        if remaining_credits < required_cost:
            return False, f"Insufficient credits. You need {required_cost} credits, but you only have {remaining_credits}."

        # 2. Check for active credits (not expired)
        if isinstance(expiry_date, datetime):
            # Ensure datetime objects are timezone-aware for comparison
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expiry_date:
                return False, "Your credits have expired. Please purchase new credits to continue."
        else:
            # This could happen if 'expired_date' is missing or not a datetime object
            # Treat as an issue if it's expected to always be a valid datetime
            return False, "Could not verify credit expiry date. Please contact support."

        return True, ""