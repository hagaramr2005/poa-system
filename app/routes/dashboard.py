from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func, extract
from app.models import PowerOfAttorney, ActivityLog, User
from datetime import date, timedelta
from app import db

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    stats = _get_stats()
    return render_template("dashboard/index.html", stats=stats)


@dashboard_bp.route("/api/stats")
@login_required
def api_stats():
    return jsonify(_get_stats())


@dashboard_bp.route("/api/chart/status")
@login_required
def chart_status():
    rows = (
        db.session.query(PowerOfAttorney.status, func.count(PowerOfAttorney.id))
        .filter_by(is_deleted=False)
        .group_by(PowerOfAttorney.status)
        .all()
    )
    return jsonify({"labels": [r[0] for r in rows], "data": [r[1] for r in rows]})


@dashboard_bp.route("/api/chart/yearly")
@login_required
def chart_yearly():
    rows = (
        db.session.query(PowerOfAttorney.year, func.count(PowerOfAttorney.id))
        .filter(PowerOfAttorney.is_deleted == False, PowerOfAttorney.year.isnot(None))
        .group_by(PowerOfAttorney.year)
        .order_by(PowerOfAttorney.year)
        .all()
    )
    return jsonify({"labels": [str(r[0]) for r in rows], "data": [r[1] for r in rows]})


@dashboard_bp.route("/api/chart/activation")
@login_required
def chart_activation():
    rows = (
        db.session.query(PowerOfAttorney.activation_status, func.count(PowerOfAttorney.id))
        .filter_by(is_deleted=False)
        .group_by(PowerOfAttorney.activation_status)
        .all()
    )
    return jsonify({"labels": [r[0] for r in rows], "data": [r[1] for r in rows]})


def _get_stats():
    total = PowerOfAttorney.query.filter_by(is_deleted=False).count()
    active = PowerOfAttorney.query.filter_by(is_deleted=False, status="ساري").count()
    expired = PowerOfAttorney.query.filter_by(is_deleted=False, status="منتهي").count()
    inactive = PowerOfAttorney.query.filter_by(is_deleted=False, activation_status="غير مفعل").count()
    pending = PowerOfAttorney.query.filter_by(is_deleted=False, status="معلق").count()
    expiring_soon = PowerOfAttorney.query.filter(
        PowerOfAttorney.is_deleted == False,
        PowerOfAttorney.expiry_date != None,
        PowerOfAttorney.expiry_date <= date.today() + timedelta(days=30),
        PowerOfAttorney.expiry_date >= date.today(),
    ).count()
    users_count = User.query.filter_by(is_active=True).count()
    recent_logs = (
        ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    )
    logs_data = [
        {
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "description": l.description,
            "user": l.user.full_name if l.user else "النظام",
            "created_at": l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
        }
        for l in recent_logs
    ]
    return {
        "total": total,
        "active": active,
        "expired": expired,
        "inactive": inactive,
        "pending": pending,
        "expiring_soon": expiring_soon,
        "users_count": users_count,
        "recent_logs": logs_data,
    }