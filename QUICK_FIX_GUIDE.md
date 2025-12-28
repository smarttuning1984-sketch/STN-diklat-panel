# 🛠️ QUICK FIX GUIDE - STN-diklat-panel

Panduan langkah demi langkah untuk memperbaiki semua issue.

---

## 🔴 CRITICAL FIXES (Fix FIRST)

### ✅ FIX #1: Remove `import os.sys` Error

**File:** `app/routes.py` - Line 13

**Current:**
```python
import os.sys  # ❌ ERROR
```

**Change to:**
```python
import sys
```

---

### ✅ FIX #2: Fix add_admin.py Model Error

**File:** `add_admin.py` - Line 4

**Current:**
```python
from app.models import db, User  # ❌ User doesn't exist

app = create_app()
with app.app_context():
    admin = User(whatsapp="081234567890", role="admin")  # ❌ Wrong model
```

**Change to:**
```python
from app.models import db, Admin  # ✅ Use Admin instead

app = create_app()
with app.app_context():
    admin = Admin(username="admin", password="admin123")  # ✅ Admin model fields
    admin.set_password("admin123")
    if not Admin.query.filter_by(username="admin").first():
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin dibuat: Username=admin, Password=admin123")
    else:
        print("⚠️ Admin sudah ada.")
```

---

### ✅ FIX #3: Apply Rate Limiting to Login

**File:** `app/routes.py` - Tambahkan decorator ke login routes

**Before (Line 49-65):**
```python
@main.route('/login', methods=['GET', 'POST'])
def login():
    # ... login code
```

**After:**
```python
# Add import di top
from .security import rate_limit_login

# Apply decorator
@main.route('/login', methods=['GET', 'POST'])
@rate_limit_login
def login():
    # ... login code
```

**Do the same for:**
```python
@main.route('/admin/login', methods=['POST'])
@rate_limit_login
def admin_do_login():
    # ... code
```

---

### ✅ FIX #4: Use Password Strength Validation

**File:** `app/routes.py` - Line 654-659 (Register route)

**Current:**
```python
if len(password) < 6:
    flash('Password minimal 6 karakter!')
    return render_template('user/register.html')
```

**Change to:**
```python
# Add import di top
from .security import validate_password_strength

# Use validation
is_valid, message = validate_password_strength(password)
if not is_valid:
    flash(f'⚠️ {message}')
    return render_template('user/register.html')
```

---

### ✅ FIX #5: Add CSRF Tokens to Forms

**Files to update:**
- `app/templates/user/login.html`
- `app/templates/user/register.html`
- `app/templates/user/profile.html`
- `app/templates/admin/login.html`
- All forms in admin templates

**Pattern - Add to EVERY form:**
```html
<form method="POST" action="/login">
    {{ csrf_token() }}  {# ✅ ADD THIS #}
    
    <input type="text" name="whatsapp" required>
    <input type="password" name="password" required>
    <button type="submit">Login</button>
</form>
```

---

### ✅ FIX #6: Set SECRET_KEY Environment Variable

**File:** Create `.env` file at root

```env
# .env
SECRET_KEY=your-super-secret-key-here-min-32-characters-long
FLASK_ENV=production
FLASK_DEBUG=0
```

**File:** `.gitignore` - Make sure to add:
```
.env
*.env
```

---

### ✅ FIX #7: Fix requirements.txt

**File:** `requirements.txt`

**Current:**
```
flask
flask-sqlalchemy
python-dotenv
google-api-python-client
google-auth
flask-wtf
flask-limiter
flask-compress
python-dotenv  # ❌ DUPLICATE!
```

**Change to:**
```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
python-dotenv==1.0.0
google-api-python-client==2.100.0
google-auth==2.23.0
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.2.0
Flask-WTF==1.1.1
Flask-Limiter==3.5.0
Flask-Compress==1.13
Werkzeug==2.3.7
```

---

## ⚠️ HIGH PRIORITY FIXES

### ✅ FIX #8: Add Pagination to List Views

**File:** `app/routes.py` - Line 383 (kelola_peserta function)

**Current:**
```python
peserta_list = query.all()  # ❌ Gets ALL rows at once
return render_template('admin/kelola_peserta.html', peserta=peserta_list, ...)
```

**Change to:**
```python
# Add at top of function
page = request.args.get('page', 1, type=int)
per_page = 50

# Change query
peserta_list = query.paginate(page=page, per_page=per_page)

return render_template(
    'admin/kelola_peserta.html',
    peserta=peserta_list.items,  # ✅ Items only, not all
    pagination=peserta_list,
    current_page=page,
    ...
)
```

**Update template:** `app/templates/admin/kelola_peserta.html`
```html
<!-- Add pagination controls at bottom -->
{% if pagination.pages > 1 %}
<nav aria-label="Page navigation">
    {% if pagination.has_prev %}
        <a href="?page={{ pagination.prev_num }}">Previous</a>
    {% endif %}
    
    Page {{ current_page }} of {{ pagination.pages }}
    
    {% if pagination.has_next %}
        <a href="?page={{ pagination.next_num }}">Next</a>
    {% endif %}
</nav>
{% endif %}
```

---

### ✅ FIX #9: Add Input Validation to Search

**File:** `app/routes.py` - Line 380-384

**Current:**
```python
search = request.args.get('search', '').strip()
if search:
    query = query.filter(...)
```

**Change to:**
```python
search = request.args.get('search', '').strip()

# ✅ Validate search input
if search:
    if len(search) > 100:
        search = search[:100]
        flash('Search terlalu panjang, dipotong 100 karakter')
    
    # Only allow alphanumeric, spaces, dash, underscore
    if not all(c.isalnum() or c in ' -_' for c in search):
        flash('Search hanya bisa berisi huruf, angka, spasi, dash, underscore')
        search = ''
    
    if search:
        query = query.filter(...)
```

---

### ✅ FIX #10: Run Database Optimization Script

**Command:**
```bash
cd /workspaces/STN-diklat-panel
python migrate_add_indexes.py
```

**Output should be:**
```
✅ Index dibuat: idx_peserta_akses_workshop
✅ Index dibuat: idx_peserta_status_pembayaran
✅ Index dibuat: idx_peserta_batch
✅ Index dibuat: idx_peserta_whatsapp
✅ Index dibuat: idx_batch_nama
✅ Index dibuat: idx_admin_username

✅ Semua indexes berhasil ditambahkan!
```

---

### ✅ FIX #11: Add Session ID Regeneration After Login

**File:** `app/routes.py` - Line 62-65 (login function)

**Current:**
```python
session['user_id'] = peserta.id
session['nama'] = peserta.nama
session['akses_workshop'] = peserta.akses_workshop
return redirect('/dashboard')
```

**Change to:**
```python
# Add import at top
from flask import session as flask_session

# Regenerate session after login
flask_session.clear()  # ✅ Clear old session
session['user_id'] = peserta.id
session['nama'] = peserta.nama
session['akses_workshop'] = peserta.akses_workshop
return redirect('/dashboard')
```

---

### ✅ FIX #12: Add File MIME Type Validation

**File:** `app/routes.py` - Line 317-339 (upload_payment)

**Current:**
```python
file = request.files['proof']
if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    # ... just save
```

**Change to:**
```python
import mimetypes

# Add this function near ALLOWED_EXTENSIONS
def get_mime_type(filename):
    """Get MIME type dari filename"""
    mime, _ = mimetypes.guess_extension(filename)
    return mime

file = request.files['proof']

# ✅ Validate MIME type
if file and allowed_file(file.filename):
    mime_type = file.content_type
    allowed_mimes = ['image/png', 'image/jpeg', 'application/pdf']
    
    if mime_type not in allowed_mimes:
        flash(f'File type tidak diizinkan: {mime_type}')
        return redirect('/dashboard')
    
    # ✅ Also check file size (max 5MB)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to start
    
    if file_size > 5 * 1024 * 1024:  # 5MB
        flash('File terlalu besar (max 5MB)')
        return redirect('/dashboard')
    
    filename = secure_filename(file.filename)
    # ... rest of code
```

---

## 📊 MEDIUM PRIORITY FIXES

### ✅ FIX #13: Batch Processing untuk CSV Import

**File:** `app/routes.py` - Line 481-545 (admin_import)

**Current:**
```python
for idx, row in enumerate(reader, start=2):
    # ...
    db.session.add(newp)  # One by one
created += 1

db.session.commit()  # One big commit at end
```

**Change to:**
```python
batch_size = 1000
for idx, row in enumerate(reader, start=2):
    try:
        # ... same logic ...
        
        # ✅ Batch commit every 1000 rows
        if (idx - 2) % batch_size == 0 and idx > 2:
            db.session.commit()
            print(f"Progress: {idx} rows processed")
    except Exception as e:
        # ...
        continue

# Final commit
db.session.commit()
```

---

### ✅ FIX #14: Add Caching for Google Drive Catalog

**File:** `sync_drive.py` - Add caching

**Add at top:**
```python
import json
from datetime import datetime, timedelta
import os

# ✅ Add caching
CACHE_DIR = 'instance/cache'
CACHE_FILE = os.path.join(CACHE_DIR, 'docs_catalog_cache.json')
CACHE_DURATION = 3600  # 1 hour

def get_cached_catalog():
    """Get catalog from cache if fresh"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                return data.get('catalog'), True  # Return cache
    return None, False

def save_catalog_cache(catalog):
    """Save catalog to cache"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'catalog': catalog
        }, f)
```

**Modify main():**
```python
def main():
    # ✅ Check cache first
    cached_catalog, from_cache = get_cached_catalog()
    if from_cache:
        print("📦 Using cached catalog (< 1 hour old)")
        return cached_catalog
    
    print("🚀 Fetching fresh catalog from Google Drive...")
    service = get_drive_service()
    catalog = {}
    # ... rest of code ...
    
    # ✅ Save to cache
    save_catalog_cache(catalog)
    return catalog
```

---

### ✅ FIX #15: Add Input Length Limits

**File:** `app/routes.py` - Add validators

```python
# Add helper function
def validate_input_length(value, field_name, max_length=255):
    """Validate input length"""
    value = str(value).strip()
    if len(value) > max_length:
        return False, f"{field_name} terlalu panjang (max {max_length} chars)"
    return True, value

# Use in register route (line 640+):
def register():
    if request.method == 'POST':
        # Validate inputs
        nama = request.form['nama'].strip()
        is_valid, nama = validate_input_length(nama, 'Nama', 100)
        if not is_valid:
            flash(is_valid)  # Error message
            return render_template('user/register.html')
        
        # ... continue for other fields ...
```

---

## 🧪 TESTING CHECKLIST

After applying fixes, test:

```bash
# 1. Test import error is fixed
python -c "from app.routes import main; print('✅ Import OK')"

# 2. Test database indexes
python migrate_add_indexes.py

# 3. Test admin creation
python add_admin.py

# 4. Start server and test
python run.py
```

Then in browser:
- [ ] Try login with weak password → Should fail
- [ ] Try login 6x quickly → Should rate limit
- [ ] Try search with "'; DROP --" → Should be blocked
- [ ] Try upload 100MB file → Should fail
- [ ] List 1000+ peserta → Should paginate

---

## 📋 DEPLOYMENT CHECKLIST

Before deploying to production:

```bash
# 1. Update requirements
pip install -r requirements.txt

# 2. Set environment
export SECRET_KEY="your-production-secret-key"
export FLASK_ENV=production
export FLASK_DEBUG=0

# 3. Run migrations
python migrate_add_indexes.py

# 4. Create initial admin
python add_admin.py

# 5. Test
python -m pytest tests/ (if you have tests)

# 6. Run with production server
gunicorn -w 4 -b 0.0.0.0:8080 run:app
```

---

**Last Updated:** 2025-12-28
