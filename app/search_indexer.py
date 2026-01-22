import os
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from .models import db, Document
from datetime import datetime

class DocumentIndexer:
    """Mengindeks dokumen dari folder arsip bengkel dan file JSON"""
    
    def __init__(self):
        self.arsip_base = os.path.join(
            os.path.dirname(__file__),
            'templates',
            'arsip bengkel'
        )
    
    def index_arsip_bengkel(self):
        """Scan dan index semua file HTML dari folder arsip bengkel"""
        indexed_count = 0
        
        for root, dirs, files in os.walk(self.arsip_base):
            for file in files:
                # Lewati folder url compilation
                if 'url compilation' in root:
                    continue
                
                if file.endswith('.html'):
                    filepath = os.path.join(root, file)
                    relative_path = os.path.relpath(filepath, self.arsip_base)
                    
                    try:
                        doc = self._index_html_file(filepath, relative_path)
                        if doc:
                            indexed_count += 1
                    except Exception as e:
                        print(f"Error indexing {relative_path}: {str(e)}")
        
        return indexed_count
    
    def index_json_files(self):
        """Scan dan index file JSON dari url compilation"""
        indexed_count = 0
        json_dir = os.path.join(self.arsip_base, 'url compilation')
        
        if not os.path.exists(json_dir):
            return indexed_count
        
        for file in os.listdir(json_dir):
            if file.endswith('.json'):
                filepath = os.path.join(json_dir, file)
                relative_path = os.path.relpath(filepath, self.arsip_base)
                
                try:
                    doc = self._index_json_file(filepath, relative_path)
                    if doc:
                        indexed_count += 1
                except Exception as e:
                    print(f"Error indexing {relative_path}: {str(e)}")
        
        return indexed_count
    
    def _index_html_file(self, filepath, relative_path):
        """Index file HTML individual"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            nama = title_tag.string if title_tag else os.path.basename(filepath)
            
            # Extract description or meta description
            meta_desc = soup.find('meta', {'name': 'description'})
            deskripsi = meta_desc.get('content', '')[:500] if meta_desc else ''
            
            # Get category dari path
            kategori = self._extract_category_from_path(relative_path)
            
            # Extract text content untuk search
            scripts = soup.find_all(['script', 'style'])
            for script in scripts:
                script.decompose()
            
            konten_search = soup.get_text()
            konten_search = ' '.join(konten_search.split())[:2000]
            
            # Get file size
            ukuran_kb = os.path.getsize(filepath) / 1024
            
            # Check if document already exists
            doc = Document.query.filter_by(filepath=relative_path).first()
            
            if doc:
                # Update existing document
                doc.nama = nama
                doc.kategori = kategori
                doc.deskripsi = deskripsi
                doc.konten_search = konten_search
                doc.ukuran_kb = ukuran_kb
                doc.tanggal_diupdate = datetime.utcnow()
            else:
                # Create new document
                doc = Document(
                    nama=nama,
                    kategori=kategori,
                    deskripsi=deskripsi,
                    filepath=relative_path,
                    tipe_file='html',
                    ukuran_kb=ukuran_kb,
                    is_arsip=True,
                    is_json=False,
                    konten_search=konten_search,
                    tags=kategori.lower()
                )
                db.session.add(doc)
            
            db.session.commit()
            return doc
            
        except Exception as e:
            print(f"Error processing {filepath}: {str(e)}")
            return None
    
    def _index_json_file(self, filepath, relative_path):
        """Index file JSON individual"""
        try:
            file_size = os.path.getsize(filepath) / 1024
            nama = os.path.basename(filepath)
            
            # Extract basic info dari JSON
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    json_data = json.load(f)
                
                # Extract searchable content dari JSON
                konten_search = json.dumps(json_data)[:2000]
            except:
                konten_search = ''
            
            kategori = 'URL Compilation'
            
            # Check if document already exists
            doc = Document.query.filter_by(filepath=relative_path).first()
            
            if doc:
                # Update existing document
                doc.nama = nama
                doc.kategori = kategori
                doc.konten_search = konten_search
                doc.ukuran_kb = file_size
                doc.tanggal_diupdate = datetime.utcnow()
            else:
                # Create new document
                doc = Document(
                    nama=nama,
                    kategori=kategori,
                    deskripsi=f'File JSON - {nama}',
                    filepath=relative_path,
                    tipe_file='json',
                    ukuran_kb=file_size,
                    is_arsip=True,
                    is_json=True,
                    konten_search=konten_search,
                    tags='json,url-compilation'
                )
                db.session.add(doc)
            
            db.session.commit()
            return doc
            
        except Exception as e:
            print(f"Error processing {filepath}: {str(e)}")
            return None
    
    def _extract_category_from_path(self, relative_path):
        """Ekstrak kategori dari path file"""
        parts = relative_path.split(os.sep)
        if len(parts) > 1:
            return parts[0]
        return 'Lainnya'
    
    def clear_index(self):
        """Hapus semua dokumen yang sudah diindex"""
        Document.query.delete()
        db.session.commit()
        return True


class DocumentSearcher:
    """Mencari dokumen dengan full-text search"""
    
    @staticmethod
    def search(query, kategori=None, tipe_file=None, limit=50):
        """
        Search dokumen dengan berbagai filter
        
        Args:
            query (str): Kata kunci pencarian
            kategori (str): Filter kategori (optional)
            tipe_file (str): Filter tipe file (optional)
            limit (int): Maksimal hasil
        
        Returns:
            list: Daftar dokumen yang cocok
        """
        search_query = query.lower()
        
        # Build query
        q = Document.query
        
        # Apply text search
        if search_query:
            # Search di nama, deskripsi, tags, dan konten
            q = q.filter(
                (Document.nama.ilike(f'%{search_query}%')) |
                (Document.deskripsi.ilike(f'%{search_query}%')) |
                (Document.tags.ilike(f'%{search_query}%')) |
                (Document.konten_search.ilike(f'%{search_query}%'))
            )
        
        # Apply kategori filter
        if kategori and kategori != 'Semua':
            q = q.filter_by(kategori=kategori)
        
        # Apply tipe file filter
        if tipe_file:
            q = q.filter_by(tipe_file=tipe_file)
        
        # Order by relevance dan date
        results = q.order_by(
            Document.tanggal_ditambah.desc()
        ).limit(limit).all()
        
        return results
    
    @staticmethod
    def get_all_categories():
        """Ambil semua kategori unik"""
        categories = db.session.query(Document.kategori).distinct().all()
        return [c[0] for c in categories if c[0]]
    
    @staticmethod
    def get_category_stats():
        """Ambil statistik dokumen per kategori"""
        from sqlalchemy import func
        stats = db.session.query(
            Document.kategori,
            func.count(Document.id)
        ).group_by(Document.kategori).all()
        
        return {cat: count for cat, count in stats}
    
    @staticmethod
    def suggest_keywords(partial_query, limit=10):
        """Autocomplete suggestions"""
        results = Document.query.filter(
            Document.nama.ilike(f'%{partial_query}%')
        ).limit(limit).all()
        
        return [doc.nama for doc in results]
