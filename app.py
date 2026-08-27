import os
import json
import sqlite3
import uuid
import secrets
import hashlib
import logging
import re
import urllib.request
from html import unescape
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

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    settings TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT,
                    expires REAL
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS email_accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email_user TEXT,
                    email_pass TEXT,
                    email_host TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    account TEXT,
                    title TEXT,
                    date TEXT,
                    description TEXT,
                    status TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS processed_emails_v2 (
                    id TEXT,
                    user_id TEXT,
                    account TEXT,
                    PRIMARY KEY (id, user_id, account)
                 )''')
    
    # Check if we need to migrate processed_emails to processed_emails_v2
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processed_emails'")
    if c.fetchone():
        logger.info("Found legacy events.db, migrating data to new schema...")
        c.execute("INSERT OR IGNORE INTO processed_emails_v2 (id, user_id, account) SELECT id, user_id, account FROM processed_emails")
        c.execute("DROP TABLE processed_emails")
        logger.info("Migration successful.")
        
    try:
        c.execute("ALTER TABLE processed_emails_v2 ADD COLUMN subject TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        c.execute("ALTER TABLE processed_emails_v2 ADD COLUMN date TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        c.execute("ALTER TABLE processed_emails_v2 ADD COLUMN body TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        c.execute("ALTER TABLE processed_emails_v2 ADD COLUMN sender TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        c.execute("ALTER TABLE processed_emails_v2 ADD COLUMN reason TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists

    try:
        c.execute("ALTER TABLE processed_emails_v2 ADD COLUMN status TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        c.execute("ALTER TABLE events ADD COLUMN location TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
        
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

# --- User Management ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

@app.get("/api/users", dependencies=[Depends(verify_auth)])
async def get_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    users = [{"id": r[0], "username": r[1]} for r in c.fetchall()]
    conn.close()
    return users

@app.post("/api/users", dependencies=[Depends(verify_auth)])
async def create_user(req: UserCreate):
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
    except sqlite3.IntegrityError:
        return {"error": "Username already exists."}
    finally:
        conn.close()
    return {"status": "success"}

@app.put("/api/users/{target_user_id}", dependencies=[Depends(verify_auth)])
async def update_user(target_user_id: str, req: UserUpdate):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if req.username:
        try:
            c.execute("UPDATE users SET username=? WHERE id=?", (req.username, target_user_id))
        except sqlite3.IntegrityError:
            conn.close()
            return {"error": "Username already exists."}
    if req.password:
        if len(req.password) < 4:
            conn.close()
            return {"error": "Password too short."}
        pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (pwd_hash, target_user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/users/{target_user_id}")
async def delete_user(target_user_id: str, current_user: str = Depends(verify_auth)):
    if target_user_id == current_user:
        return {"error": "You cannot delete yourself."}
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (target_user_id,))
    c.execute("DELETE FROM email_accounts WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM events WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=?", (target_user_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- Settings & Accounts ---
class AccountSave(BaseModel):
    id: Optional[str] = None
    email_user: str
    email_pass: str
    email_host: str = "imap.gmail.com"

class SettingsSave(BaseModel):
    ai_provider: Optional[str] = "gemini"
    ai_model: Optional[str] = "gemini-1.5-flash"
    gemini_api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""
    public_url: Optional[str] = ""
    custom_prompt: Optional[str] = ""
    fetch_interval_minutes: Optional[int] = 60
    lookback_days: Optional[int] = 7
    email_fetch_limit: Optional[int] = 20

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
        "fetch_interval_minutes": int(settings.get("fetch_interval_minutes", 60)),
        "lookback_days": int(settings.get("lookback_days", 7)),
        "email_fetch_limit": int(settings.get("email_fetch_limit", 20)),
        "last_scan_time": settings.get("last_scan_time", None),
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
    current.update({k: v for k, v in s.dict().items() if v is not None})
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(current), user_id))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} saved settings (job interval: {s.fetch_interval_minutes}m, lookback: {s.lookback_days}d).")
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
    
@app.delete("/api/settings/reset_history")
async def reset_history(user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} reset their email history.")
    return {"status": "success"}

@app.get("/api/history", dependencies=[Depends(verify_auth)])
async def get_history(user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, account, subject, date, body, sender, reason, status FROM processed_emails_v2 WHERE user_id=? ORDER BY date DESC LIMIT 100", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.delete("/api/history/{account}/{uid}", dependencies=[Depends(verify_auth)])
async def delete_history_item(account: str, uid: str, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=? AND account=? AND id=?", (user_id, account, uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/history/bulk_delete", dependencies=[Depends(verify_auth)])
async def bulk_delete_history(req: list[dict], user_id: str = Depends(verify_auth)):
    if not req:
        return {"status": "success"}
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for item in req:
        c.execute("DELETE FROM processed_emails_v2 WHERE user_id=? AND account=? AND id=?", (user_id, item.get('account'), item.get('id')))
    conn.commit()
    conn.close()
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

# --- Webview Link Resolver ---
def resolve_email_webview_links(text_content: str) -> str:
    """
    If an email is a notification stub that points to an external webview (e.g. MySchoolApp, Blackbaud,
    Podium push, newsletter webviews), automatically fetch the page content so the AI and user
    can read the actual announcement.
    """
    if not text_content:
        return text_content
        
    stub_patterns = [
        r"to view the contents of this message",
        r"click on the following link",
        r"view this email in (?:your )?browser",
        r"view in (?:web )?browser",
        r"view online",
        r"podium/push/default\.aspx",
        r"pushpage",
        r"having trouble viewing this email"
    ]
    
    is_stub = any(re.search(pat, text_content, re.IGNORECASE) for pat in stub_patterns)
    if not is_stub and len(text_content.strip()) > 350:
        return text_content
        
    found_urls = []
    paren_urls = re.findall(r'\(\s*(https?://[^\s\)]+)\s*\)', text_content, re.IGNORECASE)
    for u in paren_urls:
        if "unsubscribe" not in u.lower():
            found_urls.append(u)
            
    if not found_urls:
        all_urls = re.findall(r'https?://[^\s<>"\')]+', text_content, re.IGNORECASE)
        for u in all_urls:
            u_clean = u.rstrip('.,;()')
            if "unsubscribe" not in u_clean.lower() and not u_clean.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js')):
                found_urls.append(u_clean)
                
    if not found_urls:
        return text_content
        
    target_url = found_urls[0]
    
    try:
        req = urllib.request.Request(
            target_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            html_bytes = response.read(250000)
            charset = response.headers.get_content_charset() or 'utf-8'
            html_text = html_bytes.decode(charset, errors='replace')
            
        title_m = re.search(r'<title>(.*?)</title>', html_text, re.IGNORECASE | re.DOTALL)
        page_title = title_m.group(1).strip() if title_m else ''
        
        cleaned = re.sub(r'<script.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<head.*?</head>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<input[^>]*>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'</?(?:p|div|tr|h1|h2|h3|h4|h5|h6|li|blockquote|table|section|article)[^>]*>', '\n', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'<td[^>]*>', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        cleaned = unescape(cleaned)
        
        lines = [line.strip() for line in cleaned.split('\n')]
        body_text = '\n'.join(l for l in lines if l)
        
        if len(body_text.strip()) > 40:
            header_line = f"=== [FETCHED WEBVIEW ANNOUNCEMENT: {page_title}] ===" if page_title else "=== [FETCHED WEBVIEW ANNOUNCEMENT] ==="
            enriched_content = f"{text_content}\n\n{header_line}\nSource: {target_url}\n\n{body_text}"
            logger.info(f"Auto-fetched webview content from {target_url} ({len(body_text)} chars)")
            return enriched_content
    except Exception as e:
        logger.warning(f"Could not auto-fetch webview link {target_url}: {e}")
        
    return text_content

# --- AI Parsing ---
def extract_event(text: str, date: datetime, subject: str, settings: dict) -> dict:
    custom_instructions = settings.get("custom_prompt", "")
    custom_prompt_text = f"\n    USER CUSTOM INSTRUCTIONS: {custom_instructions}\n" if custom_instructions.strip() else ""
    
    date_str = date.isoformat() if date else "Unknown"
    prompt = f"""
    Analyze the following email to see if it contains one or more clear calendar events, appointments, meetings, flights, dinners, deadlines, assignment due dates, or scheduled tasks.
    Email Subject: {subject}
    Email Date: {date_str}
    {custom_prompt_text}
    Return your response strictly as a JSON object with two fields:
    1. "reason": A concise, clear explanation (1-2 sentences) of why events were extracted OR why no events were added to the calendar (for example: "Extracted dental appointment on Oct 14 at 2 PM", "No specific dates, meetings, or deadlines mentioned in this newsletter", "Ignored grade event per custom instructions", "Order confirmation receipt without calendar deadlines").
    2. "events": A JSON array of event objects. If there are no valid calendar events or deadlines (or if they violate the USER CUSTOM INSTRUCTIONS), return an empty array [].
       Each object in the array must have the following keys:
       - "title": Title of the event (string)
       - "date": Date and time in ISO 8601 format (e.g. "2026-10-15T14:00:00"). For assignments or deadlines without a specific time, default the time to 09:00:00 local time.
       - "description": Summary or notes (string)
       - "location": Physical address, room number, or place name (leave blank "" if none found)
       Create a separate event object for EVERY distinct scheduled time mentioned (e.g., Departure time, Event time, Return time).

    Email Content:
    {text[:15000]}
    """
    provider = settings.get("ai_provider", "gemini")
    model_name = settings.get("ai_model", "gemini-1.5-flash")
    if not model_name:
        model_name = "gemini-1.5-flash"
        
    result = ""
    try:
        if provider == "gemini":
            genai.configure(api_key=settings.get("gemini_api_key"))
            model = genai.GenerativeModel(model_name)
            result = model.generate_content(prompt).text.strip()
        elif provider == "openai":
            client = openai.OpenAI(api_key=settings.get("openai_api_key"))
            response = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.2)
            result = response.choices[0].message.content.strip()
            
        clean_result = result
        if clean_result.startswith("```json"):
            clean_result = clean_result[7:]
        elif clean_result.startswith("```"):
            clean_result = clean_result[3:]
        if clean_result.endswith("```"):
            clean_result = clean_result[:-3]
        clean_result = clean_result.strip()

        if clean_result == "NO_EVENT" or (clean_result.startswith("NO_EVENT") and not clean_result.startswith("{")):
            return {"events": [], "reason": "No calendar events or deadlines detected in email."}
            
        parsed_data = None
        try:
            parsed_data = json.loads(clean_result)
        except Exception:
            start_b = clean_result.find('{')
            end_b = clean_result.rfind('}')
            if start_b != -1 and end_b != -1 and end_b > start_b:
                parsed_data = json.loads(clean_result[start_b:end_b+1])
            else:
                start_arr = clean_result.find('[')
                end_arr = clean_result.rfind(']')
                if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
                    parsed_data = json.loads(clean_result[start_arr:end_arr+1])

        events_list = []
        reason = ""
        
        if isinstance(parsed_data, dict):
            if "events" in parsed_data:
                events_list = parsed_data.get("events") or []
                reason = parsed_data.get("reason", "")
            elif "title" in parsed_data and "date" in parsed_data:
                events_list = [parsed_data]
                reason = parsed_data.get("reason", f"Extracted event: {parsed_data.get('title')}")
            else:
                reason = parsed_data.get("reason", "No calendar events or deadlines detected.")
        elif isinstance(parsed_data, list):
            events_list = parsed_data
            reason = f"Extracted {len(events_list)} event(s)." if events_list else "No calendar events or deadlines detected."
            
        valid_events = []
        if isinstance(events_list, list):
            for e in events_list:
                if isinstance(e, dict) and all(k in e for k in ("title", "date", "description")):
                    valid_events.append(e)
                    
        if not reason:
            if valid_events:
                reason = f"Extracted {len(valid_events)} event(s): " + ", ".join(e.get("title", "Event") for e in valid_events)
            else:
                reason = "No calendar events or deadlines detected in email."
                
        return {"events": valid_events, "reason": reason}
    except Exception as e:
        logger.error(f"AI extraction error ({provider} - {model_name}): {e}")
        raise ValueError(f"AI API Error: {str(e)}") 

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
    lookback_days = int(settings.get("lookback_days", 7) or 7)
    email_fetch_limit = int(settings.get("email_fetch_limit", 20) or 20)
    
    for account in accounts:
        email_user = account['email_user']
        email_pass = account['email_pass']
        email_host = account['email_host']
        
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                date_limit = (datetime.now() - timedelta(days=lookback_days)).date()
                messages = mailbox.fetch(AND(date_gte=date_limit), limit=email_fetch_limit, reverse=True)
                
                for msg in messages:
                    c.execute("SELECT id FROM processed_emails_v2 WHERE id=? AND user_id=? AND account=?", (msg.uid, user_id, email_user))
                    if c.fetchone(): continue
                        
                    sender = getattr(msg, 'from_', '') or ''
                    text_content = msg.text or msg.html or ''
                    subject_str = msg.subject or 'No Subject'
                    date_iso = msg.date.isoformat() if msg.date else ""
                    
                    # Auto-resolve link-only webview stubs (e.g. MySchoolApp, Blackbaud, Podium push)
                    text_content = resolve_email_webview_links(text_content)
                    
                    if text_content and len(text_content.strip()) > 10:
                        try:
                            ai_result = extract_event(text_content, msg.date, subject_str, settings)
                            event_data_list = ai_result.get("events", [])
                            base_reason = ai_result.get("reason", "")
                            
                            # Gemini Free Tier limit is 15 RPM (1 request every 4 seconds)
                            if settings.get("ai_provider", "gemini") == "gemini":
                                await asyncio.sleep(4.1)
                                
                            if event_data_list:
                                email_status = "added"
                                sync_details = []
                                for event_data in event_data_list:
                                    event_id = str(uuid.uuid4())
                                    c.execute("INSERT INTO events (id, user_id, account, title, date, description, location, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')", 
                                              (event_id, user_id, email_user, 
                                               event_data.get("title", "Untitled"),
                                               event_data.get("date", ""),
                                               event_data.get("description", ""),
                                               event_data.get("location", "")
                                              ))
                                    conn.commit()
                                    
                                    # Auto-sync to Google Calendar immediately if connected!
                                    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
                                    if os.path.exists(token_file):
                                        try:
                                            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
                                            service = build('calendar', 'v3', credentials=creds)
                                            try:
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
                                                
                                                loc = event_data.get("location", "")
                                                if loc and loc.strip():
                                                    gcal_event['location'] = loc.strip()
                                                    
                                                service.events().insert(calendarId='primary', body=gcal_event).execute()
                                                c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
                                                logger.info(f"Background auto-synced event '{event_data['title']}' for {user_id}")
                                                sync_details.append(f"Auto-synced '{event_data['title']}' to Google Calendar")
                                            except Exception as date_err:
                                                logger.error(f"Failed to auto-sync event {event_data['title']} (bad date format?): {date_err}")
                                                sync_details.append(f"Saved to Dashboard (sync error: {date_err})")
                                        except Exception as e:
                                            logger.error(f"Background auto-sync failed for {user_id}: {e}")
                                            sync_details.append(f"Saved to Dashboard (Google Calendar error)")
                                    else:
                                        sync_details.append(f"Saved to Dashboard for review / manual sync")
                                    
                                    total_events_found += 1
                                    
                                final_reason = base_reason
                                if sync_details:
                                    final_reason += " (" + "; ".join(sync_details) + ")"
                            else:
                                email_status = "no_event"
                                final_reason = base_reason or "No calendar events or deadlines detected in email."
                        except ValueError as ve:
                            logger.error(f"AI API Error on {email_user}: {str(ve)}")
                            # Skip this email for now without marking it processed if the API failed
                            continue
                    else:
                        email_status = "no_event"
                        final_reason = "Email content was empty or too short to contain calendar events."
                    
                    c.execute("INSERT INTO processed_emails_v2 (id, user_id, account, subject, date, body, sender, reason, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                        (msg.uid, user_id, email_user, subject_str, date_iso, text_content, sender, final_reason, email_status))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error fetching emails for {email_user}: {e}")
            conn.close()
            return {"error": f"Email connection failed for {email_user}. Check password/host.", "new_events": total_events_found}
            
    # Record last scan time in user settings
    try:
        settings["last_scan_time"] = datetime.now().isoformat()
        c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating last_scan_time for user {user_id}: {e}")

    conn.close()
    return {"status": "success", "new_events": total_events_found}

# In-memory timestamp tracking for user job runs
USER_LAST_SCAN = {}

@app.get("/api/fetch_emails")
async def fetch_emails_endpoint(user_id: str = Depends(verify_auth)):
    logger.info(f"User {user_id} triggered manual email fetch.")
    USER_LAST_SCAN[user_id] = datetime.now().timestamp()
    return await process_user_emails(user_id)

# --- Background Task Scheduler ---
async def scheduled_email_fetch():
    logger.info("Background job scheduler initialized.")
    while True:
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT id, settings FROM users")
            users = c.fetchall()
            conn.close()

            now_ts = datetime.now().timestamp()
            for u in users:
                user_id = u["id"]
                s = json.loads(u["settings"] or "{}")
                interval_minutes = int(s.get("fetch_interval_minutes", 60))
                
                # If interval is 0 or negative, auto-fetch is disabled
                if interval_minutes <= 0:
                    continue
                    
                interval_seconds = interval_minutes * 60
                last_scan = USER_LAST_SCAN.get(user_id)
                if last_scan is None:
                    last_scan_str = s.get("last_scan_time")
                    if last_scan_str:
                        try:
                            last_scan = datetime.fromisoformat(last_scan_str).timestamp()
                        except Exception:
                            last_scan = 0
                    else:
                        last_scan = 0
                    USER_LAST_SCAN[user_id] = last_scan
                
                if (now_ts - last_scan) >= interval_seconds:
                    logger.info(f"Triggering scheduled background email scan for user {user_id} (frequency: every {interval_minutes}m)...")
                    USER_LAST_SCAN[user_id] = now_ts
                    await process_user_emails(user_id)
        except Exception as e:
            logger.error(f"Error in background job scheduler: {e}")

        await asyncio.sleep(30) # Poll every 30 seconds

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_email_fetch())

@app.get("/api/events")
async def get_events(user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    now_iso = datetime.now().isoformat()
    c.execute("SELECT * FROM events WHERE status IN ('pending', 'added') AND user_id=? AND date >= ? ORDER BY date ASC", (user_id, now_iso))
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
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, date, description, location FROM events WHERE id=? AND user_id=?", (event_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
        
    title, date_str, description, location = row
    
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        conn.close()
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
        
    try:
        start_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
        end_dt = start_dt + timedelta(hours=1)
        
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        
        gcal_event = {
            'summary': title,
            'description': description,
            'start': {'dateTime': start_dt.isoformat()},
            'end': {'dateTime': end_dt.isoformat()}
        }
        
        if location and location.strip():
            gcal_event['location'] = location.strip()
            
        service.events().insert(calendarId='primary', body=gcal_event).execute()
        
        c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/events/{event_id}")
async def dismiss_event(event_id: str, user_id: str = Depends(verify_auth)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE events SET status='dismissed' WHERE id=? AND user_id=?", (event_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

class BulkEventAction(BaseModel):
    event_ids: List[str]

@app.post("/api/events/bulk_dismiss")
async def bulk_dismiss_events(req: BulkEventAction, user_id: str = Depends(verify_auth)):
    if not req.event_ids:
        return {"status": "success"}
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    placeholders = ','.join('?' * len(req.event_ids))
    c.execute(f"UPDATE events SET status='dismissed' WHERE user_id=? AND id IN ({placeholders})", (user_id, *req.event_ids))
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
