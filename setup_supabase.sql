-- Supabase Database Setup
-- Run these SQL commands in your Supabase SQL editor

-- 1. Students table
CREATE TABLE IF NOT EXISTS students (
    student_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    class_name VARCHAR(50),
    face_image_url TEXT,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Face encodings table (separate for faster queries)
CREATE TABLE IF NOT EXISTS face_encodings (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) REFERENCES students(student_id) ON DELETE CASCADE,
    encoding TEXT NOT NULL, -- Base64 encoded face encoding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id)
);

-- 3. Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) REFERENCES students(student_id),
    date DATE NOT NULL,
    check_in_time TIMESTAMP WITH TIME ZONE NOT NULL,
    check_out_time TIMESTAMP WITH TIME ZONE,
    class_name VARCHAR(50),
    location VARCHAR(100),
    confidence_score FLOAT,
    status VARCHAR(20) DEFAULT 'present',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id, date) -- Prevent duplicate attendance per day
);

-- 4. Create indexes for performance
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_attendance_student_id ON attendance(student_id);
CREATE INDEX idx_students_class ON students(class_name);

-- 5. Create storage bucket for face images
-- Go to Storage in Supabase dashboard and create a bucket named: student-faces

-- 6. Enable Row Level Security (RLS)
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
ALTER TABLE face_encodings ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- 7. Create policies for public access (adjust as needed)
CREATE POLICY "Enable read access for all users" ON students
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON students
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON students
    FOR UPDATE USING (true);

CREATE POLICY "Enable read access for all users" ON face_encodings
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON face_encodings
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON face_encodings
    FOR UPDATE USING (true);

CREATE POLICY "Enable read access for all users" ON attendance
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON attendance
    FOR INSERT WITH CHECK (true);

-- 8. Create view for attendance with student details
CREATE OR REPLACE VIEW attendance_details AS
SELECT 
    a.*,
    s.name as student_name,
    s.email as student_email,
    s.class_name as student_class
FROM attendance a
JOIN students s ON a.student_id = s.student_id;