"""
Google Drive Auto-Sync Worker
Sinkronisasi file dari Google Drive secara otomatis
"""

import os
import time
import logging
import threading
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.models import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Folder ID mapping dari RECOMMENDATIONS.md
FOLDER_IDS = {
    "EBOOKS": "12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z",
    "Pengetahuan": "1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll",
    "Service Manual 1": "1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW",
    "Service Manual 2": "1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT"
}

# Cache untuk tracking file yang sudah disinkronisasi
FILE_SYNC_CACHE = {}

def get_drive_service():
    """Inisialisasi Google Drive service dengan credentials"""
    try:
        # Cari credentials.json
        creds_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'credentials.json'
        )
        
        if not os.path.exists(creds_path):
            logger.warning(f"credentials.json not found at {creds_path}")
            return None
        
        creds = service_account.Credentials.from_service_account_file(
            creds_path, 
            scopes=SCOPES
        )
        
        return build('drive', 'v3', credentials=creds)
    
    except Exception as e:
        logger.error(f"Failed to initialize Drive service: {str(e)}")
        return None

def sync_google_drive_files():
    """
    Sinkronisasi file dari Google Drive ke database
    Jalankan setiap 5 menit
    """
    try:
        drive_service = get_drive_service()
        
        if not drive_service:
            logger.warning("Google Drive service not available - skipping sync")
            return
        
        logger.info("Starting Google Drive sync...")
        
        sync_count = 0
        delete_count = 0
        
        for category, folder_id in FOLDER_IDS.items():
            try:
                # Query semua file di folder
                query = f"'{folder_id}' in parents and trashed=false"
                results = drive_service.files().list(
                    q=query,
                    spaces='drive',
                    fields='files(id, name, mimeType, modifiedTime, webViewLink)',
                    pageSize=100
                ).execute()
                
                files = results.get('files', [])
                logger.info(f"Found {len(files)} files in {category}")
                
                # Process setiap file
                for file in files:
                    file_id = file['id']
                    file_name = file['name']
                    file_mime = file['mimeType']
                    modified_time = file['modifiedTime']
                    
                    # Cek apakah file sudah di-cache
                    cache_key = f"{category}:{file_id}"
                    
                    if cache_key not in FILE_SYNC_CACHE:
                        # File baru
                        FILE_SYNC_CACHE[cache_key] = {
                            'name': file_name,
                            'last_modified': modified_time,
                            'sync_time': datetime.utcnow().isoformat()
                        }
                        
                        logger.info(f"[NEW] {category}: {file_name}")
                        sync_count += 1
                        
                        # TODO: Simpan ke database jika perlu
                        # save_file_to_db(file, category)
                    
                    else:
                        # File sudah ada, cek apakah ada update
                        cached = FILE_SYNC_CACHE[cache_key]
                        if cached['last_modified'] != modified_time:
                            logger.info(f"[UPDATED] {category}: {file_name}")
                            cached['last_modified'] = modified_time
                            cached['sync_time'] = datetime.utcnow().isoformat()
                            # TODO: Update di database
                
                # Cek file yang sudah dihapus
                removed_files = [
                    key for key in FILE_SYNC_CACHE.keys()
                    if key.startswith(f"{category}:")
                    and key not in [f"{category}:{f['id']}" for f in files]
                ]
                
                for removed_key in removed_files:
                    file_name = FILE_SYNC_CACHE[removed_key]['name']
                    del FILE_SYNC_CACHE[removed_key]
                    logger.info(f"[DELETED] {category}: {file_name}")
                    delete_count += 1
                    # TODO: Hapus dari database
            
            except Exception as e:
                logger.error(f"Error syncing {category}: {str(e)}")
                continue
        
        logger.info(
            f"Sync completed - Added: {sync_count}, "
            f"Deleted: {delete_count}, "
            f"Total cached: {len(FILE_SYNC_CACHE)}"
        )
    
    except Exception as e:
        logger.error(f"Google Drive sync failed: {str(e)}")

def start_background_sync_worker():
    """
    Jalankan sync worker di background thread
    Sinkronisasi setiap 5 menit
    """
    def worker():
        logger.info("Background sync worker started")
        
        while True:
            try:
                sync_google_drive_files()
            except Exception as e:
                logger.error(f"Error in sync worker: {str(e)}")
            
            # Sleep 5 menit
            time.sleep(300)
    
    # Jalankan sebagai daemon thread
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    logger.info("Background sync worker thread started")

def get_sync_status():
    """
    Get status sinkronisasi untuk monitoring
    """
    return {
        'status': 'healthy',
        'cached_files': len(FILE_SYNC_CACHE),
        'cache_details': FILE_SYNC_CACHE,
        'last_check': datetime.utcnow().isoformat()
    }

# ========== UNTUK PRODUCTION: SCHEDULED TASK ==========
# 
# Gunakan di PythonAnywhere Tasks atau Celery
# 
# from app import create_app
# from app.tasks import sync_google_drive_files
# 
# if __name__ == '__main__':
#     app = create_app()
#     with app.app_context():
#         sync_google_drive_files()
#
# ====================================================
