import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import PhotoImage
import cv2
from PIL import Image, ImageTk
from datetime import datetime
import threading
from face_recognition_module import FaceRecognitionSystem
from attendance_system import AttendanceSystem
from excel_export import ExcelExporter
from database_manager import DatabaseManager

class AttendanceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry("1200x700")
        
        self.face_recognition = FaceRecognitionSystem()
        self.attendance_system = AttendanceSystem()
        self.excel_exporter = ExcelExporter()
        self.db_manager = DatabaseManager()
        
        self.camera_running = False
        self.video_capture = None
        
        self.setup_ui()
    
    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)
        
        self.register_tab = ttk.Frame(self.notebook)
        self.attendance_tab = ttk.Frame(self.notebook)
        self.view_tab = ttk.Frame(self.notebook)
        self.export_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.register_tab, text='Register Student')
        self.notebook.add(self.attendance_tab, text='Mark Attendance')
        self.notebook.add(self.view_tab, text='View Records')
        self.notebook.add(self.export_tab, text='Export Data')
        
        self.setup_register_tab()
        self.setup_attendance_tab()
        self.setup_view_tab()
        self.setup_export_tab()
    
    def setup_register_tab(self):
        register_frame = ttk.LabelFrame(self.register_tab, text="Student Registration", padding=20)
        register_frame.pack(padx=20, pady=20, fill='both')
        
        ttk.Label(register_frame, text="Student ID:").grid(row=0, column=0, sticky='w', pady=5)
        self.student_id_entry = ttk.Entry(register_frame, width=30)
        self.student_id_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(register_frame, text="Name:").grid(row=1, column=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(register_frame, width=30)
        self.name_entry.grid(row=1, column=1, pady=5)
        
        ttk.Label(register_frame, text="Email:").grid(row=2, column=0, sticky='w', pady=5)
        self.email_entry = ttk.Entry(register_frame, width=30)
        self.email_entry.grid(row=2, column=1, pady=5)
        
        ttk.Label(register_frame, text="Department:").grid(row=3, column=0, sticky='w', pady=5)
        self.department_entry = ttk.Entry(register_frame, width=30)
        self.department_entry.grid(row=3, column=1, pady=5)
        
        ttk.Label(register_frame, text="Year:").grid(row=4, column=0, sticky='w', pady=5)
        self.year_entry = ttk.Entry(register_frame, width=30)
        self.year_entry.grid(row=4, column=1, pady=5)
        
        button_frame = ttk.Frame(register_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Select Image", command=self.select_image).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Capture from Camera", command=self.capture_for_registration).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Register", command=self.register_student).pack(side='left', padx=5)
        
        self.image_path_label = ttk.Label(register_frame, text="No image selected")
        self.image_path_label.grid(row=6, column=0, columnspan=2, pady=5)
        
        self.selected_image_path = None
    
    def setup_attendance_tab(self):
        attendance_frame = ttk.LabelFrame(self.attendance_tab, text="Mark Attendance", padding=20)
        attendance_frame.pack(padx=20, pady=20, fill='both', expand=True)
        
        self.camera_label = ttk.Label(attendance_frame)
        self.camera_label.pack(pady=10)
        
        button_frame = ttk.Frame(attendance_frame)
        button_frame.pack(pady=10)
        
        self.start_camera_btn = ttk.Button(button_frame, text="Start Camera", command=self.start_camera)
        self.start_camera_btn.pack(side='left', padx=5)
        
        self.stop_camera_btn = ttk.Button(button_frame, text="Stop Camera", command=self.stop_camera, state='disabled')
        self.stop_camera_btn.pack(side='left', padx=5)
        
        self.mark_attendance_btn = ttk.Button(button_frame, text="Mark Attendance", command=self.mark_attendance, state='disabled')
        self.mark_attendance_btn.pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="Mark Absent Students", command=self.mark_absent).pack(side='left', padx=5)
        
        self.attendance_status_label = ttk.Label(attendance_frame, text="Camera not started")
        self.attendance_status_label.pack(pady=10)
    
    def setup_view_tab(self):
        view_frame = ttk.LabelFrame(self.view_tab, text="Attendance Records", padding=20)
        view_frame.pack(padx=20, pady=20, fill='both', expand=True)
        
        date_frame = ttk.Frame(view_frame)
        date_frame.pack(pady=10)
        
        ttk.Label(date_frame, text="Select Date (YYYY-MM-DD):").pack(side='left', padx=5)
        self.date_entry = ttk.Entry(date_frame, width=15)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.pack(side='left', padx=5)
        
        ttk.Button(date_frame, text="View", command=self.view_attendance).pack(side='left', padx=5)
        ttk.Button(date_frame, text="View All", command=self.view_all_attendance).pack(side='left', padx=5)
        
        columns = ('Student ID', 'Name', 'Date/Time', 'Status')
        self.tree = ttk.Treeview(view_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(view_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.summary_label = ttk.Label(view_frame, text="", font=('Arial', 11))
        self.summary_label.pack(pady=10)
    
    def setup_export_tab(self):
        export_frame = ttk.LabelFrame(self.export_tab, text="Export Options", padding=20)
        export_frame.pack(padx=20, pady=20, fill='both')
        
        ttk.Button(export_frame, text="Export Today's Attendance", 
                  command=self.export_today, width=30).pack(pady=10)
        
        date_export_frame = ttk.Frame(export_frame)
        date_export_frame.pack(pady=10)
        
        ttk.Label(date_export_frame, text="Date (YYYY-MM-DD):").pack(side='left', padx=5)
        self.export_date_entry = ttk.Entry(date_export_frame, width=15)
        self.export_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.export_date_entry.pack(side='left', padx=5)
        
        ttk.Button(date_export_frame, text="Export by Date", 
                  command=self.export_by_date).pack(side='left', padx=5)
        
        ttk.Button(export_frame, text="Export Complete Database", 
                  command=self.export_complete, width=30).pack(pady=10)
        
        student_export_frame = ttk.Frame(export_frame)
        student_export_frame.pack(pady=10)
        
        ttk.Label(student_export_frame, text="Student ID:").pack(side='left', padx=5)
        self.export_student_entry = ttk.Entry(student_export_frame, width=15)
        self.export_student_entry.pack(side='left', padx=5)
        
        ttk.Button(student_export_frame, text="Export Student Report", 
                  command=self.export_student_report).pack(side='left', padx=5)
        
        self.export_status_label = ttk.Label(export_frame, text="", foreground='green')
        self.export_status_label.pack(pady=20)
    
    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Student Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            self.selected_image_path = file_path
            self.image_path_label.config(text=f"Selected: {file_path.split('/')[-1]}")
    
    def capture_for_registration(self):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        
        if ret:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_path = f"images/registered_students/temp_{timestamp}.jpg"
            cv2.imwrite(image_path, frame)
            self.selected_image_path = image_path
            self.image_path_label.config(text=f"Image captured successfully")
        
        cap.release()
    
    def register_student(self):
        if not self.selected_image_path:
            messagebox.showerror("Error", "Please select or capture an image")
            return
        
        student_id = self.student_id_entry.get()
        name = self.name_entry.get()
        email = self.email_entry.get()
        department = self.department_entry.get()
        year = self.year_entry.get()
        
        if not all([student_id, name]):
            messagebox.showerror("Error", "Student ID and Name are required")
            return
        
        try:
            year = int(year) if year else 1
        except ValueError:
            messagebox.showerror("Error", "Year must be a number")
            return
        
        success, message = self.face_recognition.register_face(
            self.selected_image_path, student_id, name, email, department, year
        )
        
        if success:
            messagebox.showinfo("Success", message)
            self.clear_registration_form()
        else:
            messagebox.showerror("Error", message)
    
    def clear_registration_form(self):
        self.student_id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.department_entry.delete(0, tk.END)
        self.year_entry.delete(0, tk.END)
        self.selected_image_path = None
        self.image_path_label.config(text="No image selected")
    
    def start_camera(self):
        self.camera_running = True
        self.video_capture = cv2.VideoCapture(0)
        self.start_camera_btn.config(state='disabled')
        self.stop_camera_btn.config(state='normal')
        self.mark_attendance_btn.config(state='normal')
        self.attendance_status_label.config(text="Camera running - Position yourself in front of the camera")
        
        self.update_camera_frame()
    
    def update_camera_frame(self):
        if self.camera_running and self.video_capture:
            ret, frame = self.video_capture.read()
            if ret:
                face_locations, face_names, _ = self.face_recognition.recognize_face(frame)
                frame = self.face_recognition.draw_faces(frame, face_locations, face_names)
                
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (640, 480))
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
                
                if face_names:
                    status = f"Detected: {', '.join(face_names)}"
                    self.attendance_status_label.config(text=status)
            
            self.root.after(10, self.update_camera_frame)
    
    def stop_camera(self):
        self.camera_running = False
        if self.video_capture:
            self.video_capture.release()
        self.camera_label.configure(image='')
        self.start_camera_btn.config(state='normal')
        self.stop_camera_btn.config(state='disabled')
        self.mark_attendance_btn.config(state='disabled')
        self.attendance_status_label.config(text="Camera stopped")
    
    def mark_attendance(self):
        if not self.camera_running or not self.video_capture:
            messagebox.showerror("Error", "Camera is not running")
            return
        
        ret, frame = self.video_capture.read()
        if ret:
            face_locations, face_names, face_ids = self.face_recognition.recognize_face(frame)
            
            marked_names = []
            for student_id, name in zip(face_ids, face_names):
                if student_id:
                    success = self.db_manager.mark_attendance(student_id, name, 'P')
                    if success:
                        marked_names.append(name)
            
            if marked_names:
                message = f"Attendance marked for: {', '.join(marked_names)}"
                messagebox.showinfo("Success", message)
                self.attendance_status_label.config(text=message)
            else:
                messagebox.showinfo("Info", "No new attendance to mark or faces not recognized")
    
    def mark_absent(self):
        result = messagebox.askyesno("Confirm", "Mark all remaining students as absent for today?")
        if result:
            self.attendance_system.mark_absent_students()
            messagebox.showinfo("Success", "Absent students marked successfully")
    
    def view_attendance(self):
        date = self.date_entry.get()
        records = self.db_manager.get_attendance_by_date(date)
        self.display_records(records, date_column=False)
        
        present = sum(1 for r in records if r[3] == 'P')
        absent = sum(1 for r in records if r[3] == 'A')
        total = len(records)
        
        self.summary_label.config(
            text=f"Date: {date} | Total: {total} | Present: {present} | Absent: {absent}"
        )
    
    def view_all_attendance(self):
        records = self.db_manager.get_all_attendance()
        self.display_records(records, date_column=True)
        
        if records:
            total_records = len(records)
            unique_dates = len(set(r[2] for r in records))
            self.summary_label.config(
                text=f"Total Records: {total_records} | Days: {unique_dates}"
            )
    
    def display_records(self, records, date_column=True):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for record in records:
            if date_column:
                values = (record[0], record[1], f"{record[2]} {record[3]}", record[4])
            else:
                values = (record[0], record[1], record[2], record[3])
            
            tag = 'present' if values[3] == 'P' else 'absent'
            self.tree.insert('', 'end', values=values, tags=(tag,))
        
        self.tree.tag_configure('present', background='#90EE90')
        self.tree.tag_configure('absent', background='#FFB6C1')
    
    def export_today(self):
        filename, message = self.excel_exporter.export_daily_attendance()
        if filename:
            self.export_status_label.config(text=message, foreground='green')
        else:
            self.export_status_label.config(text=message, foreground='red')
    
    def export_by_date(self):
        date = self.export_date_entry.get()
        filename, message = self.excel_exporter.export_daily_attendance(date)
        if filename:
            self.export_status_label.config(text=message, foreground='green')
        else:
            self.export_status_label.config(text=message, foreground='red')
    
    def export_complete(self):
        filename, message = self.excel_exporter.export_complete_attendance()
        if filename:
            self.export_status_label.config(text=message, foreground='green')
        else:
            self.export_status_label.config(text=message, foreground='red')
    
    def export_student_report(self):
        student_id = self.export_student_entry.get()
        if not student_id:
            messagebox.showerror("Error", "Please enter a Student ID")
            return
        
        filename, message = self.excel_exporter.export_student_report(student_id)
        if filename:
            self.export_status_label.config(text=message, foreground='green')
        else:
            self.export_status_label.config(text=message, foreground='red')

def main():
    root = tk.Tk()
    app = AttendanceGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()