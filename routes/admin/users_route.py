from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from werkzeug.security import generate_password_hash
from configs.connection import get_db
from routes.decorators import login_required, role_required

users_bp = Blueprint("users", __name__, url_prefix = "/admin")

@users_bp.route("/users", methods = ['GET'])
@login_required
def get_all():
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT
                u.id_user,
                u.username,
                u.password,
                r.nama_role  AS role,
                d.nama_dosen,
                m.nama_mahasiswa
            FROM tb_users u
            LEFT JOIN tb_roles r ON u.id_role = r.id_role
            LEFT JOIN tb_dosen d ON u.id_user = d.id_user
            LEFT JOIN tb_mahasiswa m ON u.id_user = m.id_user
        """)
        users = query.fetchall()
        
    db.close()
    
    data = {
        'title' : "Data users",
        'users' : users
    }
    
    return render_template("admin/users/users.html", **data)
        
@users_bp.route("/users/tambah", methods = ['GET'])
def form_tambah():
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT
                id_role, nama_role
            FROM tb_roles
            ORDER BY nama_role ASC
        """)
        roles = query.fetchall()
        
    db.close()
    
    data = {
        'title' : 'Tambah user',
        'roles' : roles
    }
    
    return render_template("admin/users/form_tambah.html", **data)

@users_bp.route("/api/data-role", methods = ['GET'])
def api_users():
    
    try:
        id_role = request.args.get('id_role')
        
        if not id_role:
            return jsonify({
                'status' : False,
                'message': 'Role tidak ditemukan.',
                'data' : []
            })
        
        db = get_db()
        with db.cursor() as query:
            query.execute("""
                SELECT
                    nama_role
                FROM tb_roles
                WHERE id_role = %s
            """, (id_role,))
            role = query.fetchone()
            data = []
            
            if role["nama_role"].lower() == "admin":
                query.execute("""
                    SELECT
                        id_dosen as id, nama_dosen as nama
                    FROM tb_dosen
                    WHERE id_user IS NULL
                    ORDER BY nama ASC
                """)
                data = query.fetchall()
                pass
            
            elif role["nama_role"].lower() == "mahasiswa":
                query.execute("""
                    SELECT
                        id_mahasiswa as id, nama_mahasiswa as nama
                    FROM tb_mahasiswa
                    WHERE id_user IS NULL
                    ORDER BY nama ASC
                """)
                data = query.fetchall()
                pass
            
            else:
                data = []
            
            return jsonify({
                'status' : True,
                'message' : 'Berhasil.',
                'data' : data
            })
    except Exception as e:
        return jsonify({
            'status' : False,
            'message' : str(e),
            'data' : []
        })

@users_bp.route("/users/tambah", methods=['POST'])
def insert():
    username    = request.form.get("username")
    password    = generate_password_hash(request.form.get("password"))
    id_role     = int(request.form.get("id_role"))
    id_pengguna = request.form.get("id_pengguna")

    ROLE_TABLE_MAP = {
        "admin"     : ("tb_dosen",     "id_dosen"),
        "mahasiswa" : ("tb_mahasiswa", "id_mahasiswa"),
    }

    db = get_db()
    try:
        with db.cursor() as query:
            # 1. Insert ke tb_users
            query.execute("""
                INSERT INTO tb_users (id_role, username, password, is_active)
                VALUES (%s, %s, %s, %s)
            """, (id_role, username, password, 1))
            id_user = query.lastrowid

            # Ambil nama_role — tb_roles (bukan tb_role)
            query.execute("""
                SELECT nama_role FROM tb_roles
                WHERE id_role = %s
            """, (id_role,))
            role = query.fetchone()

            if not role:
                raise Exception(f"Role dengan id {id_role} tidak ditemukan")

            nama_role = role["nama_role"].lower()

            # Jika role ada di mapping, hubungkan ke tabel entitas
            if nama_role in ROLE_TABLE_MAP:
                tabel, kolom_fk = ROLE_TABLE_MAP[nama_role]
                if id_pengguna:
                    # Dosen/mahasiswa sudah ada, tinggal hubungkan id_user
                    query.execute(f"""
                        UPDATE {tabel}
                        SET id_user = %s
                        WHERE {kolom_fk} = %s
                    """, (id_user, id_pengguna))
                else:
                    # Belum ada data entitas, insert minimal
                    query.execute(f"""
                        INSERT INTO {tabel} (id_user)
                        VALUES (%s)
                    """, (id_user,))
            # Jika role tidak ada di mapping (misal: role lain), lewati saja

        db.commit()
        return redirect(url_for("users.get_all"))

    except Exception as e:
        db.rollback()
        print(f"[ERROR insert user]: {e}")
        return f"Gagal menambahkan user: {e}", 500

    finally:
        db.close()

@users_bp.route("/users/<int:id>/edit", methods = ["GET"])
def form_edit(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT id_role, nama_role
            FROM tb_roles
            ORDER BY nama_role ASC
        """)
        roles = query.fetchall()
        
        query.execute("""
            SELECT
                id_user,id_role, username
            FROM tb_users
            WHERE id_user = %s
        """, (id,))
        user = query.fetchone()
    
    db.close()
    
    data = {
        'title' : 'Edit data user',
        'user' : user,
        'roles' : roles
    }
    return render_template("admin/users/form_edit.html", **data)

@users_bp.route("/users/<int:id>/edit", methods = ['POST'])
def update(id):
    
    # data user
    username = request.form.get("username")
    password = request.form.get("password")
    id_role = request.form.get("id_role")
    
    db = get_db()
    with db.cursor() as query:
        if password:
            password_hash = generate_password_hash(password)
            query.execute("""
                UPDATE tb_users 
                SET id_role = %s, username = %s, password = %s
                WHERE id_user = %s
            """, (id_role, username, password_hash, id))
            
        else:
            query.execute("""
                UPDATE tb_users
                SET id_role = %s, username = %s
                WHERE id_user = %s
            """, (id_role, username, id))
            
    db.commit()
    db.close()
    return redirect(url_for('users.get_all'))

@users_bp.route("/users/<int:id>/delete", methods = ['POST'])
def delete(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            DELETE FROM tb_users
            WHERE id_user = %s
        """, (id,))
    
    db.commit()
    db.close()
    
    return redirect(url_for('users.get_all'))