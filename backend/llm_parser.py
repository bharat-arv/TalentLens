from groq import Groq
from dotenv import load_dotenv
import os
import json
import httpx
import re

load_dotenv()

http_client = httpx.Client(verify=False)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=http_client
)

# Keywords that indicate unprofessional resume
UNPROFESSIONAL_KEYWORDS = {
    'urgent': 30, 'urgently': 35, 'bored': 40, 'bored at home': 45,
    'please hire': 40, 'please hire me': 45, 'genius': 35,
    'can do any job': 40, 'whatsapp': 25, 'instagram': 25,
    'youtube': 20, 'gaming': 25, 'sleeping': 30, 'timepass': 35,
    "don't remember": 30, 'some school': 35, 'some college': 35,
    'need job': 30, 'hardworking': 15, 'tiktok': 25, 'pubg': 25,
    'chicken dinner': 30, 'facebook': 20
}


def analyze_resume(resume_text):
    """Enhanced LLM parsing with better role extraction"""
    
    if not resume_text or len(resume_text.strip()) < 50:
        return generate_fallback_data(resume_text)
    
    # Check for unprofessional content first
    resume_lower = resume_text.lower()
    unprofessional_score = 0
    for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items():
        if keyword in resume_lower:
            unprofessional_score += penalty
    
    if unprofessional_score > 50:
        print(f"⚠️ Highly unprofessional resume detected")
        return generate_fallback_data(resume_text, is_worst=True)
    
    if len(resume_text) > 8000:
        resume_text = resume_text[:8000]
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON.

    Extract the following information carefully:

    {{
        "name": "Full name from resume (first and last name)",
        "current_role": "Current or most recent job title. Look for phrases like 'Senior Engineer', 'Product Manager', 'Data Scientist', etc. Extract exactly as written.",
        "total_experience_years": number (extract years of experience from summary or work history),
        "location": "City, State or City, Country from contact section",
        "email": "email address",
        "phone": "phone number",
        "linkedin": "LinkedIn URL if present",
        "professional_summary": "Professional summary or about section (2-3 sentences)",
        "skills": ["Skill1", "Skill2", "Skill3", "Skill4", "Skill5"],
        "certifications": [],
        "education": {{
            "degree": "Degree name (e.g., B.Tech, MBA, MS)",
            "institution": "University or college name",
            "year": "Graduation year (4-digit number)"
        }},
        "latest_3_experiences": [
            {{
                "company": "Company name",
                "role": "Job title",
                "duration": "Start year - End year (e.g., 2020-2024 or 2022-Present)",
                "responsibilities": ["Key responsibility 1", "Key responsibility 2"]
            }}
        ],
        "fit_score": 75,
        "strengths": ["Strength 1", "Strength 2"],
        "areas_for_improvement": ["Improvement 1", "Improvement 2"],
        "recommended_role": "Best matching job role based on experience",
        "education_raw": ["Full education text with years"],
        "experience_raw": ["Full experience text with years"]
    }}

    Resume Text:
    {resume_text[:4000]}

    Return ONLY the JSON object.
    """
    
    try:
        print("Calling Groq API...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        
        parsed_data = json.loads(result)
        
        # Ensure current_role is extracted
        if not parsed_data.get('current_role') or parsed_data.get('current_role') == 'Professional':
            # Try to extract from resume text if LLM missed it
            role_match = re.search(r'(?:Senior|Lead|Principal|Junior|Associate)?\s*(?:Software|Full Stack|Data|Product|Project|Engineering|Developer|Engineer|Analyst|Manager|Director|Architect)', resume_text, re.IGNORECASE)
            if role_match:
                parsed_data['current_role'] = role_match.group(0).strip()
        
        # Ensure name is extracted
        if not parsed_data.get('name') or parsed_data.get('name') == 'Candidate':
            name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', resume_text[:200], re.MULTILINE)
            if name_match:
                parsed_data['name'] = name_match.group(1)
        
        return parsed_data
        
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text)


def generate_fallback_data(resume_text, is_worst=False):
    """Fallback when LLM fails - with role extraction from text"""
    
    resume_lower = resume_text.lower() if resume_text else ""
    
    # Try to extract role from text
    role = "Professional"
    role_patterns = [
        r'(?:Senior|Lead|Principal|Junior|Associate)?\s*(?:Software|Full Stack|Data|Product|Project|Cloud|DevOps|Frontend|Backend)\s*(?:Engineer|Developer|Architect|Analyst|Manager)',
        r'(?:Python|Java|JavaScript|React|AWS|Azure)\s*(?:Developer|Engineer)',
        r'(?:Machine Learning|Data|AI|GenAI)\s*(?:Engineer|Scientist)',
        r'(?:Product|Project|Program)\s*(?:Manager)',
    ]
    
    for pattern in role_patterns:
        match = re.search(pattern, resume_text, re.IGNORECASE) if resume_text else None
        if match:
            role = match.group(0).strip()
            break
    
    # Try to extract name
    name = "Candidate"
    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', resume_text[:200] if resume_text else "", re.MULTILINE)
    if name_match:
        name = name_match.group(1)
    
    # Try to extract email
    email = "Not Provided"
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text) if resume_text else None
    if email_match:
        email = email_match.group()
    
    # Try to extract phone
    phone = "Not Provided"
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text) if resume_text else None
    if phone_match:
        phone = phone_match.group()
    
    if is_worst:
        return {
            "name": name,
            "current_role": "Not Specified",
            "total_experience_years": 0,
            "location": "Not Specified",
            "email": email,
            "phone": phone,
            "linkedin": "Not Provided",
            "professional_summary": "This resume requires complete rewrite - contains unprofessional content",
            "skills": ["Not specified"],
            "certifications": [],
            "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
            "latest_3_experiences": [],
            "fit_score": 15,
            "strengths": ["Not available"],
            "areas_for_improvement": [
                "Complete resume rewrite required",
                "Remove all unprofessional language",
                "Add proper work experience with dates",
                "Include relevant professional skills"
            ],
            "recommended_role": "Entry Level",
            "education_raw": ["No year mentioned"],
            "experience_raw": ["No year mentioned"],
            "red_flags": {
                "unprofessional_content": True,
                "unprofessional_language": True,
                "desperate_tone": True,
                "missing_contact_info": email == "Not Provided" or phone == "Not Provided",
                "no_work_experience": True,
                "irrelevant_skills": True,
                "missing_dates": True
            },
            "resume_quality_score": 15,
            "resume_quality_verdict": "Worst",
            "quality_observations": [
                "⚠️ CRITICAL: Resume contains extremely unprofessional content",
                "⚠️ No valid work experience with proper details",
                "⚠️ Complete resume rewrite is strongly recommended"
            ]
        }
    else:
        return {
            "name": name,
            "current_role": role,
            "total_experience_years": 0,
            "location": "Not Specified",
            "email": email,
            "phone": phone,
            "linkedin": "Not Provided",
            "professional_summary": "Professional summary not available",
            "skills": ["Communication", "Teamwork", "Problem Solving"],
            "certifications": [],
            "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
            "latest_3_experiences": [],
            "fit_score": 50,
            "strengths": ["Not available"],
            "areas_for_improvement": ["Complete all sections", "Add professional details"],
            "recommended_role": "Entry Level",
            "education_raw": ["No year mentioned"],
            "experience_raw": ["No year mentioned"],
            "red_flags": {
                "missing_contact_info": email == "Not Provided" or phone == "Not Provided",
                "no_work_experience": True,
                "missing_dates": True
            },
            "resume_quality_score": 50,
            "resume_quality_verdict": "Average",
            "quality_observations": [
                "Missing professional contact information",
                "Work experience needs more details",
                "Education section incomplete"
            ]
        }