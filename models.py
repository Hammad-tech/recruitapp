from datetime import datetime
from database import db
from flask_login import UserMixin
from sqlalchemy import Enum
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    HR = "hr"

class CandidateStatus(enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"

class JobStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100))
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    experience_level = db.Column(db.String(50))  # entry, mid, senior
    job_type = db.Column(db.String(50))  # full-time, part-time, contract
    status = db.Column(Enum(JobStatus), default=JobStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # AI-extracted skills and requirements for matching
    required_skills = db.Column(db.JSON)  # List of required skills
    preferred_skills = db.Column(db.JSON)  # List of preferred skills
    
    # Relationships
    candidates = db.relationship('CandidateJobMatch', backref='job', lazy=True, cascade='all, delete-orphan')

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    status = db.Column(Enum(CandidateStatus), default=CandidateStatus.NEW)
    
    # CV and parsing information
    #
    # `cv_filename` is kept for backwards-compatibility when CVs are stored
    # locally on the server.  When integrating with n8n and Google Drive,
    # instead of storing a local filename we persist the Drive link in
    # `cv_drive_link`.  The application does not perform matching anymore
    # (matching is handled externally in n8n), so only the link is needed.
    cv_filename = db.Column(db.String(255))
    cv_drive_link = db.Column(db.String(512))
    cv_text = db.Column(db.Text)  # Extracted text from CV
    
    # AI-extracted information
    skills = db.Column(db.JSON)  # List of skills extracted from CV
    experience_years = db.Column(db.Integer)
    education = db.Column(db.JSON)  # Education details
    work_experience = db.Column(db.JSON)  # Work experience details
    summary = db.Column(db.Text)  # AI-generated candidate summary
    
    # Source information
    source = db.Column(db.String(50))  # email, whatsapp, manual
    source_reference = db.Column(db.String(200))  # email subject, whatsapp number, etc.
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job_matches = db.relationship('CandidateJobMatch', backref='candidate', lazy=True, cascade='all, delete-orphan')

class CandidateJobMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    
    # AI-generated match information
    match_score = db.Column(db.Integer, nullable=False)  # 0-100
    matching_skills = db.Column(db.JSON)  # Skills that match
    missing_skills = db.Column(db.JSON)  # Required skills that are missing
    match_reason = db.Column(db.Text)  # AI explanation of the match
    
    # Status and notes
    status = db.Column(Enum(CandidateStatus), default=CandidateStatus.NEW)
    notes = db.Column(db.Text)  # HR notes
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint to prevent duplicate matches
    __table_args__ = (db.UniqueConstraint('candidate_id', 'job_id'),)

class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255))
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    status = db.Column(db.String(50))  # success, error, duplicate
    error_message = db.Column(db.Text)

class WhatsAppContact(db.Model):
    """Model to track WhatsApp contact state and preferences"""
    id = db.Column(db.Integer, primary_key=True)
    wa_id = db.Column(db.String(20), unique=True, nullable=False)  # WhatsApp ID (phone number)
    eu_status = db.Column(db.String(10))  # 'eu', 'non-eu', 'unknown'
    country_code = db.Column(db.String(5))  # Detected country code
    intent = db.Column(db.String(20))  # 'client', 'candidate', null
    
    # Message tracking
    last_message_text = db.Column(db.Text)
    last_message_type = db.Column(db.String(20))  # text, document, interactive, etc.
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_system_message_at = db.Column(db.DateTime)  # When we last sent system message
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WhatsAppLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    message_id = db.Column(db.String(100))
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'))
    status = db.Column(db.String(50))  # success, error, duplicate
    error_message = db.Column(db.Text)
