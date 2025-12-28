# 🧪 TESTING GUIDE - Audit Issues Verification

Panduan lengkap untuk menguji dan memverifikasi setiap issue yang ditemukan dalam audit.

---

## 📋 PRE-TESTING CHECKLIST

```bash
# 1. Backup current state
cp -r /workspaces/STN-diklat-panel /workspaces/STN-diklat-panel.backup

# 2. Install fresh dependencies
pip install -r requirements.txt --force-reinstall

# 3. Remove old database
rm database/users.db

# 4. Create fresh database
python run.py  # This will create fresh DB
# Stop with Ctrl+C

# 5. Create test admin account
python add_admin.py
```

---

## 🔴 CRITICAL ISSUES - TESTING

### Test 1: Import Error (`import os.sys`)

**Current State (BROKEN):**
```bash
python -c "from app.routes import main"
# Error: cannot import name 'sys'
```

**After Fix:**
```bash
python -c "from app.routes import main"
# Should work without error
echo "✅ OK"
```

---

### Test 2: Model Error (add_admin.py)

**Current State (BROKEN):**
```bash
python add_admin.py
# Error: ImportError: cannot import name 'User'
```

**After Fix:**
```bash
python add_admin.py
# Output: ✅ Admin dibuat: Username=admin, Password=admin123
```

**Verify:**
```bash
python -c "
from app import create_app
from app.models import db, Admin

app = create_app()
with app.app_context():
    admin = Admin.query.filter_by(username='admin').first()
    if admin and admin.check_password('admin123'):
        print('✅ Admin login works!')
    else:
        print('❌ Admin not found or wrong password')
"
```

---

### Test 3: Rate Limiting on Login

**Setup:**
```bash
# Start the server
python run.py &
```

**Test Script - Create `test_rate_limit.py`:**
```python
import requests
import time

BASE_URL = 'http://localhost:5000'
LOGIN_URL = f'{BASE_URL}/admin/login'

# Try login 6 times with wrong password
print("🧪 Testing rate limiting...")
for i in range(6):
    response = requests.post(LOGIN_URL, data={
        'username': 'admin',
        'password': 'wrongpassword'
    })
    print(f"Attempt {i+1}: Status {response.status_code}")
    
    # Check for rate limit message
    if 'Terlalu banyak percobaan' in response.text:
        print("✅ Rate limiting WORKING! Message found after attempt", i+1)
        break
    elif i == 5:
        print("❌ Rate limiting NOT WORKING - no message after 6 attempts")
    
    time.sleep(0.5)
```

**Run:**
```bash
python test_rate_limit.py
# Expected: Rate limit message after 5 failed attempts
```

---

### Test 4: Password Strength Validation

**Test in Browser:**
1. Go to: `http://localhost:5000/register`
2. Try register dengan password `abc123`
3. Should show: **❌ Error - Password minimal 8 karakter**

**Test after fix:**
1. Try password `abc` (3 chars)
   - ❌ Should fail: "minimal 8 karakter"
2. Try password `abcdefgh` (8 chars, no number)
   - ❌ Should fail: "harus mengandung minimal 1 angka"
3. Try password `abcdefgh1` (8 chars, no uppercase)
   - ❌ Should fail: "harus mengandung minimal 1 huruf besar"
4. Try password `Abcdefgh1` (valid)
   - ✅ Should succeed

---

## 🟡 HIGH PRIORITY TESTS

### Test 5: CSRF Protection

**Current (after fix):**

1. Check form has token:
```bash
curl http://localhost:5000/login 2>/dev/null | grep csrf_token
# Should show: <input type="hidden" name="csrf_token" ...>
```

2. Test POST without token:
```python
import requests

# Without CSRF token
response = requests.post(
    'http://localhost:5000/login',
    data={'whatsapp': '081234567890', 'password': 'password'}
)

if response.status_code == 400:
    print("✅ CSRF protection WORKING - request blocked")
else:
    print("❌ CSRF protection NOT working - request accepted")
```

---

### Test 6: Secret Key Environment Variable

**Current (broken):**
```bash
grep "dev-secret-key" app/__init__.py
# Found hardcoded key = BAD
```

**After fix - Test:**
```bash
# Set env variable
export SECRET_KEY="my-super-secret-production-key-min-32-chars"

# Verify app uses it
python -c "
from app import create_app
app = create_app()
if app.config['SECRET_KEY'] == 'my-super-secret-production-key-min-32-chars':
    print('✅ Using environment SECRET_KEY')
else:
    print('❌ Still using hardcoded default')
"
```

---

### Test 7: Pagination on List Views

**Test:**
```bash
python -c "
from app import create_app
from app.models import db, Peserta

app = create_app()

# Add 200 test records
with app.app_context():
    for i in range(200):
        p = Peserta(
            nama=f'Test {i}',
            whatsapp=f'{1000000000 + i}'
        )
        db.session.add(p)
    db.session.commit()
    print('✅ Created 200 test records')
"
```

1. Go to: `http://localhost:5000/admin/peserta`
2. Should only show ~50 items per page (not all 200)
3. Should have "Next" button if page 2 exists
4. Test: Click "Next" - should work
5. Check URL changes to `?page=2`

**Test slow load:**
```bash
# Without pagination (old): >10 seconds to load
# With pagination (new): <1 second to load
```

---

### Test 8: Input Validation on Search

**Test Script - Create `test_search_validation.py`:**
```python
import requests

BASE_URL = 'http://localhost:5000'
SEARCH_URL = f'{BASE_URL}/admin/peserta'

print("🧪 Testing search validation...")

# Test 1: Very long search string
long_search = "a" * 500
response = requests.get(SEARCH_URL, params={'search': long_search})
if 'Search terlalu panjang' in response.text or len(long_search) > 100:
    print("✅ Long search string rejected or truncated")
else:
    print("⚠️ Long search might not be validated")

# Test 2: SQL injection attempt
injection = "'; DROP TABLE peserta; --"
response = requests.get(SEARCH_URL, params={'search': injection})
if 'Peserta' in response.text:  # Table still exists
    print("✅ SQL injection blocked - table still exists")
else:
    print("❌ Possible SQL injection vulnerability!")

# Test 3: Special characters
special = "@#$%^&*()"
response = requests.get(SEARCH_URL, params={'search': special})
if 'Search hanya bisa berisi' in response.text or response.status_code == 200:
    print("✅ Special characters handled")
else:
    print("⚠️ Special character handling unclear")
```

**Run:**
```bash
python test_search_validation.py
```

---

### Test 9: File Upload Validation

**Test Script - Create `test_file_upload.py`:**
```python
import requests
from io import BytesIO

BASE_URL = 'http://localhost:5000'

# First login as user
session = requests.Session()
session.get(f'{BASE_URL}/login')  # Get CSRF token

# Get CSRF token from login page
response = session.get(f'{BASE_URL}/login')
# Extract CSRF token from HTML (parse it)

print("🧪 Testing file upload validation...")

# Test 1: Upload non-PDF/JPG file (.exe)
files = {'proof': ('malware.exe', b'MZ\x90\x00')}  # PE header
response = session.post(
    f'{BASE_URL}/dashboard/upload-payment',
    files=files,
    data={'csrf_token': 'token_here'}
)
if 'Format file tidak didukung' in response.text:
    print("✅ .exe file rejected")
else:
    print("❌ .exe file might be accepted!")

# Test 2: Upload large file (>5MB)
large_content = b'x' * (6 * 1024 * 1024)  # 6MB
files = {'proof': ('large.jpg', large_content)}
response = session.post(
    f'{BASE_URL}/dashboard/upload-payment',
    files=files,
)
if 'terlalu besar' in response.text or len(large_content) > (5 * 1024 * 1024):
    print("✅ Large file rejected")
else:
    print("⚠️ Large file might be accepted!")

# Test 3: Upload valid PDF
pdf_content = b'%PDF-1.4\ntest content'  # Minimal PDF
files = {'proof': ('receipt.pdf', pdf_content)}
response = session.post(
    f'{BASE_URL}/dashboard/upload-payment',
    files=files,
)
if 'berhasil' in response.text or response.status_code == 302:
    print("✅ Valid PDF accepted")
else:
    print("❌ Valid PDF rejected!")
```

---

### Test 10: Database Indexes

**Test Performance Before/After:**

```bash
# Test BEFORE running migrate_add_indexes.py
python -c "
import time
from app import create_app
from app.models import db, Peserta

app = create_app()
with app.app_context():
    # Add 5000 test records (if not exists)
    if Peserta.query.count() < 5000:
        for i in range(5000):
            p = Peserta(
                nama=f'User {i}',
                whatsapp=f'{1000000000 + i}',
                status_pembayaran='Lunas'
            )
            db.session.add(p)
        db.session.commit()
    
    # Query test (without index)
    start = time.time()
    results = Peserta.query.filter_by(status_pembayaran='Lunas').all()
    duration_before = time.time() - start
    print(f'⏱️ Query time WITHOUT index: {duration_before:.3f}s')
"

# Run migration
python migrate_add_indexes.py

# Test AFTER adding indexes
python -c "
import time
from app import create_app
from app.models import db, Peserta

app = create_app()
with app.app_context():
    start = time.time()
    results = Peserta.query.filter_by(status_pembayaran='Lunas').all()
    duration_after = time.time() - start
    print(f'⏱️ Query time WITH index: {duration_after:.3f}s')
    print(f'📈 Improvement: {duration_before/duration_after:.1f}x faster')
"
```

---

## 🟠 MEDIUM PRIORITY TESTS

### Test 11: CSV Import Batch Processing

**Create test file - `test_large_import.py`:**
```python
import csv
import time
import requests
from datetime import datetime

# Create large CSV file
print("📝 Creating large CSV file (10,000 rows)...")
csv_path = 'test_10k_contacts.csv'
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['phone', 'name', 'email', 'group'])
    writer.writeheader()
    for i in range(10000):
        writer.writerow({
            'phone': f'{1000000000 + i}',
            'name': f'Contact {i}',
            'email': f'contact{i}@example.com',
            'group': 'Test Batch'
        })

# Test import speed
print("⏱️ Importing 10,000 rows...")
start = time.time()

with open(csv_path, 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:5000/admin/import',
        files=files
    )

duration = time.time() - start
print(f"✅ Import completed in {duration:.2f} seconds")
print(f"📊 Speed: {10000/duration:.0f} rows/second")

if duration < 30:
    print("✅ FAST - Batching is working!")
else:
    print("⚠️ SLOW - Batching might not be optimized")
```

---

### Test 12: Google Drive Caching

**Test:**
```bash
# First call - should fetch from Google Drive
time curl http://localhost:5000/documents

# Second call - should use cache (much faster)
time curl http://localhost:5000/documents

# Check cache file exists
ls -lh instance/cache/docs_catalog_cache.json
```

**Expected:**
- First call: ~5-10 seconds
- Second call: <100ms

---

## ✅ POST-FIX VERIFICATION

### Run Full Test Suite

```bash
#!/bin/bash
echo "🧪 Running full test suite..."

echo "1️⃣  Testing imports..."
python -c "from app import create_app; from app.routes import main; print('✅ Imports OK')" || exit 1

echo "2️⃣  Testing database..."
python migrate_add_indexes.py || exit 1

echo "3️⃣  Testing admin creation..."
python add_admin.py || exit 1

echo "4️⃣  Testing admin login..."
python -c "
from app import create_app
from app.models import db, Admin
app = create_app()
with app.app_context():
    admin = Admin.query.filter_by(username='admin').first()
    if admin and admin.check_password('admin123'):
        print('✅ Admin login works')
    else:
        print('❌ Admin login failed')
        exit(1)
" || exit 1

echo ""
echo "🎉 All basic tests passed!"
```

---

## 📊 TEST RESULTS TEMPLATE

Copy and fill in results:

```
TEST EXECUTION REPORT
====================
Date: ___________
Tester: __________

CRITICAL TESTS:
[ ] Test 1: Import error fixed - PASS/FAIL
[ ] Test 2: Admin model fixed - PASS/FAIL
[ ] Test 3: Rate limiting works - PASS/FAIL
[ ] Test 4: Password strength enforced - PASS/FAIL

HIGH PRIORITY TESTS:
[ ] Test 5: CSRF protection active - PASS/FAIL
[ ] Test 6: SECRET_KEY from env - PASS/FAIL
[ ] Test 7: Pagination working - PASS/FAIL
[ ] Test 8: Search input validated - PASS/FAIL
[ ] Test 9: File uploads validated - PASS/FAIL
[ ] Test 10: Database indexes applied - PASS/FAIL

MEDIUM PRIORITY TESTS:
[ ] Test 11: Batch import 10k rows in <30s - PASS/FAIL
[ ] Test 12: Google Drive caching working - PASS/FAIL

OVERALL: PASS / FAIL

Issues Found: ___________
Blocking Issues: ________
```

---

**Testing Guide v1.0**  
**Last Updated:** 2025-12-28
