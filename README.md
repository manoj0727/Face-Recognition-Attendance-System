# Face Recognition Attendance System

An automated attendance management system using face recognition technology for IPCV (Image Processing and Computer Vision) project.

## Features

- **Face Recognition**: Automatically identify and verify students using facial recognition
- **Student Registration**: Register new students with their face data
- **Attendance Marking**: Mark attendance as Present (P) or Absent (A)
- **Database Management**: SQLite database for storing student and attendance records
- **Excel Export**: Export attendance data to Excel format with formatting
- **GUI Interface**: User-friendly interface with multiple tabs for different functions
- **Real-time Camera Feed**: Live camera integration for attendance marking

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

Note: You may need to install cmake first:
```bash
# macOS
brew install cmake

# Ubuntu/Debian
sudo apt-get install cmake

# Windows
# Download from https://cmake.org/download/
```

## Usage

### GUI Mode (Recommended)
```bash
python main.py
```

### Command Line Options
```bash
# Start GUI
python main.py --mode gui

# Camera mode for quick attendance
python main.py --mode camera

# Register a student via CLI
python main.py --mode register --student-id "2021001" --name "John Doe" --image "path/to/image.jpg"

# Export attendance
python main.py --export today
python main.py --export complete
python main.py --export date --date 2024-01-15
```

## GUI Features

### 1. Register Student Tab
- Enter student details (ID, Name, Email, Department, Year)
- Upload photo or capture from camera
- Face encoding stored in database

### 2. Mark Attendance Tab
- Real-time camera feed with face detection
- Automatic face recognition
- One-click attendance marking
- Mark absent students option

### 3. View Records Tab
- View attendance by date
- View all attendance records
- Color-coded status (Green for Present, Red for Absent)
- Summary statistics

### 4. Export Data Tab
- Export today's attendance
- Export by specific date
- Export complete database with summary
- Individual student reports
- Excel format with formatting and multiple sheets

## Database Schema

### Students Table
- student_id (Primary Key)
- name
- email
- department
- year
- face_encoding (BLOB)

### Attendance Table
- id (Auto-increment)
- student_id (Foreign Key)
- name
- date
- time
- status (P/A)

## Excel Export Features

- Daily attendance sheets
- Complete attendance with summary
- Student-wise reports
- Attendance percentage calculations
- Color-coded status cells
- Auto-adjusted column widths

## Project Structure

```
Face-Recognition-Attendance-System/
├── main.py                    # Main application entry point
├── gui_app.py                 # GUI interface
├── face_recognition_module.py # Face detection and recognition
├── attendance_system.py       # Attendance marking logic
├── database_manager.py        # Database operations
├── excel_export.py           # Excel export functionality
├── requirements.txt          # Python dependencies
├── database/                 # SQLite database storage
├── images/                   # Student photos
│   └── registered_students/
└── attendance_records/       # Excel export files
```

## Requirements

- Python 3.7+
- OpenCV
- face-recognition
- dlib
- pandas
- openpyxl
- tkinter
- numpy
- Pillow

## License

MIT License