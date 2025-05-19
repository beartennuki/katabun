from authlib.integrations.flask_client import OAuth
from flask import url_for, session, redirect, current_app
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from bson import ObjectId

from src.api import API
from src.util import Util

class GoogleAuth:
    def __init__(self, app):
        # 1) Fetch Mongo config
        scc, mongo_cfg = API().fetch_db_config()
        if not scc or not mongo_cfg:
            raise ConnectionError('Failed to fetch mongo_db config')

        uri          = mongo_cfg['uri']
        auth_db_name = mongo_cfg['auth_db_name']
        client       = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db           = client[auth_db_name]
        self.users   = db['users']

        # 2) Set up OAuth
        self.oauth  = OAuth(app)
        self.google = self.oauth.register(
            name='google',
            client_id            = app.config['GOOGLE_CLIENT_ID'],
            client_secret        = app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url  = 'https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs        = {'scope': 'openid email profile'}
        )

    def login(self):
        # ← changed the endpoint name here from 'auth.callback' to 'auth_callback'
        redirect_uri = url_for('auth_callback', _external=True)
        return self.google.authorize_redirect(redirect_uri=redirect_uri)

    def callback(self):
        # 1) Exchange code for token + fetch userinfo
        token = self.google.authorize_access_token()
        session['auth_token'] = token
        info = self.google.userinfo()

        google_id = info['sub']
        email = info.get('email')
        name = info.get('name')
        picture = info.get('picture')
        now = datetime.now(timezone.utc)

        # 2) Upsert user doc (atomic)
        self.users.update_one(
            {'google_id': google_id},
            {
                '$set': {
                    'email': email,
                    'name': name,
                    'picture': picture,
                    'last_login': now
                },
                '$setOnInsert': {
                    'user_id': Util().generate_user_id(),
                    'google_id': google_id,
                    'credits_info': {
                        'remaining': current_app.config['SIGNUP_CREDIT'],
                        'expired_date': now + timedelta(days=356),
                        'history': []
                    },
                    'created_at': now
                }
            },
            upsert=True
        )

        # 3) Fetch the canonical user_id from MongoDB
        doc = self.users.find_one({'google_id': google_id}, {'user_id': 1})
        if not doc or 'user_id' not in doc:
            raise ValueError("User ID not found after upsert.")

        # 4) Store everything in session—this ensures name/email/picture are always fresh
        session['user_id'] = str(doc['user_id'])
        session['user_login'] = True
        session['expired_login'] = (now + timedelta(days=90)).isoformat()

        # 5) Redirect to the account page
        return redirect(url_for('account_page'))

    def delete_user(self) -> int:
        """Remove a user record by custom user_id (string), taken from session."""
        user_id = session.get('user_id')
        if not user_id:
            return 0

        result = self.users.delete_one({'user_id': user_id})
        return result.deleted_count

    def get_user_auth_info(self) -> dict | None:
        """Return the user document for the current session user_id (custom user_id field)."""
        user_id = session.get('user_id')
        if not user_id:
            return None

        return self.users.find_one({'user_id': user_id})

    def get_credit_info(self) -> dict | None:
        """Return just the credits_info sub-document."""
        user = self.get_user_auth_info()
        return user.get('credits_info') if user else None

    def add_user_credit(self, amount: int, reason: str = 'bonus') -> bool:
        """
        Atomically add `amount` to remaining,
        record final_amount in history,
        and extend expiry by 365 days,
        based on custom user_id (string).
        """
        user_id = session.get('user_id')
        if not user_id:
            return False

        now = datetime.now(timezone.utc)

        # Fetch current credits & expiry
        doc = self.users.find_one(
            {'user_id': user_id},
            {'credits_info': 1}
        )
        if not doc or 'credits_info' not in doc:
            return False

        ci = doc['credits_info']
        curr_rem = ci.get('remaining', 0)
        curr_expiry = ci.get('expired_date', now)
        if isinstance(curr_expiry, str):
            curr_expiry = datetime.fromisoformat(curr_expiry)

        new_rem = curr_rem + amount
        new_expiry = curr_expiry + timedelta(days=365)

        update = {
            '$set': {
                'credits_info.remaining': new_rem,
                'credits_info.expired_date': new_expiry
            },
            '$push': {
                'credits_info.history': {
                    'change': amount,
                    'final_amount': new_rem,
                    'reason': reason,
                    'timestamp': now
                }
            }
        }

        result = self.users.update_one({'user_id': user_id}, update)
        return result.modified_count == 1
