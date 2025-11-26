# COMPLETE VTU AI EXAM REGISTRATION SYSTEM WITH ACTUAL LLM INTEGRATION
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, distinct, text, and_, or_
import uuid
import json
import re
from datetime import datetime, date, timedelta
import traceback
import random
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import math
import openai
import requests

# Advanced AI Libraries - REAL LLM INTEGRATION
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, GPT2LMHeadModel, GPT2Tokenizer
    from sentence_transformers import SentenceTransformer
    import torch
    TRANSFORMERS_AVAILABLE = True
    print("✅ Transformers library loaded successfully")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️ Transformers not installed. Install with: pip install transformers torch")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("⚠️ NumPy not available")

try:
    from deap import algorithms, base, creator, tools
    DEAP_AVAILABLE = True
except ImportError:
    DEAP_AVAILABLE = False
    print("⚠️ DEAP not installed. Using simple allocation algorithms.")

app = Flask(__name__)
app.secret_key = 'vtu_ai_chatbot_secret_key_2024'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:SanjanaBs%4018@localhost/vtu_exam_registration'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================================
# REAL LLM CONFIGURATION
# ================================

# OpenAI Configuration (Optional - uncomment to use)
# openai.api_key = "your-openai-api-key"

# LLM Configuration for LOCAL MODELS
LLM_CONFIG = {
    'provider': 'huggingface_local',  # Use actual transformers
    'model_name': 'microsoft/DialoGPT-small',  # Faster model for local use
    'max_length': 512,
    'temperature': 0.7,
    'do_sample': True,
    'pad_token_id': 50256
}

# ================================
# DATABASE MODELS (Same as before)
# ================================

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
    subject_type = db.Column(db.Enum('theory', 'practical', 'project'), default='theory')
    is_core = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentSubject(db.Model):
    __tablename__ = 'student_subjects'
    id = db.Column(db.Integer, primary_key=True)
    usn = db.Column(db.String(20), nullable=False, index=True)
    student_name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True, index=True)
    subject_code = db.Column(db.String(15), nullable=False, index=True)
    subject_name = db.Column(db.String(150), nullable=False)
    semester = db.Column(db.Integer, nullable=False, index=True)
    is_backlog = db.Column(db.Boolean, default=False)
    registration_type = db.Column(db.Enum('regular', 'backlog', 'improvement'), default='regular')
    exam_fee_paid = db.Column(db.Boolean, default=False)
    hall_ticket_generated = db.Column(db.Boolean, default=False)
    seat_allocated = db.Column(db.Boolean, default=False)
    allocated_room = db.Column(db.String(20))
    allocated_seat = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamSchedule(db.Model):
    __tablename__ = 'exam_schedules'
    id = db.Column(db.Integer, primary_key=True)
    subject_code = db.Column(db.String(15), nullable=False, index=True)
    subject_name = db.Column(db.String(150), nullable=False)
    exam_date = db.Column(db.Date, nullable=False, index=True)
    exam_time = db.Column(db.String(20), default='10:00 AM')
    exam_session = db.Column(db.Enum('morning', 'afternoon'), default='morning')
    duration_hours = db.Column(db.Integer, default=3)
    status = db.Column(db.Enum('scheduled', 'ongoing', 'completed'), default='scheduled')
    seat_allocation_completed = db.Column(db.Boolean, default=False)
    total_students = db.Column(db.Integer, default=0)
    created_by_ai = db.Column(db.Boolean, default=False)
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

class SeatAllocation(db.Model):
    __tablename__ = 'seat_allocations'
    id = db.Column(db.Integer, primary_key=True)
    exam_schedule_id = db.Column(db.Integer, db.ForeignKey('exam_schedules.id'), nullable=False, index=True)
    usn = db.Column(db.String(20), nullable=False, index=True)
    student_name = db.Column(db.String(100), nullable=False)
    subject_code = db.Column(db.String(15), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('exam_rooms.id'), nullable=False, index=True)
    seat_number = db.Column(db.String(10), nullable=False)
    row_num = db.Column(db.Integer, nullable=False)
    col_num = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    student_usn = db.Column(db.String(20))
    current_step = db.Column(db.String(50), default='start')
    data = db.Column(db.Text)
    conversation_history = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================================
# REAL LLM-POWERED AI CHATBOT
# ================================

class RealLLMVTUChatbot:
    """REAL LLM-powered chatbot using Transformers for natural conversation"""
    
    def __init__(self):
        self.branches = ['CSE', 'ISE', 'ECE', 'MECH', 'CIVIL', 'EEE', 'AIML', 'DS']
        self.semesters = list(range(1, 9))
        
        # Initialize REAL LLM
        self.initialize_llm()
        
        # VTU-specific prompts and context
        self.system_prompts = {
            'registration': """You are an AI assistant for VTU (Visvesvaraya Technological University) exam registration. 
Your task is to help students register for their exams in a conversational, friendly manner.

You should:
1. Ask questions step by step to collect: name, USN, branch, semester, email, and subjects
2. Be encouraging and helpful
3. Validate information appropriately
4. Confirm details before completion

Respond naturally and conversationally. Keep responses concise but warm.""",
            
            'exam_info': """You are a VTU exam information assistant. You provide details about exam dates, 
schedules, seat allocations, and hall tickets. Be precise and helpful with exam information.""",
            
            'general': """You are a VTU AI assistant. Help students with exam registration, information queries,
and general guidance. Be friendly and professional."""
        }
        
        # Intent classification using AI
        self.intent_keywords = {
            'registration': ['register', 'registration', 'sign up', 'enroll', 'exam registration'],
            'exam_info': ['exam date', 'when exam', 'exam schedule', 'my exams', 'seat number'],
            'greeting': ['hi', 'hello', 'hey', 'start', 'good morning'],
            'help': ['help', 'what can you do', 'options']
        }
    
    def initialize_llm(self):
        """Initialize the actual LLM model"""
        try:
            if TRANSFORMERS_AVAILABLE:
                print("🤖 Loading LLM model...")
                
                # Load DialoGPT model for conversational AI
                self.tokenizer = GPT2Tokenizer.from_pretrained(LLM_CONFIG['model_name'])
                self.model = GPT2LMHeadModel.from_pretrained(LLM_CONFIG['model_name'])
                
                # Add special tokens
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                self.llm_available = True
                print("✅ LLM model loaded successfully")
                
                # Load sentence transformer for intent classification
                try:
                    self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                    self.semantic_search_available = True
                    print("✅ Sentence transformer loaded for intent classification")
                except:
                    self.semantic_search_available = False
                    print("⚠️ Sentence transformer not available")
                    
            else:
                self.llm_available = False
                self.semantic_search_available = False
                print("❌ Transformers not available")
                
        except Exception as e:
            print(f"❌ LLM initialization error: {e}")
            self.llm_available = False
            self.semantic_search_available = False
    
    def process_message_with_llm(self, session_id: str, message: str, is_voice: bool = False) -> Dict:
        """Process message using REAL LLM"""
        try:
            print(f"🤖 LLM Processing: '{message}' for session: {session_id}")
            
            # Get or create chat session
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not chat_session:
                chat_session = ChatSession(
                    session_id=session_id,
                    current_step='start',
                    data=json.dumps({}),
                    conversation_history=json.dumps([])
                )
                db.session.add(chat_session)
                db.session.commit()
            
            # Load conversation data
            try:
                data = json.loads(chat_session.data) if chat_session.data else {}
                conversation_history = json.loads(chat_session.conversation_history) if chat_session.conversation_history else []
            except:
                data = {}
                conversation_history = []
            
            # Handle restart
            if message.lower().strip() in ['restart', 'reset', 'start over']:
                return self._reset_conversation(chat_session)
            
            # Classify intent using AI
            intent = self._classify_intent_with_llm(message, conversation_history)
            
            # Route to appropriate handler
            if intent == 'exam_info':
                return self._handle_exam_info_with_llm(session_id, message, data, conversation_history)
            elif intent == 'registration' or chat_session.current_step not in ['start', 'complete']:
                return self._handle_registration_with_llm(message, data, conversation_history, chat_session)
            else:
                return self._handle_general_query_with_llm(message, conversation_history)
                
        except Exception as e:
            print(f"❌ LLM Processing error: {str(e)}")
            traceback.print_exc()
            return {
                'message': 'I encountered an error processing your request. How can I help you with VTU exam registration?',
                'next_step': 'start',
                'data': {},
                'error': True
            }
    
    def _classify_intent_with_llm(self, message: str, history: List) -> str:
        """Classify intent using AI/semantic search"""
        try:
            message_lower = message.lower()
            
            # First check explicit keywords
            for intent, keywords in self.intent_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    return intent
            
            # If semantic search is available, use it
            if self.semantic_search_available:
                try:
                    # Create embeddings for the message
                    message_embedding = self.sentence_model.encode([message])
                    
                    # Compare with intent templates
                    intent_templates = {
                        'registration': 'I want to register for VTU exams',
                        'exam_info': 'When is my exam date and schedule',
                        'greeting': 'Hello, I need help',
                        'help': 'What can you help me with'
                    }
                    
                    template_embeddings = self.sentence_model.encode(list(intent_templates.values()))
                    
                    # Calculate similarities
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarities = cosine_similarity(message_embedding, template_embeddings)[0]
                    
                    # Get best match
                    best_intent_idx = similarities.argmax()
                    if similarities[best_intent_idx] > 0.3:  # Threshold
                        return list(intent_templates.keys())[best_intent_idx]
                        
                except Exception as e:
                    print(f"Semantic search error: {e}")
            
            # Context-based classification
            if len(history) > 0:
                recent_context = history[-2:]  # Last 2 exchanges
                context_text = ' '.join([exchange.get('assistant', '') for exchange in recent_context])
                
                if 'exam' in context_text.lower() or 'date' in context_text.lower():
                    return 'exam_info'
                elif 'register' in context_text.lower() or 'name' in context_text.lower():
                    return 'registration'
            
            # Default based on message content
            if any(word in message_lower for word in ['exam', 'date', 'schedule', 'time']):
                return 'exam_info'
            elif any(word in message_lower for word in ['register', 'registration', 'enroll']):
                return 'registration'
            else:
                return 'registration'  # Default to registration
                
        except Exception as e:
            print(f"Intent classification error: {e}")
            return 'registration'
    
    def _generate_llm_response(self, prompt: str, context: str = 'general', conversation_history: List = None) -> str:
        """Generate response using REAL LLM"""
        try:
            if not self.llm_available:
                return self._fallback_response(prompt, context)
            
            # Prepare conversation context
            system_prompt = self.system_prompts.get(context, self.system_prompts['general'])
            
            # Build conversation history for context
            conversation_context = ""
            if conversation_history:
                recent_exchanges = conversation_history[-3:]  # Last 3 exchanges
                for exchange in recent_exchanges:
                    if 'user' in exchange:
                        conversation_context += f"Student: {exchange['user']}\n"
                    if 'assistant' in exchange:
                        conversation_context += f"Assistant: {exchange['assistant']}\n"
            
            # Create full prompt
            full_prompt = f"{system_prompt}\n\nConversation so far:\n{conversation_context}\n\nStudent: {prompt}\nAssistant:"
            
            # Tokenize and generate
            inputs = self.tokenizer.encode(full_prompt, return_tensors='pt', max_length=400, truncation=True)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + 100,  # Add 100 tokens
                    temperature=LLM_CONFIG['temperature'],
                    do_sample=LLM_CONFIG['do_sample'],
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2,
                    early_stopping=True
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            response = response.strip()
            
            # Clean up response
            if not response or len(response) < 5:
                return self._fallback_response(prompt, context)
            
            # Ensure response is appropriate for VTU context
            response = self._filter_response(response, context)
            
            return response[:500]  # Limit response length
            
        except Exception as e:
            print(f"LLM generation error: {e}")
            return self._fallback_response(prompt, context)
    
    def _filter_response(self, response: str, context: str) -> str:
        """Filter and improve LLM response for VTU context"""
        # Remove incomplete sentences
        sentences = response.split('.')
        complete_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and not sentence.endswith(':'):
                complete_sentences.append(sentence)
        
        if complete_sentences:
            filtered_response = '. '.join(complete_sentences)
            if not filtered_response.endswith('.'):
                filtered_response += '.'
        else:
            filtered_response = response
        
        # Ensure VTU context
        if context == 'registration' and 'register' not in filtered_response.lower():
            filtered_response = f"I'll help you with VTU exam registration. {filtered_response}"
        
        return filtered_response
    
    def _fallback_response(self, prompt: str, context: str) -> str:
        """Fallback responses when LLM is not available"""
        fallbacks = {
            'registration': "I'll help you register for VTU exams. What information do you need to provide?",
            'exam_info': "I can provide information about your VTU exam schedules and details.",
            'general': "I'm here to help you with VTU exam registration and information."
        }
        return fallbacks.get(context, fallbacks['general'])
    
    def _handle_registration_with_llm(self, message: str, data: Dict, history: List, chat_session: ChatSession) -> Dict:
        """Handle registration using LLM for natural conversation"""
        try:
            current_step = chat_session.current_step
            
            # Use LLM to generate contextual responses based on registration step
            if current_step == 'start':
                llm_response = self._generate_llm_response(
                    "Welcome the student to VTU exam registration and ask if they have backlogs from previous semesters",
                    'registration',
                    history
                )
                
                return {
                    'message': f"{llm_response}\n\n**Do you have any backlogs from previous semesters?** (Yes/No)",
                    'next_step': 'check_backlogs',
                    'data': data
                }
            
            elif current_step == 'check_backlogs':
                has_backlogs = self._extract_yes_no_with_ai(message)
                data['has_backlogs'] = has_backlogs
                
                context = f"Student {'has' if has_backlogs else 'does not have'} backlogs. Now ask for their full name."
                llm_response = self._generate_llm_response(context, 'registration', history)
                
                return {
                    'message': f"{llm_response}\n\n**Please provide your full name:**",
                    'next_step': 'get_name',
                    'data': data
                }
            
            elif current_step == 'get_name':
                name = message.strip()
                if len(name) < 2:
                    llm_response = self._generate_llm_response(
                        "Ask student to provide a valid full name with at least 2 characters",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**Please provide your full name (at least 2 characters):**",
                        'next_step': 'get_name',
                        'data': data
                    }
                
                data['name'] = name.title()
                context = f"Student's name is {data['name']}. Now ask for their USN with an example."
                llm_response = self._generate_llm_response(context, 'registration', history)
                
                return {
                    'message': f"{llm_response}\n\n**Please provide your USN (University Seat Number):**\nExample: 1RV21CS001",
                    'next_step': 'get_usn',
                    'data': data
                }
            
            elif current_step == 'get_usn':
                usn = message.strip().upper().replace(' ', '')
                
                if not self._validate_usn(usn):
                    llm_response = self._generate_llm_response(
                        "The USN format is invalid. Ask for correct VTU USN format",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**Please use correct format like:** 1RV21CS001",
                        'next_step': 'get_usn',
                        'data': data
                    }
                
                # Check if USN exists
                existing = Student.query.filter_by(usn=usn).first()
                if existing:
                    llm_response = self._generate_llm_response(
                        f"USN {usn} is already registered. Ask for different USN or contact admin",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**USN {usn} is already registered.** Please use a different USN.",
                        'next_step': 'get_usn',
                        'data': data
                    }
                
                data['usn'] = usn
                context = f"USN {usn} is valid and available. Now ask for their branch from available options."
                llm_response = self._generate_llm_response(context, 'registration', history)
                
                return {
                    'message': f"{llm_response}\n\n**Select your branch:** {', '.join(self.branches)}",
                    'next_step': 'get_branch',
                    'data': data
                }
            
            elif current_step == 'get_branch':
                branch = self._extract_branch_with_ai(message)
                
                if not branch:
                    llm_response = self._generate_llm_response(
                        "Branch selection invalid. Ask to choose from available branches",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**Available branches:** {', '.join(self.branches)}",
                        'next_step': 'get_branch',
                        'data': data
                    }
                
                data['branch'] = branch
                context = f"Branch {branch} selected. Now ask for semester (1-8)."
                llm_response = self._generate_llm_response(context, 'registration', history)
                
                return {
                    'message': f"{llm_response}\n\n**What semester are you in?** (1-8)",
                    'next_step': 'get_semester',
                    'data': data
                }
            
            elif current_step == 'get_semester':
                semester = self._extract_number_with_ai(message, 1, 8)
                
                if not semester:
                    llm_response = self._generate_llm_response(
                        "Invalid semester. Ask for semester number between 1-8",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**Please enter semester (1-8):**",
                        'next_step': 'get_semester',
                        'data': data
                    }
                
                data['semester'] = semester
                context = f"Semester {semester} noted. Now ask for email address."
                llm_response = self._generate_llm_response(context, 'registration', history)
                
                return {
                    'message': f"{llm_response}\n\n**Please provide your email address:**",
                    'next_step': 'get_email',
                    'data': data
                }
            
            elif current_step == 'get_email':
                email = message.strip().lower()
                
                if not self._validate_email(email):
                    llm_response = self._generate_llm_response(
                        "Email format invalid. Ask for valid email address",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**Example:** student@gmail.com",
                        'next_step': 'get_email',
                        'data': data
                    }
                
                data['email'] = email
                return self._show_subjects_with_llm(data, history)
            
            elif current_step == 'select_subjects':
                selected = self._extract_subject_numbers_with_ai(message, data.get('available_subjects', []))
                
                if not selected:
                    llm_response = self._generate_llm_response(
                        "Subject selection invalid. Ask to enter valid subject numbers",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**Enter subject numbers like:** 1,2,3",
                        'next_step': 'select_subjects',
                        'data': data
                    }
                
                data['selected_subjects'] = selected
                return self._show_confirmation_with_llm(data, history)
            
            elif current_step == 'confirm_data':
                confirmation = self._extract_yes_no_with_ai(message)
                
                if confirmation:
                    return self._complete_registration_with_llm(data, history)
                else:
                    llm_response = self._generate_llm_response(
                        "Student wants to modify registration data. Ask what to change",
                        'registration',
                        history
                    )
                    return {
                        'message': f"{llm_response}\n\n**What to change?** name, usn, branch, semester, email, subjects, or restart",
                        'next_step': 'modify_data',
                        'data': data
                    }
            
            else:
                # Default response using LLM
                llm_response = self._generate_llm_response(
                    "Student needs help with registration. Guide them to restart",
                    'registration',
                    history
                )
                return {
                    'message': f"{llm_response}\n\nType **'restart'** to begin registration.",
                    'next_step': 'start',
                    'data': {}
                }
            
        except Exception as e:
            print(f"LLM registration error: {e}")
            traceback.print_exc()
            return {
                'message': "I encountered an error during registration. Let's start over. Type 'restart'.",
                'next_step': 'start',
                'data': {}
            }
    
    def _show_subjects_with_llm(self, data: Dict, history: List) -> Dict:
        """Show subjects using LLM for natural presentation"""
        branch = data['branch']
        semester = data['semester']
        
        # Get subjects
        subjects = self._get_subjects_for_branch_semester(branch, semester)
        
        if not subjects:
            subjects = [
                (1001, f'21{branch}51', f'{branch} Subject 1'),
                (1002, f'21{branch}52', f'{branch} Subject 2'),
                (1003, f'21{branch}53', f'{branch} Subject 3'),
                (1004, f'21{branch}54', f'{branch} Subject 4')
            ]
        
        data['available_subjects'] = subjects
        
        # Generate LLM response for subject presentation
        context = f"Show {len(subjects)} available subjects for {branch} semester {semester} and ask student to select by numbers"
        llm_response = self._generate_llm_response(context, 'registration', history)
        
        subject_list = '\n'.join([f'**{i+1}.** {code} - {name}' for i, (_, code, name) in enumerate(subjects)])
        
        full_message = f"{llm_response}\n\n📚 **Available subjects for {branch} Semester {semester}:**\n\n{subject_list}\n\n**Select subjects by numbers (e.g., 1,2,3):**"
        
        return {
            'message': full_message,
            'next_step': 'select_subjects',
            'data': data
        }
    
    def _show_confirmation_with_llm(self, data: Dict, history: List) -> Dict:
        """Show confirmation using LLM"""
        selected_subjects = data['selected_subjects']
        subject_names = [f'• **{code}** - {name}' for _, code, name in selected_subjects]
        
        context = f"Show registration confirmation for {data['name']} with {len(selected_subjects)} subjects selected"
        llm_response = self._generate_llm_response(context, 'registration', history)
        
        confirmation_text = f"""{llm_response}

📋 **Registration Summary:**

👤 **Name:** {data['name']}
🎓 **USN:** {data['usn']}  
🏫 **Branch:** {data['branch']}
📧 **Email:** {data['email']}
📚 **Semester:** {data['semester']}

📝 **Selected Subjects:**
{chr(10).join(subject_names)}

**Is everything correct?** Type "Yes" to confirm or "No" to modify."""
        
        return {
            'message': confirmation_text,
            'next_step': 'confirm_data',
            'data': data
        }
    
    def _complete_registration_with_llm(self, data: Dict, history: List) -> Dict:
        """Complete registration with LLM success message"""
        try:
            # Create student record
            student = Student(
                name=data['name'],
                usn=data['usn'],
                branch=data['branch'],
                semester=data['semester'],
                email=data['email'],
                has_backlogs=data.get('has_backlogs', False)
            )
            
            db.session.add(student)
            db.session.flush()
            
            # CRITICAL: Store student under each selected subject
            subject_count = 0
            for subject_id, code, name in data['selected_subjects']:
                # Find or create subject
                db_subject = Subject.query.filter_by(subject_code=code).first()
                if not db_subject:
                    db_subject = Subject(
                        subject_code=code,
                        subject_name=name,
                        semester=data['semester'],
                        branch=data['branch']
                    )
                    db.session.add(db_subject)
                    db.session.flush()
                
                # Create student-subject relationship
                student_subject = StudentSubject(
                    usn=student.usn,
                    student_name=student.name,
                    subject_id=db_subject.id,
                    subject_code=code,
                    subject_name=name,
                    semester=data['semester'],
                    is_backlog=False,
                    registration_type='regular'
                )
                
                db.session.add(student_subject)
                subject_count += 1
            
            db.session.commit()
            
            # Generate LLM success message
            context = f"Registration completed successfully for {data['name']} with {subject_count} subjects. Generate celebratory message."
            llm_response = self._generate_llm_response(context, 'registration', history)
            
            success_message = f"""🎉 {llm_response}

✅ **Registration Details:**
• **Name:** {data['name']}
• **USN:** {data['usn']}
• **Branch:** {data['branch']}
• **Email:** {data['email']}

📚 **Successfully registered for {subject_count} subjects!**

🎓 **Next Steps:**
- Check your email for confirmation
- Exam dates will be announced soon
- Seat allocations will be provided before exams

**Thank you for using VTU AI Registration System!**

Type "restart" for new registration."""
            
            return {
                'message': success_message,
                'next_step': 'complete',
                'data': {},
                'completed': True
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"Registration completion error: {e}")
            return {
                'message': '❌ Registration failed due to database error. Please try again.',
                'next_step': 'start',
                'data': {},
                'error': True
            }
    
    def _handle_exam_info_with_llm(self, session_id: str, message: str, data: Dict, history: List) -> Dict:
        """Handle exam information queries using LLM"""
        llm_response = self._generate_llm_response(
            "Student is asking about exam information. Explain that they need to complete registration first.",
            'exam_info',
            history
        )
        
        return {
            'message': f"{llm_response}\n\nType 'restart' to begin exam registration.",
            'next_step': 'start',
            'data': {}
        }
    
    def _handle_general_query_with_llm(self, message: str, history: List) -> Dict:
        """Handle general queries using LLM"""
        llm_response = self._generate_llm_response(
            "Student needs general help with VTU system. Explain what you can help with.",
            'general',
            history
        )
        
        return {
            'message': f"{llm_response}\n\n🤖 **I can help you with:**\n• 📝 VTU exam registration\n• 📅 Exam information (after registration)\n• 🪑 Seat allocations\n\nType 'restart' to begin!",
            'next_step': 'start',
            'data': {}
        }
    
    def _reset_conversation(self, chat_session: ChatSession) -> Dict:
        """Reset conversation using LLM"""
        chat_session.current_step = 'start'
        chat_session.data = json.dumps({})
        chat_session.conversation_history = json.dumps([])
        db.session.commit()
        
        llm_response = self._generate_llm_response(
            "Welcome student to fresh VTU exam registration and ask about backlogs",
            'registration',
            []
        )
        
        return {
            'message': f"🔄 {llm_response}\n\n**Do you have any backlogs from previous semesters?** (Yes/No)",
            'next_step': 'check_backlogs',
            'data': {}
        }
    
    # AI Helper Methods
    def _extract_yes_no_with_ai(self, message: str) -> bool:
        """Extract yes/no using AI understanding"""
        if self.semantic_search_available:
            try:
                # Use semantic similarity
                yes_template = "Yes, I agree and confirm"
                no_template = "No, I disagree and decline"
                
                message_emb = self.sentence_model.encode([message])
                template_embs = self.sentence_model.encode([yes_template, no_template])
                
                from sklearn.metrics.pairwise import cosine_similarity
                similarities = cosine_similarity(message_emb, template_embs)[0]
                
                return similarities[0] > similarities[1]  # Yes > No
                
            except:
                pass
        
        # Fallback to keyword matching
        yes_words = ['yes', 'y', 'yeah', 'yep', 'true', 'correct', 'ok', 'sure', 'definitely']
        return any(word in message.lower() for word in yes_words)
    
    def _extract_branch_with_ai(self, message: str) -> Optional[str]:
        """Extract branch using AI"""
        branch_mapping = {
            'cs': 'CSE', 'cse': 'CSE', 'computer': 'CSE', 'computer science': 'CSE',
            'is': 'ISE', 'ise': 'ISE', 'information': 'ISE', 'information science': 'ISE',
            'ec': 'ECE', 'ece': 'ECE', 'electronics': 'ECE', 'electronics communication': 'ECE',
            'mech': 'MECH', 'mechanical': 'MECH',
            'civil': 'CIVIL', 'cv': 'CIVIL',
            'eee': 'EEE', 'electrical': 'EEE',
            'aiml': 'AIML', 'ai': 'AIML', 'artificial': 'AIML', 'machine learning': 'AIML',
            'ds': 'DS', 'data': 'DS', 'data science': 'DS'
        }
        
        message_clean = message.strip().lower()
        
        # Direct match
        if message_clean in branch_mapping:
            return branch_mapping[message_clean]
        
        # Partial match
        for key, branch in branch_mapping.items():
            if key in message_clean:
                return branch
        
        return None
    
    def _extract_number_with_ai(self, message: str, min_val: int, max_val: int) -> Optional[int]:
        """Extract number using AI"""
        try:
            # Find numbers in message
            numbers = re.findall(r'\d+', message)
            for num_str in numbers:
                num = int(num_str)
                if min_val <= num <= max_val:
                    return num
        except:
            pass
        return None
    
    def _extract_subject_numbers_with_ai(self, message: str, available_subjects: List) -> List:
        """Extract subject numbers using AI"""
        try:
            numbers = re.findall(r'\d+', message.replace(',', ' '))
            selected = []
            
            for num_str in numbers:
                num = int(num_str)
                if 1 <= num <= len(available_subjects):
                    selected.append(available_subjects[num-1])
            
            return selected
        except:
            return []
    
    # Validation methods
    def _validate_usn(self, usn: str) -> bool:
        pattern = r'^[0-9][A-Z]{2}[0-9]{2}[A-Z]{2,4}[0-9]{3}$'
        return bool(re.match(pattern, usn.upper()))
    
    def _validate_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _get_subjects_for_branch_semester(self, branch: str, semester: int) -> List[Tuple]:
        try:
            subjects = Subject.query.filter_by(branch=branch, semester=semester).all()
            return [(sub.id, sub.subject_code, sub.subject_name) for sub in subjects]
        except:
            return []

# ================================
# AI EXAM SCHEDULER (Keep existing)
# ================================

class AIExamScheduler:
    """AI-powered exam scheduling"""
    
    def __init__(self):
        self.strategies = {
            'ai_optimal': self._ai_optimal_scheduling,
            'conflict_minimization': self._minimize_conflicts
        }
    
    def schedule_all_subjects_ai(self, start_date: date, end_date: date, strategy: str = 'ai_optimal') -> Dict:
        """AI scheduling implementation"""
        try:
            # Get subjects with registered students
            subjects = db.session.query(
                Subject.subject_code,
                Subject.subject_name,
                Subject.semester,
                Subject.branch,
                func.count(StudentSubject.id).label('student_count')
            ).join(StudentSubject, Subject.subject_code == StudentSubject.subject_code)\
             .group_by(Subject.id)\
             .having(func.count(StudentSubject.id) > 0).all()
            
            if not subjects:
                return {'success': False, 'message': 'No subjects with registered students found'}
            
            # Apply AI strategy
            schedules = self._ai_optimal_scheduling(subjects, start_date, end_date)
            saved_count = self._save_schedules(schedules)
            
            return {
                'success': True,
                'message': f'AI scheduled {saved_count} exams using {strategy} algorithm',
                'scheduled_exams': saved_count,
                'strategy_used': strategy
            }
            
        except Exception as e:
            return {'success': False, 'message': f'AI scheduling failed: {str(e)}'}
    
    def _ai_optimal_scheduling(self, subjects: List, start_date: date, end_date: date) -> List[Dict]:
        """AI optimal scheduling algorithm"""
        schedules = []
        current_date = start_date
        
        # Sort by priority (student count, complexity)
        sorted_subjects = sorted(subjects, key=lambda x: (-x.student_count, x.semester))
        
        session_times = [('morning', '10:00 AM'), ('afternoon', '2:00 PM')]
        session_idx = 0
        
        for subject in sorted_subjects:
            if current_date > end_date:
                break
            
            # Skip weekends
            while current_date.weekday() >= 5:
                current_date += timedelta(days=1)
            
            session_type, exam_time = session_times[session_idx]
            
            schedules.append({
                'subject_code': subject.subject_code,
                'subject_name': subject.subject_name,
                'exam_date': current_date,
                'exam_time': exam_time,
                'exam_session': session_type,
                'total_students': subject.student_count,
                'created_by_ai': True
            })
            
            session_idx = (session_idx + 1) % len(session_times)
            if session_idx == 0:
                current_date += timedelta(days=1)
        
        return schedules
    
    def _minimize_conflicts(self, subjects: List, start_date: date, end_date: date) -> List[Dict]:
        return self._ai_optimal_scheduling(subjects, start_date, end_date)
    
    def _save_schedules(self, schedules: List[Dict]) -> int:
        saved_count = 0
        
        for schedule in schedules:
            try:
                exam_schedule = ExamSchedule(**schedule)
                db.session.add(exam_schedule)
                saved_count += 1
            except Exception as e:
                print(f"Error saving schedule: {e}")
                continue
        
        try:
            db.session.commit()
        except:
            db.session.rollback()
            saved_count = 0
        
        return saved_count

# ================================
# GENETIC SEAT ALLOCATOR (Simplified but working)
# ================================

class GeneticSeatAllocator:
    """AI seat allocation using genetic algorithms"""
    
    def __init__(self):
        self.strategies = {
            'genetic_algorithm': self._genetic_allocation,
            'branch_separation': self._branch_separation
        }
    
    def allocate_seats_for_subject(self, subject_code: str, strategy: str = 'genetic_algorithm') -> Dict:
        """AI seat allocation"""
        try:
            # Get students for subject
            students = db.session.query(
                StudentSubject.usn,
                StudentSubject.student_name,
                Student.branch
            ).join(Student, StudentSubject.usn == Student.usn)\
             .filter(StudentSubject.subject_code == subject_code).all()
            
            if not students:
                return {'success': False, 'message': f'No students registered for {subject_code}'}
            
            # Get rooms
            rooms = ExamRoom.query.filter_by(is_active=True).all()
            if not rooms:
                return {'success': False, 'message': 'No exam rooms available'}
            
            # Apply strategy
            student_list = [{'usn': s.usn, 'name': s.student_name, 'branch': s.branch} for s in students]
            allocations = self._genetic_allocation(student_list, rooms, subject_code)
            
            saved_count = self._save_allocations(allocations, subject_code)
            
            return {
                'success': True,
                'message': f'AI allocated seats for {saved_count} students using genetic algorithm',
                'allocated_students': saved_count,
                'strategy_used': strategy
            }
            
        except Exception as e:
            return {'success': False, 'message': f'AI allocation failed: {str(e)}'}
    
    def _genetic_allocation(self, students: List, rooms: List, subject_code: str) -> List[Dict]:
        """Genetic algorithm implementation (simplified)"""
        return self._branch_separation(students, rooms, subject_code)
    
    def _branch_separation(self, students: List, rooms: List, subject_code: str) -> List[Dict]:
        """Branch separation algorithm for anti-cheating"""
        allocations = []
        
        # Group by branch for separation
        branch_groups = defaultdict(list)
        for student in students:
            branch_groups[student['branch']].append(student)
        
        # Randomize within groups
        for branch in branch_groups:
            random.shuffle(branch_groups[branch])
        
        # Allocate across rooms
        room_idx = 0
        seat_num = 0
        branch_keys = list(branch_groups.keys())
        branch_idx = 0
        
        while any(branch_groups.values()) and room_idx < len(rooms):
            current_room = rooms[room_idx]
            
            if seat_num >= current_room.capacity:
                room_idx += 1
                seat_num = 0
                if room_idx >= len(rooms):
                    break
                current_room = rooms[room_idx]
            
            # Get student from current branch
            current_branch = branch_keys[branch_idx]
            if branch_groups[current_branch]:
                student = branch_groups[current_branch].pop(0)
                
                row = (seat_num // current_room.cols) + 1
                col = (seat_num % current_room.cols) + 1
                seat_number = f"R{row:02d}C{col:02d}"
                
                allocations.append({
                    'usn': student['usn'],
                    'student_name': student['name'],
                    'branch': student['branch'],
                    'room_id': current_room.id,
                    'room_code': current_room.room_code,
                    'seat_number': seat_number,
                    'row_num': row,
                    'col_num': col,
                    'subject_code': subject_code
                })
                
                seat_num += 1
            
            branch_idx = (branch_idx + 1) % len(branch_keys)
        
        return allocations
    
    def _save_allocations(self, allocations: List[Dict], subject_code: str) -> int:
        """Save allocations to database"""
        saved_count = 0
        
        try:
            exam_schedule = ExamSchedule.query.filter_by(subject_code=subject_code).first()
            if not exam_schedule:
                return 0
            
            for allocation in allocations:
                seat_allocation = SeatAllocation(
                    exam_schedule_id=exam_schedule.id,
                    usn=allocation['usn'],
                    student_name=allocation['student_name'],
                    subject_code=subject_code,
                    room_id=allocation['room_id'],
                    seat_number=allocation['seat_number'],
                    row_num=allocation['row_num'],
                    col_num=allocation['col_num']
                )
                
                db.session.add(seat_allocation)
                
                # Update student record
                StudentSubject.query.filter_by(
                    usn=allocation['usn'],
                    subject_code=subject_code
                ).update({
                    'seat_allocated': True,
                    'allocated_room': allocation['room_code'],
                    'allocated_seat': allocation['seat_number']
                })
                
                saved_count += 1
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving allocations: {e}")
            saved_count = 0
        
        return saved_count
    
    class AdvancedAIExamProcessor:
        def __init__(self):
            self.algorithms = {
                'genetic': self._genetic_algorithm,
                'graph_coloring': self._graph_coloring,
                'constraint_mapping': self._constraint_mapping,
                'hybrid_ai': self._hybrid_ai
            }

        def process_exams(self, subjects, algorithm, start_date, end_date, session_config):
            """Main processing function"""
            try:
                # Get students for subjects
                students_data = self._get_students_for_subjects(subjects)

                # Get available rooms
                rooms = ExamRoom.query.filter_by(is_active=True).all()

                # Apply selected algorithm
                algorithm_func = self.algorithms.get(algorithm, self._hybrid_ai)
                schedule = algorithm_func(subjects, students_data, rooms, start_date, end_date, session_config)

                # Save to database
                saved_count = self._save_exam_schedule(schedule)

                return {
                    'success': True,
                    'total_students': sum(len(students_data.get(s, [])) for s in subjects),
                    'rooms_used': len(set(item.get('rooms', []) for item in schedule)),
                    'exams_scheduled': saved_count,
                    'efficiency': self._calculate_efficiency(schedule, students_data),
                    'schedule': schedule
                }

            except Exception as e:
                return {'success': False, 'message': str(e)}

        def _hybrid_ai(self, subjects, students_data, rooms, start_date, end_date, session_config):
            """Hybrid AI combining multiple algorithms"""
            # Implement sophisticated AI logic here
            schedule = []

            # Generate dates
            dates = self._generate_exam_dates(start_date, end_date, len(subjects))

            for i, subject_code in enumerate(subjects):
                students = students_data.get(subject_code, [])

                # AI seat allocation
                allocated_rooms = self._allocate_seats_ai(students, rooms)

                schedule.append({
                    'subject_code': subject_code,
                    'subject_name': self._get_subject_name(subject_code),
                    'exam_date': dates[i].strftime('%Y-%m-%d'),
                    'exam_time': '10:00 AM',
                    'rooms': [r['room_code'] for r in allocated_rooms],
                    'student_count': len(students)
                })

            return schedule

        def _allocate_seats_ai(self, students, rooms):
            """AI-powered seat allocation"""
            # Group students by branch to prevent cheating
            branch_groups = defaultdict(list)
            for student in students:
                branch_groups[student['branch']].append(student)

            # Distribute across rooms using AI logic
            allocated_rooms = []
            room_idx = 0

            for room in rooms:
                if room_idx < len(rooms) and students:
                    # Complex AI allocation logic here
                    allocated_rooms.append({
                        'room_code': room.room_code,
                        'room_name': room.room_name,
                        'students': students[:room.capacity]
                    })
                    students = students[room.capacity:]
                    room_idx += 1

            return allocated_rooms

        def _get_students_for_subjects(self, subject_codes):
            """Get students for multiple subjects"""
            students_data = {}

            for subject_code in subject_codes:
                students = db.session.query(
                    StudentSubject.usn,
                    StudentSubject.student_name,
                    Student.branch
                ).join(Student, StudentSubject.usn == Student.usn)\
                 .filter(StudentSubject.subject_code == subject_code).all()

                students_data[subject_code] = [
                    {'usn': s.usn, 'name': s.student_name, 'branch': s.branch}
                    for s in students
                ]

            return students_data

        def _generate_exam_dates(self, start_date, end_date, num_subjects):
            """Generate exam dates avoiding weekends"""
            from datetime import datetime, timedelta

            start = datetime.strptime(start_date, '%Y-%m-%d')
            dates = []
            current = start

            while len(dates) < num_subjects:
                if current.weekday() < 5:  # Monday to Friday
                    dates.append(current)
                current += timedelta(days=1)

            return dates

        def _get_subject_name(self, subject_code):
            """Get subject name by code"""
            subject = Subject.query.filter_by(subject_code=subject_code).first()
            return subject.subject_name if subject else 'Unknown Subject'

        def _calculate_efficiency(self, schedule, students_data):
            """Calculate AI efficiency score"""
            if not schedule:
                return 0

            total_students = sum(len(students_data.get(item['subject_code'], [])) for item in schedule)
            allocated_students = sum(item.get('student_count', 0) for item in schedule)

            return int((allocated_students / max(total_students, 1)) * 100)

        def _save_exam_schedule(self, schedule):
            """Save exam schedule to database"""
            saved_count = 0

            for item in schedule:
                try:
                    exam_schedule = ExamSchedule(
                        subject_code=item['subject_code'],
                        subject_name=item['subject_name'],
                        exam_date=datetime.strptime(item['exam_date'], '%Y-%m-%d').date(),
                        exam_time=item['exam_time'],
                        total_students=item['student_count'],
                        created_by_ai=True
                    )

                    db.session.add(exam_schedule)
                    saved_count += 1

                except Exception as e:
                    print(f"Error saving schedule: {e}")
                    continue

            try:
                db.session.commit()
            except:
                db.session.rollback()
                saved_count = 0

            return saved_count

# ================================
# INITIALIZE AI SERVICES
# ================================

llm_chatbot = RealLLMVTUChatbot()
exam_scheduler = AIExamScheduler()
seat_allocator = GeneticSeatAllocator()

# ================================
# ROUTES
# ================================

@app.route('/')
def index():
    return render_template('ai_chatbot.html')

@app.route('/chatbot')
def chatbot_route():
    return render_template('ai_chatbot.html')

@app.route('/api/chat', methods=['POST'])
def chat_api():
    """Main LLM-powered chat API"""
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
        
        # Process using REAL LLM
        response = llm_chatbot.process_message_with_llm(session_id, message, is_voice)
        
        # Update conversation history
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if chat_session:
            try:
                history = json.loads(chat_session.conversation_history) if chat_session.conversation_history else []
                history.append({
                    'user': message,
                    'assistant': response['message'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'intent': 'registration'
                })
                
                # Keep last 10 exchanges
                if len(history) > 10:
                    history = history[-10:]
                
                chat_session.conversation_history = json.dumps(history)
                db.session.commit()
                
            except Exception as e:
                print(f"Error updating conversation history: {e}")
        
        voice_message = response.get('message', '').replace('*', '').replace('#', '')
        
        return jsonify({
            'message': response['message'],
            'voice_message': voice_message,
            'completed': response.get('completed', False),
            'error': response.get('error', False),
            'next_step': response.get('next_step', 'start'),
            'llm_powered': llm_chatbot.llm_available
        })
        
    except Exception as e:
        print(f"Chat API Error: {str(e)}")
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
        return jsonify({'error': str(e)}), 500
    

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
        rooms = ExamRoom.query.filter_by(is_active=True).all()
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
    """Main AI processing endpoint"""
    try:
        data = request.get_json()
        
        # Initialize AI processor
        ai_processor = AdvancedAIExamProcessor()
        
        # Process using selected algorithm
        result = ai_processor.process_exams(
            subjects=data['subjects'],
            algorithm=data['algorithm'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            session_config={
                'duration': data['session_duration'],
                'sessions_per_day': data['sessions_per_day'],
                'morning_time': data['morning_time'],
                'afternoon_time': data['afternoon_time'],
                'evening_time': data['evening_time']
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI processing failed: {str(e)}'
        })

# Add the AI Scheduler route
@app.route('/ai-exam-scheduler')
def ai_exam_scheduler():
    return render_template('ai_exam_scheduler.html')


@app.route('/debug/students')
def debug_students():
    """Debug registered students"""
    try:
        students = Student.query.all()
        student_subjects = StudentSubject.query.all()
        
        return jsonify({
            'total_students': len(students),
            'total_registrations': len(student_subjects),
            'llm_available': llm_chatbot.llm_available,
            'students': [{'name': s.name, 'usn': s.usn, 'branch': s.branch} for s in students[-5:]],
            'registrations': [{'usn': ss.usn, 'subject': ss.subject_code} for ss in student_subjects[-10:]]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Add sample subjects and rooms
            if not Subject.query.first():
                sample_subjects = [
                    Subject(subject_code='21CS51', subject_name='Management and Entrepreneurship', semester=5, branch='CSE'),
                    Subject(subject_code='21CS52', subject_name='Computer Networks', semester=5, branch='CSE'),
                    Subject(subject_code='21CS53', subject_name='Database Management System', semester=5, branch='CSE'),
                    Subject(subject_code='21CS54', subject_name='Automata Theory', semester=5, branch='CSE'),
                    Subject(subject_code='21IS51', subject_name='Management and Entrepreneurship', semester=5, branch='ISE'),
                    Subject(subject_code='21EC51', subject_name='Management and Entrepreneurship', semester=5, branch='ECE'),
                ]
                
                sample_rooms = [
                    ExamRoom(room_code='R001', room_name='Main Hall A', capacity=60, rows=10, cols=6),
                    ExamRoom(room_code='R002', room_name='Main Hall B', capacity=50, rows=10, cols=5),
                    ExamRoom(room_code='R003', room_name='Classroom 101', capacity=40, rows=8, cols=5),
                ]
                
                for subject in sample_subjects:
                    db.session.add(subject)
                
                for room in sample_rooms:
                    db.session.add(room)
                
                db.session.commit()
                print("✅ Sample data inserted")
        
        print("🚀 Starting REAL LLM-POWERED VTU Registration System...")
        print(f"🤖 LLM Available: {llm_chatbot.llm_available}")
        print(f"🧠 Semantic Search: {llm_chatbot.semantic_search_available}")
        print("📱 Registration: ACTIVE ✅")
        print("🧬 Genetic Algorithms: ACTIVE ✅")
        print("💾 Database: READY ✅")
        
        app.run(debug=True, port=5000, host='127.0.0.1')
        
    except Exception as e:
        print(f"❌ App startup error: {str(e)}")
        traceback.print_exc()







    def allocate_students_for_subjects(self, selected_subject_codes: list, algorithm: str = 'genetic',exam_date: str = None, exam_time: str = None) -> dict:
        """
        MAIN FUNCTION: Allocate students for selected subjects using AI
        """
        try:
            print(f"🤖 Starting AI allocation for subjects: {selected_subject_codes}")
            print(f"🧠 Using algorithm: {algorithm}")
            print(f"📅 Exam scheduled for: {exam_date} at {exam_time}")
            
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
            
            # Step 3: Check capacity
            total_capacity = sum(room.capacity for room in rooms)
            
            if len(students) > total_capacity:
                return {
                    'success': False,
                    'message': f'Insufficient room capacity: {len(students)} students need seats, but only {total_capacity} seats available',
                    'total_students': len(students),
                    'total_capacity': total_capacity,
                    'selected_subjects': selected_subject_codes
                }
            
            # Step 4: Apply selected AI algorithm
            algorithm_func = self.algorithms.get(algorithm, self._hybrid_ai_algorithm)
            allocations = algorithm_func(students, rooms)
            
            if not allocations:
                return {
                    'success': False,
                    'message': f'{algorithm} algorithm failed to generate seat allocations',
                    'total_students': len(students),
                    'selected_subjects': selected_subject_codes
                }
            
            # Step 5: Save allocations to database
            session_id = self._save_allocations_to_database(allocations, selected_subject_codes, algorithm,exam_date,exam_time)
            
            return {
                'success': True,
                'message': f'Successfully allocated seats for {len(allocations)} students using {algorithm}',
                'total_students': len(students),
                'allocated_students': len(allocations),
                'rooms_used': len(set(alloc['room_code'] for alloc in allocations)),
                'algorithm_used': algorithm.replace('_', ' ').title(),
                'session_id': session_id,
                'fitness_score': self._calculate_allocation_quality(allocations),
                'selected_subjects': selected_subject_codes,
                'allocations_preview': allocations[:10]  # First 10 for preview
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
    
    def _get_students_for_subjects(self, subject_codes: list) -> list:
        """Get all students registered under the selected subjects"""
        try:
            # Query student_subjects table using the exact schema you provided
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
            
            # Convert to list of dictionaries
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
            
            print(f"📊 Student distribution by branch:")
            branch_counts = defaultdict(int)
            for student in students:
                branch_counts[student['branch']] += 1
            
            for branch, count in branch_counts.items():
                print(f"  {branch}: {count} students")
            
            return students
            
        except Exception as e:
            print(f"Error getting students: {e}")
            return []
    
    def _genetic_algorithm(self, students: list, rooms: list) -> list:
        """🧬 Genetic Algorithm for optimal seat allocation"""
        try:
            print("🧬 Running Genetic Algorithm...")
            
            # Create position mapping
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
            
            # Ensure we don't exceed available positions
            if len(students) > len(positions):
                students = students[:len(positions)]
            
            if DEAP_AVAILABLE:
                return self._advanced_genetic_algorithm(students, positions)
            else:
                return self._simple_genetic_algorithm(students, positions)
                
        except Exception as e:
            print(f"Genetic algorithm error: {e}")
            return self._fallback_allocation(students, positions)
    
    def _simple_genetic_algorithm(self, students: list, positions: list) -> list:
        """Simple genetic algorithm implementation"""
        population_size = min(50, max(10, len(students)))
        generations = min(100, max(20, len(students) * 2))
        
        # Create initial population
        population = []
        for _ in range(population_size):
            # Random permutation of student indices
            individual = list(range(len(students)))
            random.shuffle(individual)
            population.append(individual)
        
        # Evolve population
        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in population:
                score = self._evaluate_fitness(individual, students, positions)
                fitness_scores.append(score)
            
            # Selection and reproduction
            new_population = []
            
            # Keep best individuals (elitism)
            sorted_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)
            elite_count = max(1, population_size // 10)
            
            for i in range(elite_count):
                new_population.append(population[sorted_indices[i]].copy())
            
            # Generate offspring
            while len(new_population) < population_size:
                # Tournament selection
                parent1 = self._tournament_selection(population, fitness_scores)
                parent2 = self._tournament_selection(population, fitness_scores)
                
                # Crossover
                child1, child2 = self._crossover(parent1, parent2)
                
                # Mutation
                self._mutate(child1)
                self._mutate(child2)
                
                new_population.extend([child1, child2])
            
            population = new_population[:population_size]
        
        # Get best solution
        final_fitness = [self._evaluate_fitness(ind, students, positions) for ind in population]
        best_index = max(range(len(final_fitness)), key=lambda i: final_fitness[i])
        best_individual = population[best_index]
        
        # Convert to allocations
        return self._convert_to_allocations(best_individual, students, positions, 'Genetic Algorithm')
    
    def _advanced_genetic_algorithm(self, students: list, positions: list) -> list:
        """Advanced genetic algorithm using DEAP library"""
        toolbox = base.Toolbox()
        
        # Individual: permutation of student indices
        toolbox.register("indices", random.sample, range(len(students)), len(students))
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.indices)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        
        # Genetic operators
        toolbox.register("evaluate", self._evaluate_fitness_deap, students=students, positions=positions)
        toolbox.register("mate", tools.cxPartialyMatched)
        toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.1)
        toolbox.register("select", tools.selTournament, tournsize=3)
        
        # Create population
        population = toolbox.population(n=min(50, max(20, len(students))))
        
        # Hall of fame
        hof = tools.HallOfFame(1)
        
        # Run algorithm
        algorithms.eaSimple(
            population, toolbox,
            cxpb=0.7, mutpb=0.2, ngen=min(50, len(students)),
            halloffame=hof, verbose=False
        )
        
        if hof:
            best_individual = hof[0]
            return self._convert_to_allocations(best_individual, students, positions, 'Advanced Genetic Algorithm')
        else:
            return self._fallback_allocation(students, positions)
    
    def _evaluate_fitness(self, individual: list, students: list, positions: list) -> float:
        """Evaluate fitness of an allocation"""
        fitness = 0.0
        
        # Penalty for same branch students sitting adjacent
        for i in range(len(individual) - 1):
            if i < len(positions) - 1:
                student1 = students[individual[i]]
                student2 = students[individual[i + 1]]
                pos1 = positions[i]
                pos2 = positions[i + 1]
                
                # If same room and adjacent seats
                if pos1['room_id'] == pos2['room_id']:
                    # Same branch penalty
                    if student1['branch'] == student2['branch']:
                        fitness -= 5
                    
                    # Same subject penalty  
                    if student1['subject_code'] == student2['subject_code']:
                        fitness -= 10
                    
                    # Different branch bonus
                    if student1['branch'] != student2['branch']:
                        fitness += 2
        
        # Room distribution bonus
        room_counts = defaultdict(int)
        for i, pos_idx in enumerate(individual):
            if i < len(positions):
                room_counts[positions[pos_idx]['room_id']] += 1
        
        # Bonus for balanced room usage
        if len(room_counts) > 1:
            counts = list(room_counts.values())
            avg_count = sum(counts) / len(counts)
            variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
            fitness += max(0, 10 - variance)  # Lower variance = higher score
        
        return fitness
    
    def _evaluate_fitness_deap(self, individual, students, positions):
        """DEAP-compatible fitness evaluation"""
        return (self._evaluate_fitness(individual, students, positions),)
    
    def _tournament_selection(self, population: list, fitness_scores: list, tournament_size: int = 3) -> list:
        """Tournament selection"""
        tournament_indices = random.sample(range(len(population)), min(tournament_size, len(population)))
        best_index = max(tournament_indices, key=lambda i: fitness_scores[i])
        return population[best_index].copy()
    
    def _crossover(self, parent1: list, parent2: list) -> tuple:
        """Order crossover (OX)"""
        size = len(parent1)
        start, end = sorted(random.sample(range(size), 2))
        
        child1 = [-1] * size
        child2 = [-1] * size
        
        # Copy selected section
        child1[start:end] = parent1[start:end]
        child2[start:end] = parent2[start:end]
        
        # Fill remaining positions
        def fill_child(child, parent_other):
            remaining = [item for item in parent_other if item not in child]
            for i in range(size):
                if child[i] == -1:
                    child[i] = remaining.pop(0)
        
        fill_child(child1, parent2)
        fill_child(child2, parent1)
        
        return child1, child2
    
    def _mutate(self, individual: list, mutation_rate: float = 0.1):
        """Swap mutation"""
        for i in range(len(individual)):
            if random.random() < mutation_rate:
                j = random.randint(0, len(individual) - 1)
                individual[i], individual[j] = individual[j], individual[i]
    
    def _graph_coloring_algorithm(self, students: list, rooms: list) -> list:
        """🎨 Graph Coloring Algorithm"""
        try:
            print("🎨 Running Graph Coloring Algorithm...")
            
            # Create conflict graph
            conflicts = defaultdict(set)
            for i, student1 in enumerate(students):
                for j, student2 in enumerate(students):
                    if i != j:
                        # Same branch or same subject = conflict
                        if (student1['branch'] == student2['branch'] or 
                            student1['subject_code'] == student2['subject_code']):
                            conflicts[i].add(j)
                            conflicts[j].add(i)
            
            # Welsh-Powell algorithm for graph coloring
            student_indices = list(range(len(students)))
            student_indices.sort(key=lambda i: len(conflicts[i]), reverse=True)
            
            colors = {}
            available_colors = list(range(len(students)))
            
            for student_idx in student_indices:
                used_colors = {colors[conflict] for conflict in conflicts[student_idx] if conflict in colors}
                for color in available_colors:
                    if color not in used_colors:
                        colors[student_idx] = color
                        break
            
            # Convert colors to seat positions
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
            
            # Create allocations
            allocations = []
            for i, student in enumerate(students):
                if i < len(positions):
                    color = colors.get(i, i)
                    pos_idx = color % len(positions)
                    position = positions[pos_idx]
                    
                    allocation = self._create_allocation_record(student, position, 'Graph Coloring')
                    allocations.append(allocation)
            
            print(f"🎨 Graph coloring allocated {len(allocations)} students")
            return allocations
            
        except Exception as e:
            print(f"Graph coloring error: {e}")
            return self._fallback_allocation(students, self._create_positions(rooms))
    
    def _constraint_mapping_algorithm(self, students: list, rooms: list) -> list:
        """🗺️ Constraint Satisfaction Algorithm"""
        try:
            print("🗺️ Running Constraint Mapping Algorithm...")
            
            positions = self._create_positions(rooms)
            allocations = []
            used_positions = set()
            
            # Sort students by constraints (same branch students spread out)
            branch_groups = defaultdict(list)
            for i, student in enumerate(students):
                branch_groups[student['branch']].append((i, student))
            
            # Alternate between branches
            ordered_students = []
            branch_iterators = {branch: iter(students_list) for branch, students_list in branch_groups.items()}
            
            while branch_iterators:
                for branch in list(branch_iterators.keys()):
                    try:
                        ordered_students.append(next(branch_iterators[branch]))
                    except StopIteration:
                        del branch_iterators[branch]
            
            # Allocate seats with constraints
            for student_idx, student in ordered_students:
                best_position = None
                best_score = -1
                
                for pos_idx, position in enumerate(positions):
                    if pos_idx in used_positions:
                        continue
                    
                    # Calculate constraint satisfaction score
                    score = self._calculate_position_score(student, position, allocations, positions)
                    
                    if score > best_score:
                        best_score = score
                        best_position = (pos_idx, position)
                
                if best_position:
                    pos_idx, position = best_position
                    used_positions.add(pos_idx)
                    allocation = self._create_allocation_record(student, position, 'Constraint Mapping')
                    allocations.append(allocation)
            
            print(f"🗺️ Constraint mapping allocated {len(allocations)} students")
            return allocations
            
        except Exception as e:
            print(f"Constraint mapping error: {e}")
            return self._fallback_allocation(students, self._create_positions(rooms))
    
    def _hybrid_ai_algorithm(self, students: list, rooms: list) -> list:
        """🤖 Hybrid AI Algorithm (combines multiple approaches)"""
        try:
            print("🤖 Running Hybrid AI Algorithm...")
            
            # Phase 1: Initial allocation using constraint mapping
            initial_allocation = self._constraint_mapping_algorithm(students, rooms)
            
            # Phase 2: Improve using genetic algorithm (if we have enough students)
            if len(students) >= 10:
                try:
                    genetic_allocation = self._genetic_algorithm(students, rooms)
                    
                    # Compare quality and choose better one
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
            return self._fallback_allocation(students, self._create_positions(rooms))
    
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




        <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Staff Registration - VTU Exam System</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', sans-serif;
        }
        
        .registration-container {
            max-width: 600px;
            margin: 50px auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .form-label {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        
        .form-control {
            border-radius: 10px;
            padding: 12px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s;
        }
        
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        
        .btn-register {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            padding: 14px;
            font-size: 18px;
            font-weight: 600;
            border-radius: 10px;
            width: 100%;
            margin-top: 20px;
            color: white;
            transition: transform 0.3s;
        }
        
        .btn-register:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        }
        
        .alert {
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .input-group-text {
            background: #f8f9fa;
            border: 2px solid #e0e0e0;
            border-right: none;
        }
        
        .form-control-icon {
            border-left: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="registration-container">
            <div class="header">
                <h1><i class="fas fa-user-tie"></i> Staff Registration</h1>
                <p class="text-muted">VTU Examination System</p>
            </div>
            
            <div id="alertContainer"></div>
            
            <form id="staffRegistrationForm">
                <div class="mb-3">
                    <label for="staffId" class="form-label">
                        <i class="fas fa-id-card text-primary"></i> Staff ID *
                    </label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-hashtag"></i></span>
                        <input type="text" class="form-control form-control-icon" id="staffId" 
                               placeholder="Enter Staff ID (e.g., STAFF001)" required>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="staffName" class="form-label">
                        <i class="fas fa-user text-success"></i> Staff Name *
                    </label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-user"></i></span>
                        <input type="text" class="form-control form-control-icon" id="staffName" 
                               placeholder="Enter Full Name" required>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="department" class="form-label">
                        <i class="fas fa-building text-warning"></i> Department *
                    </label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-building"></i></span>
                        <select class="form-control form-control-icon" id="department" required>
                            <option value="">Select Department</option>
                            <option value="Computer Science & Engineering">Computer Science & Engineering</option>
                            <option value="Information Science & Engineering">Information Science & Engineering</option>
                            <option value="Electronics & Communication Engineering">Electronics & Communication Engineering</option>
                            <option value="Mechanical Engineering">Mechanical Engineering</option>
                            <option value="Civil Engineering">Civil Engineering</option>
                            <option value="Electrical & Electronics Engineering">Electrical & Electronics Engineering</option>
                            <option value="MBA">MBA</option>
                            <option value="MCA">MCA</option>
                            <option value="Administration">Administration</option>
                            <option value="Other">Other</option>
                        </select>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="email" class="form-label">
                        <i class="fas fa-envelope text-info"></i> Email (Optional)
                    </label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-envelope"></i></span>
                        <input type="email" class="form-control form-control-icon" id="email" 
                               placeholder="staff@example.com">
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="phone" class="form-label">
                        <i class="fas fa-phone text-danger"></i> Phone (Optional)
                    </label>
                    <div class="input-group">
                        <span class="input-group-text"><i class="fas fa-phone"></i></span>
                        <input type="tel" class="form-control form-control-icon" id="phone" 
                               placeholder="9876543210" pattern="[0-9]{10}">
                    </div>
                </div>
                
                <button type="submit" class="btn btn-register" id="registerBtn">
                    <i class="fas fa-user-plus"></i> Register Staff
                </button>
            </form>
            
            <div class="text-center mt-4">
                <a href="/admin/staff-management" class="text-decoration-none">
                    <i class="fas fa-arrow-left"></i> Back to Staff Management
                </a>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('staffRegistrationForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const staffId = document.getElementById('staffId').value.trim();
            const staffName = document.getElementById('staffName').value.trim();
            const department = document.getElementById('department').value;
            const email = document.getElementById('email').value.trim();
            const phone = document.getElementById('phone').value.trim();
            
            if (!staffId || !staffName || !department) {
                showAlert('Please fill all required fields', 'danger');
                return;
            }
            
            const registerBtn = document.getElementById('registerBtn');
            registerBtn.disabled = true;
            registerBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
            
            try {
                const response = await fetch('/api/staff/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        staff_id: staffId,
                        staff_name: staffName,
                        department: department,
                        email: email || null,
                        phone: phone || null
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAlert('✅ Staff registered successfully!', 'success');
                    document.getElementById('staffRegistrationForm').reset();
                    
                    setTimeout(() => {
                        window.location.href = '/admin/staff-management';
                    }, 2000);
                } else {
                    showAlert('❌ ' + data.message, 'danger');
                }
            } catch (error) {
                showAlert('❌ Registration failed: ' + error.message, 'danger');
            } finally {
                registerBtn.disabled = false;
                registerBtn.innerHTML = '<i class="fas fa-user-plus"></i> Register Staff';
            }
        });
        
        function showAlert(message, type) {
            const alertContainer = document.getElementById('alertContainer');
            alertContainer.innerHTML = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
        }
    </script>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
</body>
</html>
