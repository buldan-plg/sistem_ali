from flask import Blueprint, render_template, redirect, jsonify, session
from models.point_model import get_leaderboard, get_mahasiswa_points, get_solved_soal_ids
from models.quiz_model import get_total_soal

dashboard_bp = Blueprint("dashboard", __name__)

def require_login():
    if not session["user"].get("profile_id"):
        return None, ({"error": "Login terlebih dahulu."}, 401)
    return session["user"].get("profile_id"), None

# ── Halaman dashboard ─────────────────────────────────
@dashboard_bp.route("/mahasiswa/dashboard")
def halaman_dashboard():
    if not session["user"].get("profile_id"):
        
        return redirect("/login")
    return render_template("mahasiswa/home/dashboard.html", title="Dashboard")

# ── API: data lengkap dashboard (1 call) ─────────────
@dashboard_bp.route("/api/dashboard")
def api_dashboard():
    id_mhs, err = require_login()
    if err: return jsonify(err[0]), err[1]

    # Data milik mahasiswa yg login
    my_points  = get_mahasiswa_points(id_mhs) or {
        "total_point": 0, "total_soal_solved": 0,
        "total_creator_point": 0, "total_challenge_created": 0,
        "nama_mahasiswa": "", "nim": ""
    }
    solved_ids   = get_solved_soal_ids(id_mhs)
    total_soal   = get_total_soal()

    # Leaderboard top 10
    leaderboard  = get_leaderboard(10)

    # Cari posisi user di leaderboard
    my_rank = None
    for i, row in enumerate(leaderboard):
        if row.get("nim") == my_points.get("nim"):
            my_rank = i + 1
            break

    # Kalau tidak masuk top 10, hitung ranknya sendiri
    if my_rank is None:
        from configs.connection import get_db
        db  = get_db()
        cur = db.cursor()
        cur.execute("""
            SELECT COUNT(*) + 1 AS my_rank
            FROM tb_points
            WHERE total_point > (
                SELECT COALESCE(total_point, 0) FROM tb_points
                WHERE id_mahasiswa = %s
            )
        """, (id_mhs,))
        row = cur.fetchone()
        db.close()
        my_rank = row["my_rank"] if row else "—"

    return jsonify({
        "my": {
            "nama":               my_points.get("nama_mahasiswa", ""),
            "nim":                my_points.get("nim", ""),
            "total_point":        my_points.get("total_point", 0),
            "total_soal_solved":  my_points.get("total_soal_solved", 0),
            "total_soal":         total_soal,
            "total_creator_point":my_points.get("total_creator_point", 0),
            "total_challenge_created": my_points.get("total_challenge_created", 0),
            "rank":               my_rank,
            "solved_ids":         solved_ids,
        },
        "leaderboard": leaderboard,
    })