# 🚀 PYTHONANYWHERE DEPLOYMENT GUIDE

## Persiapan Sebelum Deploy

### 1. Update run.py untuk Production
```python
# run.py
from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Development only
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080)),
        debug=os.environ.get('FLASK_DEBUG', False)
    )
```

### 2. Setup Environment Variables
```bash
# Di PythonAnywhere, set variables melalui web console:
export FLASK_ENV=production
export FLASK_DEBUG=False
export SECRET_KEY=your-random-secret-key-here
export DATABASE_URL=sqlite:////home/username/STN-diklat-panel/database/users.db
```

## Langkah-Langkah Deployment

### Step 1: Upload ke PythonAnywhere
```bash
# Clone repository di PythonAnywhere console:
git clone https://github.com/smarttuning1984-sketch/STN-diklat-panel.git
cd STN-diklat-panel
```

### Step 2: Create Virtual Environment
```bash
# Di /home/username/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Setup Database
```bash
# Di project directory
python3 -c "from app import create_app; app = create_app(); print('Database initialized')"
```

### Step 4: Configure WSGI in PythonAnywhere
1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose Python 3.x
4. Choose **Manual configuration**
5. Set WSGI configuration file:
   - Source code: `/home/username/STN-diklat-panel`
   - WSGI file: `/home/username/STN-diklat-panel/pythonanywhere_wsgi.py`
   - Python: `/home/username/STN-diklat-panel/venv/bin/python3.x`

### Step 5: Update Virtualenv Path
In WSGI file configuration, update the virtualenv path:
```
/home/username/STN-diklat-panel/venv
```

### Step 6: Configure Static Files
In Web tab, add:
- URL: `/static/`
- Directory: `/home/username/STN-diklat-panel/static`

### Step 7: Reload Web App
Click **Reload** button in PythonAnywhere

## File Structure untuk Production
```
STN-diklat-panel/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── templates/
├── static/
│   └── dokumen_bengkel.db (3.0 MB)
├── database/
│   └── users.db
├── pythonanywhere_wsgi.py    ← PENTING
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── credentials.json (opsional, untuk Google Drive)
```

## Troubleshooting

### Error 500: ModuleNotFoundError
- ✅ Pastikan virtualenv di-activate
- ✅ Pastikan requirements.txt di-install
- ✅ Restart web app

### Static Files Not Loading
- ✅ Check static files path di Web settings
- ✅ Reload web app

### Database Not Found
- ✅ Pastikan database/users.db ada di server
- ✅ Set DATABASE_URL dengan path absolut

### Port Already in Use
- ✅ Di PythonAnywhere, port otomatis di-assign
- ✅ Jangan hardcode port di WSGI

## Performance Tips

1. **Set DEBUG=False** di production
2. **Use production WSGI** (tidak flask development server)
3. **Enable caching** untuk static files
4. **Monitor log files** untuk errors

## Security Checklist

- [ ] Ubah SECRET_KEY ke random string
- [ ] Set FLASK_DEBUG=False
- [ ] Jangan commit credentials.json
- [ ] Jangan commit .env file (gunakan .env.example)
- [ ] Set database permissions readonly untuk non-admin
- [ ] Update ALLOWED_HOSTS jika diperlukan

## Useful Commands

```bash
# Connect to PythonAnywhere bash console
ssh username@ssh.pythonanywhere.com

# Update code
cd ~/STN-diklat-panel
git pull origin main

# Activate virtualenv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Check logs
tail -f /var/log/pythonanywhere/user_pythonanywhere_com_wsgi.log
```

## Contact & Support

Jika ada masalah:
1. Check PythonAnywhere error logs
2. Review pythonanywhere_wsgi.py configuration
3. Verify all environment variables set correctly
