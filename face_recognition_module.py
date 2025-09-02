import face_recognition
import cv2
import numpy as np
import pickle
import os
from database_manager import DatabaseManager

class FaceRecognitionSystem:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.load_registered_faces()
    
    def load_registered_faces(self):
        students = self.db_manager.get_all_students()
        for student in students:
            student_id, name, _, _, _, face_encoding_blob = student
            if face_encoding_blob:
                face_encoding = pickle.loads(face_encoding_blob)
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(name)
                self.known_face_ids.append(student_id)
    
    def register_face(self, image_path, student_id, name, email, department, year):
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        
        if len(face_encodings) > 0:
            face_encoding = face_encodings[0]
            face_encoding_blob = pickle.dumps(face_encoding)
            
            success = self.db_manager.add_student(
                student_id, name, email, department, year, face_encoding_blob
            )
            
            if success:
                self.known_face_encodings.append(face_encoding)
                self.known_face_names.append(name)
                self.known_face_ids.append(student_id)
                return True, "Student registered successfully!"
            else:
                return False, "Student ID already exists!"
        else:
            return False, "No face detected in the image!"
    
    def recognize_face(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        face_names = []
        face_ids = []
        
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding, tolerance=0.6
            )
            name = "Unknown"
            student_id = None
            
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, face_encoding
            )
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    student_id = self.known_face_ids[best_match_index]
            
            face_names.append(name)
            face_ids.append(student_id)
        
        face_locations = [(top*4, right*4, bottom*4, left*4) 
                          for (top, right, bottom, left) in face_locations]
        
        return face_locations, face_names, face_ids
    
    def draw_faces(self, frame, face_locations, face_names):
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
        
        return frame