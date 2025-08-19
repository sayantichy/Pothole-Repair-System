﻿from flask import Flask
from config import Config
from extensions import db, migrate, login_manager
from models import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from blueprints.public import bp as public_bp
    from blueprints.staff import bp as staff_bp
    from blueprints.api import bp as api_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.user import bp as user_bp
    from blueprints.lead import bp as lead_bp  # ← IMPORTANT

    app.register_blueprint(public_bp)
    app.register_blueprint(staff_bp, url_prefix="/staff")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(lead_bp, url_prefix="/lead")  # ← IMPORTANT

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
