import os
import json
import sqlite3
import requests
import csv
from io import StringIO
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response, stream_with_context
from .models import db, Peserta, Batch, Admin, Jadwal
from werkzeug.utils import secure_filename
from flask import current_app
import time

main = Blueprint('main', __name__)

# === Database Dokumen Bengkel ===
DOKUMEN_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'dokumen_bengkel.db')

def get_dokumen_db_connection():
    """Koneksi ke database dokumen bengkel"""
    if os.path.exists(DOKUMEN_DB_PATH):
        conn = sqlite3.connect(DOKUMEN_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    return None

# === Konfigurasi kategori dokumen ===
DOKUMEN_CATEGORIES = {
    "12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z": {"name": "📚 EBOOKS", "display": "EBOOKS"},
    "1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll": {"name": "🧠 Pengetahuan", "display": "Pengetahuan"},
    "1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW": {"name": "🔧 Service Manual 1", "display": "Service Manual 1"},
    "1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT": {"name": "⚙️ Service Manual 2", "display": "Service Manual 2"}
}

# === LANDING PAGE ===
@main.route('/')
def landing():
    return render_template('landing.html')

# === PENDAFTARAN ===
@main.route('/daftar', methods=['GET', 'POST'])
def daftar():
    # Arahkan semua ke route pendaftaran utama `/register` untuk konsistensi
    return redirect(url_for('main.register'))


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
    
    # Ambil jadwal dari database berdasarkan batch peserta
    weekly_schedule = []
    if peserta:
        # Cari batch berdasarkan nama batch peserta
        batch = Batch.query.filter_by(nama=peserta.batch).first()
        if batch:
            # Ambil semua jadwal untuk batch ini
            jadwal_list = Jadwal.query.filter_by(batch_id=batch.id).all()
            weekly_schedule = [
                {
                    'day': j.hari,
                    'time': j.waktu_mulai,
                    'topic': j.topik,
                    'sesi': j.sesi,
                    'waktu_selesai': j.waktu_selesai
                }
                for j in jadwal_list
            ]
        
        # Jika tidak ada jadwal di database, gunakan default
        if not weekly_schedule:
            weekly_schedule = [
                {'day': 'Senin', 'time': '19:00', 'topic': 'Sesi 1', 'sesi': None, 'waktu_selesai': '20:30'},
                {'day': 'Rabu', 'time': '19:00', 'topic': 'Sesi 2', 'sesi': None, 'waktu_selesai': '20:30'},
                {'day': 'Jumat', 'time': '19:00', 'topic': 'Sesi 3', 'sesi': None, 'waktu_selesai': '20:30'},
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

# === DOKUMEN BENGKEL ===
@main.route('/documents')
def documents():
    if 'user_id' not in session:
        return redirect('/login')
    
    # Kategori dokumen yang tersedia
    categories = {
        'EBOOKS': {
            'icon': '📚',
            'display_name': 'EBOOKS',
            'description': 'Koleksi ebook berkualitas tinggi',
            'folder_id': '12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z'
        },
        'Pengetahuan': {
            'icon': '🧠',
            'display_name': 'Pengetahuan',
            'description': 'Materi pengetahuan dan referensi',
            'folder_id': '1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll'
        },
        'Service_Manual_1': {
            'icon': '🔧',
            'display_name': 'Service Manual 1',
            'description': 'Panduan servis kendaraan modern',
            'folder_id': '1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW'
        },
        'Service_Manual_2': {
            'icon': '⚙️',
            'display_name': 'Service Manual 2',
            'description': 'Panduan servis komponen dan sistem',
            'folder_id': '1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT'
        }
    }
    
    return render_template('user/documents.html', categories=categories)


# === LIHAT FOLDER DOKUMEN ===
@main.route('/documents/folder/<folder_id>')
def view_dokumen_folder(folder_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_dokumen_db_connection()
    if not conn:
        flash('Database dokumen tidak ditemukan')
        return redirect('/documents')
    
    try:
        # Ambil nama folder
        folder_row = conn.execute(
            "SELECT name FROM files WHERE id = ? AND is_directory = 1", (folder_id,)
        ).fetchone()
        folder_name = folder_row['name'] if folder_row else 'Folder'
        
        # Ambil isi folder
        items = conn.execute(
            "SELECT id, name, is_directory, mime_type FROM files WHERE parent_id = ? ORDER BY is_directory DESC, name",
            (folder_id,)
        ).fetchall()
        
        # Hitung file count
        file_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM files WHERE parent_id = ? AND is_directory = 0",
            (folder_id,)
        ).fetchone()['cnt']
        
        return render_template('user/dokumen_folder.html', 
                             folder_id=folder_id,
                             folder_name=folder_name,
                             items=items,
                             file_count=file_count)
    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect('/documents')
    finally:
        conn.close()


# === PREVIEW/DOWNLOAD DOKUMEN ===
@main.route('/documents/file/<file_id>')
def view_dokumen_file(file_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    conn = get_dokumen_db_connection()
    if not conn:
        flash('Database dokumen tidak ditemukan')
        return redirect('/documents')
    
    try:
        file_info = conn.execute(
            "SELECT * FROM files WHERE id = ? AND is_directory = 0", (file_id,)
        ).fetchone()
        
        if not file_info:
            flash('File tidak ditemukan')
            return redirect('/documents')
        
        return render_template('user/dokumen_preview.html', file=file_info)
    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect('/documents')
    finally:
        conn.close()


# === PROXY DOWNLOAD FILE DARI GOOGLE DRIVE ===
@main.route('/documents/download/<file_id>')
def download_dokumen(file_id):
    """Proxy untuk download file dari Google Drive menggunakan service account"""
    if 'user_id' not in session:
        return redirect('/login')
    
    # Cek apakah file ada di database
    conn = get_dokumen_db_connection()
    if conn:
        file_info = conn.execute(
            "SELECT * FROM files WHERE id = ?", (file_id,)
        ).fetchone()
        conn.close()
        if not file_info:
            return "File not found", 404
    
    # Coba ambil dari Google Drive langsung
    try:
        drive_url = f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media'
        
        # Jika ada credentials.json, gunakan service account
        creds_path = os.path.join(os.path.dirname(__file__), '..', 'app/templates/user/dokumen bengkel', 'credentials.json')
        if os.path.exists(creds_path):
            try:
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request as AuthRequest
                
                creds = service_account.Credentials.from_service_account_file(
                    creds_path, 
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
                creds.refresh(AuthRequest())
                headers = {'Authorization': f'Bearer {creds.token}'}
            except:
                headers = {}
        else:
            headers = {}
        
        # Download dari Google Drive
        response = requests.get(drive_url, headers=headers, stream=True, timeout=60)
        
        if response.status_code == 200:
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            return Response(stream_with_context(generate()), content_type=content_type)
        else:
            return f"Failed to download (status {response.status_code})", 502
    
    except Exception as e:
        return f"Error: {str(e)}", 500

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
    search = request.args.get('search', '').strip()
    
    query = Peserta.query
    
    # Filter by payment status
    if status == 'belum':
        query = query.filter_by(status_pembayaran='Belum')
    elif status == 'menunggu':
        query = query.filter_by(status_pembayaran='Menunggu')
    elif status == 'lunas':
        query = query.filter_by(status_pembayaran='Lunas')
    elif status == 'ditolak':
        query = query.filter_by(status_pembayaran='Ditolak')
    
    # Search by name or phone
    if search:
        query = query.filter(
            (Peserta.nama.ilike(f'%{search}%')) |
            (Peserta.whatsapp.ilike(f'%{search}%'))
        )
    
    peserta_list = query.all()
    total = Peserta.query.count()
    
    return render_template('admin/kelola_peserta.html', peserta=peserta_list, status_filter=status, search=search, total=total)

# === ADMIN: DOWNLOAD PESERTA ===
@main.route('/admin/peserta/download/csv')
def download_peserta_csv():
    if not session.get('admin'):
        return redirect('/admin')
    
    status = request.args.get('status', 'semua')
    search = request.args.get('search', '').strip()
    
    query = Peserta.query
    
    # Filter by payment status
    if status == 'belum':
        query = query.filter_by(status_pembayaran='Belum')
    elif status == 'menunggu':
        query = query.filter_by(status_pembayaran='Menunggu')
    elif status == 'lunas':
        query = query.filter_by(status_pembayaran='Lunas')
    elif status == 'ditolak':
        query = query.filter_by(status_pembayaran='Ditolak')
    
    # Search by name or phone
    if search:
        query = query.filter(
            (Peserta.nama.ilike(f'%{search}%')) |
            (Peserta.whatsapp.ilike(f'%{search}%'))
        )
    
    peserta_list = query.all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'No',
        'Nama',
        'WhatsApp',
        'Email',
        'Alamat',
        'Nama Bengkel',
        'Alamat Bengkel',
        'Status Pekerjaan',
        'Batch',
        'Status Pembayaran',
        'Akses Workshop',
        'Tanggal Daftar'
    ])
    
    # Data
    for idx, peserta in enumerate(peserta_list, 1):
        writer.writerow([
            idx,
            peserta.nama,
            peserta.whatsapp,
            peserta.email or '-',
            peserta.alamat or '-',
            peserta.nama_bengkel or '-',
            peserta.alamat_bengkel or '-',
            peserta.status_pekerjaan or '-',
            peserta.batch,
            peserta.status_pembayaran,
            'Ya' if peserta.akses_workshop else 'Tidak',
            peserta.tanggal_daftar.strftime('%d-%m-%Y %H:%M') if peserta.tanggal_daftar else '-'
        ])
    
    # Generate filename with timestamp
    filename = f"peserta_{status}_{datetime.now().strftime('%d-%m-%Y_%H-%M-%S')}.csv"
    
    # Return as downloadable file
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@main.route('/admin/peserta/<int:id>')

def peserta_detail(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    return render_template('admin/peserta_detail.html', peserta=peserta)

@main.route('/admin/peserta/<int:id>/edit', methods=['GET', 'POST'])
def edit_peserta(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    
    if request.method == 'POST':
        peserta.nama = request.form.get('nama', peserta.nama)
        peserta.whatsapp = request.form.get('whatsapp', peserta.whatsapp)
        peserta.email = request.form.get('email', peserta.email)
        peserta.alamat = request.form.get('alamat', peserta.alamat)
        peserta.nama_bengkel = request.form.get('nama_bengkel', peserta.nama_bengkel)
        peserta.alamat_bengkel = request.form.get('alamat_bengkel', peserta.alamat_bengkel)
        peserta.status_pekerjaan = request.form.get('status_pekerjaan', peserta.status_pekerjaan)
        peserta.alasan = request.form.get('alasan', peserta.alasan)
        peserta.batch = request.form.get('batch', peserta.batch)
        peserta.status_pembayaran = request.form.get('status_pembayaran', peserta.status_pembayaran)
        peserta.akses_workshop = 'akses_workshop' in request.form
        
        db.session.commit()
        flash(f'Data peserta {peserta.nama} berhasil diperbarui!')
        return redirect(f'/admin/peserta/{id}')
    
    batches = Batch.query.all()
    return render_template('admin/peserta_edit.html', peserta=peserta, batches=batches)

@main.route('/admin/peserta/<int:id>/toggle-akses', methods=['POST'])
def toggle_akses(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    peserta.akses_workshop = not peserta.akses_workshop
    db.session.commit()
    flash(f"Akses workshop {peserta.nama} diubah menjadi {'Aktif' if peserta.akses_workshop else 'Tidak Aktif'}")
    return redirect(f'/admin/peserta/{id}')

@main.route('/admin/peserta/<int:id>/hapus', methods=['POST'])
def hapus_peserta(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    nama = peserta.nama
    db.session.delete(peserta)
    db.session.commit()
    flash(f'Peserta {nama} berhasil dihapus!')
    return redirect('/admin/peserta')


# === ADMIN: GRUP DIKLAT (rename dari batch) ===
@main.route('/admin/grup')
def kelola_grup():
    if not session.get('admin'):
        return redirect('/admin')
    grups = Batch.query.all()
    return render_template('admin/grup_list.html', grups=grups)


@main.route('/admin/grup/<int:id>/toggle-akses', methods=['POST'])
def toggle_akses_grup(id):
    if not session.get('admin'):
        return redirect('/admin')
    grup = Batch.query.get_or_404(id)
    grup.akses_workshop_default = not grup.akses_workshop_default
    db.session.commit()
    # Apply group access setting to all peserta in this grup
    peserta_list = Peserta.query.filter_by(batch=grup.nama).all()
    for p in peserta_list:
        p.akses_workshop = grup.akses_workshop_default
    db.session.commit()
    flash(f"Akses workshop untuk grup '{grup.nama}' diubah menjadi {'Aktif' if grup.akses_workshop_default else 'Non-Aktif'} dan diterapkan ke peserta grup.")
    return redirect('/admin/dashboard')

# === ADMIN: VERIFIKASI PEMBAYARAN ===
@main.route('/admin/pembayaran')
def verifikasi_pembayaran():
    if not session.get('admin'):
        return redirect('/admin')
    
    status = request.args.get('status', 'menunggu')
    
    query = Peserta.query
    if status == 'menunggu':
        query = query.filter_by(status_pembayaran='Menunggu')
    elif status == 'lunas':
        query = query.filter_by(status_pembayaran='Lunas')
    elif status == 'ditolak':
        query = query.filter_by(status_pembayaran='Ditolak')
    else:
        query = query.filter(Peserta.status_pembayaran.in_(['Menunggu', 'Lunas', 'Ditolak']))
    
    peserta_list = query.all()
    return render_template('admin/verifikasi_pembayaran.html', peserta=peserta_list, status_filter=status)

@main.route('/admin/peserta/<int:id>/verifikasi', methods=['POST'])
def verifikasi_status(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    peserta = Peserta.query.get_or_404(id)
    status = request.form.get('status', 'Menunggu')
    
    if status in ['Belum', 'Menunggu', 'Lunas', 'Ditolak']:
        peserta.status_pembayaran = status
        db.session.commit()
        flash(f'Status pembayaran {peserta.nama} diubah menjadi {status}')
    else:
        flash('Status tidak valid!')
    
    return redirect('/admin/pembayaran')

# === ADMIN: BUAT GRUP DIKLAT BARU ===
@main.route('/admin/grup/buat', methods=['GET', 'POST'])
def buat_grup():
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
        flash('Grup diklat baru berhasil dibuat!')
        return redirect('/admin/grup')
    
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

# === ADMIN: JADWAL DIKLAT ===
@main.route('/admin/jadwal')
def admin_jadwal_list():
    if not session.get('admin'):
        return redirect('/admin')
    
    batches = Batch.query.all()
    jadwal_list = Jadwal.query.all()
    
    return render_template('admin/jadwal_list.html', batches=batches, jadwal=jadwal_list)

@main.route('/admin/jadwal/create', methods=['GET', 'POST'])
def admin_jadwal_create():
    if not session.get('admin'):
        return redirect('/admin')
    
    batches = Batch.query.all()
    
    if request.method == 'POST':
        batch_id = request.form.get('batch_id')
        hari = request.form.get('hari')
        waktu_mulai = request.form.get('waktu_mulai')
        waktu_selesai = request.form.get('waktu_selesai')
        topik = request.form.get('topik')
        sesi = request.form.get('sesi')
        keterangan = request.form.get('keterangan')
        
        if not all([batch_id, hari, waktu_mulai, waktu_selesai, topik]):
            flash('Semua field wajib diisi!')
            return render_template('admin/jadwal_form.html', batches=batches, form_title='Buat Jadwal Baru')
        
        jadwal = Jadwal(
            batch_id=batch_id,
            hari=hari,
            waktu_mulai=waktu_mulai,
            waktu_selesai=waktu_selesai,
            topik=topik,
            sesi=sesi,
            keterangan=keterangan
        )
        
        db.session.add(jadwal)
        db.session.commit()
        
        flash('Jadwal berhasil dibuat!')
        return redirect('/admin/jadwal')
    
    return render_template('admin/jadwal_form.html', batches=batches, form_title='Buat Jadwal Baru')

@main.route('/admin/jadwal/<int:id>/edit', methods=['GET', 'POST'])
def admin_jadwal_edit(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    jadwal = Jadwal.query.get_or_404(id)
    batches = Batch.query.all()
    
    if request.method == 'POST':
        jadwal.batch_id = request.form.get('batch_id')
        jadwal.hari = request.form.get('hari')
        jadwal.waktu_mulai = request.form.get('waktu_mulai')
        jadwal.waktu_selesai = request.form.get('waktu_selesai')
        jadwal.topik = request.form.get('topik')
        jadwal.sesi = request.form.get('sesi')
        jadwal.keterangan = request.form.get('keterangan')
        
        db.session.commit()
        
        flash('Jadwal berhasil diubah!')
        return redirect('/admin/jadwal')
    
    return render_template('admin/jadwal_form.html', 
                         batches=batches, 
                         jadwal=jadwal,
                         form_title='Edit Jadwal')

@main.route('/admin/jadwal/<int:id>/delete', methods=['POST'])
def admin_jadwal_delete(id):
    if not session.get('admin'):
        return redirect('/admin')
    
    jadwal = Jadwal.query.get_or_404(id)
    db.session.delete(jadwal)
    db.session.commit()
    
    flash('Jadwal berhasil dihapus!')
    return redirect('/admin/jadwal')