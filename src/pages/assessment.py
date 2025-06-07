# src/pages/assessment.py
from src.api import API
from src.mongoio import MongoIO
from src.pages.loading import Loading
from src.credit_checker import CreditChecker # Import the new CreditChecker

from flask import session, url_for, redirect, current_app # Import current_app for config

class Assessment:

    def __init__(self):
        self.mongoio = MongoIO()
        self.credit_checker = CreditChecker() # Initialize CreditChecker

    def load_assessment_data(self, assessment_id):

        assessment_doc, _ = self.mongoio.load_assessment_document(assessment_id)

        # Check if session user_id == to the recorded user_id
        recorded_user_id = assessment_doc['meta']['user_id']
        if session.get('user_id') != recorded_user_id:
            id_check = False
            answer_script = {}
            advice_dict = {}
            overall_dict = {}
            return id_check, answer_script, advice_dict, overall_dict
        else:
            id_check = True

        assessment_info = assessment_doc['assessment_info']
        advice_dict = assessment_doc['advice_dict']
        eval_id = assessment_doc['meta']['eval_id']
        quiz_meta_dict = self.mongoio.load_eval_document(eval_id, section='meta')
        overall_dict = {
            'title': quiz_meta_dict[0]['title'],
            'right_count': len(assessment_info['correct_qids']),
            'wrong_count': len(assessment_info['wrong_qids']),
            'unsure_count': len(assessment_info['dont_know_qids']),
            'question_count': len(assessment_info['correct_qids']) + len(assessment_info['wrong_qids']),
            'accuracy': assessment_info['accuracy'] * 100
        }
        if 'requested' not in advice_dict.keys():
            advice_dict['requested'] = True
        # Create answer script sorted by question index
        answer_script = []

        # Process correct answers
        for correct in assessment_info['correct_ls']:
            answer_script.append({
                "question_index": correct["question_index"],
                "question": correct["question"],
                "user_answer": correct["correct_answer"],
                "correct_answer": correct["correct_answer"],
                "is_correct": True,
                "explanation": correct["explanation"],
                "flagged": correct['question_flag_info']['flagged'],
                "dont_know": correct['question_flag_info']['dont_know'],
            })

        # Process wrong answers
        for wrong in assessment_info['wrong_ls']:
            answer_script.append({
                "question_index": wrong["question_index"],
                "question": wrong["question"],
                "user_answer": wrong["user_answer"],
                "correct_answer": wrong["correct_answer"],
                "is_correct": False,
                "explanation": wrong["explanation"],
                "flagged": wrong['question_flag_info']['flagged'],
                "dont_know": wrong['question_flag_info']['dont_know'],
            })

        # Sort by question index
        answer_script = sorted(answer_script, key=lambda x: x["question_index"])

        return id_check, answer_script, advice_dict, overall_dict

    def resubmit_assessment(self, assessment_id):
        user_id = session.get('user_id')

        # Get the cost for assessment generation from Flask's application configuration
        # Default to 5 if not found, though it should be set in katabun.py
        assessment_cost = current_app.config.get('ASSESSMENT_GENERATION_COST')

        # --- Perform Credit Check before proceeding with reassessment submission ---
        has_credits, message = self.credit_checker.has_sufficient_and_active_credits(user_id, assessment_cost)

        if not has_credits:
            # If credit check fails, prepare a redirect to the failed loading page with the error message
            load_info = {
                'flag': False,
                'message': message,
                'doc_id': assessment_id, # Still refer to the assessment ID for context
                'doc_type': 'assessment'
            }
            encode_str = Loading().encode_data(load_info)
            return redirect(url_for('loading_page', loadstr=encode_str))
        # --- End Credit Check ---

        reassessment_dic = {
            'user_id'       :user_id,
            'assessment_id' :assessment_id,
            'submit_type'   :'reassessment'
        }

        message = 'Reanalyzing your result'
        load_info = {
            'flag': True,
            'message': message,
            'doc_id': assessment_id,
            'doc_type': 'assessment'
        }

        api = API()
        respond = api.submit(reassessment_dic)

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
        return redirect(url_for('loading_page', loadstr=encode_str))