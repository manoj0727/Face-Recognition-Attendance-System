#!/usr/bin/env python3

import sys
import os
import argparse
from gui_app import main as run_gui
from attendance_system import AttendanceSystem
from face_recognition_module import FaceRecognitionSystem
from excel_export import ExcelExporter
from database_manager import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description='Face Recognition Attendance System')
    parser.add_argument('--mode', choices=['gui', 'camera', 'register'], 
                       default='gui', help='Run mode: gui, camera, or register')
    parser.add_argument('--student-id', help='Student ID for registration')
    parser.add_argument('--name', help='Student name for registration')
    parser.add_argument('--image', help='Image path for registration')
    parser.add_argument('--export', choices=['today', 'complete', 'date'], 
                       help='Export attendance data')
    parser.add_argument('--date', help='Date for export (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    if args.mode == 'gui':
        print("Starting Face Recognition Attendance System GUI...")
        print("Please wait while the application loads...")
        run_gui()
    
    elif args.mode == 'camera':
        print("Starting camera mode for attendance...")
        attendance = AttendanceSystem()
        attendance.mark_attendance_from_camera()
    
    elif args.mode == 'register':
        if not all([args.student_id, args.name, args.image]):
            print("Error: Registration requires --student-id, --name, and --image")
            sys.exit(1)
        
        if not os.path.exists(args.image):
            print(f"Error: Image file not found: {args.image}")
            sys.exit(1)
        
        face_recognition = FaceRecognitionSystem()
        success, message = face_recognition.register_face(
            args.image, 
            args.student_id, 
            args.name,
            email="",
            department="",
            year=1
        )
        print(message)
    
    elif args.export:
        exporter = ExcelExporter()
        
        if args.export == 'today':
            filename, message = exporter.export_daily_attendance()
            print(message)
        
        elif args.export == 'complete':
            filename, message = exporter.export_complete_attendance()
            print(message)
        
        elif args.export == 'date':
            if not args.date:
                print("Error: --date required for date export")
                sys.exit(1)
            filename, message = exporter.export_daily_attendance(args.date)
            print(message)

if __name__ == "__main__":
    main()