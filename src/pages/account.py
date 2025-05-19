from flask import current_app
from src.googleauth import GoogleAuth

class Account:
    def __init__(self):
        # grab (or lazily create) the same GoogleAuth you set up in create_app()
        # if you stored it on the app, you could do:
        #    self.google_auth = current_app.extensions['google_auth']
        # but if you didn’t, this will just make a new one on first use:
        self.google_auth = GoogleAuth(current_app)

    def get_user_account_info(self) -> dict:
        """
        Returns {
            'user_name':    <string>,
            'user_email':   <string>,
            'user_picture': <string URL>
        } or {} if no one’s logged in.
        """
        user = self.google_auth.get_user_auth_info()
        if not user:
            return {}

        return {
            'user_name':    user.get('name'),
            'user_email':   user.get('email'),
            'user_picture': user.get('picture'),
        }

    def get_user_credit_info(self) -> dict:
        """
        Returns {
            'current_credits': <int>,
            'credit_expiry':   <datetime>
        } or {} if no one’s logged in (or no credit info).
        """
        ci = self.google_auth.get_credit_info()
        if not ci:
            return {}

        return {
            'current_credits': ci.get('remaining'),
            'credit_expiry':   ci.get('expired_date'),
            'credit_history':   ci.get('history')
        }

