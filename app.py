"""
Flask Web Application for Face Recognition Attendance System
Runs on localhost with beautiful web interface
"""

from flask import Flask, render_template, Response, jsonify, request, send_file
from flask_cors import CORS
import cv2
import numpy as np
from datetime import datetime
import os
import base64
import pickle
from production_face_recognition import ProductionFaceRecognition
from database_manager import DatabaseManager
import pandas as pd
import threading
import time

app = Flask(__name__)
CORS(app)

# Initialize systems
face_system = ProductionFaceRecognition()
face_system.load_database()
db_manager = DatabaseManager()

# Global state
camera = None
camera_lock = threading.Lock()
is_camera_active = False
marked_today = set()

# Load today's attendance
def load_today_attendance():
    global marked_today
    today = datetime.now().strftime('%Y-%m-%d')
    records = db_manager.get_attendance_by_date(today)
    marked_today = set(record[0] for record in records)

load_today_attendance()

def get_camera():
    """Get or create camera instance with optimized settings"""
    global camera, is_camera_active
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
            # Optimized settings for better performance
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            camera.set(cv2.CAP_PROP_FPS, 30)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer lag
            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # Better codec
            is_camera_active = True
    return camera

def release_camera():
    """Release camera instance"""
    global camera, is_camera_active
    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None
            is_camera_active = False

def generate_frames():
    """Generate video frames for streaming with optimized performance"""
    global marked_today

    while is_camera_active:
        cam = get_camera()
        success, frame = cam.read()

        if not success:
            break

        # Recognize faces
        recognized_faces = face_system.recognize_faces(frame, return_all=False)

        # Auto-mark attendance
        for face in recognized_faces:
            if face['student_id'] and face['student_id'] not in marked_today:
                success = db_manager.mark_attendance(
                    face['student_id'],
                    face['name'],
                    'P'
                )
                if success:
                    marked_today.add(face['student_id'])
                    print(f"✅ Auto-marked: {face['name']}")

        # Draw results
        frame = face_system.draw_results(frame, recognized_faces)

        # Encode frame with higher quality for better recognition
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/start_camera', methods=['POST'])
def start_camera():
    """Start camera"""
    global is_camera_active
    get_camera()
    is_camera_active = True
    return jsonify({'success': True, 'message': 'Camera started'})

@app.route('/api/stop_camera', methods=['POST'])
def stop_camera():
    """Stop camera"""
    global is_camera_active
    is_camera_active = False
    release_camera()
    return jsonify({'success': True, 'message': 'Camera stopped'})

# Registration state
registration_images = []
registration_data = {}

@app.route('/api/register/start', methods=['POST'])
def start_registration():
    """Start registration process"""
    global registration_images, registration_data
    data = request.json

    student_id = data.get('student_id')
    name = data.get('name')
    email = data.get('email', '')
    department = data.get('department', '')
    year = data.get('year', '')

    if not student_id or not name:
        return jsonify({'success': False, 'error': 'Student ID and Name are required'})

    # Store registration data
    registration_data = {
        'student_id': student_id,
        'name': name,
        'email': email,
        'department': department,
        'year': year
    }
    registration_images = []

    return jsonify({'success': True, 'message': 'Registration started'})

@app.route('/api/register/capture', methods=['POST'])
def capture_registration_image():
    """Capture image for registration"""
    global registration_images

    data = request.json
    image_data = data.get('image')

    if not image_data:
        return jsonify({'success': False, 'error': 'No image data'})

    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Detect face and check quality
        detections = face_system.detect_faces(frame)

        if len(detections) == 0:
            return jsonify({'success': False, 'error': 'No face detected'})

        if len(detections) > 1:
            return jsonify({'success': False, 'error': 'Multiple faces detected. Only one person allowed'})

        detection = detections[0]
        quality = detection['quality']

        if quality['overall'] < face_system.quality_threshold:
            return jsonify({
                'success': False,
                'error': f'Image quality too low: {quality["overall"]:.2f}',
                'quality': quality
            })

        # Extract and store embedding
        embedding = face_system.extract_embedding(detection['face_image'])
        registration_images.append(embedding)

        return jsonify({
            'success': True,
            'message': f'Image {len(registration_images)} captured',
            'count': len(registration_images),
            'quality': quality
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/register/complete', methods=['POST'])
def complete_registration():
    """Complete registration with captured images"""
    global registration_images, registration_data

    if len(registration_images) < 3:
        return jsonify({
            'success': False,
            'error': f'Need at least 3 images. Currently have {len(registration_images)}'
        })

    try:
        student_id = registration_data['student_id']
        name = registration_data['name']

        # Store in face system
        face_system.encodings_db[student_id] = registration_images
        face_system.student_metadata[student_id] = {
            'name': name,
            'email': registration_data.get('email'),
            'department': registration_data.get('department'),
            'year': registration_data.get('year'),
            'registered_at': datetime.now().isoformat(),
            'num_embeddings': len(registration_images)
        }

        # Save to disk
        face_system._save_database()

        # Also add to old database for compatibility
        db_manager.add_student(
            student_id,
            name,
            registration_data.get('email'),
            registration_data.get('department'),
            int(registration_data.get('year')) if registration_data.get('year') else None,
            pickle.dumps(registration_images[0])  # Store first embedding
        )

        # Clear registration state
        registration_images = []
        registration_data = {}

        return jsonify({
            'success': True,
            'message': f'Successfully registered {name}!',
            'student_id': student_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/register/cancel', methods=['POST'])
def cancel_registration():
    """Cancel registration"""
    global registration_images, registration_data
    registration_images = []
    registration_data = {}
    return jsonify({'success': True, 'message': 'Registration cancelled'})

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all registered students"""
    students = face_system.get_all_students()
    return jsonify({'students': students, 'total': len(students)})

@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student"""
    global marked_today

    # Delete from production face recognition system
    success_face = face_system.delete_student(student_id)

    # Delete from database
    success_db = db_manager.delete_student(student_id)

    # Remove from today's marked attendance
    if student_id in marked_today:
        marked_today.remove(student_id)

    if success_face or success_db:
        return jsonify({
            'success': True,
            'message': f'Student {student_id} deleted successfully'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to delete student'
        }), 500

@app.route('/api/attendance/today', methods=['GET'])
def get_today_attendance():
    """Get today's attendance"""
    today = datetime.now().strftime('%Y-%m-%d')
    records = db_manager.get_attendance_by_date(today)

    attendance_list = []
    for record in records:
        attendance_list.append({
            'student_id': record[0],
            'name': record[1],
            'time': record[2],
            'status': record[3]
        })

    total_students = len(face_system.get_all_students())
    present = len([r for r in records if r[3] == 'P'])
    absent = total_students - present

    return jsonify({
        'date': today,
        'attendance': attendance_list,
        'stats': {
            'total': total_students,
            'present': present,
            'absent': absent,
            'attendance_rate': (present / total_students * 100) if total_students > 0 else 0
        }
    })

@app.route('/api/attendance/by_date', methods=['GET'])
def get_attendance_by_date():
    """Get attendance by specific date"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    records = db_manager.get_attendance_by_date(date)

    attendance_list = []
    for record in records:
        attendance_list.append({
            'student_id': record[0],
            'name': record[1],
            'time': record[2],
            'status': record[3]
        })

    # Get total registered students
    total_students = len(face_system.encodings_db)

    return jsonify({
        'date': date,
        'attendance': attendance_list,
        'total': len(attendance_list),
        'total_students': total_students
    })

@app.route('/api/attendance/all', methods=['GET'])
def get_all_attendance():
    """Get all attendance records"""
    records = db_manager.get_all_attendance()

    attendance_list = []
    for record in records:
        attendance_list.append({
            'student_id': record[0],
            'name': record[1],
            'date': record[2],
            'time': record[3],
            'status': record[4]
        })

    return jsonify({
        'attendance': attendance_list,
        'total': len(attendance_list)
    })

@app.route('/api/export/today', methods=['GET'])
def export_today():
    """Export today's attendance to Excel"""
    today = datetime.now().strftime('%Y-%m-%d')
    records = db_manager.get_attendance_by_date(today)

    if not records:
        return jsonify({'success': False, 'error': 'No attendance records for today'})

    # Create DataFrame
    df = pd.DataFrame(records, columns=['Student ID', 'Name', 'Time', 'Status'])
    df.insert(2, 'Date', today)

    # Save to Excel
    os.makedirs('exports', exist_ok=True)
    filename = f"attendance_{today}.xlsx"
    filepath = os.path.join('exports', filename)

    df.to_excel(filepath, index=False)

    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/api/export/by_date', methods=['GET'])
def export_by_date():
    """Export attendance by date to Excel"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    records = db_manager.get_attendance_by_date(date)

    if not records:
        return jsonify({'success': False, 'error': f'No attendance records for {date}'})

    # Create DataFrame
    df = pd.DataFrame(records, columns=['Student ID', 'Name', 'Time', 'Status'])
    df.insert(2, 'Date', date)

    # Save to Excel
    os.makedirs('exports', exist_ok=True)
    filename = f"attendance_{date}.xlsx"
    filepath = os.path.join('exports', filename)

    df.to_excel(filepath, index=False)

    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    """Update system settings"""
    data = request.json

    if 'recognition_threshold' in data:
        face_system.recognition_threshold = float(data['recognition_threshold'])

    if 'quality_threshold' in data:
        face_system.quality_threshold = float(data['quality_threshold'])

    return jsonify({
        'success': True,
        'settings': {
            'recognition_threshold': face_system.recognition_threshold,
            'quality_threshold': face_system.quality_threshold
        }
    })

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify({
        'recognition_threshold': face_system.recognition_threshold,
        'quality_threshold': face_system.quality_threshold,
        'frame_skip': face_system.frame_skip,
        'min_face_size': face_system.min_face_size
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    students = face_system.get_all_students()
    today = datetime.now().strftime('%Y-%m-%d')
    today_records = db_manager.get_attendance_by_date(today)

    total_students = len(students)
    present_today = len([r for r in today_records if r[3] == 'P'])

    return jsonify({
        'total_students': total_students,
        'present_today': present_today,
        'absent_today': total_students - present_today,
        'attendance_rate': (present_today / total_students * 100) if total_students > 0 else 0,
        'camera_active': is_camera_active
    })

if __name__ == '__main__':
    port = 8000
    print("\n" + "="*70)
    print("🚀 FACE RECOGNITION ATTENDANCE SYSTEM - WEB SERVER")
    print("="*70)
    print(f"\n✅ System initialized with {len(face_system.encodings_db)} registered students")
    print(f"✅ Server starting on http://localhost:{port}")
    print(f"✅ Open your browser and navigate to: http://localhost:{port}")
    print(f"\n💡 Press Ctrl+C to stop the server")
    print("="*70 + "\n")

    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
