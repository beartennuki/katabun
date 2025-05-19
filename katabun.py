# app.py

import os
import time
from datetime import timedelta, datetime, timezone

from flask import (
    Flask, render_template, request, session, jsonify,
    abort, redirect, url_for
)

from src.pages.autoquiz    import autoquiz
from src.pages.loading     import Loading
from src.pages.assessment  import Assessment
from src.pages.quiz        import Quiz
from src.pages.bank        import Bank
from src.pages.account     import  Account
from src.api               import API
from src.util              import Util
from src.mongoio           import MongoIO
from src.googleauth        import GoogleAuth


def create_app():
    app = Flask(__name__, static_folder='static')
    # ─── Configuration ────────────────────────────────────────────────
    app.secret_key = os.getenv('KATABUN_KEY', 'dev-secret')
    app.permanent_session_lifetime = timedelta(days=30)

    # ─── Cookie Jar Safety ──────────────────────────────────────
    katabun_env = os.getenv('KATABUN_ENV_TYPE')
    if katabun_env not in ["PROD", "DEV"]:
        raise ValueError('Unknown flask_env setting')
    elif katabun_env == "PROD":
        app.config['SESSION_COOKIE_SECURE']     = True  # Only over HTTPS
        app.config['SESSION_COOKIE_HTTPONLY']   = True  # JS can’t access
        app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'  # Prevent CSRF

    app.config['GOOGLE_CLIENT_ID']     = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # ─── Extensions / Singletons ──────────────────────────────────────
    # instantiates GoogleAuth once, discovery only when needed
    google_auth = GoogleAuth(app)
    # you can store it if you like: app.extensions['google_auth'] = google_auth

    # ─── Cost for service ──────────────────────────────────────────────
    app.config["QUIZ_GENERATION_COST"] = 5
    app.config["ASSESSMENT_GENERATION_COST"] = 5
    app.config["SIGNUP_CREDIT"] = 100

    # ─── Request Hooks ───────────────────────────────────────────────
    @app.before_request
    def assign_user_id():
        # skip static files & the auth endpoints
        if request.path.startswith('/static') or request.endpoint in (
            'login', 'auth_callback'
        ):
            return

        expired_str = session.get('expired_login')
        if expired_str:
            expired_time = datetime.fromisoformat(expired_str)
            if datetime.now(timezone.utc) > expired_time:
                session['user_login'] = False

        session.permanent = True
        if 'user_id' not in session:
            session['user_id'] = Util().generate_user_id()
            session['user_id_creation_time'] = time.time()

    # ─── Authentication Routes ───────────────────────────────────────
    @app.route('/login')
    def login():
        return google_auth.login()

    @app.route('/auth/callback')
    def auth_callback():
        return google_auth.callback()

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('account_page'))

    @app.route('/delete_account', methods=['POST'])
    def delete_account():
        count = google_auth.delete_user()
        session.clear()
        return redirect(url_for('landing_page'))

    # ─── Page Routes ─────────────────────────────────────────────────
    @app.route('/')
    def landing_page():
        return render_template('page/landing/landing.html')

    @app.route('/autoquiz', methods=['GET', 'POST'])
    def autoquiz_page():
        if request.method == 'POST':
            return autoquiz().submit_form(request)
        loggedin = session.get('user_login')
        return render_template(
            'page/autogenerator/autoquiz.html',
            loggedin=loggedin
        )

    @app.route('/guidedquiz')
    def guidedquiz_page():
        return render_template('page/guidedgenerator/guidedquiz.html')

    @app.route('/loading/<loadstr>')
    def loading_page(loadstr):
        flag, msg, doc_id, doc_type, task_url = \
            Loading().processing_request(loadstr)
        if not flag:
            return render_template(
                'page/loading/failed.html', message=msg
            )
        return render_template(
            'page/loading/success.html',
            doc_id=doc_id, doc_type=doc_type,
            task_url=task_url, message=msg
        )

    @app.route('/quiz/<doc_id>', methods=['GET','POST'])
    def quiz_page(doc_id):
        mongoio = MongoIO()
        if not mongoio.document_exists(doc_id, doc_type='eval'):
            abort(404, description=f"Unknown Doc-ID:{doc_id}")

        if request.method == 'GET':
            qz = Quiz()
            questions, info = qz.give_mcq_question(doc_id)
            user_id         = Util().get_user_id()
            assessment_id   = Util().generate_assessment_id()
            toggle_info     = qz.toggle_status()

            return render_template(
                'page/quiz/mcq.html',
                doc_id=doc_id,
                user_id=user_id,
                assessment_id=assessment_id,
                mcq_questions=questions,
                toggle_info=toggle_info,
                quiz_title=info['title']
            )
        else:
            quiz_obj = Quiz()
            resp = quiz_obj.capture_usr_respond(request)
            return quiz_obj.submit_usr_respond(resp)

    @app.route('/assessment/<assessment_id>', methods=['GET','POST'])
    def assessment_page(assessment_id):

        if request.method == 'POST':
            return Assessment().resubmit_assessment(assessment_id)
        else:
            mongoio = MongoIO()
            if not mongoio.document_exists(assessment_id, doc_type='assessment'):
                abort(404, description=f"Unknown Doc-ID:{assessment_id}")

            id_check, answer_script, advice, overall = Assessment().load_assessment_data(assessment_id)
            if id_check is False:
                abort(401)
            else:
                loggedin = session.get('user_login')
                return render_template(
                    'page/assessment/assessment.html',
                    answer_script=answer_script,
                    advice_dict=advice,
                    overall_dict=overall,
                    loggedin=loggedin,
                    doc_id=assessment_id
                )

    @app.route('/bank/', defaults={'category': None})
    @app.route('/bank/<category>')
    def bank_page(category):
        if category is None:
            return render_template('page/bank/bank.html')

        loggedin = session.get('user_login')
        cat = category.lower()
        bank = Bank()
        if cat not in bank.give_allowed_categories():
            abort(404)
        meta = bank.give_genre_ls(cat)
        return render_template(
            'page/bank/sub.html',
            catmeta_ls=meta,
            category=cat,
            loggedin=loggedin
        )

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
        if not session.get('user_login'):
            return render_template('page/account/account.html')

        acc_obj = Account()
        user_info = acc_obj.get_user_account_info()
        credit_info = acc_obj.get_user_credit_info()

        return render_template(
            'page/account/account.html',
            user_info=user_info,
            credit_info=credit_info
        )

    @app.route('/check_submission_status/<task_id>')
    def check_submission_status(task_id):
        try:
            return API().check_status(task_id)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.errorhandler(404)
    def page_not_found(e):
        msg = getattr(e, 'description', '')
        return render_template('page/error/404.html', message=msg), 404

    @app.route('/error/503')
    def service_unavailable_route():
        return render_template('page/error/503.html'), 503

    return app


# WSGI entrypoint for Gunicorn/uWSGI + Nginx
application = create_app()