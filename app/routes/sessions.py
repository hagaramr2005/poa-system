"""
sessions.py — إدارة جلسات المستخدم
- عرض الأجهزة المتصلة
- إنهاء جلسة محددة أو كل الجلسات
"""
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user, logout_user
from app import db
from app.models import UserSession

sessions_bp = Blueprint("sessions", __name__, url_prefix="/sessions")


def _parse_device(user_agent_str):
    """استخراج اسم الجهاز/المتصفح من User-Agent."""
    ua = user_agent_str or ""
    browser = "متصفح غير معروف"
    os_name = "نظام غير معروف"

    if "Chrome" in ua and "Edg" not in ua and "OPR" not in ua:
        browser = "Chrome"
    elif "Firefox" in ua:
        browser = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua:
        browser = "Safari"
    elif "Edg" in ua:
        browser = "Edge"
    elif "OPR" in ua or "Opera" in ua:
        browser = "Opera"

    if "Windows" in ua:   os_name = "Windows"
    elif "Android" in ua: os_name = "Android"
    elif "iPhone" in ua:  os_name = "iPhone"
    elif "iPad" in ua:    os_name = "iPad"
    elif "Mac" in ua:     os_name = "macOS"
    elif "Linux" in ua:   os_name = "Linux"

    return f"{browser} / {os_name}"


def create_session(user_id):
    """ينشئ جلسة جديدة ويرجع الـ token."""
    token = uuid.uuid4().hex
    ua    = request.headers.get("User-Agent", "")
    db.session.add(UserSession(
        user_id      = user_id,
        session_token= token,
        ip_address   = request.remote_addr,
        user_agent   = ua[:512],
        device_name  = _parse_device(ua),
        created_at   = datetime.utcnow(),
        last_active  = datetime.utcnow(),
        is_active    = True,
    ))
    return token


def refresh_session(token):
    """يحدّث last_active للجلسة الحالية."""
    if token:
        s = UserSession.query.filter_by(session_token=token, is_active=True).first()
        if s:
            s.last_active = datetime.utcnow()
            db.session.commit()


# ── Views ─────────────────────────────────────────────────────────────────────

@sessions_bp.route("/")
@login_required
def index():
    active_sessions = UserSession.query.filter_by(
        user_id=current_user.id, is_active=True
    ).order_by(UserSession.last_active.desc()).all()

    current_token = request.cookies.get("session_token")
    return render_template("sessions/index.html",
                           sessions=active_sessions,
                           current_token=current_token)


@sessions_bp.route("/<int:session_id>/revoke", methods=["POST"])
@login_required
def revoke(session_id):
    s = UserSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    s.is_active = False
    db.session.commit()
    flash("تم إنهاء الجلسة بنجاح", "success")
    return redirect(url_for("sessions.index"))


@sessions_bp.route("/revoke-all", methods=["POST"])
@login_required
def revoke_all():
    current_token = request.cookies.get("session_token")
    # أنهي كل الجلسات ماعدا الحالية
    UserSession.query.filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.session_token != current_token,
    ).update({"is_active": False})
    db.session.commit()
    flash("تم إنهاء جميع الجلسات الأخرى", "success")
    return redirect(url_for("sessions.index"))
