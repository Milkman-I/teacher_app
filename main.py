from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import jwt  # PyJWT library
import os
import logging

# Import configuration
from config import config

from data_validation.teacher import Teacher
from auth.JWT import create_access_token, get_current_teacher, get_current_teacher_optional
from db.teacher_auth import teacher_exists, insert_teacher, username_exists
from db.teacher_groups import *
from db.student import add_student, get_students_in_group, remove_student, generate_student_qr, get_leaderboard
from db.exam import create_exam, get_exams_for_group, get_exam_by_id, delete_exam
from db.attendance import record_attendance, get_attendance_for_group, get_attendance_for_student, get_attendance_summary, mark_absent_students
from utils.file_manager import file_manager, create_safe_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logging.info(f"Starting Teacher App API on {config.HOST}:{config.PORT}")
    logging.info(f"Debug mode: {config.DEBUG}")
    logging.info(f"CORS origins: {config.CORS_ORIGINS}")
    yield
    # Shutdown
    logging.info("Shutting down Teacher App API")

# Request models
class StudentRequest(BaseModel):
    name: str

class GroupRequest(BaseModel):
    group_name: str
    class_name: str

class ExamRequest(BaseModel):
    title: str
    date: str

# Validate configuration on startup
config.validate_config()

# Create FastAPI app
app = FastAPI(
    title="Teacher App API",
    description="Backend API for Teacher Management Application",
    version="1.0.0",
    lifespan=lifespan,
    debug=config.DEBUG
)

# Configure CORS with secure settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # Use configured origins instead of "*"
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods instead of "*"
    allow_headers=[
        "Authorization", 
        "Content-Type", 
        "Accept", 
        "Origin", 
        "User-Agent", 
        "DNT", 
        "Cache-Control", 
        "X-Mx-ReqToken", 
        "Keep-Alive", 
        "X-Requested-With", 
        "If-Modified-Since"
    ],
    expose_headers=["Content-Disposition"]
)



@app.post('/auth/register')
async def register(teacher: Teacher):
    """Register a new teacher account"""
    try:
        username = teacher.username.strip()
        password = teacher.password
        
        # Input validation
        if not username or len(username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
        
        if not password or len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
        # Check if username already exists
        if username_exists(username):
            raise HTTPException(status_code=409, detail="Username already exists")
        
        # Create the teacher account
        success = insert_teacher(username, password)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create user account")
        
        # Generate secure token
        token = create_access_token(username)
        
        logging.info(f"New teacher registered: {username}")
        return {
            "token": token, 
            "teacher": {"username": username},
            "message": "Account created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")

@app.post('/auth/login')
async def login(teacher: Teacher):
    """Authenticate teacher login"""
    try:
        username = teacher.username.strip()
        password = teacher.password
        
        # Input validation
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")
        
        # Verify credentials
        if teacher_exists(username, password):
            # Generate secure token
            token = create_access_token(username)
            
            logging.info(f"Teacher logged in: {username}")
            return {
                "token": token, 
                "teacher": {"username": username},
                "message": "Login successful"
            }
        else:
            logging.warning(f"Failed login attempt for username: {username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during login")
    
@app.get('/groups')
async def list_groups_endpoint(current_teacher: str = Depends(get_current_teacher)):
    groups = get_groups_with_student_count(current_teacher)
    return [{"group_id": g.get("group_id"), "name": g.get("name"), "class_name": g.get("class_name"), "student_count": g.get("student_count", 0)} for g in groups]

@app.post('/groups')
@app.post('/groups/create')
async def create_group_endpoint(group: GroupRequest, current_teacher: str = Depends(get_current_teacher)):
    # Use the JSON body directly - no need for complex fallback logic
    group_name = group.group_name
    class_name = group.class_name
    
    # Create the group
    create_group(group_name, class_name, current_teacher)
    return {"success": True, "group": {"name": group_name, "class_name": class_name, "teacher_name": current_teacher}}

# Delete group
@app.delete('/groups/{group_id}')
async def delete_group_endpoint(group_id: int, current_teacher: str = Depends(get_current_teacher)):
    success = delete_group_by_id(group_id)
    if success:
        return {"success": True, "group_id": group_id}
    else:
        raise HTTPException(status_code=404, detail="Group not found or could not be deleted")

# Add student to group
@app.post('/groups/{group_id}/students')
async def add_student_endpoint(group_id: int, student: StudentRequest, current_teacher: str = Depends(get_current_teacher)):
    add_student(student.name, group_id)
    return {"success": True, "student": {"name": student.name, "group_id": group_id}}

# List students in group
@app.get('/groups/{group_id}/students')
async def list_students_endpoint(group_id: int):
    students = get_students_in_group(group_id)
    return [{"student_id": s.get("student_id"), "name": s.get("name"), "group_id": s.get("group_id"), "attendance_count": s.get("attendance_count", 0)} for s in students]

# Remove student from group
@app.delete('/groups/{group_id}/students/{student_id}')
async def remove_student_endpoint(group_id: int, student_id: int):
    remove_student(student_id)
    return {"success": True, "student_id": student_id}

# Delete student (alternative endpoint)
@app.delete('/students/{student_id}')
async def delete_student_endpoint(student_id: int):
    remove_student(student_id)
    return {"success": True, "student_id": student_id}


# Create exam for a group
@app.post('/groups/{group_id}/exams')
async def create_exam_endpoint(group_id: int, exam: ExamRequest, current_teacher: str = Depends(get_current_teacher)):
    exam_id = create_exam(exam.title, exam.date, group_id, current_teacher)
    return {"success": True, "exam_id": exam_id, "title": exam.title, "date": exam.date, "group_id": group_id}

# List exams for a group
@app.get('/groups/{group_id}/exams')
async def list_exams_endpoint(group_id: int):
    exams = get_exams_for_group(group_id)
    return [{"exam_id": e.get("exam_id"), "title": e.get("title"), "date": e.get("date"), "group_id": e.get("group_id")} for e in exams]

# Get exam details
@app.get('/exams/{exam_id}')
async def get_exam_details_endpoint(exam_id: int):
    exam = get_exam_by_id(exam_id)
    if exam:
        return {"exam_id": exam.get("exam_id"), "title": exam.get("title"), "date": exam.get("date"), "group_id": exam.get("group_id")}
    else:
        return {"error": "Exam not found"}

# Delete exam
@app.delete('/exams/{exam_id}')
async def delete_exam_endpoint(exam_id: int):
    delete_exam(exam_id)
    return {"success": True, "exam_id": exam_id}

@app.post('/attendance/scan')
async def scan_attendance(request: dict, current_teacher: str = Depends(get_current_teacher)):
    student_id = request.get('student_id')
    group_id = request.get('group_id') 
    date = request.get('date')
    present = request.get('present', True)  # Default to present
    
    if not all([student_id, group_id, date]):
        raise HTTPException(status_code=400, detail="Missing required fields: student_id, group_id, date")
    
    try:
        success = record_attendance(student_id, group_id, date, present)
        if success:
            return {"success": True, "message": "Attendance recorded successfully"}
        else:
            return {"success": False, "message": "Attendance already recorded for this student today"}
    except Exception as e:
        logging.error(f"Error recording attendance: {e}")
        raise HTTPException(status_code=500, detail="Failed to record attendance")

@app.get('/groups/{group_id}/attendance')
async def group_attendance_endpoint(group_id: int):
    records = get_attendance_for_group(group_id)
    return [{"attendance_id": r.get("attendance_id"), "student_id": r.get("student_id"), "group_id": r.get("group_id"), "date": r.get("date"), "present": r.get("present", False)} for r in records]

@app.get('/students/{student_id}/attendance')
async def student_attendance_endpoint(student_id: int):
    records = get_attendance_for_student(student_id)
    return [{"attendance_id": r.get("attendance_id"), "student_id": r.get("student_id"), "group_id": r.get("group_id"), "date": r.get("date"), "present": r.get("present", False)} for r in records]

# Get attendance summary for a group
@app.get('/groups/{group_id}/attendance/summary')
async def group_attendance_summary_endpoint(group_id: int, date: str = None):
    summary = get_attendance_summary(group_id, date)
    return summary

# Mark students as absent
@app.post('/groups/{group_id}/attendance/absent')
async def mark_absent_endpoint(group_id: int, request: dict, current_teacher: str = Depends(get_current_teacher)):
    date = request.get('date')
    absent_student_ids = request.get('absent_student_ids', [])
    
    if not date or not absent_student_ids:
        raise HTTPException(status_code=400, detail="Missing required fields: date, absent_student_ids")
    
    try:
        success = mark_absent_students(group_id, date, absent_student_ids)
        if success:
            return {"success": True, "message": f"Marked {len(absent_student_ids)} students as absent"}
        else:
            return {"success": False, "message": "Failed to mark students as absent"}
    except Exception as e:
        logging.error(f"Error marking students absent: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark students as absent")

@app.get('/students/{student_id}/qr')
async def get_student_qr_endpoint(request: Request, student_id: int, current_teacher: str = Depends(get_current_teacher_optional)):
    import os
    
    # Generate QR code for the student
    qr_path = generate_student_qr(student_id)
    
    if not qr_path or not os.path.exists(qr_path):
        raise HTTPException(status_code=404, detail="QR code not found or failed to generate")
    
    # Return the PNG file directly
    return FileResponse(
        qr_path, 
        media_type="image/png",
        filename=f"student_{student_id}_QR.png",
        headers={"Content-Disposition": f"attachment; filename=student_{student_id}_QR.png"}
    )

# Leaderboard endpoint
@app.get('/leaderboard')
async def leaderboard_endpoint(limit: int = 100):
    students = get_leaderboard(limit)
    return [{
        "student_id": s.get("student_id"),
        "name": s.get("name"),
        "group_id": s.get("group_id"),
        "attendance_count": s.get("attendance_count", 0),
        "group_name": s.get("group_name"),
        "class_name": s.get("class_name")
    } for s in students]

# Serve QR code images (with authentication)
@app.get('/qrcodes/{filename}')
async def serve_qr_image(request: Request, filename: str, current_teacher: str = Depends(get_current_teacher_optional)):
    import os
    qr_path = f"qrcodes/{filename}"
    
    if not os.path.exists(qr_path):
        raise HTTPException(status_code=404, detail="QR code file not found")
    
    return FileResponse(qr_path, media_type="image/png")

@app.get('/groups/{group_id}/qrcodes')
async def get_group_qrcodes_endpoint(request: Request, group_id: int, current_teacher: str = Depends(get_current_teacher_optional)):
    import zipfile
    import os
    import time
    
    # Get all students in the group
    students = get_students_in_group(group_id)
    
    if not students:
        raise HTTPException(status_code=404, detail="No students found in this group")
    
    logging.info(f"Found {len(students)} students in group {group_id}")
    
    # Validate group size for performance
    if len(students) > config.MAX_STUDENTS_PER_GROUP:
        raise HTTPException(status_code=400, detail=f"Group too large. Maximum {config.MAX_STUDENTS_PER_GROUP} students allowed for bulk download")
    
    # Ensure qrcodes directory exists
    qr_dir = config.QR_CODES_DIR
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)
        logging.info(f"Created directory: {qr_dir}")
    
    # Generate QR codes for all students and collect valid paths
    valid_qr_files = []
    for student in students:
        student_id = student.get("student_id")  # student_id from dictionary
        student_name = student.get("name")  # student_name from dictionary
        
        logging.debug(f"Generating QR for student: {student_name} (ID: {student_id})")
        
        # Generate QR code
        qr_path = generate_student_qr(student_id)
        
        if qr_path and os.path.exists(qr_path):
            # Verify the file is readable and has content
            file_size = os.path.getsize(qr_path)
            if file_size > 0:
                # Create safe filename for ZIP
                safe_filename = create_safe_filename(f"{student_name}_QR.png")
                valid_qr_files.append((qr_path, safe_filename))
                logging.debug(f"QR generated successfully: {qr_path} ({file_size} bytes)")
            else:
                logging.warning(f"QR file is empty: {qr_path}")
        else:
            logging.error(f"Failed to generate QR for student {student_id}")
    
    if not valid_qr_files:
        raise HTTPException(status_code=500, detail="Failed to generate any QR codes")
    
    logging.info(f"Successfully generated {len(valid_qr_files)} QR codes")
    
    # Create a temporary zip file using file manager
    zip_filename = f"group_{group_id}_qrcodes_{int(time.time())}.zip"
    zip_path = file_manager.create_temp_file(suffix='.zip', prefix=f'group_{group_id}_qrcodes_')
    
    try:
        # Create ZIP file with proper compression
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            for qr_path, filename in valid_qr_files:
                if os.path.exists(qr_path):
                    # Add file to ZIP
                    zip_file.write(qr_path, filename)
                    logging.debug(f"Added to ZIP: {filename}")
                else:
                    logging.warning(f"File not found when adding to ZIP: {qr_path}")
        
        # Verify ZIP file was created and has content
        if not os.path.exists(zip_path):
            file_manager.cleanup_file(zip_path)  # Clean up on failure
            raise HTTPException(status_code=500, detail="Failed to create ZIP file")
        
        # Validate file size
        if not file_manager.validate_file_size(zip_path):
            file_manager.cleanup_file(zip_path)  # Clean up oversized file
            raise HTTPException(status_code=413, detail=f"ZIP file too large. Maximum size: {config.MAX_FILE_SIZE_MB}MB")
        
        zip_size = os.path.getsize(zip_path)
        if zip_size == 0:
            file_manager.cleanup_file(zip_path)  # Clean up empty file
            raise HTTPException(status_code=500, detail="Generated ZIP file is empty")
        
        logging.info(f"ZIP file created successfully: {zip_path} ({zip_size} bytes)")
        
        # Test ZIP file integrity
        try:
            with zipfile.ZipFile(zip_path, 'r') as test_zip:
                file_list = test_zip.namelist()
                logging.debug(f"ZIP contains {len(file_list)} files: {file_list}")
                # Test if we can read the ZIP
                test_zip.testzip()
        except Exception as e:
            file_manager.cleanup_file(zip_path)  # Clean up corrupted file
            logging.error(f"ZIP integrity test failed: {e}")
            raise HTTPException(status_code=500, detail=f"ZIP file is corrupted: {e}")
        
        # Return the zip file as a response
        return FileResponse(
            zip_path, 
            media_type="application/zip",
            filename=f"group_{group_id}_qrcodes.zip",
            headers={"Content-Disposition": f"attachment; filename=group_{group_id}_qrcodes.zip"}
        )
        
    except Exception as e:
        print(f"Error creating ZIP file: {e}")
        # Clean up if ZIP creation failed
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP file: {e}")
