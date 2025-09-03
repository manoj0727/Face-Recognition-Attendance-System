import sqlite3
from datetime import datetime
import os
import json
import numpy as np

class EnhancedDatabaseManager:
    def __init__(self, db_path='database/attendance_enhanced.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.create_tables()
    
    def create_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classrooms (
                classroom_id TEXT PRIMARY KEY,
                classroom_name TEXT NOT NULL,
                department TEXT,
                semester INTEGER,
                academic_year TEXT,
                instructor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                department TEXT,
                year INTEGER,
                face_encoding BLOB,
                face_quality_score REAL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classroom_students (
                classroom_id TEXT,
                student_id TEXT,
                enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (classroom_id, student_id),
                FOREIGN KEY (classroom_id) REFERENCES classrooms (classroom_id),
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                classroom_id TEXT,
                student_id TEXT,
                name TEXT,
                date TEXT,
                time TEXT,
                status TEXT,
                confidence_score REAL,
                detection_method TEXT,
                image_path TEXT,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (classroom_id),
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_recognition_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                student_id TEXT,
                recognition_successful BOOLEAN,
                confidence_score REAL,
                face_quality_score REAL,
                spoof_detection_result TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_classroom(self, classroom_id, classroom_name, department=None, 
                        semester=None, academic_year=None, instructor=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO classrooms 
                (classroom_id, classroom_name, department, semester, academic_year, instructor)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (classroom_id, classroom_name, department, semester, academic_year, instructor))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def add_student(self, student_id, name, email, phone=None, department=None, 
                   year=None, face_encoding=None, face_quality_score=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO students 
                (student_id, name, email, phone, department, year, face_encoding, face_quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (student_id, name, email, phone, department, year, face_encoding, face_quality_score))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def enroll_student_in_classroom(self, classroom_id, student_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO classroom_students (classroom_id, student_id)
                VALUES (?, ?)
            ''', (classroom_id, student_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def mark_attendance(self, classroom_id, student_id, name, status='P', 
                       confidence_score=None, detection_method='face_recognition', image_path=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date = datetime.now().strftime('%Y-%m-%d')
        time = datetime.now().strftime('%H:%M:%S')
        
        cursor.execute('''
            SELECT * FROM attendance 
            WHERE classroom_id = ? AND student_id = ? AND date = ?
        ''', (classroom_id, student_id, date))
        
        if cursor.fetchone() is None:
            cursor.execute('''
                INSERT INTO attendance 
                (classroom_id, student_id, name, date, time, status, confidence_score, detection_method, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (classroom_id, student_id, name, date, time, status, confidence_score, detection_method, image_path))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    
    def get_classroom_students(self, classroom_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.student_id, s.name, s.email, s.department, s.year, s.face_encoding
            FROM students s
            JOIN classroom_students cs ON s.student_id = cs.student_id
            WHERE cs.classroom_id = ?
        ''', (classroom_id,))
        students = cursor.fetchall()
        conn.close()
        return students
    
    def get_all_classrooms(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT classroom_id, classroom_name, department, semester, academic_year, instructor
            FROM classrooms
            ORDER BY created_at DESC
        ''')
        classrooms = cursor.fetchall()
        conn.close()
        return classrooms
    
    def get_classroom_attendance(self, classroom_id, date=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT student_id, name, time, status, confidence_score
                FROM attendance
                WHERE classroom_id = ? AND date = ?
                ORDER BY time
            ''', (classroom_id, date))
        else:
            cursor.execute('''
                SELECT student_id, name, date, time, status, confidence_score
                FROM attendance
                WHERE classroom_id = ?
                ORDER BY date DESC, time DESC
            ''', (classroom_id,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_student_attendance_summary(self, student_id, classroom_id=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if classroom_id:
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'P' THEN 1 END) as present_count,
                    COUNT(CASE WHEN status = 'A' THEN 1 END) as absent_count,
                    COUNT(*) as total_classes,
                    AVG(CASE WHEN status = 'P' THEN confidence_score END) as avg_confidence
                FROM attendance
                WHERE student_id = ? AND classroom_id = ?
            ''', (student_id, classroom_id))
        else:
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN status = 'P' THEN 1 END) as present_count,
                    COUNT(CASE WHEN status = 'A' THEN 1 END) as absent_count,
                    COUNT(*) as total_classes,
                    AVG(CASE WHEN status = 'P' THEN confidence_score END) as avg_confidence
                FROM attendance
                WHERE student_id = ?
            ''', (student_id,))
        
        summary = cursor.fetchone()
        conn.close()
        return summary
    
    def log_face_recognition(self, student_id, recognition_successful, confidence_score, 
                           face_quality_score=None, spoof_detection_result=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO face_recognition_logs 
            (student_id, recognition_successful, confidence_score, face_quality_score, spoof_detection_result)
            VALUES (?, ?, ?, ?, ?)
        ''', (student_id, recognition_successful, confidence_score, face_quality_score, spoof_detection_result))
        
        conn.commit()
        conn.close()
    
    def get_attendance_statistics(self, classroom_id, start_date=None, end_date=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                s.student_id,
                s.name,
                COUNT(CASE WHEN a.status = 'P' THEN 1 END) as present_days,
                COUNT(CASE WHEN a.status = 'A' THEN 1 END) as absent_days,
                COUNT(DISTINCT a.date) as total_days,
                ROUND(CAST(COUNT(CASE WHEN a.status = 'P' THEN 1 END) AS FLOAT) / 
                      CAST(COUNT(DISTINCT a.date) AS FLOAT) * 100, 2) as attendance_percentage
            FROM students s
            JOIN classroom_students cs ON s.student_id = cs.student_id
            LEFT JOIN attendance a ON s.student_id = a.student_id AND a.classroom_id = cs.classroom_id
            WHERE cs.classroom_id = ?
        '''
        
        params = [classroom_id]
        
        if start_date and end_date:
            query += ' AND a.date BETWEEN ? AND ?'
            params.extend([start_date, end_date])
        
        query += ' GROUP BY s.student_id, s.name ORDER BY s.name'
        
        cursor.execute(query, params)
        statistics = cursor.fetchall()
        conn.close()
        return statistics