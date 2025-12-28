# 🔄 ONGOING MONITORING CHECKLIST

Untuk memastikan masalah tidak terulang di masa depan.

---

## 📋 PRE-DEPLOYMENT CHECKLIST

Gunakan checklist ini sebelum deploy ke production:

### Security Checks
- [ ] Tidak ada hardcoded passwords (grep untuk "admin123", "password123", dll)
- [ ] Tidak ada API keys/credentials di git (check .env.example hanya)
- [ ] SECRET_KEY berbeda dari development
- [ ] HTTPS enabled (jika di production)
- [ ] CSRF protection active
- [ ] Rate limiting enabled
- [ ] File upload validation active

### Code Quality Checks
- [ ] Tidak ada `import os.sys` atau syntax errors
- [ ] Tidak ada unused imports
- [ ] Tidak ada print() statements (gunakan logging)
- [ ] Semua models match dengan code yang menggunakan
- [ ] Database indexes applied

### Performance Checks
- [ ] Pagination implemented di semua list views
- [ ] Database queries optimized (no N+1)
- [ ] Caching enabled untuk expensive operations
- [ ] Batch processing untuk bulk imports
- [ ] Static file caching headers set

### Dependency Checks
- [ ] requirements.txt di-update dengan versi terbaru
- [ ] Tidak ada duplicate packages
- [ ] Semua imported packages ada di requirements.txt
- [ ] No security vulnerabilities: `pip check`

---

## 🚨 CRITICAL FILES TO MONITOR

### File: `app/routes.py`
**Risk:** Ini file terbesar dengan paling banyak logic
```bash
# Regular check
wc -l app/routes.py  # Should stay < 1000 lines
grep -n "query.all()" app/routes.py  # Check for N+1 issues
grep -n "db.session.add" app/routes.py  # Check for transaction issues
```

### File: `app/__init__.py`
**Risk:** Configuration file - kesalahan di sini affects semua
```bash
# Check
grep "dev-secret-key" app/__init__.py  # Should NOT exist in production
grep "DEBUG" app/__init__.py  # Should be False in production
```

### File: `requirements.txt`
**Risk:** Dependency conflicts
```bash
# Check
grep -c "==" requirements.txt  # Should have pinned versions
pip check  # Check for conflicts
```

### File: `database/users.db`
**Risk:** Data loss
```bash
# Regular backup
cd /workspaces/STN-diklat-panel
git add database/users.db
git commit -m "Backup database [date]"
```

---

## 🔍 AUTOMATED CHECKS

### Setup Git Pre-Commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Prevent bad commits

echo "🔍 Running pre-commit checks..."

# Check for hardcoded passwords
if grep -r "password.*=.*['\"][^'\"]*['\"]" app/ --include="*.py" | grep -v "check_password"; then
    echo "❌ Found hardcoded passwords!"
    exit 1
fi

# Check for dev secrets
if grep -r "dev-secret-key\|admin123" app/ --include="*.py"; then
    echo "❌ Found dev secrets!"
    exit 1
fi

# Check for print statements (should use logging)
if grep -r "^[[:space:]]*print(" app/ --include="*.py" | head -5; then
    echo "⚠️  Found print() statements - use logging instead"
fi

# Check Python syntax
python -m py_compile app/routes.py app/models.py app/__init__.py
if [ $? -ne 0 ]; then
    echo "❌ Python syntax error!"
    exit 1
fi

echo "✅ Pre-commit checks passed"
exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📊 PERFORMANCE MONITORING

### Query Performance Log

Add to `app/__init__.py`:
```python
# Enable query logging in development
if app.debug:
    import logging
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

Monitor queries:
```bash
# Run app and look for slow queries
python run.py 2>&1 | grep -i "duration\|query"
```

### Database Health Check

Create `check_db_health.py`:
```python
#!/usr/bin/env python3
from app import create_app
from app.models import db, Peserta, Batch, Admin
import time

app = create_app()

with app.app_context():
    print("🔍 Database Health Check")
    print("=" * 40)
    
    # Count records
    print(f"📊 Peserta: {Peserta.query.count()}")
    print(f"📊 Batches: {Batch.query.count()}")
    print(f"📊 Admins: {Admin.query.count()}")
    
    # Test query performance
    start = time.time()
    results = Peserta.query.filter_by(status_pembayaran='Lunas').all()
    duration = time.time() - start
    print(f"\n⏱️  Sample query time: {duration:.3f}s")
    if duration > 1:
        print("⚠️  WARNING: Query is slow! Check indexes.")
    
    # Check database size
    import os
    db_size = os.path.getsize('database/users.db')
    print(f"\n📁 Database size: {db_size / 1024 / 1024:.2f} MB")
    
    print("\n✅ Health check complete")
```

Run regularly:
```bash
python check_db_health.py
```

---

## 🛡️ SECURITY MONITORING

### Weekly Security Audit

```bash
#!/bin/bash
# weekly_security_check.sh

echo "🛡️  Weekly Security Audit"

# Check for exposed secrets
echo "1️⃣  Checking for exposed secrets..."
grep -r "password\|secret\|api_key\|token" app/ --include="*.py" | \
    grep -v "check_password\|set_password\|validate_password"

# Check dependencies for vulnerabilities
echo "2️⃣  Checking dependencies..."
pip install safety
safety check

# Check for SQL injection patterns
echo "3️⃣  Checking for SQL injection patterns..."
grep -r "\.format\|f\"" app/ --include="*.py" | grep -i "query\|sql"

# Check file permissions
echo "4️⃣  Checking file permissions..."
ls -la app/
ls -la app/templates/
ls -la instance/

# Check logs for suspicious activity
echo "5️⃣  Checking access logs..."
if [ -f "logs/access.log" ]; then
    tail -20 logs/access.log
fi

echo "✅ Security audit complete"
```

---

## 📈 PERFORMANCE MONITORING

### Monitor These Metrics

**Database:**
```bash
# Query count per request
# Slow query log
# Index usage
```

**Application:**
```bash
# Response time (should be <500ms for 99%)
# Error rate (should be <0.1%)
# Memory usage (should be stable)
```

**Server:**
```bash
# CPU usage
# Disk space
# Network bandwidth
```

Create monitoring dashboard:
```python
# app/monitoring.py
from datetime import datetime
import psutil

def get_system_metrics():
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent
    }
```

---

## 🔄 REGULAR MAINTENANCE SCHEDULE

### Daily
- [ ] Check error logs
- [ ] Monitor disk space
- [ ] Backup database

### Weekly  
- [ ] Run security audit (script above)
- [ ] Review slow queries
- [ ] Check for unused dependencies

### Monthly
- [ ] Update dependencies (safely)
- [ ] Review access logs
- [ ] Performance testing
- [ ] Security updates

### Quarterly
- [ ] Full code audit
- [ ] Update documentation
- [ ] Penetration testing
- [ ] Disaster recovery drill

---

## 📝 ISSUE PREVENTION

### Code Review Checklist

Before merging any PR:

- [ ] No hardcoded secrets or passwords
- [ ] All user inputs validated
- [ ] No SQL injection possible
- [ ] CSRF protection on forms
- [ ] Proper authentication/authorization
- [ ] No N+1 database queries
- [ ] Performance acceptable (< 500ms)
- [ ] No unused imports
- [ ] No print() statements
- [ ] Proper error handling
- [ ] Tests added/updated
- [ ] Documentation updated

### Common Issues to Watch For

```python
# ❌ BAD - N+1 problem
for user in User.query.all():
    print(user.profile.name)  # Extra query for each user!

# ✅ GOOD - Eager loading
users = User.query.options(joinedload(User.profile)).all()

# ❌ BAD - Hardcoded secret
SECRET_KEY = 'my-secret'

# ✅ GOOD - From environment
SECRET_KEY = os.getenv('SECRET_KEY')

# ❌ BAD - No validation
query = User.query.filter(User.name == request.args.get('name'))

# ✅ GOOD - Validated
name = request.args.get('name', '').strip()[:100]
query = User.query.filter(User.name.ilike(f'%{name}%'))
```

---

## 🚨 EMERGENCY PROCEDURES

### If Critical Issue Found

1. **Immediate Actions:**
   ```bash
   # 1. Take down production if needed
   # 2. Switch to backup/last known good version
   # 3. Notify team
   # 4. Preserve logs/evidence
   ```

2. **Investigation:**
   ```bash
   # Check logs
   tail -200 logs/error.log
   
   # Check database integrity
   sqlite3 database/users.db "PRAGMA integrity_check;"
   
   # Review recent changes
   git log --oneline -20
   ```

3. **Recovery:**
   ```bash
   # Restore from backup if needed
   cp database/users.db.backup database/users.db
   
   # Or rollback code
   git revert <commit-hash>
   
   # Restart service
   systemctl restart stn-panel
   ```

---

## 📊 DASHBOARD COMMANDS

Quick commands to check system health:

```bash
# All checks at once
echo "=== DATABASE ===" && python check_db_health.py && \
echo "=== DEPENDENCIES ===" && pip check && \
echo "=== CODE ===" && python -m py_compile app/*.py && \
echo "=== SECURITY ===" && grep -r "admin123\|dev-secret-key" app/ || echo "✅ No hardcoded secrets"
```

Create alias in `.bashrc`:
```bash
alias check-health='python check_db_health.py && pip check'
alias check-security='grep -r "admin123\|dev-secret-key\|password.*=.*\"" app/'
```

---

## 📞 ESCALATION CONTACTS

When issues occur:

- **Performance Issue:** Check database, enable caching, scale server
- **Security Issue:** Take down immediately, contact security team
- **Data Loss:** Restore from backup, audit logs
- **High Error Rate:** Check logs, rollback latest changes

---

**Monitoring Guide v1.0**  
**Last Updated:** 2025-12-28
