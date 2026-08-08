from flask import Flask, session, g, redirect, url_for, request
from datetime import datetime
from configs.connection import get_db
from configs.config import Config

# Routes auth
from routes.auth_route import auth
from routes.challenge_route import challenge_bp

# Routes admin
from routes.admin.dashboard_route import admin_dashboard_bp
from routes.admin.users_route import users_bp
from routes.admin.roles_route import role_bp
from routes.admin.mahasiswa_route import mahasiswa_bp
from routes.admin.dosen_route import dosen_bp
from routes.admin.quizz_route import admin_soal_bp

# Routes mahasiswa
from routes.mahasiswa.dashboard_route import dashboard_bp
from routes.mahasiswa.quiz_route import quiz_bp

# Services
from services.koneksi_service import test_koneksi


app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if not value:
        return ""

    if isinstance(value, str):
        value = datetime.strptime(value, "%Y-%m-%d")

    return value.strftime("%m/%d/%Y")

@app.route("/", methods = ['GET'])
def index():
    
    if "user" not in session:
        
        return redirect(url_for("auth.login"))
    
    role = session["user"].get("role", "").lower()
    
    if role == "admin":
        return redirect(url_for("admin_dashboard.halaman_admin_dashboard"))
    
    elif role == "mahasiswa":
        return redirect(url_for("dashboard.halaman_dashboard"))
    
    else:
        session.clear()
        return redirect(url_for("auth.login"))


@app.route("/koneksi", methods = ['GET'])
def koneksi():
    db = get_db()
    
    if test_koneksi(db):
        return "Database connect."
    else:
        return "Database not conect."

# Routes auth
app.register_blueprint(auth)
app.register_blueprint(challenge_bp)

# Routes admin
app.register_blueprint(admin_dashboard_bp)
app.register_blueprint(users_bp)
app.register_blueprint(role_bp)
app.register_blueprint(mahasiswa_bp)
app.register_blueprint(dosen_bp)
app.register_blueprint(admin_soal_bp)

# Routes mahasiswa
app.register_blueprint(dashboard_bp)
app.register_blueprint(quiz_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug = True, port = 8000)