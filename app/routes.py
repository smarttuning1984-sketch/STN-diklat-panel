import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import db, Peserta, Batch, Admin
from werkzeug.utils import secure_filename
from flask import current_app
import time

main = Blueprint('main', __name__)

# === LANDING PAGE ===
@main.route('/')
def landing():
    return render_template('landing.html')

# === PENDAFTARAN ===
@main.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        nama = request.form['nama']
        wa = request.form['whatsapp']
        email = request.form.get('email', '')
        
        if Peserta.query.filter_by(whatsapp=wa).first():
            flash('Nomor WhatsApp sudah terdaftar!')
            return redirect('/daftar')
        
        # Buat peserta baru (tanpa akses workshop otomatis)
        peserta = Peserta(
            nama=nama,
            whatsapp=wa,
            email=email,
            batch="Menunggu Penugasan"
        )
        # Opsional: beri password default atau kosong
        peserta.set_password("default123")  # bisa diubah nanti via admin
        
        db.session.add(peserta)
        db.session.commit()
        flash('Pendaftaran berhasil! Silakan login.')
        return redirect('/login')
    
    return render_template('user/register.html')

# === LOGIN USER ===
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        wa = request.form.get('whatsapp', '').strip()
        pwd = request.form.get('password', '').strip()
        
        # Validasi input
        if not wa or not pwd:
            flash('Nomor WhatsApp dan password harus diisi!')
            return render_template('user/login.html')
        
        peserta = Peserta.query.filter_by(whatsapp=wa).first()
        
        if not peserta:
            flash('Nomor WhatsApp tidak ditemukan!')
            return render_template('user/login.html')
        
        if not peserta.check_password(pwd):
            flash('Password salah!')
            return render_template('user/login.html')
        
        # Login berhasil
        session['user_id'] = peserta.id
        session['nama'] = peserta.nama
        session['akses_workshop'] = peserta.akses_workshop
        return redirect('/dashboard')
    
    return render_template('user/login.html')

# === DASHBOARD USER ===
@main.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    peserta = Peserta.query.get(session['user_id'])
    # simple weekly schedule reminder (static for now)
    weekly_schedule = [
        {'day': 'Senin', 'time': '19:00', 'topic': 'Sesi 1'},
        {'day': 'Rabu', 'time': '19:00', 'topic': 'Sesi 2'},
        {'day': 'Jumat', 'time': '19:00', 'topic': 'Sesi 3'},
    ]
    categories = ['EBOOKS', 'Pengetahuan', 'Service Manual 1', 'Service Manual 2']
    return render_template('user/dashboard.html', peserta=peserta, weekly_schedule=weekly_schedule, categories=categories)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/dashboard/upload-payment', methods=['POST'])
def upload_payment():
    if 'user_id' not in session:
        return redirect('/login')

    peserta = Peserta.query.get(session['user_id'])
    if not peserta:
        flash('Peserta tidak ditemukan')
        return redirect('/dashboard')

    if 'proof' not in request.files:
        flash('File bukti transfer tidak ditemukan')
        return redirect('/dashboard')

    file = request.files['proof']
    if file.filename == '':
        flash('Nama file kosong')
        return redirect('/dashboard')

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = int(time.time())
        saved_name = f"peserta_{peserta.id}_{timestamp}_{filename}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_name)
        file.save(save_path)
        peserta.payment_proof = saved_name
        peserta.status_pembayaran = 'Menunggu'
        db.session.commit()
        flash('Bukti transfer berhasil diunggah. Status: Menunggu verifikasi.')
        return redirect('/dashboard')
    else:
        flash('Format file tidak didukung. Gunakan png/jpg/pdf')
        return redirect('/dashboard')


@main.route('/dashboard/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    peserta = Peserta.query.get(session['user_id'])
    if request.method == 'POST':
        peserta.nama_bengkel = request.form.get('nama_bengkel', peserta.nama_bengkel)
        peserta.alamat_bengkel = request.form.get('alamat_bengkel', peserta.alamat_bengkel)
        peserta.alamat = request.form.get('alamat', peserta.alamat)
        db.session.commit()
        flash('Profil berhasil diperbarui')
        return redirect('/dashboard')

    return render_template('user/profile.html', peserta=peserta)


@main.route('/dashboard/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect('/login')

    peserta = Peserta.query.get(session['user_id'])
    current = request.form.get('current_password', '').strip()
    new = request.form.get('new_password', '').strip()
    confirm = request.form.get('confirm_password', '').strip()

    if not peserta.check_password(current):
        flash('Password saat ini salah')
        return redirect('/dashboard')

    if new != confirm:
        flash('Password baru dan konfirmasi tidak cocok')
        return redirect('/dashboard')

    if len(new) < 6:
        flash('Password minimal 6 karakter')
        return redirect('/dashboard')

    peserta.set_password(new)
    db.session.commit()
    flash('Password berhasil diubah')
    return redirect('/dashboard')

# === DOKUMEN WORKSHOP (HANYA JIKA AKSES = TRUE) ===
@main.route('/workshop')
def workshop():
    if 'user_id' not in session or not session.get('akses_workshop', False):
        flash('Akses workshop manual hanya untuk peserta premium.')
        return redirect('/dashboard')
    
    catalog_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'docs_catalog.json')
    if os.path.exists(catalog_path):
        with open(catalog_path, encoding='utf-8') as f:
            catalog = json.load(f)
    else:
        catalog = {}
    
    return render_template('user/workshop.html', catalog=catalog)

# === LOGOUT ===
@main.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# === ADMIN: LOGIN ===
@main.route('/admin')
def admin_login():
    return render_template('admin/login.html')

@main.route('/admin/login', methods=['POST'])
def admin_do_login():
    username = request.form['username']
    password = request.form['password']
    admin = Admin.query.filter_by(username=username).first()
    
    if admin and admin.check_password(password):
        session['admin'] = True
        return redirect('/admin/dashboard')
    else:
        flash('Login admin gagal!')
        return redirect('/admin')

# === ADMIN: DASHBOARD ===
@main.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin')
    
    total_peserta = Peserta.query.count()
    belum_bayar = Peserta.query.filter_by(status_pembayaran='Belum').count()
    batches = Batch.query.all()
    
    return render_template('admin/dashboard.html',
                          total_peserta=total_peserta,
                          belum_bayar=belum_bayar,
                          batches=batches)

# === ADMIN: KELOLA PESERTA ===
@main.route('/admin/peserta')
def kelola_peserta():
    if not session.get('admin'):
        return redirect('/admin')
    
    status = request.args.get('status', 'semua')
    if status == 'belum':
        peserta_list = Peserta.query.filter_by(status_pembayaran='Belum').all()
    elif status == 'lunas':
        peserta_list = Peserta.query.filter_by(status_pembayaran='Lunas').all()
    else:
        peserta_list = Peserta.query.all()
    
    return render_template('admin/kelola_peserta.html', peserta=peserta_list, status_filter=status)

@main.route('/admin/peserta/<int:id>/toggle-akses', methods=['POST'])
def toggle_akses(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    peserta.akses_workshop = not peserta.akses_workshop
    db.session.commit()
    return redirect('/admin/peserta')

@main.route('/admin/peserta/<int:id>/hapus', methods=['POST'])
def hapus_peserta(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    db.session.delete(peserta)
    db.session.commit()
    return redirect('/admin/peserta')

# === ADMIN: BUAT BATCH BARU ===
@main.route('/admin/batch/buat', methods=['GET', 'POST'])
def buat_batch():
    if not session.get('admin'):
        return redirect('/admin')
    
    if request.method == 'POST':
        batch = Batch(
            nama=request.form['nama'],
            whatsapp_link=request.form['whatsapp_link'],
            akses_workshop_default='akses_workshop' in request.form
        )
        db.session.add(batch)
        db.session.commit()
        flash('Batch baru berhasil dibuat!')
        return redirect('/admin/dashboard')
    
    return render_template('admin/buat_batch.html')

# === ADMIN: LOGOUT ===
@main.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Ambil data
        nama = request.form['nama']
        wa = request.form['whatsapp']
        password = request.form['password']
        confirm = request.form['confirm_password']
        nama_bengkel = request.form['nama_bengkel']
        alamat_bengkel = request.form['alamat_bengkel']
        status = request.form['status_pekerjaan']
        alamat = request.form['alamat']
        alasan = request.form['alasan']

        # Validasi
        if password != confirm:
            flash('Password dan konfirmasi tidak cocok!')
            return render_template('user/register.html')
        
        if len(password) < 6:
            flash('Password minimal 6 karakter!')
            return render_template('user/register.html')

        if Peserta.query.filter_by(whatsapp=wa).first():
            flash('Nomor WhatsApp sudah terdaftar!')
            return render_template('user/register.html')

        # Buat & simpan peserta
        peserta = Peserta(
            nama=nama,
            whatsapp=wa,
            alamat=alamat,
            nama_bengkel=nama_bengkel,
            alamat_bengkel=alamat_bengkel,
            status_pekerjaan=status,
            alasan=alasan,
            batch="Menunggu Verifikasi"
        )
        peserta.set_password(password)
        
        db.session.add(peserta)
        db.session.commit()  # 🔥 INI KUNCI — JANGAN LUPA!

        flash('Pendaftaran berhasil! Silakan login.')
        return redirect('/login')
    
    return render_template('user/register.html')