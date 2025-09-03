#!/usr/bin/env python3
"""
Simple Face Recognition Attendance System
This version uses OpenCV's built-in face detection instead of dlib/face_recognition
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import numpy as np
import sqlite3
import pandas as pd
from datetime import datetime
import os
import pickle

class SimpleFaceAttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-Powered Classroom Attendance System (OpenCV)")
        self.root.geometry("1200x700")
        
        # Initialize face detector
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        # Database setup
        self.setup_database()
        
        # Camera variables
        self.camera = None
        self.current_frame = None
        
        # Create GUI
        self.create_widgets()
        
        # Load existing face data
        self.load_face_data()
        
    def setup_database(self):
        """Create database tables"""
        os.makedirs('database', exist_ok=True)
        self.conn = sqlite3.connect('database/attendance_opencv.db')
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classrooms (
                classroom_id TEXT PRIMARY KEY,
                classroom_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                classroom_id TEXT,
                face_data BLOB,
                FOREIGN KEY (classroom_id) REFERENCES classrooms (classroom_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                name TEXT,
                classroom_id TEXT,
                date TEXT,
                time TEXT,
                status TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id),
                FOREIGN KEY (classroom_id) REFERENCES classrooms (classroom_id)
            )
        ''')
        
        self.conn.commit()
        
    def create_widgets(self):
        """Create GUI widgets"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tabs
        self.classroom_tab = ttk.Frame(notebook)
        self.register_tab = ttk.Frame(notebook)
        self.attendance_tab = ttk.Frame(notebook)
        self.export_tab = ttk.Frame(notebook)
        
        notebook.add(self.classroom_tab, text="Classrooms")
        notebook.add(self.register_tab, text="Register Student")
        notebook.add(self.attendance_tab, text="Mark Attendance")
        notebook.add(self.export_tab, text="Export")
        
        self.setup_classroom_tab()
        self.setup_register_tab()
        self.setup_attendance_tab()
        self.setup_export_tab()
        
    def setup_classroom_tab(self):
        """Setup classroom management tab"""
        ttk.Label(self.classroom_tab, text="Classroom Management", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        frame = ttk.Frame(self.classroom_tab)
        frame.pack(pady=20)
        
        ttk.Label(frame, text="Classroom ID:").grid(row=0, column=0, padx=5, pady=5)
        self.classroom_id_entry = ttk.Entry(frame, width=30)
        self.classroom_id_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Classroom Name:").grid(row=1, column=0, padx=5, pady=5)
        self.classroom_name_entry = ttk.Entry(frame, width=30)
        self.classroom_name_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(frame, text="Create Classroom", command=self.create_classroom).grid(row=2, column=0, columnspan=2, pady=10)
        
        # List of classrooms
        self.classroom_listbox = tk.Listbox(self.classroom_tab, height=10, width=50)
        self.classroom_listbox.pack(pady=10)
        self.refresh_classrooms()
        
    def setup_register_tab(self):
        """Setup student registration tab"""
        ttk.Label(self.register_tab, text="Student Registration", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        frame = ttk.Frame(self.register_tab)
        frame.pack(pady=20)
        
        # Classroom selection
        ttk.Label(frame, text="Select Classroom:").grid(row=0, column=0, padx=5, pady=5)
        self.register_classroom_var = tk.StringVar()
        self.register_classroom_combo = ttk.Combobox(frame, textvariable=self.register_classroom_var, width=30)
        self.register_classroom_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Student info
        ttk.Label(frame, text="Student ID:").grid(row=1, column=0, padx=5, pady=5)
        self.student_id_entry = ttk.Entry(frame, width=30)
        self.student_id_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Student Name:").grid(row=2, column=0, padx=5, pady=5)
        self.student_name_entry = ttk.Entry(frame, width=30)
        self.student_name_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Camera preview
        self.register_camera_label = ttk.Label(self.register_tab, text="Camera Preview")
        self.register_camera_label.pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(self.register_tab)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Start Camera", command=self.start_register_camera).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Capture Faces", command=self.capture_faces).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Register Student", command=self.register_student).pack(side='left', padx=5)
        
        self.register_status = ttk.Label(self.register_tab, text="")
        self.register_status.pack(pady=10)
        
    def setup_attendance_tab(self):
        """Setup attendance marking tab"""
        ttk.Label(self.attendance_tab, text="Mark Attendance", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        # Classroom selection
        frame = ttk.Frame(self.attendance_tab)
        frame.pack(pady=10)
        
        ttk.Label(frame, text="Select Classroom:").pack(side='left', padx=5)
        self.attendance_classroom_var = tk.StringVar()
        self.attendance_classroom_combo = ttk.Combobox(frame, textvariable=self.attendance_classroom_var, width=30)
        self.attendance_classroom_combo.pack(side='left', padx=5)
        
        # Camera preview
        self.attendance_camera_label = ttk.Label(self.attendance_tab, text="Camera Preview")
        self.attendance_camera_label.pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(self.attendance_tab)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Start Attendance", command=self.start_attendance).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Stop Attendance", command=self.stop_attendance).pack(side='left', padx=5)
        
        # Attendance list
        self.attendance_text = tk.Text(self.attendance_tab, height=10, width=60)
        self.attendance_text.pack(pady=10)
        
    def setup_export_tab(self):
        """Setup export tab"""
        ttk.Label(self.export_tab, text="Export Attendance", font=('Helvetica', 16, 'bold')).pack(pady=10)
        
        frame = ttk.Frame(self.export_tab)
        frame.pack(pady=20)
        
        ttk.Label(frame, text="Select Classroom:").grid(row=0, column=0, padx=5, pady=5)
        self.export_classroom_var = tk.StringVar()
        self.export_classroom_combo = ttk.Combobox(frame, textvariable=self.export_classroom_var, width=30)
        self.export_classroom_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5)
        self.export_date_entry = ttk.Entry(frame, width=30)
        self.export_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.export_date_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(frame, text="Export to Excel", command=self.export_attendance).grid(row=2, column=0, columnspan=2, pady=10)
        
        self.export_status = ttk.Label(self.export_tab, text="")
        self.export_status.pack(pady=10)
        
    def create_classroom(self):
        """Create a new classroom"""
        classroom_id = self.classroom_id_entry.get()
        classroom_name = self.classroom_name_entry.get()
        
        if not classroom_id or not classroom_name:
            messagebox.showwarning("Error", "Please fill all fields")
            return
            
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO classrooms (classroom_id, classroom_name) VALUES (?, ?)",
                         (classroom_id, classroom_name))
            self.conn.commit()
            messagebox.showinfo("Success", "Classroom created successfully!")
            self.classroom_id_entry.delete(0, 'end')
            self.classroom_name_entry.delete(0, 'end')
            self.refresh_classrooms()
            self.update_classroom_combos()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Classroom ID already exists!")
            
    def refresh_classrooms(self):
        """Refresh classroom list"""
        self.classroom_listbox.delete(0, tk.END)
        cursor = self.conn.cursor()
        cursor.execute("SELECT classroom_id, classroom_name FROM classrooms")
        for row in cursor.fetchall():
            self.classroom_listbox.insert(tk.END, f"{row[0]} - {row[1]}")
        self.update_classroom_combos()
        
    def update_classroom_combos(self):
        """Update classroom comboboxes"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT classroom_id, classroom_name FROM classrooms")
        classrooms = [f"{row[0]} - {row[1]}" for row in cursor.fetchall()]
        
        if hasattr(self, 'register_classroom_combo'):
            self.register_classroom_combo['values'] = classrooms
        if hasattr(self, 'attendance_classroom_combo'):
            self.attendance_classroom_combo['values'] = classrooms
        if hasattr(self, 'export_classroom_combo'):
            self.export_classroom_combo['values'] = classrooms
        
    def start_register_camera(self):
        """Start camera for registration"""
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            self.update_register_camera()
            
    def update_register_camera(self):
        """Update camera preview for registration"""
        if self.camera:
            ret, frame = self.camera.read()
            if ret:
                self.current_frame = frame
                
                # Detect faces
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                # Draw rectangles
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Convert to PhotoImage
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (400, 300))
                photo = ImageTk.PhotoImage(Image.fromarray(frame))
                self.register_camera_label.configure(image=photo)
                self.register_camera_label.image = photo
                
            self.root.after(10, self.update_register_camera)
            
    def capture_faces(self):
        """Capture faces for training"""
        if self.current_frame is None:
            messagebox.showwarning("Error", "Please start camera first")
            return
            
        student_id = self.student_id_entry.get()
        if not student_id:
            messagebox.showwarning("Error", "Please enter student ID")
            return
            
        # Create directory for face images
        os.makedirs(f'faces/{student_id}', exist_ok=True)
        
        # Capture multiple images
        self.captured_faces = []
        count = 0
        
        messagebox.showinfo("Info", "Please move your face slowly. Capturing 30 images...")
        
        for i in range(30):
            ret, frame = self.camera.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    face_img = gray[y:y+h, x:x+w]
                    face_img = cv2.resize(face_img, (100, 100))
                    self.captured_faces.append(face_img)
                    cv2.imwrite(f'faces/{student_id}/face_{count}.jpg', face_img)
                    count += 1
                    
                cv2.waitKey(100)
                
        self.register_status.config(text=f"Captured {count} face images")
        
    def register_student(self):
        """Register student with face data"""
        student_id = self.student_id_entry.get()
        student_name = self.student_name_entry.get()
        classroom = self.register_classroom_var.get()
        
        if not all([student_id, student_name, classroom]):
            messagebox.showwarning("Error", "Please fill all fields")
            return
            
        classroom_id = classroom.split(' - ')[0]
        
        if not hasattr(self, 'captured_faces') or not self.captured_faces:
            messagebox.showwarning("Error", "Please capture faces first")
            return
            
        # Train face recognizer
        labels = [hash(student_id) % 1000000 for _ in self.captured_faces]
        
        # Save to database
        cursor = self.conn.cursor()
        try:
            face_data = pickle.dumps((self.captured_faces, labels[0]))
            cursor.execute("INSERT INTO students (student_id, name, classroom_id, face_data) VALUES (?, ?, ?, ?)",
                         (student_id, student_name, classroom_id, face_data))
            self.conn.commit()
            
            # Update face recognizer
            self.load_face_data()
            
            messagebox.showinfo("Success", f"Student {student_name} registered successfully!")
            
            # Clear fields
            self.student_id_entry.delete(0, 'end')
            self.student_name_entry.delete(0, 'end')
            self.register_status.config(text="")
            self.captured_faces = []
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Student ID already exists!")
            
    def load_face_data(self):
        """Load all face data for recognition"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT student_id, name, face_data FROM students WHERE face_data IS NOT NULL")
        
        all_faces = []
        all_labels = []
        self.student_mapping = {}
        
        for student_id, name, face_data in cursor.fetchall():
            if face_data:
                faces, label = pickle.loads(face_data)
                all_faces.extend(faces)
                all_labels.extend([label] * len(faces))
                self.student_mapping[label] = (student_id, name)
                
        if all_faces:
            self.face_recognizer.train(all_faces, np.array(all_labels))
            
    def start_attendance(self):
        """Start attendance marking"""
        classroom = self.attendance_classroom_var.get()
        
        if not classroom:
            messagebox.showwarning("Error", "Please select a classroom")
            return
            
        self.current_classroom_id = classroom.split(' - ')[0]
        self.marked_students = set()
        
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            
        self.marking_attendance = True
        self.attendance_text.delete('1.0', 'end')
        self.attendance_text.insert('1.0', "Attendance Session Started\n" + "="*40 + "\n")
        self.update_attendance_camera()
        
    def update_attendance_camera(self):
        """Update camera for attendance marking"""
        if hasattr(self, 'marking_attendance') and self.marking_attendance and self.camera:
            ret, frame = self.camera.read()
            if ret:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    face_img = gray[y:y+h, x:x+w]
                    face_img = cv2.resize(face_img, (100, 100))
                    
                    try:
                        label, confidence = self.face_recognizer.predict(face_img)
                        
                        if confidence < 70 and label in self.student_mapping:
                            student_id, name = self.student_mapping[label]
                            
                            if student_id not in self.marked_students:
                                self.mark_attendance(student_id, name)
                                self.marked_students.add(student_id)
                                
                            # Draw rectangle and name
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            cv2.putText(frame, name, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        else:
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                            cv2.putText(frame, "Unknown", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    except:
                        pass
                        
                # Convert to PhotoImage
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (400, 300))
                photo = ImageTk.PhotoImage(Image.fromarray(frame))
                self.attendance_camera_label.configure(image=photo)
                self.attendance_camera_label.image = photo
                
            self.root.after(10, self.update_attendance_camera)
            
    def mark_attendance(self, student_id, name):
        """Mark attendance for a student"""
        date = datetime.now().strftime('%Y-%m-%d')
        time = datetime.now().strftime('%H:%M:%S')
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO attendance (student_id, name, classroom_id, date, time, status) VALUES (?, ?, ?, ?, ?, ?)",
                      (student_id, name, self.current_classroom_id, date, time, 'P'))
        self.conn.commit()
        
        self.attendance_text.insert('end', f"{time} - {name} ({student_id}) - Present\n")
        
    def stop_attendance(self):
        """Stop attendance marking"""
        if hasattr(self, 'marking_attendance'):
            self.marking_attendance = False
            self.attendance_text.insert('end', "\n" + "="*40 + "\nAttendance Session Ended\n")
            messagebox.showinfo("Info", f"Marked attendance for {len(self.marked_students)} students")
            
    def export_attendance(self):
        """Export attendance to Excel"""
        classroom = self.export_classroom_var.get()
        date = self.export_date_entry.get()
        
        if not classroom or not date:
            messagebox.showwarning("Error", "Please select classroom and date")
            return
            
        classroom_id = classroom.split(' - ')[0]
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT student_id, name, time, status 
            FROM attendance 
            WHERE classroom_id = ? AND date = ?
        """, (classroom_id, date))
        
        data = cursor.fetchall()
        
        if not data:
            messagebox.showinfo("Info", "No attendance records found")
            return
            
        # Create DataFrame
        df = pd.DataFrame(data, columns=['Student ID', 'Name', 'Time', 'Status'])
        
        # Export to Excel
        os.makedirs('exports', exist_ok=True)
        filename = f'exports/attendance_{classroom_id}_{date}.xlsx'
        df.to_excel(filename, index=False)
        
        self.export_status.config(text=f"Exported to {filename}")
        messagebox.showinfo("Success", f"Attendance exported to {filename}")
        
    def __del__(self):
        """Cleanup"""
        if self.camera:
            self.camera.release()
        if hasattr(self, 'conn'):
            self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleFaceAttendanceApp(root)
    root.mainloop()