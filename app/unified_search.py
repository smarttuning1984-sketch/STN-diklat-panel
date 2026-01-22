"""
Unified Search Module - Mencari di Dokumen Pembelajaran dan Arsip Bengkel Teknis
Menyediakan deep search dengan full-text dan metadata matching
"""

import os
import json
import re
from .models import db, Document, Peserta
from sqlalchemy import or_, func, and_


class UnifiedSearchEngine:
    """Search engine terpadu untuk Dokumen Pembelajaran dan Arsip Bengkel"""
    
    # Kategori dokumen pembelajaran (dari Google Drive folder IDs)
    LEARNING_CATEGORIES = {
        '12ffd7GqHAiy3J62Vu65LbVt6-ultog5Z': {
            'name': 'EBOOKS',
            'icon': '📚',
            'type': 'learning'
        },
        '1Y2SLCbyHoB53BaQTTwRta2T6dv_drRll': {
            'name': 'Pengetahuan',
            'icon': '🧠',
            'type': 'learning'
        },
        '1CHz8UWZXfJtXlcjp9-FPAo-t_KkfTztW': {
            'name': 'Service Manual 1',
            'icon': '🔧',
            'type': 'learning'
        },
        '1_SsZ7SkaZxvXUZ6RUAA_o7WR_GAtgEwT': {
            'name': 'Service Manual 2',
            'icon': '⚙️',
            'type': 'learning'
        }
    }
    
    @staticmethod
    def deep_search(query, search_type='all', limit=50, offset=0):
        """
        Pencarian mendalam di semua dokumen
        
        Args:
            query (str): Kata kunci pencarian
            search_type (str): 'all', 'arsip', atau 'learning'
            limit (int): Jumlah hasil
            offset (int): Offset untuk pagination
        
        Returns:
            dict: {
                'total': jumlah total hasil,
                'results': [list dokumen],
                'facets': {kategorisasi hasil}
            }
        """
        if not query or len(query.strip()) < 2:
            return {
                'total': 0,
                'results': [],
                'facets': {}
            }
        
        search_query = query.lower().strip()
        
        # Base query - search di Document model
        q = Document.query
        
        # Apply full-text search dengan weighted scoring
        search_filter = or_(
            Document.nama.ilike(f'%{search_query}%'),
            Document.deskripsi.ilike(f'%{search_query}%'),
            Document.tags.ilike(f'%{search_query}%'),
            Document.konten_search.ilike(f'%{search_query}%'),
            Document.kategori.ilike(f'%{search_query}%')
        )
        
        q = q.filter(search_filter)
        
        # Filter by type
        if search_type == 'arsip':
            q = q.filter(Document.is_arsip == True)
        elif search_type == 'learning':
            q = q.filter(Document.is_arsip == False)
        
        # Count total
        total = q.count()
        
        # Get results dengan ordering
        results = q.order_by(
            # Prioritas: nama match > kategori > tanggal
            Document.nama.ilike(f'{search_query}%').desc(),
            Document.tanggal_ditambah.desc()
        ).offset(offset).limit(limit).all()
        
        # Build facets (kategori count)
        facets = UnifiedSearchEngine._build_facets(q)
        
        # Format results
        formatted_results = [
            UnifiedSearchEngine._format_document(doc)
            for doc in results
        ]
        
        return {
            'total': total,
            'results': formatted_results,
            'facets': facets,
            'query': query,
            'type': search_type
        }
    
    @staticmethod
    def deep_search_by_category(category, limit=50, offset=0):
        """
        Search dokumen berdasarkan kategori spesifik
        
        Args:
            category (str): Nama kategori
            limit (int): Jumlah hasil
            offset (int): Offset untuk pagination
        
        Returns:
            dict: Hasil search dengan format standar
        """
        q = Document.query.filter_by(kategori=category)
        
        total = q.count()
        
        results = q.order_by(
            Document.tanggal_ditambah.desc()
        ).offset(offset).limit(limit).all()
        
        formatted_results = [
            UnifiedSearchEngine._format_document(doc)
            for doc in results
        ]
        
        return {
            'total': total,
            'results': formatted_results,
            'category': category
        }
    
    @staticmethod
    def get_search_suggestions(partial_query, limit=15):
        """
        Get autocomplete suggestions dari semua dokumen
        
        Args:
            partial_query (str): Partial search query
            limit (int): Jumlah suggestions
        
        Returns:
            list: List suggestions
        """
        if len(partial_query) < 2:
            return []
        
        suggestions = set()
        
        # Dari nama dokumen
        results = Document.query.filter(
            Document.nama.ilike(f'{partial_query}%')
        ).limit(limit).all()
        
        for doc in results:
            suggestions.add(doc.nama)
        
        # Dari kategori
        categories = db.session.query(Document.kategori).distinct().filter(
            Document.kategori.ilike(f'%{partial_query}%')
        ).limit(5).all()
        
        for cat in categories:
            if cat[0]:
                suggestions.add(cat[0])
        
        # Dari tags
        tag_results = db.session.query(Document.tags).distinct().filter(
            Document.tags.ilike(f'%{partial_query}%')
        ).limit(5).all()
        
        for tag in tag_results:
            if tag[0]:
                for t in tag[0].split(','):
                    if t.strip().startswith(partial_query.lower()):
                        suggestions.add(t.strip())
        
        return sorted(list(suggestions))[:limit]
    
    @staticmethod
    def get_all_categories():
        """Get semua kategori dari kedua jenis dokumen"""
        db_categories = db.session.query(
            Document.kategori
        ).distinct().all()
        
        return sorted([c[0] for c in db_categories if c[0]])
    
    @staticmethod
    def get_statistics():
        """Get statistik pencarian mendalam"""
        total_docs = Document.query.count()
        
        # By type
        arsip_count = Document.query.filter_by(is_arsip=True).count()
        learning_count = Document.query.filter_by(is_arsip=False).count()
        
        # By file type
        file_type_stats = db.session.query(
            Document.tipe_file,
            func.count(Document.id)
        ).group_by(Document.tipe_file).all()
        
        # By category
        category_stats = db.session.query(
            Document.kategori,
            func.count(Document.id)
        ).group_by(Document.kategori).all()
        
        return {
            'total_documents': total_docs,
            'arsip_documents': arsip_count,
            'learning_documents': learning_count,
            'by_file_type': {ft: count for ft, count in file_type_stats},
            'by_category': {cat: count for cat, count in category_stats}
        }
    
    @staticmethod
    def search_with_filters(query, filters):
        """
        Advanced search dengan multiple filters
        
        Args:
            query (str): Search query
            filters (dict): {
                'kategori': str or list,
                'tipe_file': str or list,
                'is_arsip': bool,
                'date_from': datetime,
                'date_to': datetime
            }
        
        Returns:
            list: Filtered search results
        """
        q = Document.query
        
        # Text search
        if query:
            search_filter = or_(
                Document.nama.ilike(f'%{query}%'),
                Document.deskripsi.ilike(f'%{query}%'),
                Document.tags.ilike(f'%{query}%'),
                Document.konten_search.ilike(f'%{query}%')
            )
            q = q.filter(search_filter)
        
        # Category filter
        if 'kategori' in filters and filters['kategori']:
            if isinstance(filters['kategori'], list):
                q = q.filter(Document.kategori.in_(filters['kategori']))
            else:
                q = q.filter_by(kategori=filters['kategori'])
        
        # File type filter
        if 'tipe_file' in filters and filters['tipe_file']:
            if isinstance(filters['tipe_file'], list):
                q = q.filter(Document.tipe_file.in_(filters['tipe_file']))
            else:
                q = q.filter_by(tipe_file=filters['tipe_file'])
        
        # Arsip/Learning filter
        if 'is_arsip' in filters:
            q = q.filter_by(is_arsip=filters['is_arsip'])
        
        # Date filters
        if 'date_from' in filters and filters['date_from']:
            q = q.filter(Document.tanggal_ditambah >= filters['date_from'])
        
        if 'date_to' in filters and filters['date_to']:
            q = q.filter(Document.tanggal_ditambah <= filters['date_to'])
        
        results = q.order_by(
            Document.tanggal_ditambah.desc()
        ).all()
        
        return [UnifiedSearchEngine._format_document(doc) for doc in results]
    
    @staticmethod
    def _format_document(doc):
        """Format dokumen untuk API response"""
        return {
            'id': doc.id,
            'nama': doc.nama,
            'kategori': doc.kategori,
            'deskripsi': doc.deskripsi,
            'filepath': doc.filepath,
            'tipe_file': doc.tipe_file,
            'ukuran_kb': doc.ukuran_kb,
            'is_arsip': doc.is_arsip,
            'is_json': doc.is_json,
            'tags': doc.tags.split(',') if doc.tags else [],
            'tanggal_ditambah': doc.tanggal_ditambah.isoformat() if doc.tanggal_ditambah else None,
            'type': 'Arsip Bengkel' if doc.is_arsip else 'Dokumen Pembelajaran'
        }
    
    @staticmethod
    def _build_facets(query):
        """Build facets untuk hasil search"""
        # Get kategori dari query results
        kategori_stats = db.session.query(
            Document.kategori,
            func.count(Document.id)
        ).filter(
            Document.query.whereclause
        ).group_by(Document.kategori).all()
        
        return {
            'kategori': {cat: count for cat, count in kategori_stats if cat}
        }


class DeepIndexer:
    """
    Indexer mendalam untuk dokumen pembelajaran dari berbagai sumber
    Dapat dikembangkan untuk mengindex dari Google Drive, database, dll
    """
    
    @staticmethod
    def index_learning_documents_metadata():
        """
        Index metadata dokumen pembelajaran
        Ini adalah placeholder - dalam implementasi real bisa dari Google Drive API
        """
        # Kategori pembelajaran dari DOKUMEN_CATEGORIES di routes.py
        learning_categories = {
            'EBOOKS': {
                'icon': '📚',
                'description': 'Koleksi ebook berkualitas tinggi'
            },
            'Pengetahuan': {
                'icon': '🧠',
                'description': 'Materi pengetahuan dan referensi'
            },
            'Service Manual 1': {
                'icon': '🔧',
                'description': 'Panduan servis kendaraan modern'
            },
            'Service Manual 2': {
                'icon': '⚙️',
                'description': 'Panduan servis komponen dan sistem'
            }
        }
        
        # Pastikan kategori ada di database dengan is_arsip=False
        for cat_name, cat_info in learning_categories.items():
            # Check if metadata dokumen sudah ada
            existing = Document.query.filter_by(
                nama=cat_name,
                is_arsip=False
            ).first()
            
            if not existing:
                doc = Document(
                    nama=cat_name,
                    kategori='Learning Categories',
                    deskripsi=cat_info.get('description', ''),
                    filepath=f'learning:{cat_name}',
                    tipe_file='folder',
                    is_arsip=False,
                    is_json=False,
                    tags=cat_name.lower(),
                    konten_search=cat_name + ' ' + cat_info.get('description', '')
                )
                db.session.add(doc)
        
        db.session.commit()
        return len(learning_categories)
