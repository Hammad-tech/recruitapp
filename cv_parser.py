import os
import logging
import json
import PyPDF2
import docx
from io import BytesIO
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_pdf(filepath):
    """Extract text from PDF file"""
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
    
    except Exception as e:
        logger.error(f"Error extracting text from PDF {filepath}: {e}")
        return ""

def extract_text_from_docx(filepath):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(filepath)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {filepath}: {e}")
        return ""

def extract_text_from_txt(filepath):
    """Extract text from TXT file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read().strip()
    
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(filepath, 'r', encoding='latin-1') as file:
                return file.read().strip()
        except Exception as e:
            logger.error(f"Error extracting text from TXT {filepath}: {e}")
            return ""
    
    except Exception as e:
        logger.error(f"Error extracting text from TXT {filepath}: {e}")
        return ""

def extract_text_from_file(filepath):
    """Extract text from various file formats"""
    if not os.path.exists(filepath):
        logger.error(f"File not found: {filepath}")
        return ""
    
    file_extension = os.path.splitext(filepath)[1].lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(filepath)
    elif file_extension == '.docx':
        return extract_text_from_docx(filepath)
    elif file_extension in ['.txt', '.doc']:  # Basic .doc support as text
        return extract_text_from_txt(filepath)
    else:
        logger.error(f"Unsupported file format: {file_extension}")
        return ""

def parse_cv_with_ai(cv_text):
    """Parse CV text using OpenAI to extract structured information"""
    try:
        system_prompt = """You are an expert CV/Resume parser. Extract the following information from the CV text and return it as a JSON object:

{
  "name": "Full name of the candidate",
  "email": "Email address",
  "phone": "Phone number",
  "location": "Location/Address",
  "summary": "Brief professional summary (2-3 sentences)",
  "skills": ["List of technical and professional skills"],
  "experience_years": "Total years of experience (number only)",
  "education": [
    {
      "degree": "Degree name",
      "institution": "School/University name",
      "year": "Graduation year",
      "field": "Field of study"
    }
  ],
  "work_experience": [
    {
      "title": "Job title",
      "company": "Company name",
      "duration": "Duration (e.g., 2020-2022)",
      "description": "Brief job description"
    }
  ]
}

Extract as much information as possible. If information is not available, use null or empty arrays. Be precise with skills extraction - include both technical and soft skills."""

        user_prompt = f"Please parse this CV and extract the structured information:\n\n{cv_text}"
        
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=2000
        )
        
        result = json.loads(response.choices[0].message.content or '{}')
        
        # Ensure skills is a list
        if not isinstance(result.get('skills', []), list):
            result['skills'] = []
        
        # Ensure education is a list
        if not isinstance(result.get('education', []), list):
            result['education'] = []
        
        # Ensure work_experience is a list
        if not isinstance(result.get('work_experience', []), list):
            result['work_experience'] = []
        
        # Clean and validate experience years
        exp_years = result.get('experience_years')
        if exp_years and isinstance(exp_years, str):
            # Extract number from string
            exp_match = re.search(r'\d+', exp_years)
            result['experience_years'] = int(exp_match.group()) if exp_match else 0
        elif not isinstance(exp_years, int):
            result['experience_years'] = 0
        
        return result
    
    except Exception as e:
        logger.error(f"Error parsing CV with AI: {e}")
        return {
            'name': None,
            'email': None,
            'phone': None,
            'location': None,
            'summary': None,
            'skills': [],
            'experience_years': 0,
            'education': [],
            'work_experience': []
        }

def extract_basic_info_regex(text):
    """Extract basic information using regex as fallback"""
    info = {}
    
    # Email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    info['email'] = email_match.group() if email_match else None
    
    # Phone
    phone_pattern = r'[\+]?[\d\s\-\(\)]{10,}'
    phone_match = re.search(phone_pattern, text)
    info['phone'] = phone_match.group().strip() if phone_match else None
    
    # Simple name extraction (first two words at the beginning)
    lines = text.split('\n')
    potential_name = ""
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if line and not any(char.isdigit() for char in line) and len(line.split()) >= 2:
            potential_name = line
            break
    
    info['name'] = potential_name if potential_name else None
    
    return info

def parse_cv_file(filepath):
    """Parse CV file and return structured data"""
    # Extract text
    cv_text = extract_text_from_file(filepath)
    
    if not cv_text:
        logger.error(f"No text extracted from file: {filepath}")
        return {
            'text': '',
            'name': None,
            'email': None,
            'phone': None,
            'location': None,
            'summary': None,
            'skills': [],
            'experience_years': 0,
            'education': [],
            'work_experience': []
        }
    
    # Parse with AI
    cv_data = parse_cv_with_ai(cv_text)
    cv_data['text'] = cv_text
    
    # Fallback to regex if AI parsing failed for critical fields
    if not cv_data.get('email') or not cv_data.get('name'):
        basic_info = extract_basic_info_regex(cv_text)
        
        if not cv_data.get('email') and basic_info.get('email'):
            cv_data['email'] = basic_info['email']
        
        if not cv_data.get('name') and basic_info.get('name'):
            cv_data['name'] = basic_info['name']
        
        if not cv_data.get('phone') and basic_info.get('phone'):
            cv_data['phone'] = basic_info['phone']
    
    logger.info(f"Successfully parsed CV: {cv_data.get('name', 'Unknown')} - {cv_data.get('email', 'No email')}")
    
    return cv_data

def parse_cv_text(filepath):
    """Alias for parse_cv_file for backward compatibility"""
    return parse_cv_file(filepath)

def extract_job_requirements(requirements_text):
    """Extract structured requirements from job posting using AI"""
    try:
        system_prompt = """You are an expert job requirements parser. Extract the following information from the job requirements text and return it as a JSON object:

{
  "required_skills": ["List of absolutely required technical and professional skills"],
  "preferred_skills": ["List of nice-to-have skills"],
  "experience_level": "entry|mid|senior",
  "min_experience_years": "Minimum years of experience required (number only)",
  "education_level": "Required education level",
  "certifications": ["Required certifications if any"]
}

Focus on extracting concrete skills and requirements. Separate must-have from nice-to-have skills."""

        user_prompt = f"Please parse these job requirements and extract the structured information:\n\n{requirements_text}"
        
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result = json.loads(response.choices[0].message.content or '{}')
        
        # Ensure required fields are lists
        if not isinstance(result.get('required_skills', []), list):
            result['required_skills'] = []
        
        if not isinstance(result.get('preferred_skills', []), list):
            result['preferred_skills'] = []
        
        if not isinstance(result.get('certifications', []), list):
            result['certifications'] = []
        
        return result
    
    except Exception as e:
        logger.error(f"Error parsing job requirements with AI: {e}")
        return {
            'required_skills': [],
            'preferred_skills': [],
            'experience_level': 'mid',
            'min_experience_years': 0,
            'education_level': None,
            'certifications': []
        }

if __name__ == '__main__':
    # Test the CV parser
    test_file = input("Enter path to CV file: ")
    if os.path.exists(test_file):
        result = parse_cv_file(test_file)
        print(json.dumps(result, indent=2))
    else:
        print("File not found")
