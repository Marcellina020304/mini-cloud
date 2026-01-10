from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, send_file, send_from_directory, current_app, flash, jsonify
)
from pathlib import Path
from werkzeug.utils import secure_filename
import os, shutil, mimetypes, time
from datetime import datetime
import json
import secrets
from flask import send_file
from urllib.parse import quote
from flask import Blueprint

main_bp = Blueprint("main", __name__, template_folder="../templates", static_folder="../static")

@main_bp.app_template_filter('datetimeformat')
def datetimeformat(value):
    if not value:
        return ''
    return datetime.fromtimestamp(value).strftime('%d-%m-%Y %H:%M')

APP_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = APP_ROOT / "uploads"
os.makedirs(UPLOAD_ROOT, exist_ok=True)
TRASH_DIR = UPLOAD_ROOT / ".trash"
os.makedirs(TRASH_DIR, exist_ok=True)
FAVORITE_DIR = UPLOAD_ROOT / "favorit"
os.makedirs(FAVORITE_DIR, exist_ok=True)
FAV_FILE = FAVORITE_DIR / "favorites.json"
SHARE_DIR = UPLOAD_ROOT / "share"
os.makedirs(SHARE_DIR, exist_ok=True)
SHARE_FILE = SHARE_DIR / "shares.json"


def ensure_logged_in():
    return session.get("user") is not None

def safe_path_join(root: Path, *parts):
    try:
        candidate = (root / Path(*parts)).resolve()
        if root.resolve() in candidate.parents or candidate == root.resolve():
            return candidate
    except Exception:
        pass
    return None

def list_folder(folder_path: Path):
    folders, files = [], []

    for child in sorted(folder_path.iterdir(), key=lambda p: p.name.lower()):
        if child.name.startswith('.'):
            continue

        # FOLDER
        if child.is_dir():
            folders.append({
                'name': child.name,
                'path': str(child.relative_to(UPLOAD_ROOT)).replace("\\", "/")
            })

        # FILE
        elif child.is_file():
            mime = mimetypes.guess_type(str(child))[0] or ''
            if mime.startswith("image/"):
                icon_class = "fa-file-image"
            elif mime == "application/pdf":
                icon_class = "fa-file-pdf"
            elif mime in ["application/msword",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                icon_class = "fa-file-word"
            elif mime in ["application/vnd.ms-excel",
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                icon_class = "fa-file-excel"
            elif mime in ["application/vnd.ms-powerpoint",
                          "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
                icon_class = "fa-file-powerpoint"
            else:
                icon_class = "fa-file"

            files.append({
                'name': child.name,
                'path': str(child.relative_to(UPLOAD_ROOT)).replace("\\", "/"),
                'size': child.stat().st_size,
                'mtime': child.stat().st_mtime,
                'mime': mime,
                'icon_class': icon_class
            })

    return folders, files

def load_favorites():
    if not FAV_FILE.exists():
        return []

    try:
        data = json.loads(FAV_FILE.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_favorites(favs):
    FAV_FILE.parent.mkdir(parents=True, exist_ok=True)
    FAV_FILE.write_text(json.dumps(favs, indent=2))

def load_shares():
    if SHARE_FILE.exists():
        return json.loads(SHARE_FILE.read_text())
    return []

def save_shares(data):
    SHARE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SHARE_FILE.write_text(json.dumps(data, indent=2))

def get_storage_info():
    total_bytes = 5 * 1024 * 1024 * 1024  # 5 GB
    used_bytes = sum(f.stat().st_size for f in UPLOAD_ROOT.rglob('*') if f.is_file())
    return used_bytes, total_bytes
def format_size(bytes):
    for unit in ['B','KB','MB','GB','TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"

@main_bp.app_context_processor
def inject_storage_status():
    used, total = get_storage_info()
    return dict(
        storage_used=used,
        storage_total=total,
        storage_used_fmt=format_size(used)
    )

@main_bp.route("/", defaults={'subpath': ''})
@main_bp.route("/folder/<path:subpath>")
def index(subpath):
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))

    safe = safe_path_join(UPLOAD_ROOT, subpath)
    if not safe:
        safe = UPLOAD_ROOT

    if not safe.exists():
        safe = UPLOAD_ROOT

    rel = safe.relative_to(UPLOAD_ROOT)
    path_display = str(rel) if str(rel) != "." else "mini-cloud"

    folders, files = list_folder(safe)

    favorites = load_favorites()

    return render_template(
        "index.html",
        folders=folders,
        files=files,
        favorites=favorites,   # ⬅️ WAJIB
        current_path=path_display,
        current_subpath=str(rel).replace("\\", "/")
    )


@main_bp.route("/uploads/<path:filename>")
def serve_uploads(filename):
    safe = safe_path_join(UPLOAD_ROOT, filename)
    if not safe or not safe.exists():
        return "Not found", 404
    return send_from_directory(str(safe.parent), safe.name, as_attachment=False)

@main_bp.route("/download/<path:filename>")
def download_file(filename):
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))
    safe = safe_path_join(UPLOAD_ROOT, filename)
    if not safe or not safe.exists():
        return "Not found", 404
    return send_from_directory(str(safe.parent), safe.name, as_attachment=True)

@main_bp.route("/upload_file_or_folder", methods=["POST"])
def upload_file_or_folder():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))

    dest_path = request.form.get("dest_path", "")
    safe_dest = safe_path_join(UPLOAD_ROOT, dest_path) or UPLOAD_ROOT
    os.makedirs(safe_dest, exist_ok=True)

    total_uploaded = 0

    # --- Upload file biasa ---
    uploaded_files = request.files.getlist("files")
    for f in uploaded_files:
        if not f or not getattr(f, "filename", None):
            continue

        filename = secure_filename(f.filename)
        if not filename:
            continue

        full_path = safe_dest / filename
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            f.save(str(full_path))
            total_uploaded += 1
        except Exception as e:
            current_app.logger.exception("Gagal menyimpan file: %s", e)

    # --- Upload folder (webkitdirectory) ---
    folder_files = request.files.getlist("folder_files")
    for f in folder_files:
        if not f or not getattr(f, "filename", None):
            continue

        raw_filename = f.filename.strip()
        if not raw_filename:
            continue

        # secure semua bagian path
        parts = [secure_filename(p) for p in raw_filename.split("/") if p != ""]
        last = parts.pop()  # nama file terakhir
        safe_rel_path = Path(*parts) / last
        full_path = safe_dest / safe_rel_path

        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            f.save(str(full_path))
            total_uploaded += 1
        except Exception as e:
            current_app.logger.exception("Gagal menyimpan file dari folder upload: %s", e)

    flash(f"{total_uploaded} file berhasil di-upload.", "success")
    return redirect(request.referrer or url_for("main.index"))

@main_bp.route("/create_folder", methods=["POST"])
def create_folder():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))
    name = request.form.get("folder_name", "").strip()
    dest = request.form.get("dest_path", "").strip()
    if not name:
        flash("Nama folder kosong", "danger")
        return redirect(request.referrer or url_for("main.index"))
    safe_dest = safe_path_join(UPLOAD_ROOT, dest) or UPLOAD_ROOT
    os.makedirs(safe_dest / secure_filename(name), exist_ok=True)
    return redirect(request.referrer or url_for("main.index"))

@main_bp.route("/delete-file", methods=["POST"])
def delete_file_api():
    if not ensure_logged_in():
        return jsonify({"success": False, "error": "unauthorized"}), 401

    rel = request.form.get("path", "").strip()
    full = safe_path_join(UPLOAD_ROOT, rel)
    os.makedirs(TRASH_DIR, exist_ok=True)

    if full and full.exists():
        dest = TRASH_DIR / (str(int(time.time())) + "_" + full.name)
        shutil.move(str(full), str(dest))
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "file not found"}), 404

@main_bp.route("/recent")
def recent():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))
    
    # ambil semua file dari UPLOAD_ROOT termasuk subfolder
    files_list = []
    for path in UPLOAD_ROOT.rglob("*"):
        if path.is_file() and not path.name.startswith('.'):
            files_list.append({
                "name": path.name,
                "path": str(path.relative_to(UPLOAD_ROOT)).replace("\\","/"),
                "mtime": path.stat().st_mtime,
                "mime": mimetypes.guess_type(str(path))[0] or '',
                "favorite": False,  # default, bisa disambung ke db nanti
            })
    # urutkan berdasarkan waktu terakhir diubah (mtime), terbaru dulu
    files_sorted = sorted(files_list, key=lambda x: x['mtime'], reverse=True)

    return render_template("recent.html", files=files_sorted)

@main_bp.route("/favorite")
def toggle_favorite():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))

    path = request.args.get("path")
    if not path:
        return redirect(request.referrer or url_for("main.index"))

    favs = load_favorites()

    if path in favs:
        favs.remove(path)
    else:
        favs.append(path)

    save_favorites(favs)
    return redirect(request.referrer or url_for("main.index"))

@main_bp.route("/favorites")
def favorites():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))
    
    fav_files_list = load_favorites()  # ambil dari JSON
    files = []
    for f in fav_files_list:
        safe = safe_path_join(UPLOAD_ROOT, f)
        if safe and safe.exists():
            mime = mimetypes.guess_type(str(safe))[0] or ''
            if mime.startswith("image/"):
                icon_class = "fa-file-image"
            elif mime == "application/pdf":
                icon_class = "fa-file-pdf"
            else:
                icon_class = "fa-file"
            files.append({
                "name": safe.name,
                "path": str(safe.relative_to(UPLOAD_ROOT)).replace("\\","/"),
                "mime": mime,
                "icon_class": icon_class
            })
    return render_template("favorites.html", files=files, current_path="Favorit")

@main_bp.route("/share", methods=["POST"])
def create_share():
    if not ensure_logged_in():
        return jsonify({"success": False, "error": "unauthorized"}), 401

    path = request.form.get("path")
    if not path:
        return jsonify({"success": False, "error": "path kosong"}), 400

    safe = safe_path_join(UPLOAD_ROOT, path)
    if not safe or not safe.exists():
        return jsonify({"success": False, "error": "file tidak ditemukan"}), 404

    token = secrets.token_urlsafe(8)
    expire_at = int(time.time()) + (24 * 3600)  # 24 jam

    shares = load_shares()
    shares.append({
        "token": token,
        "path": path,
        "expire_at": expire_at
    })
    save_shares(shares)

    share_url = url_for("main.open_share", token=token, _external=True)

    return jsonify({
        "success": True,
        "url": share_url,
        "expire_at": expire_at
    })

@main_bp.route("/s/<token>")
def open_share(token):
    shares = load_shares()
    now = int(time.time())

    for s in shares:
        if s["token"] == token:
            if now > s["expire_at"]:
                return "Link sudah kadaluarsa", 410

            safe = safe_path_join(UPLOAD_ROOT, s["path"])
            if not safe or not safe.exists():
                return "File tidak ditemukan", 404

            return send_from_directory(
                str(safe.parent),
                safe.name,
                as_attachment=False
            )

    return "Link tidak valid", 404

@main_bp.route("/trash")
def trash():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))
    folders, files = [], []
    os.makedirs(TRASH_DIR, exist_ok=True)
    for child in sorted(TRASH_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            if child.is_dir():
                folders.append({"name": child.name, "mtime": child.stat().st_mtime, "mime": ""})
            elif child.is_file():
                mime = mimetypes.guess_type(str(child))[0] or ''
                files.append({
                    "name": child.name,
                    "mtime": child.stat().st_mtime,
                    "path": str(child.relative_to(UPLOAD_ROOT)).replace("\\","/"),
                    "mime": mime
                })
        except Exception:
            continue
    return render_template("trash.html", folders=folders, files=files, current_path="Sampah")

@main_bp.route("/restore", methods=["POST"])
def restore():
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))
    name = request.form.get("name")
    if not name:
        flash("Nama tidak ditemukan", "danger")
        return redirect(url_for("main.trash"))
    src = TRASH_DIR / name
    if not src.exists():
        flash("File tidak ditemukan di trash", "danger")
        return redirect(url_for("main.trash"))
    dest = UPLOAD_ROOT / name
    if dest.exists():
        dest = UPLOAD_ROOT / (name + "_" + str(int(time.time())))
    shutil.move(str(src), str(dest))
    flash("File berhasil direstore", "success")
    return redirect(url_for("main.trash"))

# preview API
@main_bp.route("/preview-info")
def preview_info():
    file_path = request.args.get("path", "")
    if not ensure_logged_in():
        return redirect(url_for("auth.login"))

    safe = safe_path_join(UPLOAD_ROOT, file_path)
    if not safe or not safe.exists():
        return jsonify({"error": "not_found"}), 404

    mime = mimetypes.guess_type(str(safe))[0] or "application/octet-stream"
    rel_path = str(safe.relative_to(UPLOAD_ROOT)).replace("\\", "/")

    return jsonify({
        "mime": mime,
        "path": rel_path
    })

@main_bp.route("/files/<path:filename>")
def serve_file(filename):
    safe = safe_path_join(UPLOAD_ROOT, filename)
    if not safe or not safe.exists():
        return "Not found", 404

    return send_from_directory(
        safe.parent,
        safe.name,
        as_attachment=False
    )

@main_bp.route("/public/<path:filename>")
def serve_public_file(filename):
    file_path = UPLOAD_ROOT / filename
    if not file_path.exists():
        return "File not found", 404

    ext = file_path.suffix.lower()
    if ext == ".docx":
        mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext == ".pptx":
        mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif ext == ".xlsx":
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif ext == ".doc":
        mimetype = "application/msword"
    elif ext == ".ppt":
        mimetype = "application/vnd.ms-powerpoint"
    elif ext == ".xls":
        mimetype = "application/vnd.ms-excel"
    elif ext == ".pdf":
        mimetype = "application/pdf"
    else:
        mimetype, _ = mimetypes.guess_type(str(file_path))
        mimetype = mimetype or "application/octet-stream"

    # as_attachment=False supaya Google Docs Viewer bisa fetch
    return send_file(file_path, as_attachment=False, mimetype=mimetype)

@main_bp.route("/preview/<path:filename>")
def preview_file(filename):
    safe = safe_path_join(UPLOAD_ROOT, filename)
    if not safe or not safe.exists():
        return "File not found", 404

    # gunakan path relatif lengkap agar serve_public_file bisa akses
    rel_path = str(safe.relative_to(UPLOAD_ROOT)).replace("\\","/")
    file_url = url_for("main.serve_public_file", filename=rel_path, _external=True)

    return render_template("preview_file.html", file_url=file_url, filename=safe.name)
