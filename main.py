#!/usr/bin/env python3
"""
Main entry point for the Recruitment Automation System
This is a lightweight Flask app that provides:
- Admin dashboard for viewing candidates and jobs
- API endpoints for N8N integration
- WhatsApp contact management
- No local CV processing (handled by N8N)
"""

from app import app

if __name__ == '__main__':
    app.run()
