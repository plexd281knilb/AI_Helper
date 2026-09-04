import os
import json
import sqlite3
import uuid
import secrets
import hashlib
import logging
import re
import ssl
import time
import urllib.request
import urllib.parse
from html import unescape
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
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
def get_db_conn():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA busy_timeout=30000;")
    c.execute("PRAGMA synchronous=NORMAL;")
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
        
    try:
        c.execute("ALTER TABLE events ADD COLUMN email_id TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    c.execute('''CREATE TABLE IF NOT EXISTS grocery_stores (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT,
                    ad_url TEXT,
                    notes TEXT,
                    last_scanned TEXT,
                    cached_deals TEXT
                 )''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS grocery_lists (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                 )''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS grocery_list_items (
                    id TEXT PRIMARY KEY,
                    list_id TEXT,
                    user_id TEXT,
                    item_name TEXT,
                    store_name TEXT,
                    price_notes TEXT,
                    category TEXT,
                    is_checked INTEGER DEFAULT 0,
                    image_url TEXT
                 )''')
                 
    try:
        c.execute("ALTER TABLE grocery_list_items ADD COLUMN image_url TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    conn.close()

init_db()

# --- Authentication & Persistent Session Logic ---
SESSION_CACHE = {} # In-memory cache for high performance: token -> (user_id, expires_timestamp)

class AuthRequest(BaseModel):
    username: str
    password: str

def get_user_id_from_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    now_ts = datetime.now().timestamp()
    
    # 1. Check fast memory cache
    cached = SESSION_CACHE.get(token)
    if cached:
        user_id, expires = cached
        if expires and expires > now_ts:
            return user_id
        else:
            del SESSION_CACHE[token]
            
    # 2. Check persistent SQLite database
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, expires FROM sessions WHERE token=?", (token,))
        row = c.fetchone()
        if row:
            user_id, expires = row[0], row[1]
            if expires and expires > now_ts:
                SESSION_CACHE[token] = (user_id, expires)
                conn.close()
                return user_id
            else:
                # Clean up expired token
                c.execute("DELETE FROM sessions WHERE token=?", (token,))
                conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error querying session token from database: {e}")
        
    return None

def verify_auth(request: Request):
    token = request.cookies.get("session_token")
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user_id

@app.get("/api/auth/status")
def auth_status(request: Request):
    token = request.cookies.get("session_token")
    user_id = get_user_id_from_token(token)
    logged_in = user_id is not None
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return {"setup_required": count == 0, "logged_in": logged_in}

@app.post("/api/auth/register")
def auth_register(req: AuthRequest):
    if len(req.password) < 4:
        return {"error": "Password must be at least 4 characters."}
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user_id = str(uuid.uuid4())
    default_settings = json.dumps({"ai_provider": "gemini", "ai_model": "gemini-1.5-flash", "public_url": ""})
    conn = get_db_conn()
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
def auth_login(req: AuthRequest, response: Response):
    req_hash = hashlib.sha256(req.password.encode()).hexdigest()
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (req.username, req_hash))
    user = c.fetchone()
    if not user:
        conn.close()
        logger.warning(f"Failed login attempt for username: {req.username}")
        return {"error": "Invalid username or password"}
        
    user_id = user[0]
    token = secrets.token_hex(32)
    # 90-day session expiration
    expires_ts = (datetime.now() + timedelta(days=90)).timestamp()
    
    try:
        c.execute("INSERT OR REPLACE INTO sessions (token, user_id, expires) VALUES (?, ?, ?)", (token, user_id, expires_ts))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to persist session token to database: {e}")
    finally:
        conn.close()
        
    SESSION_CACHE[token] = (user_id, expires_ts)
    
    # Set persistent cookie for 90 days with root path
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 90,
        expires=86400 * 90,
        samesite="lax",
        path="/"
    )
    logger.info(f"User {req.username} logged in successfully (session cached in DB for 90 days).")
    return {"status": "success"}

@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        SESSION_CACHE.pop(token, None)
        try:
            conn = get_db_conn()
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE token=?", (token,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error removing session from database: {e}")
            
    response.delete_cookie("session_token", path="/")
    logger.info("A user logged out.")
    return {"status": "success"}

# --- User Management ---
class UserCreate(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

@app.get("/api/users", dependencies=[Depends(verify_auth)])
def get_users():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    users = [{"id": r[0], "username": r[1]} for r in c.fetchall()]
    conn.close()
    return users

@app.post("/api/users", dependencies=[Depends(verify_auth)])
def create_user(req: UserCreate):
    if len(req.password) < 4:
        return {"error": "Password must be at least 4 characters."}
    pwd_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user_id = str(uuid.uuid4())
    default_settings = json.dumps({"ai_provider": "gemini", "ai_model": "gemini-1.5-flash", "public_url": ""})
    conn = get_db_conn()
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
def update_user(target_user_id: str, req: UserUpdate):
    conn = get_db_conn()
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
def delete_user(target_user_id: str, current_user: str = Depends(verify_auth)):
    if target_user_id == current_user:
        return {"error": "You cannot delete yourself."}
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (target_user_id,))
    c.execute("DELETE FROM email_accounts WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM events WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM sessions WHERE user_id=?", (target_user_id,))
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
    postal_code: Optional[str] = "76262"

@app.get("/api/settings")
def read_settings(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
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
        "postal_code": settings.get("postal_code", "76262"),
        "last_scan_time": settings.get("last_scan_time", None),
        "google_auth_ready": os.path.exists(CLIENT_SECRETS_FILE),
        "google_connected": os.path.exists(token_file)
    }

@app.post("/api/settings/ai")
def save_ai_settings(s: SettingsSave, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
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
def save_account(acc: AccountSave, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
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
def delete_account(acc_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM email_accounts WHERE id=? AND user_id=?", (acc_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}
    
@app.delete("/api/settings/reset_history")
def reset_history(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} reset their email history.")
    return {"status": "success"}

@app.get("/api/history", dependencies=[Depends(verify_auth)])
def get_history(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, account, subject, date, body, sender, reason, status FROM processed_emails_v2 WHERE user_id=? ORDER BY date DESC LIMIT 100", (user_id,))
    history_rows = [dict(r) for r in c.fetchall()]
    
    # Fetch user events to associate with history entries
    c.execute("SELECT id, email_id, account, title, date, description, location, status FROM events WHERE user_id=?", (user_id,))
    all_events = [dict(r) for r in c.fetchall()]
    conn.close()
    
    events_by_key = {}
    for ev in all_events:
        eid = ev.get("email_id")
        acc = ev.get("account")
        if eid and acc:
            key = f"{acc}_{eid}"
            if key not in events_by_key:
                events_by_key[key] = []
            events_by_key[key].append(ev)
            
    for item in history_rows:
        key = f"{item['account']}_{item['id']}"
        item["events"] = events_by_key.get(key, [])
        
    return history_rows

@app.delete("/api/history/{account}/{uid}", dependencies=[Depends(verify_auth)])
def delete_history_item(account: str, uid: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM processed_emails_v2 WHERE user_id=? AND account=? AND id=?", (user_id, account, uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/history/bulk_delete", dependencies=[Depends(verify_auth)])
def bulk_delete_history(req: list[dict], user_id: str = Depends(verify_auth)):
    if not req:
        return {"status": "success"}
    conn = get_db_conn()
    c = conn.cursor()
    for item in req:
        c.execute("DELETE FROM processed_emails_v2 WHERE user_id=? AND account=? AND id=?", (user_id, item.get('account'), item.get('id')))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/upload_client_secret", dependencies=[Depends(verify_auth)])
def upload_client_secret(file: UploadFile = File(...)):
    contents = file.file.read()
    with open(CLIENT_SECRETS_FILE, "wb") as f:
        f.write(contents)
    logger.info("Google Client Secret JSON uploaded.")
    return {"status": "success"}

class ModelRequest(BaseModel):
    provider: str
    api_key: str

@app.post("/api/models", dependencies=[Depends(verify_auth)])
def get_models(req: ModelRequest):
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

# --- Webview & Newsletter Link Resolver ---
def clean_page_html(html_str: str) -> str:
    """
    Strips scripts, styles, navigation bars, menus, and footers from fetched web pages
    so the AI receives only the actual announcement content and details.
    """
    if not html_str:
        return ""
    cleaned = re.sub(r'<script.*?</script>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<head.*?</head>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<input[^>]*>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<header.*?</header>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<nav.*?</nav>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<footer.*?</footer>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<aside.*?</aside>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:p|div|tr|h1|h2|h3|h4|h5|h6|li|blockquote|table|section|article)[^>]*>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<td[^>]*>', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = unescape(cleaned)
    
    nav_phrases = ['skip to main content', 'close menu', 'open menu', 'mobile search', 'clear search', 'search-form', 'mobile main nav', 'mobile utility', 'mobile cta']
    lines = []
    for line in cleaned.split('\n'):
        l = line.strip()
        if not l or any(np in l.lower() for np in nav_phrases):
            continue
        lines.append(l)
    return '\n'.join(lines)

def resolve_email_webview_links(text_content: str) -> str:
    """
    If an email is a notification stub, eNotice digest, or newsletter that links to online
    articles (e.g. MySchoolApp, Finalsite, Blackboard, eNotice, Blackbaud), automatically fetches
    the page content for each linked announcement so the AI extracts all calendar events.
    """
    if not text_content:
        return text_content
        
    found_urls = []
    paren_urls = re.findall(r'\(\s*(https?://[^\s\)]+)\s*\)', text_content, re.IGNORECASE)
    raw_urls = re.findall(r'https?://[^\s<>"\'\)]+', text_content, re.IGNORECASE)
    
    ignore_domains = ['instagram.com', 'facebook.com', 'twitter.com', 'x.com', 'linkedin.com', 'youtube.com', 'youtu.be']
    
    for u in (paren_urls + raw_urls):
        u_clean = u.rstrip('.,;()')
        if any(ign in u_clean.lower() for ign in ['unsubscribe', 'optout', 'privacy', 'manage-preferences']):
            continue
        if any(dom in u_clean.lower() for dom in ignore_domains):
            continue
        if u_clean.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js', '.ico')):
            continue
        if u_clean not in found_urls:
            found_urls.append(u_clean)
            
    if not found_urls:
        return text_content
        
    stub_patterns = [
        r"to view the contents of this message",
        r"click on the following link",
        r"view this email in (?:your )?browser",
        r"view in (?:web )?browser",
        r"view online",
        r"myenotice\.com",
        r"podium/push",
        r"pushpage",
        r"having trouble viewing this email"
    ]
    
    is_stub_or_digest = any(re.search(pat, text_content, re.IGNORECASE) for pat in stub_patterns)
    if not is_stub_or_digest and len(text_content.strip()) > 600:
        return text_content
        
    fetched_sections = []
    # Follow up to 5 article links per email
    for target_url in found_urls[:5]:
        try:
            req = urllib.request.Request(
                target_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html_bytes = response.read(250000)
                charset = response.headers.get_content_charset() or 'utf-8'
                html_text = html_bytes.decode(charset, errors='replace')
                
            title_m = re.search(r'<title>(.*?)</title>', html_text, re.IGNORECASE | re.DOTALL)
            page_title = title_m.group(1).strip() if title_m else ''
            page_title = re.sub(r'\s*\|\s*.*$', '', page_title).strip()
            
            body_text = clean_page_html(html_text)
            if len(body_text.strip()) > 30:
                header_line = f"=== [FETCHED ANNOUNCEMENT: {page_title}] ===" if page_title else "=== [FETCHED ANNOUNCEMENT] ==="
                fetched_sections.append(f"{header_line}\nSource: {target_url}\n\n{body_text}")
                logger.info(f"Auto-fetched announcement from {target_url} ({len(body_text)} chars)")
        except Exception as e:
            logger.warning(f"Could not auto-fetch link {target_url}: {e}")
            
    if fetched_sections:
        return text_content + "\n\n" + "\n\n".join(fetched_sections)
        
    return text_content

# --- HTML to Clean Text Converter ---
def html_to_clean_text(html_str: str) -> str:
    """
    Converts raw HTML email bodies into clean, human-readable text while preserving
    structural line breaks, headings, lists, and hyperlinks.
    """
    if not html_str:
        return ""
    cleaned = re.sub(r'<script.*?</script>', '', html_str, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<head.*?</head>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<input[^>]*>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:p|div|tr|h1|h2|h3|h4|h5|h6|li|blockquote|table|section|article)[^>]*>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<td[^>]*>', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = unescape(cleaned)
    lines = [line.strip() for line in cleaned.split('\n')]
    return '\n'.join(l for l in lines if l)

def extract_email_text(msg) -> str:
    """
    Intelligently extracts the most complete email body between plain text and HTML.
    Handles newsletters/eNotice emails that leave plain text as dummy placeholders (e.g. '<!--placeholder-->')
    or empty stubs while having rich HTML bodies.
    """
    plain_text = (getattr(msg, 'text', '') or '').strip()
    html_raw = getattr(msg, 'html', '') or ''
    html_text = html_to_clean_text(html_raw) if html_raw else ""
    
    placeholder_patterns = [
        r"^<!--.*?-->$",
        r"<!--placeholder-->",
        r"^placeholder$",
        r"^loading\.{0,3}$"
    ]
    is_placeholder = any(re.search(pat, plain_text, re.IGNORECASE) for pat in placeholder_patterns)
    
    if is_placeholder or not plain_text:
        content = html_text or plain_text
    elif html_text and len(html_text) > len(plain_text) * 1.5 and len(html_text) > 50:
        content = html_text
    else:
        content = plain_text
        
    return resolve_email_webview_links(content)

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

# --- Google Calendar Event Pusher & Duplicate Prevention ---
def push_event_to_gcal(service, title: str, description: str, date_str: str, location: str = ""):
    """
    Pushes an event to Google Calendar, with duplicate prevention by checking
    events around the same time window (+/- 2 hours) on the user's primary calendar.
    """
    start_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
    end_time = start_time + timedelta(hours=1)
    
    # Check Google Calendar for existing events in a +/- 2 hour window
    try:
        time_min = (start_time - timedelta(hours=2)).isoformat()
        time_max = (end_time + timedelta(hours=2)).isoformat()
        existing = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            maxResults=25
        ).execute()
        
        norm_title = (title or "").strip().lower()
        for item in existing.get('items', []):
            item_summary = (item.get('summary') or "").strip().lower()
            if item_summary == norm_title or (len(norm_title) > 4 and norm_title in item_summary):
                logger.info(f"Duplicate check: Event '{title}' already exists on Google Calendar around {start_time.isoformat()}. Skipping insertion.")
                return {"status": "already_exists", "event_id": item.get("id")}
    except Exception as check_err:
        logger.warning(f"Google Calendar duplicate check skipped due to notice: {check_err}")

    gcal_event = {
        'summary': title,
        'description': description,
        'start': {'dateTime': start_time.isoformat()},
        'end': {'dateTime': end_time.isoformat()}
    }
    if location and location.strip():
        gcal_event['location'] = location.strip()
        
    created = service.events().insert(calendarId='primary', body=gcal_event).execute()
    return {"status": "created", "event_id": created.get("id")}

def process_user_emails(user_id: str):
    conn = get_db_conn()
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
        
        logger.info(f"Fetching emails for user {user_id} ({email_user}) from {email_host} (lookback: {lookback_days}d, limit: {email_fetch_limit})...")
        try:
            with MailBox(email_host).login(email_user, email_pass) as mailbox:
                since_date = (datetime.now() - timedelta(days=lookback_days)).date()
                messages = list(mailbox.fetch(AND(date_gte=since_date), limit=email_fetch_limit, reverse=True))
                logger.info(f"Retrieved {len(messages)} messages for {email_user}.")
                
                for msg in messages:
                    c.execute("SELECT id FROM processed_emails_v2 WHERE id=? AND user_id=? AND account=?", (msg.uid, user_id, email_user))
                    if c.fetchone(): continue
                        
                    sender = getattr(msg, 'from_', '') or ''
                    text_content = extract_email_text(msg)
                    subject_str = msg.subject or 'No Subject'
                    date_iso = msg.date.isoformat() if msg.date else ""
                    
                    if text_content and len(text_content.strip()) > 10:
                        try:
                            ai_result = extract_event(text_content, msg.date, subject_str, settings)
                            event_data_list = ai_result.get("events", [])
                            base_reason = ai_result.get("reason", "")
                            
                            # Gemini Free Tier limit is 15 RPM (1 request every 4 seconds)
                            if settings.get("ai_provider", "gemini") == "gemini":
                                time.sleep(4.1)
                                
                            if event_data_list:
                                email_status = "added"
                                sync_details = []
                                for event_data in event_data_list:
                                    event_id = str(uuid.uuid4())
                                    c.execute("INSERT INTO events (id, user_id, account, email_id, title, date, description, location, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')", 
                                              (event_id, user_id, email_user, msg.uid,
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
                                                res = push_event_to_gcal(
                                                    service,
                                                    event_data.get("title", "Untitled"),
                                                    event_data.get("description", ""),
                                                    event_data.get("date", ""),
                                                    event_data.get("location", "")
                                                )
                                                c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
                                                if res.get("status") == "already_exists":
                                                    logger.info(f"Background: event '{event_data['title']}' already on Google Calendar for {user_id}")
                                                    sync_details.append(f"Already on Google Calendar '{event_data['title']}'")
                                                else:
                                                    logger.info(f"Background auto-synced event '{event_data['title']}' for {user_id}")
                                                    sync_details.append(f"Auto-synced '{event_data['title']}' to Google Calendar")
                                            except Exception as date_err:
                                                err_str = str(date_err)
                                                if "invalid_grant" in err_str:
                                                    logger.warning(f"Google Calendar OAuth token for {user_id} is expired or revoked.")
                                                    sync_details.append("Saved to Dashboard (Google Calendar token expired — reconnect in Settings)")
                                                else:
                                                    logger.error(f"Failed to auto-sync event {event_data['title']}: {date_err}")
                                                    sync_details.append(f"Saved to Dashboard (sync error: {err_str})")
                                        except Exception as e:
                                            err_str = str(e)
                                            if "invalid_grant" in err_str:
                                                logger.warning(f"Google Calendar OAuth token for {user_id} is expired or revoked.")
                                                sync_details.append("Saved to Dashboard (Google Calendar token expired — reconnect in Settings)")
                                            else:
                                                logger.error(f"Background auto-sync failed for {user_id}: {e}")
                                                sync_details.append(f"Saved to Dashboard (Google Calendar error: {err_str})")
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
def fetch_emails_endpoint(user_id: str = Depends(verify_auth)):
    logger.info(f"User {user_id} triggered manual email fetch.")
    USER_LAST_SCAN[user_id] = datetime.now().timestamp()
    return process_user_emails(user_id)

# --- Background Task Scheduler ---
async def scheduled_email_fetch():
    logger.info("Background job scheduler initialized.")
    while True:
        try:
            conn = get_db_conn()
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
                    await asyncio.to_thread(process_user_emails, user_id)
        except Exception as e:
            logger.error(f"Error in background job scheduler: {e}")

        await asyncio.sleep(30) # Poll every 30 seconds

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduled_email_fetch())

@app.get("/api/events")
def get_events(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    now_iso = datetime.now().isoformat()
    c.execute("SELECT * FROM events WHERE status IN ('pending', 'added') AND user_id=? AND date >= ? ORDER BY date ASC", (user_id, now_iso))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Google Calendar OAuth & Sync ---
@app.get("/api/auth/google/url")
def get_google_auth_url(request: Request, user_id: str = Depends(verify_auth)):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "Client secrets missing"}
    conn = get_db_conn()
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
def google_auth_callback(request: Request, state: str):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: secrets missing."
    conn = get_db_conn()
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

@app.delete("/api/auth/google/token", dependencies=[Depends(verify_auth)])
def disconnect_google(user_id: str = Depends(verify_auth)):
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if os.path.exists(token_file):
        try:
            os.remove(token_file)
            logger.info(f"User {user_id} disconnected Google Calendar (token removed).")
        except Exception as e:
            logger.error(f"Error removing token file for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to remove token")
    return {"status": "success"}

@app.post("/api/events/{event_id}/sync")
def sync_event(event_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT title, date, description, location FROM events WHERE id=? AND user_id=?", (event_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
        
    title = row['title']
    date_str = row['date']
    description = row['description']
    location = row['location']
    
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        conn.close()
        raise HTTPException(status_code=400, detail="Google Calendar not connected. Please connect in Settings.")
        
    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        res = push_event_to_gcal(service, title, description, date_str, location)
        
        c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "gcal_status": res["status"]}
    except Exception as e:
        conn.close()
        err_str = str(e)
        if "invalid_grant" in err_str:
            raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
        raise HTTPException(status_code=500, detail=err_str)

@app.delete("/api/events/{event_id}")
def dismiss_event(event_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("UPDATE events SET status='dismissed' WHERE id=? AND user_id=?", (event_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

class BulkEventAction(BaseModel):
    event_ids: List[str]

@app.post("/api/events/bulk_sync", dependencies=[Depends(verify_auth)])
def bulk_sync_events(req: BulkEventAction, user_id: str = Depends(verify_auth)):
    if not req.event_ids:
        return {"status": "success", "synced": 0}
        
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        raise HTTPException(status_code=400, detail="Google Calendar not connected. Please connect in Settings.")
        
    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except Exception as e:
        err_str = str(e)
        if "invalid_grant" in err_str:
            raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
        raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google: {err_str}")
        
    conn = get_db_conn()
    c = conn.cursor()
    placeholders = ','.join('?' * len(req.event_ids))
    c.execute(f"SELECT id, title, date, description, location FROM events WHERE user_id=? AND id IN ({placeholders})", (user_id, *req.event_ids))
    rows = c.fetchall()
    
    synced_count = 0
    errors = []
    for row in rows:
        event_id = row['id']
        title = row['title']
        date_str = row['date']
        description = row['description']
        location = row['location']
        try:
            res = push_event_to_gcal(service, title, description, date_str, location)
            c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
            synced_count += 1
        except Exception as e:
            err_str = str(e)
            if "invalid_grant" in err_str:
                conn.commit()
                conn.close()
                raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
            errors.append(f"Failed to sync '{title}': {err_str}")
            
    conn.commit()
    conn.close()
    return {"status": "success", "synced": synced_count, "errors": errors}

@app.post("/api/events/bulk_dismiss")
def bulk_dismiss_events(req: BulkEventAction, user_id: str = Depends(verify_auth)):
    if not req.event_ids:
        return {"status": "success"}
    conn = get_db_conn()
    c = conn.cursor()
    placeholders = ','.join('?' * len(req.event_ids))
    c.execute(f"UPDATE events SET status='dismissed' WHERE user_id=? AND id IN ({placeholders})", (user_id, *req.event_ids))
    conn.commit()
    conn.close()
    return {"status": "success"}

class BulkHistorySync(BaseModel):
    items: List[dict]

@app.post("/api/history/{account}/{uid}/sync", dependencies=[Depends(verify_auth)])
def sync_history_email(account: str, uid: str, user_id: str = Depends(verify_auth)):
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        raise HTTPException(status_code=400, detail="Google Calendar not connected. Please connect your Google account in Settings.")
        
    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except Exception as e:
        err_str = str(e)
        if "invalid_grant" in err_str:
            raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
        raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google: {err_str}")
        
    conn = get_db_conn()
    c = conn.cursor()
    
    # Check for existing events linked to this email
    c.execute("SELECT id, title, date, description, location, status FROM events WHERE user_id=? AND account=? AND email_id=?", (user_id, account, uid))
    event_rows = [dict(r) for r in c.fetchall()]
    
    # If none found by email_id, check processed_emails_v2 and extract
    if not event_rows:
        c.execute("SELECT subject, date, body, sender FROM processed_emails_v2 WHERE user_id=? AND account=? AND id=?", (user_id, account, uid))
        email_row = c.fetchone()
        if not email_row:
            conn.close()
            raise HTTPException(status_code=404, detail="Email record not found in history.")
            
        c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
        s_row = c.fetchone()
        settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
        
        email_date = None
        if email_row["date"]:
            try: email_date = datetime.fromisoformat(email_row["date"])
            except Exception: pass
            
        ai_result = extract_event(email_row["body"] or email_row["subject"], email_date, email_row["subject"] or "", settings)
        extracted = ai_result.get("events", [])
        if not extracted:
            conn.close()
            raise HTTPException(status_code=400, detail=f"No calendar events detected in this email: {ai_result.get('reason', '')}")
            
        for ed in extracted:
            eid = str(uuid.uuid4())
            c.execute("INSERT INTO events (id, user_id, account, email_id, title, date, description, location, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                      (eid, user_id, account, uid, ed.get("title", "Untitled"), ed.get("date", ""), ed.get("description", ""), ed.get("location", "")))
            event_rows.append({
                "id": eid,
                "title": ed.get("title", "Untitled"),
                "date": ed.get("date", ""),
                "description": ed.get("description", ""),
                "location": ed.get("location", ""),
                "status": "pending"
            })
        conn.commit()
        
    synced_count = 0
    already_on_cal = 0
    errors = []
    for ev in event_rows:
        try:
            res = push_event_to_gcal(service, ev["title"], ev["description"], ev["date"], ev.get("location", ""))
            c.execute("UPDATE events SET status='added' WHERE id=?", (ev["id"],))
            if res.get("status") == "already_exists":
                already_on_cal += 1
            else:
                synced_count += 1
        except Exception as pe:
            err_str = str(pe)
            if "invalid_grant" in err_str:
                conn.commit()
                conn.close()
                raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
            errors.append(f"Could not sync '{ev['title']}': {err_str}")
            
    now_str = datetime.now().strftime("%b %d, %I:%M %p")
    if synced_count > 0:
        new_reason = f"Successfully pushed {synced_count} event(s) to Google Calendar on {now_str}."
    elif already_on_cal > 0:
        new_reason = f"Event already exists on Google Calendar (verified on {now_str})."
    else:
        new_reason = f"Sync attempted on {now_str}."
        
    if errors:
        new_reason += f" (Warnings: {'; '.join(errors)})"
        
    c.execute("UPDATE processed_emails_v2 SET status='added', reason=? WHERE user_id=? AND account=? AND id=?", (new_reason, user_id, account, uid))
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "synced": synced_count,
        "already_exists": already_on_cal,
        "errors": errors,
        "reason": new_reason
    }

@app.post("/api/history/bulk_sync", dependencies=[Depends(verify_auth)])
def bulk_sync_history(req: BulkHistorySync, user_id: str = Depends(verify_auth)):
    if not req.items:
        return {"status": "success", "synced": 0}
        
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    if not os.path.exists(token_file):
        raise HTTPException(status_code=400, detail="Google Calendar not connected. Please connect in Settings.")
        
    try:
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        service = build('calendar', 'v3', credentials=creds)
    except Exception as e:
        err_str = str(e)
        if "invalid_grant" in err_str:
            raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
        raise HTTPException(status_code=500, detail=f"Failed to authenticate with Google: {err_str}")
        
    conn = get_db_conn()
    c = conn.cursor()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    
    total_synced = 0
    all_errors = []
    
    for item in req.items:
        acc = item.get("account")
        uid = item.get("id")
        if not acc or not uid:
            continue
            
        c.execute("SELECT id, title, date, description, location, status FROM events WHERE user_id=? AND account=? AND email_id=?", (user_id, acc, uid))
        event_rows = [dict(r) for r in c.fetchall()]
        
        if not event_rows:
            c.execute("SELECT subject, date, body, sender FROM processed_emails_v2 WHERE user_id=? AND account=? AND id=?", (user_id, acc, uid))
            email_row = c.fetchone()
            if not email_row:
                continue
                
            email_date = None
            if email_row["date"]:
                try: email_date = datetime.fromisoformat(email_row["date"])
                except Exception: pass
                
            try:
                ai_result = extract_event(email_row["body"] or email_row["subject"], email_date, email_row["subject"] or "", settings)
                for ed in ai_result.get("events", []):
                    eid = str(uuid.uuid4())
                    c.execute("INSERT INTO events (id, user_id, account, email_id, title, date, description, location, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                              (eid, user_id, acc, uid, ed.get("title", "Untitled"), ed.get("date", ""), ed.get("description", ""), ed.get("location", "")))
                    event_rows.append({"id": eid, "title": ed.get("title", "Untitled"), "date": ed.get("date", ""), "description": ed.get("description", ""), "location": ed.get("location", "")})
            except Exception as ex:
                all_errors.append(f"AI parse error on email {uid}: {ex}")
                continue
                
        synced_this = 0
        for ev in event_rows:
            try:
                res = push_event_to_gcal(service, ev["title"], ev["description"], ev["date"], ev.get("location", ""))
                c.execute("UPDATE events SET status='added' WHERE id=?", (ev["id"],))
                total_synced += 1
                synced_this += 1
            except Exception as pe:
                err_str = str(pe)
                if "invalid_grant" in err_str:
                    conn.commit()
                    conn.close()
                    raise HTTPException(status_code=400, detail="Google Calendar token has expired or was revoked. Please reconnect Google Calendar in Settings.")
                all_errors.append(f"Failed to sync '{ev['title']}': {err_str}")
                
        now_str = datetime.now().strftime("%b %d, %I:%M %p")
        new_reason = f"Pushed {synced_this} event(s) to Google Calendar on {now_str}."
        c.execute("UPDATE processed_emails_v2 SET status='added', reason=? WHERE user_id=? AND account=? AND id=?", (new_reason, user_id, acc, uid))
        
    conn.commit()
    conn.close()
    return {"status": "success", "synced": total_synced, "errors": all_errors}

@app.get("/api/logs", dependencies=[Depends(verify_auth)])
def get_logs():
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
@app.get("/dashboard")
@app.get("/history")
@app.get("/groceries")
@app.get("/settings")
@app.get("/users")
@app.get("/logs")
async def read_index():
    return FileResponse('static/index.html')

@app.get("/privacy")
async def privacy_policy():
    return Response(
        content="""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Privacy Policy - AI Helper</title>
<style>body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333;}</style>
</head><body>
<h1>Privacy Policy</h1>
<p>AI Helper is a self-hosted personal application for scanning emails and syncing calendar events.</p>
<p>All data is processed locally on your own private server and is not shared with or sold to third parties.</p>
</body></html>""",
        media_type="text/html"
    )

@app.get("/terms")
async def terms_of_service():
    return Response(
        content="""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Terms of Service - AI Helper</title>
<style>body{font-family:sans-serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.6;color:#333;}</style>
</head><body>
<h1>Terms of Service</h1>
<p>AI Helper is a private, personal utility provided for individual productivity and calendar management.</p>
</body></html>""",
        media_type="text/html"
    )

# =====================================================================
# --- Grocery Deals & Smart Lists Module ---
# =====================================================================

class GroceryStoreSave(BaseModel):
    id: Optional[str] = None
    name: str
    ad_url: str
    notes: Optional[str] = ""

class GroceryListSave(BaseModel):
    id: Optional[str] = None
    title: str

class GroceryItemSave(BaseModel):
    id: Optional[str] = None
    list_id: str
    item_name: str
    store_name: Optional[str] = "Any"
    price_notes: Optional[str] = ""
    category: Optional[str] = "General"
    is_checked: Optional[int] = 0
    image_url: Optional[str] = ""

class GroceryBatchItemsSave(BaseModel):
    list_id: str
    items: List[dict]

class DealQueryRequest(BaseModel):
    query: str
    store_ids: Optional[List[str]] = None

class AIGroceryListRequest(BaseModel):
    list_id: Optional[str] = None
    list_title: Optional[str] = "Weekly Meal Plan & Deals"
    prompt: str

class AutoFetchDealsRequest(BaseModel):
    postal_code: Optional[str] = "76262"

class PreferencesUpdateRequest(BaseModel):
    favorite_categories: Optional[List[str]] = None
    ignored_categories: Optional[List[str]] = None
    liked_keywords: Optional[List[str]] = None
    disliked_keywords: Optional[List[str]] = None

class FeedbackActionRequest(BaseModel):
    item_name: str
    category: Optional[str] = ""
    action: str # "more", "less", "hide_category"

DEFAULT_DEAL_PREFERENCES = {
    "favorite_categories": ["Meat & Seafood", "Produce"],
    "ignored_categories": ["Furniture & Patio", "Canned Goods & Soups"],
    "liked_keywords": ["steak", "ribeye", "brisket", "beef", "chicken", "bacon", "salmon", "pork", "wings", "eggs"],
    "disliked_keywords": ["patio", "chair", "canned soup", "furniture", "umbrella"]
}

def get_user_deal_preferences(settings: dict) -> dict:
    prefs = settings.get("deal_preferences")
    if not isinstance(prefs, dict):
        return {k: list(v) for k, v in DEFAULT_DEAL_PREFERENCES.items()}
    return {
        "favorite_categories": list(prefs.get("favorite_categories", DEFAULT_DEAL_PREFERENCES["favorite_categories"])),
        "ignored_categories": list(prefs.get("ignored_categories", DEFAULT_DEAL_PREFERENCES["ignored_categories"])),
        "liked_keywords": list(prefs.get("liked_keywords", DEFAULT_DEAL_PREFERENCES["liked_keywords"])),
        "disliked_keywords": list(prefs.get("disliked_keywords", DEFAULT_DEAL_PREFERENCES["disliked_keywords"]))
    }

def guess_deal_category(item_name: str) -> str:
    name = (item_name or '').lower()
    # Meat & Seafood (prioritized)
    if any(w in name for w in ['beef', 'steak', 'chicken', 'pork', 'rib', 'roast', 'bacon', 'salmon', 'fish', 'shrimp', 'lobster', 'crab', 'turkey', 'sausage', 'chop', 'wings', 'meat', 'patty', 'patties', 'frank', 'hot dog', 'ground chuck', 'ground round', 'brisket', 'sirloin', 'ribeye', 'tenderloin', 't-bone', 'drumstick', 'thigh', 'tender', 'cod', 'tilapia', 'halibut', 'tuna', 'ham', 'lamb', 'veal', 'loin', 'filet', 'brats', 'bratwurst', 'meatballs', 't-bone', 'strip']):
        return 'Meat & Seafood'
    # Furniture & Patio
    if any(w in name for w in ['patio', 'furniture', 'chair', 'table', 'umbrella', 'gazebo', 'cushion', 'grill tool', 'fire pit', 'outdoor seating', 'recliner', 'bench', 'lounger', 'lawn mower', 'adirondack', 'planter', 'storage box', 'hammock', 'canopy']):
        return 'Furniture & Patio'
    # Canned Goods & Soups
    if any(w in name for w in ['soup', 'campbell', 'progresso', 'canned', 'broth', 'bouillon', 'canned beans', 'canned corn', 'canned tomato', 'spaghetti-o']):
        return 'Canned Goods & Soups'
    # Produce
    if any(w in name for w in ['apple', 'berry', 'berries', 'grape', 'banana', 'peach', 'melon', 'watermelon', 'cantaloupe', 'salad', 'lettuce', 'tomato', 'potato', 'onion', 'avocado', 'zucchini', 'vegetable', 'fruit', 'lemon', 'lime', 'citrus', 'nectarine', 'cherry', 'spinach', 'kale', 'carrot', 'broccoli', 'asparagus', 'cucumber', 'pepper', 'bell pepper', 'squash', 'mango', 'pineapple', 'strawberries', 'blueberries', 'raspberries', 'mushrooms', 'garlic', 'celery']):
        return 'Produce'
    # Dairy & Eggs
    if any(w in name for w in ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'egg', 'eggs', 'dairy', 'sour cream', 'creamer', 'cheddar', 'mozzarella', 'parmesan', 'swiss', 'cottage cheese', 'half & half', 'half and half']):
        return 'Dairy & Eggs'
    # Frozen
    if any(w in name for w in ['frozen', 'ice cream', 'pizza', 'novelties', 'fillet', 'waffles', 'popsicle', 'icecream', 'gelato', 'tater tots', 'hot pockets']):
        return 'Frozen'
    # Beverages
    if any(w in name for w in ['water', 'soda', 'coke', 'pepsi', 'drink', 'coffee', 'tea', 'juice', 'beer', 'wine', 'gatorade', 'shake', 'beverage', 'seltzer', 'dr pepper', 'sprite', 'lemonade', 'sparkling water', 'energy drink']):
        return 'Beverages'
    # Bakery & Deli
    if any(w in name for w in ['bread', 'buns', 'bakery', 'cake', 'pie', 'cookie', 'deli', 'croissant', 'tortilla', 'bagel', 'muffin', 'pastry', 'donut', 'cupcake', 'sourdough', 'rolls', 'sub sandwich', 'rotisserie']):
        return 'Bakery & Deli'
    # Snacks
    if any(w in name for w in ['chip', 'snack', 'candy', 'chocolate', 'nuts', 'cracker', 'popcorn', 'pretzels', 'doritos', 'lays', 'cheetos', 'tortilla chips', 'trail mix', 'granola bar', 'gummies']):
        return 'Snacks'
    # Household & Personal
    if any(w in name for w in ['paper', 'towel', 'detergent', 'tide', 'shampoo', 'soap', 'cleaner', 'swiffer', 'bleach', 'tissue', 'foil', 'wipe', 'diaper', 'trash bag', 'toothpaste', 'deodorant', 'body wash', 'fabric softener', 'dish soap', 'ziploc', 'charcoal']):
        return 'Household & Personal'
    return 'Pantry & Dry Goods'

def normalize_grocery_store_name(merchant_raw: str) -> str:
    m = (merchant_raw or '').strip()
    ml = m.lower()
    if 'kroger' in ml: return 'Kroger'
    if 'sprouts' in ml: return 'Sprouts Farmers Market'
    if 'tom thumb' in ml: return 'Tom Thumb'
    if 'albertsons' in ml: return 'Albertsons'
    if 'h-e-b' in ml or 'heb' in ml: return 'H-E-B'
    if 'aldi' in ml: return 'ALDI'
    if 'walmart' in ml: return 'Walmart'
    if 'target' in ml: return 'Target'
    if 'costco' in ml: return 'Costco'
    if 'fiesta' in ml: return 'Fiesta Mart'
    if 'whole foods' in ml: return 'Whole Foods Market'
    if 'trader joe' in ml: return "Trader Joe's"
    if 'winco' in ml: return 'WinCo Foods'
    if 'brookshire' in ml: return "Brookshire's"
    if 'market street' in ml: return 'Market Street'
    if 'united' in ml: return 'United Supermarkets'
    return m

def parse_numeric_price(price_str: str) -> dict:
    if not price_str or not isinstance(price_str, str):
        return {'unit_price': None, 'unit': 'unknown', 'raw': ''}
    
    raw = price_str.strip()
    raw_lower = raw.lower()
    
    if 'bogo' in raw_lower or 'buy 1 get 1' in raw_lower or 'buy one get one' in raw_lower:
        return {'unit_price': None, 'unit': 'bogo', 'raw': raw}
        
    m_lb = re.search(r'\$?([0-9]+(?:\.[0-9]{1,2})?)\s*(?:/|\s+per\s+|\s+)?(?:lb|lbs|pound)\b', raw_lower)
    if m_lb:
        try:
            return {'unit_price': float(m_lb.group(1)), 'unit': 'lb', 'raw': raw}
        except Exception:
            pass
            
    m_multi = re.search(r'(\d+)\s+(?:for|/)\s+\$?([0-9]+(?:\.[0-9]{1,2})?)', raw_lower)
    if m_multi:
        try:
            qty = float(m_multi.group(1))
            total = float(m_multi.group(2))
            if qty > 0:
                return {'unit_price': round(total / qty, 2), 'unit': 'ea', 'raw': raw}
        except Exception:
            pass
            
    m_simple = re.search(r'\$?([0-9]+(?:\.[0-9]{1,2})?)', raw_lower)
    if m_simple:
        try:
            val = float(m_simple.group(1))
            unit = 'lb' if ('/lb' in raw_lower or 'per lb' in raw_lower) else 'ea'
            return {'unit_price': val, 'unit': unit, 'raw': raw}
        except Exception:
            pass
            
    return {'unit_price': None, 'unit': 'unknown', 'raw': raw}

def normalize_item_tokens(item_name: str) -> set:
    if not item_name:
        return set()
    cleaned = item_name.lower()
    cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:oz|lb|lbs|ct|pk|pack|count|fl\s*oz|gal|gallon|qt|pt|liter|l|ml|kg|g)\b', ' ', cleaned)
    cleaned = re.sub(r'\b\d+/\d+\b', ' ', cleaned)
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    
    stop_words = {
        'fresh', 'organic', 'usda', 'choice', 'prime', 'select', 'all', 'natural', 'frozen',
        'great', 'value', 'signature', 'h-e-b', 'heb', 'kroger', 'market', 'pantry',
        'family', 'pack', 'super', 'size', 'selected', 'varieties', 'brand', 'assorted', 'large',
        'small', 'medium', 'jumbo', 'grade', 'a', 'aa', 'free', 'range', 'cage', 'wild', 'caught',
        'farm', 'raised', 'boneless', 'skinless', 'bone', 'in', 'center', 'cut', 'thin', 'sliced',
        'thick', 'whole', 'half', 'quarter', 'the', 'and', 'or', 'with', 'in', 'for', 'of', 'item', 'lb', 'lbs'
    }
    return {w for w in cleaned.split() if len(w) > 2 and w not in stop_words}

def find_cross_store_comparison(current_item_name: str, current_store: str, current_price_str: str, current_category: str, all_stores_deals: list) -> dict:
    curr_parsed = parse_numeric_price(current_price_str)
    curr_price_val = curr_parsed.get('unit_price')
    curr_unit = curr_parsed.get('unit')
    curr_tokens = normalize_item_tokens(current_item_name)
    norm_curr_store = normalize_grocery_store_name(current_store).lower()

    matches = []
    
    for s in all_stores_deals:
        s_name = s.get('name', '')
        if normalize_grocery_store_name(s_name).lower() == norm_curr_store:
            continue
            
        deals = s.get('deals', [])
        for d in deals:
            d_name = d.get('item', '')
            d_cat = d.get('category', '')
            
            if current_category and d_cat and current_category not in ['General', ''] and d_cat not in ['General', ''] and current_category != d_cat:
                continue
                
            d_tokens = normalize_item_tokens(d_name)
            if not curr_tokens or not d_tokens:
                continue
                
            overlap = curr_tokens.intersection(d_tokens)
            if len(overlap) >= min(2, len(curr_tokens)) and (len(overlap) / max(len(curr_tokens), 1)) >= 0.5:
                d_parsed = parse_numeric_price(d.get('price', ''))
                matches.append({
                    'store': s_name,
                    'item': d_name,
                    'price_str': d.get('price', ''),
                    'parsed': d_parsed,
                    'overlap_count': len(overlap)
                })

    if not matches:
        return {
            'has_match': False,
            'is_best': True,
            'badge_type': 'neutral',
            'summary': 'Store Special / Great Value',
            'diff_text': '',
            'other_prices': []
        }

    matches_with_price = [m for m in matches if m['parsed']['unit_price'] is not None and (curr_unit == 'unknown' or m['parsed']['unit'] == curr_unit or curr_unit is None)]
    
    if curr_price_val is not None and matches_with_price:
        lowest_other = min(matches_with_price, key=lambda m: m['parsed']['unit_price'])
        lowest_val = lowest_other['parsed']['unit_price']
        lowest_store = lowest_other['store']
        lowest_price_str = lowest_other['price_str']
        
        diff = round(curr_price_val - lowest_val, 2)
        unit_suffix = "/lb" if curr_unit == 'lb' else ""
        
        if diff <= -0.10:
            savings = abs(diff)
            return {
                'has_match': True,
                'is_best': True,
                'badge_type': 'green',
                'summary': f"✓ Best Price! Save ${savings:.2f}{unit_suffix} vs {lowest_store} ({lowest_price_str})",
                'diff_text': f"Cheaper by ${savings:.2f}{unit_suffix}",
                'best_store': current_store,
                'lowest_other_store': lowest_store,
                'lowest_other_price': lowest_price_str,
                'other_prices': [{'store': m['store'], 'price': m['price_str'], 'item': m['item']} for m in matches[:3]]
            }
        elif diff >= 0.10:
            cheaper_by = diff
            return {
                'has_match': True,
                'is_best': False,
                'badge_type': 'red',
                'summary': f"⚠️ Cheaper at {lowest_store} ({lowest_price_str}) — Save ${cheaper_by:.2f}{unit_suffix}",
                'diff_text': f"{lowest_store} is ${cheaper_by:.2f}{unit_suffix} cheaper",
                'best_store': lowest_store,
                'lowest_other_store': lowest_store,
                'lowest_other_price': lowest_price_str,
                'other_prices': [{'store': m['store'], 'price': m['price_str'], 'item': m['item']} for m in matches[:3]]
            }
        else:
            return {
                'has_match': True,
                'is_best': True,
                'badge_type': 'green',
                'summary': f"✓ Matching Lowest Price (also {lowest_price_str} at {lowest_store})",
                'diff_text': "Matched price",
                'best_store': current_store,
                'other_prices': [{'store': m['store'], 'price': m['price_str'], 'item': m['item']} for m in matches[:3]]
            }
    else:
        first_other = matches[0]
        return {
            'has_match': True,
            'is_best': True,
            'badge_type': 'neutral',
            'summary': f"Also on sale at {first_other['store']} ({first_other['price_str']})",
            'diff_text': '',
            'other_prices': [{'store': m['store'], 'price': m['price_str'], 'item': m['item']} for m in matches[:3]]
        }

def _fetch_single_flipp_flyer(f: dict, postal_code: str, headers: dict, ctx: ssl.SSLContext, norm_store: str):
    fid = f.get('id')
    if not fid:
        return norm_store, fid, f, []
    furl = f"https://backflipp.wishabi.com/flipp/flyers/{fid}"
    try:
        freq = urllib.request.Request(furl, headers=headers)
        with urllib.request.urlopen(freq, timeout=8, context=ctx) as fresp:
            fdata = json.loads(fresp.read().decode('utf-8'))
            items = fdata.get('items', [])
            
            deals = []
            seen_names = set()
            
            for it in items:
                name = it.get('name')
                if not name or len(name.strip()) < 2:
                    continue
                clean_name = name.strip()
                if clean_name.lower() in seen_names:
                    continue
                seen_names.add(clean_name.lower())
                
                raw_price = it.get('price') or it.get('current_price') or ''
                sale_story = it.get('sale_story') or ''
                price_str = ''
                if raw_price:
                    try:
                        fval = float(raw_price)
                        price_str = f"${fval:.2f}"
                    except Exception:
                        price_str = str(raw_price)
                elif sale_story:
                    price_str = sale_story
                else:
                    price_str = "Sale"
                    
                notes_parts = []
                if sale_story and sale_story != price_str:
                    notes_parts.append(sale_story)
                if it.get('description'):
                    notes_parts.append(it.get('description'))
                if it.get('brand') and it.get('brand') not in clean_name:
                    notes_parts.append(f"Brand: {it.get('brand')}")
                    
                notes_str = " | ".join(notes_parts)
                img_url = it.get('cutout_image_url') or it.get('clean_image_url') or it.get('clipping_image_url') or it.get('image_url') or it.get('original_image_url') or ''
                
                deals.append({
                    'item': clean_name,
                    'price': price_str,
                    'category': guess_deal_category(clean_name),
                    'notes': notes_str,
                    'image_url': img_url
                })
            return norm_store, fid, f, deals
    except Exception as e:
        logger.warning(f"Error fetching Flipp flyer {fid} for {norm_store}: {e}")
        return norm_store, fid, f, []

def _enrich_single_store_search(store_name: str, postal_code: str, headers: dict, ctx: ssl.SSLContext):
    try:
        q_url = f"https://backflipp.wishabi.com/flipp/items/search?postal_code={postal_code}&q={urllib.parse.quote_plus(store_name)}"
        s_req = urllib.request.Request(q_url, headers=headers)
        with urllib.request.urlopen(s_req, timeout=6, context=ctx) as s_resp:
            s_data = json.loads(s_resp.read().decode('utf-8'))
            return store_name, s_data.get('items', [])
    except Exception as e:
        logger.debug(f"Search enrichment error for {store_name}: {e}")
        return store_name, []

def fetch_flipp_store_deals(postal_code: str = '76262', store_name_filter: Optional[str] = None) -> dict:
    if not postal_code or not postal_code.strip():
        postal_code = '76262'
    postal_code = postal_code.strip()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = f"https://backflipp.wishabi.com/flipp/flyers?postal_code={postal_code}&locale=en-us"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            flyer_data = json.loads(resp.read().decode('utf-8'))
            flyers = flyer_data.get('flyers', [])
    except Exception as e:
        logger.error(f"Error querying Flipp flyers for zip {postal_code}: {e}")
        return {}

    known_grocery_keywords = [
        'kroger', 'h-e-b', 'heb', 'tom thumb', 'albertsons', 'sprouts',
        'aldi', 'walmart', 'target', 'fiesta', 'costco', 'winco',
        'whole foods', 'trader joe', 'brookshire', 'market street', 'united supermarkets', 'bravo'
    ]
    
    stores_data = {}
    target_filter_norm = normalize_grocery_store_name(store_name_filter).lower() if store_name_filter else None

    matched_flyers = []
    for f in flyers:
        merchant = f.get('merchant') or ''
        merchant_lower = merchant.lower()
        
        # Check if grocery merchant or specifically targeted
        if not any(kw in merchant_lower for kw in known_grocery_keywords):
            if not target_filter_norm or target_filter_norm not in merchant_lower:
                continue
            
        norm_store = normalize_grocery_store_name(merchant)
        if target_filter_norm and target_filter_norm not in norm_store.lower() and norm_store.lower() not in target_filter_norm:
            continue
            
        matched_flyers.append((f, norm_store))

    if not matched_flyers:
        return {}

    # Parallel flyer item fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_single_flipp_flyer, f, postal_code, headers, ctx, nstore) for f, nstore in matched_flyers]
        for fut in as_completed(futures):
            try:
                norm_store, fid, f, deals = fut.result()
                if deals:
                    ad_web_url = f"https://flipp.com/flyer/{fid}?postal_code={postal_code}"
                    if norm_store not in stores_data:
                        stores_data[norm_store] = {
                            'name': norm_store,
                            'ad_url': ad_web_url,
                            'flyer_id': fid,
                            'flyer_title': f.get('title') or f"{norm_store} Weekly Ad",
                            'valid_from': f.get('valid_from'),
                            'valid_to': f.get('valid_to'),
                            'deals': deals
                        }
                    else:
                        existing_items = {d['item'].lower() for d in stores_data[norm_store]['deals']}
                        for d in deals:
                            if d['item'].lower() not in existing_items:
                                stores_data[norm_store]['deals'].append(d)
                                existing_items.add(d['item'].lower())
            except Exception as ex:
                logger.warning(f"Error processing flyer response: {ex}")

    # Parallel search enrichment for rich sale prices and coupon stories
    store_names = list(stores_data.keys())
    if store_names:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_enrich_single_store_search, sname, postal_code, headers, ctx) for sname in store_names]
            for fut in as_completed(futures):
                try:
                    sname, s_items = fut.result()
                    if sname in stores_data and s_items:
                        store_deals = stores_data[sname]['deals']
                        existing_map = {d['item'].lower(): d for d in store_deals}
                        
                        for sit in s_items:
                            s_name = (sit.get('name') or '').strip()
                            if not s_name:
                                continue
                            
                            s_price = sit.get('current_price')
                            s_sale = sit.get('sale_story')
                            s_price_str = f"${float(s_price):.2f}" if s_price is not None else (s_sale or "")
                            s_img = sit.get('cutout_image_url') or sit.get('clean_image_url') or sit.get('clipping_image_url') or sit.get('image_url') or sit.get('original_image_url') or ''
                            
                            if s_name.lower() in existing_map:
                                cur_deal = existing_map[s_name.lower()]
                                if (cur_deal['price'] == 'Sale' or not cur_deal['price']) and s_price_str:
                                    cur_deal['price'] = s_price_str
                                if s_sale and s_sale not in cur_deal.get('notes', ''):
                                    cur_deal['notes'] = f"{s_sale} | {cur_deal.get('notes', '')}".strip(" |")
                                if not cur_deal.get('image_url') and s_img:
                                    cur_deal['image_url'] = s_img
                            else:
                                if s_price_str or s_sale:
                                    new_deal = {
                                        'item': s_name,
                                        'price': s_price_str or "Sale",
                                        'category': guess_deal_category(s_name),
                                        'notes': s_sale or "",
                                        'image_url': s_img
                                    }
                                    store_deals.append(new_deal)
                                    existing_map[s_name.lower()] = new_deal
                except Exception as e:
                    logger.debug(f"Search enrichment error for {sname}: {e}")
            
    return stores_data

# Web content fetcher for store ads
def fetch_url_clean_content(url: str) -> str:
    if not url or not url.startswith(("http://", "https://")):
        return ""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=12, context=ctx) as response:
            html_bytes = response.read(500000)
            charset = response.headers.get_content_charset() or 'utf-8'
            html_str = html_bytes.decode(charset, errors='replace')
            return clean_page_html(html_str)
    except Exception as e:
        logger.warning(f"Error fetching weekly ad content from {url}: {e}")
        return ""

def extract_store_deals_with_ai(store_name: str, page_content: str, settings: dict) -> list:
    if not page_content or len(page_content.strip()) < 20:
        return []
    
    prompt = f"""
    You are an expert grocery bargain hunter. Extract all weekly sales, discounts, price cuts, and grocery deals from the provided store circular / weekly ad text for '{store_name}'.
    
    Return your response strictly as a JSON array of objects with the following keys:
    - "item": Name of the product or item (e.g. "USDA Choice Ribeye Steak", "Honeycrisp Apples", "Large Grade A Eggs 18ct", "Organic Whole Milk 1gal", "Tide Pods 42ct")
    - "price": Price or sale text (e.g. "$6.99/lb", "$0.99/lb", "2 for $5.00", "Buy 1 Get 1 Free", "$3.49")
    - "category": Category (one of: "Meat & Seafood", "Produce", "Dairy & Eggs", "Pantry & Dry Goods", "Bakery & Deli", "Frozen", "Beverages", "Household & Personal", "Snacks")
    - "notes": Any specific sale details, requirements (e.g. "Digital coupon required", "Must buy 2", "Valid through Tuesday", "Limit 4")
    
    Do not invent items that are not in the text.
    
    Weekly Ad Text:
    {page_content[:25000]}
    """
    
    provider = settings.get("ai_provider", "gemini")
    model_name = settings.get("ai_model", "gemini-1.5-flash") or "gemini-1.5-flash"
    result_text = ""
    try:
        if provider == "gemini":
            api_key = settings.get("gemini_api_key", "")
            if not api_key: return []
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            result_text = response.text
        elif provider == "openai":
            api_key = settings.get("openai_api_key", "")
            if not api_key: return []
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You extract grocery deals and return pure valid JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            result_text = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error extracting store deals for {store_name}: {e}")
        return []
        
    try:
        cleaned = re.sub(r'^```json\s*', '', result_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for k in ["deals", "items", "sales", "products"]:
                if k in data and isinstance(data[k], list):
                    return data[k]
        return []
    except Exception as parse_err:
        logger.warning(f"Could not parse deals JSON for {store_name}: {parse_err}")
        return []

def query_ai_deals_and_prices(user_query: str, store_deals_data: list, settings: dict) -> dict:
    deals_summary = []
    for store in store_deals_data:
        store_name = store.get("name", "Store")
        deals = store.get("deals", [])
        if deals:
            deals_summary.append(f"=== STORE: {store_name} ({len(deals)} items on sale) ===\n" + 
                                 "\n".join([f"- {d.get('item')}: {d.get('price')} [{d.get('category', 'General')}] {d.get('notes', '')}" for d in deals[:45]]))
        else:
            deals_summary.append(f"=== STORE: {store_name} (Weekly Ad configured: {store.get('ad_url', '')}) ===")
    
    all_deals_text = "\n\n".join(deals_summary) if deals_summary else "No cached circulars. Use market pricing knowledge for HEB, Kroger, Tom Thumb, Costco, Sprouts, Whole Foods, and Walmart."

    prompt = f"""
    You are an expert grocery bargain hunter and smart shopping assistant.
    The user is asking: "{user_query}"
    
    Available Local Store Weekly Deals & Circulars:
    {all_deals_text[:25000]}
    
    Instructions:
    1. Answer the user's inquiry thoroughly. Compare prices across stores (e.g. Kroger, Tom Thumb, HEB, Costco, Sprouts, Whole Foods, Walmart, etc.).
    2. Suggest which store has the best deal or value for each item requested.
    3. Include practical shopping advice (e.g. bulk buying at Costco vs produce at Sprouts/HEB vs weekly digital coupons at Kroger/Tom Thumb).
    4. Provide a structured JSON array of recommended items to add to the user's grocery list.
    
    Format your response strictly as a JSON object with two fields:
    - "analysis_markdown": A comprehensive, well-formatted Markdown response with headers, comparison tables/bullets, and tips.
    - "items": Array of item objects:
       - "item_name": Product name (string)
       - "store_name": Best store name (e.g. "HEB", "Costco", "Kroger", etc.)
       - "price_notes": Price or deal info (e.g. "$6.99/lb (Save $3/lb)", "$0.99/lb", "BOGO")
       - "category": Category ("Meat & Seafood", "Produce", "Dairy & Eggs", "Pantry", "Snacks", "Household")
    """
    
    provider = settings.get("ai_provider", "gemini")
    model_name = settings.get("ai_model", "gemini-1.5-flash") or "gemini-1.5-flash"
    result_text = ""
    try:
        if provider == "gemini":
            api_key = settings.get("gemini_api_key", "")
            if not api_key: return {"error": "Gemini API key missing in Settings"}
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            result_text = response.text
        elif provider == "openai":
            api_key = settings.get("openai_api_key", "")
            if not api_key: return {"error": "OpenAI API key missing in Settings"}
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You compare grocery prices and return JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            result_text = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error running grocery deal query: {e}")
        return {"error": str(e)}
        
    try:
        cleaned = re.sub(r'^```json\s*', '', result_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        return data
    except Exception as parse_err:
        logger.warning(f"Could not parse grocery query JSON: {parse_err}")
        return {
            "analysis_markdown": result_text,
            "items": []
        }

def ai_generate_grocery_list_items(prompt_text: str, store_deals_data: list, settings: dict) -> list:
    deals_summary = []
    for store in store_deals_data:
        store_name = store.get("name", "Store")
        deals = store.get("deals", [])
        if deals:
            deals_summary.append(f"{store_name} Sales: " + ", ".join([f"{d.get('item')} ({d.get('price')})" for d in deals[:25]]))
    
    context = "\n".join(deals_summary)
    prompt = f"""
    Create a detailed, organized grocery list based on the user request: "{prompt_text}".
    
    Current Store Sales Context:
    {context[:15000]}
    
    Return strictly a JSON array of objects:
    - "item_name": Product name (string)
    - "store_name": Store name (e.g. "HEB", "Costco", "Kroger", "Sprouts", "Walmart", "Any")
    - "price_notes": Sale price or estimated budget note (e.g. "$3.99/lb", "Buy in bulk", "On sale")
    - "category": Category ("Produce", "Meat & Seafood", "Dairy & Eggs", "Pantry & Dry Goods", "Bakery", "Frozen", "Beverages", "Household", "Snacks")
    """
    
    provider = settings.get("ai_provider", "gemini")
    model_name = settings.get("ai_model", "gemini-1.5-flash") or "gemini-1.5-flash"
    result_text = ""
    try:
        if provider == "gemini":
            api_key = settings.get("gemini_api_key", "")
            if not api_key: return []
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            result_text = response.text
        elif provider == "openai":
            api_key = settings.get("openai_api_key", "")
            if not api_key: return []
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You build grocery lists and return valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ]
            )
            result_text = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating grocery list with AI: {e}")
        return []
        
    try:
        cleaned = re.sub(r'^```json\s*', '', result_text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for k in ["items", "grocery_list", "list"]:
                if k in data and isinstance(data[k], list):
                    return data[k]
        return []
    except Exception as parse_err:
        logger.warning(f"Could not parse AI grocery list items JSON: {parse_err}")
        return []

# --- Store Management Endpoints ---
@app.get("/api/groceries/stores")
def get_grocery_stores(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, notes, last_scanned, cached_deals FROM grocery_stores WHERE user_id=? ORDER BY name ASC", (user_id,))
    rows = c.fetchall()
    conn.close()
    
    stores = []
    for r in rows:
        d = dict(r)
        deals = []
        if d.get("cached_deals"):
            try: deals = json.loads(d["cached_deals"])
            except Exception: deals = []
        d["deals_count"] = len(deals)
        d["deals_preview"] = deals[:5]
        stores.append(d)
    return stores

@app.post("/api/groceries/stores")
def save_grocery_store(store: GroceryStoreSave, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    store_id = store.id or str(uuid.uuid4())
    c.execute("SELECT id FROM grocery_stores WHERE id=? AND user_id=?", (store_id, user_id))
    if c.fetchone():
        c.execute("UPDATE grocery_stores SET name=?, ad_url=?, notes=? WHERE id=? AND user_id=?", 
                  (store.name, store.ad_url, store.notes or "", store_id, user_id))
    else:
        c.execute("INSERT INTO grocery_stores (id, user_id, name, ad_url, notes, last_scanned, cached_deals) VALUES (?, ?, ?, ?, ?, NULL, NULL)",
                  (store_id, user_id, store.name, store.ad_url, store.notes or ""))
    conn.commit()
    conn.close()
    return {"status": "success", "id": store_id}

@app.delete("/api/groceries/stores/{store_id}")
def delete_grocery_store(store_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM grocery_stores WHERE id=? AND user_id=?", (store_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

class StoreTextParseRequest(BaseModel):
    text_content: str

@app.post("/api/groceries/stores/{store_id}/parse_text", dependencies=[Depends(verify_auth)])
def parse_store_text_deals(store_id: str, req: StoreTextParseRequest, user_id: str = Depends(verify_auth)):
    if not req.text_content or len(req.text_content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text content is too short to extract deals.")
        
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name FROM grocery_stores WHERE id=? AND user_id=?", (store_id, user_id))
    store = c.fetchone()
    if not store:
        conn.close()
        raise HTTPException(status_code=404, detail="Store not found")
        
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    
    deals = extract_store_deals_with_ai(store["name"], req.text_content, settings)
    now_iso = datetime.now().isoformat()
    
    c.execute("UPDATE grocery_stores SET last_scanned=?, cached_deals=? WHERE id=? AND user_id=?",
              (now_iso, json.dumps(deals), store_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "deals_found": len(deals), "deals": deals}

@app.post("/api/groceries/auto_fetch", dependencies=[Depends(verify_auth)])
def auto_fetch_local_deals(req: AutoFetchDealsRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    
    postal_code = (req.postal_code or settings.get("postal_code", "76262")).strip()
    if not postal_code:
        postal_code = "76262"
        
    settings["postal_code"] = postal_code
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    
    stores_data = fetch_flipp_store_deals(postal_code)
    if not stores_data:
        conn.commit()
        conn.close()
        return {
            "status": "warning",
            "message": f"No digital weekly circulars found for postal code {postal_code}. Please verify the zip code.",
            "stores_count": 0,
            "total_deals": 0,
            "stores": []
        }
        
    now_iso = datetime.now().isoformat()
    updated_stores = []
    
    c.execute("SELECT id, name FROM grocery_stores WHERE user_id=?", (user_id,))
    existing_stores = {r["name"].lower(): r["id"] for r in c.fetchall()}
    
    total_deals_count = 0
    for sname, sinfo in stores_data.items():
        deals = sinfo.get("deals", [])
        total_deals_count += len(deals)
        deals_json = json.dumps(deals)
        ad_url = sinfo.get("ad_url", "")
        valid_range = f"Valid: {sinfo.get('valid_from', '')[:10]} to {sinfo.get('valid_to', '')[:10]}" if sinfo.get('valid_to') else ""
        
        norm_key = sname.lower()
        if norm_key in existing_stores:
            store_id = existing_stores[norm_key]
            c.execute(
                "UPDATE grocery_stores SET name=?, ad_url=?, notes=?, last_scanned=?, cached_deals=? WHERE id=? AND user_id=?",
                (sname, ad_url, valid_range, now_iso, deals_json, store_id, user_id)
            )
        else:
            store_id = str(uuid.uuid4())
            c.execute(
                "INSERT INTO grocery_stores (id, user_id, name, ad_url, notes, last_scanned, cached_deals) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (store_id, user_id, sname, ad_url, valid_range, now_iso, deals_json)
            )
            existing_stores[norm_key] = store_id
            
        updated_stores.append({
            "id": store_id,
            "name": sname,
            "deals_count": len(deals),
            "ad_url": ad_url,
            "valid_range": valid_range
        })
        
    conn.commit()
    conn.close()
    
    return {
        "status": "success",
        "postal_code": postal_code,
        "stores_count": len(updated_stores),
        "total_deals": total_deals_count,
        "stores": updated_stores
    }

@app.post("/api/groceries/stores/{store_id}/scan")
def scan_grocery_store(store_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url FROM grocery_stores WHERE id=? AND user_id=?", (store_id, user_id))
    store = c.fetchone()
    if not store:
        conn.close()
        raise HTTPException(status_code=404, detail="Store not found")
        
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    postal_code = settings.get("postal_code", "76262")
    
    url = store["ad_url"] or ""
    name = store["name"]
    
    deals = []
    now_iso = datetime.now().isoformat()
    warning_msg = None
    
    # Try automatic Flipp lookup first
    flipp_stores = fetch_flipp_store_deals(postal_code, store_name_filter=name)
    if flipp_stores:
        matched_info = list(flipp_stores.values())[0]
        deals = matched_info.get("deals", [])
        if matched_info.get("ad_url"):
            url = matched_info["ad_url"]
    
    # If not on Flipp or Flipp returned 0, try direct web content fetch + AI
    if not deals and url and url.startswith(("http://", "https://")) and "flipp.com" not in url:
        content = fetch_url_clean_content(url)
        deals = extract_store_deals_with_ai(name, content, settings)
        if not deals and (not content or len(content.strip()) < 50):
            warning_msg = f"Could not read circular text from {url}. Supermarkets (like Kroger, Tom Thumb, and HEB) block scrapers without cookies. Tip: Use 1-Click Auto-Fetch Deals by Zip Code or click '📋 Paste Deals' to paste flyer text directly!"
            
    c.execute("UPDATE grocery_stores SET ad_url=?, last_scanned=?, cached_deals=? WHERE id=? AND user_id=?",
              (url, now_iso, json.dumps(deals), store_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "deals_found": len(deals), "deals": deals, "warning": warning_msg}

@app.post("/api/groceries/stores/scan_all")
def scan_all_grocery_stores(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url FROM grocery_stores WHERE user_id=?", (user_id,))
    stores = c.fetchall()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    postal_code = settings.get("postal_code", "76262")
    
    # Bulk fetch Flipp deals for all stores in parallel
    flipp_stores = fetch_flipp_store_deals(postal_code)
    
    results = []
    now_iso = datetime.now().isoformat()
    
    for s in stores:
        sname = s["name"]
        norm_key = normalize_grocery_store_name(sname)
        deals = []
        ad_url = s["ad_url"]
        
        if norm_key in flipp_stores:
            matched = flipp_stores[norm_key]
            deals = matched.get("deals", [])
            if matched.get("ad_url"):
                ad_url = matched["ad_url"]
        elif s["ad_url"] and s["ad_url"].startswith(("http://", "https://")) and "flipp.com" not in s["ad_url"]:
            content = fetch_url_clean_content(s["ad_url"])
            deals = extract_store_deals_with_ai(s["name"], content, settings)
            if settings.get("ai_provider", "gemini") == "gemini":
                time.sleep(2.0)
                
        c.execute("UPDATE grocery_stores SET ad_url=?, last_scanned=?, cached_deals=? WHERE id=? AND user_id=?",
                  (ad_url, now_iso, json.dumps(deals), s["id"], user_id))
        results.append({"store": s["name"], "deals_found": len(deals)})
            
    conn.commit()
    conn.close()
    return {"status": "success", "results": results}

# --- Deal Query & Price Finder Endpoint ---
@app.post("/api/groceries/query_deals")
def query_deals(req: DealQueryRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    conn.close()
    
    store_deals_data = []
    for r in rows:
        if req.store_ids and r["id"] not in req.store_ids:
            continue
        deals = []
        if r["cached_deals"]:
            try: deals = json.loads(r["cached_deals"])
            except Exception: deals = []
        store_deals_data.append({
            "name": r["name"],
            "ad_url": r["ad_url"],
            "deals": deals
        })
        
    res = query_ai_deals_and_prices(req.query, store_deals_data, settings)
    return res

# --- Preferences & Personalized Deal Feed Endpoints ---
@app.get("/api/groceries/preferences")
def get_grocery_preferences(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    conn.close()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    return get_user_deal_preferences(settings)

@app.post("/api/groceries/preferences")
def save_grocery_preferences(req: PreferencesUpdateRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    
    current_prefs = get_user_deal_preferences(settings)
    if req.favorite_categories is not None:
        current_prefs["favorite_categories"] = [cat.strip() for cat in req.favorite_categories if cat.strip()]
    if req.ignored_categories is not None:
        current_prefs["ignored_categories"] = [cat.strip() for cat in req.ignored_categories if cat.strip()]
    if req.liked_keywords is not None:
        current_prefs["liked_keywords"] = [k.strip().lower() for k in req.liked_keywords if k.strip()]
    if req.disliked_keywords is not None:
        current_prefs["disliked_keywords"] = [k.strip().lower() for k in req.disliked_keywords if k.strip()]
        
    settings["deal_preferences"] = current_prefs
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "preferences": current_prefs}

@app.post("/api/groceries/preferences/feedback")
def submit_deal_feedback(req: FeedbackActionRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    
    prefs = get_user_deal_preferences(settings)
    action = (req.action or '').lower().strip()
    item_tokens = list(normalize_item_tokens(req.item_name))
    
    if action == "more":
        for tok in item_tokens:
            if tok not in prefs["liked_keywords"]:
                prefs["liked_keywords"].append(tok)
            if tok in prefs["disliked_keywords"]:
                prefs["disliked_keywords"].remove(tok)
        if req.category and req.category not in prefs["favorite_categories"]:
            prefs["favorite_categories"].append(req.category)
        if req.category and req.category in prefs["ignored_categories"]:
            prefs["ignored_categories"].remove(req.category)
            
    elif action == "less":
        for tok in item_tokens[:3]:
            if tok not in prefs["disliked_keywords"]:
                prefs["disliked_keywords"].append(tok)
            if tok in prefs["liked_keywords"]:
                prefs["liked_keywords"].remove(tok)
                
    elif action == "hide_category":
        if req.category and req.category not in prefs["ignored_categories"]:
            prefs["ignored_categories"].append(req.category)
        if req.category and req.category in prefs["favorite_categories"]:
            prefs["favorite_categories"].remove(req.category)
            
    settings["deal_preferences"] = prefs
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "action": action, "preferences": prefs}

@app.get("/api/groceries/feed")
def get_personalized_deals_feed(category: Optional[str] = None, best_only: Optional[bool] = False, search: Optional[str] = None, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    conn.close()
    
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    prefs = get_user_deal_preferences(settings)
    
    fav_cats_set = {cat.lower() for cat in prefs.get("favorite_categories", [])}
    ign_cats_set = {cat.lower() for cat in prefs.get("ignored_categories", [])}
    liked_kw_set = {kw.lower() for kw in prefs.get("liked_keywords", [])}
    disliked_kw_set = {kw.lower() for kw in prefs.get("disliked_keywords", [])}
    
    all_stores = []
    all_raw_deals = []
    
    for r in rows:
        deals = []
        if r["cached_deals"]:
            try: deals = json.loads(r["cached_deals"])
            except Exception: deals = []
        all_stores.append({
            "id": r["id"],
            "name": r["name"],
            "ad_url": r["ad_url"],
            "deals": deals
        })
        for d in deals:
            all_raw_deals.append((r["name"], r["ad_url"], d))
            
    scored_deals = []
    search_term = (search or '').strip().lower()
    cat_filter = (category or '').strip().lower()
    
    for store_name, store_ad_url, deal in all_raw_deals:
        item_name = deal.get("item", "").strip()
        if not item_name:
            continue
            
        item_lower = item_name.lower()
        deal_cat = deal.get("category", "Pantry & Dry Goods")
        deal_cat_lower = deal_cat.lower()
        price_str = deal.get("price", "")
        notes_str = deal.get("notes", "")
        img_url = deal.get("image_url", "")
        
        # Category filter
        if cat_filter and cat_filter != 'all' and cat_filter not in deal_cat_lower and deal_cat_lower not in cat_filter:
            continue
            
        # Search filter
        if search_term and search_term not in item_lower and search_term not in notes_str.lower() and search_term not in store_name.lower():
            continue
            
        # Hard ignore categories
        if not cat_filter or cat_filter == 'all':
            if deal_cat_lower in ign_cats_set:
                continue
                
        # Hard ignore disliked keywords
        if any(dkw in item_lower for dkw in disliked_kw_set):
            continue
            
        # Calculate Score
        score = 0
        if deal_cat_lower in fav_cats_set:
            score += 60
            if 'meat' in deal_cat_lower:
                score += 30
        else:
            score += 15
            
        matched_liked = [kw for kw in liked_kw_set if kw in item_lower]
        score += len(matched_liked) * 35
        
        if img_url:
            score += 10
            
        comp = find_cross_store_comparison(item_name, store_name, price_str, deal_cat, all_stores)
        
        if comp.get('badge_type') == 'green':
            score += 30
        elif comp.get('badge_type') == 'red':
            score -= 15
            if best_only:
                continue
                
        scored_deals.append({
            "item": item_name,
            "store": store_name,
            "store_ad_url": store_ad_url,
            "price": price_str,
            "category": deal_cat,
            "notes": notes_str,
            "image_url": img_url,
            "score": score,
            "comparison": comp,
            "matched_keywords": matched_liked
        })
        
    scored_deals.sort(key=lambda d: d["score"], reverse=True)
    
    return {
        "status": "success",
        "total_available": len(all_raw_deals),
        "deals_count": len(scored_deals),
        "preferences": prefs,
        "deals": scored_deals[:150]
    }

# --- Grocery Lists & Items Endpoints ---
@app.get("/api/groceries/lists")
def get_grocery_lists(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, title, created_at, updated_at FROM grocery_lists WHERE user_id=? ORDER BY updated_at DESC", (user_id,))
    lists = [dict(r) for r in c.fetchall()]
    
    if not lists:
        def_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        c.execute("INSERT INTO grocery_lists (id, user_id, title, created_at, updated_at) VALUES (?, ?, 'Weekly Groceries', ?, ?)",
                  (def_id, user_id, now, now))
        conn.commit()
        lists = [{"id": def_id, "title": "Weekly Groceries", "created_at": now, "updated_at": now}]
        
    conn.close()
    return lists

@app.post("/api/groceries/lists")
def save_grocery_list(glist: GroceryListSave, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    list_id = glist.id or str(uuid.uuid4())
    now = datetime.now().isoformat()
    c.execute("SELECT id FROM grocery_lists WHERE id=? AND user_id=?", (list_id, user_id))
    if c.fetchone():
        c.execute("UPDATE grocery_lists SET title=?, updated_at=? WHERE id=? AND user_id=?", (glist.title, now, list_id, user_id))
    else:
        c.execute("INSERT INTO grocery_lists (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (list_id, user_id, glist.title, now, now))
    conn.commit()
    conn.close()
    return {"status": "success", "id": list_id}

@app.delete("/api/groceries/lists/{list_id}")
def delete_grocery_list(list_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM grocery_lists WHERE id=? AND user_id=?", (list_id, user_id))
    c.execute("DELETE FROM grocery_list_items WHERE list_id=? AND user_id=?", (list_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/groceries/lists/{list_id}/items")
def get_grocery_list_items(list_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, list_id, item_name, store_name, price_notes, category, is_checked, image_url FROM grocery_list_items WHERE list_id=? AND user_id=? ORDER BY is_checked ASC, category ASC, item_name ASC", (list_id, user_id))
    rows = [dict(r) for r in c.fetchall()]
    
    c.execute("SELECT id, name, ad_url, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
    stores_raw = c.fetchall()
    conn.close()
    
    all_stores = []
    for s in stores_raw:
        deals = []
        if s["cached_deals"]:
            try: deals = json.loads(s["cached_deals"])
            except Exception: deals = []
        all_stores.append({"name": s["name"], "deals": deals})
        
    for item in rows:
        comp = find_cross_store_comparison(
            item.get("item_name", ""),
            item.get("store_name", "Any"),
            item.get("price_notes", ""),
            item.get("category", "General"),
            all_stores
        )
        item["comparison"] = comp
        
    return rows

@app.post("/api/groceries/lists/{list_id}/items")
def add_grocery_item(list_id: str, item: GroceryItemSave, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    item_id = item.id or str(uuid.uuid4())
    c.execute("INSERT INTO grocery_list_items (id, list_id, user_id, item_name, store_name, price_notes, category, is_checked, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (item_id, list_id, user_id, item.item_name, item.store_name or "Any", item.price_notes or "", item.category or "General", item.is_checked or 0, item.image_url or ""))
    now = datetime.now().isoformat()
    c.execute("UPDATE grocery_lists SET updated_at=? WHERE id=? AND user_id=?", (now, list_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "id": item_id}

@app.post("/api/groceries/lists/{list_id}/batch_items")
def add_batch_grocery_items(list_id: str, req: GroceryBatchItemsSave, user_id: str = Depends(verify_auth)):
    if not req.items:
        return {"status": "success", "count": 0}
    conn = get_db_conn()
    c = conn.cursor()
    added_count = 0
    now = datetime.now().isoformat()
    for item in req.items:
        item_id = str(uuid.uuid4())
        name = item.get("item_name") or item.get("item") or "Item"
        store = item.get("store_name") or item.get("store") or "Any"
        price = item.get("price_notes") or item.get("price") or ""
        cat = item.get("category") or "General"
        img = item.get("image_url") or ""
        c.execute("INSERT INTO grocery_list_items (id, list_id, user_id, item_name, store_name, price_notes, category, is_checked, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                  (item_id, list_id, user_id, name, store, price, cat, img))
        added_count += 1
    c.execute("UPDATE grocery_lists SET updated_at=? WHERE id=? AND user_id=?", (now, list_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "count": added_count}

@app.put("/api/groceries/items/{item_id}")
def update_grocery_item(item_id: str, payload: dict, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    fields = []
    values = []
    for k in ["item_name", "store_name", "price_notes", "category", "is_checked", "image_url"]:
        if k in payload:
            fields.append(f"{k}=?")
            values.append(payload[k])
    if fields:
        values.extend([item_id, user_id])
        c.execute(f"UPDATE grocery_list_items SET {', '.join(fields)} WHERE id=? AND user_id=?", values)
        conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/groceries/items/{item_id}")
def delete_grocery_item(item_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM grocery_list_items WHERE id=? AND user_id=?", (item_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/groceries/lists/{list_id}/clear_checked")
def clear_checked_grocery_items(list_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM grocery_list_items WHERE list_id=? AND user_id=? AND is_checked=1", (list_id, user_id))
    now = datetime.now().isoformat()
    c.execute("UPDATE grocery_lists SET updated_at=? WHERE id=? AND user_id=?", (now, list_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/groceries/ai_generate_list")
def ai_generate_list(req: AIGroceryListRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    
    c.execute("SELECT name, ad_url, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
    stores = []
    for r in c.fetchall():
        deals = []
        if r["cached_deals"]:
            try: deals = json.loads(r["cached_deals"])
            except Exception: deals = []
        stores.append({"name": r["name"], "deals": deals})
        
    items = ai_generate_grocery_list_items(req.prompt, stores, settings)
    
    list_id = req.list_id
    now = datetime.now().isoformat()
    if not list_id:
        list_id = str(uuid.uuid4())
        c.execute("INSERT INTO grocery_lists (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                  (list_id, user_id, req.list_title or "AI Generated List", now, now))
                  
    for item in items:
        item_id = str(uuid.uuid4())
        name = item.get("item_name") or item.get("item") or "Item"
        store = item.get("store_name") or item.get("store") or "Any"
        price = item.get("price_notes") or item.get("price") or ""
        cat = item.get("category") or "General"
        img = item.get("image_url") or ""
        c.execute("INSERT INTO grocery_list_items (id, list_id, user_id, item_name, store_name, price_notes, category, is_checked, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                  (item_id, list_id, user_id, name, store, price, cat, img))
                  
    c.execute("UPDATE grocery_lists SET updated_at=? WHERE id=? AND user_id=?", (now, list_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "list_id": list_id, "items": items}


