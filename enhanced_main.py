#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import os
from datetime import datetime
from classroom_attendance_system import ClassroomAttendanceSystem
from enhanced_database_manager import EnhancedDatabaseManager
from enhanced_excel_export import EnhancedExcelExporter

class EnhancedAttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI-Powered Classroom Attendance System")
        self.root.geometry("1400x800")
        
        self.system = ClassroomAttendanceSystem()
        self.db = EnhancedDatabaseManager()
        self.exporter = EnhancedExcelExporter(self.db)
        
        self.camera = None
        self.camera_running = False
        self.current_frame = None
        
        self.setup_styles()
        self.create_widgets()
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Warning.TLabel', foreground='orange')
        
    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.classroom_tab = ttk.Frame(notebook)
        self.register_tab = ttk.Frame(notebook)
        self.attendance_tab = ttk.Frame(notebook)
        self.records_tab = ttk.Frame(notebook)
        self.analytics_tab = ttk.Frame(notebook)
        self.export_tab = ttk.Frame(notebook)
        
        notebook.add(self.classroom_tab, text="Classroom Management")
        notebook.add(self.register_tab, text="Student Registration")
        notebook.add(self.attendance_tab, text="Mark Attendance")
        notebook.add(self.records_tab, text="View Records")
        notebook.add(self.analytics_tab, text="Analytics")
        notebook.add(self.export_tab, text="Export Data")
        
        self.setup_classroom_tab()
        self.setup_register_tab()
        self.setup_attendance_tab()
        self.setup_records_tab()
        self.setup_analytics_tab()
        self.setup_export_tab()
        
        # Update combos after all tabs are created
        self.update_classroom_combo()
        
    def setup_classroom_tab(self):
        ttk.Label(self.classroom_tab, text="Classroom Management", style='Title.TLabel').pack(pady=10)
        
        main_frame = ttk.Frame(self.classroom_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        create_frame = ttk.LabelFrame(main_frame, text="Create New Classroom")
        create_frame.pack(fill='x', pady=10)
        
        fields_frame = ttk.Frame(create_frame)
        fields_frame.pack(padx=10, pady=10)
        
        ttk.Label(fields_frame, text="Classroom ID:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.classroom_id_entry = ttk.Entry(fields_frame, width=30)
        self.classroom_id_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(fields_frame, text="Classroom Name:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.classroom_name_entry = ttk.Entry(fields_frame, width=30)
        self.classroom_name_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(fields_frame, text="Department:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.department_entry = ttk.Entry(fields_frame, width=30)
        self.department_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(fields_frame, text="Semester:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.semester_entry = ttk.Entry(fields_frame, width=30)
        self.semester_entry.grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Label(fields_frame, text="Academic Year:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.academic_year_entry = ttk.Entry(fields_frame, width=30)
        self.academic_year_entry.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(fields_frame, text="Instructor:").grid(row=2, column=2, sticky='w', padx=5, pady=5)
        self.instructor_entry = ttk.Entry(fields_frame, width=30)
        self.instructor_entry.grid(row=2, column=3, padx=5, pady=5)
        
        ttk.Button(create_frame, text="Create Classroom", command=self.create_classroom).pack(pady=10)
        
        list_frame = ttk.LabelFrame(main_frame, text="Existing Classrooms")
        list_frame.pack(fill='both', expand=True, pady=10)
        
        columns = ('ID', 'Name', 'Department', 'Semester', 'Year', 'Instructor')
        self.classroom_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.classroom_tree.heading(col, text=col)
            self.classroom_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.classroom_tree.yview)
        self.classroom_tree.configure(yscrollcommand=scrollbar.set)
        
        self.classroom_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')
        
        self.refresh_classroom_list()
        
    def setup_register_tab(self):
        ttk.Label(self.register_tab, text="Student Registration", style='Title.TLabel').pack(pady=10)
        
        selection_frame = ttk.Frame(self.register_tab)
        selection_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(selection_frame, text="Select Classroom:").pack(side='left', padx=5)
        self.register_classroom_var = tk.StringVar()
        self.register_classroom_combo = ttk.Combobox(selection_frame, textvariable=self.register_classroom_var, width=40)
        self.register_classroom_combo.pack(side='left', padx=5)
        
        main_frame = ttk.Frame(self.register_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        left_frame = ttk.LabelFrame(main_frame, text="Student Information")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        fields = [
            ("Student ID:", "student_id"),
            ("Name:", "name"),
            ("Email:", "email"),
            ("Phone:", "phone"),
            ("Department:", "dept"),
            ("Year:", "year")
        ]
        
        self.register_entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(left_frame, text=label).grid(row=i, column=0, sticky='w', padx=10, pady=5)
            entry = ttk.Entry(left_frame, width=30)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.register_entries[key] = entry
        
        right_frame = ttk.LabelFrame(main_frame, text="Face Capture")
        right_frame.pack(side='right', fill='both', expand=True)
        
        self.register_image_label = ttk.Label(right_frame, text="No image captured")
        self.register_image_label.pack(padx=10, pady=10)
        
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Open Camera", command=self.open_register_camera).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Capture Face", command=self.capture_register_face).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Upload Image", command=self.upload_image).pack(side='left', padx=5)
        
        ttk.Button(self.register_tab, text="Register Student", command=self.register_student, 
                  style='Accent.TButton').pack(pady=20)
        
        self.register_status_label = ttk.Label(self.register_tab, text="")
        self.register_status_label.pack(pady=10)
        
    def setup_attendance_tab(self):
        ttk.Label(self.attendance_tab, text="Mark Attendance", style='Title.TLabel').pack(pady=10)
        
        control_frame = ttk.Frame(self.attendance_tab)
        control_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(control_frame, text="Select Classroom:").pack(side='left', padx=5)
        self.attendance_classroom_var = tk.StringVar()
        self.attendance_classroom_combo = ttk.Combobox(control_frame, textvariable=self.attendance_classroom_var, width=40)
        self.attendance_classroom_combo.pack(side='left', padx=5)
        self.attendance_classroom_combo.bind('<<ComboboxSelected>>', self.on_classroom_selected)
        
        ttk.Button(control_frame, text="Start Session", command=self.start_attendance_session).pack(side='left', padx=10)
        ttk.Button(control_frame, text="End Session", command=self.end_attendance_session).pack(side='left', padx=5)
        
        main_frame = ttk.Frame(self.attendance_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Feed")
        camera_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        self.attendance_camera_label = ttk.Label(camera_frame, text="Camera not started")
        self.attendance_camera_label.pack(padx=10, pady=10)
        
        info_frame = ttk.LabelFrame(main_frame, text="Attendance Information")
        info_frame.pack(side='right', fill='both', expand=True)
        
        ttk.Label(info_frame, text="Session Status:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=10, pady=5)
        self.session_status_label = ttk.Label(info_frame, text="No session active")
        self.session_status_label.grid(row=0, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(info_frame, text="Students Loaded:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=10, pady=5)
        self.students_loaded_label = ttk.Label(info_frame, text="0")
        self.students_loaded_label.grid(row=1, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(info_frame, text="Present:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky='w', padx=10, pady=5)
        self.present_count_label = ttk.Label(info_frame, text="0", foreground='green')
        self.present_count_label.grid(row=2, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(info_frame, text="Recently Marked:", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, sticky='w', padx=10, pady=5)
        
        self.recent_list = tk.Listbox(info_frame, height=15, width=40)
        self.recent_list.grid(row=4, column=0, columnspan=2, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(info_frame, orient='vertical', command=self.recent_list.yview)
        scrollbar.grid(row=4, column=2, sticky='ns')
        self.recent_list.configure(yscrollcommand=scrollbar.set)
        
    def setup_records_tab(self):
        ttk.Label(self.records_tab, text="Attendance Records", style='Title.TLabel').pack(pady=10)
        
        filter_frame = ttk.Frame(self.records_tab)
        filter_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(filter_frame, text="Classroom:").pack(side='left', padx=5)
        self.records_classroom_var = tk.StringVar()
        self.records_classroom_combo = ttk.Combobox(filter_frame, textvariable=self.records_classroom_var, width=30)
        self.records_classroom_combo.pack(side='left', padx=5)
        
        ttk.Label(filter_frame, text="Date:").pack(side='left', padx=5)
        self.records_date_entry = ttk.Entry(filter_frame, width=15)
        self.records_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.records_date_entry.pack(side='left', padx=5)
        
        ttk.Button(filter_frame, text="Load Records", command=self.load_records).pack(side='left', padx=10)
        ttk.Button(filter_frame, text="Load All", command=self.load_all_records).pack(side='left', padx=5)
        
        columns = ('Student ID', 'Name', 'Date', 'Time', 'Status', 'Confidence')
        self.records_tree = ttk.Treeview(self.records_tab, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.records_tree.heading(col, text=col)
            self.records_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(self.records_tab, orient='vertical', command=self.records_tree.yview)
        self.records_tree.configure(yscrollcommand=scrollbar.set)
        
        self.records_tree.pack(side='left', fill='both', expand=True, padx=20, pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
        
    def setup_analytics_tab(self):
        ttk.Label(self.analytics_tab, text="Attendance Analytics", style='Title.TLabel').pack(pady=10)
        
        filter_frame = ttk.Frame(self.analytics_tab)
        filter_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(filter_frame, text="Classroom:").pack(side='left', padx=5)
        self.analytics_classroom_var = tk.StringVar()
        self.analytics_classroom_combo = ttk.Combobox(filter_frame, textvariable=self.analytics_classroom_var, width=30)
        self.analytics_classroom_combo.pack(side='left', padx=5)
        
        ttk.Button(filter_frame, text="Generate Analytics", command=self.generate_analytics).pack(side='left', padx=10)
        
        self.analytics_text = tk.Text(self.analytics_tab, height=25, width=100, wrap='word')
        self.analytics_text.pack(padx=20, pady=10, fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(self.analytics_text, orient='vertical', command=self.analytics_text.yview)
        self.analytics_text.configure(yscrollcommand=scrollbar.set)
        
    def setup_export_tab(self):
        ttk.Label(self.export_tab, text="Export Attendance Data", style='Title.TLabel').pack(pady=10)
        
        export_frame = ttk.LabelFrame(self.export_tab, text="Export Options")
        export_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        ttk.Label(export_frame, text="Select Classroom:").grid(row=0, column=0, sticky='w', padx=10, pady=10)
        self.export_classroom_var = tk.StringVar()
        self.export_classroom_combo = ttk.Combobox(export_frame, textvariable=self.export_classroom_var, width=40)
        self.export_classroom_combo.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(export_frame, text="Export Type:").grid(row=1, column=0, sticky='w', padx=10, pady=10)
        self.export_type_var = tk.StringVar(value="complete")
        export_types = [
            ("Complete Attendance with Analytics", "complete"),
            ("Today's Attendance", "today"),
            ("Specific Date", "date")
        ]
        
        for i, (text, value) in enumerate(export_types):
            ttk.Radiobutton(export_frame, text=text, variable=self.export_type_var, 
                          value=value).grid(row=2+i, column=1, sticky='w', padx=10, pady=5)
        
        ttk.Label(export_frame, text="Date (for specific date):").grid(row=5, column=0, sticky='w', padx=10, pady=10)
        self.export_date_entry = ttk.Entry(export_frame, width=15)
        self.export_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.export_date_entry.grid(row=5, column=1, sticky='w', padx=10, pady=10)
        
        self.include_analytics_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_frame, text="Include Analytics and Charts", 
                       variable=self.include_analytics_var).grid(row=6, column=1, sticky='w', padx=10, pady=10)
        
        ttk.Button(export_frame, text="Export to Excel", command=self.export_data, 
                  style='Accent.TButton').grid(row=7, column=1, pady=20)
        
        self.export_status_label = ttk.Label(export_frame, text="")
        self.export_status_label.grid(row=8, column=0, columnspan=2, pady=10)
        
    def create_classroom(self):
        classroom_id = self.classroom_id_entry.get()
        classroom_name = self.classroom_name_entry.get()
        
        if not classroom_id or not classroom_name:
            messagebox.showwarning("Input Error", "Classroom ID and Name are required!")
            return
        
        success = self.db.create_classroom(
            classroom_id=classroom_id,
            classroom_name=classroom_name,
            department=self.department_entry.get(),
            semester=self.semester_entry.get(),
            academic_year=self.academic_year_entry.get(),
            instructor=self.instructor_entry.get()
        )
        
        if success:
            messagebox.showinfo("Success", f"Classroom '{classroom_name}' created successfully!")
            self.clear_classroom_fields()
            self.refresh_classroom_list()
            self.update_classroom_combo()
        else:
            messagebox.showerror("Error", "Classroom ID already exists!")
    
    def clear_classroom_fields(self):
        self.classroom_id_entry.delete(0, 'end')
        self.classroom_name_entry.delete(0, 'end')
        self.department_entry.delete(0, 'end')
        self.semester_entry.delete(0, 'end')
        self.academic_year_entry.delete(0, 'end')
        self.instructor_entry.delete(0, 'end')
    
    def refresh_classroom_list(self):
        for item in self.classroom_tree.get_children():
            self.classroom_tree.delete(item)
        
        classrooms = self.db.get_all_classrooms()
        for classroom in classrooms:
            self.classroom_tree.insert('', 'end', values=classroom)
    
    def update_classroom_combo(self):
        classrooms = self.db.get_all_classrooms()
        classroom_list = [f"{c[0]} - {c[1]}" for c in classrooms]
        
        self.register_classroom_combo['values'] = classroom_list
        self.attendance_classroom_combo['values'] = classroom_list
        self.records_classroom_combo['values'] = classroom_list
        self.analytics_classroom_combo['values'] = classroom_list
        self.export_classroom_combo['values'] = classroom_list
    
    def open_register_camera(self):
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
            self.camera_running = True
            self.update_register_camera()
    
    def update_register_camera(self):
        if self.camera_running and self.camera:
            ret, frame = self.camera.read()
            if ret:
                self.current_frame = frame
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (400, 300))
                photo = ImageTk.PhotoImage(Image.fromarray(frame))
                self.register_image_label.configure(image=photo, text="")
                self.register_image_label.image = photo
                self.root.after(10, self.update_register_camera)
    
    def capture_register_face(self):
        if self.current_frame is not None:
            self.camera_running = False
            self.captured_frame = self.current_frame.copy()
            self.register_status_label.configure(text="Face captured!", style='Success.TLabel')
    
    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            self.uploaded_image_path = file_path
            image = Image.open(file_path)
            image = image.resize((400, 300))
            photo = ImageTk.PhotoImage(image)
            self.register_image_label.configure(image=photo, text="")
            self.register_image_label.image = photo
            self.register_status_label.configure(text="Image uploaded!", style='Success.TLabel')
    
    def register_student(self):
        classroom_id = self.register_classroom_var.get().split(' - ')[0] if self.register_classroom_var.get() else None
        
        if not classroom_id:
            messagebox.showwarning("Input Error", "Please select a classroom!")
            return
        
        student_data = {
            'student_id': self.register_entries['student_id'].get(),
            'name': self.register_entries['name'].get(),
            'email': self.register_entries['email'].get(),
            'phone': self.register_entries['phone'].get(),
            'department': self.register_entries['dept'].get(),
            'year': self.register_entries['year'].get()
        }
        
        if not student_data['student_id'] or not student_data['name']:
            messagebox.showwarning("Input Error", "Student ID and Name are required!")
            return
        
        if hasattr(self, 'captured_frame'):
            student_data['camera_frame'] = self.captured_frame
            results = self.system.register_student_batch(classroom_id, [student_data], 'camera')
        elif hasattr(self, 'uploaded_image_path'):
            student_data['image_path'] = self.uploaded_image_path
            results = self.system.register_student_batch(classroom_id, [student_data], 'upload')
        else:
            messagebox.showwarning("Input Error", "Please capture or upload a face image!")
            return
        
        if results[0]['success']:
            messagebox.showinfo("Success", f"Student registered successfully!\nQuality Score: {results[0]['quality_score']:.2f}")
            self.clear_register_fields()
        else:
            messagebox.showerror("Error", f"Registration failed: {results[0].get('error', 'Unknown error')}")
    
    def clear_register_fields(self):
        for entry in self.register_entries.values():
            entry.delete(0, 'end')
        self.register_image_label.configure(image='', text="No image captured")
        self.register_status_label.configure(text="")
        if hasattr(self, 'captured_frame'):
            delattr(self, 'captured_frame')
        if hasattr(self, 'uploaded_image_path'):
            delattr(self, 'uploaded_image_path')
    
    def on_classroom_selected(self, event=None):
        classroom_id = self.attendance_classroom_var.get().split(' - ')[0] if self.attendance_classroom_var.get() else None
        if classroom_id:
            num_students = self.system.select_classroom(classroom_id)
            self.students_loaded_label.configure(text=str(num_students))
    
    def start_attendance_session(self):
        classroom_id = self.attendance_classroom_var.get().split(' - ')[0] if self.attendance_classroom_var.get() else None
        
        if not classroom_id:
            messagebox.showwarning("Input Error", "Please select a classroom!")
            return
        
        self.system.start_attendance_session(classroom_id)
        self.session_status_label.configure(text="Session Active", foreground='green')
        
        if self.camera is None:
            self.camera = cv2.VideoCapture(0)
        
        self.attendance_running = True
        threading.Thread(target=self.process_attendance_video, daemon=True).start()
    
    def process_attendance_video(self):
        while self.attendance_running:
            ret, frame = self.camera.read()
            if ret:
                marked_students = self.system.mark_attendance_batch(frame)
                
                for student in marked_students:
                    self.recent_list.insert(0, f"{student['time']} - {student['name']} (Confidence: {student['confidence']:.2f})")
                    self.present_count_label.configure(text=str(len(self.system.recognized_students)))
                
                frame_with_boxes = self.system.face_recognition.draw_recognition_results(
                    frame, 
                    self.system.face_recognition.recognize_faces_batch(
                        frame,
                        self.system.face_recognition.known_face_encodings,
                        self.system.face_recognition.known_face_metadata
                    )
                )
                
                frame_rgb = cv2.cvtColor(frame_with_boxes, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (640, 480))
                photo = ImageTk.PhotoImage(Image.fromarray(frame_resized))
                
                self.attendance_camera_label.configure(image=photo, text="")
                self.attendance_camera_label.image = photo
    
    def end_attendance_session(self):
        self.attendance_running = False
        result = self.system.end_attendance_session()
        self.session_status_label.configure(text="Session Ended", foreground='red')
        
        messagebox.showinfo("Session Complete", 
                          f"Attendance marked:\nPresent: {len(result['present'])}\nAbsent: {len(result['absent'])}\nTotal: {result['total']}")
    
    def load_records(self):
        classroom_id = self.records_classroom_var.get().split(' - ')[0] if self.records_classroom_var.get() else None
        date = self.records_date_entry.get()
        
        if not classroom_id:
            messagebox.showwarning("Input Error", "Please select a classroom!")
            return
        
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        records = self.db.get_classroom_attendance(classroom_id, date)
        for record in records:
            self.records_tree.insert('', 'end', values=record)
    
    def load_all_records(self):
        classroom_id = self.records_classroom_var.get().split(' - ')[0] if self.records_classroom_var.get() else None
        
        if not classroom_id:
            messagebox.showwarning("Input Error", "Please select a classroom!")
            return
        
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        records = self.db.get_classroom_attendance(classroom_id)
        for record in records:
            self.records_tree.insert('', 'end', values=record)
    
    def generate_analytics(self):
        classroom_id = self.analytics_classroom_var.get().split(' - ')[0] if self.analytics_classroom_var.get() else None
        
        if not classroom_id:
            messagebox.showwarning("Input Error", "Please select a classroom!")
            return
        
        report = self.system.generate_attendance_report(classroom_id)
        
        self.analytics_text.delete('1.0', 'end')
        self.analytics_text.insert('1.0', f"Attendance Analytics Report\n{'='*50}\n\n")
        self.analytics_text.insert('end', f"Classroom: {classroom_id}\n")
        self.analytics_text.insert('end', f"Generated: {report['report_date']}\n")
        self.analytics_text.insert('end', f"Period: {report['period']['start']} to {report['period']['end']}\n\n")
        
        self.analytics_text.insert('end', f"Summary Statistics\n{'-'*30}\n")
        self.analytics_text.insert('end', f"Total Students: {report['summary']['total_students']}\n")
        self.analytics_text.insert('end', f"Average Attendance: {report['summary']['average_attendance']:.2f}%\n")
        self.analytics_text.insert('end', f"Students Above 90%: {report['summary']['students_above_90']}\n")
        self.analytics_text.insert('end', f"Students Below 75%: {report['summary']['students_below_75']}\n\n")
        
        self.analytics_text.insert('end', f"Individual Student Report\n{'-'*30}\n")
        for student in report['students']:
            self.analytics_text.insert('end', f"\n{student['name']} ({student['student_id']})\n")
            self.analytics_text.insert('end', f"  Present: {student['present_days']} days\n")
            self.analytics_text.insert('end', f"  Absent: {student['absent_days']} days\n")
            self.analytics_text.insert('end', f"  Attendance: {student['attendance_percentage']:.2f}%\n")
    
    def export_data(self):
        classroom_id = self.export_classroom_var.get().split(' - ')[0] if self.export_classroom_var.get() else None
        
        if not classroom_id:
            messagebox.showwarning("Input Error", "Please select a classroom!")
            return
        
        export_type = self.export_type_var.get()
        date = None
        
        if export_type == 'today':
            date = datetime.now().strftime('%Y-%m-%d')
        elif export_type == 'date':
            date = self.export_date_entry.get()
        
        try:
            filename = self.exporter.export_classroom_attendance(
                classroom_id, 
                date, 
                self.include_analytics_var.get()
            )
            self.export_status_label.configure(
                text=f"Export successful! File saved: {filename}", 
                foreground='green'
            )
            messagebox.showinfo("Export Complete", f"Data exported successfully!\nFile: {filename}")
        except Exception as e:
            self.export_status_label.configure(
                text=f"Export failed: {str(e)}", 
                foreground='red'
            )
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def __del__(self):
        if self.camera:
            self.camera.release()


if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedAttendanceApp(root)
    root.mainloop()