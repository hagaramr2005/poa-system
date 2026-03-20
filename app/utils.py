import os, uuid
from functools import wraps
from flask import request, abort
from flask_login import current_user
from app import db
from app.models import ActivityLog

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "gif", "doc", "docx"}
AVATAR_EXTENSIONS  = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_avatar(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in AVATAR_EXTENSIONS

def secure_save_file(file, upload_folder):
    original_name = file.filename
    ext = original_name.rsplit(".", 1)[1].lower() if "." in original_name else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, unique_name))
    return unique_name, original_name

def save_avatar(file, old_filename=None, upload_folder=None):
    from flask import current_app
    folder = os.path.join(upload_folder or current_app.config["UPLOAD_FOLDER"], "avatars")
    os.makedirs(folder, exist_ok=True)
    if old_filename:
        old_path = os.path.join(folder, old_filename)
        if os.path.exists(old_path): os.remove(old_path)
    ext = file.filename.rsplit(".", 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(folder, new_name))
    return new_name

def log_activity(action, entity_type=None, entity_id=None, description=None):
    user_id = current_user.id if current_user.is_authenticated else None
    db.session.add(ActivityLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id, description=description, ip_address=request.remote_addr,
    ))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated
