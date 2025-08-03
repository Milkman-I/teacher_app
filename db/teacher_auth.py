import sqlite3
import logging
from typing import Optional
from passlib.context import CryptContext
from .connection import DatabaseManager

# Create database manager instance
db_manager = DatabaseManager()

# Create password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

conn=sqlite3.connect("Teachers.db")

cur=conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS Teachers(teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE, password TEXT)")

def username_exists(_username: str) -> bool:
    """Check if a username already exists in the database"""

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    if not password:
        raise ValueError("Password cannot be empty")
    return pwd_context.hash(password)

def verify_password(plain_password: str, stored_password: str) -> bool:
    """Verify a password against its hash or plain text (with migration)"""
    if not plain_password or not stored_password:
        return False
    
    try:
        # First try to verify as bcrypt hash
        return pwd_context.verify(plain_password, stored_password)
    except Exception as e:
        # If bcrypt verification fails, check if it's a plain text password (legacy)
        if plain_password == stored_password:
            logging.info("Found plain text password, migrating to bcrypt hash")
            # TODO: Migrate this password to bcrypt hash in background
            return True
        else:
            logging.error(f"Password verification error: {e}")
            return False

def teacher_exists(username: str, password: str) -> bool:
    """Check if teacher exists and password is correct"""
    if not username or not password:
        return False
    
    try:
        result = db_manager.execute_query(
            "SELECT password FROM teachers WHERE username = ?", 
            (username,), 
            fetch_one=True
        )
        
        if result:
            stored_hash = result['password']
            return verify_password(password, stored_hash)
        return False
        
    except Exception as e:
        logging.error(f"Error checking teacher existence: {e}")
        return False

def insert_teacher(username: str, password: str) -> bool:
    """Insert a new teacher with proper validation and error handling"""
    if not username or not password:
        logging.error("Username and password are required")
        return False
    
    if len(username.strip()) < 3:
        logging.error("Username must be at least 3 characters long")
        return False
    
    if len(password) < 6:
        logging.error("Password must be at least 6 characters long")
        return False
    
    try:
        # Initialize database tables if needed
        db_manager.initialize_database()
        
        hashed_password = hash_password(password)
        
        rows_affected = db_manager.execute_query(
            "INSERT INTO teachers (username, password) VALUES (?, ?)", 
            (username.strip(), hashed_password)
        )
        
        if rows_affected > 0:
            logging.info(f"Teacher created successfully: {username}")
            return True
        else:
            logging.error(f"Failed to insert teacher: {username}")
            return False
            
    except sqlite3.IntegrityError as e:
        logging.error(f"Username already exists: {username}")
        return False
    except Exception as e:
        logging.error(f"Error inserting teacher: {e}")
        return False

def username_exists(username: str) -> bool:
    """Check if username already exists"""
    if not username:
        return False
    
    try:
        result = db_manager.execute_query(
            "SELECT 1 FROM teachers WHERE username = ?", 
            (username.strip(),), 
            fetch_one=True
        )
        return result is not None
        
    except Exception as e:
        logging.error(f"Error checking username existence: {e}")
        return False

def get_teacher_by_username(username: str) -> Optional[dict]:
    """Get teacher information by username"""
    if not username:
        return None
    
    try:
        result = db_manager.execute_query(
            "SELECT teacher_id, username, created_at FROM teachers WHERE username = ?", 
            (username.strip(),), 
            fetch_one=True
        )
        return result
        
    except Exception as e:
        logging.error(f"Error getting teacher by username: {e}")
        return None

def update_teacher_password(username: str, new_password: str) -> bool:
    """Update teacher password"""
    if not username or not new_password:
        return False
    
    if len(new_password) < 6:
        logging.error("New password must be at least 6 characters long")
        return False
    
    try:
        hashed_password = hash_password(new_password)
        
        rows_affected = db_manager.execute_query(
            "UPDATE teachers SET password = ? WHERE username = ?", 
            (hashed_password, username.strip())
        )
        
        if rows_affected > 0:
            logging.info(f"Password updated for teacher: {username}")
            return True
        else:
            logging.error(f"Teacher not found for password update: {username}")
            return False
            
    except Exception as e:
        logging.error(f"Error updating teacher password: {e}")
        return False

# Create the database and table if they do not exist
try:
    conn = sqlite3.connect('Teachers.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS teachers(teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE, password_hash TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT)")
    conn.commit()
    conn.close()
except sqlite3.Error as e:
    logging.error(f"Error creating database and table: {e}")