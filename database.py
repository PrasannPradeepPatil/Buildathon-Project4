import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_path='analysis.db'):
        self.db_path = db_path
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_url TEXT NOT NULL,
                analysis_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_analysis(self, repo_url, analysis_data):
        """Store analysis results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO analyses (repo_url, analysis_data) VALUES (?, ?)',
            (repo_url, json.dumps(analysis_data))
        )
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return analysis_id
    
    def get_analysis(self, analysis_id):
        """Retrieve analysis by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM analyses WHERE id = ?',
            (analysis_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'repo_url': result[1],
                'analysis_data': json.loads(result[2]),
                'created_at': result[3]
            }
        
        return None