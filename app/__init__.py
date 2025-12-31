from flask import Flask
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    # Fix: Gunakan SECRET_KEY dengan default value
    secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SECRET_KEY'] = secret_key
    # Fix: Gunakan path absolut untuk database
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'users.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    # Upload folder for payment proofs
    upload_folder = os.path.join(os.path.dirname(__file__), '..', 'instance', 'uploads')
    upload_folder = os.path.abspath(upload_folder)
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from .models import db
    db.init_app(app)

    with app.app_context():
        # ensure upload folder exists
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        except Exception:
            pass
        db.create_all()

    from .routes import main
    app.register_blueprint(main)
    
    # Jalankan Google Drive sync worker (optional)
    # Uncomment untuk mengaktifkan auto-sync
    # try:
    #     from .tasks import start_background_sync_worker
    #     start_background_sync_worker()
    #     logger.info("Google Drive sync worker started")
    # except Exception as e:
    #     logger.warning(f"Could not start sync worker: {str(e)}")

    return app