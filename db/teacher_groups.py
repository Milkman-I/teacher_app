import logging
from typing import List, Optional, Dict, Any
from db.connection import db_manager

logger = logging.getLogger(__name__)

def create_table():
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS groups (group_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, class_name TEXT, teacher_id INTEGER)")
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating table: {e}")

def create_group(group_name: str, class_name: str, teacher_id: int) -> Optional[int]:
    """Create a new group and return the group_id"""
    if not group_name or not class_name or not teacher_id:
        logger.error("Invalid group creation parameters")
        return None
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO groups (name, class_name, teacher_id) VALUES (?, ?, ?)", 
                (group_name.strip(), class_name.strip(), teacher_id)
            )
            conn.commit()
            group_id = cursor.lastrowid
            logger.info(f"Created group: {group_name} (ID: {group_id})")
            return group_id
    except Exception as e:
        logger.error(f"Error creating group: {e}")
        return None

def get_groups(teacher_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all groups, optionally filtered by teacher_id"""
    try:
        if teacher_id:
            results = db_manager.execute_query(
                "SELECT group_id, name, class_name, teacher_id FROM groups WHERE teacher_id = ? ORDER BY name", 
                (teacher_id,), 
                fetch_all=True
            )
        else:
            results = db_manager.execute_query(
                "SELECT group_id, name, class_name, teacher_id FROM groups ORDER BY name", 
                fetch_all=True
            )
        return results or []
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return []

def get_group_by_id(group_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific group by ID"""
    if not group_id:
        return None
    
    try:
        result = db_manager.execute_query(
            "SELECT group_id, name, class_name, teacher_id FROM groups WHERE group_id = ?", 
            (group_id,), 
            fetch_one=True
        )
        return result
    except Exception as e:
        logger.error(f"Error getting group by ID {group_id}: {e}")
        return None

def delete_group_by_id(group_id: int) -> bool:
    """Delete a group by ID and handle related records manually"""
    if not group_id:
        return False
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # First, delete related records to avoid FOREIGN KEY constraints
            # Delete attendance records
            cursor.execute("DELETE FROM attendance WHERE group_id = ?", (group_id,))
            attendance_deleted = cursor.rowcount
            
            # Delete exam records
            cursor.execute("DELETE FROM exams WHERE group_id = ?", (group_id,))
            exams_deleted = cursor.rowcount
            
            # Delete student records
            cursor.execute("DELETE FROM students WHERE group_id = ?", (group_id,))
            students_deleted = cursor.rowcount
            
            # Finally, delete the group
            cursor.execute("DELETE FROM groups WHERE group_id = ?", (group_id,))
            groups_deleted = cursor.rowcount
            
            conn.commit()
            
            if groups_deleted > 0:
                logger.info(f"Deleted group ID: {group_id} (with {students_deleted} students, {exams_deleted} exams, {attendance_deleted} attendance records)")
                return True
            else:
                logger.warning(f"No group found with ID: {group_id}")
                return False
                
    except Exception as e:
        logger.error(f"Error deleting group {group_id}: {e}")
        return False

def get_group_name(group_id: int) -> Optional[str]:
    """Get group name by ID"""
    if not group_id:
        return None
    
    try:
        result = db_manager.execute_query(
            "SELECT name FROM groups WHERE group_id = ?", 
            (group_id,), 
            fetch_one=True
        )
        return result['name'] if result else None
    except Exception as e:
        logger.error(f"Error getting group name for ID {group_id}: {e}")
        return None

def get_groups_with_student_count(teacher_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get groups with student count - optimized single query"""
    try:
        if teacher_id:
            query = """
                SELECT g.group_id, g.name, g.class_name, g.teacher_id, 
                       COUNT(s.student_id) as student_count
                FROM groups g
                LEFT JOIN students s ON g.group_id = s.group_id
                WHERE g.teacher_id = ?
                GROUP BY g.group_id, g.name, g.class_name, g.teacher_id
                ORDER BY g.name
            """
            params = (teacher_id,)
        else:
            query = """
                SELECT g.group_id, g.name, g.class_name, g.teacher_id, 
                       COUNT(s.student_id) as student_count
                FROM groups g
                LEFT JOIN students s ON g.group_id = s.group_id
                GROUP BY g.group_id, g.name, g.class_name, g.teacher_id
                ORDER BY g.name
            """
            params = ()
        
        results = db_manager.execute_query(query, params, fetch_all=True)
        return results or []
    except Exception as e:
        logger.error(f"Error getting groups with student count: {e}")
        return []

# Create table on module load
create_table()
