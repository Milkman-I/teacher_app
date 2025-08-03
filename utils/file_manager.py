# File management utilities for Teacher App Backend
import os
import tempfile
import time
import logging
import threading
from typing import List, Optional
from pathlib import Path
import zipfile
import shutil

from config import config

logger = logging.getLogger(__name__)

class FileManager:
    """Manages temporary files and cleanup operations"""
    
    def __init__(self):
        self.temp_files: List[str] = []
        self.cleanup_lock = threading.Lock()
        self._cleanup_interval = 3600  # 1 hour
        self._max_file_age = 86400  # 24 hours
        self._start_cleanup_scheduler()
    
    def _start_cleanup_scheduler(self):
        """Start background cleanup scheduler"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self._cleanup_interval)
                    self.cleanup_old_files()
                except Exception as e:
                    logger.error(f"Error in cleanup scheduler: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("File cleanup scheduler started")
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'teacher_app_', directory: str = None) -> str:
        """Create a temporary file and track it for cleanup"""
        if directory is None:
            directory = config.TEMP_DIR
        
        # Ensure directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Create temporary file
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
        os.close(fd)  # Close file descriptor, we just need the path
        
        # Track for cleanup
        with self.cleanup_lock:
            self.temp_files.append(temp_path)
        
        logger.debug(f"Created temporary file: {temp_path}")
        return temp_path
    
    def create_temp_directory(self, prefix: str = 'teacher_app_', directory: str = None) -> str:
        """Create a temporary directory and track it for cleanup"""
        if directory is None:
            directory = config.TEMP_DIR
        
        # Ensure parent directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=prefix, dir=directory)
        
        # Track for cleanup
        with self.cleanup_lock:
            self.temp_files.append(temp_dir)
        
        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir
    
    def cleanup_file(self, file_path: str) -> bool:
        """Clean up a specific file or directory"""
        try:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    logger.debug(f"Removed temporary directory: {file_path}")
                else:
                    os.remove(file_path)
                    logger.debug(f"Removed temporary file: {file_path}")
                
                # Remove from tracking list
                with self.cleanup_lock:
                    if file_path in self.temp_files:
                        self.temp_files.remove(file_path)
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")
            return False
    
    def cleanup_old_files(self) -> int:
        """Clean up old temporary files"""
        cleaned_count = 0
        current_time = time.time()
        
        with self.cleanup_lock:
            files_to_remove = []
            
            for file_path in self.temp_files[:]:  # Create a copy to iterate
                try:
                    if os.path.exists(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > self._max_file_age:
                            if self.cleanup_file(file_path):
                                files_to_remove.append(file_path)
                                cleaned_count += 1
                    else:
                        # File doesn't exist, remove from tracking
                        files_to_remove.append(file_path)
                except Exception as e:
                    logger.error(f"Error checking file {file_path}: {e}")
            
            # Remove cleaned files from tracking list
            for file_path in files_to_remove:
                if file_path in self.temp_files:
                    self.temp_files.remove(file_path)
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old temporary files")
        
        return cleaned_count
    
    def cleanup_qr_codes(self, max_age_hours: int = 24) -> int:
        """Clean up old QR code files"""
        qr_dir = config.QR_CODES_DIR
        if not os.path.exists(qr_dir):
            return 0
        
        cleaned_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        try:
            for filename in os.listdir(qr_dir):
                file_path = os.path.join(qr_dir, filename)
                if os.path.isfile(file_path) and filename.endswith('.png'):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        try:
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.debug(f"Removed old QR code: {filename}")
                        except Exception as e:
                            logger.error(f"Error removing QR code {filename}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old QR code files")
                
        except Exception as e:
            logger.error(f"Error cleaning QR codes directory: {e}")
        
        return cleaned_count
    
    def get_file_size_mb(self, file_path: str) -> float:
        """Get file size in MB"""
        try:
            if os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                return size_bytes / (1024 * 1024)
            return 0.0
        except Exception as e:
            logger.error(f"Error getting file size for {file_path}: {e}")
            return 0.0
    
    def validate_file_size(self, file_path: str, max_size_mb: Optional[float] = None) -> bool:
        """Validate file size against limits"""
        if max_size_mb is None:
            max_size_mb = config.MAX_FILE_SIZE_MB
        
        file_size_mb = self.get_file_size_mb(file_path)
        if file_size_mb > max_size_mb:
            logger.warning(f"File {file_path} exceeds size limit: {file_size_mb:.2f}MB > {max_size_mb}MB")
            return False
        
        return True
    
    def create_safe_filename(self, filename: str) -> str:
        """Create a safe filename by removing/replacing problematic characters"""
        # Replace problematic characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        safe_filename = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Remove multiple underscores
        while '__' in safe_filename:
            safe_filename = safe_filename.replace('__', '_')
        
        # Remove leading/trailing underscores and dots
        safe_filename = safe_filename.strip('_.')
        
        # Ensure filename is not empty
        if not safe_filename:
            safe_filename = 'file'
        
        return safe_filename
    
    def cleanup_all(self) -> dict:
        """Perform comprehensive cleanup and return statistics"""
        stats = {
            'temp_files_cleaned': 0,
            'qr_codes_cleaned': 0,
            'total_cleaned': 0
        }
        
        # Clean up temporary files
        stats['temp_files_cleaned'] = self.cleanup_old_files()
        
        # Clean up old QR codes
        stats['qr_codes_cleaned'] = self.cleanup_qr_codes()
        
        stats['total_cleaned'] = stats['temp_files_cleaned'] + stats['qr_codes_cleaned']
        
        logger.info(f"Cleanup completed: {stats}")
        return stats

# Global file manager instance
file_manager = FileManager()

# Convenience functions
def create_temp_file(suffix: str = '', prefix: str = 'teacher_app_') -> str:
    """Create a temporary file"""
    return file_manager.create_temp_file(suffix=suffix, prefix=prefix)

def create_temp_directory(prefix: str = 'teacher_app_') -> str:
    """Create a temporary directory"""
    return file_manager.create_temp_directory(prefix=prefix)

def cleanup_file(file_path: str) -> bool:
    """Clean up a specific file"""
    return file_manager.cleanup_file(file_path)

def create_safe_filename(filename: str) -> str:
    """Create a safe filename"""
    return file_manager.create_safe_filename(filename)
