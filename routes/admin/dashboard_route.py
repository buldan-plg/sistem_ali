from flask import Blueprint, render_template, jsonify, session
from configs.connection import get_db

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix = "/admin")

def require_admin():
    if session["user"].get("role") not in ("admin", "dosen"):
        return {"error": "Akses ditolak."}, 403
    return None, None

# ── Halaman ───────────────────────────────────────────
@admin_dashboard_bp.route("/dashboard")
def halaman_admin_dashboard():
    err, code = require_admin()[0], require_admin()[1]
    if err:
        from flask import redirect
        return redirect("/login")
    return render_template("admin/dashboard.html", title="Dashboard Admin")

# ── API: semua data dashboard dalam 1 call ────────────
@admin_dashboard_bp.route("/api/dashboard")
def api_admin_dashboard():
    err = require_admin()
    if err[0]: return jsonify(err[0]), err[1]

    db  = get_db()
    cur = db.cursor()

    # ── Stat utama ────────────────────────────────────
    cur.execute("SELECT COUNT(*) AS total FROM tb_soal WHERE is_active = 1")
    total_soal = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM tb_mahasiswa")
    total_mahasiswa = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM tb_quiz_results WHERE is_correct = 1")
    total_solved = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM tb_challenges WHERE status = 'pending'")
    total_pending_challenge = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM tb_challenges WHERE status = 'approved' AND expires_at > NOW()")
    total_active_challenge = cur.fetchone()["total"]

    cur.execute("SELECT COALESCE(SUM(total_point), 0) AS total FROM tb_points")
    total_point_distributed = cur.fetchone()["total"]

    # ── Soal paling sering dikerjakan (top 5) ─────────
    cur.execute("""
        SELECT s.id_soal, s.judul, s.level, s.kategori,
               COUNT(r.id_result) AS total_attempt,
               SUM(r.is_correct)  AS total_solved,
               ROUND(SUM(r.is_correct) / COUNT(r.id_result) * 100, 1) AS success_rate
        FROM tb_soal s
        LEFT JOIN tb_quiz_results r ON r.id_soal = s.id_soal
        GROUP BY s.id_soal
        ORDER BY total_attempt DESC
        LIMIT 5
    """)
    top_soal = cur.fetchall()

    # ── Soal paling susah (success rate terendah, min 5 attempt) ──
    cur.execute("""
        SELECT s.id_soal, s.judul, s.level,
               COUNT(r.id_result) AS total_attempt,
               ROUND(SUM(r.is_correct) / COUNT(r.id_result) * 100, 1) AS success_rate
        FROM tb_soal s
        JOIN tb_quiz_results r ON r.id_soal = s.id_soal
        GROUP BY s.id_soal
        HAVING total_attempt >= 3
        ORDER BY success_rate ASC
        LIMIT 5
    """)
    hardest_soal = cur.fetchall()

    # ── Leaderboard top 10 ────────────────────────────
    cur.execute("""
        SELECT
            ROW_NUMBER() OVER (ORDER BY p.total_point DESC) AS `rank`,
            m.nama_mahasiswa, m.nim, m.angkatan,
            p.total_point, p.total_soal_solved,
            p.total_creator_point, p.total_challenge_created
        FROM tb_points p
        JOIN tb_mahasiswa m ON m.id_mahasiswa = p.id_mahasiswa
        ORDER BY p.total_point DESC
        LIMIT 10
    """)
    leaderboard = cur.fetchall()

    # ── Mahasiswa belum mulai ─────────────────────────
    cur.execute("""
        SELECT COUNT(*) AS total FROM tb_mahasiswa m
        WHERE NOT EXISTS (
            SELECT 1 FROM tb_quiz_results r WHERE r.id_mahasiswa = m.id_mahasiswa
        )
    """)
    total_inactive = cur.fetchone()["total"]

    # ── Distribusi level soal solved ──────────────────
    cur.execute("""
        SELECT s.level,
               COUNT(r.id_result)      AS total_attempt,
               SUM(r.is_correct)       AS total_solved
        FROM tb_quiz_results r
        JOIN tb_soal s ON s.id_soal = r.id_soal
        GROUP BY s.level
    """)
    level_dist = cur.fetchall()

    # ── Aktivitas terbaru (10 terakhir) ───────────────
    cur.execute("""
        SELECT m.nama_mahasiswa, m.nim,
               s.judul AS soal_judul, s.level,
               r.is_correct, r.bahasa, r.attempt_count,
               r.updated_at
        FROM tb_quiz_results r
        JOIN tb_mahasiswa m ON m.id_mahasiswa = r.id_mahasiswa
        JOIN tb_soal s ON s.id_soal = r.id_soal
        ORDER BY r.updated_at DESC
        LIMIT 10
    """)
    recent_activity = cur.fetchall()

    # ── Challenge pending (untuk review) ─────────────
    cur.execute("""
        SELECT c.id_challenge, c.judul, c.level, c.created_at,
               m.nama_mahasiswa, m.nim
        FROM tb_challenges c
        JOIN tb_mahasiswa m ON m.id_mahasiswa = c.id_mahasiswa
        WHERE c.status = 'pending'
        ORDER BY c.created_at ASC
        LIMIT 5
    """)
    pending_challenges = cur.fetchall()

    # ── Statistik per kategori ────────────────────────
    cur.execute("""
        SELECT s.kategori,
               COUNT(DISTINCT s.id_soal)   AS total_soal,
               COUNT(r.id_result)           AS total_attempt,
               COALESCE(SUM(r.is_correct),0) AS total_solved
        FROM tb_soal s
        LEFT JOIN tb_quiz_results r ON r.id_soal = s.id_soal
        WHERE s.is_active = 1
        GROUP BY s.kategori
        ORDER BY total_attempt DESC
    """)
    kategori_stats = cur.fetchall()

    db.close()

    return jsonify({
        "stats": {
            "total_soal":               total_soal,
            "total_mahasiswa":          total_mahasiswa,
            "total_solved":             total_solved,
            "total_pending_challenge":  total_pending_challenge,
            "total_active_challenge":   total_active_challenge,
            "total_point_distributed":  total_point_distributed,
            "total_inactive":           total_inactive,
        },
        "top_soal":           top_soal,
        "hardest_soal":       hardest_soal,
        "leaderboard":        leaderboard,
        "level_dist":         level_dist,
        "recent_activity":    recent_activity,
        "pending_challenges": pending_challenges,
        "kategori_stats":     kategori_stats,
    })