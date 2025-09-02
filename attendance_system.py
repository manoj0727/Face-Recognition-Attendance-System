import cv2
from datetime import datetime
from face_recognition_module import FaceRecognitionSystem
from database_manager import DatabaseManager

class AttendanceSystem:
    def __init__(self):
        self.face_recognition = FaceRecognitionSystem()
        self.db_manager = DatabaseManager()
        self.marked_today = set()
        self.load_today_attendance()
    
    def load_today_attendance(self):
        today = datetime.now().strftime('%Y-%m-%d')
        records = self.db_manager.get_attendance_by_date(today)
        for record in records:
            self.marked_today.add(record[0])
    
    def mark_attendance_from_camera(self):
        video_capture = cv2.VideoCapture(0)
        
        print("Press 'q' to quit camera")
        print("Press 's' to take snapshot and mark attendance")
        
        while True:
            ret, frame = video_capture.read()
            
            if not ret:
                print("Failed to grab frame")
                break
            
            face_locations, face_names, face_ids = self.face_recognition.recognize_face(frame)
            
            display_frame = self.face_recognition.draw_faces(frame, face_locations, face_names)
            
            cv2.putText(display_frame, "Press 's' to mark attendance, 'q' to quit", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow('Attendance System', display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):
                for student_id, name in zip(face_ids, face_names):
                    if student_id and student_id not in self.marked_today:
                        success = self.db_manager.mark_attendance(student_id, name, 'P')
                        if success:
                            self.marked_today.add(student_id)
                            print(f"Attendance marked for {name} (ID: {student_id})")
                        else:
                            print(f"Attendance already marked for {name} today")
                    elif student_id and student_id in self.marked_today:
                        print(f"Attendance already marked for {name} today")
            
            elif key == ord('q'):
                break
        
        video_capture.release()
        cv2.destroyAllWindows()
    
    def mark_absent_students(self):
        today = datetime.now().strftime('%Y-%m-%d')
        all_students = self.db_manager.get_all_students()
        
        for student in all_students:
            student_id, name = student[0], student[1]
            if student_id not in self.marked_today:
                self.db_manager.mark_attendance(student_id, name, 'A')
                print(f"Marked absent: {name} (ID: {student_id})")
    
    def get_attendance_summary(self, date=None):
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        records = self.db_manager.get_attendance_by_date(date)
        
        present_count = sum(1 for r in records if r[3] == 'P')
        absent_count = sum(1 for r in records if r[3] == 'A')
        
        return {
            'date': date,
            'present': present_count,
            'absent': absent_count,
            'total': len(records),
            'records': records
        }