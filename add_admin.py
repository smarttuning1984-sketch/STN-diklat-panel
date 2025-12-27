from app import create_app
from app.models import db, User

app = create_app()
with app.app_context():
    admin = User(whatsapp="081234567890", role="admin")
    admin.set_password("admin123")
    if not User.query.filter_by(whatsapp="081234567890").first():
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin dibuat: WA=081234567890, Password=admin123")
    else:
        print("⚠️ Admin sudah ada.")