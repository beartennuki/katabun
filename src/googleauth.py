from authlib.integrations.flask_client import OAuth
from flask import url_for, session, redirect
from datetime import datetime
from pymongo import MongoClient, errors
import time

from src.api import API


class GoogleAuth:

    def __init__(self):

        scc, mongo_cfg = API().fetch_db_config()
        if scc is False or mongo_cfg is None:
            raise ConnectionError('Failed to fetch mongo_db config')

        uri = mongo_cfg['uri']
        auth_db_name = mongo_cfg['eval_db_name']
        assess_db_name = mongo_cfg['assess_db_name']
        mcq_collection_name = mongo_cfg['mcq_collection_name']