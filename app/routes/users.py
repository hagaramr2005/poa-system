import os, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.models import User
from app.utils import admin_required, log_activity, allowed_avatar, save_avatar

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/avatar/<filename>")
@login_required
def serve_avatar(filename):
    from flask import current_app
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "avatars")
    return send_from_directory(folder, filename)


@users_bp.route("/")
@login_required
@admin_required
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users/list.html", users=users)


@users_bp.route("/new", methods=["GET","POST"])
@login_required
@admin_required
def create():
    if request.method == "POST":
        username=request.form.get("username","").strip(); full_name=request.form.get("full_name","").strip()
        email=request.form.get("email","").strip(); password=request.form.get("password",""); role=request.form.get("role","employee")
        errors = []
        if not username: errors.append("اسم المستخدم مطلوب")
        elif User.query.filter_by(username=username).first(): errors.append("اسم المستخدم موجود مسبقاً")
        if not full_name: errors.append("الاسم الكامل مطلوب")
        if not email: errors.append("البريد الإلكتروني مطلوب")
        elif User.query.filter_by(email=email).first(): errors.append("البريد الإلكتروني موجود مسبقاً")
        if not password or len(password) < 6: errors.append("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        if errors:
            for e in errors: flash(e,"danger")
            return render_template("users/form.html", user=None, form_data=request.form)
        avatar_filename = None
        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename and allowed_avatar(avatar_file.filename):
            from flask import current_app
            avatar_filename = save_avatar(avatar_file, upload_folder=current_app.config["UPLOAD_FOLDER"])
        user = User(username=username, full_name=full_name, email=email,
                    password_hash=generate_password_hash(password), role=role, is_active=True,
                    avatar_filename=avatar_filename)
        db.session.add(user)
        log_activity("CREATE","user",None,f"إضافة مستخدم: {username}")
        db.session.commit(); flash("تم إنشاء المستخدم بنجاح","success")
        return redirect(url_for("users.index"))
    return render_template("users/form.html", user=None, form_data={})


@users_bp.route("/<int:user_id>/edit", methods=["GET","POST"])
@login_required
@admin_required
def edit(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == "POST":
        full_name=request.form.get("full_name","").strip(); email=request.form.get("email","").strip()
        role=request.form.get("role","employee"); is_active=request.form.get("is_active")=="1"
        password=request.form.get("password","").strip()
        errors = []
        if not full_name: errors.append("الاسم الكامل مطلوب")
        if User.query.filter(User.email==email, User.id!=user_id).first(): errors.append("البريد الإلكتروني مستخدم")
        if errors:
            for e in errors: flash(e,"danger")
            return render_template("users/form.html", user=user, form_data=request.form)
        # صورة جديدة
        from flask import current_app
        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename and allowed_avatar(avatar_file.filename):
            user.avatar_filename = save_avatar(avatar_file, old_filename=user.avatar_filename,
                                               upload_folder=current_app.config["UPLOAD_FOLDER"])
        # حذف الصورة
        if request.form.get("remove_avatar") == "1" and user.avatar_filename:
            old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "avatars", user.avatar_filename)
            if os.path.exists(old_path): os.remove(old_path)
            user.avatar_filename = None
        user.full_name=full_name; user.email=email; user.role=role; user.is_active=is_active
        if password and len(password) >= 6: user.password_hash = generate_password_hash(password)
        log_activity("UPDATE","user",user_id,f"تعديل مستخدم: {user.username}")
        db.session.commit(); flash("تم تحديث بيانات المستخدم","success")
        return redirect(url_for("users.index"))
    return render_template("users/form.html", user=user, form_data={})


@users_bp.route("/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("لا يمكنك تعطيل حسابك الخاص","danger")
        return redirect(url_for("users.index"))
    user.is_active = not user.is_active
    action = "تفعيل" if user.is_active else "تعطيل"
    log_activity("UPDATE","user",user_id,f"{action} مستخدم: {user.username}")
    db.session.commit(); flash(f"تم {action} المستخدم {user.username}","success")
    return redirect(url_for("users.index"))


@users_bp.route("/change-password", methods=["GET","POST"])
@login_required
def change_password():
    from werkzeug.security import check_password_hash
    if request.method == "POST":
        current_pw=request.form.get("current_password",""); new_pw=request.form.get("new_password",""); confirm_pw=request.form.get("confirm_password","")
        if not check_password_hash(current_user.password_hash, current_pw): flash("كلمة المرور الحالية غير صحيحة","danger")
        elif len(new_pw) < 6: flash("كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل","danger")
        elif new_pw != confirm_pw: flash("كلمة المرور الجديدة غير متطابقة","danger")
        else:
            current_user.password_hash = generate_password_hash(new_pw)
            log_activity("UPDATE","user",current_user.id,"تغيير كلمة المرور")
            db.session.commit(); flash("تم تغيير كلمة المرور بنجاح","success")
            return redirect(url_for("dashboard.index"))
    return render_template("users/change_password.html")
