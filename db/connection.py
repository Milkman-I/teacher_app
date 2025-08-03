# Database connection management for Teacher App
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator
import os
import logging

from config import config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Thread-safe database connection manager with connection pooling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = config.get_database_url()
            self.initialized = True
            self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the database file and directory exist"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created database directory: {db_dir}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic cleanup"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            conn.execute("PRAGMA journal_mode = WAL")  # Enable WAL mode for better concurrency
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error in database operation: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        """Execute a query with automatic connection management"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.rowcount
    
    def execute_many(self, query: str, params_list: list):
        """Execute multiple queries with the same statement"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def initialize_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create teachers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teachers (
                    teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create groups table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    teacher_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (teacher_name) REFERENCES teachers (username)
                )
            ''')
            
            # Create students table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    attendance_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups (group_id) ON DELETE CASCADE
                )
            ''')
            
            # Create exams table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS exams (
                    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date TEXT NOT NULL,
                    group_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups (group_id) ON DELETE CASCADE
                )
            ''')
            
            # Create attendance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    present BOOLEAN DEFAULT TRUE,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
                    FOREIGN KEY (group_id) REFERENCES groups (group_id) ON DELETE CASCADE,
                    UNIQUE(student_id, group_id, date)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_group_id ON students (group_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_exams_group_id ON exams (group_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance (student_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_group_id ON attendance (group_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance (date)')
            
            conn.commit()
            logger.info("Database tables initialized successfully")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
@contextmanager
def get_db_connection():
    """Get a database connection (backward compatibility)"""
    with db_manager.get_connection() as conn:
        yield conn

def init_database():
    """Initialize the database"""
    db_manager.initialize_database()
