from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import db
from app.models import User
from app.utils import log_activity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("هذا الحساب معطّل، يرجى التواصل مع المسؤول", "warning")
            return render_template("auth/login.html")

        login_user(user, remember=remember)
        user.last_login = datetime.utcnow()
        log_activity("LOGIN", description=f"تسجيل دخول: {user.full_name}")

        # إنشاء جلسة وإشعارات انتهاء التوكيلات
        from app.routes.sessions import create_session
        token = create_session(user.id)

        from app.routes.notifications import create_expiry_notifications
        create_expiry_notifications()

        db.session.commit()

        next_page = request.args.get("next")
        response  = make_response(redirect(next_page or url_for("dashboard.index")))
        response.set_cookie("session_token", token, httponly=True, samesite="Lax",
                            max_age=60*60*24*7)  # 7 days
        return response

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    # أنهي الجلسة الحالية
    token = request.cookies.get("session_token")
    if token:
        from app.models import UserSession
        s = UserSession.query.filter_by(session_token=token, is_active=True).first()
        if s:
            s.is_active = False
            db.session.commit()

    log_activity("LOGOUT", description=f"تسجيل خروج: {current_user.full_name}")
    db.session.commit()
    logout_user()
    flash("تم تسجيل الخروج بنجاح", "success")
    response = make_response(redirect(url_for("auth.login")))
    response.delete_cookie("session_token")
    return response
