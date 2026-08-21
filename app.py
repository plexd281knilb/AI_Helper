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

# Capture all logs (including uvicorn)
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
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    account TEXT
                 )''')
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
SESSIONS = {} # token -> user_id

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
        c.execute("INSERT INTO users (id, username, password_hash, settings) VALUES (?, ?, ?, ?)", 
                  (user_id, req.username, pwd_hash, default_settings))
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
        c.execute("UPDATE email_accounts SET email_user=?, email_pass=?, email_host=? WHERE id=?",
                  (acc.email_user, acc.email_pass, acc.email_host, acc_id))
        logger.info(f"User {user_id} updated email account {acc.email_user}")
    else:
        c.execute("INSERT INTO email_accounts (id, user_id, email_user, email_pass, email_host) VALUES (?, ?, ?, ?, ?)",
                  (acc_id, user_id, acc.email_user, acc.email_pass, acc.email_host))
        logger.info(f"User {user_id} added email account {acc.email_user}")
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
    logger.info(f"User {user_id} deleted an email account.")
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
def extract_event(text: str, date: datetime, subject: str, settings: dict) -> dict:
    prompt = f"""
    Analyze the following email to see if it contains a clear calendar event (appointment, meeting, flight, dinner, etc.).
    Email Subject: {subject}
    Email Date: {date.isoformat()}
    If it does NOT contain an event, return EXACTLY the string "NO_EVENT".
    If it DOES contain an event, return a JSON object with keys: "title", "date" (ISO 8601), "description".
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
            result = model.generate_content(prompt).text.strip()
        elif provider == "openai":
            client = openai.OpenAI(api_key=settings.get("openai_api_key"))
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.2)
            result = response.choices[0].message.content.strip()
            
        if "NO_EVENT" in result: return None
        if result.startswith("```json"): result = result[7:-3].strip()
        elif result.startswith("```"): result = result[3:-3].strip()
            
        event_dict = json.loads(result)
        if all(k in event_dict for k in ("title", "date", "description")): return event_dict
    except Exception as e:
        logger.error(f"AI extraction error ({provider}): {e}")
    return None

@app.get("/api/fetch_emails")
async def fetch_emails(user_id: str = Depends(verify_auth)):
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
        logger.warning(f"User {user_id} tried to fetch emails but has no accounts.")
        return {"error": "No email accounts configured."}
        
    total_events_found = 0
    logger.info(f"User {user_id} initiated email fetch for {len(accounts)} accounts.")
    
    for account in accounts:
        email_user = account['email_user']
        email_pass = account['email_pass']
        email_host = account['email_host']
        
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                date_limit = (datetime.now() - timedelta(days=7)).date()
                messages = mailbox.fetch(AND(date_gte=date_limit), limit=20, reverse=True)
                
                new_found_this_acc = 0
                for msg in messages:
                    c.execute("SELECT id FROM processed_emails WHERE id=? AND user_id=? AND account=?", (msg.uid, user_id, email_user))
                    if c.fetchone(): continue
                        
                    text_content = msg.text or msg.html
                    if text_content and len(text_content) > 10:
                        event_data = extract_event(text_content, msg.date, msg.subject, settings)
                        if event_data:
                            event_id = str(uuid.uuid4())
                            c.execute("""INSERT INTO events (id, user_id, email_id, account, title, date, description, status)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
                                      (event_id, user_id, msg.uid, email_user, event_data['title'], event_data['date'], event_data['description']))
                            new_found_this_acc += 1
                            total_events_found += 1
                    
                    c.execute("INSERT INTO processed_emails (id, user_id, account) VALUES (?, ?, ?)", (msg.uid, user_id, email_user))
                    conn.commit()
                logger.info(f"Successfully processed emails for {email_user}. Found {new_found_this_acc} new events.")
        except Exception as e:
            logger.error(f"Error fetching emails for {email_user}: {e}")
            
    conn.close()
    return {"status": "success", "new_events": total_events_found}

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
    
    # Save the PKCE verifier and state so we can complete the flow
    s["oauth_state"] = state
    s["oauth_verifier"] = flow.code_verifier
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(s), user_id))
    conn.commit()
    conn.close()
    
    return {"url": auth_url}

@app.get("/api/auth/google/callback")
async def google_auth_callback(request: Request, state: str):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        logger.error("OAuth callback hit, but client secrets are missing.")
        return "Error: secrets missing."
        
    # Find user by state
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
        logger.error(f"Google OAuth Failed: Invalid state {state}")
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
        logger.info(f"Google Calendar OAuth successful for user {user_id}")
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
        logger.info(f"User {user_id} synced event '{event['title']}' to Google Calendar.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Sync event failed for user {user_id}: {e}")
        return {"error": str(e)}

@app.delete("/api/events/{event_id}")
async def dismiss_event(event_id: str, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE events SET status='dismissed' WHERE id=? AND user_id=?", (event_id, user_id))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} dismissed an event.")
    return {"status": "success"}

# --- Logs Endpoint ---
@app.get("/api/logs", dependencies=[Depends(verify_auth)])
async def get_logs():
    if not os.path.exists(LOG_FILE):
        return {"logs": "No logs recorded yet."}
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(size - 1024*1024, 0)) # Last 1MB
            logs = f.read()
        return {"logs": logs}
    except Exception as e:
        return {"logs": f"Error reading logs: {e}"}

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
