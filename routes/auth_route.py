from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, session
from werkzeug.security import check_password_hash
from configs.connection import get_db

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=['GET', 'POST'])
def login():
    form_errors = {}

    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        try:
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        u.id_user,
                        u.username,
                        u.password,
                        r.nama_role  AS role,
                        d.id_dosen,
                        d.nama_dosen,
                        m.id_mahasiswa,
                        m.nama_mahasiswa
                    FROM tb_users u
                    LEFT JOIN tb_roles     r ON u.id_role = r.id_role
                    LEFT JOIN tb_dosen     d ON u.id_user = d.id_user
                    LEFT JOIN tb_mahasiswa m ON u.id_user = m.id_user
                    WHERE u.username = %s
                """, (username,))
                user = cursor.fetchone()
        finally:
            db.close()

        if not user:
            form_errors["username"] = "Username tidak terdaftar."

        elif not check_password_hash(user["password"], password):
            form_errors["password"] = "Password salah."

        else:
            role = (user["role"] or "").lower()
            role_map = {
                "admin":     (user["id_dosen"],     user["nama_dosen"]),
                "dosen":     (user["id_dosen"],     user["nama_dosen"]),
                "mahasiswa": (user["id_mahasiswa"], user["nama_mahasiswa"]),
            }
            profile_id, nama = role_map.get(role, (None, None))

            session["user"] = {
                "id":         user["id_user"],
                "profile_id": profile_id,
                "username":   user["username"],
                "role":       user["role"],
                "nama":       nama,
            }

            flash("Berhasil login.", "success")
            return redirect(url_for("index"))

    # Render langsung (GET atau POST gagal), kirim form_errors ke template
    return render_template("auth/login.html", title="Login", error=form_errors)

@auth.route("/logout", methods = ['GET'])
def logout():
    session.clear()
    flash("Berhasil logout.", "succes")
    return redirect(url_for("index"))