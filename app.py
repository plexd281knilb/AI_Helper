import os
import json
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from imap_tools import MailBox, AND
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/api/events")
async def get_events():
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    email_host = os.getenv("EMAIL_HOST", "imap.gmail.com")

    if not email_user or not email_pass:
        return {"error": "Email credentials not configured."}
        
    events = []
    
    # Connect to Gmail via IMAP
    try:
        with MailBox(email_host).login(email_user, email_pass) as mailbox:
            # Fetch recent emails (e.g., from the last 7 days)
            date_limit = (datetime.now() - timedelta(days=7)).date()
            messages = mailbox.fetch(AND(date_gte=date_limit), limit=15, reverse=True)
            
            for msg in messages:
                text_content = msg.text or msg.html
                if text_content and len(text_content) > 10:
                    event_data = extract_event_with_gemini(text_content, msg.date, msg.subject)
                    if event_data:
                        event_data['id'] = msg.uid
                        events.append(event_data)
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return {"error": "Failed to fetch emails."}

    return events

def extract_event_with_gemini(email_text: str, email_date: datetime, subject: str) -> dict:
    """Uses Gemini to determine if an email contains a calendar event and extract its details."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analyze the following email to see if it contains a clear calendar event (like an appointment, meeting, flight, dinner, etc.).
        Email Subject: {subject}
        Email Date: {email_date.isoformat()}
        
        If it does NOT contain an event, return EXACTLY the string "NO_EVENT".
        If it DOES contain an event, return a JSON object with the following keys:
        - "title": A short title for the event.
        - "date": The date and time of the event in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ). Infer the correct year/month if it says "tomorrow" or "next Tuesday" based on the Email Date.
        - "description": A brief description of the event.
        
        Email Content:
        {email_text[:2000]}
        """
        
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        if "NO_EVENT" in result:
            return None
            
        if result.startswith("```json"):
            result = result[7:-3].strip()
        elif result.startswith("```"):
            result = result[3:-3].strip()
            
        event_dict = json.loads(result)
        
        if all(k in event_dict for k in ("title", "date", "description")):
            return event_dict
            
    except Exception as e:
        print(f"Gemini API error: {e}")
        
    return None
