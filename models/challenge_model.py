from configs.connection import get_db
from .point_model import calculate_point, _upsert_total_point

CREATOR_POINT_TIERS   = [
    {"min_solvers": 7,  "max_solvers": 10, "point": 150, "label": "🔥 Legendary"},
    {"min_solvers": 4,  "max_solvers": 6,  "point": 100, "label": "⚡ Epic"},
    {"min_solvers": 1,  "max_solvers": 3,  "point": 50,  "label": "✨ Rare"},
    {"min_solvers": 0,  "max_solvers": 0,  "point": 200, "label": "💀 Unsolvable"},
]
CHALLENGE_DURATION_DAYS = 7
DOWNVOTE_AUTO_REJECT    = 5
MAX_SOLVERS_GET_POINT   = 10


def submit_challenge(id_mahasiswa, data):
    if not _is_eligible(id_mahasiswa):
        return {"success": False, "message": "Selesaikan semua soal reguler terlebih dahulu."}

    db  = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO tb_challenges
            (id_mahasiswa, judul, deskripsi, expected_output, level)
        VALUES (%s, %s, %s, %s, %s)
    """, (id_mahasiswa, data["judul"], data["deskripsi"],
          data["expected_output"], data.get("level","medium")))
    id_ch = cur.lastrowid

    for bahasa, kode in (data.get("starter_code") or {}).items():
        if kode:
            cur.execute("""
                INSERT INTO tb_challenge_starter_code (id_challenge, bahasa, kode)
                VALUES (%s, %s, %s)
            """, (id_ch, bahasa, kode))

    db.commit()
    db.close()
    return {"success": True, "message": "Tantangan disubmit! Menunggu review dosen."}


def _is_eligible(id_mahasiswa):
    from models.quiz_model import get_total_soal
    total = get_total_soal()

    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT COUNT(*) AS solved FROM tb_quiz_results WHERE id_mahasiswa=%s AND is_correct=1",
        (id_mahasiswa,)
    )
    row = cur.fetchone()
    db.close()
    return row["solved"] >= total


def approve_challenge(id_challenge):
    db  = get_db()
    cur = db.cursor()

    cur.execute("SELECT status FROM tb_challenges WHERE id_challenge=%s", (id_challenge,))
    ch = cur.fetchone()
    if not ch:
        db.close(); return {"success": False, "message": "Challenge tidak ditemukan."}
    if ch["status"] != "pending":
        db.close(); return {"success": False, "message": f"Status sudah: {ch['status']}."}

    cur.execute("""
        UPDATE tb_challenges SET
            status='approved',
            expires_at=DATE_ADD(NOW(), INTERVAL %s DAY)
        WHERE id_challenge=%s
    """, (CHALLENGE_DURATION_DAYS, id_challenge))

    db.commit()
    db.close()
    return {"success": True, "message": f"Challenge aktif selama {CHALLENGE_DURATION_DAYS} hari."}


def reject_challenge(id_challenge, reason="", reviewed_by=None):
    db  = get_db()
    cur = db.cursor()

    cur.execute("SELECT status FROM tb_challenges WHERE id_challenge=%s", (id_challenge,))
    ch = cur.fetchone()
    if not ch:
        db.close(); return {"success": False, "message": "Challenge tidak ditemukan."}
    if ch["status"] != "pending":
        db.close(); return {"success": False, "message": f"Status sudah: {ch['status']}."}

    cur.execute("""
        UPDATE tb_challenges SET
            status='rejected', rejected_reason=%s,
            reviewed_by=%s, reviewed_at=NOW()
        WHERE id_challenge=%s
    """, (reason, reviewed_by, id_challenge))

    db.commit()
    db.close()
    return {"success": True, "message": "Challenge ditolak."}


def solve_challenge(id_challenge, id_mahasiswa, is_correct, hint_used, waktu_selesai):
    db  = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM tb_challenges WHERE id_challenge=%s", (id_challenge,))
    ch = cur.fetchone()

    if not ch:
        db.close(); return {"success": False, "message": "Challenge tidak ditemukan."}
    if ch["status"] != "approved":
        db.close(); return {"success": False, "message": "Challenge belum aktif."}
    if ch["id_mahasiswa"] == id_mahasiswa:
        db.close(); return {"success": False, "message": "Tidak bisa mengerjakan tantanganmu sendiri."}

    # Cek expired
    cur.execute(
        "SELECT NOW() > expires_at AS is_expired FROM tb_challenges WHERE id_challenge=%s",
        (id_challenge,)
    )
    if cur.fetchone()["is_expired"]:
        cur.execute("UPDATE tb_challenges SET status='expired' WHERE id_challenge=%s", (id_challenge,))
        _award_creator_point(cur, ch)
        db.commit(); db.close()
        return {"success": False, "message": "Challenge sudah berakhir."}

    # Cek existing result
    cur.execute(
        "SELECT * FROM tb_challenge_results WHERE id_challenge=%s AND id_mahasiswa=%s",
        (id_challenge, id_mahasiswa)
    )
    existing = cur.fetchone()

    if existing and existing["is_correct"] == 1:
        db.close()
        return {"success": True, "status": "already_solved", "message": "Sudah diselesaikan!"}

    # Hitung rank saat ini
    cur.execute(
        "SELECT COUNT(*) AS total FROM tb_challenge_results WHERE id_challenge=%s AND is_correct=1",
        (id_challenge,)
    )
    solved_count  = cur.fetchone()["total"]
    solver_rank   = solved_count + 1 if is_correct else None
    attempt_count = 1
    point_earned  = 0

    if not existing:
        cur.execute("""
            INSERT INTO tb_challenge_results
                (id_challenge, id_mahasiswa, solver_rank, is_correct,
                 attempt_count, hint_used, waktu_selesai, solved_at, point_earned)
            VALUES (%s,%s,%s,%s,1,%s,%s,IF(%s=1,NOW(),NULL),0)
        """, (id_challenge, id_mahasiswa, solver_rank, is_correct,
              hint_used, waktu_selesai, is_correct))
    else:
        attempt_count = existing["attempt_count"] + 1
        hint_used     = max(existing["hint_used"], hint_used)
        cur.execute("""
            UPDATE tb_challenge_results SET
                is_correct=%s, attempt_count=%s, hint_used=%s, waktu_selesai=%s,
                solver_rank=IF(%s=1,%s,solver_rank),
                solved_at=IF(%s=1,NOW(),solved_at)
            WHERE id_challenge=%s AND id_mahasiswa=%s
        """, (is_correct, attempt_count, hint_used, waktu_selesai,
              is_correct, solver_rank, is_correct,
              id_challenge, id_mahasiswa))

    # Beri point solver jika rank <= 10
    if is_correct and solver_rank and solver_rank <= MAX_SOLVERS_GET_POINT:
        bd           = calculate_point(ch["level"], hint_used, attempt_count, waktu_selesai)
        point_earned = bd["total"]
        cur.execute(
            "UPDATE tb_challenge_results SET point_earned=%s WHERE id_challenge=%s AND id_mahasiswa=%s",
            (point_earned, id_challenge, id_mahasiswa)
        )
        _upsert_total_point(cur, id_mahasiswa, point_earned)

    # Cek apakah 10 solver terpenuhi → award creator point
    cur.execute(
        "SELECT COUNT(*) AS total FROM tb_challenge_results WHERE id_challenge=%s AND is_correct=1",
        (id_challenge,)
    )
    total_solvers = cur.fetchone()["total"]
    if total_solvers >= MAX_SOLVERS_GET_POINT and ch["creator_point_status"] == "pending":
        _award_creator_point(cur, ch)

    db.commit()
    db.close()

    return {
        "success":             True,
        "status":              "correct" if is_correct else "wrong",
        "solver_rank":         solver_rank,
        "point_earned":        point_earned,
        "eligible_for_point":  bool(solver_rank and solver_rank <= MAX_SOLVERS_GET_POINT),
        "message":             _solver_msg(is_correct, solver_rank, point_earned),
    }


def _award_creator_point(cur, ch):
    if ch["creator_point_status"] == "awarded":
        return

    cur.execute(
        "SELECT COUNT(*) AS total FROM tb_challenge_results WHERE id_challenge=%s AND is_correct=1",
        (ch["id_challenge"],)
    )
    total_solvers = cur.fetchone()["total"]

    creator_point = 0
    tier_label    = ""
    for tier in CREATOR_POINT_TIERS:
        if tier["min_solvers"] <= total_solvers <= tier["max_solvers"]:
            creator_point = tier["point"]
            tier_label    = tier["label"]
            break

    cur.execute("""
        UPDATE tb_challenges SET
            creator_point_status='awarded', creator_point_earned=%s
        WHERE id_challenge=%s
    """, (creator_point, ch["id_challenge"]))

    cur.execute("""
        INSERT INTO tb_points (id_mahasiswa, total_point, total_soal_solved,
                               total_challenge_created, total_creator_point)
        VALUES (%s, %s, 0, 1, %s)
        ON DUPLICATE KEY UPDATE
            total_point             = total_point + VALUES(total_point),
            total_challenge_created = total_challenge_created + 1,
            total_creator_point     = total_creator_point + VALUES(total_creator_point)
    """, (ch["id_mahasiswa"], creator_point, creator_point))


def downvote_challenge(id_challenge, id_mahasiswa, alasan=""):
    db  = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT id_mahasiswa, status, downvote_count FROM tb_challenges WHERE id_challenge=%s",
        (id_challenge,)
    )
    ch = cur.fetchone()
    if not ch:
        db.close(); return {"success": False, "message": "Challenge tidak ditemukan."}
    if ch["id_mahasiswa"] == id_mahasiswa:
        db.close(); return {"success": False, "message": "Tidak bisa downvote milik sendiri."}
    if ch["status"] not in ("pending","approved"):
        db.close(); return {"success": False, "message": "Challenge sudah tidak aktif."}

    cur.execute(
        "SELECT id_downvote FROM tb_challenge_downvotes WHERE id_challenge=%s AND id_mahasiswa=%s",
        (id_challenge, id_mahasiswa)
    )
    if cur.fetchone():
        db.close(); return {"success": False, "message": "Sudah pernah downvote."}

    cur.execute(
        "INSERT INTO tb_challenge_downvotes (id_challenge, id_mahasiswa, alasan) VALUES (%s,%s,%s)",
        (id_challenge, id_mahasiswa, alasan)
    )
    new_count = ch["downvote_count"] + 1
    cur.execute(
        "UPDATE tb_challenges SET downvote_count=%s WHERE id_challenge=%s",
        (new_count, id_challenge)
    )

    auto_rejected = False
    if new_count >= DOWNVOTE_AUTO_REJECT:
        cur.execute("""
            UPDATE tb_challenges SET status='rejected',
                rejected_reason='Auto-rejected: terlalu banyak downvote.'
            WHERE id_challenge=%s
        """, (id_challenge,))
        auto_rejected = True

    db.commit()
    db.close()
    return {"success": True, "auto_rejected": auto_rejected, "downvote_count": new_count}


def get_active_challenges(id_mahasiswa=None):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.id_challenge, c.judul, c.deskripsi, c.level,
               c.status, c.downvote_count, c.expires_at,
               c.creator_point_status, c.creator_point_earned,
               m.nama_mahasiswa AS creator_name, m.nim AS creator_nim,
               (SELECT COUNT(*) FROM tb_challenge_results r
                WHERE r.id_challenge=c.id_challenge AND r.is_correct=1) AS total_solvers,
               TIMESTAMPDIFF(HOUR, NOW(), c.expires_at) AS hours_remaining
        FROM tb_challenges c
        JOIN tb_mahasiswa m ON m.id_mahasiswa = c.id_mahasiswa
        WHERE c.status='approved' AND c.expires_at > NOW()
        ORDER BY c.created_at DESC
    """)
    challenges = cur.fetchall()

    if id_mahasiswa:
        for ch in challenges:
            ch["is_mine"]   = ch["id_challenge"] == id_mahasiswa  # akan di-override
            cur.execute(
                "SELECT id_result FROM tb_challenge_results "
                "WHERE id_challenge=%s AND id_mahasiswa=%s AND is_correct=1",
                (ch["id_challenge"], id_mahasiswa)
            )
            ch["is_solved"]  = cur.fetchone() is not None
            ch["slots_left"] = max(0, MAX_SOLVERS_GET_POINT - ch["total_solvers"])

    db.close()
    return challenges


def get_challenge_detail(id_challenge, id_mahasiswa=None):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, m.nama_mahasiswa AS creator_name,
               (SELECT COUNT(*) FROM tb_challenge_results r
                WHERE r.id_challenge=c.id_challenge AND r.is_correct=1) AS total_solvers
        FROM tb_challenges c
        JOIN tb_mahasiswa m ON m.id_mahasiswa = c.id_mahasiswa
        WHERE c.id_challenge=%s
    """, (id_challenge,))
    ch = cur.fetchone()
    if not ch:
        db.close(); return None

    ch.pop("expected_output", None)
    ch["starter_code"] = _get_challenge_starter_code(cur, id_challenge)

    if id_mahasiswa:
        cur.execute(
            "SELECT id_result FROM tb_challenge_results "
            "WHERE id_challenge=%s AND id_mahasiswa=%s AND is_correct=1",
            (id_challenge, id_mahasiswa)
        )
        ch["is_mine"]   = False  # diset di route dari session
        ch["is_solved"] = cur.fetchone() is not None

    db.close()
    return ch


def get_pending_challenges():
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*, m.nama_mahasiswa AS creator_name, m.nim
        FROM tb_challenges c
        JOIN tb_mahasiswa m ON m.id_mahasiswa = c.id_mahasiswa
        WHERE c.status='pending'
        ORDER BY c.created_at ASC
    """)
    rows = cur.fetchall()
    db.close()
    for ch in rows: ch.pop("expected_output", None)
    return rows


def get_my_challenges(id_mahasiswa):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM tb_challenge_results r
                WHERE r.id_challenge=c.id_challenge AND r.is_correct=1) AS total_solvers
        FROM tb_challenges c
        WHERE c.id_mahasiswa=%s
        ORDER BY c.created_at DESC
    """, (id_mahasiswa,))
    rows = cur.fetchall()
    db.close()
    for ch in rows: ch.pop("expected_output", None)
    return rows


def get_challenge_leaderboard(id_challenge):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT r.solver_rank, m.nama_mahasiswa, m.nim,
               r.point_earned, r.waktu_selesai, r.hint_used, r.solved_at
        FROM tb_challenge_results r
        JOIN tb_mahasiswa m ON m.id_mahasiswa = r.id_mahasiswa
        WHERE r.id_challenge=%s AND r.is_correct=1
        ORDER BY r.solver_rank ASC
    """, (id_challenge,))
    rows = cur.fetchall()
    db.close()
    return rows


def expire_old_challenges():
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT * FROM tb_challenges
        WHERE status='approved' AND expires_at <= NOW() AND creator_point_status='pending'
    """)
    expired = cur.fetchall()

    for ch in expired:
        cur.execute(
            "UPDATE tb_challenges SET status='expired' WHERE id_challenge=%s", (ch["id_challenge"],)
        )
        _award_creator_point(cur, ch)

    db.commit()
    db.close()
    return {"expired_count": len(expired)}


# ── Helpers ───────────────────────────────────────────
def _get_challenge_starter_code(cur, id_challenge):
    cur.execute(
        "SELECT bahasa, kode FROM tb_challenge_starter_code WHERE id_challenge=%s",
        (id_challenge,)
    )
    return {r["bahasa"]: r["kode"] for r in cur.fetchall()}

def _solver_msg(is_correct, rank, point):
    if not is_correct: return "❌ Belum tepat, coba lagi!"
    if rank and rank <= MAX_SOLVERS_GET_POINT:
        return f"✅ Benar! Kamu solver ke-{rank} dan mendapat {point} point!"
    return f"✅ Benar! Tapi kamu solver ke-{rank}, point hanya untuk 10 pertama."