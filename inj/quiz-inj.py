import os
import json
import sys
import time
import threading
import queue
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone # Import timezone for aware datetimes
from pymongo import MongoClient, errors # Import pymongo for direct DB interaction

# --- Configuration Parameters ---
USER_ID = os.getenv("INJ_USER_ID", "")
JSON_FILE_PATH = 'inj/quiz_inj.json'
CHECK_INTERVAL_SECONDS = 10
MAX_RETRIES = 30
MAX_THREADS = 5
QUIZ_GENERATION_COST = 5 # Define the cost per quiz generation
# --- End Configuration Parameters ---

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from src.util import Util
from src.mongoio import MongoIO # Import MongoIO

load_dotenv()

class API:
    def __init__(self):
        api_port = 5500
        katabun_env = os.getenv('KATABUN_ENV_TYPE')
        if katabun_env not in ["PROD", "DEV"]:
            raise ValueError('Unknown KATABUN_ENV_TYPE setting')

        katabun_env = os.getenv("KATABUN_ENV_TYPE", "PROD")
        if katabun_env == "DEV":
            self.api_base_url = f"http://localhost:{api_port}"
        else:
            rehal_uri = os.getenv("REHAL_URI")
            if not rehal_uri:
                raise EnvironmentError("REHAL_URI must be set in production environment")

            self.api_base_url = rehal_uri

    def submit(self, submit_info):
        try:
            endpoint = f"{self.api_base_url}/job/submit"
            headers = {
                "Content-Type": "application/json"
            }
            data = {'submit_info': submit_info}
            response = requests.post(endpoint, json=data, headers=headers)
            task_id = response.json().get("task_id")

            if response.status_code == 202:
                return {'status': True, 'task_id': task_id, 'msg': 'Task submitted'}
            else:
                return {'status': False, 'task_id': None, 'msg': 'Failed to submit'}
        except requests.exceptions.RequestException as e:
            return {'status': False, 'task_id': None, 'msg': 'Failed to connect'}

    def check_status(self, task_id):
        try:
            endpoint = f"{self.api_base_url}/job/status/{task_id}"
            resp = requests.get(endpoint, timeout=5)
            resp.raise_for_status()

            payload = resp.json()
            state = payload.get("state")
            status = payload.get("status")
            msg = payload.get("msg")

            if state == "PENDING":
                return {"state": "pending", "msg": msg}, 202

            if state in {"STARTED", "RETRY", "PROGRESS"}:
                return {"state": "processing", "msg": msg}, 202

            if state == "SUCCESS":
                return {"state": status or "success", "msg": msg}, 200

            if state == "FAILURE":
                return {"state": "fail", "msg": msg or "Task failed"}, 500

            if state == "REVOKED":
                return {"state": "revoked", "msg": msg or "Task was cancelled"}, 410

            return {"state": "unknown", "msg": f"Unrecognised Celery state: {state}"}, 400

        except requests.exceptions.RequestException as e:
            return {"error": "Request to status endpoint failed", "details": str(e)}, 502

        except (ValueError, json.JSONDecodeError):
            return {"error": "Invalid JSON from status endpoint"}, 502

    def fetch_mcq_doc(self, doc_id, section=None):
        url = self.api_base_url + '/job/load'
        headers = {"Content-Type": "application/json"}
        data = {"doc_info":
                    {"doc_type": "mcq",
                     "doc_id": doc_id}
                }
        if section:
            data["doc_info"]['section'] = section

        response = requests.post(url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            response_dict = response.json()

            if response_dict['status'] == 'SUCCESS':
                return response_dict.get('doc')
        return None

    def fetch_db_config(self):
        url = self.api_base_url + "/db-config"
        response = requests.get(url, headers={"Accept": "application/json"})
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None


api = API()
util = Util()
mongoio = MongoIO() # Initialize MongoIO globally

# Credit checking logic adapted for standalone script
def check_user_credits(user_id, required_cost: int) -> tuple[bool, str]:
    """
    Checks if a user has enough active credits directly from MongoDB.
    Returns (True, "") if sufficient and active, else (False, error_message).
    """
    scc, mongo_cfg = api.fetch_db_config()
    if not scc or not mongo_cfg:
        return False, "Failed to fetch MongoDB configuration to check credits."

    uri = mongo_cfg['uri']
    auth_db_name = mongo_cfg['auth_db_name']

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client[auth_db_name]
        users_collection = db['users']

        user_doc = users_collection.find_one({'user_id': user_id})
        if not user_doc or 'credits_info' not in user_doc:
            return False, f"User '{user_id}' not found or credit information missing."

        credit_info = user_doc['credits_info']
        remaining_credits = credit_info.get('remaining', 0)
        expiry_date = credit_info.get('expired_date')

        if remaining_credits < required_cost:
            return False, f"Insufficient credits. You need {required_cost} credits, but you only have {remaining_credits}."

        if isinstance(expiry_date, datetime):
            if expiry_date.tzinfo is None:
                expiry_date = expiry_date.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expiry_date:
                return False, "Your credits have expired. Please purchase new credits."
        else:
            return False, "Invalid credit expiry date information found for your account."

        return True, ""
    except errors.PyMongoError as e:
        return False, f"Error connecting to MongoDB or fetching user credits: {e}"
    except Exception as e:
        return False, f"An unexpected error occurred during credit check: {e}"


def worker(q):
    """
    Worker function for each thread. Continuously fetches quiz data from the queue
    and processes it until the queue is empty.
    """
    while True:
        try:
            quiz_data, index = q.get(timeout=1)
        except queue.Empty:
            break

        try:
            print(f"\n--- Processing Quiz Entry {index + 1} by thread {threading.current_thread().name} ---")

            topic = quiz_data.get('topic')
            description = quiz_data.get('description', '')
            num_questions = quiz_data.get('num_questions')
            level = quiz_data.get('level')

            if not all([topic, num_questions, level]):
                print(f"Skipping entry {index + 1} due to missing required data (topic, num_questions, or level): {quiz_data}")
                q.task_done()
                continue

            # Check if the quiz topic and level already exist in MongoDB
            existing_quiz = mongoio.eval_collections.find_one({
                "meta.input_information.submit_info.topic": topic,
                "meta.input_information.submit_info.level": level
            })

            if existing_quiz:
                print(f"Quiz for topic '{topic}' at level '{level}' already exists (Doc ID: {existing_quiz['meta']['doc_id']}). Skipping submission.")
                q.task_done()
                continue # Skip to the next item in the queue

            doc_id = util.generate_quiz_id()
            submission_id = util.generate_submission_id()

            submit_info = {
                "submit_type": "autoquiz",
                "doc_id": doc_id,
                "submission_id": submission_id,
                "user_id": USER_ID,
                "topic": topic,
                "description": description,
                "num_questions": num_questions,
                "level": level,
            }

            print(f"Submitting quiz generation request for topic: '{topic}' (Entry {index + 1})...")
            submit_response = api.submit(submit_info)

            if submit_response['status'] is True:
                task_id = submit_response['task_id']
                print(f"Request submitted successfully for '{topic}' (Task ID: {task_id}). Waiting for completion...")

                retries = 0
                task_succeeded = False
                while retries < MAX_RETRIES:
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    retries += 1

                    try:
                        status_data, status_code = api.check_status(task_id)

                        current_state = status_data.get('state')
                        message = status_data.get('msg', 'No specific message.')

                        if current_state == "SUCCESS":
                            print(f"Quiz for '{topic}' (Task ID: {task_id}) completed successfully! Message: {message}")
                            task_succeeded = True
                            break
                        elif current_state in ["PENDING", "PROCESSING"]:
                            print(f"Quiz for '{topic}' (Task ID: {task_id}) is still in '{current_state}' state. Retrying in {CHECK_INTERVAL_SECONDS}s...")
                        else:
                            print(f"Quiz for '{topic}' (Task ID: {task_id}) failed or revoked. State: '{current_state}', Message: {message}")
                            break
                    except Exception as e:
                        print(f"Error checking status for Task ID {task_id}: {e}. Retrying...")

                if not task_succeeded:
                    print(f"Quiz for '{topic}' (Task ID: {task_id}) did NOT complete successfully within {MAX_RETRIES * CHECK_INTERVAL_SECONDS} seconds.")
            else:
                print(f"Failed to submit initial request for topic: '{topic}'. Message: {submit_response['msg']}")

        finally:
            q.task_done()

if __name__ == "__main__":
    work_queue = queue.Queue()

    try:
        with open(JSON_FILE_PATH, 'r') as f:
            list_of_quiz_dicts = json.load(f)
        print(f"Successfully loaded data from {JSON_FILE_PATH}")

        total_quizzes_to_submit = len(list_of_quiz_dicts)
        required_credits = total_quizzes_to_submit * QUIZ_GENERATION_COST

        # --- Perform Credit Check for all quizzes before starting threads ---
        print(f"Checking user credits for '{USER_ID}'...")
        has_credits, message = check_user_credits(USER_ID, required_credits)

        if not has_credits:
            print(f"\nError: {message}")
            print(f"You need {required_credits} credits to submit all {total_quizzes_to_submit} quizzes.")
            sys.exit(1) # Exit the script if credits are insufficient
        else:
            print(f"\nCredit check passed. Available credits meet the required {required_credits} for {total_quizzes_to_submit} quizzes.")
        # --- End Credit Check ---

        # Populate the queue with all quiz entries
        for index, quiz_data in enumerate(list_of_quiz_dicts):
            work_queue.put((quiz_data, index))

        threads = []
        num_threads = min(MAX_THREADS, total_quizzes_to_submit)
        print(f"Starting {num_threads} worker threads...")

        # Create and start worker threads
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(work_queue,), name=f"Worker-{i+1}")
            thread.daemon = True
            threads.append(thread)
            thread.start()

        # Wait for all tasks in the queue to be processed
        work_queue.join()
        print("\nAll quiz processing tasks have completed.")

    except FileNotFoundError:
        print(f"Error: The JSON file '{JSON_FILE_PATH}' was not found.")
        print(f"Please ensure the file exists at the specified path (e.g., '{JSON_FILE_PATH}').")
    except json.JSONDecodeError:
        print(f"Error: The file '{JSON_FILE_PATH}' contains invalid JSON.")
        print("Please ensure the JSON file is correctly formatted.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")