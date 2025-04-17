import os
import time

from flask import Flask, render_template, request, session, jsonify, abort

from src.pages.autoquiz import autoquiz
from src.pages.loading import loading
from src.pages.assessment import assessment
from src.pages.quiz import Quiz
from src.pages.bank import Bank
from src.api import API
from src.util import util
from src.mongoio import MongoIO

app = Flask(__name__)
app.secret_key = os.getenv('katabun_key')


@app.before_request
def assign_user_id():
    if request.path.startswith('/static'):
        return

    if 'user_id' not in session:
        session['user_id'] = util().generate_user_id()
        session['user_id_creation_time'] = time.time()


@app.route('/')
def landing_page():
    return render_template('page/landing/landing.html')


@app.route('/autoquiz', methods=['GET', 'POST'])
def autoquiz_page():
    if request.method == 'POST':
        return autoquiz().submit_form(request)
    return render_template('page/autogenerator/autoquiz.html')


@app.route('/guidedquiz')
def guidedquiz_page():
    return render_template('page/guidedgenerator/guidedquiz.html')


@app.route('/loading/<loadstr>')
def loading_page(loadstr):
    flag, message, doc_id, doc_type, task_url = loading().processing_request(loadstr)

    if flag is False:
        return render_template('page/loading/failed.html',
                               message=message)
    return render_template('page/loading/success.html',
                           doc_id=doc_id,
                           doc_type=doc_type,
                           task_url=task_url,
                           message=message)


@app.route('/quiz/<doc_id>', methods=['GET', 'POST'])
def quiz_page(doc_id):

    if request.method == 'GET':
        mongoio = MongoIO()
        if not mongoio.document_exists(doc_id, doc_type='eval'):
            return abort(404, description=f"Unknown Doc-ID:{doc_id}")
        mcq_question_ls, info_dic = Quiz().give_mcq_question(doc_id)
        util_obj = util()
        user_id = util_obj.get_user_id()
        assessment_id = util_obj.generate_assessment_id()
        return render_template('page/quiz/mcq.html',
                               doc_id=doc_id,
                               user_id=user_id,
                               assessment_id=assessment_id,
                               mcq_questions=mcq_question_ls,
                               quiz_title=info_dic['title'])

    if request.method == 'POST':
        quiz_obj = Quiz()
        usr_respond_dic = quiz_obj.capture_usr_respond(request)
        return quiz_obj.submit_usr_respond(usr_respond_dic)


@app.route('/assessment/<assessment_id>', methods=['GET', 'POST'])
def assessment_page(assessment_id):

    #TODO create document does not exist page
    mongoio = MongoIO()
    if not mongoio.document_exists(assessment_id, doc_type='assessment'):
        return abort(404, description=f"Unknown Doc-ID:{assessment_id}")

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        assessment_id = request.form.get('assessment_id')

        if not user_id or not assessment_id:
            return abort(400, description="Missing user_id or assessment_id in the request.")

        asst_obj = assessment()
        assessment_info = asst_obj.validate_answer(request)
        feedback_info = asst_obj.get_feedback(request)
        asst_obj.cache_assessment_data(assessment_id, assessment_info, feedback_info)
        return asst_obj.call_loading_page(assessment_id)

    if request.method == 'GET':
        asst_obj = assessment()
        answer_script, advice_dict, overall_dict = asst_obj.load_assessment_data(assessment_id)
        print(advice_dict)
        return render_template('page/assessment/assessment.html',
                               answer_script=answer_script,
                               advice_dict=advice_dict,
                               overall_dict=overall_dict
                               )


@app.route('/bank/', defaults={'category': None})
@app.route('/bank/<category>')
def bank_page(category):
    if category is None:
        return render_template('page/bank/bank.html')
    else:
        category = category.lower()
        bank_obj = Bank()
        if category not in bank_obj.give_allowed_categories():
            abort(404)
        catmeta_ls = bank_obj.give_genre_ls(category)
        return render_template('page/bank/sub.html',
                               catmeta_ls=catmeta_ls,
                               category=category)


@app.route('/about')
def about_page():
    return render_template('page/others/about.html')


@app.route('/contact')
def contact_page():
    return render_template('page/contact/contactus.html')


@app.route('/feedback')
def feedback_page():
    return render_template('page/contact/feedback.html')


@app.route('/tnc')
def tnc_page():
    return render_template('page/others/tnc.html')


@app.route('/account')
def account_page():
    return render_template('/page/account/account.html')


@app.route('/check_submission_status/<task_id>', methods=['GET'])
def check_submission_status(task_id):
    try:
        response = API().check_status(task_id)
        return response

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    message = ''
    if e.description:
        message = e.description
    return render_template('page/error/404.html', message=message), 404


@app.route('/error/503')
def service_unavailable_route():
    return render_template('page/error/503.html'), 503


if __name__ == '__main__':
    app.run(debug=True)