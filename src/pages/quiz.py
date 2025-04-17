#Bismillahirahmannirahim
from src.api import API
from src.mongoio import MongoIO
from src.pages.loading import loading

from flask import redirect, url_for
class Quiz:
    def __init__(self):
        self.mongoio = MongoIO()
        self.mongo_cfg = self.mongoio.mongo_cfg

    def give_mcq_question(self, doc_id):

        doc, _ = self.mongoio.load_eval_document(doc_id)
        if doc is None:
            raise IOError(f'Doc_id: {doc_id} is not found in DB')

        ques_dic = doc['questions']
        meta_dic = doc['meta']
        info_dic = {'title': meta_dic['title']}

        qix = 0
        quiz_data_ls = []
        prefixs = ['(A) ', '(B) ', '(C) ', '(D) ']
        for item in ques_dic:
            decorated_choices = [pre + chc for pre, chc in zip(prefixs, item['choices_list'])]
            quiz_data_ls.append({
                'question_index': qix,
                'question': item['question'],
                'choices': decorated_choices,
                'qid': item['qid']
            })
            qix += 1
        return list(enumerate(quiz_data_ls)), info_dic

    def capture_usr_respond(self, request):
        """
        Capture all quiz info submitted by the user dynamically and format it into the specified JSON structure.

        """

        # Retrieve static hidden inputs
        user_id = request.form.get("user_id")
        doc_id = request.form.get("doc_id")
        assessment_id = request.form.get("assessment_id")

        responds_dic = {}

        # Dynamically detect all question inputs based on the "question-" prefix
        for key in request.form.keys():
            if key.startswith("question-"):
                question_number = key.split("-")[1]  # Extract the question index

                responds_dic[question_number] = {
                    "usr_answer": int(request.form.get(key)),  # Convert answer index to int
                    "qid": request.form.getlist("qid")[int(question_number)],  # Get corresponding qid
                    "thumbs_up": request.form.get(f"thumbs_up_{question_number}", "0") == "1",
                    "dont_know": request.form.get(f"dont_know_{question_number}", "0") == "1",
                    "flagged": request.form.get(f"flagged_{question_number}", "0") == "1"
                }

        # Capture the optional rating inputs as boolean values
        ratings = {
            "overall_rating": request.form.get("overall_rating") == "yes",
            "relevance_rating": request.form.get("relevance_rating") == "yes",
            "difficulty_rating": request.form.get("difficulty_rating") == "yes"
        }

        usr_respond_dic = {
            'user_id': user_id,
            'eval_id': doc_id,
            'assessment_id': assessment_id,
            'responds': responds_dic,
            'ratings': ratings
        }
        return usr_respond_dic

    def submit_usr_respond(self, usr_respond_dic):
        usr_respond_dic['submit_type'] = 'assessment'

        message = 'Evaluating your answers'
        assessment_id = usr_respond_dic['assessment_id']
        load_info = {
            'flag': True,
            'message': message,
            'doc_id': assessment_id,
            'doc_type': 'assessment'
        }

        api = API()
        respond = api.submit(usr_respond_dic)

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

        encode_str = loading().encode_data(load_info)
        return redirect(url_for('loading_page', loadstr=encode_str))



