# Configuration management for Teacher App Backend
import os
from typing import List
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration with environment variable support"""
    
    # Database Configuration
    DATABASE_NAME: str = os.getenv('DATABASE_NAME', 'Teachers.db')
    DATABASE_PATH: str = os.getenv('DATABASE_PATH', '.')
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ALGORITHM: str = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_HOURS: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    
    # Server Configuration
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '9070'))
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = os.getenv('CORS_ORIGINS', 'http://localhost:19006,http://localhost:3000,http://127.0.0.1:19006').split(',')
    CORS_ALLOW_CREDENTIALS: bool = os.getenv('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'
    
    # File storage settings
    UPLOAD_DIR: str = os.getenv('UPLOAD_DIR', 'uploads')
    QR_CODES_DIR: str = os.getenv('QR_CODES_DIR', 'qrcodes')
    TEMP_DIR: str = os.getenv('TEMP_DIR', 'temp')
    MAX_UPLOAD_SIZE: int = int(os.getenv('MAX_UPLOAD_SIZE', '10485760'))  # 10MB
    MAX_FILE_SIZE_MB: float = float(os.getenv('MAX_FILE_SIZE_MB', '50'))  # 50MB
    MAX_STUDENTS_PER_GROUP: int = int(os.getenv('MAX_STUDENTS_PER_GROUP', '500'))  # Performance limit  
    
    # Security Configuration
    BCRYPT_ROUNDS: int = int(os.getenv('BCRYPT_ROUNDS', '12'))
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get the full database file path"""
        return os.path.join(cls.DATABASE_PATH, cls.DATABASE_NAME)
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate critical configuration values"""
        if cls.JWT_SECRET_KEY == 'your-secret-key-change-in-production':
            print("WARNING: Using default JWT secret key! Change JWT_SECRET_KEY environment variable in production!")
        
        if not os.path.exists(cls.QR_CODES_DIR):
            os.makedirs(cls.QR_CODES_DIR, exist_ok=True)
            print(f"Created QR codes directory: {cls.QR_CODES_DIR}")

# Create global config instance
config = Config()
