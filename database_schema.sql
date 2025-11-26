-- database_schema.sql
-- VTU Exam Registration & Seat Allocation - Cleaned schema (MySQL)

CREATE DATABASE IF NOT EXISTS vtu_exam_registration;
USE vtu_exam_registration;

-- STUDENTS
CREATE TABLE IF NOT EXISTS students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    usn VARCHAR(20) UNIQUE NOT NULL,
    branch VARCHAR(50) NOT NULL,
    semester INT NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(15),
    has_backlogs BOOLEAN DEFAULT FALSE,
    current_semester INT,
    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_usn (usn),
    INDEX idx_branch (branch),
    INDEX idx_semester (semester)
) ENGINE=InnoDB;

-- SUBJECTS
CREATE TABLE IF NOT EXISTS subjects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    subject_code VARCHAR(15) NOT NULL UNIQUE,
    subject_name VARCHAR(150) NOT NULL,
    semester INT NOT NULL,
    branch VARCHAR(50) NOT NULL,
    credits INT DEFAULT 4,
    subject_type ENUM('theory','practical','project') DEFAULT 'theory',
    is_core BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_branch_semester (branch, semester),
    INDEX idx_subject_code (subject_code)
) ENGINE=InnoDB;

-- EXAM ROOMS
CREATE TABLE IF NOT EXISTS exam_rooms (
    id INT PRIMARY KEY AUTO_INCREMENT,
    room_code VARCHAR(20) NOT NULL UNIQUE,
    room_name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL,
    `rows` INT NOT NULL DEFAULT 10,
    cols INT NOT NULL DEFAULT 6,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_room_code (room_code)
) ENGINE=InnoDB;

-- DESKS (optional physical desk mapping)
CREATE TABLE IF NOT EXISTS desks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    desk_id VARCHAR(50) UNIQUE NOT NULL,
    room_code VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    `row` INT NOT NULL,
    col_start INT NOT NULL,
    col_end INT NOT NULL,
    seat1 VARCHAR(10),
    seat2 VARCHAR(10),
    capacity INT DEFAULT 2,
    is_available BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_room_code (room_code),
    INDEX idx_desk_id (desk_id),
    FOREIGN KEY (room_code) REFERENCES exam_rooms(room_code) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ALLOCATION SESSIONS (session metadata)
CREATE TABLE IF NOT EXISTS allocation_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) UNIQUE NOT NULL,
    subject_codes TEXT NOT NULL,
    algorithm_used VARCHAR(50) DEFAULT 'genetic',
    total_students INT DEFAULT 0,
    total_rooms INT DEFAULT 0,
    total_desks INT DEFAULT 0,
    fitness_score FLOAT DEFAULT 0.0,
    exam_date DATE NULL,
    exam_time TIME NULL,
    exam_duration INT DEFAULT 180 COMMENT 'Duration in minutes',
    emails_sent BOOLEAN DEFAULT FALSE,
    email_sent_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB;

-- DETAILED ALLOCATIONS (final allocation per student per session)
CREATE TABLE IF NOT EXISTS detailed_allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    student_usn VARCHAR(20) NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    subject_code VARCHAR(15) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    branch VARCHAR(50) NOT NULL,
    room_code VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    seat_number VARCHAR(20) NOT NULL,
    row_num INT NOT NULL,
    col_num INT NOT NULL,
    desk_id VARCHAR(50) NULL,
    desk_partner_usn VARCHAR(20) NULL,
    desk_position VARCHAR(10) NULL,
    allocation_method VARCHAR(50) DEFAULT 'AI',
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at DATETIME NULL,
    hall_ticket_viewed BOOLEAN DEFAULT FALSE,
    seating_plan_viewed BOOLEAN DEFAULT FALSE,
    last_viewed_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_student_usn (student_usn),
    INDEX idx_subject_code (subject_code),
    INDEX idx_room_code (room_code),
    INDEX idx_desk_id (desk_id),
    INDEX idx_student_session (student_usn, session_id),
    INDEX idx_room_session (room_code, session_id),
    INDEX idx_created_at (created_at),
    CONSTRAINT fk_detailed_allocation_session FOREIGN KEY (session_id)
      REFERENCES allocation_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- STUDENT_SUBJECTS (student registrations to subjects)
CREATE TABLE IF NOT EXISTS student_subjects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    subject_id INT,
    subject_code VARCHAR(15) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    semester INT NOT NULL,
    is_backlog BOOLEAN DEFAULT FALSE,
    registration_type ENUM('regular','backlog','improvement') DEFAULT 'regular',
    exam_fee_paid BOOLEAN DEFAULT FALSE,
    hall_ticket_generated BOOLEAN DEFAULT FALSE,
    seat_allocated BOOLEAN DEFAULT FALSE,
    allocated_room VARCHAR(20),
    allocated_seat VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
    INDEX idx_student (student_id),
    INDEX idx_subject (subject_id),
    INDEX idx_subject_code (subject_code),
    INDEX idx_semester (semester),
    INDEX idx_registration_type (registration_type),
    UNIQUE KEY unique_student_subject (student_id, subject_id)
) ENGINE=InnoDB;

-- EXAM SCHEDULES
CREATE TABLE IF NOT EXISTS exam_schedules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    exam_date DATE NOT NULL,
    exam_session ENUM('morning','afternoon') DEFAULT 'morning',
    subject_codes TEXT NOT NULL,  -- store JSON/text list of subject codes
    status ENUM('scheduled','ongoing','completed') DEFAULT 'scheduled',
    seat_allocation_completed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_exam_date (exam_date)
) ENGINE=InnoDB;

-- SEAT ALLOCATIONS (alternate allocation table)
CREATE TABLE IF NOT EXISTS seat_allocations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    exam_schedule_id INT NOT NULL,
    student_id INT NOT NULL,
    subject_code VARCHAR(15) NOT NULL,
    room_id INT NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    row_num INT NOT NULL,
    col_num INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_schedule_id) REFERENCES exam_schedules(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES exam_rooms(id) ON DELETE CASCADE,
    INDEX idx_exam_schedule (exam_schedule_id),
    INDEX idx_student (student_id),
    INDEX idx_room (room_id),
    UNIQUE KEY unique_exam_seat (exam_schedule_id, room_id, seat_number)
) ENGINE=InnoDB;

-- ALLOCATED_DESKS (aggregated desks per session)
CREATE TABLE IF NOT EXISTS allocated_desks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    desk_id VARCHAR(50) NOT NULL,
    student1_usn VARCHAR(20),
    student1_name VARCHAR(100),
    student2_usn VARCHAR(20),
    student2_name VARCHAR(100),
    room_code VARCHAR(20) NOT NULL,
    row_num INT NOT NULL,
    col_start INT NOT NULL,
    col_end INT NOT NULL,
    allocation_method VARCHAR(50) DEFAULT 'AI',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES allocation_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_desk_id (desk_id)
) ENGINE=InnoDB;

-- CHAT SESSIONS (for any chat/registration flows)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    student_usn VARCHAR(20),
    current_step VARCHAR(50) DEFAULT 'start',
    data TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id)
) ENGINE=InnoDB;

-- EMAIL LOGS
CREATE TABLE IF NOT EXISTS email_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    student_usn VARCHAR(20) NOT NULL,
    student_email VARCHAR(100) NOT NULL,
    email_type ENUM('seat_allocation','reminder','hall_ticket') DEFAULT 'seat_allocation',
    subject VARCHAR(255),
    sent_status ENUM('pending','sent','failed') DEFAULT 'pending',
    sent_at DATETIME NULL,
    error_message TEXT NULL,
    retry_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES allocation_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_student_usn (student_usn),
    INDEX idx_sent_status (sent_status)
) ENGINE=InnoDB;

-- SEATING PLAN ACCESS LOG
CREATE TABLE IF NOT EXISTS seating_plan_access_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    student_usn VARCHAR(20) NOT NULL,
    room_code VARCHAR(20) NOT NULL,
    access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_allowed BOOLEAN DEFAULT TRUE,
    minutes_before_exam INT,
    ip_address VARCHAR(50),
    FOREIGN KEY (session_id) REFERENCES allocation_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_student (session_id, student_usn),
    INDEX idx_access_time (access_time)
) ENGINE=InnoDB;

-- STAFF
CREATE TABLE IF NOT EXISTS staff (
    id INT AUTO_INCREMENT PRIMARY KEY,
    staff_id VARCHAR(20) UNIQUE NOT NULL,
    staff_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(15),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_staff_id (staff_id),
    INDEX idx_department (department)
) ENGINE=InnoDB;

-- STAFF ROOM ALLOCATIONS
CREATE TABLE IF NOT EXISTS staff_room_allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    staff_id VARCHAR(20) NOT NULL,
    room_code VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) DEFAULT 'Invigilator',
    allocated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_staff (staff_id),
    INDEX idx_room (room_code),
    UNIQUE KEY unique_allocation (session_id, staff_id, room_code)
) ENGINE=InnoDB;

-- SAMPLE VTU SUBJECTS
INSERT INTO subjects (subject_code, subject_name, semester, branch, credits, subject_type) VALUES
('21CS51', 'Management and Entrepreneurship', 5, 'CSE', 3, 'theory'),
('21CS52', 'Computer Networks', 5, 'CSE', 4, 'theory'),
('21CS53', 'Database Management System', 5, 'CSE', 4, 'theory'),
('21CS54', 'Automata Theory and Computability', 5, 'CSE', 4, 'theory'),
('21CS55', 'Application Development using Python', 5, 'CSE', 3, 'theory'),
('21CSL56', 'DBMS Laboratory', 5, 'CSE', 2, 'practical'),
('21CS61', 'Computer Graphics and Visualization', 6, 'CSE', 4, 'theory');

-- SAMPLE EXAM ROOMS
INSERT INTO exam_rooms (room_code, room_name, capacity, `rows`, cols) VALUES
('R001', 'Main Hall - Block A', 60, 10, 6),
('R002', 'Classroom - Block A', 40, 8, 5),
('R003', 'Auditorium - Block B', 100, 15, 7);

-- End of schema
