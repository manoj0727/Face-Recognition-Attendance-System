import cv2
import face_recognition
import numpy as np
import pickle
import os
from datetime import datetime
import sqlite3
import time

class AutoFaceRecognition:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.camera = None
        self.database_path = "database/attendance_enhanced.db"
        self.encodings_file = "database/face_encodings.pkl"
        self.load_known_faces()
        
    def load_known_faces(self):
        """Load pre-registered face encodings"""
        if os.path.exists(self.encodings_file):
            try:
                with open(self.encodings_file, 'rb') as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data.get('encodings', [])
                    self.known_face_names = data.get('names', [])
                print(f"Loaded {len(self.known_face_names)} registered faces")
            except Exception as e:
                print(f"Error loading faces: {e}")
    
    def save_face_encoding(self, name, encoding):
        """Save a new face encoding"""
        self.known_face_encodings.append(encoding)
        self.known_face_names.append(name)
        
        os.makedirs("database", exist_ok=True)
        data = {
            'encodings': self.known_face_encodings,
            'names': self.known_face_names
        }
        with open(self.encodings_file, 'wb') as f:
            pickle.dump(data, f)
    
    def register_new_face(self, name):
        """Register a new face using camera"""
        print(f"Registering {name}. Please look at the camera...")
        
        self.start_camera()
        start_time = time.time()
        face_captured = False
        
        while time.time() - start_time < 10:  # 10 second timeout
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                if face_encodings:
                    self.save_face_encoding(name, face_encodings[0])
                    print(f"✅ Face registered for {name}")
                    face_captured = True
                    
                    # Draw rectangle to show face detected
                    top, right, bottom, left = face_locations[0]
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, f"Registered: {name}", (left, top - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow('Face Registration', frame)
            
            if face_captured or cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.release_camera()
        cv2.destroyWindow('Face Registration')
        return face_captured
    
    def start_camera(self):
        """Start camera if not already started"""
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            time.sleep(0.5)  # Give camera time to warm up
    
    def release_camera(self):
        """Release camera resources"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
    
    def mark_attendance(self, student_name):
        """Mark attendance in database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Create attendance table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT,
                    timestamp DATETIME,
                    date DATE,
                    status TEXT DEFAULT 'Present'
                )
            ''')
            
            # Check if already marked today
            today = datetime.now().date()
            cursor.execute('''
                SELECT * FROM attendance 
                WHERE student_name = ? AND date = ?
            ''', (student_name, today))
            
            if cursor.fetchone() is None:
                cursor.execute('''
                    INSERT INTO attendance (student_name, timestamp, date, status)
                    VALUES (?, ?, ?, 'Present')
                ''', (student_name, datetime.now(), today))
                conn.commit()
                print(f"✅ Attendance marked for {student_name}")
                return True
            else:
                print(f"ℹ️ {student_name} already marked present today")
                return False
                
        except Exception as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
    
    def run_auto_recognition(self, duration_seconds=30):
        """Run automatic face recognition for specified duration"""
        print(f"Starting automatic face recognition for {duration_seconds} seconds...")
        print("Press 'q' to quit, 'r' to register new face")
        
        if not self.known_face_encodings:
            print("⚠️ No registered faces found. Please register faces first.")
            return
        
        self.start_camera()
        start_time = time.time()
        recognized_today = set()
        frame_count = 0
        
        while time.time() - start_time < duration_seconds:
            ret, frame = self.camera.read()
            if not ret:
                continue
            
            frame_count += 1
            
            # Process every 3rd frame for performance
            if frame_count % 3 == 0:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                for face_encoding, face_location in zip(face_encodings, face_locations):
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                            name = self.known_face_names[best_match_index]
                            
                            # Scale back up face locations
                            top, right, bottom, left = face_location
                            top *= 4
                            right *= 4
                            bottom *= 4
                            left *= 4
                            
                            # Draw rectangle and name
                            color = (0, 255, 0) if name not in recognized_today else (255, 255, 0)
                            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                            cv2.putText(frame, name, (left, top - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
                            
                            # Mark attendance if not already done today
                            if name not in recognized_today:
                                if self.mark_attendance(name):
                                    recognized_today.add(name)
                        else:
                            # Unknown face
                            top, right, bottom, left = face_location
                            top *= 4
                            right *= 4
                            bottom *= 4
                            left *= 4
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                            cv2.putText(frame, "Unknown", (left, top - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            
            # Display info
            remaining_time = int(duration_seconds - (time.time() - start_time))
            cv2.putText(frame, f"Time: {remaining_time}s | Present: {len(recognized_today)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv2.imshow('Auto Face Recognition', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.release_camera()
                cv2.destroyWindow('Auto Face Recognition')
                name = input("\nEnter name to register: ")
                if name:
                    self.register_new_face(name)
                self.start_camera()
        
        self.release_camera()
        cv2.destroyAllWindows()
        
        print(f"\n📊 Session Summary:")
        print(f"Total recognized: {len(recognized_today)}")
        print(f"Students present: {', '.join(recognized_today)}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.release_camera()
        cv2.destroyAllWindows()

def main():
    system = AutoFaceRecognition()
    
    while True:
        print("\n=== Automatic Face Recognition System ===")
        print("1. Start Auto Recognition (30 seconds)")
        print("2. Start Auto Recognition (custom duration)")
        print("3. Register New Face")
        print("4. View Today's Attendance")
        print("5. Exit")
        
        choice = input("\nEnter choice: ")
        
        if choice == '1':
            system.run_auto_recognition(30)
        
        elif choice == '2':
            try:
                duration = int(input("Enter duration in seconds: "))
                system.run_auto_recognition(duration)
            except ValueError:
                print("Invalid duration")
        
        elif choice == '3':
            name = input("Enter student name: ")
            if name:
                system.register_new_face(name)
        
        elif choice == '4':
            try:
                conn = sqlite3.connect(system.database_path)
                cursor = conn.cursor()
                today = datetime.now().date()
                cursor.execute('''
                    SELECT student_name, timestamp FROM attendance 
                    WHERE date = ? ORDER BY timestamp
                ''', (today,))
                records = cursor.fetchall()
                
                if records:
                    print(f"\n📅 Today's Attendance ({today}):")
                    for name, timestamp in records:
                        print(f"  • {name}: {timestamp}")
                else:
                    print("No attendance records for today")
                conn.close()
            except Exception as e:
                print(f"Error viewing attendance: {e}")
        
        elif choice == '5':
            system.cleanup()
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()