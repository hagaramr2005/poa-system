from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_object="config.Config"):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "avatars"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "..", "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "يرجى تسجيل الدخول للوصول إلى النظام"
    login_manager.login_message_category = "warning"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth          import auth_bp
    from app.routes.dashboard     import dashboard_bp
    from app.routes.poa           import poa_bp
    from app.routes.users         import users_bp
    from app.routes.reports       import reports_bp
    from app.routes.activity      import activity_bp
    from app.routes.notifications import notifications_bp
    from app.routes.sessions      import sessions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(poa_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(sessions_bp)

    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


def _seed_admin():
    from app.models import User
    from werkzeug.security import generate_password_hash
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin", full_name="المدير العام",
            email="admin@qanoony.pro",
            password_hash=generate_password_hash("Admin@2024"),
            role="admin", is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
