from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import ActivityLog
from app.utils import admin_required

activity_bp = Blueprint("activity", __name__, url_prefix="/activity")


@activity_bp.route("/")
@login_required
@admin_required
def index():
    page = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action", "").strip()
    q = ActivityLog.query.order_by(ActivityLog.created_at.desc())
    if action_filter:
        q = q.filter(ActivityLog.action == action_filter)
    pagination = q.paginate(page=page, per_page=50, error_out=False)
    return render_template("activity/list.html", pagination=pagination, action_filter=action_filter)
