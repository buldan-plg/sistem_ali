from flask import Blueprint, render_template, redirect, url_for, request
from configs.connection import get_db



role_bp = Blueprint("role", __name__, url_prefix = "/admin")

@role_bp.route("/roles", methods = ['GET'])
def get_all():
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT
                id_role, nama_role, deskripsi
            FROM tb_roles
        """)
        roles = query.fetchall()
        
    db.close()
    
    data = {
        'title' : 'Data roles',
        'roles' : roles
    }
    
    return render_template("admin/roles/roles.html", **data)

@role_bp.route("/roles/tambah", methods = ['GET'])
def form_tambah():
    
    data = {
        'title' : 'Tambah role'
    }
    return render_template("admin/roles/form_tambah.html", **data)

@role_bp.route("/roles/tambah", methods = ['POST'])
def insert():
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            INSERT INTO tb_roles(nama_role, deskripsi)
            VALUES (%s, %s)
        """, (request.form.get("nama_role"), request.form.get("deskripsi")))
    
    db.commit()
    db.close()
    return redirect(url_for('role.get_all'))

@role_bp.route("/roles/<int:id>/edit", methods = ['GET'])
def form_edit(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT id_role, nama_role, deskripsi
            FROM tb_roles
            WHERE id_role = %s
        """, (id,))
        role = query.fetchone()
    
    db.close()
    
    data = {
        'title' : 'Edit role',
        'role' : role
    }
    
    return render_template("admin/roles/form_edit.html", **data)

@role_bp.route("/roles/<int:id>/edit", methods = ['POST'])
def update(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            UPDATE tb_roles
            SET nama_role = %s, deskripsi = %s
            WHERE id_role = %s
        """, (request.form.get('nama_role'), request.form.get('deskripsi'), id))
    
    db.commit()
    db.close()
    return redirect(url_for('role.get_all'))

@role_bp.route("/roles/<int:id>/delete", methods = ['POST'])
def delete(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            DELETE FROM tb_roles
            WHERE id_role = %s
        """, (id,))
    
    db.commit()
    db.close()
    return redirect(url_for('role.get_all'))