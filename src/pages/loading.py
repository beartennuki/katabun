#bismillahhirahmanirahim
import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from flask import current_app

class Loading:

    def __init__(self):
        self.salt, self.password = self._resolve_crypto_config()

    def _resolve_crypto_config(self):
        salt = os.getenv('LOADING_SALT')
        password = os.getenv('LOADING_PASSWORD')

        try:
            app = current_app._get_current_object()
        except RuntimeError:
            app = None

        if app is not None:
            salt = salt or app.config.get('LOADING_SALT')
            password = password or app.config.get('LOADING_PASSWORD')

            # Development-safe fallback so quiz/assessment redirects do not 500
            # when the optional loading token env vars are absent.
            if not salt:
                salt = app.secret_key
            if not password:
                password = app.secret_key

        if not salt or not password:
            raise RuntimeError(
                'Missing loading token configuration. Set LOADING_SALT and '
                'LOADING_PASSWORD, or configure a Flask secret key.'
            )

        return salt, password

    def __generate_key(self):
        key = hashlib.pbkdf2_hmac(
            'sha256',
            self.password.encode(),
            self.salt.encode(),
            100000
        )
        return base64.urlsafe_b64encode(key[:32])

    def encode_data(self, data_dict):
        json_string = json.dumps(data_dict)
        key = self.__generate_key()
        cipher = Fernet(key)
        encoded = cipher.encrypt(json_string.encode())
        encoded_str = encoded.decode('utf-8')
        return encoded_str

    def decode_data(self, encode_str):
        key = self.__generate_key()
        cipher = Fernet(key)
        encoded_bytes = encode_str.encode('utf-8')
        decoded = cipher.decrypt(encoded_bytes).decode()
        return json.loads(decoded)

    def processing_request(self, loadstr):
        load_data = self.decode_data(loadstr)
        flag = load_data['flag']
        message = load_data['message']
        doc_id = load_data['doc_id']
        doc_type = load_data['doc_type']
        task_url = load_data['task_url']

        return flag, message, doc_id, doc_type, task_url

