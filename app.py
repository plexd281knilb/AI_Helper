import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from imap_tools import MailBox, AND
import google.generativeai as genai
import openai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
os.makedirs(DATA_DIR, exist_ok=True)

class Account(BaseModel):
    email_user: str
    email_pass: str
    email_host: str = "imap.gmail.com"

class Settings(BaseModel):
    accounts: List[Account] = []
    ai_provider: str = "gemini" 
    ai_model: str = "gemini-1.5-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    
class ModelRequest(BaseModel):
    provider: str
    api_key: str

def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            if "email_user" in data and "accounts" not in data:
                data["accounts"] = [{"email_user": data["email_user"], "email_pass": data.get("email_pass", ""), "email_host": "imap.gmail.com"}]
            if "ai_provider" not in data:
                data["ai_provider"] = "gemini"
                data["ai_model"] = "gemini-1.5-flash"
            return data
    return {
        "accounts": [],
        "ai_provider": "gemini",
        "ai_model": "gemini-1.5-flash",
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", "")
    }

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/api/settings")
async def read_settings():
    settings = get_settings()
    for acc in settings.get("accounts", []):
        if acc.get("email_pass"):
            acc["email_pass"] = "*" * 8
            
    return {
        "accounts": settings.get("accounts", []),
        "ai_provider": settings.get("ai_provider", "gemini"),
        "ai_model": settings.get("ai_model", "gemini-1.5-flash"),
        "gemini_api_key": "*" * 8 if settings.get("gemini_api_key") else "",
        "openai_api_key": "*" * 8 if settings.get("openai_api_key") else ""
    }

@app.post("/api/settings")
async def save_settings(settings: Settings):
    current_settings = get_settings()
    
    for i, acc in enumerate(settings.accounts):
        if acc.email_pass == "*" * 8:
            if i < len(current_settings.get("accounts", [])):
                acc.email_pass = current_settings["accounts"][i]["email_pass"]

    new_settings = {
        "accounts": [acc.dict() for acc in settings.accounts],
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "gemini_api_key": settings.gemini_api_key if settings.gemini_api_key != "*" * 8 else current_settings.get("gemini_api_key", ""),
        "openai_api_key": settings.openai_api_key if settings.openai_api_key != "*" * 8 else current_settings.get("openai_api_key", "")
    }
    
    with open(SETTINGS_FILE, "w") as f:
        json.dump(new_settings, f)
    return {"status": "success"}

@app.post("/api/models")
async def get_models(req: ModelRequest):
    api_key = req.api_key
    if api_key == "*" * 8:
        current_settings = get_settings()
        if req.provider == "gemini":
            api_key = current_settings.get("gemini_api_key", "")
        elif req.provider == "openai":
            api_key = current_settings.get("openai_api_key", "")
            
    if not api_key:
        return {"models": []}
        
    models_list = []
    try:
        if req.provider == "gemini":
            genai.configure(api_key=api_key)
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    models_list.append(name)
        elif req.provider == "openai":
            client = openai.OpenAI(api_key=api_key)
            models_response = client.models.list()
            for m in models_response.data:
                if "gpt" in m.id or "o1" in m.id:
                    models_list.append(m.id)
            models_list.sort(reverse=True)
    except Exception as e:
        print(f"Error fetching models: {e}")
        return {"error": str(e)}
        
    return {"models": models_list}

def extract_event(text: str, date: datetime, subject: str, settings: dict) -> dict:
    prompt = f"""
    Analyze the following email to see if it contains a clear calendar event (appointment, meeting, flight, dinner, etc.).
    Email Subject: {subject}
    Email Date: {date.isoformat()}
    
    If it does NOT contain an event, return EXACTLY the string "NO_EVENT".
    If it DOES contain an event, return a JSON object with the following keys:
    - "title": A short title for the event.
    - "date": The date and time of the event in ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ). Infer the correct year/month if it says "tomorrow" or "next Tuesday" based on the Email Date.
    - "description": A brief description of the event.
    
    Email Content:
    {text[:2000]}
    """
    
    provider = settings.get("ai_provider", "gemini")
    model_name = settings.get("ai_model", "gemini-1.5-flash")
    
    result = "NO_EVENT"
    
    try:
        if provider == "gemini":
            genai.configure(api_key=settings.get("gemini_api_key"))
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            result = response.text.strip()
        elif provider == "openai":
            client = openai.OpenAI(api_key=settings.get("openai_api_key"))
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            result = response.choices[0].message.content.strip()
            
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
        print(f"AI API error ({provider}): {e}")
        
    return None

@app.get("/api/events")
async def get_events():
    settings = get_settings()
    accounts = settings.get("accounts", [])
    
    if not accounts:
        return {"error": "No email accounts configured. Please visit Settings."}
        
    if settings.get("ai_provider") == "gemini" and not settings.get("gemini_api_key"):
        return {"error": "Gemini API key not configured."}
    if settings.get("ai_provider") == "openai" and not settings.get("openai_api_key"):
        return {"error": "OpenAI API key not configured."}
        
    events = []
    
    for account in accounts:
        email_user = account.get("email_user")
        email_pass = account.get("email_pass")
        email_host = account.get("email_host", "imap.gmail.com")
        
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                date_limit = (datetime.now() - timedelta(days=7)).date()
                messages = mailbox.fetch(AND(date_gte=date_limit), limit=15, reverse=True)
                
                for msg in messages:
                    text_content = msg.text or msg.html
                    if text_content and len(text_content) > 10:
                        event_data = extract_event(text_content, msg.date, msg.subject, settings)
                        if event_data:
                            event_data['id'] = f"{email_user}-{msg.uid}"
                            event_data['account'] = email_user
                            events.append(event_data)
        except Exception as e:
            print(f"Error fetching emails for {email_user}: {e}")
            
    return events
