import cv2
import face_recognition
import numpy as np
from typing import List, Tuple, Optional, Dict
import mediapipe as mp
import pickle
from datetime import datetime
import os

class EnhancedFaceRecognition:
    def __init__(self, model='hog', tolerance=0.6):
        self.model = model
        self.tolerance = tolerance
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=10,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        self.known_face_encodings = []
        self.known_face_metadata = []
        self.frame_skip = 2
        self.frame_count = 0
        
    def detect_faces_batch(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect multiple faces in a single frame efficiently"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model=self.model)
        return face_locations
    
    def encode_faces_batch(self, frame: np.ndarray, face_locations: List) -> np.ndarray:
        """Encode multiple faces in parallel"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        return face_encodings
    
    def check_face_quality(self, face_image: np.ndarray) -> Dict[str, float]:
        """Check face image quality for better recognition"""
        quality_metrics = {}
        
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        quality_metrics['sharpness'] = min(laplacian_var / 100, 1.0)
        
        brightness = np.mean(gray)
        quality_metrics['brightness'] = 1.0 - abs(brightness - 127.5) / 127.5
        
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()
        entropy = -np.sum(hist * np.log2(hist + 1e-7))
        quality_metrics['contrast'] = entropy / 8
        
        height, width = face_image.shape[:2]
        min_size = 100
        quality_metrics['resolution'] = min((min(height, width) / min_size), 1.0)
        
        quality_metrics['overall'] = np.mean(list(quality_metrics.values()))
        
        return quality_metrics
    
    def detect_spoof_attempt(self, frame: np.ndarray, face_location: Tuple) -> Dict[str, any]:
        """Detect potential spoofing attempts using multiple techniques"""
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        
        spoof_results = {
            'is_real': True,
            'confidence': 1.0,
            'checks': {}
        }
        
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        texture_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        spoof_results['checks']['texture'] = texture_score > 20
        
        results = self.face_mesh.process(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0]
            spoof_results['checks']['3d_landmarks'] = True
            
            points_3d = []
            for idx in [1, 33, 61, 199, 263, 291]:
                if idx < len(landmarks.landmark):
                    lm = landmarks.landmark[idx]
                    points_3d.append([lm.x, lm.y, lm.z])
            
            if len(points_3d) >= 4:
                points_3d = np.array(points_3d, dtype=np.float32)
                depth_variance = np.var(points_3d[:, 2])
                spoof_results['checks']['depth_variance'] = depth_variance > 0.001
        else:
            spoof_results['checks']['3d_landmarks'] = False
        
        hist = cv2.calcHist([face_image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        hist_score = cv2.compareHist(hist, hist, cv2.HISTCMP_CHISQR)
        spoof_results['checks']['color_distribution'] = hist_score < 100
        
        failed_checks = sum(1 for check in spoof_results['checks'].values() if not check)
        spoof_results['confidence'] = 1.0 - (failed_checks / len(spoof_results['checks']))
        spoof_results['is_real'] = spoof_results['confidence'] > 0.5
        
        return spoof_results
    
    def recognize_faces_batch(self, frame: np.ndarray, known_encodings: List, 
                            known_metadata: List, threshold: float = None) -> List[Dict]:
        """Recognize multiple faces in a single frame"""
        if threshold is None:
            threshold = self.tolerance
        
        face_locations = self.detect_faces_batch(frame)
        face_encodings = self.encode_faces_batch(frame, face_locations)
        
        recognized_faces = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            if len(known_encodings) == 0:
                recognized_faces.append({
                    'location': face_location,
                    'name': 'Unknown',
                    'confidence': 0.0,
                    'metadata': None
                })
                continue
            
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            confidence = 1.0 - face_distances[best_match_index]
            
            if face_distances[best_match_index] < threshold:
                quality = self.check_face_quality(frame[face_location[0]:face_location[2], 
                                                       face_location[3]:face_location[1]])
                spoof_check = self.detect_spoof_attempt(frame, face_location)
                
                recognized_faces.append({
                    'location': face_location,
                    'name': known_metadata[best_match_index]['name'],
                    'student_id': known_metadata[best_match_index]['student_id'],
                    'confidence': confidence,
                    'quality': quality,
                    'spoof_check': spoof_check,
                    'metadata': known_metadata[best_match_index]
                })
            else:
                recognized_faces.append({
                    'location': face_location,
                    'name': 'Unknown',
                    'confidence': 0.0,
                    'metadata': None
                })
        
        return recognized_faces
    
    def add_known_face(self, face_encoding: np.ndarray, metadata: Dict):
        """Add a new face to the known faces database"""
        self.known_face_encodings.append(face_encoding)
        self.known_face_metadata.append(metadata)
    
    def load_classroom_faces(self, students_data: List):
        """Load faces for all students in a classroom"""
        self.known_face_encodings = []
        self.known_face_metadata = []
        
        for student in students_data:
            if student[5]:  # face_encoding exists
                encoding = pickle.loads(student[5])
                self.known_face_encodings.append(encoding)
                self.known_face_metadata.append({
                    'student_id': student[0],
                    'name': student[1],
                    'email': student[2],
                    'department': student[3],
                    'year': student[4]
                })
    
    def capture_and_encode_face(self, image_path: str = None, camera_capture: np.ndarray = None) -> Tuple[np.ndarray, Dict]:
        """Capture and encode a face from image or camera"""
        if image_path:
            image = cv2.imread(image_path)
        elif camera_capture is not None:
            image = camera_capture
        else:
            raise ValueError("Either image_path or camera_capture must be provided")
        
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        
        if not face_locations:
            return None, {'error': 'No face detected'}
        
        if len(face_locations) > 1:
            return None, {'error': 'Multiple faces detected'}
        
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        face_location = face_locations[0]
        
        quality = self.check_face_quality(image[face_location[0]:face_location[2], 
                                               face_location[3]:face_location[1]])
        
        if quality['overall'] < 0.5:
            return None, {'error': 'Poor image quality', 'quality': quality}
        
        return face_encodings[0], {'quality': quality, 'location': face_location}
    
    def draw_recognition_results(self, frame: np.ndarray, recognized_faces: List[Dict]) -> np.ndarray:
        """Draw bounding boxes and labels on the frame"""
        for face in recognized_faces:
            top, right, bottom, left = face['location']
            
            if face['name'] != 'Unknown':
                color = (0, 255, 0) if face.get('spoof_check', {}).get('is_real', True) else (0, 0, 255)
                label = f"{face['name']} ({face['confidence']:.2f})"
                
                if not face.get('spoof_check', {}).get('is_real', True):
                    label += " [SPOOF WARNING]"
            else:
                color = (255, 0, 0)
                label = "Unknown"
            
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, label, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
            
            if face.get('quality'):
                quality_text = f"Q: {face['quality']['overall']:.2f}"
                cv2.putText(frame, quality_text, (left, top - 10), font, 0.5, color, 1)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, (10, frame.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def process_video_stream(self, cap: cv2.VideoCapture, callback=None):
        """Process video stream with optimized performance"""
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            self.frame_count += 1
            
            if self.frame_count % self.frame_skip == 0:
                recognized_faces = self.recognize_faces_batch(
                    frame, 
                    self.known_face_encodings, 
                    self.known_face_metadata
                )
                
                if callback:
                    callback(recognized_faces)
                
                frame = self.draw_recognition_results(frame, recognized_faces)
            
            yield frame