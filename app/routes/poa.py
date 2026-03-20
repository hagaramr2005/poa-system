import os, io
from datetime import datetime, date, timedelta
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, current_app,
                   send_from_directory, send_file, abort)
from flask_login import login_required, current_user
from app import db
from app.models import PowerOfAttorney, Client
from app.utils import allowed_file, secure_save_file, log_activity, admin_required

poa_bp = Blueprint("poa", __name__, url_prefix="/poa")


def _build_search_query():
    q = PowerOfAttorney.query.filter_by(is_deleted=False)
    keyword = request.args.get("q", "").strip()
    if keyword:
        like = f"%{keyword}%"
        q = q.join(PowerOfAttorney.clients, isouter=True).filter(
            db.or_(Client.full_name.ilike(like), Client.national_id.ilike(like),
                   Client.phone.ilike(like), PowerOfAttorney.poa_number.ilike(like),
                   PowerOfAttorney.poa_title.ilike(like), PowerOfAttorney.notary_office.ilike(like),
                   PowerOfAttorney.lawyer_name.ilike(like),)
        ).distinct()
    office_number = request.args.get("office_number", "").strip()
    if office_number:
        try: q = q.filter(PowerOfAttorney.office_number == int(office_number))
        except ValueError: pass
    year = request.args.get("year", "").strip()
    if year:
        try: q = q.filter(PowerOfAttorney.year == int(year))
        except ValueError: pass
    status = request.args.get("status", "").strip()
    if status: q = q.filter(PowerOfAttorney.status == status)
    activation = request.args.get("activation_status", "").strip()
    if activation: q = q.filter(PowerOfAttorney.activation_status == activation)
    letter = request.args.get("letter", "").strip()
    if letter: q = q.filter(PowerOfAttorney.letter == letter)
    lawyer = request.args.get("lawyer", "").strip()
    if lawyer: q = q.filter(PowerOfAttorney.lawyer_name.ilike(f"%{lawyer}%"))
    sort_by  = request.args.get("sort", "office_number")
    sort_dir = request.args.get("dir", "asc")
    allowed_sorts = {"office_number":PowerOfAttorney.office_number,"poa_number":PowerOfAttorney.poa_number,
                     "year":PowerOfAttorney.year,"status":PowerOfAttorney.status,"expiry_date":PowerOfAttorney.expiry_date}
    col = allowed_sorts.get(sort_by, PowerOfAttorney.office_number)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())
    return q


def _save_clients(poa, form):
    Client.query.filter_by(poa_id=poa.id).delete()
    idx = 0
    while True:
        name = form.get(f"client_{idx}_name", "").strip()
        if not name: break
        db.session.add(Client(
            poa_id=poa.id, is_primary=(idx==0), full_name=name,
            national_id=form.get(f"client_{idx}_national_id","").strip() or None,
            phone=form.get(f"client_{idx}_phone","").strip() or None,
            address=form.get(f"client_{idx}_address","").strip() or None,
        ))
        idx += 1
    if idx == 0:
        single = form.get("client_name","").strip()
        if single:
            db.session.add(Client(poa_id=poa.id, is_primary=True, full_name=single,
                national_id=form.get("national_id","").strip() or None,
                phone=form.get("phone","").strip() or None,
                address=form.get("address","").strip() or None,))


@poa_bp.route("/")
@login_required
def index():
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    pagination = _build_search_query().paginate(page=page, per_page=per_page, error_out=False)
    expiring_soon = PowerOfAttorney.query.filter(
        PowerOfAttorney.is_deleted==False, PowerOfAttorney.expiry_date!=None,
        PowerOfAttorney.expiry_date <= date.today()+timedelta(days=30),
        PowerOfAttorney.expiry_date >= date.today(), PowerOfAttorney.status!="منتهي",
    ).count()
    return render_template("poa/list.html", pagination=pagination, args=request.args, expiring_soon=expiring_soon)


@poa_bp.route("/api/search")
@login_required
def api_search():
    query    = _build_search_query()
    total    = query.count()
    page     = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    items    = query.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({"total":total,"page":page,"per_page":per_page,"items":[p.to_dict() for p in items]})


@poa_bp.route("/api/autocomplete")
@login_required
def autocomplete():
    q = request.args.get("q","").strip()
    if len(q) < 2: return jsonify([])
    like = f"%{q}%"
    results = (
        db.session.query(Client.full_name, PowerOfAttorney.office_number, PowerOfAttorney.id, PowerOfAttorney.poa_number, PowerOfAttorney.status)
        .join(PowerOfAttorney, Client.poa_id==PowerOfAttorney.id)
        .filter(PowerOfAttorney.is_deleted==False)
        .filter(db.or_(Client.full_name.ilike(like), Client.national_id.ilike(like),
                       PowerOfAttorney.poa_number.ilike(like), PowerOfAttorney.office_number.cast(db.String).ilike(like),))
        .limit(8).all()
    )
    return jsonify([{"label":f"{r[0]} — مكتب #{r[1]}","value":r[0],"poa_id":r[2],"office":r[1],"poa_number":r[3],"status":r[4]} for r in results])


@poa_bp.route("/expiring")
@login_required
def expiring():
    days = request.args.get("days", 30, type=int)
    poas = PowerOfAttorney.query.filter(
        PowerOfAttorney.is_deleted==False, PowerOfAttorney.expiry_date!=None,
        PowerOfAttorney.expiry_date <= date.today()+timedelta(days=days),
        PowerOfAttorney.expiry_date >= date.today(),
    ).order_by(PowerOfAttorney.expiry_date.asc()).all()
    return render_template("poa/expiring.html", poas=poas, days=days, today=date.today())


@poa_bp.route("/new", methods=["GET","POST"])
@login_required
def create():
    if request.method == "POST":
        errors = []
        office_number = request.form.get("office_number","").strip()
        if not office_number: errors.append("رقم التوكيل بالمكتب مطلوب")
        elif PowerOfAttorney.query.filter_by(office_number=int(office_number), is_deleted=False).first():
            errors.append("رقم التوكيل بالمكتب موجود مسبقاً")
        if not request.form.get("poa_number","").strip(): errors.append("رقم التوكيل مطلوب")
        if not request.form.get("poa_title","").strip():  errors.append("مسمى التوكيل مطلوب")
        if not request.form.get("client_0_name","").strip(): errors.append("اسم الموكل الأول مطلوب")
        if errors:
            for e in errors: flash(e,"danger")
            return render_template("poa/form.html", poa=None, form_data=request.form)
        expiry_raw = request.form.get("expiry_date","").strip()
        year_raw   = request.form.get("year","").strip()
        attachment_filename = attachment_original = None
        file = request.files.get("attachment")
        if file and file.filename and allowed_file(file.filename):
            attachment_filename, attachment_original = secure_save_file(file, current_app.config["UPLOAD_FOLDER"])
        poa = PowerOfAttorney(
            office_number=int(office_number),
            poa_number=request.form.get("poa_number","").strip(),
            poa_title=request.form.get("poa_title","").strip(),
            letter=request.form.get("letter","").strip() or None,
            year=int(year_raw) if year_raw else None,
            notary_office=request.form.get("notary_office","").strip() or None,
            status=request.form.get("status","ساري"),
            expiry_date=datetime.strptime(expiry_raw,"%Y-%m-%d").date() if expiry_raw else None,
            activation_status=request.form.get("activation_status","مفعل"),
            lawyer_name=request.form.get("lawyer_name","").strip() or None,
            notes=request.form.get("notes","").strip() or None,
            attachment_filename=attachment_filename, attachment_original_name=attachment_original,
            created_by=current_user.id, updated_by=current_user.id,
        )
        db.session.add(poa); db.session.flush()
        _save_clients(poa, request.form)
        log_activity("CREATE","poa",poa.id,f"إضافة توكيل رقم المكتب {office_number}")
        db.session.commit()
        flash("تم إضافة التوكيل بنجاح","success")
        return redirect(url_for("poa.view", poa_id=poa.id))
    return render_template("poa/form.html", poa=None, form_data={})


@poa_bp.route("/<int:poa_id>")
@login_required
def view(poa_id):
    poa = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    from app.models import ActivityLog
    history = ActivityLog.query.filter_by(entity_type="poa", entity_id=poa_id)\
                               .order_by(ActivityLog.created_at.desc()).limit(20).all()
    return render_template("poa/detail.html", poa=poa, history=history)


@poa_bp.route("/<int:poa_id>/edit", methods=["GET","POST"])
@login_required
def edit(poa_id):
    poa = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    if request.method == "POST":
        errors = []
        office_number = request.form.get("office_number","").strip()
        if not office_number: errors.append("رقم التوكيل بالمكتب مطلوب")
        else:
            dup = PowerOfAttorney.query.filter(
                PowerOfAttorney.office_number==int(office_number), PowerOfAttorney.id!=poa_id, PowerOfAttorney.is_deleted==False).first()
            if dup: errors.append("رقم التوكيل بالمكتب موجود لتوكيل آخر")
        if not request.form.get("client_0_name","").strip(): errors.append("اسم الموكل الأول مطلوب")
        if errors:
            for e in errors: flash(e,"danger")
            return render_template("poa/form.html", poa=poa, form_data=request.form)
        expiry_raw = request.form.get("expiry_date","").strip()
        year_raw   = request.form.get("year","").strip()
        file = request.files.get("attachment")
        if file and file.filename and allowed_file(file.filename):
            if poa.attachment_filename:
                old = os.path.join(current_app.config["UPLOAD_FOLDER"], poa.attachment_filename)
                if os.path.exists(old): os.remove(old)
            poa.attachment_filename, poa.attachment_original_name = secure_save_file(file, current_app.config["UPLOAD_FOLDER"])
        changes = []
        new_status = request.form.get("status","ساري")
        if poa.status != new_status: changes.append(f"الحالة: {poa.status} ← {new_status}")
        new_activation = request.form.get("activation_status","مفعل")
        if poa.activation_status != new_activation: changes.append(f"التفعيل: {poa.activation_status} ← {new_activation}")
        poa.office_number=int(office_number); poa.poa_number=request.form.get("poa_number","").strip()
        poa.poa_title=request.form.get("poa_title","").strip(); poa.letter=request.form.get("letter","").strip() or None
        poa.year=int(year_raw) if year_raw else None; poa.notary_office=request.form.get("notary_office","").strip() or None
        poa.status=new_status; poa.expiry_date=datetime.strptime(expiry_raw,"%Y-%m-%d").date() if expiry_raw else None
        poa.activation_status=new_activation; poa.lawyer_name=request.form.get("lawyer_name","").strip() or None
        poa.notes=request.form.get("notes","").strip() or None; poa.updated_by=current_user.id; poa.updated_at=datetime.utcnow()
        _save_clients(poa, request.form)
        desc = f"تعديل توكيل #{poa.office_number}"
        if changes: desc += " | " + " , ".join(changes)
        log_activity("UPDATE","poa",poa.id,desc); db.session.commit()
        flash("تم تحديث التوكيل بنجاح","success")
        return redirect(url_for("poa.view", poa_id=poa.id))
    return render_template("poa/form.html", poa=poa, form_data={})


@poa_bp.route("/<int:poa_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(poa_id):
    poa = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    poa.is_deleted=True; poa.updated_by=current_user.id
    log_activity("DELETE","poa",poa_id,f"حذف توكيل #{poa.office_number} - {poa.client_name}")
    db.session.commit(); flash("تم حذف التوكيل","warning")
    return redirect(url_for("poa.index"))


@poa_bp.route("/<int:poa_id>/duplicate", methods=["POST"])
@login_required
def duplicate(poa_id):
    orig = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    last = db.session.query(db.func.max(PowerOfAttorney.office_number)).scalar() or 0
    new_poa = PowerOfAttorney(
        office_number=last+1, poa_number=orig.poa_number, poa_title=orig.poa_title,
        letter=orig.letter, year=orig.year, notary_office=orig.notary_office,
        status="ساري", activation_status=orig.activation_status, lawyer_name=orig.lawyer_name,
        notes=orig.notes, created_by=current_user.id, updated_by=current_user.id,
    )
    db.session.add(new_poa); db.session.flush()
    for c in orig.clients.all():
        db.session.add(Client(poa_id=new_poa.id, is_primary=c.is_primary, full_name=c.full_name,
                              national_id=c.national_id, phone=c.phone, address=c.address,))
    log_activity("CREATE","poa",new_poa.id,f"نسخ توكيل #{orig.office_number} → #{new_poa.office_number}")
    db.session.commit(); flash(f"تم نسخ التوكيل برقم مكتب #{new_poa.office_number}","success")
    return redirect(url_for("poa.edit", poa_id=new_poa.id))


@poa_bp.route("/<int:poa_id>/attachment")
@login_required
def download_attachment(poa_id):
    poa = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    if not poa.attachment_filename: abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], poa.attachment_filename,
                               as_attachment=True, download_name=poa.attachment_original_name or poa.attachment_filename)


@poa_bp.route("/<int:poa_id>/qr")
@login_required
def generate_qr(poa_id):
    try: import qrcode
    except ImportError: abort(500)
    poa = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    qr_text = (f"قانوني PRO — نظام إدارة التوكيلات\n{'─'*30}\n"
               f"رقم المكتب:    #{poa.office_number}\nرقم التوكيل:   {poa.poa_number}\n"
               f"الموكل:        {poa.client_name}\nالمسمى:        {poa.poa_title}\n"
               f"الحرف:         {poa.letter or '—'}\nالسنة:         {poa.year or '—'}\n"
               f"مكتب التوثيق:  {poa.notary_office or '—'}\nالحالة:        {poa.computed_status}\n"
               f"التفعيل:       {poa.activation_status}\n{'─'*30}\n"
               f"تاريخ الانتهاء: {poa.expiry_date.strftime('%Y-%m-%d') if poa.expiry_date else '—'}")
    qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=3)
    qr.add_data(qr_text); qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"qr_توكيل_{poa.office_number}.png")


# ─── PRINT VIEW ───────────────────────────────────────────────────────────────

@poa_bp.route("/<int:poa_id>/print")
@login_required
def print_view(poa_id):
    poa = PowerOfAttorney.query.filter_by(id=poa_id, is_deleted=False).first_or_404()
    return render_template("poa/print.html", poa=poa)
