import os
import json
import requests
from flask import jsonify

class API:
    def __init__(self):
        api_port = 5500
        katabun_env = os.getenv('KATABUN_ENV_TYPE')
        if katabun_env not in ["PROD", "DEV"]:
            raise ValueError('Unknown flask_env setting')

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
        """
        Query FastAPI `/job/status/<task_id>` and translate every Celery state
        into a single, consistent JSON contract **without importing celery.states**.

        HTTP codes returned
        -------------------
        202  → task not finished yet (PENDING, STARTED, PROGRESS, RETRY)
        200  → task finished successfully (SUCCESS)
        410  → task was cancelled (REVOKED)
        500  → task ended in FAILURE or network error
        400  → anything we can’t interpret
        """
        try:
            endpoint = f"{self.api_base_url}/job/status/{task_id}"
            resp = requests.get(endpoint, timeout=5)
            resp.raise_for_status()  # raises on 4xx / 5xx

            payload = resp.json()  # may raise ValueError
            state = payload.get("state")  # Celery’s task.state
            status = payload.get("status")  # your own status key
            msg = payload.get("msg")

            # -------- map Celery states (as plain strings) to API responses ------
            if state == "PENDING":
                return jsonify({"state": "pending", "msg": msg}), 202

            if state in {"STARTED", "RETRY", "PROGRESS"}:
                return jsonify({"state": "processing", "msg": msg}), 202

            if state == "SUCCESS":
                return jsonify({"state": status or "success", "msg": msg}), 200

            if state == "FAILURE":
                return jsonify({"state": "fail",
                                "msg": msg or "Task failed"}), 500

            if state == "REVOKED":
                return jsonify({"state": "revoked",
                                "msg": msg or "Task was cancelled"}), 410

            # anything else we don’t recognise
            return jsonify({"state": "unknown",
                            "msg": f"Unrecognised Celery state: {state}"}), 400

        # -------- network / server / decoding problems ---------------------------
        except requests.exceptions.RequestException as e:
            return jsonify({"error": "Request to status endpoint failed",
                            "details": str(e)}), 502  # Bad gateway / upstream

        except (ValueError, json.JSONDecodeError):
            return jsonify({"error": "Invalid JSON from status endpoint"}), 502

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