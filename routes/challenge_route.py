from flask import Blueprint, render_template, request, jsonify, session
from models.challenge_model import (
    submit_challenge, approve_challenge, reject_challenge,
    solve_challenge, downvote_challenge,
    get_active_challenges, get_challenge_detail,
    get_pending_challenges, get_my_challenges,
    get_challenge_leaderboard, expire_old_challenges
)
from services.runner_service import run_code

challenge_bp = Blueprint("challenge", __name__)

# ── Helpers ───────────────────────────────────────────
def get_mhs_id():  return session["user"].get("profile_id")
def get_role():    return session["user"].get("role")
def get_id_user(): return session["user"].get("id_user")

def require_login():
    if not get_mhs_id():
        from flask import redirect
        return redirect("/login")
    return None

def require_admin():
    if get_role() not in ("admin","dosen"):
        return jsonify({"error": "Akses ditolak."}), 403
    return None

# ══════════════════════════════════════════════════════
# HALAMAN — Mahasiswa
# ══════════════════════════════════════════════════════

# List challenge aktif
@challenge_bp.route("/mahasiswa/challenge")
def halaman_challenge():
    r = require_login()
    if r: return r
    return render_template("mahasiswa/challenge.html", title="Challenge")

# Submit challenge baru
@challenge_bp.route("/mahasiswa/challenge/submit")
def halaman_submit():
    r = require_login()
    if r: return r
    return render_template("mahasiswa/challenge_submit.html", title="Submit Challenge")

# Detail + solve challenge
@challenge_bp.route("/mahasiswa/challenge/<int:id_challenge>")
def halaman_solve(id_challenge):
    r = require_login()
    if r: return r
    return render_template("mahasiswa/challenge_solve.html",
                           title="Solve Challenge",
                           id_challenge=id_challenge)

# ══════════════════════════════════════════════════════
# HALAMAN — Admin/Dosen
# ══════════════════════════════════════════════════════

@challenge_bp.route("/admin/challenge")
def halaman_review():
    err = require_admin()
    if err: return err
    return render_template("admin/soal/challenge_review.html", title="Review Challenge")

# ══════════════════════════════════════════════════════
# API — Mahasiswa
# ══════════════════════════════════════════════════════

# List aktif
@challenge_bp.route("/api/challenges", methods=["GET"])
def api_list():
    challenges = get_active_challenges(get_mhs_id())
    return jsonify({"challenges": challenges, "total": len(challenges)})

# Detail satu challenge
@challenge_bp.route("/api/challenges/<int:id_challenge>", methods=["GET"])
def api_detail(id_challenge):
    ch = get_challenge_detail(id_challenge, get_mhs_id())
    if not ch:
        return jsonify({"error": "Challenge tidak ditemukan."}), 404
    # Tandai apakah milik sendiri
    if get_mhs_id():
        from configs.connection import get_db
        db  = get_db()
        cur = db.cursor()
        cur.execute("SELECT id_mahasiswa FROM tb_challenges WHERE id_challenge=%s", (id_challenge,))
        row = cur.fetchone()
        db.close()
        ch["is_mine"] = row and row["id_mahasiswa"] == get_mhs_id()
    return jsonify(ch)

# Submit challenge baru
@challenge_bp.route("/api/challenges", methods=["POST"])
def api_submit():
    if not get_mhs_id():
        return jsonify({"error": "Login terlebih dahulu."}), 401
    data     = request.json
    required = ["judul","deskripsi","expected_output","level"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Field '{f}' wajib diisi."}), 400
    result = submit_challenge(get_mhs_id(), data)
    return jsonify(result), 201 if result["success"] else 403

# Run & solve
@challenge_bp.route("/api/challenges/<int:id_challenge>/run", methods=["POST"])
def api_run(id_challenge):
    if not get_mhs_id():
        return jsonify({"error": "Login terlebih dahulu."}), 401
    data          = request.json
    language      = data.get("language")
    code          = data.get("code")
    hint_used     = data.get("hint_used", 0)
    waktu_selesai = data.get("waktu_selesai")

    if not language or not code:
        return jsonify({"error": "language dan code wajib diisi."}), 400

    output = run_code(language, code)

    # Ambil expected_output dari DB
    from db import get_db
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT expected_output, level, id_mahasiswa, status FROM tb_challenges WHERE id_challenge=%s",
        (id_challenge,)
    )
    ch = cur.fetchone()
    db.close()

    if not ch:
        return jsonify({"error": "Challenge tidak ditemukan."}), 404
    if ch["id_mahasiswa"] == get_mhs_id():
        return jsonify({"error": "Tidak bisa mengerjakan tantanganmu sendiri."}), 403

    is_correct = output.strip() == ch["expected_output"].strip()
    result     = solve_challenge(
        id_challenge  = id_challenge,
        id_mahasiswa  = get_mhs_id(),
        is_correct    = is_correct,
        hint_used     = hint_used,
        waktu_selesai = waktu_selesai,
    )
    return jsonify({"output": output, "is_correct": is_correct, "result": result})

# Downvote
@challenge_bp.route("/api/challenges/<int:id_challenge>/downvote", methods=["POST"])
def api_downvote(id_challenge):
    if not get_mhs_id():
        return jsonify({"error": "Login terlebih dahulu."}), 401
    alasan = request.json.get("alasan","")
    return jsonify(downvote_challenge(id_challenge, get_mhs_id(), alasan))

# Challenge buatan saya
@challenge_bp.route("/api/challenges/mine", methods=["GET"])
def api_mine():
    if not get_mhs_id():
        return jsonify({"error": "Login terlebih dahulu."}), 401
    return jsonify(get_my_challenges(get_mhs_id()))

# Leaderboard solver
@challenge_bp.route("/api/challenges/<int:id_challenge>/leaderboard", methods=["GET"])
def api_leaderboard(id_challenge):
    return jsonify(get_challenge_leaderboard(id_challenge))

# ══════════════════════════════════════════════════════
# API — Admin/Dosen
# ══════════════════════════════════════════════════════

@challenge_bp.route("/api/admin/challenges", methods=["GET"])
def api_admin_list():
    err = require_admin()
    if err: return err
    status = request.args.get("status","pending")
    from configs.connection import get_db
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.id_challenge, c.judul, c.deskripsi, c.level,
               c.status, c.downvote_count, c.rejected_reason,
               c.creator_point_status, c.creator_point_earned,
               c.created_at, c.expires_at, c.updated_at,
               m.nama_mahasiswa AS creator_name, m.nim AS creator_nim,
               (SELECT COUNT(*) FROM tb_challenge_results r
                WHERE r.id_challenge=c.id_challenge AND r.is_correct=1) AS total_solvers
        FROM tb_challenges c
        JOIN tb_mahasiswa m ON m.id_mahasiswa = c.id_mahasiswa
        WHERE c.status = %s
        ORDER BY c.created_at DESC
    """, (status,))
    rows = cur.fetchall()
    db.close()
    for ch in rows: ch.pop("expected_output", None)
    return jsonify({"challenges": rows, "total": len(rows)})

@challenge_bp.route("/api/admin/challenges/<int:id_challenge>", methods=["GET"])
def api_admin_detail(id_challenge):
    err = require_admin()
    if err: return err
    from db import get_db
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, m.nama_mahasiswa AS creator_name, m.nim AS creator_nim
        FROM tb_challenges c
        JOIN tb_mahasiswa m ON m.id_mahasiswa = c.id_mahasiswa
        WHERE c.id_challenge = %s
    """, (id_challenge,))
    ch = cur.fetchone()
    if not ch:
        db.close()
        return jsonify({"error": "Tidak ditemukan."}), 404
    cur.execute("SELECT bahasa, kode FROM tb_challenge_starter_code WHERE id_challenge=%s", (id_challenge,))
    ch["starter_code"] = {r["bahasa"]: r["kode"] for r in cur.fetchall()}
    db.close()
    return jsonify(ch)

@challenge_bp.route("/api/admin/challenges/<int:id_challenge>/approve", methods=["POST"])
def api_approve(id_challenge):
    err = require_admin()
    if err: return err
    return jsonify(approve_challenge(id_challenge))

@challenge_bp.route("/api/admin/challenges/<int:id_challenge>/reject", methods=["POST"])
def api_reject(id_challenge):
    err = require_admin()
    if err: return err
    reason = request.json.get("reason","")
    return jsonify(reject_challenge(id_challenge, reason, reviewed_by=get_id_user()))

@challenge_bp.route("/api/admin/challenges/expire", methods=["POST"])
def api_expire():
    err = require_admin()
    if err: return err
    return jsonify(expire_old_challenges())

@challenge_bp.route("/api/admin/challenges/stats", methods=["GET"])
def api_admin_stats():
    err = require_admin()
    if err: return err
    from configs.connection import get_db
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT
            SUM(status='pending')  AS pending,
            SUM(status='approved') AS approved,
            SUM(status='rejected') AS rejected,
            SUM(status='expired')  AS expired,
            COUNT(*)               AS total
        FROM tb_challenges
    """)
    stats = cur.fetchone()
    db.close()
    return jsonify(stats)