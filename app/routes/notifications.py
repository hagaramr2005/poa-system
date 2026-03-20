"""
notifications.py — نظام الإشعارات الداخلية
- API للقراءة والتعليم كمقروءة
- دالة create_expiry_notifications() تُشغَّل عند الدخول لإنشاء إشعارات التوكيلات
"""
from datetime import date, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Notification, PowerOfAttorney, User

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


# ── إنشاء إشعارات انتهاء التوكيلات (تُستدعى من auth عند الدخول) ─────────────
def create_expiry_notifications():
    """
    ينشئ إشعارات للتوكيلات التي ستنتهي خلال 7 و30 يوم.
    يتجنب التكرار — لو الإشعار موجود بالفعل لنفس التوكيل اليوم لا يُنشئ جديد.
    """
    admins = User.query.filter_by(role="admin", is_active=True).all()
    if not admins:
        return

    today = date.today()

    # التوكيلات التي ستنتهي خلال 7 أيام
    urgent = PowerOfAttorney.query.filter(
        PowerOfAttorney.is_deleted == False,
        PowerOfAttorney.expiry_date != None,
        PowerOfAttorney.expiry_date >= today,
        PowerOfAttorney.expiry_date <= today + timedelta(days=7),
        PowerOfAttorney.status != "منتهي",
    ).all()

    # التوكيلات التي ستنتهي خلال 8-30 يوم
    soon = PowerOfAttorney.query.filter(
        PowerOfAttorney.is_deleted == False,
        PowerOfAttorney.expiry_date != None,
        PowerOfAttorney.expiry_date >= today + timedelta(days=8),
        PowerOfAttorney.expiry_date <= today + timedelta(days=30),
        PowerOfAttorney.status != "منتهي",
    ).all()

    for admin in admins:
        for poa in urgent:
            remaining = (poa.expiry_date - today).days
            _ensure_notification(
                user_id   = admin.id,
                ref_key   = f"expiry_urgent_{poa.id}_{today.isoformat()}",
                title     = f"⚠️ توكيل ينتهي خلال {remaining} يوم",
                body      = f"التوكيل #{poa.office_number} — {poa.client_name} | {poa.poa_title}",
                type      = "danger",
                link      = f"/poa/{poa.id}",
            )

        for poa in soon:
            remaining = (poa.expiry_date - today).days
            _ensure_notification(
                user_id   = admin.id,
                ref_key   = f"expiry_soon_{poa.id}_{today.isoformat()}",
                title     = f"توكيل ينتهي خلال {remaining} يوم",
                body      = f"التوكيل #{poa.office_number} — {poa.client_name} | {poa.poa_title}",
                type      = "warning",
                link      = f"/poa/{poa.id}",
            )

    db.session.commit()


def _ensure_notification(user_id, ref_key, title, body, type, link):
    """لا ينشئ إشعار مكرر لنفس ref_key في نفس اليوم."""
    existing = Notification.query.filter_by(
        user_id=user_id, title=title, is_read=False
    ).filter(Notification.body == body).first()
    if not existing:
        db.session.add(Notification(
            user_id=user_id, title=title, body=body, type=type, link=link
        ))


def push_notification(user_id, title, body="", type="info", link=None):
    """إرسال إشعار لمستخدم محدد — تُستدعى من أي route."""
    notif = Notification(user_id=user_id, title=title, body=body, type=type, link=link)
    db.session.add(notif)


# ── API ───────────────────────────────────────────────────────────────────────

@notifications_bp.route("/")
@login_required
def list_notifications():
    notifs = current_user.notifications.order_by(
        Notification.is_read.asc(), Notification.created_at.desc()
    ).limit(30).all()
    return jsonify({
        "unread": current_user.unread_notifications_count,
        "items":  [n.to_dict() for n in notifs],
    })


@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    n.is_read = True
    db.session.commit()
    return jsonify({"ok": True, "unread": current_user.unread_notifications_count})


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    current_user.notifications.filter_by(is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True, "unread": 0})


@notifications_bp.route("/<int:notif_id>", methods=["DELETE"])
@login_required
def delete_notification(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    db.session.delete(n); db.session.commit()
    return jsonify({"ok": True})
