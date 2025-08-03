import sqlite3
import qrcode
import os
import logging
from typing import List, Optional, Dict, Any
from db.connection import db_manager
from config import config

logger = logging.getLogger(__name__)

# Ensure the qrcodes directory exists
os.makedirs('qrcodes', exist_ok=True)

def create_student_table():
    conn = sqlite3.connect("Teachers.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            group_id INTEGER,
            attendance_count INTEGER DEFAULT 0,
            FOREIGN KEY(group_id) REFERENCES groups(group_id)
        )
    """)
    conn.commit()
    conn.close()

def add_student(name: str, group_id: int) -> Optional[int]:
    """Add a new student and return the student_id"""
    if not name or not group_id:
        logger.error("Invalid student creation parameters")
        return None
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO students (name, group_id) VALUES (?, ?)", 
                (name.strip(), group_id)
            )
            conn.commit()
            student_id = cursor.lastrowid
            logger.info(f"Created student: {name} (ID: {student_id})")
            return student_id
    except Exception as e:
        logger.error(f"Error creating student: {e}")
        return None

def get_students_in_group(group_id: int) -> List[Dict[str, Any]]:
    """Get all students in a specific group"""
    if not group_id:
        return []
    
    try:
        results = db_manager.execute_query(
            "SELECT student_id, name, group_id, attendance_count FROM students WHERE group_id = ? ORDER BY name", 
            (group_id,), 
            fetch_all=True
        )
        return results or []
    except Exception as e:
        logger.error(f"Error getting students in group {group_id}: {e}")
        return []

def remove_student(student_id: int) -> bool:
    """Remove a student by ID"""
    if not student_id:
        return False
    
    try:
        rows_affected = db_manager.execute_query(
            "DELETE FROM students WHERE student_id = ?", 
            (student_id,)
        )
        success = rows_affected > 0
        if success:
            logger.info(f"Removed student ID: {student_id}")
        else:
            logger.warning(f"No student found with ID: {student_id}")
        return success
    except Exception as e:
        logger.error(f"Error removing student {student_id}: {e}")
        return False

def get_leaderboard(limit: int = 100) -> List[Dict[str, Any]]:
    """Return top students ordered by attendance_count desc with group info"""
    try:
        # Optimized query with JOIN to avoid N+1 problem
        query = """
            SELECT s.student_id, s.name, s.group_id, s.attendance_count,
                   g.name as group_name, g.class_name
            FROM students s
            LEFT JOIN groups g ON s.group_id = g.group_id
            ORDER BY s.attendance_count DESC, s.name ASC
            LIMIT ?
        """
        results = db_manager.execute_query(query, (limit,), fetch_all=True)
        return results or []
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []

def generate_student_qr(student_id):
    import os
    from PIL import Image
    
    # Ensure the qrcodes directory exists
    qr_dir = "qrcodes"
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)
        print(f"Created QR codes directory: {qr_dir}")
    
    qr_path = f"{qr_dir}/student_{student_id}.png"
    
    try:
        # Create QR code with specific settings for better compatibility
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(student_id))
        qr.make(fit=True)
        
        # Create image with white background
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure it's in RGB mode for PNG compatibility
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save the image
        img.save(qr_path, "PNG", optimize=True)
        
        # Verify the file was created and has content
        if os.path.exists(qr_path):
            file_size = os.path.getsize(qr_path)
            if file_size > 0:
                print(f"QR code saved successfully: {qr_path} ({file_size} bytes)")
                return qr_path
            else:
                print(f"QR code file is empty: {qr_path}")
                return None
        else:
            print(f"QR code file was not created: {qr_path}")
            return None
            
    except Exception as e:
        print(f"Error generating QR code for student {student_id}: {e}")
        # Clean up any partially created file
        if os.path.exists(qr_path):
            try:
                os.remove(qr_path)
            except:
                pass
        return None

create_student_table()