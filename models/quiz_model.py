from configs.connection import get_db

def get_all_questions(level=None, category=None, language=None):
    db  = get_db()
    cur = db.cursor()

    sql    = """
        SELECT id_soal AS id, judul AS title, deskripsi AS description,
               level, kategori AS category,
               support_php, support_js, support_python, urutan
        FROM tb_soal WHERE is_active = 1
    """
    params = []
    if level:
        sql += " AND level = %s"; params.append(level)
    if category:
        sql += " AND kategori = %s"; params.append(category)
    if language:
        col = {"php":"support_php","javascript":"support_js","python":"support_python"}.get(language)
        if col: sql += f" AND {col} = 1"
    sql += " ORDER BY urutan ASC"

    cur.execute(sql, params)
    soal_list = cur.fetchall()

    for soal in soal_list:
        soal["languages"]    = _get_languages(soal)
        soal["starter_code"] = _get_starter_code(cur, soal["id"])
        for k in ("support_php","support_js","support_python","urutan"):
            soal.pop(k, None)

    db.close()
    return soal_list


def get_question_by_id(question_id):
    db  = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT id_soal AS id, judul AS title, deskripsi AS description,
               level, kategori AS category,
               support_php, support_js, support_python
        FROM tb_soal WHERE id_soal = %s AND is_active = 1
    """, (question_id,))
    soal = cur.fetchone()

    if not soal:
        db.close()
        return None

    soal["languages"]    = _get_languages(soal)
    soal["starter_code"] = _get_starter_code(cur, soal["id"])
    for k in ("support_php","support_js","support_python"):
        soal.pop(k, None)

    db.close()
    return soal


def validate_answer(question_id, actual_output):
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT expected_output FROM tb_soal WHERE id_soal = %s AND is_active = 1",
        (question_id,)
    )
    row = cur.fetchone()
    db.close()

    if not row:
        return {"correct": False, "message": "Soal tidak ditemukan."}

    expected = row["expected_output"].strip()
    actual   = actual_output.strip()
    correct  = expected == actual
    return {
        "correct":  correct,
        "expected": expected,
        "actual":   actual,
        "message":  "✅ Jawaban benar! Mantap!" if correct else "❌ Belum tepat, coba lagi!",
    }


def get_hint(question_id, hint_index=0):
    db  = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT isi_hint FROM tb_soal_hints
        WHERE id_soal = %s ORDER BY urutan ASC
    """, (question_id,))
    hints = cur.fetchall()
    db.close()

    total = len(hints)
    if not hints:
        return {"hint": None, "message": "Tidak ada hint.", "total": 0}
    if hint_index >= total:
        return {"hint": None, "message": "Tidak ada hint lagi.", "total": total}

    return {
        "hint":     hints[hint_index]["isi_hint"],
        "index":    hint_index,
        "total":    total,
        "has_more": hint_index + 1 < total,
    }


def get_categories():
    db  = get_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT kategori FROM tb_soal WHERE is_active = 1 ORDER BY kategori ASC")
    rows = cur.fetchall()
    db.close()
    return [r["kategori"] for r in rows]


def get_levels():
    return ["easy", "medium", "hard"]


def get_total_soal():
    db  = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM tb_soal WHERE is_active = 1")
    row = cur.fetchone()
    db.close()
    return row["total"]


def create_soal(data, created_by=None):
    db  = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO tb_soal
            (judul, deskripsi, expected_output, level, kategori,
             support_php, support_js, support_python, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data["judul"], data["deskripsi"], data["expected_output"],
        data.get("level","easy"), data.get("kategori","basic"),
        int(data.get("support_php", True)),
        int(data.get("support_js",  True)),
        int(data.get("support_python", True)),
        created_by,
    ))
    id_soal = cur.lastrowid

    for bahasa, kode in (data.get("starter_code") or {}).items():
        if kode:
            cur.execute(
                "INSERT INTO tb_soal_starter_code (id_soal, bahasa, kode) VALUES (%s,%s,%s)",
                (id_soal, bahasa, kode)
            )
    for i, hint in enumerate(data.get("hints") or []):
        if hint:
            cur.execute(
                "INSERT INTO tb_soal_hints (id_soal, urutan, isi_hint) VALUES (%s,%s,%s)",
                (id_soal, i, hint)
            )

    db.commit()
    db.close()
    return {"success": True, "id_soal": id_soal}


def update_soal(id_soal, data):
    db  = get_db()
    cur = db.cursor()

    cur.execute("""
        UPDATE tb_soal SET
            judul=%s, deskripsi=%s, expected_output=%s, level=%s, kategori=%s,
            support_php=%s, support_js=%s, support_python=%s
        WHERE id_soal=%s
    """, (
        data["judul"], data["deskripsi"], data["expected_output"],
        data.get("level","easy"), data.get("kategori","basic"),
        int(data.get("support_php", True)),
        int(data.get("support_js",  True)),
        int(data.get("support_python", True)),
        id_soal,
    ))

    if "starter_code" in data:
        cur.execute("DELETE FROM tb_soal_starter_code WHERE id_soal=%s", (id_soal,))
        for bahasa, kode in data["starter_code"].items():
            if kode:
                cur.execute(
                    "INSERT INTO tb_soal_starter_code (id_soal, bahasa, kode) VALUES (%s,%s,%s)",
                    (id_soal, bahasa, kode)
                )

    if "hints" in data:
        cur.execute("DELETE FROM tb_soal_hints WHERE id_soal=%s", (id_soal,))
        for i, hint in enumerate(data["hints"]):
            if hint:
                cur.execute(
                    "INSERT INTO tb_soal_hints (id_soal, urutan, isi_hint) VALUES (%s,%s,%s)",
                    (id_soal, i, hint)
                )

    db.commit()
    db.close()
    return {"success": True}


def delete_soal(id_soal):
    db  = get_db()
    cur = db.cursor()
    cur.execute("UPDATE tb_soal SET is_active = 0 WHERE id_soal = %s", (id_soal,))
    db.commit()
    db.close()
    return {"success": True}


# ── Helpers ───────────────────────────────────────────
def _get_languages(soal):
    langs = []
    if soal.get("support_php"):    langs.append("php")
    if soal.get("support_js"):     langs.append("javascript")
    if soal.get("support_python"): langs.append("python")
    return langs

def _get_starter_code(cur, id_soal):
    cur.execute(
        "SELECT bahasa, kode FROM tb_soal_starter_code WHERE id_soal = %s", (id_soal,)
    )
    return {r["bahasa"]: r["kode"] for r in cur.fetchall()}