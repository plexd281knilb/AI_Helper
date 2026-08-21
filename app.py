import os
import json
import sqlite3
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Request, Response, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from imap_tools import MailBox, AND
import google.generativeai as genai
import openai
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DB_FILE = os.path.join(DATA_DIR, "events.db")
CLIENT_SECRETS_FILE = os.path.join(DATA_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(DATA_DIR, "token.json")
AUTH_FILE = os.path.join(DATA_DIR, "auth.json")
SCOPES = ['https://www.googleapis.com/auth/calendar']

os.makedirs(DATA_DIR, exist_ok=True)

# --- Database Init ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails (
                    id TEXT PRIMARY KEY,
                    account TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    email_id TEXT,
                    account TEXT,
                    title TEXT,
                    date TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending'
                 )''')
    conn.commit()
    conn.close()

init_db()

# --- Authentication Logic ---
SESSIONS = set()

class AuthRequest(BaseModel):
    password: str

def get_password_hash():
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            return json.load(f).get("password_hash")
    return None

def verify_auth(request: Request):
    if not get_password_hash():
        return # Skip auth if password isn't set up yet
    token = request.cookies.get("session_token")
    if token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/api/auth/status")
async def auth_status(request: Request):
    has_pass = get_password_hash() is not None
    token = request.cookies.get("session_token")
    logged_in = token in SESSIONS
    return {"setup_required": not has_pass, "logged_in": logged_in}

@app.post("/api/auth/setup")
async def auth_setup(req: AuthRequest):
    if get_password_hash() is not None:
        return {"error": "Password already set."}
    if len(req.password) < 4:
        return {"error": "Password must be at least 4 characters."}
        
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    with open(AUTH_FILE, "w") as f:
        json.dump({"password_hash": pwd_hash}, f)
    return {"status": "success"}

@app.post("/api/auth/login")
async def auth_login(req: AuthRequest, response: Response):
    correct_hash = get_password_hash()
    req_hash = hashlib.sha256(req.password.encode()).hexdigest()
    
    if not correct_hash or req_hash != correct_hash:
        return {"error": "Invalid password"}
    
    token = secrets.token_hex(32)
    SESSIONS.add(token)
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400*30) # 30 days
    return {"status": "success"}

@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token in SESSIONS:
        SESSIONS.remove(token)
    response.delete_cookie("session_token")
    return {"status": "success"}

# --- Settings & Models ---
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

@app.get("/api/settings", dependencies=[Depends(verify_auth)])
async def read_settings():
    settings = get_settings()
    return {
        "accounts": settings.get("accounts", []),
        "ai_provider": settings.get("ai_provider", "gemini"),
        "ai_model": settings.get("ai_model", "gemini-1.5-flash"),
        "gemini_api_key": settings.get("gemini_api_key", ""),
        "openai_api_key": settings.get("openai_api_key", ""),
        "google_auth_ready": os.path.exists(CLIENT_SECRETS_FILE),
        "google_connected": os.path.exists(TOKEN_FILE)
    }

@app.post("/api/settings", dependencies=[Depends(verify_auth)])
async def save_settings(settings: Settings):
    new_settings = {
        "accounts": [acc.dict() for acc in settings.accounts],
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "gemini_api_key": settings.gemini_api_key,
        "openai_api_key": settings.openai_api_key
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(new_settings, f)
    return {"status": "success"}

@app.post("/api/upload_client_secret", dependencies=[Depends(verify_auth)])
async def upload_client_secret(file: UploadFile = File(...)):
    contents = await file.read()
    with open(CLIENT_SECRETS_FILE, "wb") as f:
        f.write(contents)
    return {"status": "success"}

@app.post("/api/models", dependencies=[Depends(verify_auth)])
async def get_models(req: ModelRequest):
    api_key = req.api_key
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
        return {"error": str(e)}
    return {"models": models_list}

# --- AI Parsing ---
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

@app.get("/api/fetch_emails", dependencies=[Depends(verify_auth)])
async def fetch_emails():
    settings = get_settings()
    accounts = settings.get("accounts", [])
    if not accounts:
        return {"error": "No email accounts configured."}
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    new_events_found = 0
    
    for account in accounts:
        email_user = account.get("email_user")
        email_pass = account.get("email_pass")
        email_host = account.get("email_host", "imap.gmail.com")
        
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                date_limit = (datetime.now() - timedelta(days=7)).date()
                messages = mailbox.fetch(AND(date_gte=date_limit), limit=20, reverse=True)
                
                for msg in messages:
                    c.execute("SELECT id FROM processed_emails WHERE id=? AND account=?", (msg.uid, email_user))
                    if c.fetchone():
                        continue
                        
                    text_content = msg.text or msg.html
                    if text_content and len(text_content) > 10:
                        event_data = extract_event(text_content, msg.date, msg.subject, settings)
                        if event_data:
                            event_id = str(uuid.uuid4())
                            c.execute("""INSERT INTO events (id, email_id, account, title, date, description, status)
                                         VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                                      (event_id, msg.uid, email_user, event_data['title'], event_data['date'], event_data['description']))
                            new_events_found += 1
                    
                    c.execute("INSERT INTO processed_emails (id, account) VALUES (?, ?)", (msg.uid, email_user))
                    conn.commit()
        except Exception as e:
            print(f"Error fetching emails for {email_user}: {e}")
            
    conn.close()
    return {"status": "success", "new_events": new_events_found}

@app.get("/api/events", dependencies=[Depends(verify_auth)])
async def get_events():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM events WHERE status='pending' ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Google Calendar OAuth & Sync ---
@app.get("/api/auth/google/url", dependencies=[Depends(verify_auth)])
async def get_google_auth_url(request: Request):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "Client secrets file missing"}
    
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/google/callback"
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, _ = flow.authorization_url(prompt='consent')
    return {"url": auth_url}

@app.get("/api/auth/google/callback")
async def google_auth_callback(request: Request):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: secrets missing."
        
    redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/google/callback"
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    authorization_response = str(request.url)
    flow.fetch_token(authorization_response=authorization_response)
    
    creds = flow.credentials
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
        
    return RedirectResponse(url="/")

@app.post("/api/events/{event_id}/sync", dependencies=[Depends(verify_auth)])
async def sync_event(event_id: str):
    if not os.path.exists(TOKEN_FILE):
        return {"error": "Google Calendar not connected"}
        
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM events WHERE id=?", (event_id,))
    event = c.fetchone()
    if not event:
        conn.close()
        return {"error": "Event not found"}
        
    start_time = datetime.fromisoformat(event['date'].replace("Z", "+00:00"))
    end_time = start_time + timedelta(hours=1)
    
    gcal_event = {
      'summary': event['title'],
      'description': event['description'],
      'start': {'dateTime': start_time.isoformat()},
      'end': {'dateTime': end_time.isoformat()}
    }
    
    try:
        service.events().insert(calendarId='primary', body=gcal_event).execute()
        c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}

@app.delete("/api/events/{event_id}", dependencies=[Depends(verify_auth)])
async def dismiss_event(event_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE events SET status='dismissed' WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
