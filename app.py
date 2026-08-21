import os
import json
import sqlite3
import uuid
import secrets
import hashlib
import logging
from logging.handlers import RotatingFileHandler
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
import asyncio

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "app.db")
CLIENT_SECRETS_FILE = os.path.join(DATA_DIR, "client_secret.json")
LOG_FILE = os.path.join(DATA_DIR, "app.log")
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Logging Setup ---
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024, backupCount=1) # 1 MB max
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(file_handler)

logger = logging.getLogger("AIHelper")
logger.info("Application starting up...")

# --- Database Init & Migration ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    settings TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS email_accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email_user TEXT,
                    email_pass TEXT,
                    email_host TEXT
                 )''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails_v2 (
                    id TEXT,
                    user_id TEXT,
                    account TEXT,
                    PRIMARY KEY (id, user_id, account)
                 )''')
                 
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_emails'")
    if c.fetchone():
        try:
            c.execute("INSERT OR IGNORE INTO processed_emails_v2 SELECT id, user_id, account FROM processed_emails")
            c.execute("DROP TABLE processed_emails")
        except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
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
SESSIONS = {} 

class AuthRequest(BaseModel):
    username: str
    password: str

def verify_auth(request: Request):
    token = request.cookies.get("session_token")
    if token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return SESSIONS[token]

@app.get("/api/auth/status")
async def auth_status(request: Request):
    token = request.cookies.get("session_token")
    logged_in = token in SESSIONS
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return {"setup_required": count == 0, "logged_in": logged_in}

@app.post("/api/auth/register")
async def auth_register(req: AuthRequest):
    if len(req.password) < 4:
        return {"error": "Password must be at least 4 characters."}
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user_id = str(uuid.uuid4())
    default_settings = json.dumps({"ai_provider": "gemini", "ai_model": "gemini-1.5-flash", "public_url": ""})
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (id, username, password_hash, settings) VALUES (?, ?, ?, ?)", (user_id, req.username, pwd_hash, default_settings))
        conn.commit()
        logger.info(f"New user registered: {req.username}")
    except sqlite3.IntegrityError:
        return {"error": "Username already exists."}
    finally:
        conn.close()
    return {"status": "success"}

@app.post("/api/auth/login")
async def auth_login(req: AuthRequest, response: Response):
    req_hash = hashlib.sha256(req.password.encode()).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (req.username, req_hash))
    user = c.fetchone()
    conn.close()
    if not user:
        logger.warning(f"Failed login attempt for username: {req.username}")
        return {"error": "Invalid username or password"}
    token = secrets.token_hex(32)
    SESSIONS[token] = user[0]
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400*30)
    logger.info(f"User {req.username} logged in successfully.")
    return {"status": "success"}

@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token in SESSIONS:
        del SESSIONS[token]
        logger.info("A user logged out.")
    response.delete_cookie("session_token")
    return {"status": "success"}

# --- Settings & Accounts ---
class AccountSave(BaseModel):
    id: Optional[str] = None
    email_user: str
    email_pass: str
    email_host: str = "imap.gmail.com"

class SettingsSave(BaseModel):
    ai_provider: str
    ai_model: str
    gemini_api_key: str = ""
    openai_api_key: str = ""
    public_url: str = ""
    custom_prompt: str = ""

@app.get("/api/settings")
async def read_settings(user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    c.execute("SELECT id, email_user, email_pass, email_host FROM email_accounts WHERE user_id=?", (user_id,))
    accounts = [dict(r) for r in c.fetchall()]
    conn.close()
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    return {
        "accounts": accounts,
        "ai_provider": settings.get("ai_provider", "gemini"),
        "ai_model": settings.get("ai_model", "gemini-1.5-flash"),
        "gemini_api_key": settings.get("gemini_api_key", ""),
        "openai_api_key": settings.get("openai_api_key", ""),
        "public_url": settings.get("public_url", ""),
        "custom_prompt": settings.get("custom_prompt", ""),
        "google_auth_ready": os.path.exists(CLIENT_SECRETS_FILE),
        "google_connected": os.path.exists(token_file)
    }

@app.post("/api/settings/ai")
async def save_ai_settings(s: SettingsSave, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    current = json.loads(row[0]) if row and row[0] else {}
    current.update(s.dict())
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(current), user_id))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} saved AI settings.")
    return {"status": "success"}

@app.post("/api/accounts")
async def save_account(acc: AccountSave, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    acc_id = acc.id or str(uuid.uuid4())
    c.execute("SELECT id FROM email_accounts WHERE id=? AND user_id=?", (acc_id, user_id))
    if c.fetchone():
        c.execute("UPDATE email_accounts SET email_user=?, email_pass=?, email_host=? WHERE id=?", (acc.email_user, acc.email_pass, acc.email_host, acc_id))
    else:
        c.execute("INSERT INTO email_accounts (id, user_id, email_user, email_pass, email_host) VALUES (?, ?, ?, ?, ?)", (acc_id, user_id, acc.email_user, acc.email_pass, acc.email_host))
    conn.commit()
    conn.close()
    return {"status": "success", "id": acc_id}

@app.delete("/api/accounts/{acc_id}")
async def delete_account(acc_id: str, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM email_accounts WHERE id=? AND user_id=?", (acc_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}
    
@app.post("/api/reset_history")
async def reset_history(user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} reset their email history.")
    return {"status": "success"}

@app.post("/api/upload_client_secret", dependencies=[Depends(verify_auth)])
async def upload_client_secret(file: UploadFile = File(...)):
    contents = await file.read()
    with open(CLIENT_SECRETS_FILE, "wb") as f:
        f.write(contents)
    logger.info("Google Client Secret JSON uploaded.")
    return {"status": "success"}

class ModelRequest(BaseModel):
    provider: str
    api_key: str

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
        logger.error(f"Error fetching models from {req.provider}: {e}")
        return {"error": str(e)}
    return {"models": models_list}

# --- AI Parsing ---
def extract_event(text: str, date: datetime, subject: str, settings: dict) -> List[dict]:
    custom_instructions = settings.get("custom_prompt", "")
    custom_prompt_text = f"\n    USER CUSTOM INSTRUCTIONS: {custom_instructions}\n" if custom_instructions.strip() else ""
    
    prompt = f"""
    Analyze the following email to see if it contains one or more clear calendar events, appointments, meetings, flights, dinners, deadlines, assignment due dates, or scheduled tasks.
    Email Subject: {subject}
    Email Date: {date.isoformat()}
    {custom_prompt_text}
    If it does NOT contain any scheduled events or deadlines (or if the event violates the USER CUSTOM INSTRUCTIONS), return EXACTLY the string "NO_EVENT".
    If it DOES contain valid events or deadlines, return a JSON ARRAY of objects, where each object has the keys: "title", "date" (ISO 8601), "description". 
    Create a separate event object for EVERY distinct scheduled time mentioned (e.g., Departure time, Event time, Return time). Include location addresses in the description if available.
    For assignments or deadlines without a specific time, default the time to 09:00:00 local time.
    Email Content:
    {text[:2000]}
    """
    provider = settings.get("ai_provider", "gemini")
    model_name = settings.get("ai_model", "gemini-1.5-flash")
    if not model_name:
        model_name = "gemini-1.5-flash"
        
    result = "NO_EVENT"
    try:
        if provider == "gemini":
            genai.configure(api_key=settings.get("gemini_api_key"))
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(prompt).text.strip()
        elif provider == "openai":
            client = openai.OpenAI(api_key=settings.get("openai_api_key"))
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.2)
            result = response.choices[0].message.content.strip()
            
        if "NO_EVENT" in result: return None
        if result.startswith("```json"): result = result[7:-3].strip()
        elif result.startswith("```"): result = result[3:-3].strip()
            
        parsed_data = json.loads(result)
        if isinstance(parsed_data, dict):
            parsed_data = [parsed_data]
            
        valid_events = []
        for e in parsed_data:
            if all(k in e for k in ("title", "date", "description")):
                valid_events.append(e)
                
        return valid_events if valid_events else None
    except Exception as e:
        logger.error(f"AI extraction error ({provider} - {model_name}): {e}")
        raise ValueError(f"AI API Error: {str(e)}") 
    return None

async def process_user_emails(user_id: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    
    c.execute("SELECT * FROM email_accounts WHERE user_id=?", (user_id,))
    accounts = c.fetchall()
    
    if not accounts:
        conn.close()
        return {"error": "No email accounts configured.", "new_events": 0}
        
    total_events_found = 0
    
    for account in accounts:
        email_user = account['email_user']
        email_pass = account['email_pass']
        email_host = account['email_host']
        
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                date_limit = (datetime.now() - timedelta(days=7)).date()
                messages = mailbox.fetch(AND(date_gte=date_limit), limit=20, reverse=True)
                
                for msg in messages:
                    c.execute("SELECT id FROM processed_emails_v2 WHERE id=? AND user_id=? AND account=?", (msg.uid, user_id, email_user))
                    if c.fetchone(): continue
                        
                    text_content = msg.text or msg.html
                    if text_content and len(text_content) > 10:
                        try:
                            event_data_list = extract_event(text_content, msg.date, msg.subject, settings)
                            if event_data_list:
                                for event_data in event_data_list:
                                    event_id = str(uuid.uuid4())
                                    c.execute("""INSERT INTO events (id, user_id, email_id, account, title, date, description, status)
                                                 VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                                              (event_id, user_id, msg.uid, email_user, event_data['title'], event_data['date'], event_data['description']))
                                
                                # Auto-sync to Google Calendar immediately if connected!
                                    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
                                    if os.path.exists(token_file):
                                        try:
                                            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
                                            service = build('calendar', 'v3', credentials=creds)
                                            start_time = datetime.fromisoformat(event_data['date'].replace("Z", "+00:00"))
                                            if start_time.tzinfo is None:
                                                start_time = start_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
                                            end_time = start_time + timedelta(hours=1)
                                            gcal_event = {
                                              'summary': event_data['title'],
                                              'description': event_data['description'],
                                              'start': {'dateTime': start_time.isoformat()},
                                              'end': {'dateTime': end_time.isoformat()}
                                            }
                                            service.events().insert(calendarId='primary', body=gcal_event).execute()
                                            c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
                                            logger.info(f"Background auto-synced event '{event_data['title']}' for {user_id}")
                                        except Exception as e:
                                            logger.error(f"Background auto-sync failed for {user_id}: {e}")
                                    
                                    total_events_found += 1
                        except ValueError as ve:
                            conn.close()
                            return {"error": f"AI Error on {email_user}: {str(ve)}", "new_events": total_events_found}
                    
                    c.execute("INSERT INTO processed_emails_v2 (id, user_id, account) VALUES (?, ?, ?)", (msg.uid, user_id, email_user))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error fetching emails for {email_user}: {e}")
            conn.close()
            return {"error": f"Email connection failed for {email_user}. Check password/host.", "new_events": total_events_found}
            
    conn.close()
    return {"status": "success", "new_events": total_events_found}

@app.get("/api/fetch_emails")
async def fetch_emails_endpoint(user_id: str = Depends(verify_auth)):
    logger.info(f"User {user_id} triggered manual email fetch.")
    return await process_user_emails(user_id)

# --- Background Task Scheduler ---
async def scheduled_email_fetch():
    while True:
        await asyncio.sleep(3600)  # Sleep for 1 hour
        logger.info("Running scheduled hourly email fetch for all users...")
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT DISTINCT user_id FROM email_accounts")
            users = [r[0] for r in c.fetchall()]
            conn.close()
            
            for user_id in users:
                await process_user_emails(user_id)
        except Exception as e:
            logger.error(f"Error in background fetch scheduler: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_email_fetch())

@app.get("/api/events")
async def get_events(user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM events WHERE status='pending' AND user_id=? ORDER BY date DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Google Calendar OAuth & Sync ---
@app.get("/api/auth/google/url")
async def get_google_auth_url(request: Request, user_id: str = Depends(verify_auth)):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "Client secrets missing"}
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s = json.loads(c.fetchone()[0] or "{}")
    base_url = s.get("public_url") or f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/google/callback"
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(prompt='consent')
    s["oauth_state"] = state
    s["oauth_verifier"] = flow.code_verifier
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(s), user_id))
    conn.commit()
    conn.close()
    return {"url": auth_url}

@app.get("/api/auth/google/callback")
async def google_auth_callback(request: Request, state: str):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: secrets missing."
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, settings FROM users")
    user_id = None
    user_settings = {}
    for row in c.fetchall():
        s = json.loads(row[1] or "{}")
        if s.get("oauth_state") == state:
            user_id = row[0]
            user_settings = s
            break
    conn.close()
    if not user_id:
        return "Error: Invalid state or session expired. Try logging in with Google again."
    base_url = user_settings.get("public_url") or f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/google/callback"
    try:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        flow.code_verifier = user_settings.get("oauth_verifier")
        flow.fetch_token(authorization_response=str(request.url))
        token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
        with open(token_file, 'w') as f:
            f.write(flow.credentials.to_json())
    except Exception as e:
        logger.error(f"Google OAuth Failed for user {user_id}: {e}")
    return RedirectResponse(url="/")

@app.post("/api/events/{event_id}/sync")
async def sync_event(event_id: str, user_id: str = Depends(verify_auth)):
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        return {"error": "Google Calendar not connected"}
    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM events WHERE id=? AND user_id=?", (event_id, user_id))
        event = c.fetchone()
        if not event:
            conn.close()
            return {"error": "Event not found"}
        start_time = datetime.fromisoformat(event['date'].replace("Z", "+00:00"))
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
        end_time = start_time + timedelta(hours=1)
        gcal_event = {
          'summary': event['title'],
          'description': event['description'],
          'start': {'dateTime': start_time.isoformat()},
          'end': {'dateTime': end_time.isoformat()}
        }
        service.events().insert(calendarId='primary', body=gcal_event).execute()
        c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/events/{event_id}")
async def dismiss_event(event_id: str, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE events SET status='dismissed' WHERE id=? AND user_id=?", (event_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/logs", dependencies=[Depends(verify_auth)])
async def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": "No logs recorded yet."}
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(size - 1024*1024, 0))
            logs = f.read()
        return {"logs": logs}
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
