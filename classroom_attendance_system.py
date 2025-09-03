import cv2
import numpy as np
from datetime import datetime
import pickle
import os
from typing import List, Dict, Optional
from enhanced_database_manager import EnhancedDatabaseManager
from enhanced_face_recognition import EnhancedFaceRecognition
import threading
import queue
import time

class ClassroomAttendanceSystem:
    def __init__(self):
        self.db = EnhancedDatabaseManager()
        self.face_recognition = EnhancedFaceRecognition()
        self.current_classroom = None
        self.attendance_queue = queue.Queue()
        self.is_marking_attendance = False
        self.recognized_students = set()
        
    def select_classroom(self, classroom_id: str):
        """Select a classroom for attendance marking"""
        self.current_classroom = classroom_id
        students = self.db.get_classroom_students(classroom_id)
        self.face_recognition.load_classroom_faces(students)
        self.recognized_students.clear()
        return len(students)
    
    def register_student_batch(self, classroom_id: str, students_data: List[Dict], 
                              capture_method: str = 'upload'):
        """Register multiple students at once for a classroom"""
        results = []
        
        for student in students_data:
            try:
                if capture_method == 'upload' and 'image_path' in student:
                    face_encoding, metadata = self.face_recognition.capture_and_encode_face(
                        image_path=student['image_path']
                    )
                elif capture_method == 'camera' and 'camera_frame' in student:
                    face_encoding, metadata = self.face_recognition.capture_and_encode_face(
                        camera_capture=student['camera_frame']
                    )
                else:
                    results.append({
                        'student_id': student['student_id'],
                        'success': False,
                        'error': 'Invalid capture method or missing image data'
                    })
                    continue
                
                if face_encoding is None:
                    results.append({
                        'student_id': student['student_id'],
                        'success': False,
                        'error': metadata.get('error', 'Failed to encode face')
                    })
                    continue
                
                face_quality_score = metadata.get('quality', {}).get('overall', 0.0)
                face_encoding_blob = pickle.dumps(face_encoding)
                
                success = self.db.add_student(
                    student_id=student['student_id'],
                    name=student['name'],
                    email=student.get('email', ''),
                    phone=student.get('phone', ''),
                    department=student.get('department', ''),
                    year=student.get('year'),
                    face_encoding=face_encoding_blob,
                    face_quality_score=face_quality_score
                )
                
                if success:
                    self.db.enroll_student_in_classroom(classroom_id, student['student_id'])
                    
                    if 'image_path' in student:
                        save_path = f"images/registered_students/{classroom_id}/{student['student_id']}.jpg"
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        image = cv2.imread(student['image_path'])
                        cv2.imwrite(save_path, image)
                
                results.append({
                    'student_id': student['student_id'],
                    'success': success,
                    'quality_score': face_quality_score
                })
                
            except Exception as e:
                results.append({
                    'student_id': student.get('student_id', 'Unknown'),
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def mark_attendance_batch(self, frame: np.ndarray) -> List[Dict]:
        """Mark attendance for multiple faces in a single frame"""
        if not self.current_classroom:
            return []
        
        recognized_faces = self.face_recognition.recognize_faces_batch(
            frame,
            self.face_recognition.known_face_encodings,
            self.face_recognition.known_face_metadata
        )
        
        marked_students = []
        
        for face in recognized_faces:
            if face['name'] != 'Unknown':
                student_id = face['student_id']
                
                if student_id not in self.recognized_students:
                    if face.get('spoof_check', {}).get('is_real', True):
                        snapshot_path = self.save_attendance_snapshot(frame, face)
                        
                        success = self.db.mark_attendance(
                            classroom_id=self.current_classroom,
                            student_id=student_id,
                            name=face['name'],
                            status='P',
                            confidence_score=face['confidence'],
                            image_path=snapshot_path
                        )
                        
                        if success:
                            self.recognized_students.add(student_id)
                            marked_students.append({
                                'student_id': student_id,
                                'name': face['name'],
                                'time': datetime.now().strftime('%H:%M:%S'),
                                'confidence': face['confidence'],
                                'quality': face.get('quality', {}).get('overall', 0)
                            })
                            
                            self.db.log_face_recognition(
                                student_id=student_id,
                                recognition_successful=True,
                                confidence_score=face['confidence'],
                                face_quality_score=face.get('quality', {}).get('overall'),
                                spoof_detection_result='REAL'
                            )
                    else:
                        self.db.log_face_recognition(
                            student_id=student_id,
                            recognition_successful=False,
                            confidence_score=face['confidence'],
                            face_quality_score=face.get('quality', {}).get('overall'),
                            spoof_detection_result='SPOOF_DETECTED'
                        )
        
        return marked_students
    
    def save_attendance_snapshot(self, frame: np.ndarray, face_data: Dict) -> str:
        """Save a snapshot of the student when marking attendance"""
        top, right, bottom, left = face_data['location']
        face_image = frame[top:bottom, left:right]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = f"attendance_snapshots/{self.current_classroom}/{datetime.now().strftime('%Y-%m-%d')}"
        os.makedirs(snapshot_dir, exist_ok=True)
        
        snapshot_path = f"{snapshot_dir}/{face_data['student_id']}_{timestamp}.jpg"
        cv2.imwrite(snapshot_path, face_image)
        
        return snapshot_path
    
    def mark_absent_students(self):
        """Mark remaining students as absent for the current session"""
        if not self.current_classroom:
            return []
        
        all_students = self.db.get_classroom_students(self.current_classroom)
        absent_students = []
        
        for student in all_students:
            student_id = student[0]
            if student_id not in self.recognized_students:
                success = self.db.mark_attendance(
                    classroom_id=self.current_classroom,
                    student_id=student_id,
                    name=student[1],
                    status='A'
                )
                if success:
                    absent_students.append({
                        'student_id': student_id,
                        'name': student[1]
                    })
        
        return absent_students
    
    def start_attendance_session(self, classroom_id: str, duration_minutes: int = 10):
        """Start an attendance marking session with a time limit"""
        self.select_classroom(classroom_id)
        self.is_marking_attendance = True
        
        def session_timer():
            time.sleep(duration_minutes * 60)
            self.end_attendance_session()
        
        timer_thread = threading.Thread(target=session_timer)
        timer_thread.daemon = True
        timer_thread.start()
    
    def end_attendance_session(self):
        """End the current attendance session and mark absent students"""
        self.is_marking_attendance = False
        absent_students = self.mark_absent_students()
        return {
            'present': list(self.recognized_students),
            'absent': absent_students,
            'total': len(self.face_recognition.known_face_metadata)
        }
    
    def get_classroom_statistics(self, classroom_id: str, date: str = None) -> Dict:
        """Get attendance statistics for a classroom"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        attendance_records = self.db.get_classroom_attendance(classroom_id, date)
        all_students = self.db.get_classroom_students(classroom_id)
        
        present_count = sum(1 for record in attendance_records if record[3] == 'P')
        absent_count = len(all_students) - present_count
        
        statistics = {
            'classroom_id': classroom_id,
            'date': date,
            'total_students': len(all_students),
            'present': present_count,
            'absent': absent_count,
            'attendance_percentage': (present_count / len(all_students) * 100) if all_students else 0,
            'average_confidence': np.mean([record[4] for record in attendance_records if record[4]]) if attendance_records else 0
        }
        
        return statistics
    
    def generate_attendance_report(self, classroom_id: str, start_date: str = None, end_date: str = None):
        """Generate a comprehensive attendance report for a classroom"""
        statistics = self.db.get_attendance_statistics(classroom_id, start_date, end_date)
        
        report = {
            'classroom_id': classroom_id,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'period': {
                'start': start_date or 'Beginning',
                'end': end_date or datetime.now().strftime('%Y-%m-%d')
            },
            'students': []
        }
        
        for stat in statistics:
            student_report = {
                'student_id': stat[0],
                'name': stat[1],
                'present_days': stat[2],
                'absent_days': stat[3],
                'total_days': stat[4],
                'attendance_percentage': stat[5] if stat[5] else 0
            }
            report['students'].append(student_report)
        
        report['summary'] = {
            'total_students': len(statistics),
            'average_attendance': np.mean([s[5] for s in statistics if s[5]]) if statistics else 0,
            'students_below_75': sum(1 for s in statistics if s[5] and s[5] < 75),
            'students_above_90': sum(1 for s in statistics if s[5] and s[5] > 90)
        }
        
        return report