import cv2
import face_recognition
import numpy as np
from datetime import datetime, timedelta
import pickle
import base64
import json
import os
from typing import Optional, List, Dict, Tuple
import hashlib
from supabase import create_client, Client
from supabase_config import SupabaseConfig
import io
from PIL import Image
import time

class SupabaseManager:
    """Optimized Supabase manager for face recognition system"""
    
    def __init__(self):
        self.config = SupabaseConfig()
        self.supabase: Optional[Client] = None
        self.local_cache = {}
        self.cache_timestamp = {}
        self.face_encodings_cache = {}
        
        if self.config.is_configured():
            self.supabase = create_client(
                self.config.SUPABASE_URL,
                self.config.SUPABASE_KEY
            )
            self.setup_database()
    
    def setup_database(self):
        """Initialize database tables if they don't exist"""
        try:
            # Tables will be created via Supabase dashboard
            # This is just to verify connection
            self.supabase.table(self.config.STUDENTS_TABLE).select("*").limit(1).execute()
        except Exception as e:
            print(f"Database setup note: {e}")
    
    def optimize_image(self, image: np.ndarray, max_size: Tuple[int, int] = (400, 400)) -> bytes:
        """
        Optimize image for storage - resize and compress
        Returns compressed JPEG bytes
        """
        # Convert BGR to RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize if needed
        height, width = image.shape[:2]
        if width > max_size[0] or height > max_size[1]:
            scale = min(max_size[0]/width, max_size[1]/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(image)
        
        # Compress as JPEG
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=85, optimize=True)
        return buffer.getvalue()
    
    def generate_student_id(self, name: str) -> str:
        """Generate unique student ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(name.encode()).hexdigest()[:6]
        return f"STU{timestamp}{hash_part}"
    
    def register_student(self, name: str, email: str = None, class_name: str = None, 
                        face_image: np.ndarray = None, face_encoding: np.ndarray = None) -> Dict:
        """
        Register a new student with optimized image storage
        Only stores ONE image per student
        """
        try:
            student_id = self.generate_student_id(name)
            image_url = None
            
            # Upload optimized face image if provided
            if face_image is not None:
                # Optimize image before upload
                optimized_image = self.optimize_image(face_image)
                
                # Upload to Supabase storage
                file_name = f"{student_id}.jpg"
                response = self.supabase.storage.from_(self.config.FACES_BUCKET).upload(
                    file_name,
                    optimized_image,
                    file_options={"content-type": "image/jpeg"}
                )
                
                # Get public URL
                image_url = self.supabase.storage.from_(self.config.FACES_BUCKET).get_public_url(file_name)
            
            # Store student data
            student_data = {
                'student_id': student_id,
                'name': name,
                'email': email,
                'class_name': class_name,
                'face_image_url': image_url,
                'registered_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table(self.config.STUDENTS_TABLE).insert(student_data).execute()
            
            # Store face encoding separately for faster retrieval
            if face_encoding is not None:
                encoding_data = {
                    'student_id': student_id,
                    'encoding': base64.b64encode(pickle.dumps(face_encoding)).decode('utf-8'),
                    'created_at': datetime.now().isoformat()
                }
                self.supabase.table(self.config.FACE_ENCODINGS_TABLE).insert(encoding_data).execute()
                
                # Update cache
                self.face_encodings_cache[student_id] = {
                    'name': name,
                    'encoding': face_encoding,
                    'timestamp': time.time()
                }
            
            return {'success': True, 'student_id': student_id, 'message': f'Student {name} registered successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_face_encodings(self) -> Dict[str, np.ndarray]:
        """
        Get all face encodings with caching for high-speed recognition
        Uses local cache to minimize API calls
        """
        # Check cache validity
        if self.config.CACHE_ENABLED and self.face_encodings_cache:
            cache_age = time.time() - min(data['timestamp'] for data in self.face_encodings_cache.values())
            if cache_age < self.config.CACHE_TTL:
                return {
                    student_id: data['encoding'] 
                    for student_id, data in self.face_encodings_cache.items()
                }
        
        try:
            # Fetch from database
            encodings_result = self.supabase.table(self.config.FACE_ENCODINGS_TABLE).select("*").execute()
            students_result = self.supabase.table(self.config.STUDENTS_TABLE).select("student_id, name").execute()
            
            # Create student name mapping
            student_names = {s['student_id']: s['name'] for s in students_result.data}
            
            # Decode and cache encodings
            self.face_encodings_cache.clear()
            for record in encodings_result.data:
                student_id = record['student_id']
                encoding_bytes = base64.b64decode(record['encoding'])
                encoding = pickle.loads(encoding_bytes)
                
                self.face_encodings_cache[student_id] = {
                    'name': student_names.get(student_id, 'Unknown'),
                    'encoding': encoding,
                    'timestamp': time.time()
                }
            
            return {
                student_id: data['encoding'] 
                for student_id, data in self.face_encodings_cache.items()
            }
            
        except Exception as e:
            print(f"Error fetching encodings: {e}")
            return {}
    
    def mark_attendance(self, student_id: str, class_name: str = None, 
                       location: str = None, confidence: float = None) -> bool:
        """
        Mark attendance with duplicate prevention
        Only allows one attendance per day per student
        """
        try:
            today = datetime.now().date().isoformat()
            
            # Check if already marked today (using cache first)
            cache_key = f"attendance_{student_id}_{today}"
            if cache_key in self.local_cache:
                print(f"Already marked (cached): {student_id}")
                return False
            
            # Check in database
            existing = self.supabase.table(self.config.ATTENDANCE_TABLE)\
                .select("*")\
                .eq('student_id', student_id)\
                .eq('date', today)\
                .execute()
            
            if existing.data:
                self.local_cache[cache_key] = True
                print(f"Already marked (database): {student_id}")
                return False
            
            # Mark attendance
            attendance_data = {
                'student_id': student_id,
                'date': today,
                'check_in_time': datetime.now().isoformat(),
                'class_name': class_name,
                'location': location,
                'confidence_score': confidence,
                'status': 'present'
            }
            
            self.supabase.table(self.config.ATTENDANCE_TABLE).insert(attendance_data).execute()
            self.local_cache[cache_key] = True
            
            return True
            
        except Exception as e:
            print(f"Error marking attendance: {e}")
            return False
    
    def get_today_attendance(self, class_name: Optional[str] = None) -> List[Dict]:
        """Get today's attendance records"""
        try:
            today = datetime.now().date().isoformat()
            query = self.supabase.table(self.config.ATTENDANCE_TABLE)\
                .select("*, students(name, email)")\
                .eq('date', today)
            
            if class_name:
                query = query.eq('class_name', class_name)
            
            result = query.order('check_in_time', desc=False).execute()
            return result.data
            
        except Exception as e:
            print(f"Error fetching attendance: {e}")
            return []
    
    def update_student_image(self, student_id: str, new_face_image: np.ndarray, 
                            new_face_encoding: np.ndarray) -> bool:
        """
        Update student's face image (replaces old one)
        Maintains single image per student policy
        """
        try:
            # Delete old image if exists
            try:
                old_file = f"{student_id}.jpg"
                self.supabase.storage.from_(self.config.FACES_BUCKET).remove([old_file])
            except:
                pass  # Old image might not exist
            
            # Upload new optimized image
            optimized_image = self.optimize_image(new_face_image)
            file_name = f"{student_id}.jpg"
            
            self.supabase.storage.from_(self.config.FACES_BUCKET).upload(
                file_name,
                optimized_image,
                file_options={"content-type": "image/jpeg", "upsert": "true"}
            )
            
            # Update face encoding
            encoding_data = {
                'encoding': base64.b64encode(pickle.dumps(new_face_encoding)).decode('utf-8'),
                'updated_at': datetime.now().isoformat()
            }
            
            self.supabase.table(self.config.FACE_ENCODINGS_TABLE)\
                .update(encoding_data)\
                .eq('student_id', student_id)\
                .execute()
            
            # Clear cache to force refresh
            if student_id in self.face_encodings_cache:
                del self.face_encodings_cache[student_id]
            
            return True
            
        except Exception as e:
            print(f"Error updating student image: {e}")
            return False
    
    def get_attendance_stats(self, days: int = 30) -> Dict:
        """Get attendance statistics for the last N days"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            result = self.supabase.table(self.config.ATTENDANCE_TABLE)\
                .select("*")\
                .gte('date', start_date)\
                .execute()
            
            stats = {
                'total_records': len(result.data),
                'unique_students': len(set(r['student_id'] for r in result.data)),
                'dates': len(set(r['date'] for r in result.data)),
                'average_daily': len(result.data) / max(1, len(set(r['date'] for r in result.data)))
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def sync_offline_data(self, offline_records: List[Dict]) -> int:
        """Sync offline attendance records to Supabase"""
        synced = 0
        for record in offline_records:
            try:
                # Check if already exists
                existing = self.supabase.table(self.config.ATTENDANCE_TABLE)\
                    .select("*")\
                    .eq('student_id', record['student_id'])\
                    .eq('date', record['date'])\
                    .execute()
                
                if not existing.data:
                    self.supabase.table(self.config.ATTENDANCE_TABLE).insert(record).execute()
                    synced += 1
            except:
                continue
        
        return synced