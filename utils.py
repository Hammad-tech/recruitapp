import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

def validate_email(email: str) -> bool:
    """Validate email address format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return False
    
    # Remove spaces, dashes, parentheses
    clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check if it's a valid international format
    pattern = r'^\+?[\d]{10,15}$'
    return bool(re.match(pattern, clean_phone))

def clean_filename(filename: str) -> str:
    """Clean and secure filename"""
    if not filename:
        return "unnamed_file"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Secure the filename
    secure_name = secure_filename(filename)
    
    # If secure_filename returns empty string, provide default
    if not secure_name:
        ext = os.path.splitext(filename)[1]
        secure_name = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    
    return secure_name

def extract_skills_from_text(text: str) -> List[str]:
    """Extract potential skills from text using simple keyword matching"""
    if not text:
        return []
    
    # Common skill keywords
    skill_patterns = [
        # Programming languages
        r'\b(?:Python|Java|JavaScript|C\+\+|C#|PHP|Ruby|Go|Rust|Swift|Kotlin)\b',
        
        # Web technologies
        r'\b(?:HTML|CSS|React|Angular|Vue|Node\.js|Django|Flask|Spring|Laravel)\b',
        
        # Databases
        r'\b(?:MySQL|PostgreSQL|MongoDB|SQLite|Oracle|SQL Server|Redis)\b',
        
        # Cloud and DevOps
        r'\b(?:AWS|Azure|Google Cloud|Docker|Kubernetes|Jenkins|Git|GitHub|GitLab)\b',
        
        # Data Science
        r'\b(?:Machine Learning|Deep Learning|TensorFlow|PyTorch|Pandas|NumPy|Scikit-learn)\b',
        
        # Other technical skills
        r'\b(?:Linux|Windows|macOS|Agile|Scrum|REST API|GraphQL|Microservices)\b',
        
        # Soft skills
        r'\b(?:Leadership|Communication|Project Management|Team Lead|Problem Solving)\b'
    ]
    
    skills = []
    text_upper = text.upper()
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        skills.extend(matches)
    
    # Remove duplicates and return
    return list(set(skills))

def calculate_experience_years(work_experience: List[Dict]) -> int:
    """Calculate total years of experience from work history"""
    if not work_experience:
        return 0
    
    total_months = 0
    
    for job in work_experience:
        duration = job.get('duration', '')
        if not duration:
            continue
        
        # Try to parse duration like "2020-2022", "Jan 2020 - Dec 2021", etc.
        years = extract_years_from_duration(duration)
        if years:
            total_months += years * 12
    
    return max(0, total_months // 12)

def extract_years_from_duration(duration: str) -> int:
    """Extract years from duration string"""
    if not duration:
        return 0
    
    # Look for patterns like "2020-2022", "2020 - 2022"
    year_pattern = r'(\d{4})\s*[-–]\s*(\d{4})'
    match = re.search(year_pattern, duration)
    
    if match:
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        return max(0, end_year - start_year)
    
    # Look for single year with "present", "current", etc.
    current_pattern = r'(\d{4})\s*[-–]\s*(?:present|current|now)'
    match = re.search(current_pattern, duration, re.IGNORECASE)
    
    if match:
        start_year = int(match.group(1))
        current_year = datetime.now().year
        return max(0, current_year - start_year)
    
    return 0

def format_phone_number(phone: str) -> str:
    """Format phone number to standard international format"""
    if not phone:
        return ""
    
    # Remove all non-digit characters except +
    clean_phone = re.sub(r'[^\d\+]', '', phone)
    
    # If it doesn't start with +, add it
    if not clean_phone.startswith('+'):
        clean_phone = '+' + clean_phone
    
    return clean_phone

def is_cv_file(filename: str) -> bool:
    """Check if file is a potential CV based on extension"""
    if not filename:
        return False
    
    allowed_extensions = {'.pdf', '.doc', '.docx', '.txt'}
    file_extension = os.path.splitext(filename.lower())[1]
    
    return file_extension in allowed_extensions

def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    if not filename:
        return ""
    
    return os.path.splitext(filename.lower())[1]

def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to specified length with ellipsis"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def sanitize_html(text: str) -> str:
    """Basic HTML sanitization for display"""
    if not text:
        return ""
    
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

def parse_salary_range(salary_text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse salary range from text"""
    if not salary_text:
        return None, None
    
    # Remove currency symbols and common words
    clean_text = re.sub(r'[$£€,]', '', salary_text)
    clean_text = re.sub(r'\b(?:per|year|annual|salary|range)\b', '', clean_text, flags=re.IGNORECASE)
    
    # Look for range patterns like "50000-70000" or "50k-70k"
    range_pattern = r'(\d+)(?:k)?\s*[-–]\s*(\d+)(?:k)?'
    match = re.search(range_pattern, clean_text, re.IGNORECASE)
    
    if match:
        min_val = int(match.group(1))
        max_val = int(match.group(2))
        
        # Handle 'k' notation
        if 'k' in match.group(0).lower():
            min_val *= 1000
            max_val *= 1000
        
        return min_val, max_val
    
    # Look for single value
    single_pattern = r'(\d+)(?:k)?'
    match = re.search(single_pattern, clean_text, re.IGNORECASE)
    
    if match:
        val = int(match.group(1))
        if 'k' in match.group(0).lower():
            val *= 1000
        
        return val, val
    
    return None, None

def get_country_from_phone(phone: str) -> Optional[str]:
    """Get country name from phone number prefix"""
    if not phone:
        return None
    
    # Remove + and get first few digits
    clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    
    # Country code mapping (simplified)
    country_codes = {
        '44': 'United Kingdom',
        '49': 'Germany',
        '33': 'France',
        '39': 'Italy',
        '34': 'Spain',
        '31': 'Netherlands',
        '32': 'Belgium',
        '48': 'Poland',
        '43': 'Austria',
        '45': 'Denmark',
        '46': 'Sweden',
        '47': 'Norway',
        '41': 'Switzerland',
        '1': 'United States/Canada',
    }
    
    for code, country in country_codes.items():
        if clean_phone.startswith(code):
            return country
    
    return None

def log_processing_time(func):
    """Decorator to log function processing time"""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.info(f"{func.__name__} completed in {processing_time:.2f} seconds")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            logger.error(f"{func.__name__} failed after {processing_time:.2f} seconds: {e}")
            raise
    
    return wrapper

class ConfigHelper:
    """Helper class for configuration management"""
    
    @staticmethod
    def get_email_config():
        """Get email configuration from environment"""
        return {
            'imap_server': os.getenv('IMAP_SERVER', 'imap.gmail.com'),
            'imap_port': int(os.getenv('IMAP_PORT', '993')),
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'email_user': os.getenv('EMAIL_USER', ''),
            'email_password': os.getenv('EMAIL_PASSWORD', ''),
            'filter_eu_only': os.getenv('FILTER_EU_ONLY', 'false').lower() == 'true'
        }
    
    @staticmethod
    def get_whatsapp_config():
        """Get WhatsApp configuration from environment"""
        return {
            'api_key': os.getenv('WHATSAPP_API_KEY', ''),
            'phone_number_id': os.getenv('WHATSAPP_PHONE_NUMBER_ID', ''),
            'verify_token': os.getenv('WHATSAPP_VERIFY_TOKEN', 'recruitment_verify_token'),
            'filter_eu_only': os.getenv('FILTER_EU_ONLY', 'false').lower() == 'true'
        }
    
    @staticmethod
    def get_openai_config():
        """Get OpenAI configuration from environment"""
        return {
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'model': 'gpt-5'  # Latest model as per blueprint
        }

# Validation helpers
def validate_candidate_data(data: Dict) -> List[str]:
    """Validate candidate data and return list of errors"""
    errors = []
    
    if not data.get('name'):
        errors.append("Name is required")
    
    if not data.get('email'):
        errors.append("Email is required")
    elif not validate_email(data['email']):
        errors.append("Invalid email format")
    
    phone = data.get('phone')
    if phone and not validate_phone(phone):
        errors.append("Invalid phone number format")
    
    return errors

def validate_job_data(data: Dict) -> List[str]:
    """Validate job data and return list of errors"""
    errors = []
    
    if not data.get('title'):
        errors.append("Job title is required")
    
    if not data.get('description'):
        errors.append("Job description is required")
    
    if not data.get('requirements'):
        errors.append("Job requirements are required")
    
    salary_min = data.get('salary_min')
    salary_max = data.get('salary_max')
    
    if salary_min and salary_max and salary_min > salary_max:
        errors.append("Minimum salary cannot be greater than maximum salary")
    
    return errors
