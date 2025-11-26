# COMPLETE VTU Exam Registration System with AI Seat Allocation
from flask import Flask, render_template, request, jsonify, session, redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, distinct, text, and_, or_
import uuid
import json
import re
from datetime import datetime, date
import traceback
import random
import numpy as np
from deap import algorithms, base, creator, tools
from collections import defaultdict
import math
import random
from itertools import combinations
from datetime import datetime
from typing import List, Dict, Tuple, Optional

app = Flask(__name__)
app.secret_key = 'vtu_chatbot_secret_key_2024'
app.config['SESSION_TYPE'] = 'filesystem'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:SanjanaBs%4018@localhost/vtu_exam_registration'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    usn = db.Column(db.String(20), unique=True, nullable=False, index=True)
    branch = db.Column(db.String(50), nullable=False, index=True)
    semester = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    has_backlogs = db.Column(db.Boolean, default=False)
    current_semester = db.Column(db.Integer)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(15), nullable=False, unique=True, index=True)
    subject_name = db.Column(db.String(150), nullable=False)
    semester = db.Column(db.Integer, nullable=False, index=True)
    branch = db.Column(db.String(50), nullable=False, index=True)
    credits = db.Column(db.Integer, default=4)
    subject_type = db.Column(db.Enum('theory', 'practical', 'project', name='subject_type'), default='theory')
    is_core = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentSubject(db.Model):
    __tablename__ = 'student_subjects'
    id = db.Column(db.Integer, primary_key=True)
    usn = db.Column(db.String(20), nullable=False, index=True)  # Instead of student_id
    student_name = db.Column(db.String(100), nullable=False)    # New field
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True, index=True)
    subject_code = db.Column(db.String(15), nullable=False, index=True)
    subject_name = db.Column(db.String(150), nullable=False)
    semester = db.Column(db.Integer, nullable=False, index=True)
    is_backlog = db.Column(db.Boolean, default=False)
    registration_type = db.Column(db.Enum('regular', 'backlog', 'improvement', name='reg_type'), default='regular')
    exam_fee_paid = db.Column(db.Boolean, default=False)
    hall_ticket_generated = db.Column(db.Boolean, default=False)
    seat_allocated = db.Column(db.Boolean, default=False)
    allocated_room = db.Column(db.String(20))
    allocated_seat = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    student_usn = db.Column(db.String(20))
    current_step = db.Column(db.String(50), default='start')
    data = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamRoom(db.Model):
    __tablename__ = 'exam_rooms'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(20), nullable=False, unique=True, index=True)
    room_name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    rows = db.Column(db.Integer, nullable=False, default=10)
    cols = db.Column(db.Integer, nullable=False, default=6)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamSchedule(db.Model):
    __tablename__ = 'exam_schedules'
    id = db.Column(db.Integer, primary_key=True)
    exam_date = db.Column(db.Date, nullable=False, index=True)
    exam_session = db.Column(db.Enum('morning', 'afternoon', name='exam_session'), default='morning')
    subject_codes = db.Column(db.Text, nullable=False)  # JSON array
    status = db.Column(db.Enum('scheduled', 'ongoing', 'completed', name='exam_status'), default='scheduled')
    seat_allocation_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SeatAllocation(db.Model):
    __tablename__ = 'seat_allocations'
    id = db.Column(db.Integer, primary_key=True)
    exam_schedule_id = db.Column(db.Integer, db.ForeignKey('exam_schedules.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_code = db.Column(db.String(15), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('exam_rooms.id', ondelete='CASCADE'), nullable=False, index=True)
    seat_number = db.Column(db.String(10), nullable=False)
    row_num = db.Column(db.Integer, nullable=False)
    col_num = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AllocationSession(db.Model):
    __tablename__ = 'allocation_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    subject_codes = db.Column(db.Text, nullable=False)  # JSON array
    algorithm_used = db.Column(db.String(50), default='genetic')
    total_students = db.Column(db.Integer, default=0)
    total_rooms = db.Column(db.Integer, default=0)
    total_desks = db.Column(db.Integer, default=0)  # NEW: Track desks used
    fitness_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    exam_date = db.Column(db.Date, nullable=True)
    exam_time = db.Column(db.Time, nullable=True)
    exam_duration = db.Column(db.Integer, default=180)
    emails_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)


class DetailedAllocation(db.Model):
    __tablename__ = 'detailed_allocations'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False, index=True)
    student_usn = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(15), nullable=False)
    subject_name = db.Column(db.String(150), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    room_code = db.Column(db.String(20), nullable=False)
    room_name = db.Column(db.String(100), nullable=False)
    seat_number = db.Column(db.String(20), nullable=False)
    row_num = db.Column(db.Integer, nullable=False)
    col_num = db.Column(db.Integer, nullable=False)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    hall_ticket_viewed = db.Column(db.Boolean, default=False)
    seating_plan_viewed = db.Column(db.Boolean, default=False)
    last_viewed_at = db.Column(db.DateTime, nullable=True)
    
    # NEW: Desk-based allocation fields
    desk_id = db.Column(db.String(50), nullable=True, index=True)  # Desk identifier
    desk_partner_usn = db.Column(db.String(20), nullable=True)     # Partner's USN
    desk_position = db.Column(db.String(10), nullable=True)        # 'LEFT' or 'RIGHT'
    
    allocation_method = db.Column(db.String(50), default='AI')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add indexes for better performance
    __table_args__ = (
        db.Index('idx_session_desk', session_id, desk_id),
        db.Index('idx_student_session', student_usn, session_id),
        db.Index('idx_room_session', room_code, session_id),
    )

class Desk(db.Model):
    __tablename__ = 'desks'
    
    id = db.Column(db.Integer, primary_key=True)
    desk_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    room_code = db.Column(db.String(20), nullable=False, index=True)
    room_name = db.Column(db.String(100), nullable=False)
    row = db.Column(db.Integer, nullable=False)
    col_start = db.Column(db.Integer, nullable=False)
    col_end = db.Column(db.Integer, nullable=False)
    seat1 = db.Column(db.String(10))
    seat2 = db.Column(db.String(10))
    capacity = db.Column(db.Integer, default=2)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key to exam_rooms
    __table_args__ = (
        db.ForeignKeyConstraint(['room_code'], ['exam_rooms.room_code'], ondelete='CASCADE'),
        db.Index('idx_room_code', 'room_code'),
        db.Index('idx_desk_id', 'desk_id'),
        db.Index('idx_row_col', 'row', 'col_start'),
        db.Index('idx_available', 'is_available'),
    )
    
    def __repr__(self):
        return f'<Desk {self.desk_id}>'
    
class Staff(db.Model):
    """Staff/Faculty members who will supervise exams"""
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.String(20), unique=True, nullable=False)
    staff_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff_name,
            'department': self.department,
            'email': self.email,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class StaffRoomAllocation(db.Model):
    """Maps staff members to examination rooms for a specific session"""
    __tablename__ = 'staff_room_allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False)
    staff_id = db.Column(db.String(20), nullable=False)
    room_code = db.Column(db.String(20), nullable=False)
    room_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='Invigilator')  # Invigilator, Chief Invigilator, etc.
    allocated_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'staff_id': self.staff_id,
            'room_code': self.room_code,
            'room_name': self.room_name,
            'role': self.role,
            'allocated_at': self.allocated_at.strftime('%Y-%m-%d %H:%M:%S') if self.allocated_at else None
        }


# ===================================================================
# MODEL 2: EmailLog Table
# ===================================================================

class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False, index=True)
    student_usn = db.Column(db.String(20), nullable=False, index=True)
    student_email = db.Column(db.String(100), nullable=False)
    email_type = db.Column(db.Enum('seat_allocation', 'reminder', 'hall_ticket', name='email_type_enum'), default='seat_allocation')
    subject = db.Column(db.String(255))
    sent_status = db.Column(db.Enum('pending', 'sent', 'failed', name='email_status_enum'), default='pending')
    sent_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key to allocation_sessions
    __table_args__ = (
        db.ForeignKeyConstraint(['session_id'], ['allocation_sessions.session_id'], ondelete='CASCADE'),
        db.Index('idx_session_id', 'session_id'),
        db.Index('idx_student_usn', 'student_usn'),
        db.Index('idx_sent_status', 'sent_status'),
        db.Index('idx_email_type', 'email_type'),
        db.Index('idx_sent_at', 'sent_at'),
    )
    
    def __repr__(self):
        return f'<EmailLog {self.student_usn} - {self.email_type}>'


# ===================================================================
# MODEL 3: SeatingPlanAccessLog Table
# ===================================================================

class SeatingPlanAccessLog(db.Model):
    __tablename__ = 'seating_plan_access_log'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False, index=True)
    student_usn = db.Column(db.String(20), nullable=False)
    room_code = db.Column(db.String(20), nullable=False)
    access_time = db.Column(db.DateTime, default=datetime.utcnow)
    access_allowed = db.Column(db.Boolean, default=True)
    minutes_before_exam = db.Column(db.Integer)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key to allocation_sessions
    __table_args__ = (
        db.ForeignKeyConstraint(['session_id'], ['allocation_sessions.session_id'], ondelete='CASCADE'),
        db.Index('idx_session_student', 'session_id', 'student_usn'),
        db.Index('idx_student_usn', 'student_usn'),
        db.Index('idx_access_time', 'access_time'),
        db.Index('idx_access_allowed', 'access_allowed'),
    )
    
    def __repr__(self):
        return f'<SeatingPlanAccessLog {self.student_usn} - {self.access_time}>'


# ===================================================================
# MODEL 4: AllocatedDesks Table (Optional but Recommended)
# ===================================================================

class AllocatedDesk(db.Model):
    __tablename__ = 'allocated_desks'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), nullable=False, index=True)
    desk_id = db.Column(db.String(50), nullable=False, index=True)
    student1_usn = db.Column(db.String(20))
    student1_name = db.Column(db.String(100))
    student2_usn = db.Column(db.String(20))
    student2_name = db.Column(db.String(100))
    room_code = db.Column(db.String(20), nullable=False)
    row_num = db.Column(db.Integer, nullable=False)
    col_start = db.Column(db.Integer, nullable=False)
    col_end = db.Column(db.Integer, nullable=False)
    allocation_method = db.Column(db.String(50), default='AI')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    __table_args__ = (
        db.ForeignKeyConstraint(['session_id'], ['allocation_sessions.session_id'], ondelete='CASCADE'),
        db.ForeignKeyConstraint(['desk_id'], ['desks.desk_id'], ondelete='CASCADE'),
        db.Index('idx_session_id', 'session_id'),
        db.Index('idx_desk_id', 'desk_id'),
        db.Index('idx_student1', 'student1_usn'),
        db.Index('idx_student2', 'student2_usn'),
        db.Index('idx_allocation_method', 'allocation_method'),
    )
    
    def __repr__(self):
        return f'<AllocatedDesk {self.desk_id} - {self.student1_usn}, {self.student2_usn}>'



# AI-Based Seat Allocation Engine
 # For more advanced genetic algorithm (optional - install with pip install deap)
try:
    from deap import algorithms, base, creator, tools
    DEAP_AVAILABLE = True
    
        
except ImportError:
    DEAP_AVAILABLE = False
    print("DEAP not available, using simple genetic algorithm")


class CompleteAISeatAllocator:
    """COMPLETE AI-powered seat allocation system with working algorithms"""
    
    def __init__(self):

        from deap import base, creator, tools, algorithms
        import numpy as np
    
    # Clear any existing definitions (prevents errors on reload)
        if hasattr(creator, 'FitnessMax'):
            del creator.FitnessMax
        if hasattr(creator, 'Individual'):
            del creator.Individual
    
    # Create fitness and individual classes
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))  # Maximize fitness
        creator.create("Individual", list, fitness=creator.FitnessMax)
    
        print("✅ DEAP creator classes initialized")
        self.algorithms = {
            'genetic': self._genetic_algorithm,
            'graph_coloring': self._graph_coloring_algorithm,
            'constraint_mapping': self._constraint_mapping_algorithm,
            'hybrid_ai': self._hybrid_ai_algorithm
           }
    
    def allocate_students_for_subjects(self, selected_subject_codes: list, algorithm: str = 'genetic',exam_date: str = None, exam_time: str = None) -> dict:
        
        try:
            print(f"🤖 Starting COLUMN-BASED AI allocation for subjects: {selected_subject_codes}")
            print(f"🧠 Using algorithm: {algorithm}")
            
            # Step 1: Get all students registered under selected subjects
            students = self._get_students_for_subjects(selected_subject_codes)
            
            if not students:
                return {
                    'success': False,
                    'message': 'No students found for the selected subjects',
                    'total_students': 0,
                    'selected_subjects': selected_subject_codes
                }
            
            print(f"👥 Found {len(students)} students across {len(selected_subject_codes)} subjects")

            # RANDOMIZE students for desk allocation
            random.shuffle(students)
            print("🎲 Students shuffled randomly for desk allocation")
            
            # Step 2: Get available exam rooms
            rooms = ExamRoom.query.filter_by(is_active=True).all()
            
            if not rooms:
                return {
                    'success': False,
                    'message': 'No exam rooms available',
                    'total_students': len(students),
                    'selected_subjects': selected_subject_codes
                }
            
            print(f"🏢 Found {len(rooms)} available rooms")
            
            # Step 3: Create desk positions (Each column = 1 desk)
            desks = self._create_desk_positions(rooms)
            total_desk_capacity = sum(desk.get('capacity', 2) for desk in desks)
            
            if len(students) > total_desk_capacity:
                return {
                    'success': False,
                    'message': f'Insufficient desk capacity: {len(students)} students need seats, but only {total_desk_capacity} desk seats available',
                    'total_students': len(students),
                    'total_capacity': total_desk_capacity,
                    'selected_subjects': selected_subject_codes
                }
            
            print(f"🪑 Available: {len(desks)} desks ({total_desk_capacity} seats total)")
            
            # ✅ FIXED: Handle ALL students (even odd numbers)
            print(f"✅ Allocating ALL {len(students)} students (including odd numbers if any)")
            
            # Step 4: Apply selected AI algorithm with DESK allocation
            algorithm_func = self.algorithms.get(algorithm, self._hybrid_ai_algorithm)
            allocations = algorithm_func(students, rooms)
            
            if not allocations:
                return {
                    'success': False,
                    'message': f'{algorithm} algorithm failed to generate desk-based seat allocations',
                    'total_students': len(students),
                    'selected_subjects': selected_subject_codes
                }
            
            # Step 5: Save allocations to database
            session_id = self.save_allocations_safely(allocations, selected_subject_codes, algorithm,exam_date=exam_date,exam_time=exam_time)
            
            if session_id == "error":
                return {
                    'success': False,
                    'message': 'Failed to save allocation results'
                }
            
            rooms_used = len({a['room_code'] for a in allocations})
            desks_used = len({a['desk_id'] for a in allocations if a.get('desk_id')}) 
            fitness = self._calculate_allocation_quality(allocations)
            
            return {
                'success': True,
                'message': f'Successfully allocated {len(allocations)} students to desks using {algorithm}',
                'total_students': len(students),
                'allocated_students': len(allocations),
                'desks_used': desks_used,
                'rooms_used': rooms_used,
                'algorithm_used': f'{algorithm.replace("_", " ").title()}',
                'session_id': session_id,
                'fitness_score': fitness,
                'efficiency': round(fitness * 100, 1),
                'selected_subjects': selected_subject_codes
            }
            
        except Exception as e:
            print(f"❌ AI allocation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'AI allocation failed: {str(e)}',
                'total_students': 0,
                'selected_subjects': selected_subject_codes
            }
    
    def _create_desk_positions(self, rooms: list) -> list:
        
        desks = []

        for room in rooms:
            print(f"🪑 Creating desks for {room.room_name}: {room.rows} rows × {room.cols} columns")

            desk_id = 1

            # Create one desk per (row, col) position
            # Each desk has capacity for 2 students (side by side)
            for col in range(1, room.cols + 1):
                for row in range(1, room.rows + 1):
                    desk = {
                        'desk_id': f"{room.room_code}_D{desk_id:03d}",
                        'room_id': room.id,
                        'room_code': room.room_code,
                        'room_name': room.room_name,
                        'row': row,
                        'col': col,
                        'capacity': 2,  # Each desk always has 2 seats
                        'seat1': f"R{row:02d}C{col:02d}_S1",
                        'seat2': f"R{row:02d}C{col:02d}_S2"
                    }
                    desks.append(desk)
                    desk_id += 1

            total_capacity = len(desks) * 2
            print(f"🪑 Room {room.room_code}: Created {len(desks)} desks with {total_capacity} total seats")

        print(f"🎯 Total: {len(desks)} desks created across all rooms")
        return desks

    def _allocate_students_to_desks(self, students: list, desks: list) -> list:
        
        allocations = []
        from collections import OrderedDict

        # Group desks by room
        room_desks = OrderedDict()
        for desk in desks:
            room_desks.setdefault(desk['room_code'], []).append(desk)

        desk_assignments = {desk['desk_id']: [] for desk in desks}
        remaining_students = students[:]

        print(f"🎯 Starting allocation: {len(remaining_students)} students to allocate")

        # Process each room completely before moving to next
        for room_code, desks_in_room in room_desks.items():
            if not remaining_students:
                print("✅ All students allocated!")
                break

            print(f"🏢 Processing room: {room_code}")

            # Sort desks by column first, then row (column by column, row by row)
            sorted_desks = sorted(desks_in_room, key=lambda d: (d['col'], d['row']))

            # Count total seats in this room
            total_seats_in_room = sum(desk.get('capacity', 2) for desk in sorted_desks)
            print(f"📍 Room {room_code} has {len(sorted_desks)} desks with {total_seats_in_room} total seats")

            # Fill every desk in order, completely before moving to next desk
            for desk in sorted_desks:
                if not remaining_students:
                    print("✅ All students allocated!")
                    break

                desk_id = desk['desk_id']
                capacity = desk.get('capacity', 2)
                col = desk['col']
                row = desk['row']

                # Fill both seats of this desk before moving to next desk
                for seat_num in range(capacity):
                    if not remaining_students:
                        break

                    # Check current occupancy
                    current_occupancy = len(desk_assignments[desk_id])
                    if current_occupancy >= capacity:
                        break

                    assigned = False
                    for _ in range(len(remaining_students) + 1):
                        student = remaining_students.pop(0)
                        conflict = self._check_student_conflicts(student, desk, desk_assignments)
                        if not conflict:
                            if current_occupancy == 0:
                                self._assign_single_student_to_desk(student, desk, desk_assignments, allocations)
                                print(f"✅ {student['usn']}")
                            else:
                                partner = desk_assignments[desk_id][0]
                                self._assign_single_student_to_desk(
                                     student, desk, desk_assignments, allocations, partner_usn=partner['usn']
                                 )   
                                print(f"✅ {student['usn']} ")
                                assigned = True
                                break 
                        remaining_students.append(student)
                    if not assigned and remaining_students:
                        student = remaining_students.pop(0)    
                        if current_occupancy == 0:
                            self._assign_single_student_to_desk(student, desk, desk_assignments, allocations)
                        else:
                            partner = desk_assignments[desk_id][0]
                            self._assign_single_student_to_desk(
                                 student, desk, desk_assignments, allocations, partner_usn=partner['usn']
                                     )      
                        print(f"🔄 Forced {student['usn']} ")      

        # Handle any remaining students (emergency allocation)
        if remaining_students:
            print(f"🚨 Emergency allocation for {len(remaining_students)} remaining students")
            while remaining_students:
                student = remaining_students.pop(0)
                emergency_desk = self._get_or_create_emergency_desk(desks, desk_assignments)
                self._assign_single_student_to_desk(student, emergency_desk, desk_assignments, allocations)
                print(f"🚨 Emergency: {student['usn']} → {emergency_desk['desk_id']}")

        print(f"🎯 FINAL: {len(allocations)} students allocated, {len(remaining_students)} unallocated")
        return allocations

    def _assign_students_to_desk(self, student1: dict, student2: dict, desk: dict, desk_assignments: dict, allocations: list):
        
        # Student 1
        allocation1 = {
            'usn': student1['usn'],
            'student_name': student1['name'],
            'subject_code': student1['subject_code'],
            'subject_name': student1['subject_name'],
            'branch': student1['branch'],
            'room_id': desk['room_id'],
            'room_code': desk['room_code'],
            'room_name': desk['room_name'],
            'desk_id': desk['desk_id'],
            'seat_number': desk['seat1'],
            'row_num': desk['row'],
            'col_num': desk['col_start'],
            'desk_partner_usn': student2['usn'],
            'allocation_method': 'AI-Desk-Pairing'
        }
        
        # Student 2
        allocation2 = {
            'usn': student2['usn'],
            'student_name': student2['name'],
            'subject_code': student2['subject_code'],
            'subject_name': student2['subject_name'],
            'branch': student2['branch'],
            'room_id': desk['room_id'],
            'room_code': desk['room_code'],
            'room_name': desk['room_name'],
            'desk_id': desk['desk_id'],
            'seat_number': desk['seat2'] or f"R{desk['row']:02d}C{desk['col_end']:02d}",
            'row_num': desk['row'],
            'col_num': desk['col_end'],
            'desk_partner_usn': student1['usn'],
            'allocation_method': 'AI-Desk-Pairing'
        }
        
        desk_assignments[desk['desk_id']].extend([allocation1, allocation2])
        allocations.extend([allocation1, allocation2])

    def _assign_single_student_to_desk(self, student: dict, desk: dict, desk_assignments: dict, allocations: list, partner_usn: str = None):
        
        current_occupancy = len(desk_assignments[desk['desk_id']])
        
        # Determine seat position
        if current_occupancy == 0:
            seat_number = desk['seat1']
            col_num = desk['col_start']
        else:
            seat_number = desk['seat2'] or f"R{desk['row']:02d}C{desk['col_end']:02d}"
            col_num = desk['col_end']
        
        allocation = {
            'usn': student['usn'],
            'student_name': student['name'],
            'subject_code': student['subject_code'],
            'subject_name': student['subject_name'],
            'branch': student['branch'],
            'room_id': desk['room_id'],
            'room_code': desk['room_code'],
            'room_name': desk['room_name'],
            'desk_id': desk['desk_id'],
            'seat_number': seat_number,
            'row_num': desk['row'],
            'col_num': col_num,
            'desk_partner_usn': partner_usn,
            'allocation_method': 'AI-Desk-Single' + ('-Conflict' if partner_usn else '')
        }
        
        desk_assignments[desk['desk_id']].append(allocation)
        allocations.append(allocation)

    def _get_or_create_emergency_desk(self, desks: list, desk_assignments: dict) -> dict:
        
        # First try to find any desk with space
        for desk in desks:
            if len(desk_assignments[desk['desk_id']]) < desk.get('capacity', 2):
                return desk
        
        # Create emergency desk if no space available
        emergency_desk = {
            'desk_id': f"EMERGENCY_D{len(desks) + 1:03d}",
            'room_id': desks[0]['room_id'] if desks else 1,
            'room_code': desks[0]['room_code'] if desks else 'EMRG',
            'room_name': desks[0]['room_name'] if desks else 'Emergency Room',
            'row': 1,
            'col_start': 1,
            'col_end': 2,
            'seat1': 'EMRG_01',
            'seat2': 'EMRG_02',
            'capacity': 2
        }
        
        desks.append(emergency_desk)
        desk_assignments[emergency_desk['desk_id']] = []
        return emergency_desk
    
    def _genetic_algorithm(self, students: list, rooms: list) -> list:
        
        try:
            print("🧬 Running Genetic Algorithm with desk-based allocation...")
            
            # Create desk positions (2 students per desk)
            desks = self._create_desk_positions(rooms)
            
            if len(students) > len(desks) * 2:
                students = students[:len(desks) * 2]
            
            if DEAP_AVAILABLE:
                return self._advanced_genetic_algorithm_desks(students, desks)
            else:
                return self._simple_genetic_algorithm_desks(students, desks)
                
        except Exception as e:
            print(f"Genetic algorithm error: {e}")
            return self._fallback_desk_allocation(students, self._create_desk_positions(rooms))
    
    def _simple_genetic_algorithm_desks(self, students: list, desks: list) -> list:
        
        population_size = min(50, max(10, len(students) // 2))
        generations = min(100, max(20, len(students)))
        
        # Create initial population (student pairs for desks)
        population = []
        for _ in range(population_size):
            student_pairs = self._create_random_desk_pairs(students)
            population.append(student_pairs)
        
        # Evolve population
        for generation in range(generations):
            fitness_scores = []
            for individual in population:
                score = self._evaluate_desk_fitness(individual, desks)
                fitness_scores.append(score)
            
            # Selection and reproduction
            new_population = []
            
            # Elitism
            sorted_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)
            elite_count = max(1, population_size // 10)
            
            for i in range(elite_count):
                new_population.append([pair.copy() for pair in population[sorted_indices[i]]])
            
            # Generate offspring
            while len(new_population) < population_size:
                parent1 = self._tournament_selection_desks(population, fitness_scores)
                parent2 = self._tournament_selection_desks(population, fitness_scores)
                
                child1, child2 = self._crossover_desks(parent1, parent2)
                self._mutate_desks(child1)
                self._mutate_desks(child2)
                
                new_population.extend([child1, child2])
            
            population = new_population[:population_size]
        
        # Get best solution
        final_fitness = [self._evaluate_desk_fitness(ind, desks) for ind in population]
        best_index = max(range(len(final_fitness)), key=lambda i: final_fitness[i])
        best_pairs = population[best_index]
        
        return self._convert_desk_pairs_to_allocations(best_pairs, desks, 'Genetic Algorithm')
    
    def _create_random_desk_pairs(self, students: list) -> list:
       
        shuffled_students = students.copy()
        random.shuffle(shuffled_students)
        
        pairs = []
        for i in range(0, len(shuffled_students), 2):
            if i + 1 < len(shuffled_students):
                pair = [shuffled_students[i], shuffled_students[i + 1]]
                pairs.append(pair)
        
        return pairs
    
    def _evaluate_desk_fitness(self, student_pairs: list, desks: list) -> float:
        
        fitness = 0.0
        
        # Evaluate each desk pair
        for pair in student_pairs:
            if len(pair) == 2:
                student1, student2 = pair
                
                # CRITICAL CONSTRAINT: Same subject + same branch = HEAVY PENALTY
                if (student1['subject_code'] == student2['subject_code'] and 
                    student1['branch'] == student2['branch']):
                    fitness -= 50  # Heavy penalty
                
                # Same subject but different branch = moderate penalty
                elif student1['subject_code'] == student2['subject_code']:
                    fitness -= 20
                
                # Same branch but different subject = light penalty
                elif student1['branch'] == student2['branch']:
                    fitness -= 10
                
                # Different subject AND different branch = BONUS
                else:
                    fitness += 15
        
        return fitness
    
    def _tournament_selection_desks(self, population: list, fitness_scores: list, tournament_size: int = 3) -> list:
        
        tournament_indices = random.sample(range(len(population)), min(tournament_size, len(population)))
        best_index = max(tournament_indices, key=lambda i: fitness_scores[i])
        return [pair.copy() for pair in population[best_index]]
    
    def _crossover_desks(self, parent1: list, parent2: list) -> tuple:
        
        child1 = [pair.copy() for pair in parent1]
        child2 = [pair.copy() for pair in parent2]
        
        if len(child1) > 1 and len(child2) > 1:
            crossover_point = random.randint(1, min(len(child1), len(child2)) - 1)
            child1[crossover_point:], child2[crossover_point:] = child2[crossover_point:], child1[crossover_point:]
        
        return child1, child2
    
    def _mutate_desks(self, student_pairs: list, mutation_rate: float = 0.2):
        
        if len(student_pairs) > 1 and random.random() < mutation_rate:
            pair1_idx = random.randint(0, len(student_pairs) - 1)
            pair2_idx = random.randint(0, len(student_pairs) - 1)
            
            if pair1_idx != pair2_idx:
                pair1 = student_pairs[pair1_idx]
                pair2 = student_pairs[pair2_idx]
                
                if len(pair1) == 2 and len(pair2) == 2:
                    student1_pos = random.randint(0, 1)
                    student2_pos = random.randint(0, 1)
                    pair1[student1_pos], pair2[student2_pos] = pair2[student2_pos], pair1[student1_pos]
    
    def _convert_desk_pairs_to_allocations(self, student_pairs: list, desks: list, method: str) -> list:
       
        allocations = []
        
        for i, pair in enumerate(student_pairs):
            if i < len(desks) and len(pair) == 2:
                desk = desks[i]
                col = desk['col'] 
                
                # First student
                allocation1 = {
                    'usn': pair[0]['usn'],
                    'student_name': pair[0]['name'],
                    'subject_code': pair[0]['subject_code'],
                    'subject_name': pair[0]['subject_name'],
                    'branch': pair[0]['branch'],
                    'semester': pair[0]['semester'],
                    'room_id': desk['room_id'],
                    'room_code': desk['room_code'],
                    'room_name': desk['room_name'],
                    'seat_number': desk['seat1'],
                    'row_num': desk['row'],
                    'col_num': col,
                    'desk_id': desk['desk_id'],
                    'desk_partner_usn': pair[1]['usn'],
                    'allocation_method': method
                }
                
                # Second student
                allocation2 = {
                    'usn': pair[1]['usn'],
                    'student_name': pair[1]['name'],
                    'subject_code': pair[1]['subject_code'],
                    'subject_name': pair[1]['subject_name'],
                    'branch': pair[1]['branch'],
                    'semester': pair[1]['semester'],
                    'room_id': desk['room_id'],
                    'room_code': desk['room_code'],
                    'room_name': desk['room_name'],
                    'seat_number': desk['seat2'],
                    'row_num': desk['row'],
                    'col_num': col,
                    'desk_id': desk['desk_id'],
                    'desk_partner_usn': pair[0]['usn'],
                    'allocation_method': method
                }
                
                allocations.extend([allocation1, allocation2])
        
        return allocations
        
    
    def _graph_coloring_algorithm(self, students: list, rooms: list) -> list:
        
        try:
            print("🎨 Running Graph Coloring Algorithm with desk-based allocation...")
            
            # Create conflict graph for desk pairing
            conflicts = defaultdict(set)
            
            for i, student1 in enumerate(students):
                for j, student2 in enumerate(students):
                    if i != j:
                        # Strong conflict: same subject + same branch
                        if (student1['branch'] == student2['branch'] and 
                            student1['subject_code'] == student2['subject_code']):
                            conflicts[i].add(j)
                            conflicts[j].add(i)
            
            # Create optimal student pairs
            student_pairs = []
            used_students = set()
            
            # Sort by conflict count for better pairing
            student_indices = sorted(range(len(students)), 
                                   key=lambda i: len(conflicts[i]), reverse=True)
            
            for student_idx in student_indices:
                if student_idx in used_students:
                    continue
                
                # Find best partner (different subject + different branch)
                best_partner = None
                best_score = -1
                
                for partner_idx in range(len(students)):
                    if (partner_idx != student_idx and 
                        partner_idx not in used_students and 
                        partner_idx not in conflicts[student_idx]):
                        
                        student = students[student_idx]
                        partner = students[partner_idx]
                        
                        # Calculate pairing score
                        score = 0
                        if student['subject_code'] != partner['subject_code']:
                            score += 5
                        if student['branch'] != partner['branch']:
                            score += 3
                        
                        if score > best_score:
                            best_score = score
                            best_partner = partner_idx
                
                if best_partner is not None:
                    pair = [students[student_idx], students[best_partner]]
                    student_pairs.append(pair)
                    used_students.add(student_idx)
                    used_students.add(best_partner)
            
            # Create desk positions and convert to allocations
            desks = self._create_desk_positions(rooms)
            allocations = self._convert_desk_pairs_to_allocations(student_pairs, desks, 'Graph Coloring')
            
            print(f"🎨 Graph coloring created {len(student_pairs)} desk pairs ({len(allocations)} allocations)")
            return allocations
            
        except Exception as e:
            print(f"Graph coloring error: {e}")
            return self._fallback_desk_allocation(students, self._create_desk_positions(rooms))
    
    def _constraint_mapping_algorithm(self, students: list, rooms: list) -> list:
        
        try:
            print("🗺️ Running Constraint Mapping Algorithm with desk-based allocation...")
            
            desks = self._create_desk_positions(rooms)
            student_pairs_indices = []
            used_students = set()
            
            # Group students by branch and subject
            branch_subject_groups = defaultdict(list)
            for i, student in enumerate(students):
                key = f"{student['branch']}_{student['subject_code']}"
                branch_subject_groups[key].append(i)
            
            # Create pairs ensuring different combinations
            group_keys = list(branch_subject_groups.keys())
            
            for i, key1 in enumerate(group_keys):
                for j, key2 in enumerate(group_keys):
                    if i >= j:
                        continue
                    
                    group1_indices = branch_subject_groups[key1]
                    group2_indices = branch_subject_groups[key2]
                    
                    min_pairs = min(len(group1_indices), len(group2_indices))
                    
                    for k in range(min_pairs):
                        idx1 = group1_indices[k]
                        idx2 = group2_indices[k]
                            
                        if idx1 not in used_students and idx2 not in used_students:
                            student_pairs_indices.append((idx1, idx2))
                            used_students.add(idx1)
                            used_students.add(idx2)
            
            # Handle remaining students
            remaining_indices = [i for i, student in enumerate(students) if i not in used_students]
            
            for i in range(0, len(remaining_indices) - 1, 2):
                idx1 = remaining_indices[i]
                idx2 = remaining_indices[i + 1]
                student_pairs_indices.append((idx1, idx2))  # ✅ Tuple of two INTEGERS
                used_students.add(idx1)
                used_students.add(idx2)
            if len(remaining_indices) % 2 == 1:
                last_idx = remaining_indices[-1]
            # Pair with itself (will sit alone at desk)
                student_pairs_indices.append((last_idx, last_idx))  # ✅ Same index twice
                print(f"⚠️ Odd student: {students[last_idx].get('usn')} will sit alone")
        
                print(f"📦 Total pairs created: {len(student_pairs_indices)}")
            allocations = self._convert_desk_pairs_to_allocations(student_pairs_indices, students,desks, 'Constraint Mapping')
            
            print(f"🗺️ Constraint mapping created {len(student_pairs_indices)} desk pairs ({len(allocations)} allocations)")
            return allocations
            
        except Exception as e:
            print(f"Constraint mapping error: {e}")
            return self._fallback_desk_allocation(students, self._create_desk_positions(rooms))
    
    def _hybrid_ai_algorithm(self, students: list, rooms: list) -> list:
        
        try:
            print("🤖 Running Hybrid AI Algorithm with desk-based allocation...")
            
            # Phase 1: Initial allocation using constraint mapping
            initial_allocation = self._constraint_mapping_algorithm(students, rooms)
            
            # Phase 2: Improve using genetic algorithm (if enough students)
            if len(students) >= 20:
                try:
                    genetic_allocation = self._genetic_algorithm(students, rooms)
                    
                    initial_quality = self._calculate_allocation_quality(initial_allocation)
                    genetic_quality = self._calculate_allocation_quality(genetic_allocation)
                    
                    if genetic_quality > initial_quality:
                        print(f"🤖 Using genetic result (quality: {genetic_quality:.3f} vs {initial_quality:.3f})")
                        return genetic_allocation
                    else:
                        print(f"🤖 Using constraint result (quality: {initial_quality:.3f} vs {genetic_quality:.3f})")
                        return initial_allocation
                        
                except:
                    print("🤖 Genetic phase failed, using constraint mapping result")
                    return initial_allocation
            else:
                print("🤖 Too few students for genetic optimization, using constraint mapping")
                return initial_allocation
                
        except Exception as e:
            print(f"Hybrid AI error: {e}")
            return self._fallback_desk_allocation(students, self._create_desk_positions(rooms))
    
    def _fallback_desk_allocation(self, students: list, desks: list) -> list:
        
        print("⚠️ Using fallback desk allocation method")
        
        # Simple random pairing
        shuffled_students = students.copy()
        random.shuffle(shuffled_students)
        
        student_pairs = []
        for i in range(0, len(shuffled_students), 2):
            if i + 1 < len(shuffled_students):
                pair = [shuffled_students[i], shuffled_students[i + 1]]
                student_pairs.append(pair)
        
        return self._convert_desk_pairs_to_allocations(student_pairs, desks, 'Fallback')
    
    def _calculate_allocation_quality(self, allocations: list) -> float:
        
        if not allocations:
            return 0.0
        
        quality = 0.0
        total_desk_pairs = 0
        
        # Group allocations by desk_id
        desk_groups = defaultdict(list)
        for alloc in allocations:
            if 'desk_id' in alloc:
                desk_groups[alloc['desk_id']].append(alloc)
        
        # Evaluate each desk pair
        for desk_id, desk_students in desk_groups.items():
            if len(desk_students) == 2:
                total_desk_pairs += 1
                student1, student2 = desk_students
                
                # Same subject + same branch = heavy penalty
                if (student1['subject_code'] == student2['subject_code'] and 
                    student1['branch'] == student2['branch']):
                    quality -= 10
                
                # Same subject but different branch = moderate penalty
                elif student1['subject_code'] == student2['subject_code']:
                    quality -= 5
                
                # Same branch but different subject = light penalty
                elif student1['branch'] == student2['branch']:
                    quality -= 2
                
                # Different subject AND different branch = bonus
                else:
                    quality += 5
        
        return quality / max(total_desk_pairs, 1) if total_desk_pairs > 0 else 0.5    

    def _get_students_for_subjects(self, subject_codes: list) -> list:
        """Get all students registered under the selected subjects"""
        try:
            students_query = db.session.query(
                StudentSubject.usn,
                StudentSubject.student_name,
                StudentSubject.subject_code,
                StudentSubject.subject_name,
                Student.branch,
                Student.semester,
                Student.email
            ).join(Student, StudentSubject.usn == Student.usn)\
             .filter(StudentSubject.subject_code.in_(subject_codes))\
             .order_by(Student.branch, StudentSubject.usn)
            
            students_data = students_query.all()
            
            students = []
            for student in students_data:
                students.append({
                    'usn': student.usn,
                    'name': student.student_name,
                    'subject_code': student.subject_code,
                    'subject_name': student.subject_name,
                    'branch': student.branch,
                    'semester': student.semester,
                    'email': student.email
                })
            
            random.shuffle(students)
            print(f"📊 Found {len(students)} students for subjects: {subject_codes}")
            
            return students
            
        except Exception as e:
            print(f"Error getting students: {e}")
            return []


    # def _save_allocations_to_database(self, allocations: list, subject_codes: list, algorithm: str) -> str:
    #     """Save desk-based allocations to database - FIXED"""
    #     try:
    #         session_id = str(uuid.uuid4())[:8]

    #         # Count unique desks
    #         unique_desks = len(set(alloc.get('desk_id') for alloc in allocations if alloc.get('desk_id')))

    #         # Create allocation session record
    #         allocation_session = AllocationSession(
    #             session_id=session_id,
    #             subject_codes=json.dumps(subject_codes),
    #             algorithm_used=f"{algorithm} (Desk-based)",
    #             total_students=len(allocations),
    #             total_rooms=len(set(alloc.get('room_id', alloc.get('room_code', 'unknown')) for alloc in allocations)),
    #             total_desks=unique_desks,
    #             fitness_score=self._calculate_allocation_quality(allocations)
    #         )
    #         db.session.add(allocation_session)

    #         # Save ALL detailed allocations with desk info
    #         for alloc in allocations:
    #             detailed_allocation = DetailedAllocation(
    #                 session_id=session_id,
    #                 student_usn=alloc['usn'],
    #                 student_name=alloc['student_name'],
    #                 subject_code=alloc['subject_code'],
    #                 subject_name=alloc['subject_name'],
    #                 branch=alloc['branch'],
    #                 room_code=alloc['room_code'],
    #                 room_name=alloc['room_name'],
    #                 seat_number=alloc['seat_number'],
    #                 row_num=alloc['row_num'],
    #                 col_num=alloc['col_num'],
    #                 desk_id=alloc.get('desk_id'),
    #                 desk_partner_usn=alloc.get('desk_partner_usn'),
    #                 allocation_method=alloc['allocation_method']
    #             )
    #             db.session.add(detailed_allocation)

    #         # Commit once at the end
    #         db.session.commit()
    #         print(f"💾 Saved {len(allocations)} desk-based allocations with {unique_desks} desks, session ID: {session_id}")

    #         return session_id

    #     except Exception as e:
    #         db.session.rollback()
    #         print(f"Error saving allocations: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         return "error"
        
    # Keep your existing methods that don't need changes
    def _advanced_genetic_algorithm(self, students: list, positions: list) -> list:
        """
        Advanced genetic algorithm for position-based allocation
        FIXED: Properly initializes indices without toolbox.attr_student error
        """
        try:
            if not students or not positions:
                return self._fallback_allocation(students, positions)
            
            toolbox = base.Toolbox()
            
            # FIXED: Create a function that returns a valid individual
            def create_individual():
                """Create random permutation of student indices"""
                return random.sample(range(len(students)), len(students))
            
            # FIXED: Use tools.initIterate properly
            toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            
            # Genetic operators
            toolbox.register("evaluate", self._evaluate_fitness_deap, students=students, positions=positions)
            toolbox.register("mate", tools.cxPartialyMatched)
            toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.1)
            toolbox.register("select", tools.selTournament, tournsize=3)
            
            # Create population
            pop_size = min(50, max(20, len(students)))
            population = toolbox.population(n=pop_size)
            
            # Hall of fame
            hof = tools.HallOfFame(1)
            
            # Statistics
            stats = tools.Statistics(lambda ind: ind.fitness.values)
            stats.register("avg", np.mean)
            stats.register("max", np.max)
            
            # Run algorithm
            generations = min(50, max(20, len(students) // 2))
            population, logbook = algorithms.eaSimple(
                population, toolbox,
                cxpb=0.7,      # Crossover probability
                mutpb=0.2,     # Mutation probability
                ngen=generations,
                stats=stats,
                halloffame=hof,
                verbose=False
            )
            
            if hof and len(hof) > 0:
                best_individual = hof[0]
                return self._convert_to_allocations(
                    best_individual, 
                    students, 
                    positions, 
                    'Advanced Genetic Algorithm'
                )
            else:
                return self._fallback_allocation(students, positions)
                
        except Exception as e:
            print(f"⚠️  Advanced genetic algorithm error: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_allocation(students, positions)

    def _advanced_genetic_algorithm_desks(self, students: list, desks: list) -> list:
        """
        Advanced genetic algorithm for desk-based seating allocation
        FIXED: Properly initializes without toolbox.attr_student error
        """
        try:
            if not students or not desks:
                return self._fallback_desk_allocation(students, desks)
            
            toolbox = base.Toolbox()
            
            # FIXED: Create a function that returns random desk pairs
            def create_desk_pairs():
                """Create random desk pair assignments"""
                pairs = []
                shuffled_students = students.copy()
                random.shuffle(shuffled_students)
                
                for i in range(0, len(shuffled_students) - 1, 2):
                    pairs.append((i, i + 1))
                
                return pairs
            
            # FIXED: Use proper individual creation
            toolbox.register("individual", tools.initIterate, creator.Individual, create_desk_pairs)
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            
            # Genetic operators
            toolbox.register("evaluate", self._evaluate_desk_fitness_deap, students=students, desks=desks)
            toolbox.register("mate", self._crossover_desk_pairs)
            toolbox.register("mutate", self._mutate_desk_pairs, indpb=0.2)
            toolbox.register("select", tools.selTournament, tournsize=3)
            
            # Create population
            pop_size = min(30, max(10, len(students) // 4))
            population = toolbox.population(n=pop_size)
            
            # Hall of fame
            hof = tools.HallOfFame(1)
            
            # Run algorithm
            generations = min(50, max(20, len(students) // 2))
            algorithms.eaSimple(
                population, toolbox,
                cxpb=0.6,      # Crossover probability
                mutpb=0.3,     # Mutation probability
                ngen=generations,
                halloffame=hof,
                verbose=False
            )
            
            if hof and len(hof) > 0:
                best_pairs = hof[0]
                return self._convert_desk_pairs_to_allocations(
                    best_pairs, 
                    students,
                    desks, 
                    'Advanced Genetic Algorithm (Desks)'
                )
            else:
                return self._fallback_desk_allocation(students, desks)
                
        except Exception as e:
            print(f"⚠️  Advanced genetic algorithm error: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_desk_allocation(students, desks)

    def _evaluate_fitness_deap(self, individual, students, positions):
        """
        DEAP-compatible fitness evaluation for position-based allocation
        Returns tuple (fitness,) for DEAP
        """
        try:
            fitness = 0.0
            
            # Evaluate adjacency penalties
            for i in range(len(individual) - 1):
                if i < len(positions) - 1:
                    idx1 = individual[i]
                    idx2 = individual[i + 1]
                    
                    if idx1 < len(students) and idx2 < len(students):
                        student1 = students[idx1]
                        student2 = students[idx2]
                        pos1 = positions[i]
                        pos2 = positions[i + 1]
                        
                        # Check if same room and adjacent seats
                        if pos1.get('room_id') == pos2.get('room_id'):
                            # Same branch penalty
                            if student1.get('branch') == student2.get('branch'):
                                fitness -= 5
                            
                            # Same subject penalty
                            if student1.get('subject_code') == student2.get('subject_code'):
                                fitness -= 10
                            
                            # Different branch bonus
                            else:
                                fitness += 2
            
            # Room distribution bonus
            from collections import defaultdict
            room_counts = defaultdict(int)
            for i, idx in enumerate(individual):
                if i < len(positions) and idx < len(students):
                    room_counts[positions[i].get('room_id')] += 1
            
            # Bonus for balanced room usage
            if len(room_counts) > 1:
                counts = list(room_counts.values())
                avg_count = sum(counts) / len(counts)
                variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
                fitness = fitness + max(0, 10 - variance)
            
            return (fitness,)
            
        except Exception as e:
            print(f"Error in fitness evaluation: {e}")
            return (0,)

    def _evaluate_desk_fitness_deap(self, pair_indices, students, desks):
        """
        DEAP-compatible fitness evaluation for desk pairs
        Returns tuple (fitness,) for DEAP
        """
        try:
            fitness = 0.0
            
            # Evaluate desk pairings
            valid_pairs = 0
            for i, (idx1, idx2) in enumerate(pair_indices):
                if i < len(desks):
                    # Validate indices
                    if idx1 < len(students) and idx2 < len(students) and idx1 != idx2:
                        student1 = students[idx1]
                        student2 = students[idx2]
                        
                        # Same subject + different branch = excellent
                        if (student1.get('subject_code') == student2.get('subject_code')):
                            if student1.get('branch') != student2.get('branch'):
                                fitness += 5  # Bonus
                            else:
                                fitness -= 10  # Penalty for same branch+subject
                        else:
                            # Different subject - always good
                            fitness += 3
                        
                        valid_pairs += 1
            
            # Bonus for using many desks
            fitness += valid_pairs * 0.5
            
            return (fitness,)
            
        except Exception as e:
            print(f"Error in desk fitness evaluation: {e}")
            return (0,)

    def _crossover_desk_pairs(self, ind1, ind2):
        """
        Crossover for desk pairs
        """
        try:
            if len(ind1) == 0 or len(ind2) == 0:
                return ind1, ind2
            
            size = min(len(ind1), len(ind2))
            start = random.randint(0, size - 1)
            end = random.randint(start, size - 1)
            
            # Swap sections
            ind1_copy = ind1[:]
            ind2_copy = ind2[:]
            
            ind1[start:end] = ind2_copy[start:end]
            ind2[start:end] = ind1_copy[start:end]
            
            return ind1, ind2
            
        except Exception as e:
            print(f"Error in crossover: {e}")
            return ind1, ind2

    def _mutate_desk_pairs(self, individual, indpb=0.2):
        """
        Mutation for desk pairs (swap mutation)
        """
        try:
            for i in range(len(individual)):
                if random.random() < indpb and len(individual) > 0:
                    # Swap with random pair
                    j = random.randint(0, len(individual) - 1)
                    individual[i], individual[j] = individual[j], individual[i]
            
            return (individual,)
            
        except Exception as e:
            print(f"Error in mutation: {e}")
            return (individual,)

    def _convert_to_allocations(self, individual, students, positions, algorithm_name):
        """
        Convert best individual to allocations
        """
        try:
            allocations = []
            
            for pos_idx, student_idx in enumerate(individual):
                if pos_idx < len(positions) and student_idx < len(students):
                    position = positions[pos_idx]
                    student = students[student_idx]
                    
                    allocation = {
                        'usn': student.get('usn', f'student_{student_idx}'),
                        'student_name': student.get('name', 'Unknown'),
                        'subject_code': student.get('subject_code', ''),
                        'subject_name': student.get('subject_name', ''),
                        'branch': student.get('branch', 'UNKNOWN'),
                        'room_code': position.get('room_code', ''),
                        'room_name': position.get('room_name', ''),
                        'row_num': position.get('row', 0),
                        'col_num': position.get('col', 0),
                        'seat_number': position.get('seat_number', f'Seat-{pos_idx}'),
                        'allocation_method': algorithm_name
                    }
                    
                    allocations.append(allocation)
            
            print(f"✅ {algorithm_name}: {len(allocations)} students allocated")
            return allocations
            
        except Exception as e:
            print(f"Error converting to allocations: {e}")
            return []

    def _convert_desk_pairs_to_allocations(self, pair_indices, students, desks, algorithm_name):
        
        try:
            allocations = []
            
            for pair_idx, (idx1, idx2) in enumerate(pair_indices):
                if pair_idx < len(desks):
                    # Validate indices
                    if idx1 >= len(students) or idx2 >= len(students):
                        continue
                    
                    desk = desks[pair_idx]
                    student1 = students[idx1]
                    student2 = students[idx2]

                    room_id = desk.get('room_id') or desk.get('id')
                    
                    # Allocate first student (left seat)
                    allocation1 = {
                        'usn': student1.get('usn', f'student_{idx1}'),
                        'student_name': student1.get('name', 'Unknown'),
                        'subject_code': student1.get('subject_code', ''),
                        'subject_name': student1.get('subject_name', ''),
                        'branch': student1.get('branch', 'UNKNOWN'),
                        'room_id': room_id,
                        'room_code': desk.get('room_code', ''),
                        'room_name': desk.get('room_name', ''),
                        'row_num': desk.get('row', 0),
                        'col_num': desk.get('col', 0),
                        'seat_number': desk.get('seat1', f"{desk.get('desk_id', '')}-L"),
                        'desk_id': desk.get('desk_id', ''),
                        'desk_position': 'left',
                        'desk_partner_usn': student2.get('usn', f'student_{idx2}'),
                        'allocation_method': algorithm_name
                    }
                    
                    # Allocate second student (right seat)
                    allocation2 = {
                        'usn': student2.get('usn', f'student_{idx2}'),
                        'student_name': student2.get('name', 'Unknown'),
                        'subject_code': student2.get('subject_code', ''),
                        'subject_name': student2.get('subject_name', ''),
                        'branch': student2.get('branch', 'UNKNOWN'),
                        'room_id': room_id,
                        'room_code': desk.get('room_code', ''),
                        'room_name': desk.get('room_name', ''),
                        'row_num': desk.get('row', 0),
                        'col_num': desk.get('col', 0),
                        'seat_number': desk.get('seat2', f"{desk.get('desk_id', '')}-R"),
                        'desk_id': desk.get('desk_id', ''),
                        'desk_position': 'right',
                        'desk_partner_usn': student1.get('usn', f'student_{idx1}'),
                        'allocation_method': algorithm_name
                    }
                    
                    allocations.append(allocation1)
                    allocations.append(allocation2)
            
            print(f"✅ {algorithm_name}: {len(allocations)} students allocated")
            return allocations
            
        except Exception as e:
            print(f"Error converting pairs to allocations: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _fallback_allocation(self, students: list, positions: list) -> list:
        """
        Simple fallback allocation (sequential)
        """
        try:
            allocations = []
            
            for i in range(min(len(students), len(positions))):
                student = students[i]
                position = positions[i]
                
                allocation = {
                    'usn': student.get('usn', f'student_{i}'),
                    'student_name': student.get('name', 'Unknown'),
                    'subject_code': student.get('subject_code', ''),
                    'subject_name': student.get('subject_name', ''),
                    'branch': student.get('branch', 'UNKNOWN'),
                    'room_code': position.get('room_code', ''),
                    'room_name': position.get('room_name', ''),
                    'row_num': position.get('row', 0),
                    'col_num': position.get('col', 0),
                    'seat_number': position.get('seat_number', f'Seat-{i}'),
                    'allocation_method': 'Fallback (Sequential)'
                }
                
                allocations.append(allocation)
            
            print(f"✅ Fallback allocation: {len(allocations)} students allocated")
            return allocations
            
        except Exception as e:
            print(f"Error in fallback allocation: {e}")
            return []

    def _fallback_desk_allocation(self, students: list, desks: list) -> list:
        """
        Simple fallback desk allocation (sequential pairing)
        """
        try:
            allocations = []
            
            for desk_idx in range(min(len(desks), len(students) // 2)):
                idx1 = desk_idx * 2
                idx2 = desk_idx * 2 + 1
                
                if idx1 < len(students) and idx2 < len(students):
                    desk = desks[desk_idx]
                    student1 = students[idx1]
                    student2 = students[idx2]
                    room_id = desk.get('room_id') or desk.get('id')
                    
                    allocation1 = {
                        'usn': student1.get('usn', f'student_{idx1}'),
                        'student_name': student1.get('name', 'Unknown'),
                        'subject_code': student1.get('subject_code', ''),
                        'subject_name': student1.get('subject_name', ''),
                        'branch': student1.get('branch', 'UNKNOWN'),
                        'room_id': room_id,
                        'room_code': desk.get('room_code', ''),
                        'room_name': desk.get('room_name', ''),
                        'row_num': desk.get('row', 0),
                        'col_num': desk.get('col', 0),
                        'seat_number': desk.get('seat1', f"{desk.get('desk_id', '')}-L"),
                        'desk_id': desk.get('desk_id', ''),
                        'desk_position': 'left',
                        'desk_partner_usn': student2.get('usn', f'student_{idx2}'),
                        'allocation_method': 'Fallback (Sequential)'
                    }
                    
                    allocation2 = {
                        'usn': student2.get('usn', f'student_{idx2}'),
                        'student_name': student2.get('name', 'Unknown'),
                        'subject_code': student2.get('subject_code', ''),
                        'subject_name': student2.get('subject_name', ''),
                        'branch': student2.get('branch', 'UNKNOWN'),
                        'room_id': room_id,
                        'room_code': desk.get('room_code', ''),
                        'room_name': desk.get('room_name', ''),
                        'row_num': desk.get('row', 0),
                        'col_num': desk.get('col', 0),
                        'seat_number': desk.get('seat2', f"{desk.get('desk_id', '')}-R"),
                        'desk_id': desk.get('desk_id', ''),
                        'desk_position': 'right',
                        'desk_partner_usn': student1.get('usn', f'student_{idx1}'),
                        'allocation_method': 'Fallback (Sequential)'
                    }
                    
                    allocations.append(allocation1)
                    allocations.append(allocation2)
            
            print(f"✅ Fallback desk allocation: {len(allocations)} students allocated")
            return allocations
            
        except Exception as e:
            print(f"Error in fallback desk allocation: {e}")
            return []
    
    
    
    def _create_positions(self, rooms: list) -> list:
        """Create list of all available seat positions"""
        positions = []
        for room in rooms:
            for row in range(1, room.rows + 1):
                for col in range(1, room.cols + 1):
                    positions.append({
                        'room_id': room.id,
                        'room_code': room.room_code,
                        'room_name': room.room_name,
                        'row': row,
                        'col': col
                    })
        return positions
    
    def _calculate_position_score(self, student: dict, position: dict, current_allocations: list, all_positions: list) -> float:
        """Calculate how good a position is for a student given current allocations"""
        score = 10.0  # Base score
        
        # Check adjacent positions for conflicts
        adjacent_positions = self._get_adjacent_positions(position, all_positions)
        
        for allocation in current_allocations:
            alloc_pos = {
                'room_id': allocation['room_id'],
                'row': allocation['row_num'],
                'col': allocation['col_num']
            }
            
            # If this allocation is adjacent to our position
            if alloc_pos in adjacent_positions:
                # Same branch penalty
                if allocation['branch'] == student['branch']:
                    score -= 5
                
                # Same subject penalty
                if allocation['subject_code'] == student['subject_code']:
                    score -= 10
                
                # Different branch bonus
                if allocation['branch'] != student['branch']:
                    score += 2
        
        return score
    
    def _get_adjacent_positions(self, position: dict, all_positions: list) -> list:
        """Get positions adjacent to given position"""
        adjacent = []
        room_id = position['room_id']
        row, col = position['row'], position['col']
        
        # Check 8 adjacent positions
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                
                adj_pos = {
                    'room_id': room_id,
                    'row': row + dr,
                    'col': col + dc
                }
                
                # Check if this position exists
                for pos in all_positions:
                    if (pos['room_id'] == adj_pos['room_id'] and 
                        pos['row'] == adj_pos['row'] and 
                        pos['col'] == adj_pos['col']):
                        adjacent.append(adj_pos)
                        break
        
        return adjacent
    
    def _create_allocation_record(self, student: dict, position: dict, method: str) -> dict:
        """Create allocation record in standard format"""
        seat_number = f"R{position['row']:02d}C{position['col']:02d}"
        
        return {
            'usn': student['usn'],
            'student_name': student['name'],
            'subject_code': student['subject_code'],
            'subject_name': student['subject_name'],
            'branch': student['branch'],
            'semester': student['semester'],
            'room_id': position['room_id'],
            'room_code': position['room_code'],
            'room_name': position['room_name'],
            'seat_number': seat_number,
            'row_num': position['row'],
            'col_num': position['col'],
            'allocation_method': method
        }
    
    def _convert_to_allocations(self, individual: list, students: list, positions: list, method: str) -> list:
        """Convert genetic algorithm solution to allocation records"""
        allocations = []
        
        for i, student_idx in enumerate(individual):
            if i < len(positions) and student_idx < len(students):
                student = students[student_idx]
                position = positions[i]
                allocation = self._create_allocation_record(student, position, method)
                allocations.append(allocation)
        
        return allocations

    def _convert_desk_pairs_to_allocations(self, pair_indices, students, desks, algorithm_name):
        try:    
        
            allocations = []
            
            for pair_idx, (idx1, idx2) in enumerate(pair_indices):
                if pair_idx < len(desks):
                    # Validate indices
                    if idx1 >= len(students) or idx2 >= len(students):
                        continue
                    
                    desk = desks[pair_idx]
                    student1 = students[idx1]
                    student2 = students[idx2]

                    room_id = desk.get('room_id') or desk.get('id')
                    
                    # Allocate first student (left seat)
                    allocation1 = {
                        'usn': student1.get('usn', f'student_{idx1}'),
                        'student_name': student1.get('name', 'Unknown'),
                        'subject_code': student1.get('subject_code', ''),
                        'subject_name': student1.get('subject_name', ''),
                        'branch': student1.get('branch', 'UNKNOWN'),
                        'room_id': room_id,
                        'room_code': desk.get('room_code', ''),
                        'room_name': desk.get('room_name', ''),
                        'row_num': desk.get('row', 0),
                        'col_num': desk.get('col', 0),
                        'seat_number': desk.get('seat1', f"{desk.get('desk_id', '')}-L"),
                        'desk_id': desk.get('desk_id', ''),
                        'desk_position': 'left',
                        'desk_partner_usn': student2.get('usn', f'student_{idx2}'),
                        'allocation_method': algorithm_name
                    }
                    
                    # Allocate second student (right seat)
                    allocation2 = {
                        'usn': student2.get('usn', f'student_{idx2}'),
                        'student_name': student2.get('name', 'Unknown'),
                        'subject_code': student2.get('subject_code', ''),
                        'subject_name': student2.get('subject_name', ''),
                        'branch': student2.get('branch', 'UNKNOWN'),
                        'room_id': room_id,
                        'room_code': desk.get('room_code', ''),
                        'room_name': desk.get('room_name', ''),
                        'row_num': desk.get('row', 0),
                        'col_num': desk.get('col', 0),
                        'seat_number': desk.get('seat2', f"{desk.get('desk_id', '')}-R"),
                        'desk_id': desk.get('desk_id', ''),
                        'desk_position': 'right',
                        'desk_partner_usn': student1.get('usn', f'student_{idx1}'),
                        'allocation_method': algorithm_name
                    }
                    
                    allocations.append(allocation1)
                    allocations.append(allocation2)
            
            print(f"✅ {algorithm_name}: {len(allocations)} students allocated")
            return allocations
            
        except Exception as e:
            print(f"Error converting pairs to allocations: {e}")
            import traceback
            traceback.print_exc()
            return []    
    
    def _fallback_allocation(self, students: list, positions: list) -> list:
        """Simple fallback allocation when AI algorithms fail"""
        print("⚠️ Using fallback allocation method")
        
        allocations = []
        
        # Simple round-robin by branch
        branch_groups = defaultdict(list)
        for student in students:
            branch_groups[student['branch']].append(student)
        
        # Interleave students from different branches
        branch_iterators = {branch: iter(students_list) for branch, students_list in branch_groups.items()}
        position_idx = 0
        
        while branch_iterators and position_idx < len(positions):
            for branch in list(branch_iterators.keys()):
                try:
                    student = next(branch_iterators[branch])
                    if position_idx < len(positions):
                        position = positions[position_idx]
                        allocation = self._create_allocation_record(student, position, 'Fallback')
                        allocations.append(allocation)
                        position_idx += 1
                except StopIteration:
                    del branch_iterators[branch]
        
        return allocations
    
    def _calculate_allocation_quality(self, allocations: list) -> float:
        """Calculate quality score of allocation"""
        if not allocations:
            return 0.0
        
        quality = 0.0
        total_comparisons = 0
        
        # Check adjacent seat conflicts
        for i, alloc1 in enumerate(allocations):
            for j, alloc2 in enumerate(allocations):
                if i >= j or alloc1['room_id'] != alloc2['room_id']:
                    continue
                
                # Calculate distance
                distance = math.sqrt(
                    (alloc1['row_num'] - alloc2['row_num']) ** 2 +
                    (alloc1['col_num'] - alloc2['col_num']) ** 2
                )
                
                if distance <= 1.5:  # Adjacent seats
                    total_comparisons += 1
                    
                    # Same branch penalty
                    if alloc1['branch'] == alloc2['branch']:
                        quality -= 1
                    else:
                        quality += 1
                    
                    # Same subject penalty
                    if alloc1['subject_code'] == alloc2['subject_code']:
                        quality -= 2
        
        return quality / max(total_comparisons, 1) if total_comparisons > 0 else 0.5
    
    def _save_allocations_to_database(self, allocations: list, subject_codes: list, algorithm: str, exam_date: str = None, exam_time: str = None) -> str:
        """Save allocations to database and return session ID"""
        try:
            from datetime import datetime, date, time
            session_id = str(uuid.uuid4())[:8]

            exam_date_obj = None
            exam_time_obj = None

            if exam_date:
                try:
                # Handle different date formats
                    if 'T' in exam_date:  # ISO format: "2025-11-25T00:00:00"
                        exam_date_obj = datetime.fromisoformat(exam_date).date()
                    else:  # Simple format: "2025-11-25"
                        exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d').date()
                        print(f"✅ Parsed exam date: {exam_date_obj}")
                except Exception as e:
                    print(f"⚠️ Error parsing exam date '{exam_date}': {e}")

            if exam_time:
                try:
                # Remove AM/PM if present and convert to 24-hour format
                    time_str = exam_time.strip()
                    if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                    # Handle "10:00 AM" format
                       exam_time_obj = datetime.strptime(time_str, '%I:%M %p').time()
                    elif len(time_str.split(':')) == 2:
                    # Handle "10:00" format
                        exam_time_obj = datetime.strptime(time_str, '%H:%M').time()
                    else:
                    # Handle "10:00:00" format
                        exam_time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
                        print(f"✅ Parsed exam time: {exam_time_obj}")
                except Exception as e:
                     print(f"⚠️ Error parsing exam time '{exam_time}': {e}") 
            unique_rooms = len(set(alloc.get('roomid') or alloc.get('room_id') for alloc in allocations))             
            
            # Create allocation session record
            allocation_session = AllocationSession(
                session_id=session_id,
                subject_codes=json.dumps(subject_codes),
                algorithm_used=algorithm,
                total_students=len(allocations),
                total_rooms=len(set(alloc['room_id'] for alloc in allocations)),
                fitness_score=self._calculate_allocation_quality(allocations),
                exam_date=exam_date_obj,  # ✅ SAVE EXAM DATE
                exam_time=exam_time_obj,  # ✅ SAVE EXAM TIME
             exam_duration=180
            )
            db.session.add(allocation_session)
            
            # Save detailed allocations
            for allocation in allocations:
                detailed_allocation = DetailedAllocation(
                    session_id=session_id,
                    student_usn=allocation['usn'],
                    student_name=allocation['student_name'],
                    subject_code=allocation['subject_code'],
                    subject_name=allocation['subject_name'],
                    branch=allocation['branch'],
                    room_code=allocation['room_code'],
                    room_name=allocation['room_name'],
                    seat_number=allocation['seat_number'],
                    row_num=allocation['row_num'],
                    col_num=allocation['col_num'],
                    allocation_method=allocation['allocation_method']
                )
                db.session.add(detailed_allocation)
                
                # Update student_subjects table with allocation info
                StudentSubject.query.filter_by(
                    usn=allocation['usn'],
                    subject_code=allocation['subject_code']
                ).update({
                    'seat_allocated': True,
                    'allocated_room': allocation['room_code'],
                    'allocated_seat': allocation['seat_number']
                })
            
            db.session.commit()
            print(f"💾 Saved {len(allocations)} allocations to database with session ID: {session_id}")
            
            return session_id
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving allocations: {e}")
            return "error"

    def save_allocations_safely(self, allocations: list, subject_codes: list, algorithm: str, exam_date: str = None, exam_time: str = None) -> str:
        try:
            from datetime import datetime
            import json
        
            session_id = str(uuid.uuid4())[:8]
        
        # ✅ PARSE DATE AND TIME
            exam_date_obj = None
            exam_time_obj = None
        
            if exam_date:
                try:
                    if 'T' in exam_date:
                        exam_date_obj = datetime.fromisoformat(exam_date).date()
                    else:
                        exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d').date()
                        print(f"✅ Parsed exam date: {exam_date_obj}")
                except Exception as e:
                    print(f"⚠️ Error parsing exam date '{exam_date}': {e}")
        
            if exam_time:
                try:
                    time_str = exam_time.strip()
                    if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                        exam_time_obj = datetime.strptime(time_str, '%I:%M %p').time()
                    elif len(time_str.split(':')) == 2:
                        exam_time_obj = datetime.strptime(time_str, '%H:%M').time()
                    else:
                        exam_time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
                        print(f"✅ Parsed exam time: {exam_time_obj}")
                except Exception as e:
                    print(f"⚠️ Error parsing exam time '{exam_time}': {e}")
        
            unique_rooms = len(set(alloc.get('room_code') for alloc in allocations))
            fitness_score = self._calculate_allocation_quality(allocations)
        
        # ✅ CREATE SESSION WITH DATE/TIME
            allocation_session = AllocationSession(
            session_id=session_id,
            subject_codes=json.dumps(subject_codes),
            algorithm_used=algorithm,
            total_students=len(allocations),
            total_rooms=unique_rooms,
            total_desks=len(allocations) // 2,
            fitness_score=fitness_score,
            exam_date=exam_date_obj,      # ✅ WITH UNDERSCORE
            exam_time=exam_time_obj,      # ✅ WITH UNDERSCORE
            exam_duration=180             # ✅ WITH UNDERSCORE
            )
        
            db.session.add(allocation_session)
        
        # Save detailed allocations
            for allocation in allocations:
                detailed_allocation = DetailedAllocation(
                session_id=session_id,
                student_usn=allocation.get('usn') or allocation.get('student_usn'),
                student_name=allocation.get('student_name'),
                subject_code=allocation.get('subject_code'),
                subject_name=allocation.get('subject_name'),
                branch=allocation.get('branch'),
                room_code=allocation.get('room_code'),
                room_name=allocation.get('room_name'),
                seat_number=allocation.get('seat_number'),
                row_num=allocation.get('row_num'),
                col_num=allocation.get('col_num'),
                allocation_method=allocation.get('allocation_method', 'AI')
                )
                db.session.add(detailed_allocation)
        
            db.session.commit()
            print(f"💾 Saved {len(allocations)} allocations with session ID: {session_id}")
        
            return session_id
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving allocations: {str(e)}")
            import traceback
            traceback.print_exc()
            return "error"       

# Initialize the AI allocator
ai_seat_allocator = CompleteAISeatAllocator()
    


class VTUChatbot:
    def __init__(self):
        self.branches = ['CSE', 'ISE', 'ECE', 'MECH', 'CIVIL', 'EEE', 'AIML', 'DS']
        self.semesters = list(range(1, 9))
        
    def validate_usn(self, usn):
        """Validate VTU USN format"""
        pattern = r'^[0-9][A-Z]{2}[0-9]{2}[A-Z]{2,4}[0-9]{3}$'
        return bool(re.match(pattern, usn.upper()))
        
    def validate_email(self, email):
        """Enhanced email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def get_subjects_for_branch_semester(self, branch, semester):
        """Get available subjects for a branch and semester from database"""
        try:
            subjects = Subject.query.filter_by(branch=branch, semester=semester).all()
            return [(sub.id, sub.subject_code, sub.subject_name) for sub in subjects]
        except Exception as e:
            print(f"Error fetching subjects: {e}")
            return []

    def process_message(self, session_id, message, is_voice=False):
        """Enhanced message processing with voice support"""
        try:
            print(f"🎯 Processing {'voice' if is_voice else 'text'} message: '{message}' for session: {session_id}")
            
            # Get or create chat session
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not chat_session:
                chat_session = ChatSession(
                    session_id=session_id,
                    current_step='start',
                    data=json.dumps({})
                )
                db.session.add(chat_session)
                db.session.commit()
            
            current_step = chat_session.current_step
            try:
                data = json.loads(chat_session.data) if chat_session.data else {}
            except:
                data = {}
            
            print(f"📍 Current step: {current_step}")
            
            response = self.handle_step(current_step, message, data, is_voice)
            
            # Save session state
            if response and 'data' in response:
                chat_session.current_step = response['next_step']
                chat_session.data = json.dumps(response['data'])
                chat_session.completed = response.get('completed', False)
                
                if response.get('completed') and 'usn' in response['data']:
                    chat_session.student_usn = response['data']['usn']
                
                db.session.commit()
                print(f"✅ Session updated - Next step: {chat_session.current_step}")
            
            return response
            
        except Exception as e:
            print(f"❌ ERROR in process_message: {str(e)}")
            traceback.print_exc()
            db.session.rollback()
            return {
                'message': f'Sorry, I encountered an error: {str(e)}. Please type "restart" to begin again.',
                'next_step': 'start',
                'data': {},
                'error': True
            }
    
    def handle_step(self, step, message, data, is_voice=False):
        """Complete step handling for VTU registration with field modification"""
        
        # Handle restart
        if message.lower().strip() in ['restart', 'reset', 'start over']:
            return {
                'message': '🔄 **Restarting Registration**\n\n🎓 Welcome to VTU Exam Registration!\n\n**Do you have any backlogs from previous semesters?**\n\nPlease reply with "Yes" or "No"',
                'next_step': 'check_backlogs',
                'data': {}
            }
        
        if step == 'start':
            return {
                'message': '🎓 **Welcome to VTU Exam Registration Chatbot!**\n\nI will help you register for VTU exams and organize you under your selected subjects.\n\n**Do you have any backlogs from previous semesters?**\n\nPlease reply with "Yes" or "No"',
                'next_step': 'check_backlogs',
                'data': data
            }
        
        elif step == 'check_backlogs':
            message_lower = message.lower().strip()
            if message_lower in ['yes', 'y', 'yeah', 'yep', 'true']:
                data['has_backlogs'] = True
                return {
                    'message': '📚 I see you have backlogs. I\'ll help you register for both current semester and backlog subjects.\n\n**Please enter your full name:**',
                    'next_step': 'get_name',
                    'data': data
                }
            elif message_lower in ['no', 'n', 'nope', 'false']:
                data['has_backlogs'] = False
                return {
                    'message': '✅ Great! You have no backlogs. I\'ll help you register for your current semester subjects.\n\n**Please enter your full name:**',
                    'next_step': 'get_name',
                    'data': data
                }
            else:
                return {
                    'message': '❓ Please answer with "Yes" or "No" only.\n\n**Do you have any backlogs from previous semesters?**',
                    'next_step': 'check_backlogs',
                    'data': data
                }
        
        elif step == 'get_name':
            if len(message.strip()) < 2:
                return {
                    'message': '❌ Please enter a valid name (at least 2 characters).\n\n**Please enter your full name:**',
                    'next_step': 'get_name',
                    'data': data
                }
            data['name'] = message.strip().title()
            return {
                'message': f'👋 Hello **{data["name"]}**!\n\n**Please enter your USN (University Seat Number):**\n\nExample: 1RV21CS001',
                'next_step': 'get_usn',
                'data': data
            }
            
        elif step == 'get_usn':
            usn = message.strip().upper().replace(' ', '')
            if not self.validate_usn(usn):
                return {
                    'message': '❌ Invalid USN format. Please enter a valid VTU USN.\n\nExample: 1RV21CS001\n\n**Please enter your USN:**',
                    'next_step': 'get_usn',
                    'data': data
                }
            
            # Check if USN already exists
            try:
                existing_student = Student.query.filter_by(usn=usn).first()
                if existing_student:
                    return {
                        'message': f'⚠️ A student with USN **{usn}** is already registered.\n\nIf this is you, please contact the exam office.\n\n**Please enter a different USN or type "restart":**',
                        'next_step': 'get_usn',
                        'data': data
                    }
            except Exception as e:
                print(f"Database check error: {e}")
            
            data['usn'] = usn
            return {
                'message': f'📝 USN: **{usn}** recorded.\n\n**Please select your branch:**\n\n' + 
                          '\n'.join([f'• **{branch}**' for branch in self.branches]) +
                          '\n\nType your branch code (CSE, ISE, ECE, etc.):',
                'next_step': 'get_branch',
                'data': data
            }
            
        elif step == 'get_branch':
            branch = message.strip().upper()
            
            # Branch validation with mapping
            branch_mapping = {
                'CS': 'CSE', 'CSE': 'CSE', 'COMPUTER': 'CSE',
                'IS': 'ISE', 'ISE': 'ISE', 'INFORMATION': 'ISE',
                'EC': 'ECE', 'ECE': 'ECE', 'ELECTRONICS': 'ECE',
                'MECH': 'MECH', 'MECHANICAL': 'MECH',
                'CIVIL': 'CIVIL', 'CV': 'CIVIL',
                'EEE': 'EEE', 'ELECTRICAL': 'EEE',
                'AIML': 'AIML', 'AI': 'AIML',
                'DS': 'DS', 'DATA': 'DS'
            }
            
            branch = branch_mapping.get(branch, branch)
            
            if branch not in self.branches:
                return {
                    'message': f'❌ Unknown branch: "{message}". Please choose from:\n\n' + 
                              '\n'.join([f'• **{branch}**' for branch in self.branches]) +
                              '\n\n**Please enter your branch code:**',
                    'next_step': 'get_branch',
                    'data': data
                }
            
            data['branch'] = branch
            
            if data.get('has_backlogs', False):
                return {
                    'message': f'🎯 Branch: **{branch}**\n\n**What is your current semester? (1-8)**',
                    'next_step': 'get_current_semester',
                    'data': data
                }
            else:
                return {
                    'message': f'🎯 Branch: **{branch}**\n\n**What semester are you in? (1-8)**',
                    'next_step': 'get_semester',
                    'data': data
                }
        
        elif step == 'get_current_semester':
            try:
                semester = int(message.strip())
                if semester not in self.semesters:
                    raise ValueError
                data['current_semester'] = semester
                data['semester'] = semester
                return {
                    'message': f'📅 Current Semester: **{semester}**\n\n**Which semesters do you have backlog subjects from?**\n\nEnter semester numbers separated by commas (e.g., 3,4,5):',
                    'next_step': 'get_backlog_semesters',
                    'data': data
                }
            except ValueError:
                return {
                    'message': '❌ Please enter a valid semester number (1-8).\n\n**What is your current semester?**',
                    'next_step': 'get_current_semester',
                    'data': data
                }
                
        elif step == 'get_backlog_semesters':
            try:
                semester_str = message.replace(',', ' ').replace('and', ' ')
                backlog_semesters = [int(s.strip()) for s in semester_str.split() if s.strip().isdigit()]
                backlog_semesters = [s for s in backlog_semesters if s in self.semesters]
                if not backlog_semesters:
                    raise ValueError
                data['backlog_semesters'] = backlog_semesters
                return {
                    'message': f'📚 Backlog Semesters: **{", ".join(map(str, backlog_semesters))}**\n\n**Please enter your email address:**',
                    'next_step': 'get_email',
                    'data': data
                }
            except ValueError:
                return {
                    'message': '❌ Please enter valid semester numbers separated by commas.\n\nExample: 3,4,5\n\n**Which semesters do you have backlog subjects from?**',
                    'next_step': 'get_backlog_semesters',
                    'data': data
                }
        
        elif step == 'get_semester':
            try:
                semester = int(message.strip())
                if semester not in self.semesters:
                    raise ValueError
                data['semester'] = semester
                return {
                    'message': f'📅 Semester: **{semester}**\n\n**Please enter your email address:**',
                    'next_step': 'get_email',
                    'data': data
                }
            except ValueError:
                return {
                    'message': '❌ Please enter a valid semester number (1-8).\n\n**What semester are you in?**',
                    'next_step': 'get_semester',
                    'data': data
                }
                
        elif step == 'get_email':
            email = message.strip().lower()
            
            if not self.validate_email(email):
                return {
                    'message': '❌ Please enter a valid email address.\n\nExample: student@gmail.com\n\n**Please enter your email:**',
                    'next_step': 'get_email',
                    'data': data
                }
            
            data['email'] = email
            
            try:
                has_backlogs = data.get('has_backlogs', False)
                
                if has_backlogs:
                    response = self.show_backlog_subjects(data)
                else:
                    response = self.show_regular_subjects(data)
                
                return response
                
            except Exception as e:
                print(f"ERROR in email->subjects transition: {str(e)}")
                return {
                    'message': f'❌ Error proceeding to subject selection: {str(e)}\n\nPlease type "restart" to try again.',
                    'next_step': 'start',
                    'data': {},
                    'error': True
                }
        
        elif step == 'select_subjects':
            try:
                # Parse subject numbers
                subject_numbers = []
                
                if ',' in message:
                    parts = message.split(',')
                    for part in parts:
                        num_str = part.strip()
                        if num_str.isdigit():
                            subject_numbers.append(int(num_str))
                else:
                    parts = message.replace(',', ' ').split()
                    for part in parts:
                        if part.strip().isdigit():
                            subject_numbers.append(int(part.strip()))
                
                available_subjects = data.get('available_subjects', [])
                
                if not subject_numbers:
                    raise ValueError("No valid numbers found")
                    
                if not available_subjects:
                    raise ValueError("No subjects available")
                    
                if max(subject_numbers) > len(available_subjects):
                    raise ValueError("Number too high")
                
                selected_subjects = [available_subjects[i-1] for i in subject_numbers]
                data['selected_subjects'] = selected_subjects
                
                print(f"🎯 Selected subjects: {selected_subjects}")
                
                return self.show_data_confirmation(data)
                
            except (ValueError, IndexError) as e:
                available_subjects = data.get('available_subjects', [])
                subject_count = len(available_subjects) if available_subjects else 0
                return {
                    'message': f'❌ Please enter valid subject numbers (1-{subject_count}) separated by commas.\n\nExample: 1,2,3\n\n**Select subjects by entering their numbers:**',
                    'next_step': 'select_subjects',
                    'data': data
                }
        
        elif step == 'confirm_data':
            message_lower = message.lower().strip()
            if message_lower in ['yes', 'y', 'confirm', 'ok', 'correct']:
                return self.complete_registration(data)
            elif message_lower in ['no', 'n', 'change', 'modify', 'edit']:
                return {
                    'message': '🔄 **What would you like to change?**\n\nYou can type:\n\n• **"name"** - to change your name\n• **"usn"** - to change your USN\n• **"branch"** - to change your branch\n• **"semester"** - to change your semester\n• **"email"** - to change your email\n• **"subjects"** - to change subject selection\n• **"restart"** - to start over completely',
                    'next_step': 'modify_data',
                    'data': data
                }

        # Handle field modifications (same as before)
        elif step == 'modify_data':
            field_to_modify = message.lower().strip()
            
            if field_to_modify == 'name':
                return {
                    'message': f'📝 **Change Name**\n\nCurrent name: **{data.get("name", "Not set")}**\n\n**Please enter your new name:**',
                    'next_step': 'modify_name',
                    'data': data
                }
            elif field_to_modify == 'usn':
                return {
                    'message': f'📝 **Change USN**\n\nCurrent USN: **{data.get("usn", "Not set")}**\n\n**Please enter your new USN:**\n\nExample: 1RV21CS001',
                    'next_step': 'modify_usn',
                    'data': data
                }
            elif field_to_modify == 'branch':
                return {
                    'message': f'📝 **Change Branch**\n\nCurrent branch: **{data.get("branch", "Not set")}**\n\n**Please select your new branch:**\n\n' + 
                              '\n'.join([f'• **{branch}**' for branch in self.branches]) +
                              '\n\nType your branch code:',
                    'next_step': 'modify_branch',
                    'data': data
                }
            elif field_to_modify == 'semester':
                if data.get('has_backlogs', False):
                    return {
                        'message': f'📝 **Change Current Semester**\n\nCurrent semester: **{data.get("current_semester", "Not set")}**\n\n**Please enter your new current semester (1-8):**',
                        'next_step': 'modify_current_semester',
                        'data': data
                    }
                else:
                    return {
                        'message': f'📝 **Change Semester**\n\nCurrent semester: **{data.get("semester", "Not set")}**\n\n**Please enter your new semester (1-8):**',
                        'next_step': 'modify_semester',
                        'data': data
                    }
            elif field_to_modify == 'email':
                return {
                    'message': f'📝 **Change Email**\n\nCurrent email: **{data.get("email", "Not set")}**\n\n**Please enter your new email address:**',
                    'next_step': 'modify_email',
                    'data': data
                }
            elif field_to_modify == 'subjects':
                # Re-show subjects based on current branch/semester
                has_backlogs = data.get('has_backlogs', False)
                if has_backlogs:
                    return self.show_backlog_subjects(data)
                else:
                    return self.show_regular_subjects(data)
            elif field_to_modify == 'restart':
                return {
                    'message': '🔄 **Restarting Registration**\n\n🎓 Welcome to VTU Exam Registration!\n\n**Do you have any backlogs from previous semesters?**\n\nPlease reply with "Yes" or "No"',
                    'next_step': 'check_backlogs',
                    'data': {}
                }
            else:
                return {
                    'message': '❌ **Invalid option.** Please choose what you want to change:\n\n• **"name"** - to change your name\n• **"usn"** - to change your USN\n• **"branch"** - to change your branch\n• **"semester"** - to change your semester\n• **"email"** - to change your email\n• **"subjects"** - to change subject selection\n• **"restart"** - to start over completely',
                    'next_step': 'modify_data',
                    'data': data
                }

        # Individual field modification handlers
        elif step == 'modify_name':
            if len(message.strip()) < 2:
                return {
                    'message': '❌ Please enter a valid name (at least 2 characters).\n\n**Please enter your new name:**',
                    'next_step': 'modify_name',
                    'data': data
                }
            data['name'] = message.strip().title()
            return self.show_data_confirmation(data)

        elif step == 'modify_usn':
            usn = message.strip().upper().replace(' ', '')
            if not self.validate_usn(usn):
                return {
                    'message': '❌ Invalid USN format. Please enter a valid VTU USN.\n\nExample: 1RV21CS001\n\n**Please enter your new USN:**',
                    'next_step': 'modify_usn',
                    'data': data
                }
            
            # Check if USN already exists
            try:
                existing_student = Student.query.filter_by(usn=usn).first()
                if existing_student:
                    return {
                        'message': f'⚠️ A student with USN **{usn}** is already registered.\n\n**Please enter a different USN:**',
                        'next_step': 'modify_usn',
                        'data': data
                    }
            except Exception as e:
                print(f"Database check error: {e}")
            
            data['usn'] = usn
            return self.show_data_confirmation(data)

        elif step == 'modify_branch':
            branch = message.strip().upper()
            
            # Branch validation with mapping
            branch_mapping = {
                'CS': 'CSE', 'CSE': 'CSE', 'COMPUTER': 'CSE',
                'IS': 'ISE', 'ISE': 'ISE', 'INFORMATION': 'ISE',
                'EC': 'ECE', 'ECE': 'ECE', 'ELECTRONICS': 'ECE',
                'MECH': 'MECH', 'MECHANICAL': 'MECH',
                'CIVIL': 'CIVIL', 'CV': 'CIVIL',
                'EEE': 'EEE', 'ELECTRICAL': 'EEE',
                'AIML': 'AIML', 'AI': 'AIML',
                'DS': 'DS', 'DATA': 'DS'
            }
            
            branch = branch_mapping.get(branch, branch)
            
            if branch not in self.branches:
                return {
                    'message': f'❌ Unknown branch: "{message}". Please choose from:\n\n' + 
                              '\n'.join([f'• **{branch}**' for branch in self.branches]) +
                              '\n\n**Please enter your branch code:**',
                    'next_step': 'modify_branch',
                    'data': data
                }
            
            old_branch = data.get('branch')
            data['branch'] = branch
            
            # If branch changed, need to reload subjects
            if old_branch != branch:
                # Clear selected subjects since branch changed
                data.pop('selected_subjects', None)
                data.pop('available_subjects', None)
                
                # Re-show subjects for new branch
                has_backlogs = data.get('has_backlogs', False)
                if has_backlogs:
                    return self.show_backlog_subjects(data)
                else:
                    return self.show_regular_subjects(data)
            else:
                return self.show_data_confirmation(data)

        elif step == 'modify_semester':
            try:
                semester = int(message.strip())
                if semester not in self.semesters:
                    raise ValueError
                
                old_semester = data.get('semester')
                data['semester'] = semester
                
                # If semester changed, need to reload subjects
                if old_semester != semester:
                    data.pop('selected_subjects', None)
                    data.pop('available_subjects', None)
                    return self.show_regular_subjects(data)
                else:
                    return self.show_data_confirmation(data)
                    
            except ValueError:
                return {
                    'message': '❌ Please enter a valid semester number (1-8).\n\n**Please enter your new semester:**',
                    'next_step': 'modify_semester',
                    'data': data
                }

        elif step == 'modify_current_semester':
            try:
                semester = int(message.strip())
                if semester not in self.semesters:
                    raise ValueError
                
                old_semester = data.get('current_semester')
                data['current_semester'] = semester
                data['semester'] = semester
                
                # If current semester changed, need to reload subjects
                if old_semester != semester:
                    data.pop('selected_subjects', None)
                    data.pop('available_subjects', None)
                    return self.show_backlog_subjects(data)
                else:
                    return self.show_data_confirmation(data)
                    
            except ValueError:
                return {
                    'message': '❌ Please enter a valid semester number (1-8).\n\n**Please enter your new current semester:**',
                    'next_step': 'modify_current_semester',
                    'data': data
                }

        elif step == 'modify_email':
            email = message.strip().lower()
            
            if not self.validate_email(email):
                return {
                    'message': '❌ Please enter a valid email address.\n\nExample: student@gmail.com\n\n**Please enter your new email:**',
                    'next_step': 'modify_email',
                    'data': data
                }
            
            data['email'] = email
            return self.show_data_confirmation(data)
        
        # Default fallback
        return {
            'message': 'I didn\'t understand that. Type "restart" to start over.',
            'next_step': 'start',
            'data': {}
        }

    def show_regular_subjects(self, data):
        """Show subjects for regular registration (no backlogs)"""
        branch = data.get('branch')
        semester = data.get('semester')
        
        print(f"📚 Showing regular subjects for {branch} semester {semester}")
        
        if not branch or not semester:
            return {
                'message': '❌ Missing branch or semester information. Type "restart" to start over.',
                'next_step': 'start',
                'data': {}
            }
            
        # Get subjects from database
        subjects = self.get_subjects_for_branch_semester(branch, semester)
        
        print(f"🔍 Found {len(subjects)} subjects in database")
        
        if not subjects:
            # Create fallback subjects if none in database
            subjects = [
                (1000 + semester, f'{branch}0{semester}1', f'{branch} Subject {semester}-1'),
                (1000 + semester + 1, f'{branch}0{semester}2', f'{branch} Subject {semester}-2'),
                (1000 + semester + 2, f'{branch}0{semester}3', f'{branch} Subject {semester}-3'),
                (1000 + semester + 3, f'{branch}0{semester}4', f'{branch} Subject {semester}-4'),
                (1000 + semester + 4, f'{branch}0{semester}5', f'{branch} Subject {semester}-5'),
                (1000 + semester + 5, f'{branch}0{semester}6', f'{branch} Subject {semester}-6'),
                (1000 + semester + 6, f'{branch}0{semester}7', f'{branch} Subject {semester}-7')
            ]
            print(f"⚠️ Using fallback subjects: {len(subjects)} subjects created")
        
        data['available_subjects'] = subjects
        subject_list = '\n'.join([f'**{i+1}.** {code} - {name}' for i, (_, code, name) in enumerate(subjects)])
        
        return {
            'message': f'📚 **Available Subjects for {branch} Semester {semester}:**\n\n{subject_list}\n\n**Select subjects by entering their numbers (separated by commas):**\n\nExample: 1,2,3,5\n\n⚠️ **Note:** You will be registered UNDER each subject you select!',
            'next_step': 'select_subjects',
            'data': data
        }

    def show_backlog_subjects(self, data):
        """Show subjects for backlog registration"""
        branch = data.get('branch')
        current_semester = data.get('current_semester')
        backlog_semesters = data.get('backlog_semesters', [])
        
        print(f"📚 Showing backlog subjects for {branch}, current sem {current_semester}, backlogs {backlog_semesters}")
        
        if not branch or not current_semester:
            return {
                'message': '❌ Missing branch or semester information. Type "restart" to start over.',
                'next_step': 'start',
                'data': {}
            }
            
        all_subjects = []
        
        # Add current semester subjects
        current_subjects = self.get_subjects_for_branch_semester(branch, current_semester)
        if not current_subjects:
            current_subjects = [
                (2000 + current_semester, f'{branch}0{current_semester}1', f'Current {branch} Subject {current_semester}-1'),
                (2000 + current_semester + 1, f'{branch}0{current_semester}2', f'Current {branch} Subject {current_semester}-2')
            ]
        all_subjects.extend([(subject_id, code, name, current_semester, False) for subject_id, code, name in current_subjects])
        
        # Add backlog semester subjects
        for sem in backlog_semesters:
            backlog_subjects = self.get_subjects_for_branch_semester(branch, sem)
            if not backlog_subjects:
                backlog_subjects = [
                    (3000 + sem, f'{branch}0{sem}1', f'Backlog {branch} Subject {sem}-1'),
                    (3000 + sem + 10, f'{branch}0{sem}2', f'Backlog {branch} Subject {sem}-2')
                ]
            all_subjects.extend([(subject_id, code, name, sem, True) for subject_id, code, name in backlog_subjects])
        
        print(f"🔍 Generated {len(all_subjects)} total subjects")
        
        data['available_subjects'] = all_subjects
        
        # Format subject list
        subject_list = []
        current_subjects_list = [s for s in all_subjects if not s[4]]
        backlog_subjects_list = [s for s in all_subjects if s[4]]
        
        if current_subjects_list:
            subject_list.append(f"**📖 Current Semester {current_semester} Subjects:**")
            for i, (subject_id, code, name, sem, is_backlog) in enumerate(current_subjects_list, 1):
                subject_list.append(f"**{i}.** {code} - {name}")
        
        if backlog_subjects_list:
            subject_list.append(f"\n**📚 Backlog Subjects:**")
            start_idx = len(current_subjects_list) + 1
            for i, (subject_id, code, name, sem, is_backlog) in enumerate(backlog_subjects_list, start_idx):
                subject_list.append(f"**{i}.** {code} - {name} *(Sem {sem})*")
        
        return {
            'message': f'📚 **Available Subjects for Registration:**\n\n' + '\n'.join(subject_list) + 
                      f'\n\n**Select subjects by entering their numbers (separated by commas):**\n\nExample: 1,2,3,5\n\n⚠️ **Note:** You will be registered UNDER each subject you select!',
            'next_step': 'select_subjects',
            'data': data
        }

    def show_data_confirmation(self, data):
        """Show all collected data for user confirmation with modification options"""
        selected_subjects = data.get('selected_subjects', [])
        subject_names = []
        
        for subject_info in selected_subjects:
            if len(subject_info) == 5:  # Backlog format: (subject_id, code, name, semester, is_backlog)
                subject_id, code, name, semester, is_backlog = subject_info
                subject_names.append(f"• **{code}** - {name}" + (f" *(Backlog Sem {semester})*" if is_backlog else ""))
            else:  # Regular format: (subject_id, code, name)
                subject_id, code, name = subject_info
                subject_names.append(f"• **{code}** - {name}")
        
        backlog_info = ""
        if data.get('backlog_semesters'):
            backlog_info = f"\n• **Backlog Semesters:** {', '.join(map(str, data['backlog_semesters']))}"

        confirmation_msg = f"""📋 **Please Review Your Information:**

**👤 Personal Details:**
• **Name:** {data.get('name', 'Not provided')}
• **USN:** {data.get('usn', 'Not provided')}
• **Branch:** {data.get('branch', 'Not provided')}
• **Semester:** {data.get('current_semester', data.get('semester', 'Not provided'))}
• **Email:** {data.get('email', 'Not provided')}
• **Has Backlogs:** {"Yes" if data.get('has_backlogs', False) else "No"}{backlog_info}

**📚 Selected Subjects ({len(subject_names)}):**
{chr(10).join(subject_names)}

🎯 **IMPORTANT:** Your details will be stored UNDER each of the {len(subject_names)} subjects above for proper subject-wise organization!

**✅ Is all the information correct?**

Reply with:
• **"Yes"** - to confirm and complete registration
• **"No"** - to make changes to any field"""

        return {
            'message': confirmation_msg,
            'next_step': 'confirm_data',
            'data': data
        }

    def complete_registration(self, data):
        """CRITICAL: Complete registration with SUBJECT-WISE student storage - FIXED VERSION"""
        try:
            print("🚀 STARTING SUBJECT-WISE REGISTRATION...")
            
            # Validate required fields
            required_fields = ['name', 'usn', 'branch', 'email', 'selected_subjects']
            for field in required_fields:
                if not data.get(field):
                    print(f"❌ Missing field: {field}")
                    return {
                        'message': f'❌ **Registration Failed!**\n\nMissing {field}. Type "restart" to start over.',
                        'next_step': 'start',
                        'data': {},
                        'error': True
                    }
            
            # Create student record
            student = Student(
                name=data.get('name'),
                usn=data.get('usn'),
                branch=data.get('branch'),
                semester=data.get('current_semester', data.get('semester')),
                email=data.get('email'),
                has_backlogs=data.get('has_backlogs', False),
                current_semester=data.get('current_semester')
            )
            
            print(f"🎓 Creating student: {student.name}, USN: {student.usn}")
            
            db.session.add(student)
            db.session.flush()  # Get student ID immediately
            
            print(f"✅ Created student with ID: {student.id}")
            
            # CRITICAL: Store student UNDER each selected subject
            selected_subjects = data.get('selected_subjects', [])
            print(f"📚 Processing {len(selected_subjects)} selected subjects...")
            
            subject_registration_count = 0
            
            for subject_info in selected_subjects:
                try:
                    if len(subject_info) == 5:  # Backlog format
                        subject_id, code, name, semester, is_backlog = subject_info
                    elif len(subject_info) == 3:  # Regular format  
                        subject_id, code, name = subject_info
                        semester = data.get('semester', data.get('current_semester'))
                        is_backlog = False
                    else:
                        print(f"⚠️ Unexpected subject format: {subject_info}")
                        continue
                    
                    print(f"🎯 Processing subject: {code} (ID: {subject_id})")
                    
                    # Find or create subject in database
                    db_subject = None
                    
                    # First try to find existing subject by code
                    if isinstance(subject_id, int) and subject_id < 1000:
                        # Real subject from database
                        db_subject = Subject.query.get(subject_id)
                    
                    if not db_subject:
                        # Try to find by code
                        db_subject = Subject.query.filter_by(subject_code=code).first()
                    
                    # If still not found, create new subject
                    if not db_subject:
                        print(f"📝 Creating new subject: {code}")
                        db_subject = Subject(
                            subject_code=code,
                            subject_name=name,
                            semester=semester,
                            branch=data.get('branch'),
                            credits=4
                        )
                        db.session.add(db_subject)
                        db.session.flush()  # Get the new subject ID
                        print(f"✅ Created subject {code} with ID: {db_subject.id}")
                    
                    # Check if student-subject relationship already exists
                    existing_relation = StudentSubject.query.filter_by(
                         usn=student.usn,  # FIXED: Use USN instead of student_id
                           subject_code=code
                           ).first()

                    if not existing_relation:
                        student_subject = StudentSubject(
        usn=student.usn,  # FIXED: Use USN instead of student_id
        student_name=student.name,  # FIXED: Add student_name
        subject_id=db_subject.id,
        subject_code=code,
        subject_name=name,
        semester=semester,
        is_backlog=is_backlog,
        registration_type='backlog' if is_backlog else 'regular'
    )
                        db.session.add(student_subject)
                        subject_registration_count += 1
                        print(f"✅ Stored student UNDER subject {code} - Count: {subject_registration_count}")
                    else:
                        print(f"ℹ️ Student already registered for subject {code}")
                    
                except Exception as subject_error:
                    print(f"❌ Error processing subject {subject_info}: {subject_error}")
                    traceback.print_exc()
                    continue
            
            # CRITICAL: Commit all changes
            try:
                db.session.commit()
                print(f"🎉 REGISTRATION COMPLETED! Student stored under {subject_registration_count} subjects")
            except Exception as commit_error:
                db.session.rollback()
                print(f"❌ Commit error: {commit_error}")
                traceback.print_exc()
                return {
                    'message': f'❌ **Registration Failed!**\n\nDatabase error: {str(commit_error)}\n\nType "restart" to try again.',
                    'next_step': 'start',
                    'data': {},
                    'error': True
                }
            
            # Format confirmation message
            subject_names = []
            for subject_info in selected_subjects:
                if len(subject_info) == 5:
                    subject_id, code, name, semester, is_backlog = subject_info
                    subject_names.append(f"• **{code}** - {name}" + (f" *(Backlog Sem {semester})*" if is_backlog else ""))
                else:
                    subject_id, code, name = subject_info
                    subject_names.append(f"• **{code}** - {name}")
            
            confirmation = f"""🎉 **REGISTRATION SUCCESSFUL!**

**👤 Student Details:**
• **Name:** {data.get('name')}
• **USN:** {data.get('usn')}
• **Branch:** {data.get('branch')}
• **Current Semester:** {data.get('current_semester', data.get('semester'))}
• **Email:** {data.get('email')}
• **Has Backlogs:** {"Yes" if data.get('has_backlogs', False) else "No"}

**📚 Registered Under {len(subject_names)} Subjects:**
{chr(10).join(subject_names)}

🎯 **SUBJECT-WISE ORGANIZATION COMPLETE!**
✅ Your details are now stored UNDER each of the {len(subject_names)} subjects above
✅ Subject-wise student lists will show you under each subject
✅ Perfect organization for VTU exam management
✅ Ready for AI-powered seat allocation

**📋 Next Steps:**
1. ✅ Registration complete - stored under {len(subject_names)} subjects
2. 📧 Check your email for confirmation
3. 💳 Pay exam fees before the deadline  
4. 🎫 Download hall ticket 1 week before exams
5. 📊 View your registration in Dashboard → Subjects
6. 🤖 Admin can now allocate seats using AI algorithms

**🎓 Thank you for using VTU Exam Registration System!**

Type "restart" to register another student."""

            return {
                'message': confirmation,
                'next_step': 'complete',
                'data': {},
                'completed': True
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Registration error: {str(e)}")
            traceback.print_exc()
            return {
                'message': f'❌ **Registration Failed!**\n\nUnexpected error: {str(e)}\n\nType "restart" to try again.',
                'next_step': 'start',
                'data': {},
                'error': True
            }

    
    def process_exams(self, subjects, algorithm, start_date, end_date, session_config):
        """Main processing function"""
        try:
            if algorithm in ['genetic', 'genetic_algorithm', 'hybrid_ai']:
                # Use genetic algorithm
                result = self.genetic_allocator.allocate_seats_genetic(subjects)
                
                if result['success']:
                    # Add scheduling information
                    result.update({
                        'schedule': self._create_basic_schedule(subjects, start_date, end_date),
                        'efficiency': 95,  # Genetic algorithm efficiency
                        'algorithm_used': 'Genetic Algorithm'
                    })
                
                return result
            else:
                # Use other algorithms (implement as needed)
                return self._other_algorithms(subjects, algorithm, start_date, end_date)
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Processing failed: {str(e)}'
            }
    
    def _create_basic_schedule(self, subjects, start_date, end_date):
        """Create basic schedule for genetic algorithm results"""
        from datetime import datetime, timedelta
        
        schedule = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        
        for i, subject_code in enumerate(subjects):
            exam_date = start + timedelta(days=i)
            
            # Skip weekends
            while exam_date.weekday() >= 5:
                exam_date += timedelta(days=1)
            
            # Get subject info
            subject = Subject.query.filter_by(subject_code=subject_code).first()
            student_count = StudentSubject.query.filter_by(subject_code=subject_code).count()
            
            schedule.append({
                'subject_code': subject_code,
                'subject_name': subject.subject_name if subject else 'Unknown',
                'exam_date': exam_date.strftime('%Y-%m-%d'),
                'exam_time': '10:00 AM',
                'student_count': student_count,
                'rooms': ['Multiple Rooms']  # Genetic algorithm handles room allocation
            })
        
        return schedule
    
    def _other_algorithms(self, subjects, algorithm, start_date, end_date):
        """Handle other algorithms"""
        return {
            'success': False,
            'message': f'Algorithm {algorithm} not yet implemented. Use genetic algorithm.'
        }

# Initialize services
chatbot = VTUChatbot()
"""
COMPLETE PYTHON BACKEND CODE FOR EMAIL AND SEATING PLAN SYSTEM
Add this to your Flask application (app.py)
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

# ===============================================================================
# STEP 3: EMAIL CONFIGURATION (Already provided earlier)
# ===============================================================================

EMAIL_CONFIG = {
    'MAIL_SERVER': 'smtp.gmail.com',
    'MAIL_PORT': 587,
    'MAIL_USE_TLS': True,
    'MAIL_USERNAME': 'sanjanabs315@gmail.com',  # CHANGE THIS
    'MAIL_PASSWORD': 'mnuw iodr hyzw mhxa',     # CHANGE THIS
    'MAIL_DEFAULT_SENDER': 'VTU Exam Cell <sanjanabs315@gmail.com>'
}

# ===============================================================================
# STEP 4: INITIALIZE SCHEDULER
# ===============================================================================

scheduler = BackgroundScheduler()
scheduler.start()

# ===============================================================================
# STEP 5: ENHANCED EMAIL SERVICE WITH SCHEDULING
# ===============================================================================
import os
class EmailService:
    """Enhanced email service with scheduling support"""
    
    def __init__(self, app):
        self.app = app
        self.config = EMAIL_CONFIG
        self.public_url = os.getenv('https://droughtiest-gaspingly-charmain.ngrok-free.app', 'http://127.0.0.1:5000')
    
    def send_email(self, to_email, subject, html_body):
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config['MAIL_DEFAULT_SENDER']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.config['MAIL_SERVER'], self.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(self.config['MAIL_USERNAME'], self.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def send_seat_allocation_email(self, student_usn, session_id):
        """Send immediate seat allocation email with app context"""
        with self.app.app_context():
            try:
                # Get allocation details
                allocation = DetailedAllocation.query.filter_by(
                    session_id=session_id,
                    student_usn=student_usn
                ).first()
                
                if not allocation:
                    return False, "Allocation not found"
                
                # Get student from students table
                student = Student.query.filter_by(usn=student_usn).first()
                if not student or not student.email:
                    return False, f"Student email not found for {student_usn}"
                
                # Get session details
                session = AllocationSession.query.filter_by(session_id=session_id).first()
                if not session:
                    return False, "Session not found"
                
                if session.exam_date and session.exam_time:
                    exam_datetime = datetime.combine(
                         session.exam_date, 
                         session.exam_time
                )
                    exam_str = exam_datetime.strftime("%d %B %Y, %I:%M %p")
                    seating_available = (exam_datetime - timedelta(minutes=15)).strftime("%I:%M %p")
                else:
                    exam_str = "To be announced"
                    seating_available = "15 minutes before exam"
                
                # Generate email HTML
                html_body = self._generate_allocation_email(student, allocation, session)
                (
                student, 
                allocation, 
                session, 
                exam_str, 
                seating_available
            )
                subject = f"VTU Exam Seat Allocation - {allocation.subject_code}"

                
                # Send email
                success, error = self.send_email(student.email, subject, html_body)
                
                # Log email
                email_log = EmailLog(
                    session_id=session_id,
                    student_usn=student_usn,
                    student_email=student.email,
                    email_type='seat_allocation',
                    subject=subject,
                    sent_status='sent' if success else 'failed',
                    sent_at=datetime.now() if success else None,
                    error_message=error
                )
                db.session.add(email_log)
                
                # Update allocation
                if success:
                    allocation.email_sent = True
                    allocation.email_sent_at = datetime.now()
                
                db.session.commit()
                
                return success, error
                
            except Exception as e:
                return False, str(e)
    
    def send_reminder_email(self, student_usn, session_id):
        """Send reminder email 15 minutes before exam"""
        with self.app.app_context():
            try:
                allocation = DetailedAllocation.query.filter_by(
                    session_id=session_id,
                    student_usn=student_usn
                ).first()
                
                if not allocation:
                    return False, "Allocation not found"
                
                student = Student.query.filter_by(usn=student_usn).first()
                if not student or not student.email:
                    return False, "Student email not found"
                
                session = AllocationSession.query.filter_by(session_id=session_id).first()
                if not session:
                    return False, "Session not found"
                
                # Generate reminder email
                html_body = self._generate_reminder_email(student, allocation, session)
                subject = f"⏰ REMINDER: Exam in 15 Minutes - {allocation.subject_code}"
                
                success, error = self.send_email(student.email, subject, html_body)
                
                # Log reminder email
                email_log = EmailLog(
                    session_id=session_id,
                    student_usn=student_usn,
                    student_email=student.email,
                    email_type='reminder',
                    subject=subject,
                    sent_status='sent' if success else 'failed',
                    sent_at=datetime.now() if success else None,
                    error_message=error
                )
                db.session.add(email_log)
                db.session.commit()
                
                return success, error
                
            except Exception as e:
                return False, str(e)
    
    def _generate_allocation_email(self, student, allocation, session):
        """Generate seat allocation email HTML"""
        
        if session.exam_date and session.exam_time:
            exam_datetime = datetime.combine(session.exam_date, session.exam_time)
            exam_str = exam_datetime.strftime("%d %B %Y, %I:%M %p")
            seating_available = (exam_datetime - timedelta(minutes=15)).strftime("%I:%M %p")
        else:
            exam_str = "To be announced"
            seating_available = "15 minutes before exam"
        
        seating_url = f"{self.public_url}/student/seating-plan/{session.session_id}/{student.usn}"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 650px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.12); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .content {{ padding: 35px; }}
        .info-box {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 6px; }}
        .info-row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #dee2e6; }}
        .info-row:last-child {{ border-bottom: none; }}
        .label {{ font-weight: 600; color: #495057; }}
        .value {{ color: #212529; text-align: right; }}
        .highlight {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin: 20px 0; border-radius: 6px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 35px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; }}
        .instructions {{ background: #e7f3ff; border-left: 4px solid #0066cc; padding: 20px; margin: 20px 0; border-radius: 6px; }}
        .footer {{ background: #f8f9fa; padding: 25px; text-align: center; color: #6c757d; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 VTU Exam Seat Allocation</h1>
            <p>Your seat has been successfully allocated</p>
        </div>
        
        <div class="content">
            <div style="font-size: 18px; margin-bottom: 20px;">Dear <strong>{student.name}</strong>,</div>
            <p>Your seat has been allocated for the upcoming VTU examination. Please find your complete details below:</p>
            
            <div class="info-box">
                <h3 style="margin: 0 0 15px 0; color: #495057;">📚 Examination Details</h3>
                <div class="info-row">
                    <span class="label">USN:</span>
                    <span class="value"><strong>{student.usn}</strong></span>
                </div>
                <div class="info-row">
                    <span class="label">Subject Code:</span>
                    <span class="value">{allocation.subject_code}</span>
                </div>
                <div class="info-row">
                    <span class="label">Subject Name:</span>
                    <span class="value">{allocation.subject_name}</span>
                </div>
                <div class="info-row">
                    <span class="label">Branch:</span>
                    <span class="value">{allocation.branch}</span>
                </div>
                <div class="info-row">
                    <span class="label">Exam Date & Time:</span>
                    <span class="value"><strong>{exam_str}</strong></span>
                </div>
            </div>
            
            <div class="info-box">
                <h3 style="margin: 0 0 15px 0; color: #495057;">🪑 Your Seat Allocation</h3>
                <div class="info-row">
                    <span class="label">Examination Hall:</span>
                    <span class="value"><strong>{allocation.room_name}</strong></span>
                </div>
                <div class="info-row">
                    <span class="label">Room Code:</span>
                    <span class="value">{allocation.room_code}</span>
                </div>
                <div class="info-row">
                    <span class="label">Seat Number:</span>
                    <span class="value" style="color: #28a745; font-weight: bold; font-size: 18px;">{allocation.seat_number}</span>
                </div>
                <div class="info-row">
                    <span class="label">Desk Position:</span>
                    <span class="value">Row {allocation.row_num}, Column {allocation.col_num}</span>
                </div>
            </div>
            
            <div class="highlight">
                <h3 style="margin: 0 0 10px 0; color: #856404;">⏰ IMPORTANT: Seating Plan Access</h3>
                <p style="margin: 8px 0; color: #856404;"><strong>The complete seating plan will be available online from {seating_available}</strong> (15 minutes before the exam starts).</p>
                <p style="margin: 8px 0; color: #856404;">You will also receive a reminder email 15 minutes before the exam with the seating plan link.</p>
            </div>
            
            <center>
                <a href="{seating_url}" class="button">🗺️ View Seating Plan (Available from {seating_available})</a>
            </center>
            
            <div class="instructions">
                <h3 style="margin: 0 0 15px 0; color: #004085;">📋 Important Instructions</h3>
                <ul style="margin: 10px 0; padding-left: 25px; color: #004085;">
                    <li style="margin: 10px 0;">Report to the examination hall <strong>30 minutes before</strong> the scheduled exam time</li>
                    <li style="margin: 10px 0;">Carry your <strong>hall ticket and valid photo ID proof</strong> (Aadhar/College ID)</li>
                    <li style="margin: 10px 0;">Mobile phones and electronic devices are <strong style="color: #dc3545;">strictly prohibited</strong></li>
                    <li style="margin: 10px 0;">You will receive a reminder email 15 minutes before the exam</li>
                    <li style="margin: 10px 0;">Locate your seat using the seating plan before entering</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>VTU Examination Cell</strong></p>
            <p>Visvesvaraya Technological University</p>
            <p style="margin-top: 15px;">This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
        """
    
    def _generate_reminder_email(self, student, allocation, session):
        """Generate 15-minute reminder email"""
        
        exam_datetime = datetime.combine(session.exam_date, session.exam_time)
        exam_str = exam_datetime.strftime("%I:%M %p")
        seating_url = f"{self.public_url}/student/seating-plan/{session.session_id}/{student.usn}"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 650px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.12); }}
        .header {{ background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 40px 30px; text-align: center; }}
        .urgent {{ background: #fff3cd; border: 2px solid #ffc107; padding: 25px; margin: 20px 0; border-radius: 8px; text-align: center; }}
        .button {{ display: inline-block; background: #28a745; color: white; padding: 16px 40px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; font-size: 16px; }}
        .info-box {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 6px; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ EXAM REMINDER</h1>
            <p style="font-size: 20px; margin: 10px 0;">Your exam starts in 15 minutes!</p>
        </div>
        
        <div style="padding: 35px;">
            <div class="urgent">
                <h2 style="margin: 0 0 15px 0; color: #856404;">⚠️ URGENT: Your Exam is Starting Soon!</h2>
                <p style="font-size: 18px; margin: 10px 0; color: #856404;">
                    <strong>{allocation.subject_code} - {allocation.subject_name}</strong>
                </p>
                <p style="font-size: 24px; margin: 15px 0; color: #dc3545;">
                    <strong>Starts at: {exam_str}</strong>
                </p>
            </div>
            
            <div class="info-box">
                <h3 style="margin: 0 0 15px 0;">🪑 Your Seat Details</h3>
                <p style="margin: 8px 0;"><strong>Room:</strong> {allocation.room_name} ({allocation.room_code})</p>
                <p style="margin: 8px 0;"><strong>Seat Number:</strong> <span style="color: #28a745; font-size: 20px; font-weight: bold;">{allocation.seat_number}</span></p>
                <p style="margin: 8px 0;"><strong>Position:</strong> Row {allocation.row_num}, Column {allocation.col_num}</p>
            </div>
            
            <center>
                <a href="{seating_url}" class="button">📍 VIEW SEATING PLAN NOW</a>
            </center>
            
            <div style="background: #e7f3ff; border-left: 4px solid #0066cc; padding: 20px; margin: 20px 0; border-radius: 6px;">
                <h3 style="margin: 0 0 10px 0; color: #004085;">✅ Quick Checklist</h3>
                <ul style="margin: 5px 0; padding-left: 25px; color: #004085;">
                    <li>Hall ticket ✓</li>
                    <li>Photo ID ✓</li>
                    <li>Stationery ✓</li>
                    <li>Mobile phone - Leave outside ✓</li>
                </ul>
            </div>
            
            <p style="text-align: center; font-size: 16px; color: #dc3545; margin: 20px 0;">
                <strong>⚠️ Rush to the examination hall immediately!</strong>
            </p>
        </div>
        
        <div class="footer">
            <p><strong>VTU Examination Cell</strong></p>
            <p>Good luck with your exam!</p>
        </div>
    </div>
</body>
</html>
        """

    def generate_staff_allocation_email(self, staff_id, session_id):
        try:
            staff = Staff.query.filter_by(staff_id=staff_id).first()
            if not staff:
                return None, "Staff not found"
        
        # Get staff room allocation
            allocation = StaffRoomAllocation.query.filter_by(
               staff_id=staff_id,
            session_id=session_id
            ).first()
        
            if not allocation:
                return None, "No allocation found for this staff"
        
        # Get session details
            session = AllocationSession.query.filter_by(session_id=session_id).first()
        
        # Get all students in this room
            students = DetailedAllocation.query.filter_by(
            session_id=session_id,
            room_code=allocation.room_code
            ).all()
        
        # Count students by branch
            branch_counts = {}
            for student in students:
                branch = student.branch or 'Unknown'
                branch_counts[branch] = branch_counts.get(branch, 0) + 1
        
        # Get unique subjects in room
            subjects = {}
            for student in students:
                subject_key = f"{student.subject_code} - {student.subject_name}"
                subjects[subject_key] = subjects.get(subject_key, 0) + 1
        
        # Format exam date and time
            exam_date_str = session.exam_date.strftime('%d %B %Y') if session.exam_date else 'TBD'
            exam_time_str = session.exam_time.strftime('%I:%M %p') if session.exam_time else 'TBD'
        
        # Generate email HTML
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 650px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .content {{
            padding: 35px;
        }}
        .role-badge {{
            display: inline-block;
            background: {'linear-gradient(135deg, #28a745, #20c997)' if allocation.role == 'Chief Invigilator' else 'linear-gradient(135deg, #007bff, #0056b3)'};
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 16px;
            margin: 15px 0;
        }}
        .info-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }}
        .branch-item {{
            background: white;
            padding: 12px 15px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .count-badge {{
            background: #28a745;
            color: white;
            padding: 6px 12px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 18px;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 16px 40px;
            text-decoration: none;
            border-radius: 8px;
            margin: 20px 0;
            font-weight: bold;
            font-size: 16px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 13px;
        }}
        .instructions {{
            background: #e7f3ff;
            border-left: 4px solid #0066cc;
            padding: 20px;
            margin: 20px 0;
            border-radius: 6px;
        }}
        .subject-list {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #ffc107;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ Staff Room Allocation</h1>
            <p style="font-size: 18px; margin: 10px 0;">VTU Examination - {session_id}</p>
        </div>
        
        <div class="content">
            <h2>Dear {staff.staff_name},</h2>
            
            <p style="font-size: 16px; line-height: 1.6;">
                You have been assigned as <strong>{allocation.role}</strong> for the upcoming examination.
            </p>
            
            <div class="role-badge">
                {'👨‍💼 Chief Invigilator' if allocation.role == 'Chief Invigilator' else '👨‍🏫 Invigilator'}
            </div>
            
            <div class="info-box">
                <h3 style="margin: 0 0 15px 0; color: #667eea;">📍 Your Assigned Room</h3>
                <p style="margin: 8px 0;"><strong>Room:</strong> {allocation.room_name} ({allocation.room_code})</p>
                <p style="margin: 8px 0;"><strong>Total Students:</strong> <span style="color: #28a745; font-size: 20px; font-weight: bold;">{len(students)}</span></p>
                <p style="margin: 8px 0;"><strong>Exam Date:</strong> {exam_date_str} at {exam_time_str}</p>
            </div>
            
            <h3 style="margin: 25px 0 15px 0; color: #333;">📊 Branch-wise Student Distribution</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 10px;">
                {''.join([f'''
                <div class="branch-item">
                    <span style="font-weight: bold; color: #333;">🎓 {branch}</span>
                    <span class="count-badge">{count}</span>
                </div>
                ''' for branch, count in sorted(branch_counts.items(), key=lambda x: x[1], reverse=True)])}
            </div>
            
            <div class="subject-list">
                <h3 style="margin: 0 0 15px 0; color: #856404;">📚 Subjects in Your Room</h3>
                {''.join([f'<p style="margin: 8px 0; color: #856404;"><strong>{subject}</strong> - {count} student(s)</p>' for subject, count in subjects.items()])}
            </div>
            
            <div class="instructions">
                <h3 style="margin: 0 0 15px 0; color: #004085;">🔐 Access Student Seating Arrangement</h3>
                <p style="margin: 10px 0; color: #004085;">
                    To view the complete seating arrangement and student details, please login to the <strong>AI-Based Exam Seating Arrangement System</strong>.
                </p>
                <center>
                    <a href="http://127.0.0.1:5000/staff-registration" class="button">
                        🔓 Login to View Seating Plan
                    </a>
                </center>
                <p style="margin: 15px 0 5px 0; color: #004085;">
                    <strong>Your Login Credentials:</strong>
                </p>
                <ul style="margin: 5px 0; padding-left: 25px; color: #004085;">
                    <li><strong>Staff ID:</strong> {staff.staff_id}</li>
                    <li><strong>Department:</strong> {staff.department}</li>
                </ul>
            </div>
            
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin: 20px 0; border-radius: 6px;">
                <h3 style="margin: 0 0 10px 0; color: #856404;">⚠️ Important Instructions</h3>
                <ul style="margin: 10px 0; padding-left: 25px; color: #856404;">
                    <li style="margin: 10px 0;">Report to the examination hall <strong>30 minutes before</strong> the scheduled exam time</li>
                    <li style="margin: 10px 0;">Carry your <strong>staff ID card</strong></li>
                    <li style="margin: 10px 0;">Review the seating arrangement before the exam</li>
                    <li style="margin: 10px 0;">Ensure all students are seated according to the allocation</li>
                    <li style="margin: 10px 0;">Mobile phones are <strong style="color: #dc3545;">strictly prohibited</strong> in the examination hall</li>
                </ul>
            </div>
            
            <p style="text-align: center; font-size: 16px; color: #667eea; margin: 20px 0;">
                <strong>Thank you for your cooperation!</strong>
            </p>
        </div>
        
        <div class="footer">
            <p><strong>VTU Examination Cell</strong></p>
            <p>Visvesvaraya Technological University</p>
            <p style="margin-top: 15px;">This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Email subject
            subject = f"Room Allocation - {allocation.role} - {allocation.room_name} ({session_id})"
        
            return html_content, subject
        
        except Exception as e:
            print(f"Error generating staff email: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, str(e)


    def send_staff_allocation_email(self, staff_id, session_id):
    
        try:
        # Get staff details
            staff = Staff.query.filter_by(staff_id=staff_id).first()
            if not staff or not staff.email:
                return False, "Staff not found or email not available"
        
        # Generate email content
            html_content, subject = self.generate_staff_allocation_email(staff_id, session_id)
        
            if not html_content:
                return False, subject  # subject contains error message
        
        # Send email
            success = self.send_email(
            to_email=staff.email,
            subject=subject,
            html_body=html_content
            )
        
            if success:
                print(f"✅ Email sent to {staff.staff_name} ({staff.email})")
                return True, "Email sent successfully"
            else:
                return False, "Failed to send email"
            
        except Exception as e:
            print(f"Error sending staff email: {str(e)}")
            return False, str(e)


# Initialize email service
email_service = EmailService(app)

# ===============================================================================
# STEP 6: SCHEDULE REMINDER EMAILS FOR A SESSION
# ===============================================================================

def schedule_reminder_emails(session_id):
    """Schedule reminder emails 15 minutes before exam for all students"""
    with app.app_context():
        try:
            # Get session
            session = AllocationSession.query.filter_by(session_id=session_id).first()
            if not session or not session.exam_date or not session.exam_time:
                print(f"❌ Cannot schedule reminders: No exam date/time for session {session_id}")
                return False
            
            # Calculate reminder time (15 minutes before exam)
            exam_datetime = datetime.combine(session.exam_date, session.exam_time)
            reminder_time = exam_datetime - timedelta(minutes=15)
            
            # Check if reminder time is in the future
            if reminder_time <= datetime.now():
                print(f"❌ Cannot schedule reminders: Exam time has passed for session {session_id}")
                return False
            
            # Get all students in this session
            allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()
            student_usns = list(set([a.student_usn for a in allocations]))
            
            # Schedule reminder for each student
            for usn in student_usns:
                scheduler.add_job(
                    func=email_service.send_reminder_email,
                    trigger=DateTrigger(run_date=reminder_time),
                    args=[usn, session_id],
                    id=f"reminder_{session_id}_{usn}",
                    replace_existing=True
                )
            
            print(f"✅ Scheduled {len(student_usns)} reminder emails for {reminder_time}")
            return True
            
        except Exception as e:
            print(f"❌ Error scheduling reminders: {str(e)}")
            return False

# ===============================================================================
# STEP 7: FIXED EMAIL SENDING API WITH PROGRESS TRACKING
# ===============================================================================

@app.route('/api/send-allocation-emails/<session_id>', methods=['POST'])
def send_allocation_emails(session_id):
    """Send immediate allocation emails + schedule 15-min reminders"""
    try:
        allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()
        
        if not allocations:
            return jsonify({'success': False, 'message': 'No allocations found'})
        
        student_usns = list(set([a.student_usn for a in allocations]))
        
        def send_emails_background():
            with app.app_context():  # ← FIXES THE ERROR
                success_count = 0
                failed_count = 0
                failed_students = []
                
                for usn in student_usns:
                    success, error = email_service.send_seat_allocation_email(usn, session_id)
                    if success:
                        success_count += 1
                        print(f"✅ Email sent to {usn}")
                    else:
                        failed_count += 1
                        failed_students.append({'usn': usn, 'error': error})
                        print(f"❌ Failed to send email to {usn}: {error}")
                
                # Update session
                session = AllocationSession.query.filter_by(session_id=session_id).first()
                if session:
                    session.emails_sent = True
                    session.email_sent_at = datetime.now()
                    db.session.commit()
                
                print(f"📧 Email Summary: {success_count} sent, {failed_count} failed")
                
                # Schedule reminder emails
                schedule_reminder_emails(session_id)
        
        thread = threading.Thread(target=send_emails_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Sending {len(student_usns)} emails and scheduling reminders',
            'total_students': len(student_usns)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/email-progress/<session_id>')
def get_email_progress(session_id):
    """Get real-time email sending progress"""
    try:
        logs = EmailLog.query.filter_by(session_id=session_id).all()
        
        # Separate by email type
        allocation_logs = [l for l in logs if l.email_type == 'seat_allocation']
        reminder_logs = [l for l in logs if l.email_type == 'reminder']
        
        allocation_sent = len([l for l in allocation_logs if l.sent_status == 'sent'])
        allocation_failed = len([l for l in allocation_logs if l.sent_status == 'failed'])
        
        reminder_sent = len([l for l in reminder_logs if l.sent_status == 'sent'])
        reminder_scheduled = len(allocation_logs) - len(reminder_logs)  # Scheduled but not sent yet
        
        total = len(allocation_logs)
        percentage = (allocation_sent / total * 100) if total > 0 else 0
        
        return jsonify({
            'success': True,
            'allocation_emails': {
                'total': total,
                'sent': allocation_sent,
                'failed': allocation_failed,
                'percentage': round(percentage, 1)
            },
            'reminder_emails': {
                'sent': reminder_sent,
                'scheduled': reminder_scheduled
            },
            'status': 'completed' if (allocation_sent + allocation_failed) >= total else 'in_progress'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def session_to_dict(session):
    """Convert SQLAlchemy session object to dictionary"""
    if not session:
        return {}
    
    return {
        'session_id': getattr(session, 'session_id', ''),
        'algorithm_used': getattr(session, 'algorithm_used', 'AI Algorithm'),
        'total_students': getattr(session, 'total_students', 0),
        'total_desks': getattr(session, 'total_desks', 0),
        'total_rooms': getattr(session, 'total_rooms', 0),
        'fitness_score': getattr(session, 'fitness_score', 0.85),
        'created_at': str(getattr(session, 'created_at', '')),
        'is_active': getattr(session, 'is_active', True),
    }

    
# Routes
# @app.route('/')
# def index():
#     return render_template('chatbot_with_voice.html')

@app.route('/chatbot')
def chatbot_route():
    return render_template('chatbot_with_voice.html')

@app.route('/')
def landing_page():
    """Landing page with role selection"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """Enhanced dashboard with subject-wise statistics"""
    try:
        total_students = db.session.query(func.count(Student.id)).scalar() or 0
        total_registrations = db.session.query(func.count(StudentSubject.id)).scalar() or 0
        total_subjects = db.session.query(func.count(Subject.id)).scalar() or 0

        branch_stats = db.session.query(
            Student.branch.label('branch'),
            func.count(distinct(Student.id)).label('student_count'),
            func.count(StudentSubject.id).label('registration_count')
        ).outerjoin(StudentSubject, Student.usn == StudentSubject.usn)\
         .group_by(Student.branch).all()

        semester_stats = db.session.query(
            Student.semester.label('semester'),
            func.count(distinct(Student.id)).label('student_count'),
            func.count(StudentSubject.id).label('registration_count')
        ).outerjoin(StudentSubject, Student.usn == StudentSubject.usn)\
         .group_by(Student.semester).order_by(Student.semester).all()


        return render_template(
            'dashboard.html',
            total_students=total_students,
            total_registrations=total_registrations,
            total_subjects=total_subjects,
            branch_stats=branch_stats,
            semester_stats=semester_stats
        )
    except Exception as e:
        print("Dashboard error:", e)
        return render_template('dashboard.html',
            total_students=0, total_registrations=0, total_subjects=0,
            branch_stats=[], semester_stats=[]
        )


@app.route('/subjects')
def subjects_management():
    """Subject-wise student management"""
    try:
        branch = request.args.get('branch', '')
        semester = request.args.get('semester', '', type=int)
        subject_code = request.args.get('subject_code', '')
        
        query = db.session.query(
            Subject.id,
            Subject.subject_code,
            Subject.subject_name,
            Subject.semester,
            Subject.branch,
            Subject.credits,
            Subject.subject_type,
            func.count(StudentSubject.id).label('registered_students')
        ).outerjoin(StudentSubject, Subject.id == StudentSubject.subject_id)\
         .group_by(Subject.id)
        
        if branch:
            query = query.filter(Subject.branch == branch)
        if semester:
            query = query.filter(Subject.semester == semester)
        if subject_code:
            query = query.filter(Subject.subject_code.contains(subject_code))
        
        subjects = query.order_by(Subject.branch, Subject.semester, Subject.subject_code).all()
        
        branches = [branch[0] for branch in db.session.query(Subject.branch.distinct()).all()]
        semesters = [sem[0] for sem in db.session.query(Subject.semester.distinct()).order_by(Subject.semester).all()]
        
        return render_template('subjects.html', 
                             subjects=subjects,
                             branches=branches,
                             semesters=semesters,
                             current_branch=branch,
                             current_semester=semester,
                             current_subject_code=subject_code)
    except Exception as e:
        print(f"Subjects management error: {e}")
        return render_template('subjects.html', subjects=[], branches=[], semesters=[])

@app.route('/subjects/<subject_code>/students')
def subject_students(subject_code):
    """Get all students registered UNDER a specific subject"""
    try:
        subject = Subject.query.filter_by(subject_code=subject_code).first()
        if not subject:
            return render_template('subject_students.html', subject=None, students=[])
        
        students = db.session.query(
            StudentSubject.student_name.label('name'),
            StudentSubject.usn,
            StudentSubject.semester,
            StudentSubject.registration_type,
            StudentSubject.is_backlog,
            StudentSubject.exam_fee_paid,
            StudentSubject.seat_allocated,
            StudentSubject.allocated_room,
            StudentSubject.allocated_seat,
            StudentSubject.created_at
        ).filter(StudentSubject.subject_code == subject_code)\
         .order_by(StudentSubject.usn).all()

        # Get additional student details if needed
        enhanced_students = []
        for student in students:
            student_details = Student.query.filter_by(usn=student.usn).first()
            enhanced_student = {
                'name': student.name,
                'usn': student.usn,
                'branch': student_details.branch if student_details else 'Unknown',
                'semester': student.semester,
                'email': student_details.email if student_details else 'Unknown',
                'has_backlogs': student_details.has_backlogs if student_details else False,
                'registration_type': student.registration_type,
                'is_backlog': student.is_backlog,
                'exam_fee_paid': student.exam_fee_paid,
                'seat_allocated': student.seat_allocated,
                'allocated_room': student.allocated_room,
                'allocated_seat': student.allocated_seat,
                'created_at': student.created_at
            }
            enhanced_students.append(enhanced_student)

        return render_template('subject_students.html', subject=subject, students=enhanced_students)
    except Exception as e:
        print(f"Subject students error: {e}")
        return render_template('subject_students.html', subject=None, students=[])



@app.route('/exam-scheduler')
def exam_scheduler():
    """Enhanced exam scheduler with AI allocation"""
    if not session.get('admin_portal_access'):
        flash('Please enter the admin portal password first.', 'warning')
        return redirect(url_for('admin_login'))
    try:
        # Get subjects with registered students
        subjects_with_students = db.session.query(
            Subject.subject_code,
            Subject.subject_name,
            Subject.branch,
            Subject.semester,
            func.count(StudentSubject.id).label('student_count')
        ).join(StudentSubject, Subject.id == StudentSubject.subject_id)\
         .group_by(Subject.id)\
         .having(func.count(StudentSubject.id) > 0)\
         .order_by(Subject.branch, Subject.semester, Subject.subject_code).all()
        
        # Get exam rooms
        rooms = ExamRoom.query.filter_by(is_active=True).order_by(ExamRoom.room_code).all()
        
        # Get recent exam schedules
        recent_exams = ExamSchedule.query.order_by(ExamSchedule.created_at.desc()).limit(10).all()
        
        return render_template('exam-scheduler.html', 
                             subjects=subjects_with_students,
                             rooms=rooms,
                             recent_exams=recent_exams)
    except Exception as e:
        print(f"Exam scheduler error: {e}")
        return render_template('exam-scheduler.html', subjects=[], rooms=[], recent_exams=[])

@app.route('/api/schedule-exam-with-allocation', methods=['POST'])
def api_schedule_exam_with_allocation():
    """API endpoint for scheduling exams with AI allocation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        print(f"🎯 Exam scheduling request received: {data}")
        ai_seat_allocator = CompleteAISeatAllocator()
        
        # Use the enhanced AI allocator
        result = ai_seat_allocator.schedule_exam_with_allocation(data)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Exam scheduling API error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Scheduling failed: {str(e)}'
        }), 500

@app.route('/api/subjects-with-students', methods=['GET'])
def api_subjects_with_students():
    """Get subjects with registered students"""
    try:
        subjects = db.session.query(
            Subject.subject_code,
            Subject.subject_name,
            Subject.branch,
            Subject.semester,
            func.count(StudentSubject.id).label('student_count')
        ).join(StudentSubject, Subject.subject_code == StudentSubject.subject_code)\
         .group_by(Subject.id)\
         .having(func.count(StudentSubject.id) > 0)\
         .order_by(Subject.branch, Subject.semester).all()
        
        subject_list = [{
            'subject_code': s.subject_code,
            'subject_name': s.subject_name,
            'branch': s.branch,
            'semester': s.semester,
            'student_count': s.student_count
        } for s in subjects]
        
        return jsonify({'success': True, 'subjects': subject_list})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/exam-rooms', methods=['GET'])
def api_exam_rooms():
    """Get all exam rooms"""
    try:
        rooms = ExamRoom.query.filter_by(is_active=True).order_by(ExamRoom.room_code).all()
        room_list = [{
            'room_code': r.room_code,
            'room_name': r.room_name,
            'capacity': r.capacity,
            'rows': r.rows,
            'cols': r.cols
        } for r in rooms]
        
        return jsonify({'success': True, 'rooms': room_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/add-exam-room', methods=['POST'])
def api_add_exam_room():
    """Add new exam room"""
    try:
        data = request.get_json()
        
        # Check if room code exists
        existing = ExamRoom.query.filter_by(room_code=data['room_code']).first()
        if existing:
            return jsonify({'success': False, 'message': 'Room code already exists'})
        
        new_room = ExamRoom(
            room_code=data['room_code'],
            room_name=data['room_name'],
            capacity=data['capacity'],
            rows=data['rows'],
            cols=data['cols']
        )
        
        db.session.add(new_room)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Room added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/delete-exam-room', methods=['POST'])
def api_delete_exam_room():
    """Delete exam room"""
    try:
        data = request.get_json()
        room = ExamRoom.query.filter_by(room_code=data['room_code']).first()
        
        if not room:
            return jsonify({'success': False, 'message': 'Room not found'})
        
        db.session.delete(room)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Room deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/ai-process-exams', methods=['POST'])
def api_ai_process_exams():
    """Main AI processing endpoint for seat allocation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Get selected subjects
        subjects = data.get('subjects', [])
        algorithm = data.get('algorithm', 'hybrid_ai')

        exam_date = data.get('examDate') or data.get('start_date')  # Try both keys
        exam_time = data.get('examTime') or data.get('morning_time')
        
        if not subjects:
            return jsonify({'success': False, 'message': 'No subjects selected'}), 400
        
        print(f"🤖 Processing {len(subjects)} subjects: {subjects}")
        print(f"🧠 Using algorithm: {algorithm}")
        print(f"📅 Exam Date: {exam_date}, Time: {exam_time}")
        ai_seat_allocator = CompleteAISeatAllocator()
        
        # Use the AI allocator
        result = ai_seat_allocator.allocate_students_for_subjects(subjects, algorithm,exam_date=exam_date,exam_time=exam_time)
        
        # Add additional information for frontend
        if result['success']:
            result['exams_scheduled'] = len(subjects)
            result['efficiency'] = int(result.get('fitness_score', 0) * 20 + 80)
            
            # Create basic schedule information
            result['schedule'] = []
            for subject_code in subjects:
                student_count = StudentSubject.query.filter_by(subject_code=subject_code).count()
                result['schedule'].append({
                    'subject_code': subject_code,
                    'subject_name': f'Subject {subject_code}',
                    'exam_date': data.get('start_date', '2025-10-20'),
                    'exam_time': data.get('morning_time', '10:00 AM'),
                    'student_count': student_count
                })
            
            # FIXED: Extract session_id from result and ensure it's a STRING
            session_id = result.get('session_id')
            if session_id:
                result['session_id'] = str(session_id)  # ← ENSURE STRING
                print(f"✅ Allocation session_id: {result['session_id']}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ AI processing error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'AI processing failed: {str(e)}'
        }), 500


# ===================================================================
# FIX 2: CORRECTED view_allocation_results() Route
# ===================================================================

@app.route('/allocation-results/<session_id>')
def view_allocation_results(session_id):
    """Display detailed desk-based allocation results"""
    try:
        print(f"📊 Loading allocation results for session: {session_id}")
        
        # FIXED: Validate session_id first
        if not session_id or session_id == '[object Object]' or session_id == 'undefined':
            print(f"❌ Invalid session_id: {session_id}")
            return render_template('allocation_results.html',
                                 session=None,
                                 allocations=[],
                                 desk_partnerships={},
                                 error=f"Invalid session ID: {session_id}")
        
        # Ensure session_id is a string
        session_id = str(session_id).strip()
        
        # Get allocation session
        allocation_session = AllocationSession.query.filter_by(session_id=session_id).first()
        
        if not allocation_session:
            print(f"❌ Session {session_id} not found in allocation_sessions table")
            # Check if allocations exist without session record
            allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()
            
            if allocations:
                print(f"✅ Found {len(allocations)} allocations without session record")
                # Create a dictionary instead of dummy object
                from datetime import datetime
                allocation_session = {
                    'session_id': session_id,
                    'algorithm_used': 'AI Algorithm',
                    'total_students': len(allocations),
                    'total_desks': len(allocations) // 2,
                    'total_rooms': len(set(a.room_code for a in allocations)),
                    'fitness_score': 0.85,
                    'created_at': datetime.now()
                }
            else:
                print(f"❌ No allocations found for session {session_id}")
                return render_template('allocation_results.html',
                                     session=None,
                                     allocations=[],
                                     desk_partnerships={},
                                     error=f"No data found for session: {session_id}")
        else:
            # Get detailed allocations
            allocations = DetailedAllocation.query.filter_by(session_id=session_id)\
                                                  .order_by(DetailedAllocation.room_code,
                                                           DetailedAllocation.desk_id,
                                                           DetailedAllocation.seat_number).all()
        
        print(f"✅ Found {len(allocations)} allocations for session {session_id}")
        
        # Group allocations by desk_id for partnership analysis
        desk_partnerships = {}
        for allocation in allocations:
            if allocation.desk_id:
                if allocation.desk_id not in desk_partnerships:
                    desk_partnerships[allocation.desk_id] = []
                desk_partnerships[allocation.desk_id].append(allocation)
        
        print(f"🪑 Found {len(desk_partnerships)} desk partnerships")
        
        # Convert SQLAlchemy objects to dictionaries for template
        allocations_data = []
        for alloc in allocations:
            allocations_data.append({
                'student_usn': alloc.student_usn,
                'student_name': alloc.student_name,
                'subject_code': alloc.subject_code,
                'subject_name': alloc.subject_name,
                'branch': alloc.branch,
                'room_code': alloc.room_code,
                'room_name': alloc.room_name,
                'seat_number': alloc.seat_number,
                'row_num': alloc.row_num,
                'col_num': alloc.col_num,
                'desk_id': alloc.desk_id,
                'desk_partner_usn': alloc.desk_partner_usn,
                'allocation_method': alloc.allocation_method
            })
        
        # FIXED: Handle session as either dict or SQLAlchemy object
        if isinstance(allocation_session, dict):
            session_dict = allocation_session
        else:
            # Convert SQLAlchemy object to dict
            session_dict = {
                'session_id': allocation_session.session_id,
                'algorithm_used': allocation_session.algorithm_used,
                'total_students': allocation_session.total_students,
                'total_desks': allocation_session.total_desks if hasattr(allocation_session, 'total_desks') else 0,
                'total_rooms': allocation_session.total_rooms if hasattr(allocation_session, 'total_rooms') else 0,
                'fitness_score': allocation_session.fitness_score if hasattr(allocation_session, 'fitness_score') else 0,
                'created_at': allocation_session.created_at if hasattr(allocation_session, 'created_at') else None
            }
        
        # Pass to template
        return render_template('allocation_results.html',
                             session=session_dict,
                             allocations=allocations_data,
                             desk_partnerships=desk_partnerships)
        
    except Exception as e:
        print(f"❌ Error loading allocation results: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('allocation_results.html',
                             session=None,
                             allocations=[],
                             desk_partnerships={},
                             error=f"Error loading results: {str(e)}")

@app.route('/api/allocation-results/<session_id>', methods=['GET'])
def get_allocation_results_api(session_id):
    """
    FIXED: API endpoint to fetch allocation results
    """
    try:
        from app import AllocationSession, DetailedAllocation
        
        if not session_id:
            return jsonify({'success': False, 'message': 'No session_id provided'}), 400
        
        # Query allocation session
        allocation_session = AllocationSession.query.filter_by(
            session_id=str(session_id)
        ).first()
        
        if not allocation_session:
            return jsonify({'success': False, 'message': 'Session not found'}), 404
        
        # Get all allocations
        detailed_allocations = DetailedAllocation.query.filter_by(
            session_id=str(session_id)
        ).all()
        
        # Convert to JSON
        allocations_data = []
        for alloc in detailed_allocations:
            allocations_data.append({
                'usn': alloc.student_usn,
                'name': alloc.student_name,
                'subject_code': alloc.subject_code,
                'subject_name': alloc.subject_name,
                'branch': alloc.branch,
                'room_code': alloc.room_code,
                'room_name': alloc.room_name,
                'seat_number': alloc.seat_number,
                'row_num': alloc.row_num,
                'col_num': alloc.col_num,
                'desk_id': alloc.desk_id,
                'desk_partner_usn': alloc.desk_partner_usn,
                'desk_position': alloc.desk_position
            })
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'algorithm': allocation_session.algorithm_used,
            'total_students': len(allocations_data),
            'allocations': allocations_data
        }), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/allocation-sessions/all', methods=['GET'])
def get_all_allocation_sessions():
    """Get all allocation sessions - FIXED VERSION"""
    try:
        # Get all sessions ordered by creation date (newest first)
        sessions = AllocationSession.query.order_by(
            AllocationSession.created_at.desc()
        ).all()
        
        if not sessions:
            print("⚠️ No allocation sessions found in database")
            return jsonify({
                'success': True,
                'sessions': [],
                'total': 0
            })
        
        # Format sessions data
        result = []
        for session in sessions:
            try:
                # Parse subject codes if stored as JSON string
                subject_codes = session.subject_codes
                if isinstance(subject_codes, str):
                    try:
                        subject_codes_list = json.loads(subject_codes)
                        subject_codes_str = ', '.join(subject_codes_list)
                    except:
                        subject_codes_str = subject_codes
                else:
                    subject_codes_str = str(subject_codes)
                
                result.append({
                    'session_id': session.session_id,
                    'subject_codes': subject_codes_str,
                    'total_students': session.total_students,
                    'total_rooms': session.total_rooms,
                    'algorithm_used': session.algorithm_used,
                    'fitness_score': session.fitness_score,
                    'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S') if session.created_at else None
                })
            except Exception as e:
                print(f"Error formatting session {session.session_id}: {e}")
                continue
        
        print(f"✅ Found {len(result)} allocation sessions")
        
        return jsonify({
            'success': True,
            'sessions': result,
            'total': len(result)
        })
        
    except Exception as e:
        print(f"❌ Error fetching allocation sessions: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/allocation-sessions/<session_id>', methods=['GET'])
def get_allocation_session(session_id):
    """Get specific allocation session"""
    try:
        session = AllocationSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404
        
        return jsonify({
            'success': True,
            'session': {
                'session_id': session.session_id,
                'subject_codes': session.subject_codes,
                'total_students': session.total_students,
                'total_rooms': session.total_rooms,
                'algorithm_used': session.algorithm_used,
                'fitness_score': session.fitness_score,
                'exam_date': session.exam_date.strftime('%Y-%m-%d') if session.exam_date else None,
                'exam_time': session.exam_time.strftime('%H:%M:%S') if session.exam_time else None,
                'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S') if session.created_at else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def _create_exam_schedule(subjects, data):
    """Create a simple exam schedule from a list of subject codes and request data."""
    from datetime import datetime, timedelta
    try:
        start_date = data.get('start_date') if data else None
        if not start_date:
            start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

        schedule = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        for i, subject_code in enumerate(subjects):
            exam_date = start + timedelta(days=i)
            # Skip weekends
            while exam_date.weekday() >= 5:
                exam_date += timedelta(days=1)

            subject = Subject.query.filter_by(subject_code=subject_code).first()
            student_count = StudentSubject.query.filter_by(subject_code=subject_code).count()
            schedule.append({
                'subject_code': subject_code,
                'subject_name': subject.subject_name if subject else 'Unknown Subject',
                'exam_date': exam_date.strftime('%Y-%m-%d'),
                'exam_time': data.get('morning_time', '10:00 AM') if data else '10:00 AM',
                'student_count': student_count,
                'rooms': ['Optimally Allocated']
            })

        return schedule
    except Exception as e:
        print(f"Schedule creation error: {e}")
        return []

# NEW: AI Seat Allocation Routes
@app.route('/seat-allocation')
def seat_allocation_page():
    """AI seat allocation interface"""
    try:
        # Get available subjects with registered students
        subjects_with_students = db.session.query(
            Subject.subject_code,
            Subject.subject_name,
            Subject.branch,
            Subject.semester,
            func.count(StudentSubject.id).label('student_count')
        ).join(StudentSubject, Subject.id == StudentSubject.subject_id)\
         .group_by(Subject.id)\
         .having(func.count(StudentSubject.id) > 0)\
         .order_by(Subject.branch, Subject.semester, Subject.subject_code).all()
        
        # Get exam rooms
        rooms = ExamRoom.query.filter_by(is_active=True).order_by(ExamRoom.room_code).all()
        
        # Get recent exam schedules
        recent_exams = ExamSchedule.query.order_by(ExamSchedule.created_at.desc()).limit(10).all()
        
        return render_template('seat_allocation.html', 
                             subjects=subjects_with_students,
                             rooms=rooms,
                             recent_exams=recent_exams)
    except Exception as e:
        print(f"Seat allocation page error: {e}")
        return render_template('seat_allocation.html', subjects=[], rooms=[], recent_exams=[])
    
@app.route('/api/delete-student-from-subject', methods=['POST'])
def api_delete_student_from_subject():
    """Delete a student from a specific subject"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        usn = data.get('usn', '').strip()
        subject_code = data.get('subject_code', '').strip()
        
        if not usn or not subject_code:
            return jsonify({'success': False, 'message': 'USN and subject code are required'}), 400
        
        print(f"🗑️ Delete request: USN={usn}, Subject={subject_code}")
        
        # Find the student-subject relationship
        student_subject = StudentSubject.query.filter_by(
            usn=usn,
            subject_code=subject_code
        ).first()
        
        if not student_subject:
            return jsonify({
                'success': False, 
                'message': f'Student {usn} is not registered for subject {subject_code}'
            }), 404
        
        # Get student name for the response
        student_name = student_subject.student_name
        
        # Delete the student-subject relationship
        db.session.delete(student_subject)
        
        # Check if this was the student's only subject registration
        remaining_subjects = StudentSubject.query.filter_by(usn=usn).count()
        
        # If student has no more subjects, optionally delete from students table too
        # (Comment out this section if you want to keep the student record)
        if remaining_subjects == 1:  # Will be 0 after we commit the deletion above
            student = Student.query.filter_by(usn=usn).first()
            if student:
                print(f"🗑️ Deleting student {usn} from students table (no more subject registrations)")
                db.session.delete(student)
        
        # Also delete any seat allocations for this student-subject combination
        try:
            from sqlalchemy import and_
            SeatAllocation.query.filter(
                and_(
                    SeatAllocation.usn == usn,
                    SeatAllocation.subject_code == subject_code
                )
            ).delete()
        except Exception as seat_error:
            print(f"⚠️ Error deleting seat allocations: {seat_error}")
        
        # Commit all changes
        db.session.commit()
        
        print(f"✅ Successfully deleted {student_name} (USN: {usn}) from subject {subject_code}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {student_name} from {subject_code}',
            'deleted_student': {
                'usn': usn,
                'name': student_name,
                'subject_code': subject_code
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Delete error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error deleting student: {str(e)}'
        }), 500

@app.route('/api/room-dimensions/<room_code>')
def get_room_dimensions(room_code):
    """Get actual room dimensions from database"""
    try:
        room = ExamRoom.query.filter_by(room_code=room_code).first()
        if room:
            return jsonify({
                'success': True,
                'room_code': room.room_code,
                'room_name': room.room_name,
                'rows': room.rows,
                'cols': room.cols,
                'capacity': room.capacity
            })
        else:
            return jsonify({'success': False, 'message': 'Room not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/all-room-dimensions')
def get_all_room_dimensions():
    """Get all room dimensions"""
    try:
        rooms = ExamRoom.query.filter_by(is_active=True).all()
        room_data = {}
        for room in rooms:
            room_data[room.room_code] = {
                'room_name': room.room_name,
                'rows': room.rows,
                'cols': room.cols,
                'capacity': room.capacity
            }
        return jsonify({'success': True, 'rooms': room_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/exam-schedule/<int:schedule_id>/allocations')
def get_exam_allocations(schedule_id):
    """Get seat allocations for an exam schedule"""
    try:
        allocations = db.session.query(
            SeatAllocation.seat_number,
            SeatAllocation.row_num,
            SeatAllocation.col_num,
            Student.name,
            Student.usn,
            Student.branch,
            SeatAllocation.subject_code,
            ExamRoom.room_code,
            ExamRoom.room_name
        ).join(Student, SeatAllocation.student_id == Student.id)\
         .join(ExamRoom, SeatAllocation.room_id == ExamRoom.id)\
         .filter(SeatAllocation.exam_schedule_id == schedule_id)\
         .order_by(ExamRoom.room_code, SeatAllocation.row_num, SeatAllocation.col_num).all()
        
        result = []
        for allocation in allocations:
            result.append({
                'seat_number': allocation.seat_number,
                'row_num': allocation.row_num,
                'col_num': allocation.col_num,
                'student_name': allocation.name,
                'usn': allocation.usn,
                'branch': allocation.branch,
                'subject_code': allocation.subject_code,
                'room_code': allocation.room_code,
                'room_name': allocation.room_name
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Get allocations error: {e}")
        return jsonify([])

@app.route('/api/ai-allocate-seats', methods=['POST'])
def api_ai_allocate_seats():
    """Main API for AI seat allocation"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        selected_subjects = data.get('subjects', [])
        algorithm = data.get('algorithm', 'genetic')

        exam_date_str = data.get('examDate')  # Format: "YYYY-MM-DD"
        exam_time_str = data.get('examTime')
        
        if not selected_subjects:
            return jsonify({'success': False, 'message': 'No subjects selected'}), 400
        
        print(f"🚀 AI allocation request: {len(selected_subjects)} subjects, algorithm: {algorithm}")
        ai_seat_allocator = CompleteAISeatAllocator()

        result = ai_seat_allocator.allocate_students_for_subjects(
            selected_subjects, 
            algorithm,
            exam_date=exam_date_str,
            exam_time=exam_time_str
        )
        
        return jsonify(result)
        
        # # Run AI allocation
        # result = ai_seat_allocator.allocate_students_to_exams(selected_subjects, algorithm)
        
        # return jsonify(result)
        
    except Exception as e:
        print(f"❌ API error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'API error: {str(e)}'
        }), 500

@app.route('/api/get-allocation-results/<session_id>')
def api_get_allocation_results(session_id):
    """Get detailed allocation results"""
    try:
        # Get session info
        session = AllocationSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'success': False, 'message': 'Session not found'})
        
        # Get detailed allocations
        allocations = DetailedAllocation.query.filter_by(
            session_id=session_id
        ).order_by(DetailedAllocation.room_code, DetailedAllocation.row_num, DetailedAllocation.col_num).all()
        
        # Group by room
        room_data = defaultdict(list)
        for alloc in allocations:
            room_data[alloc.room_code].append({
                'usn': alloc.student_usn,
                'name': alloc.student_name,
                'branch': alloc.branch,
                'subject_code': alloc.subject_code,
                'seat_number': alloc.seat_number,
                'row_num': alloc.row_num,
                'col_num': alloc.col_num
            })
        
        return jsonify({
            'success': True,
            'session_info': {
                'session_id': session.session_id,
                'algorithm_used': session.algorithm_used,
                'total_students': session.total_students,
                'total_rooms': session.total_rooms,
                'fitness_score': session.fitness_score,
                'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S')
            },
            'room_allocations': dict(room_data),
            'total_allocations': len(allocations)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# @app.route('/allocation-results/<session_id>')
# def allocation_results_page(session_id):
#     """View allocation results page"""
#     return render_template('allocation_results.html', session_id=session_id)

@app.route('/allocation-results/<session_id>')
def allocation_results(session_id):
    allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()
    session = AllocationSession.query.filter_by(session_id=session_id).first()
    
    return render_template('allocation_results.html',
                         allocations=[{
                             'student_usn': a.student_usn,
                             'student_name': a.student_name,
                             'branch': a.branch,
                             'subject_code': a.subject_code,
                             'subject_name': a.subject_name,
                             'room_code': a.room_code,
                             'room_name': a.room_name,
                             'row_num': a.row_num,
                             'col_num': a.col_num,
                             'desk_id': a.desk_id,
                             'seat_number': a.seat_number,
                             'desk_partner_usn': a.desk_partner_usn
                         } for a in allocations],
                         session=session)


# Add this route to your Flask application to provide room-wise branch statistics

@app.route('/api/room-branch-statistics/<session_id>')
def get_room_branch_statistics(session_id):
    """Get branch-wise student count for each room in a session"""
    try:
        allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()

        if not allocations:
            return jsonify({'success': False, 'message': 'No allocations found'})

        # Group by room and count branches
        room_stats = {}

        for alloc in allocations:
            room_code = alloc.room_code
            branch = alloc.branch

            if room_code not in room_stats:
                room_stats[room_code] = {
                    'room_name': alloc.room_name,
                    'branches': {},
                    'total_students': 0
                }

            if branch not in room_stats[room_code]['branches']:
                room_stats[room_code]['branches'][branch] = 0

            room_stats[room_code]['branches'][branch] += 1
            room_stats[room_code]['total_students'] += 1

        # Calculate percentages
        for room_code in room_stats:
            total = room_stats[room_code]['total_students']
            for branch in room_stats[room_code]['branches']:
                count = room_stats[room_code]['branches'][branch]
                room_stats[room_code]['branches'][branch] = {
                    'count': count,
                    'percentage': round((count / total) * 100, 1)
                }

        return jsonify({
            'success': True,
            'session_id': session_id,
            'room_statistics': room_stats
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/overall-branch-statistics/<session_id>')
def get_overall_branch_statistics(session_id):
    """Get overall branch distribution across all rooms"""
    try:
        allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()

        if not allocations:
            return jsonify({'success': False, 'message': 'No allocations found'})

        branch_counts = {}
        total_students = 0

        for alloc in allocations:
            branch = alloc.branch
            if branch not in branch_counts:
                branch_counts[branch] = 0
            branch_counts[branch] += 1
            total_students += 1

        # Format response
        branch_stats = {}
        for branch, count in branch_counts.items():
            branch_stats[branch] = {
                'count': count,
                'percentage': round((count / total_students) * 100, 1)
            }

        return jsonify({
            'success': True,
            'session_id': session_id,
            'total_students': total_students,
            'branch_statistics': branch_stats
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/staff-view/<staff_id>')
def staff_view_page(staff_id):
    """Staff view page for allocated rooms"""
    return render_template('staff_view.html', staff_id=staff_id)

# ============================================
# STAFF PASSWORD PROTECTION
# ============================================

# Staff portal password (change this to your desired password)
STAFF_PORTAL_PASSWORD = "gsksjti@2025"  # CHANGE THIS TO YOUR PASSWORD

@app.route('/staff-login', methods=['GET', 'POST'])
def staff_login():
    """Staff portal password login page"""
    session.pop('staff_portal_access', None)

    if request.method == 'POST':
        entered_password = request.form.get('password')
        
        if entered_password == STAFF_PORTAL_PASSWORD:
            # Password correct - set session
            session['staff_portal_access'] = True
            flash('Access granted! Welcome to Staff Portal.', 'success')
            return redirect(url_for('staff_registration_page'))
        else:
            flash('Incorrect password. Access denied.', 'danger')
            return render_template('staff_login.html')
    
    return render_template('staff_login.html')


@app.route('/staff-registration')
def staff_registration_page():
    """Staff registration page - protected"""
    # Check if user has access
    if not session.get('staff_portal_access'):
        flash('Please enter the staff portal password first.', 'warning')
        return redirect(url_for('staff_login'))
    
    return render_template('staff_registration.html')


@app.route('/staff-logout')
def staff_logout():
    """Logout from staff portal"""
    session.pop('staff_portal_access', None)
    flash('You have been logged out from the staff portal.', 'info')
    return redirect(url_for('landing_page'))


@app.route('/admin/staff-management')
def admin_staff_management():
    """Admin page to manage staff and allocate to rooms"""
    return render_template('admin_staff_management.html')


@app.route('/api/staff/register', methods=['POST'])
def register_staff():
    """Register new staff member"""
    try:
        data = request.get_json()
        required_fields = ['staff_id', 'staff_name', 'department']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Check if staff_id already exists
        existing_staff = Staff.query.filter_by(staff_id=data['staff_id']).first()
        if existing_staff:
            return jsonify({
                'success': False,
                'message': f'Staff ID {data["staff_id"]} already registered'
            }), 400
        
        # Create new staff
        new_staff = Staff(
            staff_id=data['staff_id'],
            staff_name=data['staff_name'],
            department=data['department'],
            email=data.get('email'),
            phone=data.get('phone'),
            is_active=True
        )
        
        db.session.add(new_staff)
        db.session.commit()
        
        print(f"✅ Staff registered: {data['staff_name']} ({data['staff_id']})")
        
        return jsonify({
            'success': True,
            'message': 'Staff registered successfully',
            'staff': new_staff.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Staff registration error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Registration failed: {str(e)}'
        }), 500
    
@app.route('/api/staff/login', methods=['POST'])
def api_staff_login():
    """Staff login endpoint - VALIDATE STAFF ID"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        staff_id = data.get('staff_id', '').strip()
        
        if not staff_id:
            return jsonify({
                'success': False,
                'message': 'Staff ID is required'
            }), 400
        
        print(f"🔍 Login attempt: Staff ID = {staff_id}")
        
        # Find staff member in database
        staff = Staff.query.filter_by(staff_id=staff_id).first()
        
        if not staff:
            return jsonify({
                'success': False,
                'message': f'Staff ID "{staff_id}" not found. Please check your ID or register first.'
            }), 404
        
        if not staff.is_active:
            return jsonify({
                'success': False,
                'message': 'Your account is inactive. Please contact administrator.'
            }), 403
        
        print(f"✅ Login successful: {staff.staff_name} ({staff_id})")
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'staff': staff.to_dict()
        })
        
    except Exception as e:
        print(f"❌ Staff login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }), 500
    
ADMIN_PORTAL_PASSWORD = "admin@2025"  # CHANGE THIS TO YOUR PASSWORD

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Admin portal password login page - ALWAYS ASK FOR PASSWORD"""
    
    # Clear session every time this page loads - ensures password is always asked
    session.pop('admin_portal_access', None)
    
    if request.method == 'POST':
        entered_password = request.form.get('password')
        
        if entered_password == ADMIN_PORTAL_PASSWORD:
            session['admin_portal_access'] = True
            flash('Access granted! Welcome to Admin Portal.', 'success')
            return redirect(url_for('exam_scheduler'))
        else:
            flash('Incorrect password. Access denied.', 'danger')
            return render_template('admin_login.html')
    
    return render_template('admin_login.html')


@app.route('/admin-logout')
def admin_logout():
    """Logout from admin portal"""
    session.pop('admin_portal_access', None)
    flash('You have been logged out from the admin portal.', 'info')
    return redirect(url_for('landing_page'))    

@app.route('/api/staff/all', methods=['GET'])
def get_all_staff():
    """Get all registered staff members"""
    try:
        staff_members = Staff.query.order_by(Staff.staff_name).all()
        
        return jsonify({
            'success': True,
            'staff': [staff.to_dict() for staff in staff_members],
            'total': len(staff_members)
        })
        
    except Exception as e:
        print(f"❌ Error fetching staff: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/staff/<staff_id>', methods=['GET'])
def get_staff_by_id(staff_id):
    """Get staff details by staff_id"""
    try:
        staff = Staff.query.filter_by(staff_id=staff_id).first()
        
        if not staff:
            return jsonify({
                'success': False,
                'message': 'Staff not found'
            }), 404
        
        return jsonify({
            'success': True,
            'staff': staff.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/staff/<staff_id>/update', methods=['PUT'])
def update_staff(staff_id):
    """Update staff details"""
    try:
        staff = Staff.query.filter_by(staff_id=staff_id).first()
        
        if not staff:
            return jsonify({
                'success': False,
                'message': 'Staff not found'
            }), 404
        
        data = request.get_json()
        
        # Update fields
        if 'staff_name' in data:
            staff.staff_name = data['staff_name']
        if 'department' in data:
            staff.department = data['department']
        if 'email' in data:
            staff.email = data['email']
        if 'phone' in data:
            staff.phone = data['phone']
        if 'is_active' in data:
            staff.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Staff updated successfully',
            'staff': staff.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
@app.route('/api/staff/<staff_id>/delete', methods=['DELETE'])
def delete_staff(staff_id):
    """Delete staff member"""
    try:
        staff = Staff.query.filter_by(staff_id=staff_id).first()
        
        if not staff:
            return jsonify({
                'success': False,
                'message': 'Staff not found'
            }), 404
        
        # Check if staff has any allocations
        allocations = StaffRoomAllocation.query.filter_by(staff_id=staff_id).count()
        
        if allocations > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete. Staff has {allocations} room allocation(s). Remove allocations first.'
            }), 400
        
        db.session.delete(staff)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Staff deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500



@app.route('/api/staff-allocations/session/<session_id>', methods=['GET'])
def get_staff_allocations_by_session(session_id):
    """Get all staff room allocations for a session"""
    try:
        allocations = StaffRoomAllocation.query.filter_by(session_id=session_id).all()
        
        # Enrich with staff details
        result = []
        for allocation in allocations:
            staff = Staff.query.filter_by(staff_id=allocation.staff_id).first()
            alloc_dict = allocation.to_dict()
            if staff:
                alloc_dict['staff_name'] = staff.staff_name
                alloc_dict['department'] = staff.department
            result.append(alloc_dict)
        
        return jsonify({
            'success': True,
            'allocations': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/staff/<staff_id>/allocations', methods=['GET'])
def get_allocations_by_staff_id(staff_id):
    """Get all room allocations for a staff member with branch-wise student counts"""
    try:
        print(f"🔍 Fetching allocations for staff: {staff_id}")
        
        # Verify staff exists
        staff = Staff.query.filter_by(staff_id=staff_id).first()
        
        if not staff:
            return jsonify({
                'success': False,
                'message': 'Staff not found'
            }), 404
        
        # Get all room allocations for this staff
        allocations = StaffRoomAllocation.query.filter_by(staff_id=staff_id).all()
        
        print(f"📋 Found {len(allocations)} room allocations for {staff_id}")
        
        result = []
        for alloc in allocations:
            # Get all students in this room
            students = DetailedAllocation.query.filter_by(
                session_id=alloc.session_id,
                room_code=alloc.room_code
            ).all()
            
            # Count students by branch
            branch_counts = {}
            for student in students:
                branch = student.branch or 'Unknown'
                branch_counts[branch] = branch_counts.get(branch, 0) + 1
            
            # Get session info
            session = AllocationSession.query.filter_by(
                session_id=alloc.session_id
            ).first()
            
            allocation_data = {
                'allocation_id': alloc.id,
                'session_id': alloc.session_id,
                'room_code': alloc.room_code,
                'room_name': alloc.room_name,
                'role': alloc.role,
                'total_students': len(students),
                'branch_distribution': branch_counts,
                'allocated_at': alloc.allocated_at.strftime('%Y-%m-%d %H:%M:%S') if alloc.allocated_at else None,
                'exam_date': session.exam_date.strftime('%Y-%m-%d') if session and session.exam_date else None,
                'exam_time': session.exam_time.strftime('%H:%M') if session and session.exam_time else None,
                'subject_codes': session.subject_codes if session else None
            }
            
            result.append(allocation_data)
            print(f"  ✅ {alloc.room_name}: {len(students)} students, {len(branch_counts)} branches")
        
        return jsonify({
            'success': True,
            'staff': staff.to_dict(),
            'allocations': result,
            'total_rooms': len(result)
        })
        
    except Exception as e:
        print(f"❌ Error fetching staff allocations: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/staff-allocations/allocate', methods=['POST'])
def allocate_staff_to_room():
    """Allocate staff to examination room"""
    try:
        data = request.get_json()
        
        required = ['session_id', 'staff_id', 'room_code', 'room_name']
        for field in required:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Missing field: {field}'
                }), 400
        
        # Check if staff exists
        staff = Staff.query.filter_by(staff_id=data['staff_id']).first()
        if not staff:
            return jsonify({
                'success': False,
                'message': 'Staff not found'
            }), 404
        
        # Check if already allocated
        existing = StaffRoomAllocation.query.filter_by(
            session_id=data['session_id'],
            staff_id=data['staff_id'],
            room_code=data['room_code']
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'Staff already allocated to this room'
            }), 400
        
        # Create allocation
        allocation = StaffRoomAllocation(
            session_id=data['session_id'],
            staff_id=data['staff_id'],
            room_code=data['room_code'],
            room_name=data['room_name'],
            role=data.get('role', 'Invigilator')
        )
        
        db.session.add(allocation)
        db.session.commit()
        
        print(f"✅ Staff {staff.staff_name} allocated to room {data['room_code']}")
        
        return jsonify({
            'success': True,
            'message': 'Staff allocated successfully',
            'allocation': allocation.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Allocation error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/staff-allocations/<int:allocation_id>/remove', methods=['DELETE'])
def remove_staff_allocation(allocation_id):
    """Remove staff from room allocation"""
    try:
        allocation = StaffRoomAllocation.query.get(allocation_id)
        
        if not allocation:
            return jsonify({
                'success': False,
                'message': 'Allocation not found'
            }), 404
        
        db.session.delete(allocation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Staff allocation removed'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    
@app.route('/api/staff-auto-allocate', methods=['POST'])
def staff_auto_allocate():
    """
    Automatically allocate staff to rooms for the latest allocation session
    Assigns 2 staff members per room (1 Chief Invigilator + 1 Regular Invigilator)
    """
    try:
        print("🚀 Starting auto staff allocation...")
        
        # Get the most recent allocation session
        latest_session = AllocationSession.query.order_by(
            AllocationSession.created_at.desc()
        ).first()
        
        if not latest_session:
            return jsonify({
                'success': False,
                'message': 'No allocation session found. Please allocate students first.'
            }), 404
        
        session_id = latest_session.session_id
        print(f"📋 Using session: {session_id}")
        
        # Get all unique rooms from this session
        rooms = db.session.query(
            DetailedAllocation.room_code,
            DetailedAllocation.room_name
        ).filter_by(
            session_id=session_id
        ).distinct().all()
        
        if not rooms:
            return jsonify({
                'success': False,
                'message': 'No rooms found in this session'
            }), 404
        
        print(f"🏛️ Found {len(rooms)} rooms to allocate")
        
        # Get all active staff members
        active_staff = Staff.query.filter_by(is_active=True).all()
        
        if not active_staff:
            return jsonify({
                'success': False,
                'message': 'No active staff members available'
            }), 404
        
        if len(active_staff) < len(rooms) * 2:
            return jsonify({
                'success': False,
                'message': f'Insufficient staff: Need {len(rooms) * 2} staff (2 per room), but only {len(active_staff)} active staff available'
            }), 400
        
        # Delete existing allocations for this session
        StaffRoomAllocation.query.filter_by(session_id=session_id).delete()
        
        allocations_created = 0
        staff_index = 0
        
        # Allocate 2 staff per room
        for room in rooms:
            room_code = room.room_code
            room_name = room.room_name
            
            # Assign Chief Invigilator
            if staff_index < len(active_staff):
                chief_staff = active_staff[staff_index]
                chief_allocation = StaffRoomAllocation(
                    session_id=session_id,
                    staff_id=chief_staff.staff_id,
                    room_code=room_code,
                    room_name=room_name,
                    role='Chief Invigilator'
                )
                db.session.add(chief_allocation)
                allocations_created += 1
                staff_index += 1
                print(f"  ✅ {room_code}: Chief = {chief_staff.staff_name}")
            
            # Assign Regular Invigilator
            if staff_index < len(active_staff):
                regular_staff = active_staff[staff_index]
                regular_allocation = StaffRoomAllocation(
                    session_id=session_id,
                    staff_id=regular_staff.staff_id,
                    room_code=room_code,
                    room_name=room_name,
                    role='Invigilator'
                )
                db.session.add(regular_allocation)
                allocations_created += 1
                staff_index += 1
                print(f"  ✅ {room_code}: Regular = {regular_staff.staff_name}")
        
        # Commit all allocations
        db.session.commit()
        
        print(f"✅ Successfully created {allocations_created} staff allocations")
        
        return jsonify({
            'success': True,
            'message': f'Successfully allocated {allocations_created} staff members to {len(rooms)} rooms',
            'session_id': session_id,
            'total_rooms': len(rooms),
            'total_allocations': allocations_created
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Auto allocation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Auto-allocation failed: {str(e)}'
        }), 500


@app.route('/api/rooms/allocated/<session_id>', methods=['GET'])
def get_allocated_rooms(session_id):
    """Get all rooms that have student allocations for a session"""
    try:
        # Get unique rooms from detailed allocations
        rooms = db.session.query(
            DetailedAllocation.room_code,
            DetailedAllocation.room_name,
            func.count(DetailedAllocation.id).label('student_count')
        ).filter_by(
            session_id=session_id
        ).group_by(
            DetailedAllocation.room_code,
            DetailedAllocation.room_name
        ).all()
        
        result = []
        for room in rooms:
            result.append({
                'room_code': room.room_code,
                'room_name': room.room_name,
                'student_count': room.student_count
            })
        
        return jsonify({
            'success': True,
            'rooms': result,
            'total': len(result)
        })
        
    except Exception as e:
        print(f"❌ Error fetching allocated rooms: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/room-layout/<session_id>/<room_code>', methods=['GET'])
def get_room_layout(session_id, room_code):
    """
    Get room layout with exact seating arrangement 
    (Same view as allocation results page)
    """
    try:
        print(f"🗺️ Fetching room layout: Session={session_id}, Room={room_code}")
        
        # Get room info
        room = ExamRoom.query.filter_by(room_code=room_code).first()
        
        if not room:
            return jsonify({
                'success': False,
                'message': f'Room {room_code} not found'
            }), 404
        
        # Get all students in this room for this session
        students = DetailedAllocation.query.filter_by(
            session_id=session_id,
            room_code=room_code
        ).order_by(
            DetailedAllocation.row_num,
            DetailedAllocation.col_num
        ).all()
        
        if not students:
            return jsonify({
                'success': False,
                'message': 'No students allocated to this room'
            }), 404
        
        print(f"📊 Found {len(students)} students in {room_code}")
        
        # Format student data for layout
        students_data = []
        for student in students:
            students_data.append({
                'usn': student.student_usn,
                'name': student.student_name,
                'branch': student.branch,
                'subject_code': student.subject_code,
                'subject_name': student.subject_name,
                'seat_number': student.seat_number,
                'row_num': student.row_num,
                'col_num': student.col_num,
                'desk_id': student.desk_id,
                'desk_position': student.desk_position
            })
        
        return jsonify({
            'success': True,
            'room_info': {
                'room_code': room.room_code,
                'room_name': room.room_name,
                'rows': room.rows,
                'cols': room.cols,
                'capacity': room.capacity
            },
            'students': students_data,
            'total_students': len(students_data)
        })
        
    except Exception as e:
        print(f"❌ Error fetching room layout: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/send-staff-emails/<session_id>', methods=['POST'])
def send_staff_allocation_emails(session_id):
    """Send allocation emails to all staff for a session"""
    try:
        print(f"📧 Sending staff allocation emails for session: {session_id}")
        
        # Get all staff allocations for this session
        allocations = StaffRoomAllocation.query.filter_by(session_id=session_id).all()
        
        if not allocations:
            return jsonify({
                'success': False,
                'message': 'No staff allocations found for this session'
            }), 404
        
        print(f"📋 Found {len(allocations)} staff allocations")
        
        # Send emails in background
        success_count = 0
        failed_count = 0
        failed_staff = []
        
        for allocation in allocations:
            staff = Staff.query.filter_by(staff_id=allocation.staff_id).first()
            
            if not staff or not staff.email:
                failed_count += 1
                failed_staff.append({
                    'staff_id': allocation.staff_id,
                    'error': 'No email address'
                })
                print(f"❌ No email for {allocation.staff_id}")
                continue
            
            # Send email
            success, error = email_service.send_staff_allocation_email(
                allocation.staff_id,
                session_id
            )
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                failed_staff.append({
                    'staff_id': allocation.staff_id,
                    'staff_name': staff.staff_name,
                    'error': error
                })
                print(f"❌ Failed to send email to {staff.staff_name}: {error}")
        
        print(f"✅ Email Summary: {success_count} sent, {failed_count} failed")
        
        return jsonify({
            'success': True,
            'message': f'Sent {success_count} emails, {failed_count} failed',
            'total_staff': len(allocations),
            'success_count': success_count,
            'failed_count': failed_count,
            'failed_staff': failed_staff
        })
        
    except Exception as e:
        print(f"❌ Error sending staff emails: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/student/seating-plan/<session_id>/<usn>')
def student_seating_plan(session_id, usn):
    """
    Display seating plan for a specific student - RESTRICTED ACCESS
    Students can ONLY view this page, nothing else
    """
    try:
        print(f"📱 Student seating plan request: Session={session_id}, USN={usn}")
        
        # ✅ SECURITY: Validate session_id and USN format
        if not session_id or not usn:
            return render_template('student_error.html', 
                message="Invalid access link"), 403
        
        # Get student's allocation
        allocation = DetailedAllocation.query.filter_by(
            session_id=session_id,
            student_usn=usn.upper()
        ).first()
        
        if not allocation:
            return render_template('student_error.html', 
                message=f"No seat allocation found for {usn}"), 404
        
        # Get session details
        session = AllocationSession.query.filter_by(session_id=session_id).first()
        
        # Get student details
        student = Student.query.filter_by(usn=usn.upper()).first()
        
        if not student:
            return render_template('student_error.html', 
                message="Student record not found"), 404
        
        # Get all students in the same room ONLY
        room_students = DetailedAllocation.query.filter_by(
            session_id=session_id,
            room_code=allocation.room_code
        ).order_by(
            DetailedAllocation.row_num,
            DetailedAllocation.col_num
        ).all()
        
        # Get room info
        room = ExamRoom.query.filter_by(room_code=allocation.room_code).first()
        
        if not room:
            return render_template('student_error.html', 
                message=f"Room information not available"), 404
        
        # Calculate branch distribution
        branch_counts = {}
        for s in room_students:
            branch = s.branch or 'Unknown'
            branch_counts[branch] = branch_counts.get(branch, 0) + 1
        
        # ✅ RENDER STANDALONE TEMPLATE (No navigation, no links to other pages)
        return render_template(
            'student_seating_standalone.html',
            student=student,
            allocation=allocation,
            session=session,
            room=room,
            room_students=room_students,
            branch_counts=branch_counts
        )
        
    except Exception as e:
        print(f"❌ Error loading seating plan: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('student_error.html', 
            message="Unable to load seating plan. Please contact examination cell."), 500

@app.route('/debug/sessions')
@app.route('/debug/sessions')
def debug_sessions():
    """Debug route to check sessions"""
    try:
        sessions = AllocationSession.query.order_by(AllocationSession.created_at.desc()).limit(10).all()
        allocations = DetailedAllocation.query.limit(20).all()
        
        debug_info = {
            'total_sessions': AllocationSession.query.count(),
            'total_allocations': DetailedAllocation.query.count(),
            'recent_sessions': [
                {
                    'session_id': s.session_id,
                    'algorithm': s.algorithm_used,
                    'students': s.total_students,
                    'created': str(s.created_at)
                } for s in sessions
            ],
            'sample_allocations': [
                {
                    'session_id': a.session_id,
                    'student_usn': a.student_usn,
                    'desk_id': a.desk_id,
                    'room_code': a.room_code
                } for a in allocations
            ]
        }
        
        return f"<pre>{json.dumps(debug_info, indent=2)}</pre>"
        
    except Exception as e:
        return f"Debug error: {str(e)}"


# API Routes
@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Enhanced chat API with better error handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400
            
        message = data.get('message', '').strip()
        is_voice = data.get('is_voice', False)
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        print(f"🌐 API Processing: {message} (Voice: {is_voice})")
        
        response = chatbot.process_message(session_id, message, is_voice)
        
        voice_message = response.get('message', '').replace('*', '').replace('#', '')
        
        result = {
            'message': response['message'],
            'voice_message': voice_message,
            'completed': response.get('completed', False),
            'error': response.get('error', False),
            'next_step': response.get('next_step', 'start')
        }
        
        print(f"🌐 API Response: Error={result.get('error', False)}, Step={result.get('next_step')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    """Reset chat session"""
    try:
        if 'session_id' in session:
            chat_session = ChatSession.query.filter_by(session_id=session['session_id']).first()
            if chat_session:
                db.session.delete(chat_session)
                db.session.commit()
        
        session.pop('session_id', None)
        return jsonify({'message': 'Chat reset successfully'})
    except Exception as e:
        print(f"Reset error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")
            
        print("🚀 Starting COMPLETE VTU Exam Registration & AI Seat Allocation System...")
        app.run(debug=True, port=5000, host='127.0.0.1')
    except Exception as e:
        print(f"❌ App startup error: {str(e)}")
        traceback.print_exc()
