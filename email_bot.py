import imaplib
import email
import os
import logging
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re
from werkzeug.utils import secure_filename
from app import app
from database import db
from models import Candidate, EmailLog
from cv_parser import parse_cv_text
# Note: job matching is handled externally by n8n.  The email bot no longer
# imports or calls job matching functions here.

class EmailBot:
    def __init__(self):
        self.imap_server = os.getenv('IMAP_SERVER', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def connect_imap(self):
        """Connect to IMAP server"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_user, self.email_password)
            return mail
        except Exception as e:
            self.logger.error(f"IMAP connection failed: {e}")
            return None

    def extract_email_info(self, sender):
        """Extract name and email from sender string"""
        # Handle formats like "John Doe <john@example.com>" or just "john@example.com"
        email_pattern = r'<(.+?)>|([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        name_pattern = r'^(.+?)\s*<'
        
        email_match = re.search(email_pattern, sender)
        name_match = re.search(name_pattern, sender)
        
        email_addr = email_match.group(1) or email_match.group(2) if email_match else sender
        name = name_match.group(1).strip() if name_match else email_addr.split('@')[0]
        
        return name, email_addr

    def is_eu_phone_number(self, text):
        """Check if text contains EU phone numbers"""
        # EU country codes (simplified list)
        eu_codes = ['+44', '+49', '+33', '+39', '+34', '+31', '+32', '+48', '+43', '+45', '+46', '+47', '+41']
        
        for code in eu_codes:
            if code in text:
                return True
        return False

    def extract_cv_attachments(self, msg):
        """Extract CV attachments from email"""
        attachments = []
        
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename and any(filename.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.txt']):
                    content = part.get_payload(decode=True)
                    attachments.append({
                        'filename': secure_filename(filename),
                        'content': content
                    })
        
        return attachments

    def save_attachment(self, attachment):
        """Save attachment to uploads folder"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + attachment['filename']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(attachment['content'])
        
        return filename, filepath

    def send_reply(self, to_email, subject, message):
        """Send automated reply email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = to_email
            msg['Subject'] = f"Re: {subject}"
            
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            self.logger.info(f"Reply sent to {to_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send reply to {to_email}: {e}")
            return False

    def process_email(self, msg, sender_email, subject):
        """Process individual email message"""
        with app.app_context():
            try:
                # Check if we've already processed this email
                existing_log = EmailLog.query.filter_by(
                    sender_email=sender_email,
                    subject=subject
                ).first()
                
                if existing_log:
                    self.logger.info(f"Email from {sender_email} already processed")
                    return
                
                # Extract sender name
                sender_name, sender_email_clean = self.extract_email_info(sender_email)
                
                # Check if candidate already exists
                existing_candidate = Candidate.query.filter_by(email=sender_email_clean).first()
                
                # Get email body text
                email_body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            email_body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                else:
                    email_body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                # Filter EU phone numbers if required
                if os.getenv('FILTER_EU_ONLY', 'false').lower() == 'true':
                    if not self.is_eu_phone_number(email_body):
                        self.logger.info(f"Non-EU candidate filtered: {sender_email}")
                        
                        # Send rejection email
                        rejection_msg = """
                        Thank you for your interest in our positions. 
                        Currently, we are only considering candidates based in the European Union.
                        We appreciate your understanding.
                        
                        Best regards,
                        HR Team
                        """
                        self.send_reply(sender_email_clean, subject, rejection_msg)
                        
                        # Log the filtering
                        log_entry = EmailLog(
                            sender_email=sender_email_clean,
                            subject=subject,
                            status='filtered_non_eu'
                        )
                        db.session.add(log_entry)
                        db.session.commit()
                        return
                
                # Extract CV attachments
                attachments = self.extract_cv_attachments(msg)
                
                if not attachments and not existing_candidate:
                    # No CV found, request it
                    request_msg = """
                    Thank you for your interest in our positions.
                    
                    We notice that your email doesn't contain a CV attachment. 
                    Please reply to this email with your CV attached in PDF, DOC, or DOCX format 
                    so we can properly review your application.
                    
                    Best regards,
                    HR Team
                    """
                    self.send_reply(sender_email_clean, subject, request_msg)
                    
                    log_entry = EmailLog(
                        sender_email=sender_email_clean,
                        subject=subject,
                        status='cv_requested'
                    )
                    db.session.add(log_entry)
                    db.session.commit()
                    return
                
                candidate = existing_candidate
                cv_filename = None
                
                # Process CV attachment if present
                if attachments:
                    attachment = attachments[0]  # Use first CV attachment
                    cv_filename, filepath = self.save_attachment(attachment)
                    
                    # Parse CV
                    cv_data = parse_cv_text(filepath)
                    
                    if candidate:
                        # Update existing candidate
                        candidate.cv_filename = cv_filename
                        candidate.cv_text = cv_data.get('text')
                        candidate.skills = cv_data.get('skills', [])
                        candidate.experience_years = cv_data.get('experience_years')
                        candidate.education = cv_data.get('education', [])
                        candidate.work_experience = cv_data.get('work_experience', [])
                        candidate.summary = cv_data.get('summary')
                        candidate.last_updated = datetime.utcnow()
                    else:
                        # Create new candidate
                        candidate = Candidate(
                            name=cv_data.get('name', sender_name),
                            email=sender_email_clean,
                            phone=cv_data.get('phone'),
                            location=cv_data.get('location'),
                            cv_filename=cv_filename,
                            cv_text=cv_data.get('text'),
                            skills=cv_data.get('skills', []),
                            experience_years=cv_data.get('experience_years'),
                            education=cv_data.get('education', []),
                            work_experience=cv_data.get('work_experience', []),
                            summary=cv_data.get('summary'),
                            source='email',
                            source_reference=subject
                        )
                        db.session.add(candidate)
                        db.session.flush()  # Get candidate ID
                
                db.session.commit()
                
                # Send confirmation email.  Matching is handled externally by n8n.
                if candidate:
                    confirmation_msg = """
                    Thank you for your application!
                    
                    We have received your CV and it has been added to our candidate database.
                    Your profile will be matched to suitable positions by our automation system.
                    
                    If there's a good match, our HR team will contact you shortly.
                    
                    Best regards,
                    HR Team
                    """
                    self.send_reply(sender_email_clean, subject, confirmation_msg)
                
                # Log successful processing
                log_entry = EmailLog(
                    sender_email=sender_email_clean,
                    subject=subject,
                    candidate_id=candidate.id if candidate else None,
                    status='success'
                )
                db.session.add(log_entry)
                db.session.commit()
                
                self.logger.info(f"Successfully processed email from {sender_email}")
                
            except Exception as e:
                self.logger.error(f"Error processing email from {sender_email}: {e}")
                
                # Log error
                log_entry = EmailLog(
                    sender_email=sender_email,
                    subject=subject,
                    status='error',
                    error_message=str(e)
                )
                db.session.add(log_entry)
                db.session.commit()

    def check_emails(self):
        """Check for new emails and process them"""
        if not self.email_user or not self.email_password:
            self.logger.warning("Email credentials not configured")
            return
        
        mail = self.connect_imap()
        if not mail:
            return
        
        try:
            # Select inbox
            mail.select('inbox')
            
            # Search for unread emails
            result, messages = mail.search(None, 'UNSEEN')
            
            if result == 'OK' and messages[0]:
                email_ids = messages[0].split()
                self.logger.info(f"Found {len(email_ids)} new emails")
                
                for email_id in email_ids:
                    try:
                        # Fetch email
                        result, msg_data = mail.fetch(email_id, '(RFC822)')
                        
                        if result == 'OK':
                            email_body = msg_data[0][1]
                            msg = email.message_from_bytes(email_body)
                            
                            sender = msg['From']
                            subject = msg['Subject']
                            
                            self.logger.info(f"Processing email from {sender}: {subject}")
                            self.process_email(msg, sender, subject)
                            
                            # Mark as read
                            mail.store(email_id, '+FLAGS', '\\Seen')
                            
                    except Exception as e:
                        self.logger.error(f"Error processing email ID {email_id}: {e}")
                        continue
            
        except Exception as e:
            self.logger.error(f"Error checking emails: {e}")
        finally:
            mail.logout()

    def start_monitoring(self):
        """Start continuous email monitoring"""
        self.logger.info("Starting email monitoring...")
        
        while True:
            try:
                self.check_emails()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                self.logger.info("Email monitoring stopped")
                break
            except Exception as e:
                self.logger.error(f"Email monitoring error: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

def start_email_monitoring():
    """Entry point for starting email monitoring in a thread"""
    bot = EmailBot()
    bot.start_monitoring()

if __name__ == '__main__':
    start_email_monitoring()
