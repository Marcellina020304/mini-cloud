from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app

auth_bp = Blueprint("auth", __name__, url_prefix="")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # jika sudah login -> index
    if session.get("user"):
        return redirect(url_for("main.index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = current_app.config.get("USERS", {})
        if username and users.get(username) == password:
            session["user"] = username
            return redirect(url_for("main.index"))
        error = "Username atau password salah"
        flash(error, "danger")
    return render_template("login.html", error=error)

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("auth.login"))
