import cv2
import face_recognition
import numpy as np
from datetime import datetime
import time
from typing import Dict, List, Optional, Tuple
import threading
import queue
from collections import deque
from supabase_manager import SupabaseManager
import os
import json

class OptimizedFaceRecognition:
    """
    High-speed face recognition with Supabase integration
    Features:
    - Frame skipping for performance
    - Multi-threading for parallel processing
    - Local caching for speed
    - Automatic Supabase sync
    - Single image per person storage
    """
    
    def __init__(self):
        self.supabase = SupabaseManager()
        self.camera = None
        self.known_encodings = {}
        self.student_names = {}
        self.recognition_cache = {}
        self.cache_timeout = 5  # seconds
        
        # Performance settings
        self.frame_skip = 3  # Process every 3rd frame
        self.scale_factor = 0.25  # Scale down for faster processing
        self.recognition_threshold = 0.5  # Lower = more strict
        
        # Threading for parallel processing
        self.frame_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        self.processing = False
        
        # Offline mode
        self.offline_mode = False
        self.offline_records = []
        
        # Load face encodings
        self.load_encodings()
    
    def load_encodings(self):
        """Load face encodings from Supabase with caching"""
        print("Loading face encodings...")
        
        # Try loading from Supabase
        if self.supabase.config.is_configured():
            encodings = self.supabase.get_all_face_encodings()
            
            for student_id, encoding in encodings.items():
                self.known_encodings[student_id] = encoding
                # Get student name from cache
                if student_id in self.supabase.face_encodings_cache:
                    self.student_names[student_id] = self.supabase.face_encodings_cache[student_id]['name']
        
        # Fallback to local cache if offline
        if not self.known_encodings:
            self.load_local_cache()
        
        print(f"Loaded {len(self.known_encodings)} face encodings")
    
    def load_local_cache(self):
        """Load from local cache file"""
        cache_file = "cache/face_encodings.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for student_id, record in data.items():
                        encoding_bytes = base64.b64decode(record['encoding'])
                        self.known_encodings[student_id] = pickle.loads(encoding_bytes)
                        self.student_names[student_id] = record['name']
                self.offline_mode = True
                print("Running in offline mode")
            except Exception as e:
                print(f"Error loading local cache: {e}")
    
    def save_local_cache(self):
        """Save encodings to local cache"""
        os.makedirs("cache", exist_ok=True)
        cache_data = {}
        
        for student_id, encoding in self.known_encodings.items():
            cache_data[student_id] = {
                'name': self.student_names.get(student_id, 'Unknown'),
                'encoding': base64.b64encode(pickle.dumps(encoding)).decode('utf-8')
            }
        
        with open("cache/face_encodings.json", 'w') as f:
            json.dump(cache_data, f)
    
    def process_frame_worker(self):
        """Worker thread for processing frames"""
        while self.processing:
            try:
                frame = self.frame_queue.get(timeout=1)
                if frame is None:
                    continue
                
                # Process frame
                results = self.recognize_faces_in_frame(frame)
                self.result_queue.put(results)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Processing error: {e}")
    
    def recognize_faces_in_frame(self, frame: np.ndarray) -> List[Dict]:
        """Recognize faces in a single frame with optimization"""
        # Resize for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find faces
        face_locations = face_recognition.face_locations(rgb_small_frame, model='hog')  # HOG is faster
        
        if not face_locations:
            return []
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        results = []
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Check cache first
            encoding_hash = hash(face_encoding.tobytes())
            
            if encoding_hash in self.recognition_cache:
                cached_result = self.recognition_cache[encoding_hash]
                if time.time() - cached_result['timestamp'] < self.cache_timeout:
                    results.append(cached_result['data'])
                    continue
            
            # Perform recognition
            if self.known_encodings:
                # Vectorized comparison for speed
                known_encodings_list = list(self.known_encodings.values())
                known_ids = list(self.known_encodings.keys())
                
                distances = face_recognition.face_distance(known_encodings_list, face_encoding)
                
                if len(distances) > 0:
                    best_match_idx = np.argmin(distances)
                    
                    if distances[best_match_idx] < self.recognition_threshold:
                        student_id = known_ids[best_match_idx]
                        name = self.student_names.get(student_id, "Unknown")
                        confidence = 1.0 - distances[best_match_idx]
                        
                        # Scale back up face location
                        top, right, bottom, left = face_location
                        top = int(top / self.scale_factor)
                        right = int(right / self.scale_factor)
                        bottom = int(bottom / self.scale_factor)
                        left = int(left / self.scale_factor)
                        
                        result = {
                            'student_id': student_id,
                            'name': name,
                            'confidence': confidence,
                            'location': (top, right, bottom, left),
                            'timestamp': time.time()
                        }
                        
                        # Cache result
                        self.recognition_cache[encoding_hash] = {
                            'data': result,
                            'timestamp': time.time()
                        }
                        
                        results.append(result)
        
        return results
    
    def register_new_student(self, name: str, email: str = None, class_name: str = None) -> bool:
        """Register new student with single optimized image"""
        print(f"Registering {name}...")
        print("Please look at the camera. Press SPACE to capture, ESC to cancel")
        
        self.start_camera()
        captured = False
        
        while True:
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            # Detect face
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            display_frame = frame.copy()
            
            if face_locations:
                # Draw rectangle
                top, right, bottom, left = face_locations[0]
                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(display_frame, "Face Detected - Press SPACE to capture", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(display_frame, "No face detected", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Registration', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' ') and face_locations:
                # Capture face
                face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                
                # Extract face image
                top, right, bottom, left = face_locations[0]
                face_image = frame[top:bottom, left:right]
                
                # Register with Supabase
                result = self.supabase.register_student(
                    name=name,
                    email=email,
                    class_name=class_name,
                    face_image=face_image,
                    face_encoding=face_encoding
                )
                
                if result['success']:
                    student_id = result['student_id']
                    # Update local cache
                    self.known_encodings[student_id] = face_encoding
                    self.student_names[student_id] = name
                    print(f"✅ Registered successfully! ID: {student_id}")
                    captured = True
                else:
                    print(f"❌ Registration failed: {result.get('error')}")
                
                break
            
            elif key == 27:  # ESC
                print("Registration cancelled")
                break
        
        self.release_camera()
        cv2.destroyWindow('Registration')
        return captured
    
    def start_camera(self):
        """Initialize camera with optimization"""
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            
            # Set camera properties for speed
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # Warm up camera
            for _ in range(5):
                self.camera.read()
    
    def release_camera(self):
        """Release camera resources"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
    
    def run_recognition_session(self, duration: int = 30, class_name: str = None):
        """Run optimized recognition session"""
        print(f"Starting {duration} second recognition session...")
        
        if not self.known_encodings:
            print("❌ No registered students found")
            return
        
        self.start_camera()
        self.processing = True
        
        # Start processing thread
        process_thread = threading.Thread(target=self.process_frame_worker)
        process_thread.start()
        
        start_time = time.time()
        frame_count = 0
        recognized_today = set()
        last_recognition = {}
        
        while time.time() - start_time < duration:
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # Skip frames for performance
            if frame_count % self.frame_skip == 0:
                # Add frame to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait(frame.copy())
                except queue.Full:
                    pass
            
            # Get recognition results
            display_frame = frame.copy()
            try:
                while not self.result_queue.empty():
                    results = self.result_queue.get_nowait()
                    
                    for result in results:
                        student_id = result['student_id']
                        name = result['name']
                        confidence = result['confidence']
                        top, right, bottom, left = result['location']
                        
                        # Debounce recognition (avoid multiple marks)
                        if student_id in last_recognition:
                            if time.time() - last_recognition[student_id] < 2:
                                continue
                        
                        # Draw on frame
                        color = (0, 255, 0) if student_id not in recognized_today else (255, 255, 0)
                        cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                        label = f"{name} ({confidence:.2f})"
                        cv2.putText(display_frame, label, (left, top - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
                        # Mark attendance
                        if student_id not in recognized_today:
                            if self.offline_mode:
                                # Save offline
                                self.offline_records.append({
                                    'student_id': student_id,
                                    'date': datetime.now().date().isoformat(),
                                    'check_in_time': datetime.now().isoformat(),
                                    'class_name': class_name,
                                    'confidence_score': confidence
                                })
                                recognized_today.add(student_id)
                                print(f"✅ Marked (offline): {name}")
                            else:
                                # Mark in Supabase
                                if self.supabase.mark_attendance(student_id, class_name, confidence=confidence):
                                    recognized_today.add(student_id)
                                    print(f"✅ Marked: {name}")
                        
                        last_recognition[student_id] = time.time()
                        
            except queue.Empty:
                pass
            
            # Display stats
            remaining = int(duration - (time.time() - start_time))
            fps = frame_count / max(1, time.time() - start_time)
            
            cv2.putText(display_frame, f"Time: {remaining}s | FPS: {fps:.1f} | Present: {len(recognized_today)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if self.offline_mode:
                cv2.putText(display_frame, "OFFLINE MODE", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            cv2.imshow('Face Recognition', display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Cleanup
        self.processing = False
        process_thread.join()
        self.release_camera()
        cv2.destroyAllWindows()
        
        # Sync offline data if needed
        if self.offline_mode and self.offline_records and self.supabase.config.is_configured():
            print("Syncing offline records...")
            synced = self.supabase.sync_offline_data(self.offline_records)
            print(f"Synced {synced} offline records")
            self.offline_records.clear()
        
        # Summary
        print(f"\n📊 Session Summary:")
        print(f"Total recognized: {len(recognized_today)}")
        print(f"Average FPS: {fps:.1f}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.processing = False
        self.release_camera()
        cv2.destroyAllWindows()
        
        # Save cache
        if self.known_encodings:
            self.save_local_cache()

def main():
    system = OptimizedFaceRecognition()
    
    while True:
        print("\n=== Optimized Face Recognition (Supabase) ===")
        print("1. Start Recognition (30s)")
        print("2. Register New Student")
        print("3. View Today's Attendance")
        print("4. Sync Offline Data")
        print("5. Exit")
        
        choice = input("\nChoice: ")
        
        if choice == '1':
            class_name = input("Enter class name (optional): ")
            system.run_recognition_session(30, class_name if class_name else None)
        
        elif choice == '2':
            name = input("Student name: ")
            email = input("Email (optional): ")
            class_name = input("Class (optional): ")
            system.register_new_student(
                name,
                email if email else None,
                class_name if class_name else None
            )
        
        elif choice == '3':
            if system.supabase.config.is_configured():
                records = system.supabase.get_today_attendance()
                if records:
                    print(f"\n📅 Today's Attendance:")
                    for record in records:
                        student_name = record.get('students', {}).get('name', 'Unknown')
                        check_in = record.get('check_in_time', '')
                        print(f"  • {student_name}: {check_in}")
                else:
                    print("No attendance records for today")
            else:
                print("Supabase not configured")
        
        elif choice == '4':
            if system.offline_records:
                synced = system.supabase.sync_offline_data(system.offline_records)
                print(f"Synced {synced} records")
                system.offline_records.clear()
            else:
                print("No offline records to sync")
        
        elif choice == '5':
            system.cleanup()
            break

if __name__ == "__main__":
    main()