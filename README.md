# Face Recognition Attendance System

High-speed automated attendance system with cloud integration and real-time face recognition.

## 🚀 Features

- **Automatic Face Recognition** - Real-time detection without manual capture
- **Cloud Storage** - Supabase integration with optimized image storage
- **High Performance** - 30+ FPS with smart caching
- **Offline Mode** - Works without internet, syncs when online
- **Smart Camera** - Auto-releases when not in use
- **Single Image Policy** - One optimized image per person (~50KB)

## 📋 Prerequisites

- Python 3.8+
- Webcam
- Supabase account (free tier works)

## ⚡ Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Setup Supabase:**
   - Create project at [supabase.com](https://supabase.com)
   - Run `setup_supabase.sql` in SQL editor
   - Create storage bucket `student-faces`

3. **Configure:**
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

4. **Run:**
```bash
# Cloud-enabled system
python optimized_recognition.py

# Local-only system
python auto_recognition.py
```

## 🎯 Usage

### Cloud System (optimized_recognition.py)
- Register face once
- Auto-recognizes and marks attendance
- Syncs with Supabase cloud

### Local System (auto_recognition.py)
- Works completely offline
- Stores in local SQLite database

## 📁 Key Files

```
├── optimized_recognition.py  # Cloud-enabled high-speed system
├── supabase_manager.py       # Database operations
├── auto_recognition.py       # Standalone local system
├── setup_supabase.sql       # Database schema
└── .env.example            # Environment template
```

## 🔧 Performance Features

- **HOG Algorithm** - Fast face detection
- **Frame Skipping** - Process every 3rd frame
- **Image Compression** - JPEG optimization
- **Memory Cache** - Face encodings cached
- **Multi-threading** - Parallel processing

## 📊 Database Schema

### Students Table
- student_id, name, email, class_name, face_image_url

### Attendance Table  
- student_id, date, check_in_time, confidence_score, status

### Face Encodings Table
- student_id, encoding (base64), timestamps

## 📄 License

MIT License