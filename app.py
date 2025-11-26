



# COMPLETE VTU Exam Registration System with AI Seat Allocation
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, distinct, text, and_, or_
import uuid
import json
import re
from datetime import datetime, date
import traceback
import random
import numpy as np
from typing import List, Dict, Tuple, Optional

app = Flask(__name__)
app.secret_key = 'vtu_chatbot_secret_key_2024'

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

# AI-Based Seat Allocation Engine


# Enhanced VTU Chatbot (keeping the working parts)
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

# Initialize services
chatbot = VTUChatbot()


# Routes
@app.route('/')
def index():
    return render_template('chatbot_with_voice.html')

@app.route('/chatbot')
def chatbot_route():
    return render_template('chatbot_with_voice.html')

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

@app.route('/admin')
def admin():
    """Enhanced admin panel"""
    try:
        students = Student.query.order_by(Student.created_at.desc()).all()
        
        student_data = []
        for student in students:
            subjects = StudentSubject.query.filter_by(usn=student.usn).all()
            student_info = {
                'student': student,
                'subjects_count': len(subjects),
                'subjects': subjects
            }
            student_data.append(student_info)
        
        return render_template('admin.html', student_data=student_data)
    except Exception as e:
        print(f"Admin route error: {e}")
        return render_template('admin.html', student_data=[])

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





def _allocate_students_to_desks(self, students: list, desks: list) -> list:
        """
        STRICT ALLOCATION: Fill EVERY seat in EVERY desk in EVERY column/row before moving to next room.
        No empty seats allowed in current room until all students are exhausted or room is completely full.
        """
        allocations = []
        from collections import OrderedDict

        # Group desks by room in input order
        room_desks = OrderedDict()
        for desk in desks:
            room_desks.setdefault(desk['room_code'], []).append(desk)

        desk_assignments = {desk['desk_id']: [] for desk in desks}
        remaining_students = students[:]

        print(f"🎯 Starting allocation with {len(remaining_students)} students")

        # Process each room COMPLETELY before moving to next
        for room_code, desks_in_this_room in room_desks.items():
            if not remaining_students:
                print("✅ All students allocated!")
                break
            
            print(f"🏢 Processing room: {room_code}")
            
            # Create ordered list of every individual seat in this room
            desk_map = {(desk['col'], desk['row']): desk for desk in desks_in_this_room}
            all_cols = sorted(set(desk['col'] for desk in desks_in_this_room))
            all_rows = sorted(set(desk['row'] for desk in desks_in_this_room))
            
            # Build complete seat sequence: column by column, row by row, seat by seat
            all_seats = []
            for col in all_cols:
                for row in all_rows:
                    desk = desk_map.get((col, row))
                    if desk:
                        capacity = desk.get('capacity', 2)
                        for seat_position in range(capacity):
                            all_seats.append({
                                'desk': desk,
                                'seat_position': seat_position,
                                'col': col,
                                'row': row
                            })
            
            print(f"📍 Room {room_code} has {len(all_seats)} total seats to fill")
            
            # Fill EVERY seat in this room in exact order
            for seat_info in all_seats:
                if not remaining_students:
                    print(f"⚠️ No more students left to fill remaining seats in room {room_code}")
                    break
                
                desk = seat_info['desk']
                desk_id = desk['desk_id']
                seat_position = seat_info['seat_position']
                col = seat_info['col']
                row = seat_info['row']
                
                # Check if this seat is already filled
                current_occupancy = len(desk_assignments[desk_id])
                if current_occupancy > seat_position:
                    print(f"⚠️ Seat {seat_position + 1} in desk {desk_id} already filled")
                    continue
                
                # Take next student and assign to this exact seat
                student = remaining_students.pop(0)
                
                if seat_position == 0:
                    # First seat in desk
                    self._assign_single_student_to_desk(student, desk, desk_assignments, allocations)
                    print(f"✅ Assigned {student['usn']} to desk {desk_id} at col={col}, row={row} (seat 1)")
                else:
                    # Second seat in desk (partner)
                    partner = desk_assignments[desk_id][0]
                    self._assign_single_student_to_desk(student, desk, desk_assignments, allocations, partner_usn=partner['usn'])
                    print(f"✅ Assigned {student['usn']} to desk {desk_id} at col={col}, row={row} (seat 2, partner: {partner['usn']})")
        
        # Handle any remaining students (emergency allocation)
        if remaining_students:
            print(f"🚨 Emergency allocation for {len(remaining_students)} remaining students")
            while remaining_students:
                student = remaining_students.pop(0)
                emergency_desk = self._get_or_create_emergency_desk(desks, desk_assignments)
                self._assign_single_student_to_desk(student, emergency_desk, desk_assignments, allocations)
                print(f"🚨 Emergency: {student['usn']} -> {emergency_desk['desk_id']}")

        print(f"🎯 FINAL RESULT: {len(allocations)} students allocated, {len(remaining_students)} unallocated")
        return allocations



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
        
        if not subjects:
            return jsonify({'success': False, 'message': 'No subjects selected'}), 400
        
        print(f"🤖 Processing {len(subjects)} subjects: {subjects}")
        print(f"🧠 Using algorithm: {algorithm}")
        
        # Use the AI allocator
        result = ai_seat_allocator.allocate_students_for_subjects(subjects, algorithm)
        
        # Add additional information for frontend
        if result['success']:
            result['exams_scheduled'] = len(subjects)
            result['efficiency'] = int(result.get('fitness_score', 0) * 20 + 80)  # Convert to percentage
            
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
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ AI processing error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'AI processing failed: {str(e)}'
        }), 500

@app.route('/allocation-results/<session_id>')
def view_allocation_results(session_id):
    """Display detailed desk-based allocation results"""
    try:
        print(f"📊 Loading allocation results for session: {session_id}")
        
        # Get allocation session
        
        allocation_session = AllocationSession.query.filter_by(session_id=session_id).first()
        
        if not allocation_session:
            print(f"❌ Session {session_id} not found in allocation_sessions table")
            # Let's also check if there's any data in detailed_allocations
            allocations = DetailedAllocation.query.filter_by(session_id=session_id).all()
            if allocations:
                print(f"✅ Found {len(allocations)} allocations without session record")
                # Create a dummy session object
                from datetime import datetime
                allocation_session = type('obj', (object,), {
                    'session_id': session_id,
                    'algorithm_used': 'AI Algorithm',
                    'total_students': len(allocations),
                    'total_desks': len(allocations) // 2,
                    'total_rooms': len(set(a.room_code for a in allocations)),
                    'fitness_score': 0.85,  # Default score
                    'created_at': datetime.now()
                })
            else:
                print(f"❌ No allocations found for session {session_id}")
                return render_template('allocation_results.html',
    
                                     session=None, 
                                     allocations=[], 
                                     desk_partnerships={})
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

        if allocation_session:
            session_dict = session_to_dict(allocation_session)
        else:
            session_dict = {}
        
        # Pass the sanitized session dictionary to the template (avoid duplicate keyword)
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