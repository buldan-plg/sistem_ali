from flask import Blueprint, render_template, request, jsonify, session
from models.quiz_model import (
    get_all_questions, get_question_by_id,
    validate_answer, get_hint,
    get_categories, get_levels
)
from services.runner_service import run_code
from models.point_model import (
    save_quiz_result, get_mahasiswa_points,
    get_solved_soal_ids, get_leaderboard, get_quiz_history
)

quiz_bp = Blueprint("quiz", __name__, url_prefix = '/mahasiswa')


# ── Helper: ambil id_mahasiswa dari session ──────────
def get_current_mahasiswa_id():
    """
    Ambil id_mahasiswa dari session login.
    Sesuaikan dengan sistem auth kamu.
    """
    return session["user"].get("profile_id")


# ─────────────────────────────────────────────────────
# Halaman utama
# ─────────────────────────────────────────────────────
@quiz_bp.route("/quiz")
def index():
    
    data = {
        'title' : 'Quiz'
    }
    return render_template("mahasiswa/quiz.html", **data)


# ─────────────────────────────────────────────────────
# API: Daftar soal
# GET /api/questions?level=easy&category=loop
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/questions", methods=["GET"])
def api_get_questions():
    level    = request.args.get("level")
    category = request.args.get("category")
    language = request.args.get("language")

    questions = get_all_questions(level=level, category=category, language=language)

    # Tandai soal yang sudah solved (dari DB jika login)
    id_mhs = get_current_mahasiswa_id()
    solved_ids = get_solved_soal_ids(id_mhs) if id_mhs else []
    for q in questions:
        q["solved"] = q["id"] in solved_ids

    return jsonify({"questions": questions, "total": len(questions)})


# ─────────────────────────────────────────────────────
# API: Detail soal
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/questions/<int:question_id>", methods=["GET"])
def api_get_question(question_id):
    question = get_question_by_id(question_id)
    if not question:
        return jsonify({"error": "Soal tidak ditemukan"}), 404
    return jsonify(question)


# ─────────────────────────────────────────────────────
# API: Run + Validasi + Simpan Point
# POST /api/run
# Body: { question_id, language, code, hint_used, waktu_selesai }
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/run", methods=["POST"])
def api_run_code():
    data          = request.json
    language      = data.get("language")
    code          = data.get("code")
    question_id   = data.get("question_id")
    hint_used     = data.get("hint_used", 0)
    waktu_selesai = data.get("waktu_selesai")  # detik dari timer frontend

    if not language or not code:
        return jsonify({"error": "language dan code wajib diisi"}), 400

    # 1. Jalankan kode
    output = run_code(language, code)

    result = {"output": output}

    # 2. Validasi jawaban
    if question_id:
        validation = validate_answer(question_id, output)
        result["validation"] = validation

        # 3. Simpan ke DB jika mahasiswa login
        id_mhs = get_current_mahasiswa_id()
        if id_mhs:
            question = get_question_by_id(question_id)
            level = question.get("level", "easy") if question else "easy"

            point_result = save_quiz_result(
                id_mahasiswa  = id_mhs,
                id_soal       = question_id,
                bahasa        = language,
                is_correct    = validation["correct"],
                hint_used     = hint_used,
                waktu_selesai = waktu_selesai,
                level         = level
            )
            result["point_result"] = point_result

    return jsonify(result)


# ─────────────────────────────────────────────────────
# API: Hint
# GET /api/questions/<id>/hint?index=0
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/questions/<int:question_id>/hint", methods=["GET"])
def api_get_hint(question_id):
    hint_index = int(request.args.get("index", 0))
    return jsonify(get_hint(question_id, hint_index))


# ─────────────────────────────────────────────────────
# API: Point mahasiswa yang sedang login
# GET /api/my-points
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/my-points", methods=["GET"])
def api_my_points():
    id_mhs = get_current_mahasiswa_id()
    if not id_mhs:
        return jsonify({"error": "Belum login"}), 401

    data = get_mahasiswa_points(id_mhs)
    return jsonify(data or {"total_point": 0, "total_soal_solved": 0})


# ─────────────────────────────────────────────────────
# API: Riwayat pengerjaan
# GET /api/my-history
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/my-history", methods=["GET"])
def api_my_history():
    id_mhs = get_current_mahasiswa_id()
    if not id_mhs:
        return jsonify({"error": "Belum login"}), 401

    return jsonify(get_quiz_history(id_mhs))


# ─────────────────────────────────────────────────────
# API: Leaderboard
# GET /api/leaderboard?limit=10
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    limit = int(request.args.get("limit", 10))
    return jsonify(get_leaderboard(limit))


# ─────────────────────────────────────────────────────
# API: Metadata
# ─────────────────────────────────────────────────────
@quiz_bp.route("/api/metadata", methods=["GET"])
def api_metadata():
    return jsonify({
        "categories": get_categories(),
        "levels":     get_levels(),
        "languages":  ["php", "javascript", "python"]
    })