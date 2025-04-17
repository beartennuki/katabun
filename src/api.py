import json
import requests
from flask import jsonify

class API:
    def __init__(self):
        # Get API base URL from environment variable or set default
        api_port = 5500
        self.api_base_url = f"http://localhost:{api_port}"

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
        Check quiz submission status by making a GET request.

        :param task_id: Task ID to check the status.
        :return: JSON response with the status of the quiz processing.
        """
        try:
            endpoint = f"{self.api_base_url}/job/status/{task_id}"
            response = requests.get(endpoint)

            # Check for HTTP errors before processing
            if response.status_code != 200:
                return jsonify({
                    "error": f"Failed to fetch status, received {response.status_code}",
                    "details": response.text
                }), response.status_code

            # Correct way to parse JSON
            response_dict = response.json()

            # Extract values safely
            res_state = response_dict.get('state')
            res_status = response_dict.get('status')
            res_msg = response_dict.get('msg', None)

            # Default message
            msg = None

            # Handling different statuses
            if res_state == 'FAILURE' or res_status == 'FAILURE':
                msg = res_msg if res_msg is not None else "Failed to retrieve quiz status"
                return jsonify({
                    'state': 'fail',
                    'msg': msg
                }), 500  # Internal Server Error

            elif res_state == 'PENDING':
                return jsonify({
                    'state': 'pending',
                    'msg': None
                }), 200  # OK

            elif res_state == 'SUCCESS' and res_status == 'SUCCESS':
                return jsonify({
                    'state': 'success',
                    'msg': None
                }), 200  # OK

            else:
                return jsonify({
                    "error": f"Unknown res_state={res_state} and res_status={res_status} value"
                }), 400  # Bad Request

        except requests.exceptions.RequestException as e:
            return jsonify({
                "error": "Request failed",
                "details": str(e)
            }), 500  # Internal Server Error

        except json.JSONDecodeError:
            return jsonify({
                "error": "Invalid JSON response from server"
            }), 500  # Internal Server Error

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