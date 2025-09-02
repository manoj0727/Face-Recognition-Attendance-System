import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path='database/attendance.db'):
        self.db_path = db_path
        self.create_tables()
    
    def create_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                department TEXT,
                year INTEGER,
                face_encoding BLOB
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                name TEXT,
                date TEXT,
                time TEXT,
                status TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_student(self, student_id, name, email, department, year, face_encoding):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO students (student_id, name, email, department, year, face_encoding)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, name, email, department, year, face_encoding))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def mark_attendance(self, student_id, name, status='P'):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date = datetime.now().strftime('%Y-%m-%d')
        time = datetime.now().strftime('%H:%M:%S')
        
        cursor.execute('''
            SELECT * FROM attendance 
            WHERE student_id = ? AND date = ?
        ''', (student_id, date))
        
        if cursor.fetchone() is None:
            cursor.execute('''
                INSERT INTO attendance (student_id, name, date, time, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, name, date, time, status))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    
    def get_all_students(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT student_id, name, email, department, year, face_encoding FROM students')
        students = cursor.fetchall()
        conn.close()
        return students
    
    def get_attendance_by_date(self, date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT student_id, name, time, status 
            FROM attendance 
            WHERE date = ?
        ''', (date,))
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_all_attendance(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT student_id, name, date, time, status 
            FROM attendance 
            ORDER BY date DESC, time DESC
        ''')
        records = cursor.fetchall()
        conn.close()
        return records