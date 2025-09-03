import os
from dotenv import load_dotenv

load_dotenv()

class SupabaseConfig:
    """Configuration for Supabase connection"""
    
    # These will be set from environment variables
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Table names
    STUDENTS_TABLE = 'students'
    ATTENDANCE_TABLE = 'attendance'
    FACE_ENCODINGS_TABLE = 'face_encodings'
    
    # Storage bucket names
    FACES_BUCKET = 'student-faces'
    
    # Cache settings
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # 1 hour in seconds
    
    @classmethod
    def is_configured(cls):
        """Check if Supabase credentials are configured"""
        return bool(cls.SUPABASE_URL and cls.SUPABASE_KEY)
    
    @classmethod
    def get_config(cls):
        """Get configuration dictionary"""
        return {
            'url': cls.SUPABASE_URL,
            'key': cls.SUPABASE_KEY,
            'configured': cls.is_configured()
        }