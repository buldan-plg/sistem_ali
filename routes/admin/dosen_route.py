from flask import Blueprint, render_template, redirect, url_for, request
from configs.connection import get_db


dosen_bp = Blueprint("dosen", __name__, url_prefix="/admin")
@dosen_bp.route('/dosen', methods=['GET'])
def all_dosen():

    db=get_db()
    with db.cursor() as cursor:
        cursor.execute('''
            SELECT 
                id_dosen, nidn, nama_dosen, email
            FROM tb_dosen
            ORDER BY id_dosen DESC
        ''')
        dosen=cursor.fetchall()
    cursor.close()
    data = {
        'title' : 'Tabel Data Dosen',
        'dosen' : dosen
    }
    return render_template ('admin/dosen/tb_dosen.html', **data)

@dosen_bp.route('/dosen/tambah', methods=['GET'])
def tambah_dosen():
    data = {
        'title' : 'Tambah Data Dosen'
    }
    return render_template ('admin/dosen/add_dosen.html', **data)

@dosen_bp.route ('/dosen/tambah/simpan', methods=['POST'])
def tambah_simpan():
    # id_dosen=request.form['id_dosen']
    # id_user=request.form['id_user']
    nidn=request.form['nidn']
    nama_dosen=request.form['nama']
    email=request.form['email']
    no_hp=request.form['no_hp']
    alamat=request.form['alamat']
    # created_at=request.form['created_at']
    # updated_at=request.form['updated_at']
    db=get_db()
    with db.cursor() as cursor:
        cursor.execute('''INSERT INTO tb_dosen (nidn, nama_dosen, email, no_hp, alamat) 
        VALUES (%s, %s, %s, %s, %s)''',
        (nidn, nama_dosen, email, no_hp, alamat))
    db.commit()
    db.close()
    return redirect (url_for('dosen.all_dosen'))

@dosen_bp.route('/dosen/edit/<id>', methods=['GET'])
def edit_dosen(id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
            SELECT
                id_dosen, nidn, nama_dosen, email, no_hp, alamat
            FROM tb_dosen
            WHERE id_dosen = %s
        ''', (id,))
        row = cursor.fetchone()
        db.close()
    data = {
        "title" : "Edit data dosen",
        "dosen" : row
    }
    return render_template("admin/dosen/edit_dosen.html", **data)

@dosen_bp.route('/dosen/update', methods=['POST'])
def update():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
            UPDATE tb_dosen
            SET 
                nidn = %s, nama_dosen = %s, email = %s, no_hp = %s, alamat = %s
            WHERE id_dosen = %s
        ''', (request.form["nidn"], request.form['nama'], request.form['email'], request.form['nomor'], request.form['alamat'], request.form['id_dosen']))
    db.commit()
    db.close()
    return redirect(url_for('dosen.all_dosen'))

@dosen_bp.route('/dosen/delete/<id>', methods=['POST'])
def delete(id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute('''
            DELETE
            FROM tb_dosen
            WHERE id_dosen = %s
        ''', (id,))
    db.commit()
    db.close()
    return redirect(url_for('dosen.all_dosen'))