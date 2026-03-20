from datetime import datetime, date
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    full_name       = db.Column(db.String(128), nullable=False)
    email           = db.Column(db.String(128), unique=True, nullable=False)
    password_hash   = db.Column(db.String(256), nullable=False)
    role            = db.Column(db.String(20),  nullable=False, default="employee")
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    avatar_filename = db.Column(db.String(256), nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_login      = db.Column(db.DateTime, nullable=True)

    poas_created    = db.relationship("PowerOfAttorney", backref="created_by_user", lazy="dynamic", foreign_keys="PowerOfAttorney.created_by")
    poas_updated    = db.relationship("PowerOfAttorney", backref="updated_by_user", lazy="dynamic", foreign_keys="PowerOfAttorney.updated_by")
    activity_logs   = db.relationship("ActivityLog",     backref="user", lazy="dynamic")
    notifications   = db.relationship("Notification",    backref="user", lazy="dynamic", foreign_keys="Notification.user_id")
    sessions        = db.relationship("UserSession",     backref="user", lazy="dynamic")

    @property
    def is_admin(self): return self.role == "admin"

    @property
    def avatar_url(self):
        if self.avatar_filename:
            return f"/users/avatar/{self.avatar_filename}"
        return None

    @property
    def unread_notifications_count(self):
        return self.notifications.filter_by(is_read=False).count()


class Notification(db.Model):
    __tablename__ = "notifications"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title       = db.Column(db.String(256), nullable=False)
    body        = db.Column(db.Text,        nullable=True)
    type        = db.Column(db.String(30),  nullable=False, default="info")  # info | warning | danger | success
    link        = db.Column(db.String(512), nullable=True)
    is_read     = db.Column(db.Boolean, default=False, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "body": self.body,
            "type": self.type, "link": self.link,
            "is_read": self.is_read,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }


class UserSession(db.Model):
    __tablename__ = "user_sessions"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    session_token= db.Column(db.String(128), unique=True, nullable=False, index=True)
    ip_address   = db.Column(db.String(45),  nullable=True)
    user_agent   = db.Column(db.String(512), nullable=True)
    device_name  = db.Column(db.String(128), nullable=True)   # e.g. "Chrome / Windows"
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    last_active  = db.Column(db.DateTime, default=datetime.utcnow)
    is_active    = db.Column(db.Boolean, default=True, nullable=False)


class Client(db.Model):
    __tablename__ = "clients"
    id          = db.Column(db.Integer, primary_key=True)
    poa_id      = db.Column(db.Integer, db.ForeignKey("powers_of_attorney.id"), nullable=False, index=True)
    is_primary  = db.Column(db.Boolean, default=True, nullable=False)
    full_name   = db.Column(db.String(256), nullable=False, index=True)
    national_id = db.Column(db.String(20),  nullable=True)
    phone       = db.Column(db.String(30),  nullable=True)
    address     = db.Column(db.String(512), nullable=True)

    def to_dict(self):
        return {"id":self.id,"full_name":self.full_name,"national_id":self.national_id,
                "phone":self.phone,"address":self.address,"is_primary":self.is_primary}


class PowerOfAttorney(db.Model):
    __tablename__ = "powers_of_attorney"
    id                       = db.Column(db.Integer, primary_key=True)
    office_number            = db.Column(db.Integer,     nullable=False, unique=True, index=True)
    poa_number               = db.Column(db.String(50),  nullable=False, index=True)
    poa_title                = db.Column(db.String(256), nullable=False)
    letter                   = db.Column(db.String(10),  nullable=True)
    year                     = db.Column(db.Integer,     nullable=True, index=True)
    notary_office            = db.Column(db.String(128), nullable=True)
    status                   = db.Column(db.String(30),  nullable=False, default="ساري", index=True)
    expiry_date              = db.Column(db.Date,        nullable=True)
    activation_status        = db.Column(db.String(20),  nullable=False, default="مفعل")
    lawyer_name              = db.Column(db.String(256), nullable=True)
    attachment_filename      = db.Column(db.String(256), nullable=True)
    attachment_original_name = db.Column(db.String(256), nullable=True)
    notes                    = db.Column(db.Text,        nullable=True)
    created_by               = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by               = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at               = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at               = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted               = db.Column(db.Boolean, default=False, nullable=False)
    clients = db.relationship("Client", backref="poa", lazy="dynamic", cascade="all, delete-orphan", foreign_keys="Client.poa_id")

    @property
    def primary_client(self):
        return self.clients.filter_by(is_primary=True).first() or self.clients.first()
    @property
    def client_name(self):
        c = self.primary_client; return c.full_name if c else "—"
    @property
    def display_name(self):
        names = [c.full_name for c in self.clients.order_by(Client.is_primary.desc()).all()]
        return " / ".join(names) if names else "—"
    @property
    def clients_sorted(self):
        return self.clients.order_by(Client.is_primary.desc()).all()
    @property
    def is_active(self): return self.activation_status == "مفعل"
    @property
    def is_expired(self):
        if self.expiry_date: return self.expiry_date < date.today()
        return self.status == "منتهي"
    @property
    def computed_status(self):
        if self.expiry_date and self.expiry_date < date.today(): return "منتهي"
        return self.status

    def to_dict(self):
        return {
            "id":self.id,"office_number":self.office_number,
            "client_name":self.client_name,"display_name":self.display_name,
            "poa_number":self.poa_number,"poa_title":self.poa_title,
            "letter":self.letter,"year":self.year,"notary_office":self.notary_office,
            "status":self.computed_status,
            "expiry_date":self.expiry_date.isoformat() if self.expiry_date else None,
            "activation_status":self.activation_status,"lawyer_name":self.lawyer_name,
            "notes":self.notes,"has_attachment":bool(self.attachment_filename),
            "clients":[c.to_dict() for c in self.clients.all()],
            "created_at":self.created_at.isoformat() if self.created_at else None,
            "updated_at":self.updated_at.isoformat() if self.updated_at else None,
        }


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id          = db.Column(db.Integer,     primary_key=True)
    user_id     = db.Column(db.Integer,     db.ForeignKey("users.id"), nullable=True)
    action      = db.Column(db.String(50),  nullable=False)
    entity_type = db.Column(db.String(50),  nullable=True)
    entity_id   = db.Column(db.Integer,     nullable=True)
    description = db.Column(db.String(512), nullable=True)
    ip_address  = db.Column(db.String(45),  nullable=True)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow, index=True)
