#bismillahhirahmanirahim
import json
import base64
import hashlib
from cryptography.fernet import Fernet

class Loading:

    def __init__(self):
        self.salt = 'mkn103@'
        self.password = 'pass123'

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


