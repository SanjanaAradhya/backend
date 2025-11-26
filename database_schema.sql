# VTU Exam Registration Database Schema

CREATE DATABASE vtu_exam_registration;
USE vtu_exam_registration;

# Students table for storing registration data
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    usn VARCHAR(20) UNIQUE NOT NULL,
    branch VARCHAR(50) NOT NULL,
    semester INT NOT NULL,
    email VARCHAR(100) NOT NULL,
    has_backlogs BOOLEAN DEFAULT FALSE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    phone VARCHAR(15),
    current_semester INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

# Subjects table for exam subjects
CREATE TABLE subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(10) NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    semester INT NOT NULL,
    branch VARCHAR(50) NOT NULL,
    credits INT DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Student subject registrations
CREATE TABLE student_subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    subject_code VARCHAR(10) NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    semester INT NOT NULL,
    is_backlog BOOLEAN DEFAULT FALSE,
    registration_type ENUM('regular', 'backlog') DEFAULT 'regular',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Chat sessions for tracking user interactions
CREATE TABLE chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    student_usn VARCHAR(20),
    current_step VARCHAR(50) DEFAULT 'start',
    data JSON,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

# Insert sample subjects for different branches and semesters
INSERT INTO subjects (subject_code, subject_name, semester, branch) VALUES
-- CSE Subjects
('18CS51', 'Management and Entrepreneurship', 5, 'CSE'),
('18CS52', 'Computer Networks', 5, 'CSE'),
('18CS53', 'Database Management System', 5, 'CSE'),
('18CS54', 'Automata Theory and Computability', 5, 'CSE'),
('18CS55', 'Application Development using Python', 5, 'CSE'),
('18CS56', 'Unix System Programming', 5, 'CSE'),

-- ISE Subjects  
('18IS51', 'Management and Entrepreneurship', 5, 'ISE'),
('18IS52', 'Computer Networks', 5, 'ISE'),
('18IS53', 'Database Management System', 5, 'ISE'),
('18IS54', 'Software Engineering', 5, 'ISE'),
('18IS55', 'Machine Learning', 5, 'ISE'),

-- ECE Subjects
('18EC51', 'Management and Entrepreneurship', 5, 'ECE'),
('18EC52', 'Microprocessors', 5, 'ECE'),
('18EC53', 'Analog and Digital Communication', 5, 'ECE'),
('18EC54', 'Digital Signal Processing', 5, 'ECE'),

-- Mechanical Subjects
('18ME51', 'Management and Entrepreneurship', 5, 'MECH'),
('18ME52', 'Thermal Engineering', 5, 'MECH'),
('18ME53', 'Design of Machine Elements', 5, 'MECH'),
('18ME54', 'Fluid Mechanics', 5, 'MECH');