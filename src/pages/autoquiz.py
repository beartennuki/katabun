# src/pages/autoquiz.py (modified)
from flask import redirect, url_for, current_app, session

from src.util import Util
from src.api import API
from src.pages.loading import Loading
from src.credit_checker import CreditChecker

class autoquiz:

    def __init__(self):
        # Initialize the CreditChecker when autoquiz class is instantiated
        self.credit_checker = CreditChecker()

    def submit_form(self, request):
        topic = request.form.get('topic')
        description = request.form.get('description', '')  # Optional field
        num_questions = request.form.get('numQuestions')
        level = request.form.get('level')

        # Get the quiz generation cost from Flask's application configuration
        # Default to 5 if not found, though it should be set in katabun.py
        quiz_cost = current_app.config.get('QUIZ_GENERATION_COST')

        # First, check for T&C agreement
        if not request.form.get('agreeTnC'):
            load_info = {
                'flag': False,
                'message': 'You must agree to the Terms and Conditions.',
                'doc_id': '',  # No doc_id generated yet as submission is halted
                'doc_type': 'autoquiz'
            }
            encode_str = Loading().encode_data(load_info)
            return redirect(url_for('loading_page', loadstr=encode_str))

        # --- Perform Credit Check before proceeding with quiz generation ---
        user_id = session.get('user_id') # Retrieve user_id from session

        has_credits, message = self.credit_checker.has_sufficient_and_active_credits(user_id, quiz_cost)

        if not has_credits:
            # If credit check fails, prepare a redirect to the failed loading page with the error message
            load_info = {
                'flag': False,
                'message': message,
                'doc_id': '',  # No doc_id generated as submission is halted
                'doc_type': 'autoquiz'
            }
            encode_str = Loading().encode_data(load_info)
            return redirect(url_for('loading_page', loadstr=encode_str))
        # --- End Credit Check ---

        # If all checks pass, proceed with generating IDs and submitting to API
        quiz_id = Util().generate_quiz_id()
        submission_id = Util().generate_submission_id()

        submit_info = {
            "submit_type": "autoquiz",
            'doc_id':  quiz_id,
            'submission_id': submission_id,
            'user_id': user_id,
            'topic': topic,
            'description': description,
            'num_questions': num_questions,
            'level': level,
        }

        # Prepare initial loading information
        load_info = {
            'flag': True,
            'message': 'Processing your request',
            'doc_id': quiz_id,
            'doc_type': 'autoquiz'
        }

        api = API()
        respond = api.submit(submit_info) # Submit the request to the backend

        if respond['status'] is True:
            load_info['task_url'] = url_for('check_submission_status',
                                            task_id=respond['task_id'],
                                            _external=True)
            load_info['message'] = load_info['message'] + '\n' + respond['msg']
        elif respond['status'] is False:
            load_info['flag'] = False
            load_info['message'] = load_info['message'] + '\n' + respond['msg']
        else:
            raise ValueError('Unknown respond["status"] value')

        encode_str = Loading().encode_data(load_info)
        return redirect(url_for('loading_page',loadstr=encode_str))