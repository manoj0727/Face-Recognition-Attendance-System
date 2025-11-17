import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path='database/attendance.db'):
        self.db_path = db_path
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_tables()

    def create_tables(self):
        """Create database tables with proper error handling"""
        conn = None
        try:
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

            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_attendance_date
                ON attendance(date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_attendance_student_date
                ON attendance(student_id, date)
            ''')

            conn.commit()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def add_student(self, student_id, name, email, department, year, face_encoding):
        """Add a student to the database with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO students (student_id, name, email, department, year, face_encoding)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, name, email, department, year, face_encoding))
            conn.commit()
            print(f"✅ Student {student_id} added to database")
            return True
        except sqlite3.IntegrityError as e:
            print(f"⚠️ Student {student_id} already exists: {e}")
            return False
        except Exception as e:
            print(f"❌ Error adding student: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def mark_attendance(self, student_id, name, status='P'):
        """Mark attendance with proper error handling and duplicate prevention"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            date = datetime.now().strftime('%Y-%m-%d')
            time = datetime.now().strftime('%H:%M:%S')

            # Check if already marked today
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
                print(f"✅ Attendance marked for {name} ({student_id})")
                return True
            else:
                print(f"⚠️ Attendance already marked for {student_id} today")
                return False
        except Exception as e:
            print(f"❌ Error marking attendance: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_all_students(self):
        """Get all students with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT student_id, name, email, department, year, face_encoding FROM students')
            students = cursor.fetchall()
            return students
        except Exception as e:
            print(f"❌ Error fetching students: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_attendance_by_date(self, date):
        """Get attendance by date with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT student_id, name, time, status
                FROM attendance
                WHERE date = ?
                ORDER BY time ASC
            ''', (date,))
            records = cursor.fetchall()
            return records
        except Exception as e:
            print(f"❌ Error fetching attendance for {date}: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_all_attendance(self):
        """Get all attendance records with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT student_id, name, date, time, status
                FROM attendance
                ORDER BY date DESC, time DESC
            ''')
            records = cursor.fetchall()
            return records
        except Exception as e:
            print(f"❌ Error fetching all attendance: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def delete_student(self, student_id):
        """Delete student and all their attendance records with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Delete attendance records first (foreign key constraint)
            cursor.execute('DELETE FROM attendance WHERE student_id = ?', (student_id,))
            deleted_attendance = cursor.rowcount

            # Delete student
            cursor.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
            deleted_student = cursor.rowcount

            conn.commit()
            print(f"✅ Deleted student {student_id} ({deleted_attendance} attendance records)")
            return True
        except Exception as e:
            print(f"❌ Error deleting student {student_id}: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()