from flask import Flask
from pathlib import Path
import os

APP_ROOT = Path(__file__).resolve().parent
UPLOAD_ROOT = APP_ROOT / "uploads"
TRASH_DIR = UPLOAD_ROOT / ".trash"

os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs(TRASH_DIR, exist_ok=True)

def create_app():
    app = Flask(
        __name__,
        template_folder="app/templates",
        static_folder="app/static"
    )

    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["UPLOAD_ROOT"] = UPLOAD_ROOT

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app

app = create_app()
