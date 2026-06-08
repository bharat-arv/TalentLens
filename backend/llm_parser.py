from groq import Groq
from dotenv import load_dotenv
import os
import json
import httpx
import re

load_dotenv()

# Keep verify=False as requested for office network
http_client = httpx.Client(verify=False)

# ============================================================
# FIX: Handle missing API key gracefully
# ============================================================
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("=" * 50)
    print("WARNING: GROQ_API_KEY environment variable not set.")
    print("LLM features will use fallback data generation.")
    print("=" * 50)
    client = None
else:
    print("GROQ_API_KEY found. Initializing Groq client.")
    client = Groq(
        api_key=api_key,
        http_client=http_client
    )


def analyze_resume(resume_text):
    """Enhanced LLM parsing with fallback for missing API key"""
    
    # If no API key, immediately return fallback data
    if client is None:
        print("No Groq API key configured. Using fallback data generation.")
        return generate_fallback_data(resume_text)
    
    # Validate input
    if not resume_text or len(resume_text.strip()) < 50:
        print(f"Warning: Resume text is too short or empty")
        return generate_fallback_data(resume_text)
    
    if len(resume_text) > 8000:
        resume_text = resume_text[:8000]
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON. Do not include any markdown.

    Extract the following information:

    {{
        "name": "Full name from resume",
        "gender": "male/female/neutral",
        "current_role": "Current job title",
        "total_experience_years": number,
        "location": "City, Country",
        "email": "email address",
        "phone": "phone number",
        "linkedin": "LinkedIn URL",
        "professional_summary": "Brief 2-3 sentence summary",
        "skills": ["Skill1", "Skill2", "Skill3"],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {{
            "degree": "Degree name",
            "institution": "University name",
            "year": "Graduation year"
        }},
        "latest_3_experiences": [
            {{
                "company": "Company name",
                "role": "Job title",
                "duration": "Start - End",
                "responsibilities": ["Achievement 1", "Achievement 2"]
            }}
        ],
        "fit_score": 75,
        "strengths": ["Strength 1", "Strength 2"],
        "areas_for_improvement": ["Improvement 1", "Improvement 2"],
        "recommended_role": "Recommended role",
        "education_raw": ["Full education text"],
        "experience_raw": ["Full experience text"]
    }}

    Resume Text:
    {resume_text[:8000]}

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
        
        # Ensure required fields
        if not parsed_data.get('name'):
            parsed_data['name'] = "Candidate"
        if not parsed_data.get('skills'):
            parsed_data['skills'] = ["Communication", "Teamwork"]
        if not parsed_data.get('latest_3_experiences'):
            parsed_data['latest_3_experiences'] = []
        if not parsed_data.get('fit_score'):
            parsed_data['fit_score'] = 75
        if not parsed_data.get('education_raw'):
            parsed_data['education_raw'] = ["No year mentioned"]
        if not parsed_data.get('experience_raw'):
            parsed_data['experience_raw'] = ["No year mentioned"]
        
        return parsed_data
        
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text)


def generate_fallback_data(resume_text):
    """Fallback when LLM fails or API key missing"""
    
    # Try to extract basic info
    name = "Candidate"
    email = "Not Provided"
    phone = "Not Provided"
    
    # Simple extraction
    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', resume_text[:200] if resume_text else "")
    if name_match:
        name = name_match.group(1)
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text) if resume_text else None
    if email_match:
        email = email_match.group()
    
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text) if resume_text else None
    if phone_match:
        phone = phone_match.group()
    
    return {
        "name": name,
        "gender": "neutral",
        "current_role": "Professional",
        "total_experience_years": 0,
        "location": "Not Specified",
        "email": email,
        "phone": phone,
        "linkedin": "Not Provided",
        "professional_summary": "Professional summary not available" if not resume_text else resume_text[:200],
        "skills": ["Communication", "Teamwork", "Problem Solving"],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
        "latest_3_experiences": [],
        "fit_score": 50,
        "strengths": ["Not available"],
        "areas_for_improvement": ["Complete all sections"],
        "recommended_role": "Entry Level",
        "education_raw": ["No year mentioned"],
        "experience_raw": ["No year mentioned"]
    }