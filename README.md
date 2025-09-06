# 🚀 Recruitment Automation System

A lightweight Flask application that provides admin dashboard and API endpoints for recruitment automation. All CV processing, job matching, and communication handling is done via N8N workflows.

## ✨ Features

### 📊 Admin Dashboard
- **Jobs Management**: Create, edit, pause, and delete job postings
- **Candidates Overview**: View all candidates with advanced filtering
- **WhatsApp Contacts**: Track EU/Non-EU contacts and client/candidate intents
- **Real-time Statistics**: Dashboard with live updates
- **Advanced Search**: Filter by status, source, experience, location

### 🔗 API Endpoints
- **`GET /api/jobs`** - Get all active jobs (for N8N)
- **`POST /api/candidate`** - Create candidates with job scores (from N8N)
- **WhatsApp Contact Management** - Complete CRUD operations
- **Job Details** - Detailed job information with candidate matches

### 🎯 N8N Integration
- **Email CV Processing**: Automatic extraction and job matching
- **WhatsApp Automation**: EU/Non-EU routing with intelligent responses
- **Google Drive Storage**: CV storage and sharing
- **OpenAI Analysis**: Candidate profiling and job scoring

## 🚀 Quick Start

### Local Development
```bash
git clone https://github.com/Hammad-tech/recruitapp.git
cd recruitapp
pip install -r requirements.txt
python app.py
```

### Production Deployment (Render)
```bash
# Build Command: pip install -r requirements.txt
# Start Command: python app.py
# Runtime: python-3.11
```

## 🔐 Environment Variables

```bash
DATABASE_URL=sqlite:///recruitment.db
SESSION_SECRET=your-secret-key
OPENAI_API_KEY=sk-your-openai-key  # Used by N8N workflows
WHATSAPP_VERIFY_TOKEN=your-verify-token
ALLOWED_ORIGINS=*
PORT=5000  # Auto-set by hosting platforms
```

## 📱 Default Login
- **Username**: `admin`
- **Password**: `admin123`
- **⚠️ Change password after first login**

## 🔄 N8N Workflows

Import the included workflow files:
- **`whatsapp_complete_final_workflow.json`** - Complete WhatsApp automation
- Update URLs in workflows to point to your deployed app

## 📋 API Documentation

### Get Jobs
```bash
GET /api/jobs
Response: {"success": true, "jobs": [...], "count": 5}
```

### Create Candidate
```bash
POST /api/candidate
Body: {
  "name": "John Doe",
  "email": "john@example.com",
  "cv_drive_link": "https://drive.google.com/...",
  "skills": ["Python", "JavaScript"],
  "job_scores": [{"job_id": 1, "score": 85, "matching_skills": [...]}]
}
```

### WhatsApp Contact Management
```bash
POST /api/whatsapp/contacts/upsert
GET /api/whatsapp/contacts/{wa_id}
PATCH /api/whatsapp/contacts/{wa_id}
GET /api/whatsapp/contacts
```

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    N8N      │───▶│  Flask App  │───▶│  Database   │
│ Workflows   │    │(Dashboard)  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│  OpenAI     │    │   Admin     │
│   API       │    │    UI       │
└─────────────┘    └─────────────┘
```

## 📞 Support

For issues or questions, check the GitHub repository or contact the development team.

---

**Built with ❤️ for modern recruitment automation**
