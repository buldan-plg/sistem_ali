from configs.connection import get_db

BASE_POINTS      = {"easy": 100, "medium": 200, "hard": 350}
BONUS_NO_HINT    = {"easy": 20,  "medium": 50,  "hard": 100}
BONUS_SPEED      = {
    "easy":   {"limit": 60,  "bonus": 30},
    "medium": {"limit": 120, "bonus": 60},
    "hard":   {"limit": 180, "bonus": 100},
}
PENALTY_PER_WRONG = 10
MAX_PENALTY       = 50


def calculate_point(level, hint_used, attempt_count, waktu_selesai):
    base    = BASE_POINTS.get(level, 100)
    bonus_h = BONUS_NO_HINT.get(level, 0) if hint_used == 0 else 0
    bonus_s = 0
    cfg     = BONUS_SPEED.get(level, {})
    if waktu_selesai and cfg and waktu_selesai <= cfg["limit"]:
        bonus_s = cfg["bonus"]
    penalty = min(max(0, attempt_count - 1) * PENALTY_PER_WRONG, MAX_PENALTY)
    return {
        "base":        base,
        "bonus_hint":  bonus_h,
        "bonus_speed": bonus_s,
        "penalty":     -penalty,
        "total":       max(0, base + bonus_h + bonus_s - penalty),
    }


def save_quiz_result(id_mahasiswa, id_soal, bahasa, is_correct,
                     hint_used, waktu_selesai, level):
    db  = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT id_result, is_correct, attempt_count, hint_used FROM tb_quiz_results "
        "WHERE id_mahasiswa=%s AND id_soal=%s",
        (id_mahasiswa, id_soal)
    )
    existing = cur.fetchone()

    if existing and existing["is_correct"] == 1:
        db.close()
        return {"status": "already_solved", "message": "Soal ini sudah pernah kamu selesaikan!", "point": None}

    point_breakdown = None

    if not existing:
        cur.execute("""
            INSERT INTO tb_quiz_results
                (id_mahasiswa, id_soal, bahasa, is_correct, attempt_count, hint_used,
                 waktu_selesai, solved_at)
            VALUES (%s, %s, %s, %s, 1, %s, %s, IF(%s=1, NOW(), NULL))
        """, (id_mahasiswa, id_soal, bahasa, is_correct, hint_used,
              waktu_selesai, is_correct))
        attempt_count = 1
    else:
        attempt_count = existing["attempt_count"] + 1
        hint_used     = max(existing["hint_used"], hint_used)
        cur.execute("""
            UPDATE tb_quiz_results SET
                is_correct=%s, attempt_count=%s, hint_used=%s,
                waktu_selesai=%s, bahasa=%s,
                solved_at=IF(%s=1, NOW(), solved_at)
            WHERE id_mahasiswa=%s AND id_soal=%s
        """, (is_correct, attempt_count, hint_used, waktu_selesai,
              bahasa, is_correct, id_mahasiswa, id_soal))

    if is_correct:
        point_breakdown = calculate_point(level, hint_used, attempt_count, waktu_selesai)
        _upsert_total_point(cur, id_mahasiswa, point_breakdown["total"])

    db.commit()
    db.close()
    return {
        "status":  "correct" if is_correct else "wrong",
        "message": "Berhasil!" if is_correct else "Belum tepat, coba lagi!",
        "point":   point_breakdown,
        "attempt": attempt_count,
    }


def _upsert_total_point(cur, id_mahasiswa, earned_point):
    cur.execute("""
        INSERT INTO tb_points (id_mahasiswa, total_point, total_soal_solved)
        VALUES (%s, %s, 1)
        ON DUPLICATE KEY UPDATE
            total_point       = total_point + VALUES(total_point),
            total_soal_solved = total_soal_solved + 1
    """, (id_mahasiswa, earned_point))


def get_mahasiswa_points(id_mahasiswa):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT p.total_point, p.total_soal_solved,
               p.total_challenge_created, p.total_creator_point,
               m.nama_mahasiswa, m.nim
        FROM tb_points p
        JOIN tb_mahasiswa m ON m.id_mahasiswa = p.id_mahasiswa
        WHERE p.id_mahasiswa = %s
    """, (id_mahasiswa,))
    row = cur.fetchone()
    db.close()
    return row


def get_solved_soal_ids(id_mahasiswa):
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id_soal FROM tb_quiz_results WHERE id_mahasiswa=%s AND is_correct=1",
        (id_mahasiswa,)
    )
    rows = cur.fetchall()
    db.close()
    return [r["id_soal"] for r in rows]


def get_leaderboard(limit=10):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT
            ROW_NUMBER() OVER (ORDER BY p.total_point DESC) AS `rank`,
            m.nama_mahasiswa, m.nim,
            p.total_point, p.total_soal_solved,
            p.total_creator_point
        FROM tb_points p
        JOIN tb_mahasiswa m ON m.id_mahasiswa = p.id_mahasiswa
        ORDER BY p.total_point DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    db.close()
    return rows


def get_quiz_history(id_mahasiswa):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT r.id_soal, s.judul, r.bahasa, r.is_correct,
               r.attempt_count, r.hint_used, r.waktu_selesai, r.solved_at
        FROM tb_quiz_results r
        JOIN tb_soal s ON s.id_soal = r.id_soal
        WHERE r.id_mahasiswa = %s
        ORDER BY r.updated_at DESC
    """, (id_mahasiswa,))
    rows = cur.fetchall()
    db.close()
    return rows