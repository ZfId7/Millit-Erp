# In app.py (project root: /Millit_ERP/)
import os

from flask import Flask
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from modules import module_blueprints
from database.models import db  # ✅ Adjusted to match /Millit_ERP/database/models.py
from dotenv import load_dotenv
from database.models import User
from werkzeug.security import generate_password_hash
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")

    # ✅ Use correct relative path from project root
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(BASE_DIR, "instance", "database.db")
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

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

