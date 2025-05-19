#Bismillahhirahmannirahim
from flask import redirect, url_for

from src.util import Util
from src.api import API
from src.pages.loading import Loading


class autoquiz:

    def __init__(self):
        pass

    def submit_form(self, request):

        topic = request.form.get('topic')
        description = request.form.get('description', '')  # Optional field
        num_questions = request.form.get('numQuestions')
        level = request.form.get('level')

        message = 'Processing your request'
        flag = True
        if not request.form.get('agreeTnC'):
            flag = False
            message = 'You must agree to the Terms and Conditions.'

        submit_info = {}
        quiz_id = ''
        if flag is True:
            quiz_id = Util().generate_quiz_id()
            submission_id = Util().generate_submission_id()
            user_id = Util().get_user_id()

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

        load_info = {
            'flag': flag,
            'message': message,
            'doc_id': quiz_id,
            'doc_type': 'autoquiz'
        }

        api = API()
        respond = api.submit(submit_info)

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

