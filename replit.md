# Overview

This is a comprehensive recruitment automation system built with Flask that streamlines the entire hiring process from job posting to candidate matching. The system integrates AI-powered CV parsing, automated email and WhatsApp processing, and intelligent candidate-job matching using OpenAI's GPT models. It features a web dashboard for HR teams to manage jobs and candidates, automated background processing for incoming applications, and real-time notifications for high-quality matches.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Flask with Jinja2 templating engine
- **UI Framework**: Bootstrap 5 with Replit dark theme for consistent styling
- **JavaScript**: Vanilla JavaScript for interactive features (file uploads, form validation, notifications)
- **Icons**: Feather Icons for consistent iconography
- **Responsive Design**: Mobile-first approach with Bootstrap grid system

## Backend Architecture
- **Web Framework**: Flask with modular route organization
- **Authentication**: Flask-Login for session management with role-based access (Admin/HR)
- **Database ORM**: SQLAlchemy with declarative base for model definitions
- **File Handling**: Werkzeug utilities for secure file uploads and processing
- **Background Processing**: Python schedule library for automated tasks
- **Logging**: Python logging module for debugging and monitoring

## Data Storage Solutions
- **Primary Database**: SQLite for development with configurable PostgreSQL support
- **File Storage**: Local filesystem for CV documents in organized upload folders
- **Session Management**: Flask sessions with configurable secret keys
- **Database Models**: User management, Job postings, Candidate profiles, Match scores, Email/WhatsApp logs

## Authentication and Authorization
- **User Authentication**: Password hashing with Werkzeug security utilities
- **Session Management**: Flask-Login for user session handling
- **Role-Based Access**: Admin and HR user roles with different permission levels
- **Login Protection**: Decorators for protecting routes requiring authentication

## AI Integration Architecture
- **CV Parsing**: OpenAI GPT-5 API for extracting structured data from resume documents
- **Text Extraction**: PyPDF2 for PDF processing, python-docx for Word documents
- **Candidate Matching**: AI-powered scoring system comparing candidate skills to job requirements
- **Skill Extraction**: Natural language processing for identifying technical and soft skills

## Communication Systems
- **Email Processing**: IMAP integration for automated email monitoring and CV extraction
- **WhatsApp Integration**: Facebook Graph API for WhatsApp Business messaging
- **Automated Responses**: Template-based messaging for candidate communications
- **Notification System**: Real-time alerts for high-scoring candidate matches

## Background Task Management
- **Email Monitoring**: Continuous IMAP connection for processing incoming applications
- **Scheduled Reports**: Daily and weekly recruitment statistics generation
- **Match Processing**: Automated candidate-job matching when new profiles are added
- **File Processing**: Asynchronous CV parsing and data extraction

# External Dependencies

## AI and Machine Learning Services
- **OpenAI API**: GPT-5 model for CV parsing and candidate-job matching
- **API Key Management**: Environment variable configuration for secure API access

## Email Services
- **IMAP Integration**: Gmail and other email providers for automated application processing
- **SMTP Integration**: Email sending capabilities for automated responses and reports
- **Email Parsing**: Standard email libraries for attachment processing and content extraction

## WhatsApp Business API
- **Facebook Graph API**: WhatsApp Business platform integration
- **Message Processing**: Webhook handling for incoming messages and media
- **Media Download**: API endpoints for retrieving CV files sent via WhatsApp

## Database Systems
- **SQLite**: Default development database with automatic table creation
- **PostgreSQL**: Production database support through environment configuration
- **Connection Pooling**: SQLAlchemy engine options for connection management

## File Processing Libraries
- **PyPDF2**: PDF document text extraction and processing
- **python-docx**: Microsoft Word document parsing
- **Werkzeug**: Secure filename handling and file upload utilities

## Frontend Dependencies
- **Bootstrap 5**: CSS framework with Replit dark theme integration
- **Feather Icons**: SVG icon library for consistent UI elements
- **CDN Resources**: External hosting for CSS and JavaScript libraries

## Development and Deployment
- **Flask Development Server**: Built-in server for local development
- **Environment Configuration**: Flexible configuration through environment variables
- **ProxyFix Middleware**: Production deployment support for reverse proxy setups
- **Logging Configuration**: Configurable logging levels for debugging and monitoring