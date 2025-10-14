# app.py

import os
import time
from dotenv import load_dotenv
from datetime import timedelta, datetime, timezone

from flask import (
    Flask, render_template, request, session, jsonify,
    abort, redirect, url_for, make_response, send_from_directory
)

from src.pages.autoquiz import autoquiz
from src.pages.loading import Loading
from src.pages.assessment import Assessment
from src.pages.quiz import Quiz
from src.pages.bank import Bank
from src.pages.account import Account
from src.api import API
from src.util import Util
from src.mongoio import MongoIO
from src.googleauth import GoogleAuth
from src.sitemap_generator import SitemapGenerator

def create_app():
    load_dotenv()
    app = Flask(__name__, static_folder='static')
    # ─── Configuration ────────────────────────────────────────────────
    app.secret_key = os.getenv('KATABUN_KEY', 'dev-secret')
    app.permanent_session_lifetime = timedelta(days=30)

    # ─── Cookie Jar Safety ──────────────────────────────────────
    katabun_env = os.getenv('KATABUN_ENV_TYPE')
    if katabun_env not in ["PROD", "DEV"]:
        raise ValueError('Unknown KATABUN_ENV_TYPE setting')
    elif katabun_env == "PROD":
        app.config['SESSION_COOKIE_SECURE'] = True  # Only over HTTPS
        app.config['SESSION_COOKIE_HTTPONLY'] = True  # JS can’t access
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Prevent CSRF

    app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

    # ─── Extensions / Singletons ──────────────────────────────────────
    # instantiates GoogleAuth once, discovery only when needed
    google_auth = GoogleAuth(app)
    # you can store it if you like: app.extensions['google_auth'] = google_auth

    # ─── Cost for service ──────────────────────────────────────────────
    app.config["QUIZ_GENERATION_COST"] = 5
    app.config["ASSESSMENT_GENERATION_COST"] = 5
    app.config["SIGNUP_CREDIT"] = 30

    # ─── Context Define ───────────────────────────────────────────────
    @app.context_processor
    def inject_ga4_key():
        ga4_key = os.getenv("GOOGLE_ANALYTICS_KEY")
        return {"ga_key": ga4_key} if ga4_key else {}

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

    # ─── 1. Core App & SEO Routes ───────────────────────────────────
    @app.route('/')
    def landing_page():
        mongoio = MongoIO()
        top_quizzes = mongoio.get_top_n_popular_quizzes(9)
        return render_template('page/landing/landing.html', top_quizzes=top_quizzes)

    @app.route('/sitemap.xml')
    def sitemap():
        """
        This route generates and serves the dynamic sitemap.xml file.
        """
        try:
            generator = SitemapGenerator()
            sitemap_xml = generator.generate_sitemap()

            # Create a response object with the correct XML content type
            response = make_response(sitemap_xml)
            response.headers['Content-Type'] = 'application/xml'

            return response
        except Exception as e:
            # Log the error and return a 500 status in case of failure
            app.logger.error(f"Sitemap generation failed: {e}")
            abort(500)

    @app.route("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, "robots.txt", mimetype="text/plain")
    
    # ─── 2. Authentication & User Account Routes ─────────────────────
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

    @app.route('/delete_account', methods=['POST'])
    def delete_account():
        count = google_auth.delete_user()
        session.clear()
        return redirect(url_for('landing_page'))

    # ─── 3. Quiz Generation & Core Flow Routes ───────────────────────
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
        quiz_slug = None
        if doc_type == 'autoquiz' and doc_id:
            mongoio = MongoIO()
            quiz_slug = mongoio.get_quiz_slug(doc_id)
        return render_template(
            'page/loading/success.html',
            doc_id=doc_id, doc_type=doc_type,
            task_url=task_url, message=msg,
            quiz_slug=quiz_slug
        )

    # ─── 4. Quiz Interaction & Results Routes ────────────────────────
    @app.route('/quiz/<slug>', methods=['GET', 'POST'])
    def quiz_page(slug):
        mongoio = MongoIO()
        document, _ = mongoio.load_eval_document_by_slug(slug)

        if document is None:
            document, _ = mongoio.load_eval_document(slug)
            if document is None:
                abort(404, description=f"Unknown Quiz:{slug}")

        doc_meta = document.get('meta', {})
        doc_id = doc_meta.get('doc_id')
        canonical_slug = doc_meta.get('slug') or slug

        if request.method == 'GET':
            if canonical_slug != slug:
                return redirect(url_for('quiz_page', slug=canonical_slug), code=301)

            qz = Quiz()
            questions, info = qz.give_mcq_question(doc_id=doc_id, document=document)
            user_id = Util().get_user_id()
            assessment_id = Util().generate_assessment_id()
            toggle_info = qz.toggle_status()

            return render_template(
                'page/quiz/mcq.html',
                doc_id=doc_id,
                quiz_slug=canonical_slug,
                user_id=user_id,
                assessment_id=assessment_id,
                mcq_questions=questions,
                toggle_info=toggle_info,
                quiz_title=info['title'],
                quiz_description=info['description']
            )
        else:
            quiz_obj = Quiz()
            resp = quiz_obj.capture_usr_respond(request)
            return quiz_obj.submit_usr_respond(resp)

    @app.route('/assessment/<assessment_id>', methods=['GET', 'POST'])
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

    # ─── 5. Content Discovery Routes ─────────────────────────────────
    @app.route('/bank/', defaults={'category': None})
    @app.route('/bank/<category>')
    def bank_page(category):
        if category is None:
            return render_template('page/bank/bank.html')

        page = request.args.get('page', 1, type=int)
        loggedin = session.get('user_login')
        cat = category.lower()
        bank = Bank()
        mongoio = MongoIO()
        if cat not in bank.give_allowed_categories():
            abort(404)
        meta = bank.give_genre_ls(cat)
        top_quizzes = mongoio.get_top_n_popular_quizzes(3, genre=cat)
        return render_template(
            'page/bank/sub.html',
            catmeta_ls=meta,
            category=cat,
            loggedin=loggedin,
            page=page,
            top_quizzes=top_quizzes
        )

    # ─── 6. Informational & Static Pages ─────────────────────────────
    @app.route('/ibl')
    def ibl_page():
        return render_template('page/ibl/ibl.html')

    @app.route('/about')
    def about_page():
        return render_template('page/others/about.html')

    @app.route('/payment', methods=['GET', 'POST'])
    def payment_page():
        if request.method == 'POST':
            mongoio = MongoIO()
            willing_to_pay = request.form.get('willing_to_pay')
            feedback_data = {
                "feedback_id": Util().generate_feedback_id(),
                "user_id": session.get('user_id', 'anonymous'),
                "willing_to_pay": willing_to_pay,
                "geolocation": {
                    "latitude": request.form.get('latitude'),
                    "longitude": request.form.get('longitude')
                },
                "timezone": request.form.get('timezone'),
                "submitted_at": datetime.now(timezone.utc)
            }

            if willing_to_pay == 'no':
                feedback_data['suggested_prices'] = {
                    '30_credits': request.form.get('price_30_credits'),
                    '100_credits': request.form.get('price_100_credits'),
                    '500_credits': request.form.get('price_500_credits'),
                    '1500_credits': request.form.get('price_1500_credits'),
                }

            mongoio.save_form_submission(feedback_data, 'pricing_feedback')
            return redirect(url_for('submission_success_page'))

        return render_template('page/others/payment.html')

    # ─── 7. Contact, Feedback & Legal Routes ─────────────────────────
    @app.route('/contact', methods=['GET', 'POST'])
    def contact_page():
        if request.method == 'POST':
            inquiry_data = {
                "inquiry_id": Util().generate_inquiry_id(),
                "name": request.form.get('name'),
                "email": request.form.get('email'),
                "subject": request.form.get('subject'),
                "message": request.form.get('message'),
                "submitted_at": datetime.now(timezone.utc)
            }
            mongoio = MongoIO()
            mongoio.save_form_submission(inquiry_data, '4urClass_inquiries')
            return redirect(url_for('submission_success_page'))

        return render_template('page/contact/contactus.html')

    @app.route('/feedback', methods=['GET', 'POST'])
    def feedback_page():
        if request.method == 'POST':
            feedback_data = {
                "feedback_id": Util().generate_feedback_id(),
                "relevance": request.form.get('relevance'),
                "easeOfUse": request.form.get('easeOfUse'),
                "recommend": request.form.get('recommend'),
                "suggestions": request.form.get('suggestions'),
                "newsletter": True if request.form.get('newsletter') == 'on' else False,
                "submitted_at": datetime.now(timezone.utc)
            }
            mongoio = MongoIO()
            mongoio.save_form_submission(feedback_data, '4urClass_feedback')
            return redirect(url_for('submission_success_page'))

        return render_template('page/contact/feedback.html')

    @app.route('/thank-you')
    def submission_success_page():
        return render_template('page/contact/success.html')

    @app.route('/log_interest/<feature>')
    def log_interest(feature):
        user_id = session.get('user_id')
        if user_id:
            mongoio = MongoIO()
            mongoio.log_user_interest(user_id, feature)
        return redirect(url_for('submission_success_page'))

    @app.route('/tnc')
    def tnc_page():
        return render_template('page/others/tnc.html')

    @app.route('/privacy-policy')
    def privacy_policy_page():
        return render_template('page/others/privacy_policy.html')

    @app.route('/cookie-policy')
    def cookie_policy_page():
        return render_template('page/others/cookie_policy.html')

    @app.route('/disclaimer')
    def disclaimer_page():
        return render_template('page/others/disclaimer.html')

    # ─── 8. API & Asynchronous Task Routes ───────────────────────────
    @app.route('/check_submission_status/<task_id>')
    def check_submission_status(task_id):
        try:
            return API().check_status(task_id)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ─── 9. Error Handlers ───────────────────────────────────────────
    @app.errorhandler(404)
    def page_not_found(e):
        msg = getattr(e, 'description', '')
        return render_template('page/error/404.html', message=msg), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # You can add logging here to log the error
        return render_template('page/error/503.html'), 500

    @app.route('/error/503')
    def service_unavailable_route():
        return render_template('page/error/503.html'), 503

    return app


# WSGI entrypoint for Gunicorn/uWSGI + Nginx
application = create_app()
