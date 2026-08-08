from flask import Blueprint, render_template, redirect, url_for, request
from configs.connection import get_db

mahasiswa_bp = Blueprint('mahasiswa', __name__, url_prefix = '/admin')

@mahasiswa_bp.route("/mahasiswa", methods = ['GET'])
def get_all():
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT 
                id_mahasiswa,
                nim,
                nama_mahasiswa,
                jenis_kelamin,
                alamat
            FROM tb_mahasiswa
        """)
        mahasiswa = query.fetchall()
    
    db.close()
    
    data = {
        'title' : 'Data mahasiswa',
        'mahasiswa' : mahasiswa
    }
    return render_template("admin/mahasiswa/mahasiswa.html", **data)

@mahasiswa_bp.route("/mahasiswa/<int:id>/detail", methods = ['GET'])
def get_detail(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT 
                nim,
                nama_mahasiswa as nama,
                jenis_kelamin,
                tanggal_lahir,
                email,
                no_hp,
                alamat,
                angkatan
            FROM tb_mahasiswa
            WHERE id_mahasiswa = %s
        """, (id,))
        mahasiswa = query.fetchone()
    
    db.close()
    data = {
        'title' : 'Detail mahasiswa',
        'mahasiswa' : mahasiswa
    }
    
    return render_template("admin/mahasiswa/detail.html", **data)

@mahasiswa_bp.route("/mahasiswa/tambah", methods = ['GET'])
def form_tambah():
    
    data = {
        'title' : 'Tambah mahsiswa'
    }
    return render_template("admin/mahasiswa/form_tambah.html", **data)

@mahasiswa_bp.route("/mahasiswa/tambah", methods = ['POST'])
def insert():
    
    # data mahasiswa
    nim = request.form.get("nim")
    nama = request.form.get("nama")
    angkatan = request.form.get("angkatan")[:4]
    jk = request.form.get("jk")
    tgl_lahir = request.form.get("tgl_lahir")
    email = request.form.get("email")
    no_hp = request.form.get("no_hp")
    alamat = request.form.get("alamat")
    
    # query insert
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            INSERT INTO tb_mahasiswa
                (nim, nama_mahasiswa, jenis_kelamin, tanggal_lahir, email, no_hp, alamat, angkatan)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (nim, nama, jk, tgl_lahir, email, no_hp, alamat, angkatan))
    
    db.commit()
    db.close()
    
    return redirect(url_for('mahasiswa.get_all'))

@mahasiswa_bp.route("/mahasiswa/<int:id>/edit", methods = ['GET'])
def form_edit(id):
    
    db = get_db()
    with db.cursor() as query:
        query.execute("""
            SELECT
                id_mahasiswa,
                nim,
                nama_mahasiswa as nama,
                jenis_kelamin,
                tanggal_lahir,
                email,
                no_hp,
                alamat,
                angkatan
            FROM tb_mahasiswa
            WHERE id_mahasiswa = %s
        """, (id,))
        mahasiswa = query.fetchone()
    
    db.close()
    data = {
        'title' : 'Edit mahasiswa',
        'mahasiswa' : mahasiswa
    }
    return render_template("admin/mahasiswa/form_edit.html", **data)