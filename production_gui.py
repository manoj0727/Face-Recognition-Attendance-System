"""
Production GUI for Face Recognition Attendance System
Beautiful, user-friendly interface with real-time feedback
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import cv2
from datetime import datetime
import threading
from production_face_recognition import ProductionFaceRecognition
from database_manager import DatabaseManager
import pandas as pd
import os

class ProductionAttendanceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Production Face Recognition Attendance System")
        self.root.geometry("1400x900")

        # Systems
        self.face_system = ProductionFaceRecognition()
        self.face_system.load_database()
        self.db_manager = DatabaseManager()

        # Camera state
        self.camera_running = False
        self.video_capture = None
        self.current_frame = None

        # Attendance tracking
        self.marked_today = set()
        self.load_today_attendance()

        # Setup UI
        self.setup_ui()
        self.update_stats()

    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use('clam')

        # Configure colors
        style.configure('Success.TButton', background='#4CAF50', foreground='white')
        style.configure('Danger.TButton', background='#f44336', foreground='white')
        style.configure('Primary.TButton', background='#2196F3', foreground='white')

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tabs
        self.attendance_tab = ttk.Frame(self.notebook)
        self.register_tab = ttk.Frame(self.notebook)
        self.reports_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.attendance_tab, text='📹 Live Attendance')
        self.notebook.add(self.register_tab, text='➕ Register Student')
        self.notebook.add(self.reports_tab, text='📊 Reports')
        self.notebook.add(self.settings_tab, text='⚙️ Settings')

        self.setup_attendance_tab()
        self.setup_register_tab()
        self.setup_reports_tab()
        self.setup_settings_tab()

    def setup_attendance_tab(self):
        """Live attendance marking with real-time video feed"""
        # Left panel - Video
        left_panel = ttk.Frame(self.attendance_tab)
        left_panel.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        # Video display
        video_frame = ttk.LabelFrame(left_panel, text="Live Camera Feed", padding=10)
        video_frame.pack(fill='both', expand=True)

        self.video_label = tk.Label(video_frame, bg='black')
        self.video_label.pack(fill='both', expand=True)

        # Controls
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill='x', pady=10)

        self.start_btn = ttk.Button(control_frame, text="🎥 Start Camera",
                                    command=self.start_camera, style='Primary.TButton')
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = ttk.Button(control_frame, text="⏹ Stop Camera",
                                   command=self.stop_camera, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        ttk.Button(control_frame, text="📊 Export Today's Attendance",
                  command=self.export_today_attendance).pack(side='right', padx=5)

        # Status
        self.status_label = tk.Label(left_panel, text="Camera not started",
                                     font=('Arial', 12), bg='#f0f0f0', pady=10)
        self.status_label.pack(fill='x')

        # Right panel - Today's attendance
        right_panel = ttk.Frame(self.attendance_tab, width=400)
        right_panel.pack(side='right', fill='both', padx=10, pady=10)
        right_panel.pack_propagate(False)

        # Stats
        stats_frame = ttk.LabelFrame(right_panel, text="Today's Statistics", padding=10)
        stats_frame.pack(fill='x', pady=5)

        self.stats_text = tk.Text(stats_frame, height=6, font=('Arial', 11))
        self.stats_text.pack(fill='x')

        # Attendance list
        list_frame = ttk.LabelFrame(right_panel, text="Marked Present", padding=10)
        list_frame.pack(fill='both', expand=True, pady=5)

        # Scrollable list
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side='right', fill='y')

        self.attendance_listbox = tk.Listbox(list_frame, font=('Arial', 10),
                                            yscrollcommand=list_scroll.set)
        self.attendance_listbox.pack(fill='both', expand=True)
        list_scroll.config(command=self.attendance_listbox.yview)

    def setup_register_tab(self):
        """Student registration interface"""
        # Main frame
        main_frame = ttk.Frame(self.register_tab)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Form
        form_frame = ttk.LabelFrame(main_frame, text="Student Information", padding=20)
        form_frame.pack(fill='x', pady=10)

        # Fields
        fields = [
            ("Student ID:", "student_id"),
            ("Full Name:", "name"),
            ("Email:", "email"),
            ("Department:", "department"),
            ("Year:", "year")
        ]

        self.register_entries = {}

        for i, (label, key) in enumerate(fields):
            ttk.Label(form_frame, text=label, font=('Arial', 11)).grid(
                row=i, column=0, sticky='w', pady=8, padx=5
            )
            entry = ttk.Entry(form_frame, width=40, font=('Arial', 11))
            entry.grid(row=i, column=1, pady=8, padx=5)
            self.register_entries[key] = entry

        # Instructions
        instructions = ttk.LabelFrame(main_frame, text="Registration Instructions", padding=20)
        instructions.pack(fill='x', pady=10)

        instructions_text = """
📸 Multi-Angle Registration Process:

1. Enter student details above
2. Click 'Start Registration' button
3. Capture 3-7 high-quality images:
   • Face straight to camera (press SPACE)
   • Turn slightly left (press SPACE)
   • Turn slightly right (press SPACE)
   • Normal expression variations (press SPACE)

💡 Tips for best accuracy:
   • Ensure good lighting
   • Remove glasses if possible
   • Maintain neutral expression
   • Stay still when capturing
   • Quality score should be > 0.6

Press Q to finish early (minimum 3 images required)
Press ESC to cancel registration
        """

        tk.Label(instructions, text=instructions_text, font=('Arial', 10),
                justify='left', bg='#f9f9f9').pack(fill='x')

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=20)

        ttk.Button(button_frame, text="🎥 Start Registration",
                  command=self.start_registration,
                  style='Primary.TButton').pack(side='left', padx=5)

        ttk.Button(button_frame, text="🔄 Clear Form",
                  command=self.clear_registration_form).pack(side='left', padx=5)

        # Status
        self.register_status = tk.Label(main_frame, text="", font=('Arial', 11))
        self.register_status.pack(pady=10)

    def setup_reports_tab(self):
        """Reports and analytics"""
        # Controls
        control_frame = ttk.Frame(self.reports_tab)
        control_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(control_frame, text="Select Date:", font=('Arial', 11)).pack(side='left', padx=5)

        self.report_date_entry = ttk.Entry(control_frame, width=15, font=('Arial', 11))
        self.report_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.report_date_entry.pack(side='left', padx=5)

        ttk.Button(control_frame, text="🔍 View Records",
                  command=self.view_date_records).pack(side='left', padx=5)

        ttk.Button(control_frame, text="📊 View All",
                  command=self.view_all_records).pack(side='left', padx=5)

        ttk.Button(control_frame, text="💾 Export to Excel",
                  command=self.export_to_excel).pack(side='right', padx=5)

        # Table
        table_frame = ttk.Frame(self.reports_tab)
        table_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Treeview
        columns = ('Student ID', 'Name', 'Date', 'Time', 'Status')
        self.reports_tree = ttk.Treeview(table_frame, columns=columns,
                                         show='headings', height=20)

        for col in columns:
            self.reports_tree.heading(col, text=col)
            self.reports_tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(table_frame, orient='vertical',
                                 command=self.reports_tree.yview)
        self.reports_tree.configure(yscrollcommand=scrollbar.set)

        self.reports_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Summary
        self.report_summary = tk.Label(self.reports_tab, text="",
                                       font=('Arial', 11), bg='#f0f0f0', pady=10)
        self.report_summary.pack(fill='x', padx=20)

    def setup_settings_tab(self):
        """System settings"""
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Recognition Settings",
                                       padding=20)
        settings_frame.pack(fill='x', padx=20, pady=20)

        # Recognition threshold
        ttk.Label(settings_frame, text="Recognition Threshold:",
                 font=('Arial', 11)).grid(row=0, column=0, sticky='w', pady=10)

        self.threshold_var = tk.DoubleVar(value=self.face_system.recognition_threshold)
        threshold_scale = ttk.Scale(settings_frame, from_=0.5, to=0.9,
                                   variable=self.threshold_var, orient='horizontal',
                                   length=300)
        threshold_scale.grid(row=0, column=1, pady=10, padx=10)

        self.threshold_label = tk.Label(settings_frame, text=f"{self.threshold_var.get():.2f}",
                                       font=('Arial', 11))
        self.threshold_label.grid(row=0, column=2, pady=10)

        threshold_scale.config(command=self.update_threshold_label)

        # Quality threshold
        ttk.Label(settings_frame, text="Quality Threshold:",
                 font=('Arial', 11)).grid(row=1, column=0, sticky='w', pady=10)

        self.quality_var = tk.DoubleVar(value=self.face_system.quality_threshold)
        quality_scale = ttk.Scale(settings_frame, from_=0.3, to=0.8,
                                 variable=self.quality_var, orient='horizontal',
                                 length=300)
        quality_scale.grid(row=1, column=1, pady=10, padx=10)

        self.quality_label = tk.Label(settings_frame, text=f"{self.quality_var.get():.2f}",
                                      font=('Arial', 11))
        self.quality_label.grid(row=1, column=2, pady=10)

        quality_scale.config(command=self.update_quality_label)

        # Apply button
        ttk.Button(settings_frame, text="✅ Apply Settings",
                  command=self.apply_settings,
                  style='Success.TButton').grid(row=2, column=1, pady=20)

        # System info
        info_frame = ttk.LabelFrame(self.settings_tab, text="System Information",
                                   padding=20)
        info_frame.pack(fill='x', padx=20, pady=10)

        students = self.face_system.get_all_students()
        info_text = f"""
📊 Database Statistics:
   • Total Registered Students: {len(students)}
   • Recognition Model: FaceNet (512D)
   • Detection Model: MTCNN
   • Database Path: database/production/

⚡ Performance Settings:
   • Frame Skip: {self.face_system.frame_skip}
   • Min Face Size: {self.face_system.min_face_size}px
   • Registration Images: {self.face_system.min_registration_images}-{self.face_system.max_registration_images}
        """

        tk.Label(info_frame, text=info_text, font=('Arial', 10),
                justify='left', bg='#f9f9f9').pack(fill='x')

    def update_threshold_label(self, val):
        self.threshold_label.config(text=f"{float(val):.2f}")

    def update_quality_label(self, val):
        self.quality_label.config(text=f"{float(val):.2f}")

    def apply_settings(self):
        self.face_system.recognition_threshold = self.threshold_var.get()
        self.face_system.quality_threshold = self.quality_var.get()
        messagebox.showinfo("Success", "Settings applied successfully!")

    def start_camera(self):
        """Start camera for live attendance"""
        self.camera_running = True
        self.video_capture = cv2.VideoCapture(0)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="🎥 Camera Running - Ready to mark attendance",
                                bg='#4CAF50', fg='white')

        self.update_camera_feed()

    def update_camera_feed(self):
        """Update camera feed with face recognition"""
        if not self.camera_running or not self.video_capture:
            return

        ret, frame = self.video_capture.read()
        if not ret:
            self.root.after(10, self.update_camera_feed)
            return

        # Recognize faces
        recognized_faces = self.face_system.recognize_faces(frame)

        # Auto-mark attendance
        for face in recognized_faces:
            if face['student_id'] and face['student_id'] not in self.marked_today:
                # Mark attendance
                success = self.db_manager.mark_attendance(
                    face['student_id'],
                    face['name'],
                    'P'
                )
                if success:
                    self.marked_today.add(face['student_id'])
                    self.attendance_listbox.insert(0,
                        f"✅ {face['name']} - {datetime.now().strftime('%H:%M:%S')} (Conf: {face['confidence']:.2f})"
                    )
                    self.update_stats()
                    print(f"✅ Marked: {face['name']}")

        # Draw results
        display_frame = self.face_system.draw_results(frame, recognized_faces)

        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(display_frame, timestamp, (10, display_frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Convert to PhotoImage
        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        display_frame = cv2.resize(display_frame, (960, 720))
        img = Image.fromarray(display_frame)
        imgtk = ImageTk.PhotoImage(image=img)

        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        # Continue loop
        self.root.after(10, self.update_camera_feed)

    def stop_camera(self):
        """Stop camera"""
        self.camera_running = False
        if self.video_capture:
            self.video_capture.release()

        self.video_label.configure(image='')
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text="Camera stopped", bg='#f0f0f0', fg='black')

    def start_registration(self):
        """Start student registration process"""
        # Validate inputs
        student_id = self.register_entries['student_id'].get().strip()
        name = self.register_entries['name'].get().strip()

        if not student_id or not name:
            messagebox.showerror("Error", "Student ID and Name are required!")
            return

        # Get optional fields
        email = self.register_entries['email'].get().strip() or None
        department = self.register_entries['department'].get().strip() or None
        year_str = self.register_entries['year'].get().strip()
        year = int(year_str) if year_str else None

        # Register in background
        def register_thread():
            result = self.face_system.register_student(
                student_id, name, email, department, year
            )

            if result['success']:
                self.root.after(0, lambda: self.register_status.config(
                    text=f"✅ Successfully registered {name} with {result['num_images']} images!",
                    fg='green'
                ))
                self.root.after(0, self.clear_registration_form)
                self.root.after(0, self.update_stats)

                # Also add to old database for compatibility
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"Registered {name} successfully with {result['num_images']} high-quality images!"
                ))
            else:
                self.root.after(0, lambda: self.register_status.config(
                    text=f"❌ Registration failed: {result.get('error')}",
                    fg='red'
                ))

        threading.Thread(target=register_thread, daemon=True).start()

    def clear_registration_form(self):
        """Clear registration form"""
        for entry in self.register_entries.values():
            entry.delete(0, tk.END)
        self.register_status.config(text="")

    def load_today_attendance(self):
        """Load today's attendance from database"""
        today = datetime.now().strftime('%Y-%m-%d')
        records = self.db_manager.get_attendance_by_date(today)
        self.marked_today = set(record[0] for record in records)

    def update_stats(self):
        """Update statistics display"""
        students = self.face_system.get_all_students()
        total_students = len(students)
        present_today = len(self.marked_today)
        absent_today = total_students - present_today

        attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0

        stats_text = f"""
📊 Today's Statistics ({datetime.now().strftime('%Y-%m-%d')}):

   Total Students: {total_students}
   Present: {present_today}
   Absent: {absent_today}
   Attendance Rate: {attendance_rate:.1f}%
        """

        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)

    def view_date_records(self):
        """View records for specific date"""
        date = self.report_date_entry.get()
        records = self.db_manager.get_attendance_by_date(date)
        self.display_records(records, date)

    def view_all_records(self):
        """View all attendance records"""
        records = self.db_manager.get_all_attendance()
        self.display_records(records, "All Dates")

    def display_records(self, records, date_info):
        """Display records in treeview"""
        # Clear existing
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item)

        # Add records
        for record in records:
            if len(record) == 4:  # Date-specific records
                student_id, name, time, status = record
                date = self.report_date_entry.get()
            else:  # All records
                student_id, name, date, time, status = record

            self.reports_tree.insert('', 'end', values=(student_id, name, date, time, status))

        # Summary
        present = sum(1 for r in records if r[-1] == 'P')
        absent = sum(1 for r in records if r[-1] == 'A')
        total = len(records)

        self.report_summary.config(
            text=f"📊 {date_info} | Total: {total} | Present: {present} | Absent: {absent}"
        )

    def export_today_attendance(self):
        """Export today's attendance to Excel"""
        today = datetime.now().strftime('%Y-%m-%d')
        records = self.db_manager.get_attendance_by_date(today)

        if not records:
            messagebox.showinfo("Info", "No attendance records for today")
            return

        # Create DataFrame
        df = pd.DataFrame(records, columns=['Student ID', 'Name', 'Time', 'Status'])
        df.insert(2, 'Date', today)

        # Save
        filename = f"attendance_{today}.xlsx"
        os.makedirs('exports', exist_ok=True)
        filepath = os.path.join('exports', filename)

        df.to_excel(filepath, index=False)
        messagebox.showinfo("Success", f"Exported to {filepath}")

    def export_to_excel(self):
        """Export current view to Excel"""
        items = self.reports_tree.get_children()
        if not items:
            messagebox.showinfo("Info", "No records to export")
            return

        data = []
        for item in items:
            data.append(self.reports_tree.item(item)['values'])

        df = pd.DataFrame(data, columns=['Student ID', 'Name', 'Date', 'Time', 'Status'])

        # Save dialog
        filepath = filedialog.asksaveasfilename(
            defaultextension='.xlsx',
            filetypes=[('Excel files', '*.xlsx')],
            initialfile=f"attendance_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

        if filepath:
            df.to_excel(filepath, index=False)
            messagebox.showinfo("Success", f"Exported to {filepath}")


def main():
    root = tk.Tk()
    app = ProductionAttendanceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
