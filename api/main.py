from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ollama
import os

router = APIRouter(prefix="/emails", tags=["Emails"])

class LeadRequest(BaseModel):
    first_name: str
    company: str
    role: str
    email: str

@router.post("/generate-draft")
def generate_email_draft(lead: LeadRequest):
    """
    Uses local offline Gemma via Ollama to generate a hyper-personalized 
    cold outreach pitch and saves it to a safe local markdown queue.
    """
    prompt = f"""
    Write a short, professional, and personalized cold email from a software engineering student to an engineering lead or recruiter.
    
    Recipient Name: {lead.first_name}
    Company: {lead.company}
    Role: {lead.role}
    
    Keep the tone polite, concise, and under 100 words.
    """
    
    try:
        # Call local Gemma model via Ollama (100% private & offline)
        response = ollama.chat(
            model='gemma', 
            messages=[{'role': 'user', 'content': prompt}]
        )
        pitch = response['message']['content']
        
        # Human-in-the-loop safety queue: Save as markdown draft
        os.makedirs("drafts", exist_ok=True)
        filename = os.path.join("drafts", f"draft_{lead.company}_{lead.first_name}.md".replace(" ", "_"))
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# To: {lead.first_name} <{lead.email}>\n\n{pitch}")
            
        return {
            "status": "Success",
            "model_used": "gemma",
            "lead": lead.first_name,
            "company": lead.company,
            "draft_file": filename,
            "message": "Pitch successfully generated via local Gemma and queued for review!"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama/Gemma inference error: {str(e)}")