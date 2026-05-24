from pymongo import MongoClient, errors
import time
import redis
import json

from src.api import API
from src.util import Util


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

        # Utility helper for slug generation
        self.util = Util()

        # Initialize Redis client
        self.redis_client = redis.Redis(decode_responses=True)

    def _ensure_slug_for_document(self, document):
        """Ensure a slug exists for the provided document and return it."""
        if not document:
            return None

        meta = document.get('meta', {})
        title = meta.get('title')
        doc_id = meta.get('doc_id')

        if not title:
            return None

        base_slug = self.util.generate_slug(title)
        if not base_slug:
            return None

        slug = meta.get('slug')
        target_slug = base_slug

        if doc_id:
            conflict_query = {
                "meta.slug": base_slug,
                "meta.doc_id": {"$ne": doc_id}
            }
            if self.eval_collections.count_documents(conflict_query, limit=1):
                target_slug = self.util.generate_slug(f"{title}-{doc_id}") or base_slug

        if slug != target_slug:
            document.setdefault('meta', {})['slug'] = target_slug
            if doc_id:
                self.eval_collections.update_one(
                    {"meta.doc_id": doc_id},
                    {"$set": {"meta.slug": target_slug}}
                )
        else:
            document['meta']['slug'] = slug

        return document['meta'].get('slug')

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

            self._ensure_slug_for_document(document)
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

    def load_eval_document_by_slug(self, slug, section=None):
        """Load an evaluation document by its slug."""
        if not slug:
            return None, None

        doc_meta = self.eval_collections.find_one(
            {"meta.slug": slug},
            {"meta.doc_id": 1, "_id": 0}
        )

        if not doc_meta:
            return None, None

        doc_id = doc_meta['meta']['doc_id']
        return self.load_eval_document(doc_id, section=section)

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

        for document in documents:
            self._ensure_slug_for_document(document)

        return documents

    # Add this new method to the MongoIO class in src/mongoio.py

    def save_form_submission(self, data, collection_name):
        """
        Saves a form submission document to a specified collection.

        :param data: A dictionary containing the form data.
        :param collection_name: The name of the collection to save the data to (e.g., 'feedback' or 'inquiries').
        :return: The inserted_id of the new document or None if insertion fails.
        """
        try:
            # You might want to use a different database for user-generated content
            # For simplicity, this example uses the same 'eval_db' from your config
            db = self.client[self.mongo_cfg['eval_db_name']]
            collection = db[collection_name]
            result = collection.insert_one(data)
            return result.inserted_id
        except errors.PyMongoError as e:
            print(f"Error saving to MongoDB collection {collection_name}: {e}")
            return None

    def get_top_n_popular_quizzes(self, n, from_cache=True, genre=None):
        """
        Retrieves the top n most popular quizzes based on the number of loads.
        :param n: The number of top quizzes to retrieve.
        :param from_cache: Boolean to indicate if the cache should be used.
        :param genre: Optional genre to filter quizzes by.
        :return: A list of the top n quiz documents, sorted by popularity.
        """
        cache_key = f"top_{n}_popular_quizzes"
        if genre:
            cache_key += f"_{genre}"

        if from_cache:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    result_docs = json.loads(cached_data)
                    for document in result_docs:
                        self._ensure_slug_for_document(document)
                    return result_docs
            except redis.exceptions.ConnectionError as e:
                print(f"Redis connection error: {e}. Falling back to DB.")

        print("Cache miss or disabled. Fetching from MongoDB...")
        pipeline = []
        if genre:
            pipeline.append({"$match": {"meta.genre": genre}})

        pipeline.extend([
            {
                "$project": {
                    "doc": "$$ROOT",
                    "load_count": {"$size": "$meta.load_time_stamp"}
                }
            },
            {
                "$sort": {"load_count": -1}
            },
            {
                "$limit": n
            }
        ])

        popular_quizzes = list(self.eval_collections.aggregate(pipeline))
        result_docs = []
        for quiz in popular_quizzes:
            doc = quiz['doc']
            self._ensure_slug_for_document(doc)
            result_docs.append(doc)

        try:
            serializable_result = json.dumps(result_docs, default=str)
            self.redis_client.setex(cache_key, 3600, serializable_result)
        except redis.exceptions.ConnectionError as e:
            print(f"Redis connection error during setex: {e}. Could not cache results.")
        except TypeError as e:
            print(f"Could not serialize the MongoDB documents for caching: {e}")

        return result_docs

    def get_quiz_slug(self, doc_id):
        """Return the slug for the quiz identified by doc_id."""
        meta_doc = self.eval_collections.find_one(
            {"meta.doc_id": doc_id},
            {"meta.slug": 1, "meta.title": 1, "meta.doc_id": 1, "_id": 0}
        )
        if not meta_doc:
            return None
        temp_document = {"meta": meta_doc.get('meta', {})}
        return self._ensure_slug_for_document(temp_document)

    def log_user_interest(self, user_id, feature):
        """
        Logs user interest in a new feature.
        """
        try:
            db = self.client[self.mongo_cfg['eval_db_name']]
            collection = db['user_interest']
            collection.insert_one({
                'user_id': user_id,
                'feature': feature,
                'timestamp': time.time()
            })
            return True
        except errors.PyMongoError as e:
            print(f"Error logging user interest: {e}")
            return False