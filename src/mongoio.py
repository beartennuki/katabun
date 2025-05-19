from pymongo import MongoClient, errors
import time

from src.api import API


class MongoIO:
    def __init__(self):

        scc, mongo_cfg = API().fetch_db_config()
        if scc is False or mongo_cfg is None:
            raise ConnectionError('Failed to fetch mongo_db config')

        uri = mongo_cfg['uri']
        eval_db_name = mongo_cfg['eval_db_name']
        assess_db_name = mongo_cfg['assess_db_name']
        mcq_collection_name = mongo_cfg['mcq_collection_name']


        # Set a timeout (in milliseconds) for the initial connection attempt
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        eval_db = self.client[eval_db_name]
        self.eval_collections = eval_db[mcq_collection_name]

        assess_db = self.client[assess_db_name]
        self.assess_collection = assess_db[mcq_collection_name]
        self.mongo_cfg = mongo_cfg

    def load_eval_document(self, doc_id, section=None):
        """
        Loads (retrieves) a document by its `doc_id` stored in `meta.doc_id`.
        Can return the whole document or just a specific section along with its version.

        :param doc_id: The document ID stored inside `meta.doc_id`
        :param section: The section to retrieve (e.g., "feedback", "input", etc.).
                        If None, retrieves the full document.
        :return: A tuple (data, version) where:
                 - `data` is the requested section (or full document).
                 - `version` is the document's version.
                 - Returns (None, None) if the document is not found.
        """
        # Construct the query
        query = {"meta.doc_id": doc_id}
        collections = self.eval_collections
        current_timestamp = time.time()

        if section is None:
            document = collections.find_one(query)

            if not document:
                return None, None

            version = document['control']['version']
            collections.update_one(
                {"meta.doc_id": doc_id},
                {"$push": {"meta.load_time_stamp": current_timestamp}}
            )
            return document, version
        else:
            projection = {"control": 1, section: 1, "_id": 0}
            document = collections.find_one(query, projection)
            if not document:
                return None, None
            version = document['control']['version']
            section_document = document[section]
            return section_document, version

    def load_assessment_document(self, assessment_id, section=None):
        """
        Loads (retrieves) a document by its `doc_id` stored in `meta.doc_id`.
        Can return the whole document or just a specific section along with its version.

        :param doc_id: The document ID stored inside `meta.doc_id`
        :param section: The section to retrieve (e.g., "feedback", "input", etc.).
                        If None, retrieves the full document.
        :return: A tuple (data, version) where:
                 - `data` is the requested section (or full document).
                 - `version` is the document's version.
                 - Returns (None, None) if the document is not found.
        """
        # Construct the query
        query = {"meta.assessment_id": assessment_id}
        if section is None:
            document = self.assess_collection.find_one(query)
            if not document:
                return None, None

            version = document['control']['version']
            return document, version
        else:
            projection = {"control": 1, section: 1, "_id": 0}
            document = self.assess_collection.find_one(query, projection)
            if not document:
                return None, None
            version = document['control']['version']
            section_document = document[section]
            return section_document, version

    def document_exists(self, doc_id, doc_type):

        if doc_type == 'eval':
            return self.eval_collections.find_one({"meta.doc_id": doc_id}) is not None
        elif doc_type == 'assessment':
            return self.assess_collection.find_one({"meta.assessment_id": doc_id}) is not None
        else:
            raise ValueError('Unknown doc_type')

    def is_online(self):
        """
        Checks if the MongoDB server is online and the specified database is accessible.

        :return: True if MongoDB is online and the database is accessible, otherwise False.
        """
        try:
            # Ping the server
            self.client.admin.command('ping')

            # Optional: check if the database appears in the list of database names.
            # Note: A new database with no collections may not appear, so this check is optional.
            if self.db_name not in self.client.list_database_names():
                # You might choose to return False here if the database must pre-exist.
                pass

            return True
        except errors.PyMongoError as e:
            print("Error connecting to MongoDB:", e)
            return False

    def load_documents_by_genre(self, genre_value):
        """
        Retrieves documents where meta.genre matches the specified value.

        :param genre_value: The value of meta.genre to search for.
        :param doc_type: The type of document to search ('eval' or 'assessment').
        :return: A list of matching documents.
        """
        collection = self.eval_collections
        query = {"meta.genre": genre_value}
        projection = {"meta": 1, "_id": 0}
        documents = list(collection.find(query, projection).sort("meta.creation_time", -1))

        return documents
