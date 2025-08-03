import sqlite3
import logging
from typing import List, Optional, Dict, Any
from db.connection import db_manager

logger = logging.getLogger(__name__)

def create_attendance_table():
    """Create attendance table with proper constraints"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table exists and get its structure
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'")
            existing_table = cursor.fetchone()
            
            if not existing_table:
                # Create new table with proper constraints
                cursor.execute("""
                    CREATE TABLE attendance (
                        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER NOT NULL,
                        group_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        present INTEGER DEFAULT 1,
                        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                        FOREIGN KEY(group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
                        UNIQUE(student_id, date)
                    )
                """)
                logger.info("Created new attendance table with CASCADE constraints")
            else:
                # Table exists, just ensure it has basic structure
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendance (
                        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        group_id INTEGER,
                        date TEXT,
                        present INTEGER DEFAULT 1,
                        FOREIGN KEY(student_id) REFERENCES students(student_id),
                        FOREIGN KEY(group_id) REFERENCES groups(group_id)
                    )
                """)
                logger.info("Using existing attendance table structure")
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student_date ON attendance (student_id, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_group_date ON attendance (group_id, date)')
            
            conn.commit()
            logger.info("Attendance table setup completed")
    except Exception as e:
        logger.error(f"Error setting up attendance table: {e}")

def record_attendance(student_id: int, group_id: int, date: str, present: bool = True) -> bool:
    """Record attendance for a student, preventing duplicates for the same day"""
    if not all([student_id, group_id, date]):
        logger.error("Invalid attendance parameters")
        return False
    
    try:
        # Check if attendance already exists for this student on this date
        existing = db_manager.execute_query(
            "SELECT attendance_id FROM attendance WHERE student_id = ? AND date = ?",
            (student_id, date),
            fetch_one=True
        )
        
        if existing:
            logger.warning(f"Attendance already recorded for student {student_id} on {date}")
            return False
        
        # Insert new attendance record
        rows_affected = db_manager.execute_query(
            "INSERT INTO attendance (student_id, group_id, date, present) VALUES (?, ?, ?, ?)",
            (student_id, group_id, date, 1 if present else 0)
        )
        
        if rows_affected > 0:
            # Update student's attendance count if present
            if present:
                db_manager.execute_query(
                    "UPDATE students SET attendance_count = attendance_count + 1 WHERE student_id = ?",
                    (student_id,)
                )
            
            logger.info(f"Attendance recorded for student {student_id}: {'Present' if present else 'Absent'}")
            return True
        else:
            logger.error(f"Failed to record attendance for student {student_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error recording attendance: {e}")
        return False

def get_attendance_for_group(group_id: int) -> List[Dict[str, Any]]:
    """Get all attendance records for a group"""
    if not group_id:
        return []
    
    try:
        results = db_manager.execute_query(
            "SELECT attendance_id, student_id, group_id, date, present FROM attendance WHERE group_id = ? ORDER BY date DESC, student_id",
            (group_id,),
            fetch_all=True
        )
        return results or []
    except Exception as e:
        logger.error(f"Error getting attendance for group {group_id}: {e}")
        return []

def get_attendance_for_student(student_id: int) -> List[Dict[str, Any]]:
    """Get all attendance records for a student"""
    if not student_id:
        return []
    
    try:
        results = db_manager.execute_query(
            "SELECT attendance_id, student_id, group_id, date, present FROM attendance WHERE student_id = ? ORDER BY date DESC",
            (student_id,),
            fetch_all=True
        )
        return results or []
    except Exception as e:
        logger.error(f"Error getting attendance for student {student_id}: {e}")
        return []

def get_attendance_summary(group_id: int, date: str = None) -> Dict[str, Any]:
    """Get attendance summary for a group on a specific date or overall"""
    if not group_id:
        return {}
    
    try:
        if date:
            # Get attendance for specific date
            query = """
                SELECT 
                    COUNT(*) as total_records,
                    SUM(present) as present_count,
                    COUNT(*) - SUM(present) as absent_count
                FROM attendance 
                WHERE group_id = ? AND date = ?
            """
            params = (group_id, date)
        else:
            # Get overall attendance summary
            query = """
                SELECT 
                    COUNT(*) as total_records,
                    SUM(present) as present_count,
                    COUNT(*) - SUM(present) as absent_count,
                    COUNT(DISTINCT date) as total_days,
                    COUNT(DISTINCT student_id) as total_students
                FROM attendance 
                WHERE group_id = ?
            """
            params = (group_id,)
        
        result = db_manager.execute_query(query, params, fetch_one=True)
        return result or {}
        
    except Exception as e:
        logger.error(f"Error getting attendance summary for group {group_id}: {e}")
        return {}

def mark_absent_students(group_id: int, date: str, absent_student_ids: List[int]) -> bool:
    """Mark specific students as absent for a given date"""
    if not all([group_id, date, absent_student_ids]):
        return False
    
    try:
        success_count = 0
        for student_id in absent_student_ids:
            if record_attendance(student_id, group_id, date, present=False):
                success_count += 1
        
        logger.info(f"Marked {success_count}/{len(absent_student_ids)} students as absent")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error marking students absent: {e}")
        return False

# Create table on module load
create_attendance_table()