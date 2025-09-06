import os
import logging
import time
import requests
from datetime import datetime
from app import app
from database import db
from models import Candidate, WhatsAppLog
from cv_parser import parse_cv_text
# Note: job matching is handled externally via n8n, so we no longer
# import or invoke job matching functions here.
import tempfile
from werkzeug.utils import secure_filename

class WhatsAppBot:
    def __init__(self):
        self.api_key = os.getenv('WHATSAPP_API_KEY', '')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'recruitment_verify_token')
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}"
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def send_message(self, to_phone, message):
        """Send WhatsApp message"""
        try:
            url = f"{self.base_url}/messages"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'to': to_phone,
                'type': 'text',
                'text': {'body': message}
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                self.logger.info(f"Message sent to {to_phone}")
                return True
            else:
                self.logger.error(f"Failed to send message to {to_phone}: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending WhatsApp message to {to_phone}: {e}")
            return False

    def download_media(self, media_id):
        """Download media file from WhatsApp"""
        try:
            # Get media URL
            url = f"https://graph.facebook.com/v17.0/{media_id}"
            headers = {'Authorization': f'Bearer {self.api_key}'}
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                self.logger.error(f"Failed to get media URL: {response.text}")
                return None
            
            media_info = response.json()
            media_url = media_info.get('url')
            
            if not media_url:
                return None
            
            # Download media
            media_response = requests.get(media_url, headers=headers)
            if media_response.status_code == 200:
                return media_response.content
            else:
                self.logger.error(f"Failed to download media: {media_response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error downloading media {media_id}: {e}")
            return None

    def is_eu_phone_number(self, phone_number):
        """Check if phone number is from EU"""
        # Remove + and any spaces/dashes
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
        
        # EU country codes (simplified)
        eu_codes = ['44', '49', '33', '39', '34', '31', '32', '48', '43', '45', '46', '47', '41']
        
        for code in eu_codes:
            if clean_phone.startswith(code):
                return True
        return False

    def process_whatsapp_message(self, message_data):
        """Process incoming WhatsApp message"""
        with app.app_context():
            try:
                from_phone = message_data.get('from')
                message_id = message_data.get('id')
                
                # Check if already processed
                existing_log = WhatsAppLog.query.filter_by(
                    phone_number=from_phone,
                    message_id=message_id
                ).first()
                
                if existing_log:
                    self.logger.info(f"WhatsApp message from {from_phone} already processed")
                    return
                
                # Filter EU numbers if required
                if os.getenv('FILTER_EU_ONLY', 'false').lower() == 'true':
                    if not self.is_eu_phone_number(from_phone):
                        self.logger.info(f"Non-EU WhatsApp number filtered: {from_phone}")
                        
                        rejection_msg = """Thank you for your interest in our positions. Currently, we are only considering candidates based in the European Union. We appreciate your understanding."""
                        self.send_message(from_phone, rejection_msg)
                        
                        # Log the filtering
                        log_entry = WhatsAppLog(
                            phone_number=from_phone,
                            message_id=message_id,
                            status='filtered_non_eu'
                        )
                        db.session.add(log_entry)
                        db.session.commit()
                        return
                
                # Check for document attachment
                if message_data.get('type') == 'document':
                    document = message_data.get('document', {})
                    media_id = document.get('id')
                    filename = document.get('filename', 'document')
                    
                    # Check if it's a CV file
                    if any(filename.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.txt']):
                        # Download the document
                        file_content = self.download_media(media_id)
                        
                        if file_content:
                            # Save file
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                            safe_filename = secure_filename(filename)
                            cv_filename = timestamp + safe_filename
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], cv_filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(file_content)
                            
                            # Parse CV
                            cv_data = parse_cv_text(filepath)
                            
                            # Check if candidate exists
                            email = cv_data.get('email')
                            if email:
                                existing_candidate = Candidate.query.filter_by(email=email).first()
                            else:
                                existing_candidate = None
                            
                            if existing_candidate:
                                # Update existing candidate
                                candidate = existing_candidate
                                candidate.phone = from_phone
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
                                    name=cv_data.get('name', f"WhatsApp User {from_phone}"),
                                    email=email or f"whatsapp_{from_phone}@temp.com",
                                    phone=from_phone,
                                    location=cv_data.get('location'),
                                    cv_filename=cv_filename,
                                    cv_text=cv_data.get('text'),
                                    skills=cv_data.get('skills', []),
                                    experience_years=cv_data.get('experience_years'),
                                    education=cv_data.get('education', []),
                                    work_experience=cv_data.get('work_experience', []),
                                    summary=cv_data.get('summary'),
                                    source='whatsapp',
                                    source_reference=from_phone
                                )
                                db.session.add(candidate)
                                db.session.flush()
                            
                            db.session.commit()
                            
                            # Send confirmation.  Matching is handled externally by n8n.
                            confirmation_msg = """Thank you for sending your CV! 📄
We have received your application and it has been added to our candidate database. Our system will automatically match your profile with suitable positions.

If there's a good match, our HR team will contact you shortly.

Best regards,
HR Team"""
                            
                            self.send_message(from_phone, confirmation_msg)
                            
                            # Log success
                            log_entry = WhatsAppLog(
                                phone_number=from_phone,
                                message_id=message_id,
                                candidate_id=candidate.id,
                                status='success'
                            )
                            db.session.add(log_entry)
                            db.session.commit()
                            
                            self.logger.info(f"Successfully processed WhatsApp CV from {from_phone}")
                        
                        else:
                            # Failed to download
                            error_msg = "Sorry, we couldn't download your document. Please try sending it again."
                            self.send_message(from_phone, error_msg)
                            
                            log_entry = WhatsAppLog(
                                phone_number=from_phone,
                                message_id=message_id,
                                status='download_failed'
                            )
                            db.session.add(log_entry)
                            db.session.commit()
                    
                    else:
                        # Not a CV file
                        msg = "Please send your CV in PDF, DOC, or DOCX format for us to process your application."
                        self.send_message(from_phone, msg)
                
                elif message_data.get('type') == 'text':
                    # Text message - request CV
                    text = message_data.get('text', {}).get('body', '')
                    
                    if 'cv' in text.lower() or 'resume' in text.lower() or 'job' in text.lower():
                        welcome_msg = """Hello! 👋

Thank you for your interest in our job opportunities.

To process your application, please send us your CV as a document (PDF, DOC, or DOCX format).

Our automated system will review your profile and match you with suitable positions.

Looking forward to receiving your CV!

Best regards,
HR Team"""
                        
                        self.send_message(from_phone, welcome_msg)
                    
                    # Log text message
                    log_entry = WhatsAppLog(
                        phone_number=from_phone,
                        message_id=message_id,
                        status='text_received'
                    )
                    db.session.add(log_entry)
                    db.session.commit()
                
            except Exception as e:
                self.logger.error(f"Error processing WhatsApp message from {from_phone}: {e}")
                
                # Log error
                log_entry = WhatsAppLog(
                    phone_number=from_phone,
                    message_id=message_id,
                    status='error',
                    error_message=str(e)
                )
                db.session.add(log_entry)
                db.session.commit()

    def handle_webhook(self, data):
        """Handle WhatsApp webhook data"""
        try:
            entry = data.get('entry', [])
            for item in entry:
                changes = item.get('changes', [])
                for change in changes:
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        messages = value.get('messages', [])
                        
                        for message in messages:
                            self.process_whatsapp_message(message)
                            
        except Exception as e:
            self.logger.error(f"Error handling WhatsApp webhook: {e}")

def handle_whatsapp_webhook(data):
    """Entry point for handling WhatsApp webhooks"""
    bot = WhatsAppBot()
    bot.handle_webhook(data)

if __name__ == '__main__':
    # For testing
    bot = WhatsAppBot()
    print("WhatsApp bot initialized")
