import sys
from pathlib import Path
import os
import sqlite3
from datetime import datetime, timedelta
import secrets
import mimetypes
import shutil
import time
from flask import Flask, redirect, url_for, session

# --- PAKSA ROOT ADA DI PATH ---
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# buat folder uploads / trash
UPLOAD_ROOT = APP_ROOT / "uploads"
TRASH_DIR = UPLOAD_ROOT / ".trash"
MAX_STORAGE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
os.makedirs(UPLOAD_ROOT, exist_ok=True)
os.makedirs(TRASH_DIR, exist_ok=True)


def create_app():
    app = Flask(
        __name__,
        template_folder=str(APP_ROOT / "app/templates"),
        static_folder=str(APP_ROOT / "app/static")
    )

    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-123")
    app.config['USERS'] = {"admin": "admin1234"}
    app.config['UPLOAD_ROOT'] = UPLOAD_ROOT
    app.config['TRASH_DIR'] = TRASH_DIR
    app.config['MAX_STORAGE_BYTES'] = MAX_STORAGE_BYTES

    # --- IMPORT BLUEPRINTS SETELAH PATH FIX ---
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # favicon helper
    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
