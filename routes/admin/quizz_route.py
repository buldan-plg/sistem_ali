from flask import Blueprint, render_template, request, jsonify, session
from configs.connection import get_db
from models.quiz_model import create_soal, update_soal, delete_soal
from services.runner_service import run_code

admin_soal_bp = Blueprint("admin_soal", __name__, url_prefix = "/admin")

def require_admin():
    if session["user"].get("role") not in ("admin", "dosen"):
        return jsonify({"error": "Akses ditolak."}), 403
    return None

def get_id_user():
    return session["user"].get("id")

# ── Halaman ───────────────────────────────────────────
@admin_soal_bp.route("/soal")
def halaman_soal():
    err = require_admin()
    if err: return err
    return render_template("admin/soal/soal.html", title="Manajemen Soal")

# ── List semua soal ───────────────────────────────────
@admin_soal_bp.route("/api/soal", methods=["GET"])
def api_list_soal():
    err = require_admin()
    if err: return err
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.id_soal, s.judul, s.level, s.kategori,
               s.support_php, s.support_js, s.support_python,
               s.is_active, s.urutan, s.created_at,
               u.username AS created_by_name,
               (SELECT COUNT(*) FROM tb_quiz_results r
                WHERE r.id_soal = s.id_soal AND r.is_correct = 1) AS total_solved
        FROM tb_soal s
        LEFT JOIN tb_users u ON u.id_user = s.created_by
        ORDER BY s.urutan ASC, s.created_at DESC
    """)
    rows = cur.fetchall()
    db.close()
    return jsonify({"soal": rows, "total": len(rows)})

# ── Detail soal (untuk edit, include expected_output) ─
@admin_soal_bp.route("/api/soal/<int:id_soal>", methods=["GET"])
def api_detail_soal(id_soal):
    err = require_admin()
    if err: return err
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id_soal, judul, deskripsi, expected_output, level, kategori,
               support_php, support_js, support_python, is_active, urutan
        FROM tb_soal WHERE id_soal = %s
    """, (id_soal,))
    soal = cur.fetchone()
    if not soal:
        db.close()
        return jsonify({"error": "Soal tidak ditemukan."}), 404
    cur.execute(
        "SELECT bahasa, kode FROM tb_soal_starter_code WHERE id_soal = %s", (id_soal,)
    )
    soal["starter_code"] = {r["bahasa"]: r["kode"] for r in cur.fetchall()}
    cur.execute(
        "SELECT isi_hint FROM tb_soal_hints WHERE id_soal = %s ORDER BY urutan ASC",
        (id_soal,)
    )
    soal["hints"] = [r["isi_hint"] for r in cur.fetchall()]
    db.close()
    return jsonify(soal)

# ── Test run kode ─────────────────────────────────────
@admin_soal_bp.route("/api/soal/test", methods=["POST"])
def api_test_soal():
    err = require_admin()
    if err: return err
    data = request.json
    if not data.get("language") or not data.get("code"):
        return jsonify({"error": "language dan code wajib diisi."}), 400
    return jsonify({"output": run_code(data["language"], data["code"])})

# ── Tambah soal ───────────────────────────────────────
@admin_soal_bp.route("/api/soal", methods=["POST"])
def api_create_soal():
    err = require_admin()
    if err: return err
    data = request.json
    for f in ["judul", "deskripsi", "expected_output", "level", "kategori"]:
        if not data.get(f):
            return jsonify({"error": f"Field '{f}' wajib diisi."}), 400
    if not any([data.get("support_php"), data.get("support_js"), data.get("support_python")]):
        return jsonify({"error": "Pilih minimal 1 bahasa."}), 400
    return jsonify(create_soal(data, created_by=get_id_user())), 201

# ── Update soal ───────────────────────────────────────
@admin_soal_bp.route("/api/soal/<int:id_soal>", methods=["PUT"])
def api_update_soal(id_soal):
    err = require_admin()
    if err: return err
    data = request.json
    for f in ["judul", "deskripsi", "expected_output", "level", "kategori"]:
        if not data.get(f):
            return jsonify({"error": f"Field '{f}' wajib diisi."}), 400
    return jsonify(update_soal(id_soal, data))

# ── Toggle aktif/nonaktif ─────────────────────────────
@admin_soal_bp.route("/api/soal/<int:id_soal>/toggle", methods=["PATCH"])
def api_toggle_soal(id_soal):
    err = require_admin()
    if err: return err
    db  = get_db()
    cur = db.cursor()
    cur.execute("UPDATE tb_soal SET is_active = NOT is_active WHERE id_soal = %s", (id_soal,))
    cur.execute("SELECT is_active FROM tb_soal WHERE id_soal = %s", (id_soal,))
    row = cur.fetchone()
    db.commit()
    db.close()
    return jsonify({"success": True, "is_active": row["is_active"]})

# ── Hapus soal (soft delete) ──────────────────────────
@admin_soal_bp.route("/api/soal/<int:id_soal>", methods=["DELETE"])
def api_delete_soal(id_soal):
    err = require_admin()
    if err: return err
    return jsonify(delete_soal(id_soal))