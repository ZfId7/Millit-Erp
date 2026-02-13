# In app.py (project root: /Millit_ERP/)
import os
import click
import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine

from flask import Flask, request
from dotenv import load_dotenv
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash

from modules.shared.op_links import op_queue_url
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from modules import module_blueprints
from database.models import db, User
from modules.shared.nav_registry import DEPT_NAV, infer_department_from_request
from modules.shared.secondary_nav import resolve_secondary_tabs

load_dotenv()

event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        username = username.strip()

        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo("User already exists.")
            return

        u = User(
            username=username,
            password_hash=generate_password_hash(password),
            role="admin",
        )
        db.session.add(u)
        db.session.commit()
        click.echo("Admin user created.")





def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")

    @app.context_processor
    def inject_department_nav():
        dept = infer_department_from_request(request)
        return {
            "current_dept": dept,
            "dept_nav": DEPT_NAV.get(dept, []) if dept else [],
        }

    @app.context_processor
    def inject_secondary_nav():
        bp = request.blueprint
        return {
            "secondary_tabs": resolve_secondary_tabs(request.blueprint, request.endpoint),
    }
    from routes.time import utc_to_mountain, fmt_dt

    app.jinja_env.filters["mt"] = utc_to_mountain
    app.jinja_env.filters["dt"] = fmt_dt
    
    app.jinja_env.globals["op_queue_url"] = op_queue_url

    # ✅ Database path (env override for worktrees)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    db_path = os.getenv("MERP_DB_PATH") or os.path.join(
        BASE_DIR, "instance", "database.db"
    )
    db_path = os.path.abspath(db_path)

    # Ensure DB directory exists (safe for both cases)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print("✅ DB:", db_path)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Claim system v0
    app.config.setdefault("MERP_CLAIM_STALE_SECONDS", 2 * 60 * 60)  # 2 hours
    
    db.init_app(app)
    register_cli(app)
    Migrate(app, db)

    if os.getenv("MERP_CREATE_DB") == "1":
        with app.app_context():
            db.create_all()



    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    
    
    for name, blueprint, prefix in module_blueprints:
        print(f"🧠 Registering {name} → prefix: {prefix}, blueprint ID: {id(blueprint)}")
        app.register_blueprint(blueprint, url_prefix=prefix)
    
    
    return app



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False, threaded=True)

