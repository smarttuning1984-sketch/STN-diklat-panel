from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Peserta(db.Model):
    __tablename__ = 'peserta'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    whatsapp = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=True)
    alamat = db.Column(db.String(255), nullable=True)
    nama_bengkel = db.Column(db.String(100), nullable=True)
    alamat_bengkel = db.Column(db.String(255), nullable=True)
    status_pekerjaan = db.Column(db.String(50), nullable=True)
    alasan = db.Column(db.Text, nullable=True)
    batch = db.Column(db.String(50), default="Batch Baru")
    akses_workshop = db.Column(db.Boolean, default=False)
    status_pembayaran = db.Column(db.String(20), default="Belum")  # "Belum", "Lunas", "Ditolak"
    whatsapp_link = db.Column(db.String(255), nullable=True)
    tanggal_daftar = db.Column(db.DateTime, default=datetime.utcnow)
    password_hash = db.Column(db.String(128), nullable=True)
    payment_proof = db.Column(db.String(255), nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class Batch(db.Model):
    __tablename__ = 'batch'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), unique=True, nullable=False)
    whatsapp_link = db.Column(db.String(255), nullable=False)
    akses_workshop_default = db.Column(db.Boolean, default=False)
    aktif = db.Column(db.Boolean, default=True)
    tanggal_dibuat = db.Column(db.DateTime, default=datetime.utcnow)

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Jadwal(db.Model):
    __tablename__ = 'jadwal'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=False)
    batch = db.relationship('Batch', backref='jadwal_list')
    hari = db.Column(db.String(20), nullable=False)  # Senin, Selasa, etc
    waktu_mulai = db.Column(db.String(10), nullable=False)  # HH:MM format
    waktu_selesai = db.Column(db.String(10), nullable=False)  # HH:MM format
    topik = db.Column(db.String(255), nullable=False)
    sesi = db.Column(db.String(50), nullable=True)  # Sesi 1, Sesi 2, etc
    keterangan = db.Column(db.Text, nullable=True)
    tanggal_dibuat = db.Column(db.DateTime, default=datetime.utcnow)
    tanggal_diubah = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Document(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(255), nullable=False, index=True)
    kategori = db.Column(db.String(100), nullable=False, index=True)
    deskripsi = db.Column(db.Text, nullable=True)
    filepath = db.Column(db.String(500), nullable=False, unique=True)
    tipe_file = db.Column(db.String(50), nullable=False)  # html, json, pdf, etc
    ukuran_kb = db.Column(db.Float, nullable=True)
    is_arsip = db.Column(db.Boolean, default=True)  # True untuk arsip bengkel
    is_json = db.Column(db.Boolean, default=False)  # True untuk file JSON
    konten_search = db.Column(db.Text, nullable=True)  # Konten untuk full-text search
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    tanggal_ditambah = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    tanggal_diupdate = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Document {self.nama}>'
