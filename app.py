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
DB_FILE = os.path.join(DATA_DIR, "app.db")
CLIENT_SECRETS_FILE = os.path.join(DATA_DIR, "client_secret.json")
SCOPES = ['https://www.googleapis.com/auth/calendar']

os.makedirs(DATA_DIR, exist_ok=True)

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
                 
    # Legacy migration (if upgrading from single-user events.db)
    legacy_db = os.path.join(DATA_DIR, "events.db")
    if os.path.exists(legacy_db):
        try:
            lc = sqlite3.connect(legacy_db).cursor()
            lc.execute("SELECT * FROM events")
            for row in lc.fetchall():
                try:
                    c.execute("INSERT INTO events (id, user_id, email_id, account, title, date, description, status) VALUES (?, 'admin', ?, ?, ?, ?, ?, ?)", 
                              (row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
                except: pass
            lc.execute("SELECT * FROM processed_emails")
            for row in lc.fetchall():
                try:
                    c.execute("INSERT INTO processed_emails (id, user_id, account) VALUES (?, 'admin', ?)", (row[0], row[1]))
                except: pass
            os.rename(legacy_db, legacy_db + ".bak")
        except Exception as e:
            print("Legacy DB migration skipped/failed:", e)
            
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

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
        return {"error": "Invalid username or password"}
    
    token = secrets.token_hex(32)
    SESSIONS[token] = user[0]
    response.set_cookie(key="session_token", value=token, httponly=True, max_age=86400*30)
    return {"status": "success"}

@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token in SESSIONS:
        del SESSIONS[token]
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
    
    # Check google auth
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
    else:
        c.execute("INSERT INTO email_accounts (id, user_id, email_user, email_pass, email_host) VALUES (?, ?, ?, ?, ?)",
                  (acc_id, user_id, acc.email_user, acc.email_pass, acc.email_host))
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

@app.post("/api/upload_client_secret", dependencies=[Depends(verify_auth)])
async def upload_client_secret(file: UploadFile = File(...)):
    contents = await file.read()
    with open(CLIENT_SECRETS_FILE, "wb") as f:
        f.write(contents)
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
    except Exception as e: print(f"AI error: {e}")
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
        return {"error": "No email accounts configured."}
        
    new_events_found = 0
    for account in accounts:
        email_user = account['email_user']
        email_pass = account['email_pass']
        email_host = account['email_host']
        
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                date_limit = (datetime.now() - timedelta(days=7)).date()
                messages = mailbox.fetch(AND(date_gte=date_limit), limit=20, reverse=True)
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
                            new_events_found += 1
                    
                    c.execute("INSERT INTO processed_emails (id, user_id, account) VALUES (?, ?, ?)", (msg.uid, user_id, email_user))
                    conn.commit()
        except Exception as e:
            print(f"Error fetching emails for {email_user}: {e}")
            
    conn.close()
    return {"status": "success", "new_events": new_events_found}

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
    conn.close()
    
    base_url = s.get("public_url") or f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/google/callback"
    
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    # Pass user_id in state
    auth_url, _ = flow.authorization_url(prompt='consent', state=user_id)
    return {"url": auth_url}

@app.get("/api/auth/google/callback")
async def google_auth_callback(request: Request, state: str):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: secrets missing."
        
    # State contains the user_id
    user_id = state
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s = json.loads(c.fetchone()[0] or "{}")
    conn.close()
    
    base_url = s.get("public_url") or f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/google/callback"
    
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow.fetch_token(authorization_response=str(request.url))
    
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    with open(token_file, 'w') as f:
        f.write(flow.credentials.to_json())
        
    return RedirectResponse(url="/")

@app.post("/api/events/{event_id}/sync")
async def sync_event(event_id: str, user_id: str = Depends(verify_auth)):
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        return {"error": "Google Calendar not connected"}
        
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
    
    try:
        service.events().insert(calendarId='primary', body=gcal_event).execute()
        c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}

@app.delete("/api/events/{event_id}")
async def dismiss_event(event_id: str, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE events SET status='dismissed' WHERE id=? AND user_id=?", (event_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}
