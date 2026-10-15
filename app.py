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
from datetime import datetime, timedelta, timezone
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
import calendar

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, "app.db")
CLIENT_SECRETS_FILE = os.path.join(DATA_DIR, "client_secret.json")
LOG_FILE = os.path.join(DATA_DIR, "app.log")
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/userinfo.email', 'openid']

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

# --- Default Household & Parsing Rules Configuration ---
DEFAULT_FAMILY_PROFILE = {
    "family_name": "Our Family",
    "total_members": 5,
    "members": [
        {
            "id": "m1",
            "name": "Dominic",
            "role": "self",
            "relation": "Father",
            "age": 38,
            "gender": "male",
            "appetite": "large",
            "grade": "Class of 2006",
            "school": "",
            "sports": "",
            "notes": "Dad / Self, Class of 2006 graduate"
        },
        {
            "id": "m2",
            "name": "Wife",
            "role": "spouse",
            "relation": "Mother",
            "age": 37,
            "gender": "female",
            "appetite": "normal",
            "grade": "",
            "school": "",
            "sports": "",
            "notes": "Mom / Spouse"
        },
        {
            "id": "m3",
            "name": "Gia",
            "role": "child",
            "relation": "Teen Daughter",
            "age": 15,
            "gender": "female",
            "appetite": "normal",
            "grade": "9th Grade",
            "school": "Liberty Christian School",
            "sports": "Softball",
            "notes": "9th grade (High School), plays softball"
        },
        {
            "id": "m4",
            "name": "Ellie",
            "role": "child",
            "relation": "Daughter",
            "age": 11,
            "gender": "female",
            "appetite": "normal",
            "grade": "6th Grade",
            "school": "Liberty Christian School",
            "sports": "XC, Soccer, Track",
            "notes": "6th grade (Middle School), plays cross country (XC), soccer, track"
        },
        {
            "id": "m5",
            "name": "Leo",
            "role": "child",
            "relation": "Son",
            "age": 8,
            "gender": "male",
            "appetite": "normal",
            "grade": "2nd Grade",
            "school": "Liberty Christian School",
            "sports": "",
            "notes": "2nd grade boy"
        }
    ],
    "notes": "5 family members (Dominic, Wife, Gia, Ellie, Leo)"
}

DEFAULT_PARSING_RULES = {
    "bill_reminders": True,
    "bill_amounts_in_calendar": False,
    "school_grade_filter": True,
    "grades_allowed": ["2nd Grade", "6th Grade", "9th Grade", "Middle School", "High School"],
    "assume_teacher_is_for_kids": True,
    "filter_unregistered_camps": True,
    "abbreviate_cross_country_xc": True,
    "match_children": True,
    "label_non_child_for_self": True,
    "self_name": "Dominic",
    "expand_liberty_location": True,
    "last_day_of_month_dates": True,
    "filter_promotions_and_travel": True,
    "filter_package_deliveries": True,
    "filter_corporate_webinars": True,
    "invite_reminders": True,
    "custom_instructions": ""
}

def build_parsing_prompt_instructions(settings: dict) -> str:
    rules = settings.get("parsing_rules") or DEFAULT_PARSING_RULES
    family = settings.get("family_profile") or DEFAULT_FAMILY_PROFILE
    members = family.get("members", [])
    
    kids = [m for m in members if m.get("role") == "child" or m.get("name") in ["Leo", "Ellie", "Gia"]]
    self_member = next((m for m in members if m.get("role") == "self" or m.get("name") == "Dominic"), None)
    self_name = self_member.get("name", "Dominic") if self_member else "Dominic"
    
    sections = []

    # 1. Family Members & Event Recipient Matching
    if rules.get("match_children", True) and kids:
        kids_desc = []
        for k in kids:
            k_name = k.get("name", "")
            k_grade = k.get("grade", "")
            k_gender = k.get("gender", "")
            k_sports = k.get("sports", "")
            k_school = k.get("school", "")
            line = f"  * {k_name}: {k_grade} ({k_gender})"
            if k_sports:
                line += f" | Sports/Activities: {k_sports}"
            if k_school:
                line += f" | School: {k_school}"
            kids_desc.append(line)
        
        kids_text = "\n".join(kids_desc)
        sections.append(f"""1. FAMILY MEMBERS & EVENT RECIPIENT MATCHING:
- Family Members:
{kids_text}
  * {self_name} (Self / Parent, Class of 2006 graduate)
- MATCHING & TITLING RULES:
  * Try to match each event with the relevant child based on grade, sport, or teacher context.
  * ALWAYS append the person's name at the very end of the event title with a hyphen (e.g. "Track Meet - Ellie", "Softball Practice - Gia", "Spelling Bee - Leo").
  * NEVER include the school grade in the event title (e.g., use "Track Meet - Ellie", NOT "Track Meet - 6th Grade").
  * If an event is NOT for one of the children (e.g. personal, household, or general appointments), label it for {self_name} at the end of the title (e.g. "Dentist Appointment - {self_name}").
  * Write a robust and detailed event description specifying who the event is for and relevant context from the email.""")

    # 2. School Events & Grade Filter
    if rules.get("school_grade_filter", True):
        sections.append("""2. SCHOOL EVENT & GRADE FILTERING:
- The children are in 2nd, 6th, and 9th grades (6th grade is considered Middle School; 9th grade is High School).
- ONLY extract school events for 2nd, 6th, and 9th grades (and middle/high school activities relevant to them).
- STRICTLY IGNORE school events for all other grades (Kindergarten, 1st, 3rd, 4th, 5th, 7th, 8th, 10th, 11th, 12th).
- If an email is from a teacher, coach, or school staff, assume it is for one of the children and scan it thoroughly for calendar events to add.""")

    # 3. Block Unregistered School Camps & Registration Solicitations
    if rules.get("filter_unregistered_camps", True):
        sections.append("""3. REJECT UNREGISTERED CAMPS & REGISTRATION SOLICITATIONS:
- Do NOT add school camps, clinics, or programs that show an open sign-up or registration call to action.
- Examples of promotional solicitations to IGNORE / REJECT:
  * "Beginning Sept. 14 Cost: $300 Register here"
  * "Please CLICK HERE to register"
  * "(Registration closes Sept 16th)"
  * "After-School Enrichment Opportunities"
  * Flyers inviting parents to register or pay for upcoming optional camps/programs.
- That language indicates the user has NOT signed up yet. DO NOT add it to the calendar!
- ONLY add events that the family or child has ACTUALLY signed up for, confirmed registrations, or official school schedule events (e.g. actual team games, practices, meets, school calendar days, parent-teacher conferences).""")

    # 4. Cross Country Abbreviation
    if rules.get("abbreviate_cross_country_xc", True):
        sections.append("""4. SPORT ABBREVIATIONS:
- Always abbreviate Cross Country as "XC" in all event titles and descriptions (e.g. "XC Meet - Ellie", "XC Practice - Ellie").""")

    # 5. Location Mapping (Liberty)
    if rules.get("expand_liberty_location", True):
        sections.append("""5. LOCATION MAPPING:
- If an email or event mentions location "liberty" or "Liberty", set the location to "Liberty Christian School, Argyle, Texas".""")

    # 6. Relative Dates (end of MM/YYYY)
    if rules.get("last_day_of_month_dates", True):
        sections.append("""6. RELATIVE DATES:
- If a date is stated as "end of MM/YYYY" (e.g. "end of 08/2026"), set the date to All Day on the last day of that month (e.g. "2026-08-31T09:00:00").""")

    # 7. Promotions, Deliveries & Marketing Filter
    filter_items = []
    if rules.get("filter_promotions_and_travel", True):
        filter_items.append("  * Ignore marketing promotions, rewards deadlines (e.g. 'deadline to book Atmos Rewards Global Getaways by TOMORROW', 'Daily Drop Pro sale ending on Sept 8'). Ignore promotional offers and travel news.")
    if rules.get("filter_package_deliveries", True):
        filter_items.append("  * Do NOT add events for items being delivered, shipped, or package tracking dates.")
    if rules.get("filter_corporate_webinars", True):
        filter_items.append("  * Do NOT add promotional corporate events, career days, or webinars (e.g. 'Cloudflare AI week', 'Fidelity Career day').")
    if filter_items:
        sections.append("7. PROMOTIONAL, DELIVERY & MARKETING FILTERING:\n" + "\n".join(filter_items))

    # 8. Bill Reminders & Dollar Amount Privacy
    if rules.get("bill_reminders", True):
        if not rules.get("bill_amounts_in_calendar", False):
            sections.append("""8. BILL REMINDERS & PAYMENT DEADLINES:
- Bill due dates and payment deadlines MAY be extracted as calendar reminder events.
- IMPORTANT PRIVACY RULE: DO NOT include bill dollar amounts (e.g. $145.20) in the event title or description! Keep the event clean (e.g. "Electric Bill Due - Dominic").""")
        else:
            sections.append("""8. BILL REMINDERS & PAYMENT DEADLINES:
- Bill due dates and payment deadlines may be extracted as calendar reminder events with amounts included.""")
    else:
        sections.append("""8. BILL REMINDERS:
- Do NOT extract bill due dates or payment notices.""")

    # 9. Calendar Invites
    if rules.get("invite_reminders", True):
        sections.append("""9. CALENDAR & MEETING INVITES:
- Scan for incoming meeting invitations, appointments, and RSVP deadlines.""")

    # 10. Additional Custom Prompt
    custom = (rules.get("custom_instructions") or settings.get("custom_prompt") or "").strip()
    if custom:
        sections.append(f"10. ADDITIONAL USER CUSTOM INSTRUCTIONS:\n{custom}")

    return "\n\n".join(sections)

def post_process_extracted_event(e: dict, settings: dict, subject: str, body: str) -> Optional[dict]:
    rules = settings.get("parsing_rules") or DEFAULT_PARSING_RULES
    title = e.get("title", "") or ""
    desc = e.get("description", "") or ""
    loc = e.get("location", "") or ""
    date_val = e.get("date", "") or ""
    full_context = f"{title} {desc} {subject} {body}".lower()

    # 1. Unregistered camps / sign-up solicitations filter
    if rules.get("filter_unregistered_camps", True):
        camp_patterns = [
            r'register\s+here',
            r'click\s+here\s+to\s+register',
            r'registration\s+closes',
            r'open\s+for\s+registration',
            r'cost:\s*\$\d+.*register',
            r'after-school\s+enrichment\s+opportunities',
            r'registration\s+deadline',
            r'please\s+register'
        ]
        is_solicitation = any(re.search(pat, full_context) for pat in camp_patterns)
        has_confirmed = any(kw in full_context for kw in ["you are registered", "registration confirmed", "ticket confirmed", "receipt", "order confirmation", "official game schedule", "practice schedule"])
        if is_solicitation and not has_confirmed:
            if any(kw in full_context for kw in ["camp", "clinic", "enrichment", "workshop", "tryout", "sign up", "signup"]):
                logger.info(f"Filtered unregistered camp solicitation: '{title}'")
                return None

    # 2. Marketing / Travel / Flash Sales filter
    if rules.get("filter_promotions_and_travel", True):
        marketing_patterns = [
            r'atmos\s+rewards',
            r'daily\s+drop\s+pro',
            r'global\s+getaways',
            r'flash\s+sale',
            r'book\s+by\s+tomorrow',
            r'travel\s+news',
            r'limited\s+time\s+offer',
            r'discount\s+code',
            r'sale\s+ends'
        ]
        if any(re.search(pat, full_context) for pat in marketing_patterns):
            logger.info(f"Filtered marketing promotion: '{title}'")
            return None

    # 3. Delivery / Shipment tracking filter
    if rules.get("filter_package_deliveries", True):
        delivery_patterns = [
            r'scheduled\s+for\s+delivery',
            r'out\s+for\s+delivery',
            r'tracking\s+number',
            r'package\s+will\s+arrive',
            r'shipped\s+via',
            r'estimated\s+delivery'
        ]
        if any(re.search(pat, full_context) for pat in delivery_patterns):
            logger.info(f"Filtered package delivery event: '{title}'")
            return None

    # 4. Corporate promotional webinars / career days filter
    if rules.get("filter_corporate_webinars", True):
        corp_patterns = [
            r'cloudflare(?:\'s)?\s+ai\s+week',
            r'fidelity(?:\'s)?\s+career\s+day',
            r'webinar:\s*',
            r'virtual\s+summit',
            r'career\s+fair\s+promo'
        ]
        if any(re.search(pat, full_context) for pat in corp_patterns):
            logger.info(f"Filtered corporate webinar/career day: '{title}'")
            return None

    # 5. Cross Country -> XC abbreviation
    if rules.get("abbreviate_cross_country_xc", True):
        title = re.sub(r'\b[Cc]ross\s+[Cc]ountry\b', 'XC', title)
        desc = re.sub(r'\b[Cc]ross\s+[Cc]ountry\b', 'XC', desc)

    # 6. Location mapping: "liberty" -> "Liberty Christian School, Argyle, Texas"
    if rules.get("expand_liberty_location", True):
        if loc and "liberty" in loc.lower() and "argyle" not in loc.lower():
            loc = "Liberty Christian School, Argyle, Texas"
        elif not loc and ("liberty" in title.lower() or "liberty" in desc.lower() or "liberty" in subject.lower()):
            loc = "Liberty Christian School, Argyle, Texas"

    # 7. Bill dollar amounts stripping
    if not rules.get("bill_amounts_in_calendar", False):
        title = re.sub(r'\s*\$\d+(?:,\d{3})*(?:\.\d{2})?\b', '', title).strip()
        desc = re.sub(r'\bamount due:?\s*\$\d+(?:,\d{3})*(?:\.\d{2})?\b', '', desc, flags=re.IGNORECASE).strip()

    # 8. Relative dates: "end of MM/YYYY" -> Last day of month
    if rules.get("last_day_of_month_dates", True):
        m_rel = re.search(r'\bend of\s+(0?[1-9]|1[0-2])/(\d{4})\b', full_context)
        if m_rel:
            m_num = int(m_rel.group(1))
            y_num = int(m_rel.group(2))
            last_day = calendar.monthrange(y_num, m_num)[1]
            date_val = f"{y_num:04d}-{m_num:02d}-{last_day:02d}T09:00:00"

    # 9. Child / Person Suffix: "Event Title - Name"
    if rules.get("match_children", True):
        self_name = rules.get("self_name", "Dominic")
        family = settings.get("family_profile") or DEFAULT_FAMILY_PROFILE
        members = family.get("members", [])
        child_names = [m.get("name") for m in members if m.get("role") == "child" or m.get("name") in ["Leo", "Ellie", "Gia"]]
        if not child_names:
            child_names = ["Leo", "Ellie", "Gia"]

        # First clean any trailing grade label that AI might have generated
        title = re.sub(r'\s*-\s*\d+(?:st|nd|rd|th)?\s+grade\b.*$', '', title, flags=re.IGNORECASE).strip()
        title = re.sub(r'\s*\(?\d+(?:st|nd|rd|th)?\s+grade\)?$', '', title, flags=re.IGNORECASE).strip()

        # Check if title already ends with any valid name suffix
        all_possible_names = child_names + [self_name, "Wife"]
        has_name_suffix = any(title.strip().endswith(f"- {n}") or title.strip().endswith(f"({n})") for n in all_possible_names)

        if not has_name_suffix:
            matched_person = None
            if "leo" in full_context or "2nd grade" in full_context or "second grade" in full_context:
                matched_person = "Leo"
            elif "ellie" in full_context or "6th grade" in full_context or "sixth grade" in full_context or "middle school" in full_context or " xc " in f" {full_context} " or "soccer" in full_context or "track" in full_context:
                matched_person = "Ellie"
            elif "gia" in full_context or "9th grade" in full_context or "ninth grade" in full_context or "softball" in full_context or "high school" in full_context:
                matched_person = "Gia"
            elif rules.get("label_non_child_for_self", True):
                matched_person = self_name

            if matched_person:
                title = f"{title} - {matched_person}"

    # 10. Robust description enhancement
    if "ellie" in title.lower() and "ellie" not in desc.lower():
        desc = f"Event for Ellie (6th Grade XC, Soccer & Track). {desc}".strip()
    elif "gia" in title.lower() and "gia" not in desc.lower():
        desc = f"Event for Gia (9th Grade Softball). {desc}".strip()
    elif "leo" in title.lower() and "leo" not in desc.lower():
        desc = f"Event for Leo (2nd Grade). {desc}".strip()
    elif "dominic" in title.lower() and "dominic" not in desc.lower():
        desc = f"Personal event for Dominic. {desc}".strip()

    e["title"] = title
    e["description"] = desc
    e["location"] = loc
    e["date"] = date_val
    return e

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
                    cached_deals TEXT,
                    valid_from TEXT,
                    valid_to TEXT
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
        
    try:
        c.execute("ALTER TABLE grocery_stores ADD COLUMN valid_from TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        c.execute("ALTER TABLE grocery_stores ADD COLUMN valid_to TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    c.execute('''CREATE TABLE IF NOT EXISTS grocery_price_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    item_name TEXT,
                    normalized_key TEXT,
                    store_name TEXT,
                    price_str TEXT,
                    unit_price REAL,
                    unit TEXT,
                    beef_grade TEXT,
                    category TEXT,
                    recorded_at TEXT
                 )''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_gph_user_key ON grocery_price_history(user_id, normalized_key, recorded_at);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_gph_user_store ON grocery_price_history(user_id, store_name, recorded_at);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_user_status_date ON events(user_id, status, date);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_email_acc_user ON email_accounts(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pe_user_date ON processed_emails_v2(user_id, date DESC);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_gs_user ON grocery_stores(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_gs_user_valid_to ON grocery_stores(user_id, valid_to);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_gl_user ON grocery_lists(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_gli_list_user ON grocery_list_items(list_id, user_id);")
    c.execute('''CREATE TABLE IF NOT EXISTS meal_plans (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    plan_type TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    meals_data TEXT,
                    dietary_pref TEXT,
                    servings INTEGER DEFAULT 4,
                    notes TEXT
                 )''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_mp_user_date ON meal_plans(user_id, start_date DESC);")
    c.execute('''CREATE TABLE IF NOT EXISTS site_suggestions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    page TEXT,
                    title TEXT,
                    description TEXT,
                    author TEXT DEFAULT 'Wife',
                    priority TEXT DEFAULT 'improvement',
                    status TEXT DEFAULT 'open',
                    created_at TEXT,
                    completed_at TEXT
                 )''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_sug_user_status ON site_suggestions(user_id, status, created_at DESC);")
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Ensure at least one admin exists if users exist
    try:
        c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
        if not c.fetchone():
            c.execute("SELECT id FROM users ORDER BY rowid ASC LIMIT 1")
            first_u = c.fetchone()
            if first_u:
                c.execute("UPDATE users SET role='admin' WHERE id=?", (first_u[0],))
                logger.info(f"Assigned administrator role to initial user {first_u[0]}.")
    except Exception as e:
        logger.debug(f"Role initialization note: {e}")
        
    # Ensure users have family profile and smart parsing rules initialized
    try:
        c.execute("SELECT id, settings FROM users")
        for u in c.fetchall():
            uid = u[0]
            s = json.loads(u[1]) if u[1] else {}
            changed = False
            fp = s.get("family_profile")
            if not fp or (fp.get("members") and any(m.get("name") in ["Adult 1", "Child 1"] for m in fp.get("members", []))):
                s["family_profile"] = DEFAULT_FAMILY_PROFILE
                changed = True
            if "parsing_rules" not in s:
                s["parsing_rules"] = DEFAULT_PARSING_RULES
                changed = True
            if changed:
                c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(s), uid))
                logger.info(f"Initialized family profile and smart parsing rules for user {uid}.")
    except Exception as e:
        logger.debug(f"Parsing rules migration note: {e}")

    conn.commit()
    conn.close()

init_db()

# --- Password Hashing & Security ---
def hash_password(plain_password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = secrets.token_hex(16)
    iters = 100000
    h = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), iters).hex()
    return f"pbkdf2:sha256:{iters}${salt}${h}"

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify password supporting both PBKDF2-HMAC-SHA256 and legacy unsalted SHA-256."""
    if not password_hash or not plain_password:
        return False
    if password_hash.startswith("pbkdf2:sha256:"):
        try:
            prefix, salt, stored_hash = password_hash.split("$", 2)
            iters = int(prefix.split(":")[-1])
            computed = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), iters).hex()
            return secrets.compare_digest(computed, stored_hash)
        except Exception:
            return False
    # Legacy unsalted SHA-256 fallback
    legacy = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return secrets.compare_digest(legacy, password_hash)

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

def verify_admin(current_user: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE id=?", (current_user,))
    row = c.fetchone()
    conn.close()
    if not row or (row["role"] or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Administrator privileges required.")
    return current_user

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "app": "AI Helper"
    }

@app.get("/api/auth/status")
def auth_status(request: Request):
    token = request.cookies.get("session_token")
    user_id = get_user_id_from_token(token)
    logged_in = user_id is not None
    username = None
    role = "user"
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    if logged_in:
        c.execute("SELECT username, COALESCE(role, 'user') as role FROM users WHERE id=?", (user_id,))
        u = c.fetchone()
        if u:
            username = u["username"]
            role = (u["role"] or "user").lower()
    conn.close()
    return {
        "setup_required": count == 0,
        "logged_in": logged_in,
        "user_id": user_id,
        "username": username,
        "role": role,
        "is_admin": role == "admin"
    }

@app.post("/api/auth/register")
def auth_register(req: AuthRequest):
    if len(req.password) < 4:
        return {"error": "Password must be at least 4 characters."}
    pwd_hash = hash_password(req.password)
    user_id = str(uuid.uuid4())
    default_settings = json.dumps({"ai_provider": "gemini", "ai_model": "gemini-1.5-flash", "public_url": ""})
    conn = get_db_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        assigned_role = "admin" if count == 0 else "user"
        c.execute("INSERT INTO users (id, username, password_hash, settings, role) VALUES (?, ?, ?, ?, ?)", (user_id, req.username, pwd_hash, default_settings, assigned_role))
        conn.commit()
        logger.info(f"New user registered: {req.username} (role: {assigned_role})")
    except sqlite3.IntegrityError:
        return {"error": "Username already exists."}
    finally:
        conn.close()
    return {"status": "success"}

@app.post("/api/auth/login")
def auth_login(req: AuthRequest, response: Response):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE username=?", (req.username,))
    user = c.fetchone()
    if not user or not verify_password(req.password, user["password_hash"]):
        conn.close()
        logger.warning(f"Failed login attempt for username: {req.username}")
        return {"error": "Invalid username or password"}
        
    user_id = user["id"]
    # Automatically upgrade legacy unsalted SHA-256 password hashes to PBKDF2
    if not user["password_hash"].startswith("pbkdf2:"):
        try:
            upgraded_hash = hash_password(req.password)
            c.execute("UPDATE users SET password_hash=? WHERE id=?", (upgraded_hash, user_id))
            conn.commit()
            logger.info(f"Upgraded password hash for user {req.username} to PBKDF2.")
        except Exception as up_err:
            logger.debug(f"Could not auto-upgrade password hash: {up_err}")

    token = secrets.token_hex(32)
    # 90-day session expiration
    expires_ts = (datetime.now() + timedelta(days=90)).timestamp()
    
    try:
        c.execute("INSERT OR REPLACE INTO sessions (token, user_id, expires) VALUES (?, ?, ?)", (token, user_id, expires_ts))
        # Purge any expired sessions
        c.execute("DELETE FROM sessions WHERE expires < ?", (datetime.now().timestamp(),))
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
    role: Optional[str] = "user"

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

@app.get("/api/users", dependencies=[Depends(verify_admin)])
def get_users():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, COALESCE(role, 'user') as role FROM users")
    users = [{"id": r[0], "username": r[1], "role": r[2]} for r in c.fetchall()]
    conn.close()
    return users

@app.post("/api/users", dependencies=[Depends(verify_admin)])
def create_user(req: UserCreate):
    if len(req.password) < 4:
        return {"error": "Password must be at least 4 characters."}
    pwd_hash = hash_password(req.password)
    user_id = str(uuid.uuid4())
    default_settings = json.dumps({"ai_provider": "gemini", "ai_model": "gemini-1.5-flash", "public_url": ""})
    role = "admin" if (req.role or "").lower() == "admin" else "user"
    conn = get_db_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (id, username, password_hash, settings, role) VALUES (?, ?, ?, ?, ?)", (user_id, req.username, pwd_hash, default_settings, role))
        conn.commit()
    except sqlite3.IntegrityError:
        return {"error": "Username already exists."}
    finally:
        conn.close()
    return {"status": "success"}

@app.put("/api/users/{target_user_id}")
def update_user(target_user_id: str, req: UserUpdate, current_user: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE id=?", (current_user,))
    caller = c.fetchone()
    is_admin = caller and (caller["role"] or "").lower() == "admin"
    
    if not is_admin and current_user != target_user_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Permission denied. You can only update your own account.")

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
        pwd_hash = hash_password(req.password)
        c.execute("UPDATE users SET password_hash=? WHERE id=?", (pwd_hash, target_user_id))
    if req.role and is_admin:
        new_role = "admin" if req.role.lower() == "admin" else "user"
        c.execute("UPDATE users SET role=? WHERE id=?", (new_role, target_user_id))

    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/users/{target_user_id}", dependencies=[Depends(verify_admin)])
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
    c.execute("DELETE FROM grocery_stores WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM grocery_lists WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM grocery_list_items WHERE user_id=?", (target_user_id,))
    c.execute("DELETE FROM meal_plans WHERE user_id=?", (target_user_id,))
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
    parsing_rules: Optional[dict] = None
    family_profile: Optional[dict] = None

class ParsingRulesSaveRequest(BaseModel):
    rules: dict
    family_profile: Optional[dict] = None

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
    
    parsing_rules = settings.get("parsing_rules", DEFAULT_PARSING_RULES)
    family_profile = settings.get("family_profile", DEFAULT_FAMILY_PROFILE)
    compiled_prompt = build_parsing_prompt_instructions(settings)

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
        "google_connected": os.path.exists(token_file),
        "parsing_rules": parsing_rules,
        "family_profile": family_profile,
        "compiled_prompt": compiled_prompt
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

@app.get("/api/settings/parsing_rules")
def get_parsing_rules_api(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    rules = settings.get("parsing_rules", DEFAULT_PARSING_RULES)
    family_profile = settings.get("family_profile", DEFAULT_FAMILY_PROFILE)
    compiled_prompt = build_parsing_prompt_instructions(settings)
    return {
        "status": "success",
        "rules": rules,
        "family_profile": family_profile,
        "compiled_prompt": compiled_prompt
    }

@app.post("/api/settings/parsing_rules")
def save_parsing_rules_api(req: ParsingRulesSaveRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    settings["parsing_rules"] = req.rules
    if req.family_profile:
        settings["family_profile"] = req.family_profile
        if "members" in req.family_profile:
            if "meal_preferences" not in settings:
                settings["meal_preferences"] = {}
            settings["meal_preferences"]["default_servings"] = len(req.family_profile["members"])

    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    compiled_prompt = build_parsing_prompt_instructions(settings)
    return {
        "status": "success",
        "rules": req.rules,
        "family_profile": settings.get("family_profile", DEFAULT_FAMILY_PROFILE),
        "compiled_prompt": compiled_prompt
    }

class AccountTest(BaseModel):
    email_user: str
    email_pass: str
    email_host: str = "imap.gmail.com"

@app.post("/api/accounts/test", dependencies=[Depends(verify_auth)])
def test_account_connection(req: AccountTest):
    clean_user = req.email_user.strip()
    clean_pass = req.email_pass.replace(" ", "")
    clean_host = req.email_host.strip()
    try:
        with MailBox(clean_host).login(clean_user, clean_pass) as mailbox:
            return {
                "status": "success",
                "message": f"Successfully connected to {clean_user} on {clean_host}!"
            }
    except Exception as e:
        err_msg = str(e)
        logger.warning(f"Test email connection failed for {clean_user}@{clean_host}: {err_msg}")
        hint = ""
        err_upper = err_msg.upper()
        if "AUTHENTICATIONFAILED" in err_upper or "INVALID CREDENTIALS" in err_upper or "LOGIN FAILED" in err_upper:
            if "gmail" in clean_host.lower():
                hint = "Gmail requires a 16-character App Password (not your normal Google account password). Make sure 2-Step Verification is ON in your Google Account Security settings."
            elif "apple" in clean_host.lower() or "icloud" in clean_host.lower():
                hint = "iCloud requires an App-Specific Password generated at appleid.apple.com."
            elif "outlook" in clean_host.lower() or "office365" in clean_host.lower():
                hint = "Microsoft Outlook/Hotmail accounts require an App Password generated at account.microsoft.com."
            elif "yahoo" in clean_host.lower():
                hint = "Yahoo Mail requires an App Password generated under Yahoo Account Security."
        elif "TIMED OUT" in err_upper or "REFUSED" in err_upper or "NAME OR SERVICE NOT KNOWN" in err_upper:
            hint = f"Could not reach {clean_host}. Please double-check the IMAP server host name."

        return {
            "status": "error",
            "message": f"Connection failed: {err_msg}",
            "hint": hint
        }

@app.post("/api/accounts")
def save_account(acc: AccountSave, user_id: str = Depends(verify_auth)):
    clean_user = acc.email_user.strip()
    clean_pass = acc.email_pass.replace(" ", "")
    clean_host = acc.email_host.strip()
    conn = get_db_conn()
    c = conn.cursor()
    acc_id = acc.id or str(uuid.uuid4())
    c.execute("SELECT id FROM email_accounts WHERE id=? AND user_id=?", (acc_id, user_id))
    if c.fetchone():
        c.execute("UPDATE email_accounts SET email_user=?, email_pass=?, email_host=? WHERE id=?", (clean_user, clean_pass, clean_host, acc_id))
    else:
        c.execute("INSERT INTO email_accounts (id, user_id, email_user, email_pass, email_host) VALUES (?, ?, ?, ?, ?)", (acc_id, user_id, clean_user, clean_pass, clean_host))
    conn.commit()
    conn.close()
    return {"status": "success", "id": acc_id}

# --- Onboarding Setup Wizard Endpoints ---
@app.get("/api/onboarding/status", dependencies=[Depends(verify_auth)])
def get_onboarding_status(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row[0]) if row and row[0] else {}
    c.execute("SELECT id, email_user, email_host FROM email_accounts WHERE user_id=?", (user_id,))
    accounts = [dict(r) for r in c.fetchall()]
    conn.close()

    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    google_connected = os.path.exists(token_file)
    google_auth_ready = os.path.exists(CLIENT_SECRETS_FILE)
    onboarding_completed = settings.get("onboarding_completed", False)
    google_email = settings.get("google_email", "")

    return {
        "onboarding_completed": bool(onboarding_completed),
        "google_connected": google_connected,
        "google_auth_ready": google_auth_ready,
        "google_email": google_email,
        "accounts": accounts,
        "accounts_count": len(accounts),
        "has_accounts": len(accounts) > 0,
        "postal_code": settings.get("postal_code", "76262"),
        "lookback_days": int(settings.get("lookback_days", 7)),
        "fetch_interval_minutes": int(settings.get("fetch_interval_minutes", 60)),
        "family_size": 5
    }

@app.post("/api/onboarding/complete", dependencies=[Depends(verify_auth)])
def complete_onboarding(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row[0]) if row and row[0] else {}
    settings["onboarding_completed"] = True
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    logger.info(f"User {user_id} completed onboarding setup wizard.")
    return {"status": "success"}

@app.post("/api/onboarding/reset", dependencies=[Depends(verify_auth)])
def reset_onboarding(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row[0]) if row and row[0] else {}
    settings["onboarding_completed"] = False
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

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
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as response:
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
    rules_text = build_parsing_prompt_instructions(settings)
    date_str = date.isoformat() if date else "Unknown"
    prompt = f"""
    Analyze the following email to see if it contains one or more clear calendar events, appointments, meetings, flights, dinners, deadlines, assignment due dates, or scheduled tasks.
    Email Subject: {subject}
    Email Date: {date_str}

    CRITICAL PARSING RULES & FAMILY PREFERENCES:
    {rules_text}

    Return your response strictly as a JSON object with two fields:
    1. "reason": A concise, clear explanation (1-2 sentences) of why events were extracted OR why no events were added to the calendar (for example: "Extracted XC meet for Ellie on Oct 14 at 2 PM", "No specific dates, meetings, or deadlines mentioned in this newsletter", "Ignored 5th grade event per custom grade filter", "Filtered unregistered camp solicitation with open registration link").
    2. "events": A JSON array of event objects. If there are no valid calendar events or deadlines (or if they violate the PARSING RULES or USER CUSTOM INSTRUCTIONS), return an empty array [].
       Each object in the array must have the following keys:
       - "title": Title of the event (string, formatted per the child/person suffix rules e.g. "Track Meet - Ellie")
       - "date": Date and time in ISO 8601 format (e.g. "2026-10-15T14:00:00"). For assignments or deadlines without a specific time, default the time to 09:00:00 local time.
       - "description": Robust summary or notes identifying who the event is for and relevant context (string)
       - "location": Physical address, room number, or place name (leave blank "" if none found; if Liberty, use "Liberty Christian School, Argyle, Texas")
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
                    pe = post_process_extracted_event(e, settings, subject, text)
                    if pe:
                        valid_events.append(pe)
                    
        if not reason:
            if valid_events:
                reason = f"Extracted {len(valid_events)} event(s): " + ", ".join(e.get("title", "Event") for e in valid_events)
            else:
                reason = "No calendar events or deadlines detected in email."
        elif not valid_events and events_list:
            reason = "Filtered promotional, unregistered camp, or non-matching grade items per parsing rules."
                
        return {"events": valid_events, "reason": reason}
    except Exception as e:
        logger.error(f"AI extraction error ({provider} - {model_name}): {e}")
        raise ValueError(f"AI API Error: {str(e)}") 

# --- Google Calendar Event Pusher & Duplicate Prevention ---
def parse_flexible_iso_datetime(date_str: str) -> datetime:
    """Robustly parse ISO dates, date-only strings, and common datetime formats."""
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Empty or invalid date string")
    clean = date_str.strip().replace("Z", "+00:00")
    if re.match(r'^\d{4}-\d{2}-\d{2}$', clean):
        clean += "T09:00:00"
    elif " " in clean and "T" not in clean:
        clean = clean.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(clean)
    except Exception:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(clean, fmt)
                break
            except Exception:
                pass
        else:
            raise ValueError(f"Cannot parse datetime from '{date_str}'")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return dt

def normalize_event_title(title: str) -> str:
    """Normalize event title by removing routine prefixes, emojis, and punctuation."""
    t = (title or "").lower()
    t = re.sub(r'^(?:fwd|re|reminder|invitation|notice|alert|dinner|meal|lunch|event|meeting)\s*[:\-]\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t) # remove emojis
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return ' '.join(t.split())

def are_events_duplicate(title1: str, date1_str: str, title2: str, date2_str: str) -> bool:
    """
    Determines if two events are duplicates based on title similarity and calendar day overlap (+/- 4 hours).
    """
    if not title1 or not title2 or not date1_str or not date2_str:
        return False
        
    try:
        d1 = parse_flexible_iso_datetime(date1_str)
        d2 = parse_flexible_iso_datetime(date2_str)
    except Exception:
        if date1_str[:10] != date2_str[:10]:
            return False
        d1 = None
        d2 = None
        
    if d1 and d2:
        same_day = (d1.date() == d2.date())
        time_diff = abs((d1 - d2).total_seconds())
        if not same_day and time_diff > 14400: # 4 hours
            return False
            
    n1 = normalize_event_title(title1)
    n2 = normalize_event_title(title2)
    
    if not n1 or not n2:
        return False
        
    if n1 == n2:
        return True
    if len(n1) >= 6 and (n1 in n2 or n2 in n1):
        return True
        
    toks1 = set(n1.split())
    toks2 = set(n2.split())
    stop = {'the', 'and', 'at', 'in', 'on', 'for', 'of', 'with', 'to', 'a', 'an'}
    t1 = toks1 - stop
    t2 = toks2 - stop
    if not t1 or not t2:
        return False
        
    overlap = t1.intersection(t2)
    min_len = min(len(t1), len(t2))
    jaccard = len(overlap) / len(t1.union(t2))
    
    if len(overlap) >= 2 and (len(overlap) / min_len >= 0.7 or jaccard >= 0.5):
        return True
        
    return False

def is_food_or_meal_title(title: str) -> bool:
    """Detects whether an event summary or title corresponds to a meal, dinner, lunch, or food gathering."""
    if not title:
        return False
    t = title.lower()
    food_keywords = [
        "dinner", "supper", "lunch", "meal", "food", "cook", "restaurant",
        "pizza", "bbq", "barbecue", "eat out", "family dinner", "taco",
        "steak", "brunch", "breakfast", "buffet", "potluck"
    ]
    if any(k in t for k in food_keywords):
        return True
    if re.search(r'[\U0001F354-\U0001F37F\U0001F950-\U0001F96F]', title): # Food emojis
        return True
    return False

def find_existing_event_in_db(user_id: str, title: str, date_str: str, conn: sqlite3.Connection = None) -> dict:
    """
    Checks if an event with a similar title and time window already exists in the local database.
    """
    should_close = False
    if conn is None:
        conn = get_db_conn()
        should_close = True
    try:
        try:
            dt = parse_flexible_iso_datetime(date_str)
            day_str = dt.date().isoformat()
        except Exception:
            day_str = date_str[:10] if date_str else ""
        if not day_str:
            return None
        c = conn.cursor()
        c.execute("""
            SELECT id, user_id, account, email_id, title, date, description, location, status
            FROM events
            WHERE user_id=? AND date LIKE ? AND status IN ('pending', 'added')
        """, (user_id, f"{day_str}%"))
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            if are_events_duplicate(title, date_str, r['title'], r['date']):
                return r
        return None
    finally:
        if should_close:
            conn.close()

def find_existing_meal_or_food_on_calendar(user_id: str, date_str: str, service=None, conn: sqlite3.Connection = None) -> dict:
    """
    Checks if a meal or dinner event is already scheduled for the given date,
    checking both the local database 'events' table and Google Calendar (if service provided).
    Returns dict with event details if found, or None.
    """
    should_close = False
    if conn is None:
        conn = get_db_conn()
        should_close = True
    try:
        try:
            dt = parse_flexible_iso_datetime(date_str)
            day_str = dt.date().isoformat()
        except Exception:
            day_str = date_str[:10] if date_str else ""
        if not day_str:
            return None
            
        c = conn.cursor()
        c.execute("""
            SELECT id, user_id, account, email_id, title, date, description, location, status
            FROM events
            WHERE user_id=? AND date LIKE ? AND status IN ('pending', 'added')
        """, (user_id, f"{day_str}%"))
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            if is_food_or_meal_title(r['title']) or r.get('account') == 'Smart Meal Planner':
                return {"source": "local_db", "title": r['title'], "id": r['id'], "event": r}
                
        # If Google Calendar service is connected, check Google Calendar
        if service:
            try:
                time_min = f"{day_str}T00:00:00Z"
                time_max = f"{day_str}T23:59:59Z"
                gcal_events = service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    maxResults=50
                ).execute()
                for item in gcal_events.get('items', []):
                    summary = item.get('summary', '')
                    if is_food_or_meal_title(summary):
                        return {"source": "google_calendar", "title": summary, "id": item.get('id')}
            except Exception as ge:
                logger.warning(f"GCal check for existing meal on {day_str}: {ge}")
                
        return None
    finally:
        if should_close:
            conn.close()

def push_event_to_gcal(service, title: str, description: str, date_str: str, location: str = "", is_meal: bool = False):
    """
    Pushes an event to Google Calendar, with comprehensive duplicate prevention:
    - Queries a full day window (+/- 14 hours) on the user's primary calendar
    - Checks are_events_duplicate for resilient title & token similarity
    - If is_meal is True, checks if any food/dinner event already exists on that date
    """
    start_time = parse_flexible_iso_datetime(date_str)
    end_time = start_time + timedelta(hours=1)
    
    # Check Google Calendar for existing events in a full-day (+/- 14 hour) window
    try:
        time_min = (start_time - timedelta(hours=14)).isoformat()
        time_max = (end_time + timedelta(hours=14)).isoformat()
        existing = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            maxResults=50
        ).execute()
        
        for item in existing.get('items', []):
            item_summary = (item.get('summary') or "").strip()
            item_start = item.get('start', {}).get('dateTime') or item.get('start', {}).get('date') or date_str
            
            # Check duplicate by title and time
            if are_events_duplicate(title, date_str, item_summary, item_start):
                logger.info(f"Duplicate check: Event '{title}' matches existing Google Calendar event '{item_summary}'. Skipping insertion.")
                return {"status": "already_exists", "event_id": item.get("id"), "title": item_summary}
                
            # If is_meal, prevent duplicate meal events on the same calendar day
            if is_meal and is_food_or_meal_title(item_summary):
                logger.info(f"Meal duplicate check: Existing meal/dinner '{item_summary}' found on Google Calendar for {start_time.date()}. Skipping insertion.")
                return {"status": "already_exists", "event_id": item.get("id"), "title": item_summary, "meal_conflict": True}
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
    try:
        c = conn.cursor()
        c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
        row = c.fetchone()
        settings = json.loads(row['settings']) if row and row['settings'] else {}
        
        c.execute("SELECT * FROM email_accounts WHERE user_id=?", (user_id,))
        accounts = c.fetchall()
        
        if not accounts:
            return {"error": "No email accounts configured.", "new_events": 0}
            
        total_events_found = 0
        account_errors = []
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
                                        ev_title = event_data.get("title", "Untitled")
                                        ev_date = event_data.get("date", "")
                                        ev_desc = event_data.get("description", "")
                                        ev_loc = event_data.get("location", "")
                                        
                                        # Duplicate prevention in local DB
                                        existing_db = find_existing_event_in_db(user_id, ev_title, ev_date, conn=conn)
                                        if existing_db:
                                            logger.info(f"Duplicate check (DB): Event '{ev_title}' on {ev_date} already exists (ID: {existing_db['id']}). Skipping duplicate insertion.")
                                            sync_details.append(f"Already tracked '{ev_title}' (duplicate skipped)")
                                            continue

                                        event_id = str(uuid.uuid4())
                                        c.execute("INSERT INTO events (id, user_id, account, email_id, title, date, description, location, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')", 
                                                  (event_id, user_id, email_user, msg.uid,
                                                   ev_title,
                                                   ev_date,
                                                   ev_desc,
                                                   ev_loc
                                                  ))
                                        conn.commit()
                                        
                                        # Auto-sync to Google Calendar immediately if connected!
                                        token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
                                        if os.path.exists(token_file):
                                            try:
                                                creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
                                                service = build('calendar', 'v3', credentials=creds)
                                                try:
                                                    res = push_event_to_gcal(
                                                        service,
                                                        ev_title,
                                                        ev_desc,
                                                        ev_date,
                                                        ev_loc
                                                    )
                                                    c.execute("UPDATE events SET status='added' WHERE id=?", (event_id,))
                                                    if res.get("status") == "already_exists":
                                                        logger.info(f"Background: event '{ev_title}' already on Google Calendar for {user_id}")
                                                        sync_details.append(f"Already on Google Calendar '{ev_title}'")
                                                    else:
                                                        logger.info(f"Background auto-synced event '{ev_title}' for {user_id}")
                                                        sync_details.append(f"Auto-synced '{ev_title}' to Google Calendar")
                                                except Exception as date_err:
                                                    err_str = str(date_err)
                                                    if "invalid_grant" in err_str:
                                                        logger.warning(f"Google Calendar OAuth token for {user_id} is expired or revoked.")
                                                        sync_details.append("Saved to Dashboard (Google Calendar token expired — reconnect in Settings)")
                                                    else:
                                                        logger.error(f"Failed to auto-sync event {ev_title}: {date_err}")
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
                account_errors.append(f"{email_user}: {str(e)}")
                continue
                
        # Record last scan time in user settings
        try:
            settings["last_scan_time"] = datetime.now().isoformat()
            c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating last_scan_time for user {user_id}: {e}")

        result = {"status": "success", "new_events": total_events_found}
        if account_errors:
            result["warnings"] = account_errors
            if total_events_found == 0 and len(account_errors) == len(accounts):
                result["error"] = f"Failed to connect to email account(s): {'; '.join(account_errors)}"
        return result
    finally:
        conn.close()

# In-memory timestamp tracking for user job runs
USER_LAST_SCAN = {}
USER_LAST_DEAL_SCAN = {}

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
                
                # Proactive Background Deal Freshness Check & Ingestion (Every 30 minutes)
                # Automatically detects expired circulars and pulls the next circular immediately (e.g. 9/9 after 9/8)
                last_deal_scan = USER_LAST_DEAL_SCAN.get(user_id, 0)
                if (now_ts - last_deal_scan) >= 1800: # 30 minutes
                    USER_LAST_DEAL_SCAN[user_id] = now_ts
                    try:
                        deal_refresh_res = await asyncio.to_thread(refresh_user_expired_deals, user_id)
                        if deal_refresh_res.get("refreshed", 0) > 0:
                            logger.info(f"Background worker: Auto-pulled {deal_refresh_res['refreshed']} new weekly circular(s) for user {user_id}")
                    except Exception as d_err:
                        logger.error(f"Error checking deal circular freshness for user {user_id}: {d_err}")

                # If interval is 0 or negative, auto-fetch for email is disabled
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
    # Use start of current day so events occurring earlier today or all-day events remain visible
    today_start = datetime.now().date().isoformat()
    c.execute("SELECT * FROM events WHERE status IN ('pending', 'added') AND user_id=? AND date >= ? ORDER BY date ASC", (user_id, today_start))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Google Calendar OAuth & Sync ---
@app.get("/api/auth/google/url")
def get_google_auth_url(request: Request, from_wizard: Optional[bool] = False, user_id: str = Depends(verify_auth)):
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "Client secrets missing"}
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s = json.loads(c.fetchone()[0] or "{}")
    base_url = s.get("public_url") or f"{request.url.scheme}://{request.url.netloc}"
    redirect_uri = f"{base_url.rstrip('/')}/api/auth/google/callback"
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    s["oauth_state"] = state
    s["oauth_verifier"] = flow.code_verifier
    s["oauth_from_wizard"] = bool(from_wizard)
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
    from_wizard = user_settings.pop("oauth_from_wizard", False)
    try:
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=redirect_uri)
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        flow.code_verifier = user_settings.get("oauth_verifier")
        flow.fetch_token(authorization_response=str(request.url))
        token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
        with open(token_file, 'w') as f:
            f.write(flow.credentials.to_json())

        # Extract user's Google email if returned in id_token
        google_email = ""
        if flow.credentials and flow.credentials.id_token:
            try:
                import base64
                parts = flow.credentials.id_token.split(".")
                if len(parts) >= 2:
                    padding = "=" * (4 - len(parts[1]) % 4)
                    payload_json = base64.urlsafe_b64decode(parts[1] + padding).decode("utf-8")
                    payload = json.loads(payload_json)
                    google_email = payload.get("email", "")
            except Exception as e:
                logger.debug(f"Could not parse email from id_token: {e}")
        
        if google_email:
            user_settings["google_email"] = google_email

        conn = get_db_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(user_settings), user_id))
        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Google OAuth Failed for user {user_id}: {e}")

    if from_wizard:
        return RedirectResponse(url="/?wizard_step=3&oauth_success=1")
    return RedirectResponse(url="/?oauth_success=1")

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
        creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
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
        creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
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
        creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
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
            existing_ev = find_existing_event_in_db(user_id, ed.get("title", ""), ed.get("date", ""), conn=conn)
            if existing_ev:
                event_rows.append(existing_ev)
            else:
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
        creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
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
                    existing_ev = find_existing_event_in_db(user_id, ed.get("title", ""), ed.get("date", ""), conn=conn)
                    if existing_ev:
                        event_rows.append(existing_ev)
                    else:
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

@app.get("/api/logs", dependencies=[Depends(verify_admin)])
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
@app.get("/meals")
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

def stem_word(w: str) -> str:
    """Stem English plural nouns into singular canonical forms."""
    if len(w) <= 3:
        return w
    if w.endswith('ies') and len(w) > 4:
        return w[:-3] + 'y' # berries -> berry, cherries -> cherry
    if w.endswith(('sses', 'shes', 'ches', 'xes', 'zes')):
        return w[:-2] # dishes -> dish, peaches -> peach, boxes -> box
    if w.endswith('oes'):
        return w[:-2] # potatoes -> potato, tomatoes -> tomato
    if w.endswith('s') and not w.endswith('ss'):
        return w[:-1] # apples -> apple, steaks -> steak, eggs -> egg
    return w

def normalize_grocery_store_name(merchant_raw: str) -> str:
    m = (merchant_raw or '').strip()
    ml = m.lower()
    if 'kroger' in ml: return 'Kroger'
    if 'sprouts' in ml: return 'Sprouts Farmers Market'
    if 'tom thumb' in ml: return 'Tom Thumb'
    if 'albertsons' in ml: return 'Albertsons'
    if 'central market' in ml: return 'Central Market'
    if 'h-e-b' in ml or 'heb' in ml: return 'H-E-B'
    if 'publix' in ml: return 'Publix'
    if 'safeway' in ml: return 'Safeway'
    if 'sam' in ml and 'club' in ml: return "Sam's Club"
    if 'food lion' in ml: return 'Food Lion'
    if 'meijer' in ml: return 'Meijer'
    if 'hy-vee' in ml or 'hyvee' in ml: return 'Hy-Vee'
    if 'wegmans' in ml: return 'Wegmans'
    if 'lidl' in ml: return 'Lidl'
    if 'jewel' in ml: return 'Jewel-Osco'
    if 'vons' in ml: return 'Vons'
    if 'ralphs' in ml: return 'Ralphs'
    if 'smith' in ml: return "Smith's"
    if 'fry' in ml: return "Fry's Food Stores"
    if 'king soopers' in ml: return 'King Soopers'
    if 'harris teeter' in ml: return 'Harris Teeter'
    if 'giant' in ml: return 'Giant Food'
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

def parse_flyer_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime or date string into a UTC-aware datetime object."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    s = dt_str.strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    try:
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
        if m:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 23, 59, 59, tzinfo=timezone.utc)
    except Exception:
        pass
    return None

def is_store_deals_expired(store: dict) -> bool:
    """
    Check if a store's cached circular deals are expired and should be re-fetched.
    If a flyer ran 9/1 to 9/8, on 9/9 valid_to < now() returns True, triggering
    automatic ingestion of the new 9/9 circular deals.
    """
    valid_to_str = store.get('valid_to')
    if not valid_to_str and store.get('notes'):
        m = re.search(r'to\s+(\d{4}-\d{2}-\d{2})', store['notes'], re.I)
        if m:
            valid_to_str = m.group(1)
            
    now_utc = datetime.now(timezone.utc)
    if valid_to_str:
        v_to = parse_flyer_datetime(valid_to_str)
        if v_to:
            return now_utc > v_to

    cached = store.get('cached_deals')
    if not cached or cached == '[]' or cached == 'null':
        return True
        
    last_scanned = store.get('last_scanned')
    if not last_scanned:
        return True
        
    ls_dt = parse_flyer_datetime(last_scanned)
    if ls_dt:
        if (now_utc - ls_dt).total_seconds() > 86400:
            return True
            
    return False

def sanitize_deal_price_and_notes(price_str: str, notes_str: str = "") -> tuple:
    p = (price_str or '').strip()
    n = (notes_str or '').strip()
    
    if len(p) > 25 or ('buy ' in p.lower() and 'get ' in p.lower()) or 'coupon' in p.lower() or 'free with' in p.lower() or 'save up to' in p.lower() or p.lower().startswith('save '):
        if not n:
            n = p
        elif p not in n:
            n = f"{p} | {n}"
            
        pl = p.lower()
        if 'yellow coupon' in pl:
            if 'free' in pl:
                p = 'Yellow Coupon (Free Item)'
            else:
                p = 'Yellow Coupon Deal'
        elif 'digital coupon' in pl:
            p = 'Digital Coupon'
        elif 'get free' in pl or 'get 1 free' in pl or 'bogo' in pl:
            p = 'Buy & Get Free'
        elif 'save ' in pl or 'save up to' in pl:
            m_save = re.search(r'(save\s+(?:up\s+to\s+)?\$?\d+(?:\.\d{1,2})?(?:\s*(?:/|per)\s*lb)?)', p, re.I)
            if m_save:
                p = m_save.group(1).title()
            else:
                p = 'Special Savings'
        else:
            p = 'Special Promo'
            
    return p, n

def parse_numeric_price(price_str: str) -> dict:
    if not price_str or not isinstance(price_str, str):
        return {'unit_price': None, 'unit': 'unknown', 'raw': ''}
    
    raw = price_str.strip()
    raw_lower = raw.lower()
    
    if len(raw) > 28 or 'coupon' in raw_lower or ('buy ' in raw_lower and 'get ' in raw_lower) or 'free with' in raw_lower or 'save up to' in raw_lower or raw_lower.startswith('save '):
        return {'unit_price': None, 'unit': 'coupon', 'raw': raw}
        
    if 'bogo' in raw_lower or 'buy 1 get 1' in raw_lower or 'buy one get one' in raw_lower:
        return {'unit_price': None, 'unit': 'bogo', 'raw': raw}
        
    # Cents per lb (e.g. 99¢/lb, 79c per lb, 88 cents/lb)
    m_cents_lb = re.search(r'([0-9]{1,3})\s*(?:¢|c\b|cents?\b)\s*(?:/|\s+per\s+|\s+)?(?:lb|lbs|pound)\b', raw_lower)
    if m_cents_lb:
        try:
            return {'unit_price': round(float(m_cents_lb.group(1)) / 100.0, 2), 'unit': 'lb', 'raw': raw}
        except Exception:
            pass

    # Cents each or general cents (e.g. 99¢, 50¢ ea, 49c)
    m_cents = re.search(r'([0-9]{1,3})\s*(?:¢|c\b|cents?\b)', raw_lower)
    if m_cents:
        try:
            unit = 'lb' if ('/lb' in raw_lower or 'per lb' in raw_lower) else 'ea'
            return {'unit_price': round(float(m_cents.group(1)) / 100.0, 2), 'unit': unit, 'raw': raw}
        except Exception:
            pass

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

def detect_beef_grade(item_name: str, category: str = "") -> str:
    name = (item_name or '').lower()
    cat = (category or '').lower()
    
    # Check if beef/meat
    beef_indicators = [
        'beef', 'steak', 'ribeye', 'strip', 'sirloin', 'brisket', 'roast',
        'chuck', 'tenderloin', 'filet', 't-bone', 'porterhouse', 'flank',
        'skirt', 'round', 'tri-tip', 'patty', 'patties', 'ground beef',
        'short rib', 'prime rib', 'top sirloin', 'new york strip'
    ]
    
    is_beef = any(b in name for b in beef_indicators) or ('meat' in cat and any(b in name for b in ['steak', 'roast', 'angus']))
    if not is_beef:
        return ""
        
    # Detect grade
    if re.search(r'\b(?:usda\s*prime|prime\s*1|prime\s*beef|prime\s*choice\s*n\/a|prime)\b', name):
        return "prime"
    if re.search(r'\b(?:usda\s*choice|choice\s*beef|choice)\b', name):
        return "choice"
    if re.search(r'\b(?:usda\s*select|select\s*beef|select)\b', name):
        return "select"
    if re.search(r'\b(?:wagyu|kobe|american\s*wagyu)\b', name):
        return "wagyu"
    if re.search(r'\b(?:black\s*angus|angus)\b', name):
        return "angus"
        
    return "none"

def normalize_item_history_key(item_name: str, category: str = "") -> tuple:
    name = (item_name or '').lower()
    
    # 1. Detect beef grade if beef
    beef_grade = detect_beef_grade(item_name, category)
    
    # 2. Clean weights, measurements, packaging
    cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:oz|lb|lbs|ct|pk|pack|count|fl\s*oz|gal|gallon|qt|pt|liter|l|ml|kg|g)\b', ' ', name)
    cleaned = re.sub(r'\b\d+/\d+\b', ' ', cleaned)
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', cleaned)
    
    # 3. Stop words
    stop_words = {
        'fresh', 'organic', 'usda', 'prime', 'choice', 'select', 'all', 'natural', 'frozen',
        'great', 'value', 'signature', 'h-e-b', 'heb', 'kroger', 'market', 'pantry',
        'family', 'pack', 'super', 'size', 'selected', 'varieties', 'brand', 'assorted', 'large',
        'small', 'medium', 'jumbo', 'grade', 'a', 'aa', 'free', 'range', 'cage', 'wild', 'caught',
        'farm', 'raised', 'boneless', 'skinless', 'bone', 'in', 'center', 'cut', 'thin', 'sliced',
        'thick', 'whole', 'half', 'quarter', 'the', 'and', 'or', 'with', 'in', 'for', 'of', 'item', 'lb', 'lbs',
        'claws', 'claw'
    }
    
    tokens = [w for w in cleaned.split() if len(w) > 2 and w not in stop_words]
    
    # Stem simple plurals
    canonical_tokens = [stem_word(t) for t in tokens]
        
    if 'claw' in name and 'claw' not in canonical_tokens:
        canonical_tokens.append('claw')
    if 'crab' in name and 'crab' not in canonical_tokens:
        canonical_tokens.append('crab')
        
    canonical_tokens.sort()
    base_key = " ".join(canonical_tokens)
    
    if beef_grade:
        final_key = f"beef:{base_key}:{beef_grade}"
    else:
        final_key = base_key
        
    return final_key, beef_grade

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
    return {stem_word(w) for w in cleaned.split() if len(w) > 2 and w not in stop_words}

def find_cross_store_comparison(current_item_name: str, current_store: str, current_price_str: str, current_category: str, all_stores_deals: list) -> dict:
    clean_curr_price, _ = sanitize_deal_price_and_notes(current_price_str, "")
    curr_parsed = parse_numeric_price(clean_curr_price)
    curr_price_val = curr_parsed.get('unit_price')
    curr_unit = curr_parsed.get('unit')
    curr_tokens = normalize_item_tokens(current_item_name)
    norm_curr_store = normalize_grocery_store_name(current_store).lower()
    curr_grade = detect_beef_grade(current_item_name, current_category)

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
                
            # Grade isolation for beef: prevent comparing Prime vs Select or Choice vs Select
            if curr_grade:
                d_grade = detect_beef_grade(d_name, d_cat)
                if d_grade and d_grade != curr_grade:
                    continue
                
            d_tokens = normalize_item_tokens(d_name)
            if not curr_tokens or not d_tokens:
                continue
                
            overlap = curr_tokens.intersection(d_tokens)
            if len(overlap) >= min(2, len(curr_tokens)) and (len(overlap) / max(len(curr_tokens), 1)) >= 0.5:
                d_clean_price, _ = sanitize_deal_price_and_notes(d.get('price', ''), d.get('notes', ''))
                d_parsed = parse_numeric_price(d_clean_price)
                matches.append({
                    'store': s_name,
                    'item': d_name,
                    'price_str': d_clean_price,
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
                'lowest_other_store': lowest_store,
                'lowest_other_price': lowest_price_str,
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

def record_store_deals_price_history(conn, user_id: str, store_name: str, deals: list, recorded_at_iso: Optional[str] = None):
    if not deals:
        return
    recorded_at = recorded_at_iso or datetime.now().isoformat()
    rec_date = recorded_at[:10]
    c = conn.cursor()
    
    for d in deals:
        raw_name = d.get('item') or ''
        if not raw_name or len(raw_name.strip()) < 2:
            continue
        clean_price, notes_str = sanitize_deal_price_and_notes(d.get('price', ''), d.get('notes', ''))
        parsed = parse_numeric_price(clean_price)
        unit_price = parsed.get('unit_price')
        unit = parsed.get('unit') or 'ea'
        category = d.get('category', 'Pantry & Dry Goods')
        
        if unit_price is None:
            continue
            
        norm_key, beef_grade = normalize_item_history_key(raw_name, category)
        if not norm_key:
            continue
            
        try:
            c.execute('''SELECT id FROM grocery_price_history 
                         WHERE user_id=? AND normalized_key=? AND store_name=? AND substr(recorded_at, 1, 10)=?''',
                      (user_id, norm_key, store_name, rec_date))
            existing = c.fetchone()
            if existing:
                c.execute('''UPDATE grocery_price_history SET price_str=?, unit_price=?, unit=?, beef_grade=?, category=?, recorded_at=? WHERE id=?''',
                          (clean_price, unit_price, unit, beef_grade, category, recorded_at, existing[0]))
            else:
                rec_id = str(uuid.uuid4())
                c.execute('''INSERT INTO grocery_price_history (id, user_id, item_name, normalized_key, store_name, price_str, unit_price, unit, beef_grade, category, recorded_at)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (rec_id, user_id, raw_name, norm_key, store_name, clean_price, unit_price, unit, beef_grade, category, recorded_at))
        except Exception as ex:
            logger.debug(f"Error saving price history point: {ex}")

def get_item_price_history_metrics(conn, user_id: str, item_name: str, current_price_val: Optional[float], category: str = "", current_unit: str = "ea") -> Optional[dict]:
    if current_price_val is None:
        return None
        
    norm_key, beef_grade = normalize_item_history_key(item_name, category)
    if not norm_key:
        return None
        
    try:
        c = conn.cursor()
        c.execute('''SELECT store_name, price_str, unit_price, unit, recorded_at 
                     FROM grocery_price_history 
                     WHERE user_id=? AND normalized_key=? AND unit=? 
                     ORDER BY recorded_at DESC''',
                  (user_id, norm_key, current_unit))
        rows = c.fetchall()
        
        if not rows:
            return {
                'has_history': False,
                'beef_grade': beef_grade,
                'records_count': 0,
                'history_badge': None,
                'badge_type': 'neutral',
                'summary': f"First time recorded ({beef_grade.upper()} Grade)" if beef_grade and beef_grade != 'none' else "First time recorded"
            }
            
        prices = [r[2] for r in rows]
        all_time_low = min(prices)
        all_time_high = max(prices)
        avg_price = round(sum(prices) / len(prices), 2)
        
        lowest_row = min(rows, key=lambda r: r[2])
        lowest_store = lowest_row[0]
        lowest_price_str = lowest_row[1]
        lowest_date_str = lowest_row[4][:10]
        
        now = datetime.now()
        better_or_equal_dates = []
        for r in rows:
            if r[2] <= current_price_val:
                try:
                    better_or_equal_dates.append(datetime.fromisoformat(r[4]))
                except Exception:
                    pass
                    
        days_since_seen = None
        if better_or_equal_dates:
            most_recent_better = max(better_or_equal_dates)
            days_since_seen = max((now - most_recent_better).days, 0)
        else:
            oldest_record_dates = []
            for r in rows:
                try: oldest_record_dates.append(datetime.fromisoformat(r[4]))
                except Exception: pass
            if oldest_record_dates:
                days_since_seen = max((now - min(oldest_record_dates)).days, 1)
            else:
                days_since_seen = 30
                
        grade_label = f" [{beef_grade.upper()}]" if beef_grade and beef_grade != 'none' else ""
        unit_suffix = "/lb" if current_unit == 'lb' else ""
        
        diff_from_low = round(current_price_val - all_time_low, 2)
        diff_from_avg = round(current_price_val - avg_price, 2)
        
        if diff_from_low <= -0.15:
            savings = abs(diff_from_low)
            badge_type = 'all_time_low'
            time_frame = f"{days_since_seen} days" if days_since_seen < 60 else f"{days_since_seen // 30} months"
            summary = f"🔥 Best{grade_label} Price in {time_frame}! Save ${savings:.2f}{unit_suffix} vs prev low ({lowest_price_str} at {lowest_store})"
        elif abs(diff_from_low) <= 0.10:
            badge_type = 'matching_low'
            summary = f"🏷️ Matching All-Time Low{grade_label} ({lowest_price_str} at {lowest_store})"
        elif diff_from_avg <= -0.50:
            savings = abs(diff_from_avg)
            badge_type = 'below_avg'
            summary = f"📉 ${savings:.2f}{unit_suffix} Below Avg{grade_label} (Avg: ${avg_price:.2f}{unit_suffix})"
        elif diff_from_avg >= 0.50:
            extra = diff_from_avg
            badge_type = 'above_avg'
            summary = f"📈 ${extra:.2f}{unit_suffix} Above Avg{grade_label} (Avg: ${avg_price:.2f}{unit_suffix})"
        else:
            badge_type = 'typical'
            summary = f"⚖️ Typical Price{grade_label} (Avg: ${avg_price:.2f}{unit_suffix})"
            
        return {
            'has_history': True,
            'beef_grade': beef_grade,
            'records_count': len(rows),
            'all_time_low': all_time_low,
            'all_time_low_store': lowest_store,
            'all_time_low_date': lowest_date_str,
            'avg_price': avg_price,
            'diff_from_low': diff_from_low,
            'diff_from_avg': diff_from_avg,
            'badge_type': badge_type,
            'summary': summary,
            'history_badge': summary
        }
    except Exception as e:
        logger.debug(f"Error querying price history metrics: {e}")
        return None

def clean_deal_name(name: str) -> str:
    if not name:
        return ''
    n = name.strip()
    n = re.sub(r'^(?:fresh!?|sale!?|hot\s+deal!?|new!?|special!?|great\s+price!?|save!?|super\s+sale!?)\s*', '', n, flags=re.I).strip()
    n = re.sub(r'[\*\#]+$', '', n).strip()
    n = re.sub(r'\s+', ' ', n)
    return n

def format_deal_price_and_notes(raw_price, sale_story: Optional[str], description: Optional[str], brand: Optional[str], clean_name: str):
    price_str = ''
    notes_parts = []
    
    if raw_price:
        try:
            fval = float(raw_price)
            price_str = f"${fval:.2f}"
        except Exception:
            price_str = str(raw_price).strip()
            
    if sale_story:
        ss = sale_story.strip()
        if re.match(r'^\$?\d+(?:\.\d{1,2})?(?:\s*/\s*(?:lb|ea|oz))?$', ss, re.I) or re.match(r'^\d+\s+(?:for|/)\s+\$?\d+(?:\.\d{1,2})?$', ss, re.I) or re.match(r'^(?:bogo|buy\s+1\s+get\s+1(?:\s+free)?)$', ss, re.I):
            if not price_str:
                price_str = ss
        else:
            if not price_str:
                m_save = re.search(r'(save\s+(?:up\s+to\s+)?\$?\d+(?:\.\d{1,2})?(?:\s*(?:/|per)\s*lb)?)', ss, re.I)
                if m_save:
                    price_str = m_save.group(1).title()
                elif 'yellow coupon' in ss.lower():
                    price_str = 'Yellow Coupon'
                elif 'digital coupon' in ss.lower():
                    price_str = 'Digital Coupon'
                elif 'coupon' in ss.lower():
                    price_str = 'Coupon Deal'
                else:
                    price_str = 'Special Offer'
            # Only add to notes if not identical or redundant with the item name or price
            if ss.lower() != clean_name.lower() and clean_name.lower() not in ss.lower() and ss.lower() != price_str.lower():
                notes_parts.append(ss)
            
    if not price_str:
        price_str = 'Sale'
        
    if description and description.strip():
        d_clean = description.strip()
        if d_clean not in notes_parts and d_clean.lower() != clean_name.lower() and clean_name.lower() not in d_clean.lower() and d_clean.lower() != price_str.lower():
            notes_parts.append(d_clean)
    if brand and brand.strip() and brand.strip().lower() not in clean_name.lower():
        notes_parts.append(f"Brand: {brand.strip()}")
        
    notes_str = ' | '.join(notes_parts)
    return price_str, notes_str

def _fetch_single_flipp_flyer(f: dict, postal_code: str, headers: dict, ctx: ssl.SSLContext, norm_store: str):
    fid = f.get('id')
    if not fid:
        return norm_store, fid, f, []
    furl = f"https://backflipp.wishabi.com/flipp/flyers/{fid}?postal_code={postal_code}&locale=en-us"
    try:
        freq = urllib.request.Request(furl, headers=headers)
        with urllib.request.urlopen(freq, timeout=8, context=ctx) as fresp:
            fdata = json.loads(fresp.read().decode('utf-8'))
            items = fdata.get('items', [])
            
            deals_map = {}
            
            for it in items:
                raw_name = it.get('name')
                if not raw_name or len(raw_name.strip()) < 2:
                    continue
                clean_name = clean_deal_name(raw_name)
                if not clean_name:
                    continue
                
                raw_price = it.get('price') or it.get('current_price') or ''
                sale_story = it.get('sale_story') or ''
                desc = it.get('description') or ''
                brand = it.get('brand') or ''
                
                price_str, notes_str = format_deal_price_and_notes(raw_price, sale_story, desc, brand, clean_name)
                
                img_url = it.get('cutout_image_url') or it.get('clean_image_url') or it.get('clipping_image_url') or it.get('image_url') or it.get('original_image_url') or ''
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('http://'):
                    img_url = 'https://' + img_url[7:]
                
                name_key = clean_name.lower()
                if name_key in deals_map:
                    cur = deals_map[name_key]
                    has_curr_num = parse_numeric_price(cur['price']).get('unit_price') is not None
                    has_new_num = parse_numeric_price(price_str).get('unit_price') is not None
                    if not has_curr_num and has_new_num:
                        cur['price'] = price_str
                    if not cur.get('image_url') and img_url:
                        cur['image_url'] = img_url
                    if notes_str and notes_str not in cur.get('notes', ''):
                        cur['notes'] = f"{cur.get('notes', '')} | {notes_str}".strip(" |")
                else:
                    deals_map[name_key] = {
                        'item': clean_name,
                        'price': price_str,
                        'category': guess_deal_category(clean_name),
                        'notes': notes_str,
                        'image_url': img_url
                    }
            return norm_store, fid, f, list(deals_map.values())
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
        'whole foods', 'trader joe', 'brookshire', 'market street', 'united supermarkets',
        'publix', 'safeway', 'sam', 'food lion', 'meijer', 'hy-vee', 'hyvee', 'wegmans',
        'lidl', 'jewel', 'vons', 'ralphs', 'smith', 'fry', 'king soopers', 'harris teeter',
        'giant', 'central market', 'bravo'
    ]
    
    stores_data = {}
    target_filter_norm = normalize_grocery_store_name(store_name_filter).lower() if store_name_filter else None

    now_utc = datetime.now(timezone.utc)
    merchant_flyers_map = {}
    
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
            
        v_from = parse_flyer_datetime(f.get('valid_from'))
        v_to = parse_flyer_datetime(f.get('valid_to'))
        is_active = (v_to is None or v_to >= now_utc)
        
        if norm_store not in merchant_flyers_map:
            merchant_flyers_map[norm_store] = []
        merchant_flyers_map[norm_store].append({
            'flyer': f,
            'is_active': is_active,
            'valid_from_dt': v_from,
            'valid_to_dt': v_to
        })

    if not merchant_flyers_map:
        return {}

    # For each store, select the best active / upcoming flyer(s)
    # If active flyers exist, discard expired flyers so they never pollute fresh deals
    matched_flyers = []
    for nstore, f_entries in merchant_flyers_map.items():
        active_entries = [e for e in f_entries if e['is_active']]
        if active_entries:
            # Sort active flyers by valid_from descending (most recent/upcoming promotional week first)
            active_entries.sort(key=lambda e: (
                e['valid_from_dt'] or datetime.min.replace(tzinfo=timezone.utc),
                e['flyer'].get('title') or ''
            ), reverse=True)
            for e in active_entries:
                matched_flyers.append((e['flyer'], nstore))
        else:
            # Fallback if no active flyer exists yet: keep the newest expired flyer temporarily
            f_entries.sort(key=lambda e: (
                e['valid_to_dt'] or datetime.min.replace(tzinfo=timezone.utc)
            ), reverse=True)
            if f_entries:
                matched_flyers.append((f_entries[0]['flyer'], nstore))

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
                    f_v_from = f.get('valid_from')
                    f_v_to = f.get('valid_to')
                    if norm_store not in stores_data:
                        stores_data[norm_store] = {
                            'name': norm_store,
                            'ad_url': ad_web_url,
                            'flyer_id': fid,
                            'flyer_title': f.get('title') or f"{norm_store} Weekly Ad",
                            'valid_from': f_v_from,
                            'valid_to': f_v_to,
                            'deals': deals
                        }
                    else:
                        cur_v_to_dt = parse_flyer_datetime(stores_data[norm_store].get('valid_to'))
                        new_v_to_dt = parse_flyer_datetime(f_v_to)
                        # Keep earlier expiration date if merging weekly ad with longer seasonal promo
                        if new_v_to_dt and cur_v_to_dt and new_v_to_dt < cur_v_to_dt:
                            stores_data[norm_store]['valid_to'] = f_v_to
                            stores_data[norm_store]['ad_url'] = ad_web_url
                        existing_map = {d['item'].lower(): d for d in stores_data[norm_store]['deals']}
                        for d in deals:
                            d_key = d['item'].lower()
                            if d_key not in existing_map:
                                stores_data[norm_store]['deals'].append(d)
                                existing_map[d_key] = d
                            else:
                                cur = existing_map[d_key]
                                has_curr_num = parse_numeric_price(cur['price']).get('unit_price') is not None
                                has_new_num = parse_numeric_price(d['price']).get('unit_price') is not None
                                if not has_curr_num and has_new_num:
                                    cur['price'] = d['price']
                                if not cur.get('image_url') and d.get('image_url'):
                                    cur['image_url'] = d['image_url']
                                if d.get('notes') and d['notes'] not in cur.get('notes', ''):
                                    cur['notes'] = f"{cur.get('notes', '')} | {d['notes']}".strip(" |")
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
                            # Skip expired items from search cache
                            sit_v_to = parse_flyer_datetime(sit.get('valid_to'))
                            if sit_v_to and sit_v_to < now_utc:
                                continue
                            raw_name = sit.get('name') or ''
                            if not raw_name or len(raw_name.strip()) < 2:
                                continue
                            clean_name = clean_deal_name(raw_name)
                            if not clean_name:
                                continue
                            
                            s_raw_price = sit.get('current_price') or sit.get('price') or ''
                            s_sale = sit.get('sale_story') or ''
                            s_desc = sit.get('description') or ''
                            s_brand = sit.get('brand') or ''
                            
                            s_price_str, s_notes_str = format_deal_price_and_notes(s_raw_price, s_sale, s_desc, s_brand, clean_name)
                            
                            s_img = sit.get('cutout_image_url') or sit.get('clean_image_url') or sit.get('clipping_image_url') or sit.get('image_url') or sit.get('original_image_url') or ''
                            if s_img.startswith('//'):
                                s_img = 'https:' + s_img
                            elif s_img.startswith('http://'):
                                s_img = 'https://' + s_img[7:]
                            
                            name_key = clean_name.lower()
                            if name_key in existing_map:
                                cur_deal = existing_map[name_key]
                                has_curr_num = parse_numeric_price(cur_deal['price']).get('unit_price') is not None
                                has_new_num = parse_numeric_price(s_price_str).get('unit_price') is not None
                                
                                if not has_curr_num and has_new_num:
                                    cur_deal['price'] = s_price_str
                                if s_notes_str and s_notes_str not in cur_deal.get('notes', ''):
                                    cur_deal['notes'] = f"{cur_deal.get('notes', '')} | {s_notes_str}".strip(" |")
                                if not cur_deal.get('image_url') and s_img:
                                    cur_deal['image_url'] = s_img
                            else:
                                if s_price_str or s_notes_str:
                                    new_deal = {
                                        'item': clean_name,
                                        'price': s_price_str or "Sale",
                                        'category': guess_deal_category(clean_name),
                                        'notes': s_notes_str or "",
                                        'image_url': s_img
                                    }
                                    store_deals.append(new_deal)
                                    existing_map[name_key] = new_deal
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

def refresh_user_expired_deals(user_id: str, force: bool = False) -> dict:
    """
    Checks if any grocery stores for user_id have expired deals (or if force=True).
    If a deal ran 9/1 to 9/8, on 9/9 valid_to < now() triggers an automatic refresh,
    pulling the next new deals for that store and updating the database cache.
    """
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, notes, last_scanned, cached_deals, valid_from, valid_to FROM grocery_stores WHERE user_id=?", (user_id,))
    stores = [dict(r) for r in c.fetchall()]
    
    if not stores:
        conn.close()
        return {"refreshed": 0, "message": "No stores configured"}
        
    now_utc = datetime.now(timezone.utc)
    expired_stores = []
    
    for s in stores:
        if force:
            expired_stores.append(s)
            continue
            
        # Cooldown check: if checked in the last 15 minutes and has non-empty deals, don't spam
        ls = s.get("last_scanned")
        cached = s.get("cached_deals")
        has_deals = bool(cached and cached != '[]' and cached != 'null')
        if ls and has_deals:
            ls_dt = parse_flyer_datetime(ls)
            if ls_dt and (now_utc - ls_dt).total_seconds() < 900: # 15 minutes cooldown
                continue
                
        if is_store_deals_expired(s):
            expired_stores.append(s)
            
    if not expired_stores:
        conn.close()
        return {"refreshed": 0, "message": "All store deals are currently fresh"}
        
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
    postal_code = (settings.get("postal_code") or "76262").strip()
    
    logger.info(f"Auto-refreshing {len(expired_stores)} expired grocery stores for user {user_id} (zip {postal_code})...")
    
    # Fetch newest circulars from Flipp
    flipp_stores = fetch_flipp_store_deals(postal_code)
    now_iso = datetime.now().isoformat()
    refreshed_count = 0
    
    for s in expired_stores:
        sname = s["name"]
        norm_key = normalize_grocery_store_name(sname)
        new_deals = []
        new_valid_from = None
        new_valid_to = None
        new_ad_url = s["ad_url"]
        new_notes = s["notes"] or ""
        
        if norm_key in flipp_stores:
            f_info = flipp_stores[norm_key]
            new_deals = f_info.get("deals", [])
            new_valid_from = f_info.get("valid_from")
            new_valid_to = f_info.get("valid_to")
            if new_valid_to:
                new_notes = f"Valid: {new_valid_from[:10]} to {new_valid_to[:10]}" if new_valid_from else f"Valid to {new_valid_to[:10]}"
            if f_info.get("ad_url"):
                new_ad_url = f_info["ad_url"]
        elif s["ad_url"] and s["ad_url"].startswith(("http://", "https://")) and "flipp.com" not in s["ad_url"]:
            content = fetch_url_clean_content(s["ad_url"])
            if content:
                new_deals = extract_store_deals_with_ai(sname, content, settings)
                
        if new_deals:
            c.execute(
                "UPDATE grocery_stores SET ad_url=?, notes=?, last_scanned=?, cached_deals=?, valid_from=?, valid_to=? WHERE id=? AND user_id=?",
                (new_ad_url, new_notes, now_iso, json.dumps(new_deals), new_valid_from, new_valid_to, s["id"], user_id)
            )
            record_store_deals_price_history(conn, user_id, sname, new_deals, now_iso)
            refreshed_count += 1
        else:
            # Even if 0 deals were found on this pass, touch last_scanned so we don't spam in tight loops
            c.execute("UPDATE grocery_stores SET last_scanned=? WHERE id=? AND user_id=?", (now_iso, s["id"], user_id))
            
    conn.commit()
    conn.close()
    
    logger.info(f"Auto-refresh complete: updated {refreshed_count} stores with newest circular deals.")
    return {"refreshed": refreshed_count, "expired_count": len(expired_stores)}

# --- Store Management Endpoints ---
@app.get("/api/groceries/stores")
def get_grocery_stores(user_id: str = Depends(verify_auth)):
    try:
        refresh_user_expired_deals(user_id)
    except Exception as e:
        logger.warning(f"Error checking deal freshness in get_grocery_stores: {e}")

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, notes, last_scanned, cached_deals, valid_from, valid_to FROM grocery_stores WHERE user_id=? ORDER BY name ASC", (user_id,))
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
        d["is_expired"] = is_store_deals_expired(d)
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
    record_store_deals_price_history(conn, user_id, store["name"], deals, now_iso)
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
        valid_from = sinfo.get("valid_from")
        valid_to = sinfo.get("valid_to")
        valid_range = f"Valid: {valid_from[:10]} to {valid_to[:10]}" if valid_to else ""
        
        norm_key = sname.lower()
        if norm_key in existing_stores:
            store_id = existing_stores[norm_key]
            c.execute(
                "UPDATE grocery_stores SET name=?, ad_url=?, notes=?, last_scanned=?, cached_deals=?, valid_from=?, valid_to=? WHERE id=? AND user_id=?",
                (sname, ad_url, valid_range, now_iso, deals_json, valid_from, valid_to, store_id, user_id)
            )
        else:
            store_id = str(uuid.uuid4())
            c.execute(
                "INSERT INTO grocery_stores (id, user_id, name, ad_url, notes, last_scanned, cached_deals, valid_from, valid_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (store_id, user_id, sname, ad_url, valid_range, now_iso, deals_json, valid_from, valid_to)
            )
            existing_stores[norm_key] = store_id
            
        record_store_deals_price_history(conn, user_id, sname, deals, now_iso)
        updated_stores.append({
            "id": store_id,
            "name": sname,
            "deals_count": len(deals),
            "ad_url": ad_url,
            "valid_range": valid_range,
            "valid_from": valid_from,
            "valid_to": valid_to
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
    c.execute("SELECT id, name, ad_url, notes FROM grocery_stores WHERE id=? AND user_id=?", (store_id, user_id))
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
    valid_range = store["notes"] or ""
    valid_from = None
    valid_to = None
    
    deals = []
    now_iso = datetime.now().isoformat()
    warning_msg = None
    
    # Try automatic Flipp lookup first
    flipp_stores = fetch_flipp_store_deals(postal_code, store_name_filter=name)
    if flipp_stores:
        matched_info = list(flipp_stores.values())[0]
        deals = matched_info.get("deals", [])
        valid_from = matched_info.get("valid_from")
        valid_to = matched_info.get("valid_to")
        if valid_to:
            valid_range = f"Valid: {valid_from[:10]} to {valid_to[:10]}" if valid_from else f"Valid to {valid_to[:10]}"
        if matched_info.get("ad_url"):
            url = matched_info["ad_url"]
    
    # If not on Flipp or Flipp returned 0, try direct web content fetch + AI
    if not deals and url and url.startswith(("http://", "https://")) and "flipp.com" not in url:
        content = fetch_url_clean_content(url)
        deals = extract_store_deals_with_ai(name, content, settings)
        if not deals and (not content or len(content.strip()) < 50):
            warning_msg = f"Could not read circular text from {url}. Supermarkets (like Kroger, Tom Thumb, and HEB) block scrapers without cookies. Tip: Use 1-Click Auto-Fetch Deals by Zip Code or click '📋 Paste Deals' to paste flyer text directly!"
            
    c.execute("UPDATE grocery_stores SET ad_url=?, notes=?, last_scanned=?, cached_deals=?, valid_from=?, valid_to=? WHERE id=? AND user_id=?",
              (url, valid_range, now_iso, json.dumps(deals), valid_from, valid_to, store_id, user_id))
    record_store_deals_price_history(conn, user_id, name, deals, now_iso)
    conn.commit()
    conn.close()
    return {"status": "success", "deals_found": len(deals), "deals": deals, "valid_from": valid_from, "valid_to": valid_to, "warning": warning_msg}

@app.post("/api/groceries/stores/scan_all")
def scan_all_grocery_stores(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, notes FROM grocery_stores WHERE user_id=?", (user_id,))
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
        valid_from = None
        valid_to = None
        valid_range = s["notes"] or ""
        
        if norm_key in flipp_stores:
            matched = flipp_stores[norm_key]
            deals = matched.get("deals", [])
            valid_from = matched.get("valid_from")
            valid_to = matched.get("valid_to")
            if valid_to:
                valid_range = f"Valid: {valid_from[:10]} to {valid_to[:10]}" if valid_from else f"Valid to {valid_to[:10]}"
            if matched.get("ad_url"):
                ad_url = matched["ad_url"]
        elif s["ad_url"] and s["ad_url"].startswith(("http://", "https://")) and "flipp.com" not in s["ad_url"]:
            content = fetch_url_clean_content(s["ad_url"])
            deals = extract_store_deals_with_ai(s["name"], content, settings)
            if settings.get("ai_provider", "gemini") == "gemini":
                time.sleep(2.0)
                
        c.execute("UPDATE grocery_stores SET ad_url=?, notes=?, last_scanned=?, cached_deals=?, valid_from=?, valid_to=? WHERE id=? AND user_id=?",
                  (ad_url, valid_range, now_iso, json.dumps(deals), valid_from, valid_to, s["id"], user_id))
        record_store_deals_price_history(conn, user_id, s["name"], deals, now_iso)
        results.append({"store": s["name"], "deals_found": len(deals), "valid_from": valid_from, "valid_to": valid_to})
            
    conn.commit()
    conn.close()
    return {"status": "success", "results": results}

# --- Deal Query & Price Finder Endpoint ---
@app.post("/api/groceries/query_deals")
def query_deals(req: DealQueryRequest, user_id: str = Depends(verify_auth)):
    try:
        refresh_user_expired_deals(user_id)
    except Exception as e:
        logger.warning(f"Error checking deal freshness in query_deals: {e}")

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
    try:
        refresh_user_expired_deals(user_id)
    except Exception as e:
        logger.warning(f"Error checking deal freshness in get_personalized_deals_feed: {e}")

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, ad_url, cached_deals, valid_from, valid_to FROM grocery_stores WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    s_row = c.fetchone()
    
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
            "valid_from": r["valid_from"],
            "valid_to": r["valid_to"],
            "deals": deals
        })
        for d in deals:
            all_raw_deals.append((r["name"], r["ad_url"], d, r["valid_from"], r["valid_to"]))
            
    scored_deals = []
    search_term = (search or '').strip().lower()
    cat_filter = (category or '').strip().lower()
    
    for store_name, store_ad_url, deal, v_from, v_to in all_raw_deals:
        item_name = deal.get("item", "").strip()
        if not item_name:
            continue
            
        item_lower = item_name.lower()
        deal_cat = deal.get("category", "Pantry & Dry Goods")
        deal_cat_lower = deal_cat.lower()
        price_str, notes_str = sanitize_deal_price_and_notes(deal.get("price", ""), deal.get("notes", ""))
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

        parsed_price = parse_numeric_price(price_str)
        curr_val = parsed_price.get('unit_price')
        curr_u = parsed_price.get('unit') or 'ea'
        beef_grade = detect_beef_grade(item_name, deal_cat)
        hist_metrics = get_item_price_history_metrics(conn, user_id, item_name, curr_val, deal_cat, curr_u)
        
        if hist_metrics and hist_metrics.get('badge_type') == 'all_time_low':
            score += 45
        elif hist_metrics and hist_metrics.get('badge_type') == 'below_avg':
            score += 20
        elif hist_metrics and hist_metrics.get('badge_type') == 'matching_low':
            score += 15
                
        scored_deals.append({
            "item": item_name,
            "store": store_name,
            "store_ad_url": store_ad_url,
            "valid_from": v_from,
            "valid_to": v_to,
            "price": price_str,
            "category": deal_cat,
            "notes": notes_str,
            "image_url": img_url,
            "score": score,
            "comparison": comp,
            "beef_grade": beef_grade,
            "price_history": hist_metrics,
            "matched_keywords": matched_liked
        })
        
    conn.close()
    scored_deals.sort(key=lambda d: d["score"], reverse=True)
    
    return {
        "status": "success",
        "total_available": len(all_raw_deals),
        "deals_count": len(scored_deals),
        "preferences": prefs,
        "deals": scored_deals[:150]
    }

# --- Grocery Price History Endpoint ---
@app.get("/api/groceries/price_history")
def get_grocery_price_history(item: str, category: Optional[str] = "", user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    norm_key, beef_grade = normalize_item_history_key(item, category or "")
    c = conn.cursor()
    c.execute('''SELECT id, item_name, store_name, price_str, unit_price, unit, beef_grade, category, recorded_at 
                 FROM grocery_price_history 
                 WHERE user_id=? AND normalized_key=? 
                 ORDER BY recorded_at DESC LIMIT 50''',
              (user_id, norm_key))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {
        "status": "success",
        "normalized_key": norm_key,
        "beef_grade": beef_grade,
        "history": rows
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
        
        p_clean, _ = sanitize_deal_price_and_notes(item.get("price_notes", ""), "")
        parsed = parse_numeric_price(p_clean)
        item["beef_grade"] = detect_beef_grade(item.get("item_name", ""), item.get("category", ""))
        item["price_history"] = get_item_price_history_metrics(
            conn, user_id,
            item.get("item_name", ""),
            parsed.get("unit_price"),
            item.get("category", ""),
            parsed.get("unit") or "ea"
        )
        
    conn.close()
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
    try:
        c = conn.cursor()
        c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
        s_row = c.fetchone()
        settings = json.loads(s_row['settings']) if s_row and s_row['settings'] else {}
        
        c.execute("SELECT name, ad_url, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
        stores = []
        deal_images = {}
        for r in c.fetchall():
            deals = []
            if r["cached_deals"]:
                try: deals = json.loads(r["cached_deals"])
                except Exception: deals = []
            stores.append({"name": r["name"], "deals": deals})
            for d in deals:
                d_item = (d.get("item") or "").lower().strip()
                d_img = d.get("image_url") or ""
                if d_item and d_img and d_item not in deal_images:
                    deal_images[d_item] = d_img
            
        items = ai_generate_grocery_list_items(req.prompt, stores, settings)
        
        list_id = req.list_id
        now = datetime.now().isoformat()
        if list_id:
            c.execute("SELECT id FROM grocery_lists WHERE id=? AND user_id=?", (list_id, user_id))
            if not c.fetchone():
                c.execute("INSERT INTO grocery_lists (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                          (list_id, user_id, req.list_title or "AI Generated List", now, now))
        else:
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
            
            # If no image was provided, find best match from cached store circular deals
            if not img and deal_images:
                toks = normalize_item_tokens(name)
                for d_name, d_img in deal_images.items():
                    d_toks = normalize_item_tokens(d_name)
                    if toks and d_toks and toks.intersection(d_toks) and len(toks.intersection(d_toks)) >= min(len(toks), 2):
                        img = d_img
                        item["image_url"] = img
                        break
                        
            c.execute("INSERT INTO grocery_list_items (id, list_id, user_id, item_name, store_name, price_notes, category, is_checked, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                      (item_id, list_id, user_id, name, store, price, cat, img))
                      
        c.execute("UPDATE grocery_lists SET updated_at=? WHERE id=? AND user_id=?", (now, list_id, user_id))
        conn.commit()
        return {"status": "success", "list_id": list_id, "items": items}
    finally:
        conn.close()




# =====================================================================
# SMART MEAL PLANNER ENGINE & ENDPOINTS
# Plans meals for the week & month, matches circular sales to recipes,
# tracks thumbs up/down user preferences, adds to calendar, and exports
# ingredients to grocery lists with the lowest price stores.
# =====================================================================

class MealPlanGenerateRequest(BaseModel):
    plan_type: str = "week" # "week" or "month"
    dietary_pref: Optional[str] = "All"
    servings: Optional[int] = 4
    start_date: Optional[str] = None
    custom_notes: Optional[str] = ""

class MealFeedbackRequest(BaseModel):
    feedback: str # "like", "dislike", "none"

class MealExportGroceryRequest(BaseModel):
    list_id: Optional[str] = None
    list_title: Optional[str] = None
    meal_ids: Optional[list[str]] = None

def find_best_store_for_ingredient(item_name: str, category: str, all_stores: list) -> dict:
    """
    Given an ingredient name, category, and list of store objects with cached circular deals,
    finds the supermarket offering the lowest unit price, deal price string, and product image.
    """
    clean_ing = (item_name or "").strip()
    ing_tokens = normalize_item_tokens(clean_ing)
    curr_grade = detect_beef_grade(clean_ing, category)
    
    matches = []
    for store in all_stores:
        s_name = store.get("name", "Store")
        deals = store.get("deals", [])
        for d in deals:
            d_name = d.get("item", "")
            d_cat = d.get("category", "")
            
            if curr_grade:
                d_grade = detect_beef_grade(d_name, d_cat)
                if d_grade and d_grade != curr_grade:
                    continue
                    
            d_tokens = normalize_item_tokens(d_name)
            if not ing_tokens or not d_tokens:
                continue
                
            overlap = ing_tokens.intersection(d_tokens)
            if len(overlap) >= min(2, len(ing_tokens)) and (len(overlap) / max(len(ing_tokens), 1)) >= 0.35:
                d_clean_price, _ = sanitize_deal_price_and_notes(d.get("price", ""), d.get("notes", ""))
                d_parsed = parse_numeric_price(d_clean_price)
                matches.append({
                    "store": s_name,
                    "item": d_name,
                    "price_str": d_clean_price,
                    "unit_price": d_parsed.get("unit_price"),
                    "unit": d_parsed.get("unit", "ea"),
                    "image_url": d.get("image_url", ""),
                    "overlap": len(overlap)
                })
                
    if not matches:
        return {
            "store": "Any",
            "price": "Regular shelf price",
            "on_sale": False,
            "image_url": "",
            "savings": ""
        }
        
    matches_with_price = [m for m in matches if m["unit_price"] is not None]
    if matches_with_price:
        best = min(matches_with_price, key=lambda m: m["unit_price"])
    else:
        best = max(matches, key=lambda m: m["overlap"])
        
    return {
        "store": best["store"],
        "price": best["price_str"],
        "on_sale": True,
        "image_url": best.get("image_url", ""),
        "savings": f"Sale at {best['store']}"
    }

# Note: DEFAULT_FAMILY_PROFILE is defined at top level for unified household sync across calendar and meals

def calculate_family_nutrition_needs(family_profile: dict) -> dict:
    """
    Computes portion multiplier, recommended batch food weight (protein, carbs, veggies),
    and target dinner calories/macros for the family based on member ages, genders, and appetites.
    """
    members = family_profile.get("members", []) if family_profile else []
    if not members:
        members = DEFAULT_FAMILY_PROFILE["members"]
        
    total_portion_ratio = 0.0
    adults = 0
    teens = 0
    kids = 0
    total_dinner_cals = 0
    
    for m in members:
        try:
            age = int(m.get("age", 25))
        except Exception:
            age = 25
        gender_raw = str(m.get("gender", "male")).lower()
        is_male = gender_raw in ["male", "m"]
        appetite = str(m.get("appetite", "moderate")).lower()
        
        # Portion ratio based on age & gender (USDA Dietary Reference Guidelines)
        if age >= 19:
            adults += 1
            base_ratio = 1.15 if is_male else 1.0
            base_cals = 700 if is_male else 550
        elif age >= 13:
            teens += 1
            base_ratio = 1.25 if is_male else 1.05
            base_cals = 750 if is_male else 600
        elif age >= 9:
            kids += 1
            base_ratio = 0.85
            base_cals = 500
        elif age >= 4:
            kids += 1
            base_ratio = 0.65
            base_cals = 400
        else:
            kids += 1
            base_ratio = 0.45
            base_cals = 300
            
        if appetite == "hearty":
            base_ratio *= 1.2
            base_cals = int(base_cals * 1.2)
        elif appetite == "light":
            base_ratio *= 0.85
            base_cals = int(base_cals * 0.85)
            
        total_portion_ratio += base_ratio
        total_dinner_cals += base_cals
        
    portion_multiplier = round(total_portion_ratio, 2)
    rec_protein_lbs = round(portion_multiplier * 0.48, 2)
    rec_produce_lbs = round(portion_multiplier * 0.35, 2)
    rec_starches_lbs = round(portion_multiplier * 0.28, 2)
    
    dinner_protein_g = int(rec_protein_lbs * 90)
    dinner_carbs_g = int(total_dinner_cals * 0.40 / 4)
    dinner_fat_g = int(total_dinner_cals * 0.30 / 9)
    dinner_fiber_g = int(total_dinner_cals * 0.014)
    
    label_parts = []
    if adults: label_parts.append(f"{adults} Adult{'s' if adults > 1 else ''}")
    if teens: label_parts.append(f"{teens} Teen{'s' if teens > 1 else ''}")
    if kids: label_parts.append(f"{kids} Kid{'s' if kids > 1 else ''}")
    summary_label = f"{len(members)} Family Members ({', '.join(label_parts)})"
    
    return {
        "total_members": len(members),
        "portion_multiplier": portion_multiplier,
        "recommended_protein_lbs": rec_protein_lbs,
        "recommended_produce_lbs": rec_produce_lbs,
        "recommended_starches_lbs": rec_starches_lbs,
        "target_dinner_calories": total_dinner_cals,
        "target_dinner_protein_g": dinner_protein_g,
        "target_dinner_carbs_g": dinner_carbs_g,
        "target_dinner_fat_g": dinner_fat_g,
        "target_dinner_fiber_g": dinner_fiber_g,
        "summary_label": summary_label
    }

MEAL_RECIPES_CATALOG = [
    {
        "id": "recipe-ny-strip",
        "title": "Pan-Seared NY Strip Steak with Garlic Butter Asparagus",
        "description": "Tender New York strip steaks seared in a cast-iron skillet with aromatic garlic-herb butter and roasted asparagus.",
        "cuisine": "American Steakhouse",
        "prep_time": "10 mins",
        "cook_time": "15 mins",
        "calories": 590,
        "protein_g": 48,
        "carbs_g": 12,
        "fat_g": 38,
        "fiber_g": 4,
        "effort_level": "standard",
        "bulk_category": "beef",
        "key_protein_keywords": ["strip", "steak", "beef", "ny strip"],
        "produce_keywords": ["asparagus", "garlic", "rosemary"],
        "dietary_tags": ["High Protein", "Low Carb", "All"],
        "base_cost": 18.50,
        "ingredients": [
            {"name": "New York Strip Steaks (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Fresh Asparagus (1 lb)", "category": "Produce", "suggested_unit": "lb"},
            {"name": "Fresh Garlic (1 bulb)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Unsalted Butter (2 tbsp)", "category": "Dairy & Eggs", "suggested_unit": "ea"},
            {"name": "Fresh Rosemary Sprigs", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Season strip steaks generously with coarse kosher salt and cracked black pepper.",
            "Heat cast iron skillet over high heat until smoking; add 1 tbsp neutral oil.",
            "Sear steaks for 3-4 minutes per side until deep mahogany crust forms.",
            "Lower heat, toss in butter, smashed garlic, and rosemary sprigs; baste continuously for 2 minutes.",
            "Toss asparagus in olive oil and roast in a 400°F oven for 10-12 minutes until tender-crisp. Rest steaks 5 minutes before serving."
        ]
    },
    {
        "id": "recipe-sirloin-guac",
        "title": "Carne Asada Sirloin Tacos with Fresh Guacamole",
        "description": "Citrus-marinated top sirloin grilled hot and sliced thin, served on warm corn tortillas with homemade avocado guacamole.",
        "cuisine": "Mexican Street Food",
        "prep_time": "20 mins",
        "cook_time": "12 mins",
        "calories": 520,
        "protein_g": 42,
        "carbs_g": 45,
        "fat_g": 22,
        "fiber_g": 8,
        "effort_level": "standard",
        "bulk_category": "beef",
        "key_protein_keywords": ["sirloin", "steak", "beef", "skirt", "fajita"],
        "produce_keywords": ["avocado", "lime", "cilantro", "onion"],
        "dietary_tags": ["Family Favorites", "High Protein", "All"],
        "base_cost": 16.00,
        "ingredients": [
            {"name": "Top Sirloin Steak (1.5 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Haas Avocados (3 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Limes (2 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Fresh Cilantro (1 bunch)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "White Corn Tortillas (1 pack)", "category": "Bakery", "suggested_unit": "ea"},
            {"name": "Yellow Onion (1 ct)", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Marinate sirloin with lime juice, minced garlic, cumin, salt, and olive oil for 20 minutes.",
            "Mash avocados with diced red onion, cilantro, lime juice, and salt for fresh guacamole.",
            "Sear steak over high heat for 4 minutes per side for medium-rare; rest 10 minutes then slice thinly against the grain.",
            "Warm corn tortillas on dry skillet until pliable.",
            "Assemble tacos with sliced steak, diced onions, cilantro, and generous spoonfuls of guacamole."
        ]
    },
    {
        "id": "recipe-chicken-piccata",
        "title": "Crispy Lemon Herb Chicken Piccata with Garlic Pasta",
        "description": "Pan-golden chicken breasts simmered in a bright lemon-butter caper sauce, served over garlic butter fettuccine.",
        "cuisine": "Italian Bistro",
        "prep_time": "15 mins",
        "cook_time": "20 mins",
        "calories": 540,
        "protein_g": 44,
        "carbs_g": 52,
        "fat_g": 16,
        "fiber_g": 3,
        "effort_level": "easy",
        "bulk_category": "chicken",
        "key_protein_keywords": ["chicken breast", "chicken", "poultry"],
        "produce_keywords": ["lemon", "garlic", "parsley"],
        "dietary_tags": ["Family Favorites", "Quick & Easy", "All"],
        "base_cost": 12.50,
        "ingredients": [
            {"name": "Boneless Skinless Chicken Breasts (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Fresh Lemons (2 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Fettuccine or Angel Hair Pasta (1 lb)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Capers in Brine (1 jar)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Fresh Italian Parsley", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Garlic (4 cloves)", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Cut chicken breasts in half horizontally into cutlets; dredge lightly in flour seasoned with salt and pepper.",
            "Cook pasta in salted boiling water until al dente.",
            "Heat olive oil and butter in a wide skillet; sear chicken cutlets 3-4 minutes per side until golden brown and cooked through; transfer to plate.",
            "Deglaze pan with chicken broth and lemon juice; stir in capers and butter to emulsify into a silky sauce.",
            "Toss cooked pasta with olive oil, garlic, and chopped parsley; top with chicken cutlets and spoon lemon caper sauce over top."
        ]
    },
    {
        "id": "recipe-salmon-teriyaki",
        "title": "Honey Teriyaki Glazed Atlantic Salmon with Sesame Broccoli",
        "description": "Pan-seared salmon fillets brushed with a savory-sweet honey teriyaki reduction, paired with tender steamed sesame broccoli.",
        "cuisine": "Asian Fusion",
        "prep_time": "10 mins",
        "cook_time": "15 mins",
        "calories": 560,
        "protein_g": 46,
        "carbs_g": 38,
        "fat_g": 24,
        "fiber_g": 5,
        "effort_level": "standard",
        "bulk_category": "seafood",
        "key_protein_keywords": ["salmon", "fish", "seafood"],
        "produce_keywords": ["broccoli", "ginger", "garlic", "green onion"],
        "dietary_tags": ["High Protein", "Mediterranean & Fresh", "All"],
        "base_cost": 17.00,
        "ingredients": [
            {"name": "Atlantic Salmon Fillets (1.5 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Fresh Broccoli Crowns (1.5 lbs)", "category": "Produce", "suggested_unit": "lb"},
            {"name": "Honey Teriyaki Sauce (1 bottle)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Jasmine Rice (2 cups)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Toasted Sesame Seeds & Green Onions", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Cook jasmine rice according to package instructions.",
            "Steam broccoli florets until bright green and tender-crisp; toss with sesame oil and a pinch of salt.",
            "Season salmon fillets with salt and pepper; sear skin-side down in a hot skillet with sesame oil for 4 minutes.",
            "Flip salmon, pour teriyaki sauce into skillet, and simmer for 3 minutes until glaze thickens and coats fish.",
            "Serve salmon over steamed rice and broccoli, garnished with sesame seeds and sliced scallions."
        ]
    },
    {
        "id": "recipe-bolognese-pasta",
        "title": "Classic Slow-Simmered Beef Bolognese with Garlic Toast",
        "description": "Hearty ground beef simmered with crushed tomatoes, garlic, Italian herbs, and a touch of cream over al dente rigatoni.",
        "cuisine": "Italian Classic",
        "prep_time": "15 mins",
        "cook_time": "30 mins",
        "calories": 610,
        "protein_g": 38,
        "carbs_g": 68,
        "fat_g": 22,
        "fiber_g": 5,
        "effort_level": "involved",
        "bulk_category": "ground_beef",
        "key_protein_keywords": ["ground beef", "beef", "meatball"],
        "produce_keywords": ["onion", "garlic", "basil", "parsley"],
        "dietary_tags": ["Family Favorites", "Budget Saver", "All"],
        "base_cost": 13.00,
        "ingredients": [
            {"name": "Lean Ground Beef 85/15 (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Crushed San Marzano Tomatoes (28 oz can)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Rigatoni or Penne Pasta (1 lb)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Grated Parmesan Cheese (4 oz)", "category": "Dairy & Eggs", "suggested_unit": "ea"},
            {"name": "Garlic (1 bulb)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Crusty French Baguette", "category": "Bakery", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Brown ground beef in a heavy Dutch oven, breaking it into small crumbles; drain excess fat.",
            "Add diced onions and minced garlic; cook until softened and fragrant.",
            "Pour in crushed tomatoes, Italian seasoning, a pinch of red pepper flakes, and salt; simmer on low for 25 minutes.",
            "Boil pasta in salted water until al dente; reserve 1/2 cup pasta cooking water.",
            "Toss pasta directly into bolognese sauce; serve hot with fresh grated parmesan and toasted garlic baguette slices."
        ]
    },
    {
        "id": "recipe-pork-chops",
        "title": "Tuscan Garlic Herb Seared Pork Chops with Sautéed Spinach",
        "description": "Thick-cut pork chops seared until caramelized with rosemary, garlic, and olive oil, served alongside fresh wilted garlic spinach.",
        "cuisine": "Italian Rustic",
        "prep_time": "10 mins",
        "cook_time": "18 mins",
        "calories": 480,
        "protein_g": 44,
        "carbs_g": 14,
        "fat_g": 28,
        "fiber_g": 4,
        "effort_level": "easy",
        "bulk_category": "pork",
        "key_protein_keywords": ["pork chop", "pork", "chops"],
        "produce_keywords": ["spinach", "garlic", "rosemary"],
        "dietary_tags": ["High Protein", "Low Carb", "Budget Saver", "All"],
        "base_cost": 11.50,
        "ingredients": [
            {"name": "Bone-in or Boneless Center Cut Pork Chops (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Fresh Baby Spinach (10 oz container)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Fresh Garlic (6 cloves)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Olive Oil (3 tbsp)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Fresh Rosemary & Thyme", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Rub pork chops with olive oil, minced rosemary, garlic powder, salt, and pepper.",
            "Heat a skillet over medium-high heat. Sear chops 4-5 minutes per side until internal temperature reaches 145°F.",
            "Remove chops to a warm cutting board and rest 5 minutes.",
            "In the same skillet, add a splash of olive oil and sliced garlic; toss in fresh baby spinach and cook 2 minutes until wilted.",
            "Serve pork chops atop the garlic spinach, drizzled with natural pan drippings."
        ]
    },
    {
        "id": "recipe-sheetpan-fajitas",
        "title": "Sizzling Sheet Pan Chicken Fajitas with Bell Peppers & Lime",
        "description": "Sliced chicken breast tossed with colorful bell peppers, sweet onions, and Mexican spices, roasted on a single sheet pan.",
        "cuisine": "Tex-Mex",
        "prep_time": "15 mins",
        "cook_time": "20 mins",
        "calories": 490,
        "protein_g": 42,
        "carbs_g": 48,
        "fat_g": 15,
        "fiber_g": 7,
        "effort_level": "easy",
        "bulk_category": "chicken",
        "key_protein_keywords": ["chicken breast", "chicken", "fajita"],
        "produce_keywords": ["bell pepper", "onion", "lime", "cilantro"],
        "dietary_tags": ["Family Favorites", "Quick & Easy", "All"],
        "base_cost": 12.00,
        "ingredients": [
            {"name": "Boneless Skinless Chicken Breasts (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Tri-Color Bell Peppers (3 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Red and Yellow Onions (2 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Fajita Seasoning & Lime", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Flour Tortillas (1 pack)", "category": "Bakery", "suggested_unit": "ea"},
            {"name": "Sour Cream & Salsa", "category": "Dairy & Eggs", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Slice chicken breasts, bell peppers, and onions into uniform strips.",
            "Spread evenly across a large baking sheet; toss with 2 tbsp olive oil and fajita seasoning blend.",
            "Bake at 425°F for 18-20 minutes until chicken is cooked through and peppers have charred edges.",
            "Squeeze fresh lime juice generously over the hot baking sheet.",
            "Serve family-style with warm flour tortillas, cool sour cream, and salsa."
        ]
    },
    {
        "id": "recipe-pork-tenderloin",
        "title": "Balsamic Honey Roasted Pork Tenderloin with Green Beans",
        "description": "Succulent pork tenderloin roasted with a glossy balsamic-honey glaze and crisp roasted green beans.",
        "cuisine": "French Bistro",
        "prep_time": "10 mins",
        "cook_time": "25 mins",
        "calories": 440,
        "protein_g": 45,
        "carbs_g": 22,
        "fat_g": 18,
        "fiber_g": 5,
        "effort_level": "standard",
        "bulk_category": "pork",
        "key_protein_keywords": ["pork tenderloin", "pork"],
        "produce_keywords": ["green beans", "garlic", "shallot"],
        "dietary_tags": ["High Protein", "Budget Saver", "All"],
        "base_cost": 13.00,
        "ingredients": [
            {"name": "Pork Tenderloin (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Fresh Green Beans (1.5 lbs)", "category": "Produce", "suggested_unit": "lb"},
            {"name": "Balsamic Vinegar & Honey Glaze", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Garlic (4 cloves)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Dijon Mustard (1 tbsp)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Whisk balsamic vinegar, honey, Dijon mustard, minced garlic, and salt for the glaze.",
            "Sear pork tenderloin in an oven-safe skillet on all sides for 5 minutes total.",
            "Toss green beans around the pork in the skillet with olive oil, salt, and pepper.",
            "Brush glaze generously over pork; roast at 400°F for 18 minutes until 145°F internal temperature.",
            "Rest tenderloin 8 minutes before slicing into medallions; serve alongside roasted green beans."
        ]
    },
    {
        "id": "recipe-chuck-roast",
        "title": "Tender Prime Beef Chuck Pot Roast with Carrots & Potatoes",
        "description": "Melt-in-your-mouth beef chuck roast braised low and slow with sweet carrots, baby red potatoes, and rich beef gravy.",
        "cuisine": "American Comfort",
        "prep_time": "20 mins",
        "cook_time": "3 hrs",
        "calories": 620,
        "protein_g": 52,
        "carbs_g": 32,
        "fat_g": 31,
        "fiber_g": 6,
        "effort_level": "involved",
        "bulk_category": "beef",
        "key_protein_keywords": ["chuck roast", "beef", "pot roast"],
        "produce_keywords": ["carrots", "potatoes", "onion", "celery"],
        "dietary_tags": ["Family Favorites", "Comfort Food", "All"],
        "base_cost": 17.50,
        "ingredients": [
            {"name": "USDA Prime or Choice Beef Chuck Roast (3 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Baby Red or Yukon Gold Potatoes (1.5 lbs)", "category": "Produce", "suggested_unit": "lb"},
            {"name": "Whole Carrots (1 lb bag)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Yellow Onion (1 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Beef Broth & Tomato Paste", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Fresh Thyme & Bay Leaves", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Pat chuck roast dry and season liberally with salt, pepper, and garlic powder.",
            "Sear roast on all sides in a hot Dutch oven until a deep brown crust develops; remove to plate.",
            "Sauté chopped onions, tomato paste, and garlic in the pot; deglaze with beef broth.",
            "Return roast to pot; cover tightly and braise at 300°F for 2 hours.",
            "Add halved baby potatoes and carrot chunks; return to oven for another 45-60 minutes until fork-tender."
        ]
    },
    {
        "id": "recipe-shrimp-scampi",
        "title": "Garlic Butter Shrimp Scampi with Linguine & Fresh Lemon",
        "description": "Succulent shrimp tossed in white wine, butter, roasted garlic, and crushed red pepper flakes over ribbons of linguine.",
        "cuisine": "Italian Seafood",
        "prep_time": "10 mins",
        "cook_time": "12 mins",
        "calories": 510,
        "protein_g": 36,
        "carbs_g": 54,
        "fat_g": 17,
        "fiber_g": 3,
        "effort_level": "easy",
        "bulk_category": "seafood",
        "key_protein_keywords": ["shrimp", "seafood"],
        "produce_keywords": ["garlic", "lemon", "parsley"],
        "dietary_tags": ["Quick & Easy", "Mediterranean & Fresh", "All"],
        "base_cost": 15.00,
        "ingredients": [
            {"name": "Raw Peeled & Deveined Shrimp (1.5 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Linguine Pasta (1 lb box)", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Butter (4 tbsp) & Olive Oil", "category": "Dairy & Eggs", "suggested_unit": "ea"},
            {"name": "Fresh Garlic (6 cloves, minced)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Fresh Lemon & Italian Parsley", "category": "Produce", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Cook linguine in salted boiling water until al dente; reserve 1/2 cup pasta cooking water.",
            "Melt 2 tbsp butter and 2 tbsp olive oil in a large skillet over medium-high heat.",
            "Add minced garlic and red pepper flakes; cook for 1 minute until fragrant.",
            "Add shrimp in a single layer; cook 2 minutes per side until pink and opaque.",
            "Stir in remaining butter, lemon juice, and chopped parsley; toss pasta into sauce with a splash of pasta water."
        ]
    },
    {
        "id": "recipe-mediterranean-chicken",
        "title": "Greek Lemon Herb Chicken with Cucumber Feta Salad",
        "description": "Marinated grilled chicken breasts paired with crisp English cucumbers, heirloom cherry tomatoes, kalamata olives, and feta.",
        "cuisine": "Mediterranean",
        "prep_time": "15 mins",
        "cook_time": "15 mins",
        "calories": 460,
        "protein_g": 46,
        "carbs_g": 24,
        "fat_g": 20,
        "fiber_g": 6,
        "effort_level": "easy",
        "bulk_category": "chicken",
        "key_protein_keywords": ["chicken breast", "chicken"],
        "produce_keywords": ["cucumber", "tomato", "lemon", "feta", "olive"],
        "dietary_tags": ["Low Carb", "Mediterranean & Fresh", "All"],
        "base_cost": 14.00,
        "ingredients": [
            {"name": "Boneless Skinless Chicken Breasts (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "English Cucumbers (2 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Cherry or Grape Tomatoes (1 pint)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Crumbled Feta Cheese (6 oz)", "category": "Dairy & Eggs", "suggested_unit": "ea"},
            {"name": "Kalamata Olives & Extra Virgin Olive Oil", "category": "Pantry & Dry Goods", "suggested_unit": "ea"},
            {"name": "Dried Oregano & Lemon", "category": "Pantry & Dry Goods", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Marinate chicken with olive oil, lemon juice, oregano, garlic, salt, and pepper for 15 minutes.",
            "Chop cucumbers and halve tomatoes; toss in a bowl with kalamata olives, crumbled feta, olive oil, and oregano.",
            "Grill or sear chicken on medium-high heat for 6-7 minutes per side until cooked through (165°F).",
            "Rest chicken 5 minutes, then slice diagonally.",
            "Serve sliced chicken alongside refreshing chilled Greek salad with a wedge of lemon."
        ]
    },
    {
        "id": "recipe-smash-burgers",
        "title": "Double Cheddar Smash Burgers with Sweet Potato Wedges",
        "description": "Crispy lace-edged beef patties topped with melted sharp cheddar, caramelized onions, and secret burger sauce on brioche.",
        "cuisine": "American Comfort",
        "prep_time": "15 mins",
        "cook_time": "15 mins",
        "calories": 680,
        "protein_g": 44,
        "carbs_g": 56,
        "fat_g": 32,
        "fiber_g": 5,
        "effort_level": "easy",
        "bulk_category": "ground_beef",
        "key_protein_keywords": ["ground beef", "beef", "patty"],
        "produce_keywords": ["sweet potato", "onion", "lettuce", "pickle"],
        "dietary_tags": ["Family Favorites", "Budget Saver", "All"],
        "base_cost": 14.50,
        "ingredients": [
            {"name": "Ground Beef 80/20 (2 lbs)", "category": "Meat & Seafood", "suggested_unit": "lb"},
            {"name": "Sharp Cheddar Cheese Slices (8 ct)", "category": "Dairy & Eggs", "suggested_unit": "ea"},
            {"name": "Brioche Hamburger Buns (4 pack)", "category": "Bakery", "suggested_unit": "ea"},
            {"name": "Sweet Potatoes (2 lbs)", "category": "Produce", "suggested_unit": "lb"},
            {"name": "Yellow Onion (1 ct)", "category": "Produce", "suggested_unit": "ea"},
            {"name": "Pickles & Burger Sauce", "category": "Pantry & Dry Goods", "suggested_unit": "ea"}
        ],
        "instructions": [
            "Cut sweet potatoes into wedges; toss with olive oil, paprika, and salt; roast at 425°F for 25 minutes.",
            "Thinly slice onion and caramelize in a skillet with butter until golden brown.",
            "Divide ground beef into 8 loose meatballs; heat a cast-iron skillet screaming hot.",
            "Press meatballs firmly with a heavy spatula onto dry hot skillet; season heavily with salt and pepper.",
            "Flip after 2 minutes of hard searing; immediately top each patty with cheddar; assemble double burgers on toasted brioche."
        ]
    }
]

DEFAULT_DAY_RULES = {
    "Sunday": {
        "mode": "no_meal",
        "effort": "easy",
        "name": "Sunday Dinner with Family",
        "notes": "Weekly dinner with extended family — no home cooking or meal prep needed."
    },
    "Monday": {
        "mode": "cook",
        "effort": "easy",
        "name": "",
        "notes": "Quick & easy dinner (< 25 min)."
    },
    "Tuesday": {
        "mode": "cook",
        "effort": "easy",
        "name": "",
        "notes": "Busy weeknight — quick skillet or sheet pan."
    },
    "Wednesday": {
        "mode": "cook",
        "effort": "standard",
        "name": "",
        "notes": "Midweek standard cooking (30-40 min)."
    },
    "Thursday": {
        "mode": "cook",
        "effort": "easy",
        "name": "",
        "notes": "Almost Friday — quick prep dinner."
    },
    "Friday": {
        "mode": "themed",
        "effort": "easy",
        "name": "Friday Family Pizza Night",
        "notes": "Pick up favorite frozen pizzas and extra toppings to bake together at home.",
        "recipe_title": "Friday Family Pizza Night (Frozen Pizzas & Extra Toppings)",
        "cuisine": "Family Pizza Night",
        "prep_time": "5 mins",
        "cook_time": "18 mins",
        "calories": 650,
        "protein_g": 32,
        "carbs_g": 72,
        "fat_g": 26,
        "fiber_g": 4,
        "effort_level": "easy",
        "bulk_category": "frozen_pizza",
        "base_cost": 12.00,
        "ingredients": [
            {"name": "Frozen Pizzas (DiGiorno, Freschetta, or Red Baron - 2 ct)", "category": "Frozen"},
            {"name": "Shredded Mozzarella Cheese (8 oz)", "category": "Dairy & Eggs"},
            {"name": "Sliced Pepperoni (5 oz pack)", "category": "Meat & Seafood"},
            {"name": "Fresh Bell Pepper or Toppings", "category": "Produce"}
        ],
        "instructions": [
            "Preheat oven to 425°F (or per frozen pizza package instructions).",
            "Unwrap frozen pizzas and place on baking sheets or pizza stone.",
            "Layer generously with extra shredded mozzarella cheese, pepperoni slices, and desired veggie toppings.",
            "Bake 15-18 minutes until the crust is crisp-golden and cheese is melted and bubbling.",
            "Let rest 3 minutes, slice into wedges, and enjoy family pizza night!"
        ]
    },
    "Saturday": {
        "mode": "cook",
        "effort": "involved",
        "name": "",
        "notes": "Weekend cooking — more time for gourmet or slow simmer."
    }
}

BULK_INGREDIENT_SYNERGY = {
    "chicken": {
        "title": "5 lb Family Pack Chicken Breasts",
        "savings": "~$6.00",
        "note": "Shared with {other_day} ({other_title}) — buy in bulk to keep costs down"
    },
    "ground_beef": {
        "title": "5 lb Value Pack Ground Beef (80/20 or 85/15)",
        "savings": "~$5.50",
        "note": "Shared with {other_day} ({other_title}) — buy in bulk to keep costs down"
    },
    "pork": {
        "title": "Family Pack Pork Cuts",
        "savings": "~$4.50",
        "note": "Shared with {other_day} ({other_title}) — buy in bulk to keep costs down"
    },
    "beef": {
        "title": "USDA Beef Value Pack",
        "savings": "~$5.00",
        "note": "Shared with {other_day} ({other_title}) — buy in bulk to keep costs down"
    },
    "potatoes": {
        "title": "5 lb Value Sack Potatoes",
        "savings": "~$2.50",
        "note": "Shared with {other_day} ({other_title}) — buy in bulk to keep costs down"
    }
}

def build_themed_pizza_night_meal(date_str: str, day_name: str, week_num: int, servings: int, rule: dict, all_stores: list) -> dict:
    pizza_title = rule.get("name") or "Friday Family Pizza Night"
    pizza_desc = rule.get("notes") or "Pick up favorite frozen pizzas and extra toppings to bake together at home."
    cuisine = rule.get("cuisine", "Family Pizza Night")
    prep_time = rule.get("prep_time", "5 mins")
    cook_time = rule.get("cook_time", "18 mins")
    calories = rule.get("calories", 650)
    instructions = rule.get("instructions", [
        "Preheat oven to 425°F (or per frozen pizza package instructions).",
        "Unwrap frozen pizzas and place on baking sheets or pizza stone.",
        "Layer generously with extra shredded mozzarella cheese, pepperoni slices, and desired veggie toppings.",
        "Bake 15-18 minutes until the crust is crisp-golden and cheese is melted and bubbling.",
        "Let rest 3 minutes, slice into wedges, and enjoy family pizza night!"
    ])
    
    target_items = [
        {"name": "Frozen Pizzas (DiGiorno, Freschetta, or Red Baron - 2 ct)", "search_term": "pizza", "category": "Frozen", "base_cost": 8.00},
        {"name": "Shredded Mozzarella Cheese (8 oz)", "search_term": "mozzarella cheese", "category": "Dairy & Eggs", "base_cost": 2.50},
        {"name": "Sliced Pepperoni (5 oz pack)", "search_term": "pepperoni", "category": "Meat & Seafood", "base_cost": 2.50},
        {"name": "Fresh Bell Pepper or Toppings", "search_term": "bell pepper", "category": "Produce", "base_cost": 1.50}
    ]
    
    ingredients = []
    sale_highlights = []
    meal_cost = 0.0
    meal_savings = 0.0
    
    servings_factor = max(servings, 1) / 4.0
    
    for item in target_items:
        best_match = find_best_store_for_ingredient(item["search_term"], item["category"], all_stores)
        ing_cost = round(item["base_cost"] * (servings_factor if "pizza" in item["search_term"] or "pepperoni" in item["search_term"] else 1.0), 2)
        if best_match["on_sale"]:
            sale_saving = round(ing_cost * 0.30, 2)
            meal_savings += sale_saving
            ing_cost -= sale_saving
            sale_highlights.append({
                "item": item["name"].split("(")[0].strip(),
                "store": best_match["store"],
                "price": best_match["price"],
                "savings": f"Save ${sale_saving:.2f} at {best_match['store']}"
            })
            
        meal_cost += ing_cost
        ingredients.append({
            "name": item["name"],
            "category": item["category"],
            "store": best_match["store"],
            "price": best_match["price"],
            "on_sale": best_match["on_sale"],
            "image_url": best_match.get("image_url", ""),
            "savings": best_match.get("savings", "")
        })
        
    meal_cost_serv = meal_cost / max(servings, 1)
    
    return {
        "id": str(uuid.uuid4()),
        "recipe_id": "routine-friday-pizza",
        "day": day_name,
        "date": date_str,
        "week_num": week_num,
        "meal_type": "Dinner",
        "title": pizza_title,
        "description": pizza_desc,
        "cuisine": cuisine,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "servings": servings,
        "calories": calories,
        "protein_g": 32,
        "carbs_g": 72,
        "fat_g": 26,
        "fiber_g": 4,
        "effort_level": "easy",
        "effort_label": "⚡ Quick & Easy (18 min)",
        "macros": {
            "calories": calories,
            "protein_g": 32,
            "carbs_g": 72,
            "fat_g": 26,
            "fiber_g": 4
        },
        "family_macros": {
            "calories": calories * servings,
            "protein_g": 32 * servings,
            "carbs_g": 72 * servings,
            "fat_g": 26 * servings,
            "fiber_g": 4 * servings
        },
        "family_portion_guide": f"Family Pizza Night for {servings}: 2-3 pizzas with extra mozzarella & toppings",
        "bulk_reuse": {"is_bulk": False},
        "key_protein": "pepperoni / cheese",
        "estimated_cost": f"${meal_cost:.2f}",
        "estimated_cost_per_serving": f"${meal_cost_serv:.2f}",
        "sale_highlights": sale_highlights,
        "ingredients": ingredients,
        "instructions": instructions,
        "feedback": None,
        "calendar_synced": False,
        "calendar_event_id": None,
        "is_themed_routine": True,
        "theme_type": "pizza",
        "is_no_meal_needed": False,
        "is_calendar_reserved": False,
        "_cost_num": meal_cost,
        "_savings_num": meal_savings
    }

def build_no_meal_needed_day(date_str: str, day_name: str, week_num: int, servings: int, rule: dict) -> dict:
    title = rule.get("name") or f"{day_name} Dinner with Family"
    desc = rule.get("notes") or "Weekly dinner with extended family — no home cooking or meal prep needed."
    return {
        "id": str(uuid.uuid4()),
        "recipe_id": f"no-meal-{day_name.lower()}",
        "day": day_name,
        "date": date_str,
        "week_num": week_num,
        "meal_type": "Dinner",
        "title": title,
        "description": desc,
        "cuisine": "Family Gathering",
        "prep_time": "0 min",
        "cook_time": "0 min",
        "servings": servings,
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "fiber_g": 0,
        "effort_level": "easy",
        "effort_label": "👨‍👩‍👧 Family Gathering",
        "macros": {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "fiber_g": 0
        },
        "family_macros": {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "fiber_g": 0
        },
        "family_portion_guide": "Weekly family gathering — no home cooking required",
        "bulk_reuse": {"is_bulk": False},
        "key_protein": "none",
        "estimated_cost": "$0.00",
        "estimated_cost_per_serving": "$0.00",
        "sale_highlights": [],
        "ingredients": [],
        "instructions": ["Spend quality time with family. No grocery shopping or home cooking required today!"],
        "feedback": None,
        "calendar_synced": False,
        "calendar_event_id": None,
        "is_no_meal_needed": True,
        "is_themed_routine": False,
        "is_calendar_reserved": False,
        "_cost_num": 0.0,
        "_savings_num": 0.0
    }

def build_calendar_reserved_meal(date_str: str, day_name: str, week_num: int, servings: int, existing_title: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "recipe_id": "calendar-reserved",
        "day": day_name,
        "date": date_str,
        "week_num": week_num,
        "meal_type": "Dinner",
        "title": f"📅 Scheduled: {existing_title}",
        "description": f"Pre-scheduled meal already found on your calendar: '{existing_title}'. No duplicate dinner planned.",
        "cuisine": "Scheduled Event",
        "prep_time": "0 min",
        "cook_time": "0 min",
        "servings": servings,
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "fiber_g": 0,
        "effort_level": "easy",
        "effort_label": "📅 Pre-Scheduled",
        "macros": {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "fiber_g": 0
        },
        "family_macros": {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "fiber_g": 0
        },
        "family_portion_guide": f"Pre-scheduled event: '{existing_title}'",
        "bulk_reuse": {"is_bulk": False},
        "key_protein": "calendar",
        "estimated_cost": "$0.00",
        "estimated_cost_per_serving": "$0.00",
        "sale_highlights": [],
        "ingredients": [],
        "instructions": [f"Enjoy your pre-scheduled meal: '{existing_title}'!"],
        "feedback": None,
        "calendar_synced": True,
        "calendar_event_id": None,
        "is_no_meal_needed": False,
        "is_themed_routine": False,
        "is_calendar_reserved": True,
        "_cost_num": 0.0,
        "_savings_num": 0.0
    }

def generate_smart_meal_plan(
    user_id: str,
    plan_type: str = "week",
    dietary_pref: str = "All",
    servings: int = 5,
    start_date_str: str = None,
    custom_notes: str = "",
    all_stores: list = None,
    user_prefs: dict = None,
    conn: sqlite3.Connection = None,
    service = None
) -> dict:
    if not all_stores:
        all_stores = []
    if not user_prefs:
        user_prefs = {
            "liked_cuisines": [],
            "disliked_cuisines": [],
            "liked_ingredients": [],
            "disliked_ingredients": [],
            "liked_meals": [],
            "disliked_meals": []
        }
        
    days_count = 28 if plan_type == "month" else 7
    
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str[:10], "%Y-%m-%d")
        except Exception:
            start_dt = datetime.now()
    else:
        now = datetime.now()
        days_ahead = (0 - now.weekday()) % 7
        if days_ahead == 0 and now.hour < 14:
            start_dt = now
        elif days_ahead == 0:
            start_dt = now + timedelta(days=7)
        else:
            start_dt = now + timedelta(days=days_ahead)
            
    end_dt = start_dt + timedelta(days=days_count - 1)
    
    sale_proteins = set()
    sale_produce = set()
    for s in all_stores:
        for d in s.get("deals", []):
            item_name = (d.get("item") or "").lower()
            toks = normalize_item_tokens(item_name)
            cat = (d.get("category") or "").lower()
            if "meat" in cat or "seafood" in cat:
                sale_proteins.update(toks)
            elif "produce" in cat:
                sale_produce.update(toks)
                
    disliked_c = set(c.lower() for c in user_prefs.get("disliked_cuisines", []))
    liked_c = set(c.lower() for c in user_prefs.get("liked_cuisines", []))
    disliked_i = set(i.lower() for i in user_prefs.get("disliked_ingredients", []))
    liked_i = set(i.lower() for i in user_prefs.get("liked_ingredients", []))
    disliked_m = set(m.lower() for m in user_prefs.get("disliked_meals", []))
    
    base_scored_recipes = []
    for r in MEAL_RECIPES_CATALOG:
        title_low = r["title"].lower()
        if any(dm in title_low for dm in disliked_m):
            continue
        cuis_low = r["cuisine"].lower()
        if any(dc in cuis_low for dc in disliked_c):
            continue
            
        score = 10
        for pk in r["key_protein_keywords"]:
            if any(stem in pk for stem in sale_proteins):
                score += 15
                break
        for prk in r["produce_keywords"]:
            if any(stem in prk for stem in sale_produce):
                score += 5
                break
        if any(lc in cuis_low for lc in liked_c):
            score += 12
        for ing in r["ingredients"]:
            ing_low = ing["name"].lower()
            if any(li in ing_low for li in liked_i):
                score += 8
            if any(di in ing_low for di in disliked_i):
                score -= 20
                
        if dietary_pref and dietary_pref != "All":
            tags = [t.lower() for t in r.get("dietary_tags", [])]
            pref_low = dietary_pref.lower()
            if any(pref_low in t or t in pref_low for t in tags):
                score += 25
                
        base_scored_recipes.append((score, r))
        
    meals = []
    total_cost = 0.0
    total_savings = 0.0
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_rules = user_prefs.get("day_rules", DEFAULT_DAY_RULES) if user_prefs else DEFAULT_DAY_RULES
    if not isinstance(day_rules, dict):
        day_rules = DEFAULT_DAY_RULES
        
    # Bulk ingredient reuse tracker: category -> (meal_idx, day_name, meal_title)
    bulk_first_meal = {}
    bulk_category_counts = {}
    
    servings_factor = max(servings, 1) / 4.0
    rec_protein_lbs = round(servings * 0.48, 1)
    rec_sides_lbs = round(servings * 0.32, 1)
    
    for i in range(days_count):
        cur_date = start_dt + timedelta(days=i)
        date_str = cur_date.strftime("%Y-%m-%d")
        day_name = day_names[cur_date.weekday()]
        week_num = (i // 7) + 1
        
        # 1. Check if calendar already has a meal / dinner event on this date
        calendar_meal = find_existing_meal_or_food_on_calendar(user_id, date_str, service=service, conn=conn)
        if calendar_meal:
            existing_title = calendar_meal.get("title") or calendar_meal.get("event", {}).get("title", "Scheduled Dinner")
            logger.info(f"Meal plan generator: Found existing calendar meal '{existing_title}' on {date_str}. Reserving day.")
            m_obj = build_calendar_reserved_meal(date_str, day_name, week_num, servings, existing_title)
            m_obj.pop("_cost_num", None)
            m_obj.pop("_savings_num", None)
            meals.append(m_obj)
            continue
            
        # 2. Check Day-of-Week Routine Rules
        rule = day_rules.get(day_name, {"mode": "cook", "effort": "standard"})
        rule_mode = rule.get("mode", "cook")
        rule_effort = rule.get("effort", "standard")
        
        if rule_mode == "no_meal":
            logger.info(f"Meal plan generator: Day rule for {day_name} is no_meal ({rule.get('name')}).")
            m_obj = build_no_meal_needed_day(date_str, day_name, week_num, servings, rule)
            m_obj.pop("_cost_num", None)
            m_obj.pop("_savings_num", None)
            meals.append(m_obj)
            continue
            
        if rule_mode == "themed":
            logger.info(f"Meal plan generator: Day rule for {day_name} is themed ({rule.get('name')}).")
            m_obj = build_themed_pizza_night_meal(date_str, day_name, week_num, servings, rule, all_stores)
            total_cost += m_obj.pop("_cost_num", 0.0)
            total_savings += m_obj.pop("_savings_num", 0.0)
            meals.append(m_obj)
            continue
        
        # Score recipes specifically for this day taking into account requested effort and bulk synergy
        day_candidates = []
        for b_score, r in base_scored_recipes:
            cur_score = b_score
            r_effort = r.get("effort_level", "standard")
            if r_effort == rule_effort:
                cur_score += 35
            elif rule_effort == "easy" and r_effort == "involved":
                cur_score -= 40
            elif rule_effort == "involved" and r_effort == "easy":
                cur_score -= 15
                
            # Bulk synergy boost: if a recipe shares a bulk category used in the week, promote it!
            b_cat = r.get("bulk_category")
            if b_cat and b_cat in bulk_category_counts and bulk_category_counts[b_cat] == 1:
                cur_score += 25
                
            day_candidates.append((cur_score, r))
            
        day_candidates.sort(key=lambda x: x[0], reverse=True)
        candidate_recipes = [x[1] for x in day_candidates] if day_candidates else MEAL_RECIPES_CATALOG
        
        prev_protein = meals[-1]["key_protein"] if meals else None
        selected_recipe = None
        for cand in candidate_recipes:
            cand_id = cand["id"]
            if any(m["recipe_id"] == cand_id for m in meals[-min(len(meals), 6):]):
                continue
            cand_protein = cand["key_protein_keywords"][0] if cand["key_protein_keywords"] else ""
            if prev_protein and cand_protein == prev_protein and len(candidate_recipes) > 2:
                continue
            selected_recipe = cand
            break
            
        if not selected_recipe:
            selected_recipe = candidate_recipes[i % len(candidate_recipes)]
            
        meal_ingredients = []
        sale_highlights = []
        meal_cost = 0.0
        meal_savings = 0.0
        
        for base_ing in selected_recipe["ingredients"]:
            ing_name = base_ing["name"]
            ing_cat = base_ing["category"]
            
            # Scale quantity label for 5+ family members
            if servings >= 5:
                if "(2 lbs)" in ing_name:
                    ing_name = ing_name.replace("(2 lbs)", f"({round(2.0 * servings_factor, 1)} lbs)")
                elif "(1.5 lbs)" in ing_name:
                    ing_name = ing_name.replace("(1.5 lbs)", f"({round(1.5 * servings_factor, 1)} lbs)")
                elif "(3 lbs)" in ing_name:
                    ing_name = ing_name.replace("(3 lbs)", f"({round(3.0 * servings_factor, 1)} lbs)")
                elif "(1 lb)" in ing_name:
                    ing_name = ing_name.replace("(1 lb)", f"({round(1.0 * servings_factor, 1)} lbs)")
                    
            best_match = find_best_store_for_ingredient(ing_name, ing_cat, all_stores)
            
            base_cost = 3.50
            if "strip" in ing_name.lower() or "steak" in ing_name.lower() or "salmon" in ing_name.lower() or "shrimp" in ing_name.lower():
                base_cost = 8.50
            elif "chicken" in ing_name.lower() or "beef" in ing_name.lower() or "pork" in ing_name.lower():
                base_cost = 5.50
            elif "produce" in ing_cat.lower():
                base_cost = 2.00
            elif "dairy" in ing_cat.lower():
                base_cost = 2.50
            else:
                base_cost = 1.75
                
            ing_cost = round(base_cost * servings_factor, 2)
            if best_match["on_sale"]:
                sale_saving = round(ing_cost * 0.35, 2)
                meal_savings += sale_saving
                ing_cost -= sale_saving
                sale_highlights.append({
                    "item": ing_name.split("(")[0].strip(),
                    "store": best_match["store"],
                    "price": best_match["price"],
                    "savings": f"Save ${sale_saving:.2f} at {best_match['store']}"
                })
                
            meal_cost += ing_cost
            meal_ingredients.append({
                "name": ing_name,
                "category": ing_cat,
                "store": best_match["store"],
                "price": best_match["price"],
                "on_sale": best_match["on_sale"],
                "image_url": best_match.get("image_url", ""),
                "savings": best_match.get("savings", "")
            })
            
        meal_cost_serv = meal_cost / max(servings, 1)
        total_cost += meal_cost
        total_savings += meal_savings
        
        # Check bulk ingredient reuse synergy
        r_bulk = selected_recipe.get("bulk_category")
        meal_bulk_info = {"is_bulk": False}
        
        if r_bulk and r_bulk in bulk_first_meal:
            prev_info = bulk_first_meal[r_bulk]
            spec = BULK_INGREDIENT_SYNERGY.get(r_bulk, {})
            if spec:
                meal_bulk_info = {
                    "is_bulk": True,
                    "bulk_title": spec["title"],
                    "bulk_savings": spec["savings"],
                    "paired_day": prev_info["day"],
                    "paired_meal": prev_info["title"],
                    "bulk_note": spec["note"].format(other_day=prev_info["day"], other_title=prev_info["title"])
                }
                # Also cross-link earlier meal
                prev_idx = prev_info["index"]
                if prev_idx < len(meals):
                    meals[prev_idx]["bulk_reuse"] = {
                        "is_bulk": True,
                        "bulk_title": spec["title"],
                        "bulk_savings": spec["savings"],
                        "paired_day": day_name,
                        "paired_meal": selected_recipe["title"],
                        "bulk_note": spec["note"].format(other_day=day_name, other_title=selected_recipe["title"])
                    }
            bulk_category_counts[r_bulk] = bulk_category_counts.get(r_bulk, 0) + 1
        elif r_bulk:
            bulk_first_meal[r_bulk] = {
                "index": len(meals),
                "day": day_name,
                "title": selected_recipe["title"]
            }
            bulk_category_counts[r_bulk] = 1
        
        cals = selected_recipe.get("calories", 550)
        prot = selected_recipe.get("protein_g", 42)
        crbs = selected_recipe.get("carbs_g", 45)
        fat = selected_recipe.get("fat_g", 20)
        fib = selected_recipe.get("fiber_g", 5)
        r_effort = selected_recipe.get("effort_level", "standard")
        effort_lbl = "⚡ Quick & Easy" if r_effort == "easy" else ("👨‍🍳 More Involved" if r_effort == "involved" else "🍳 Standard")
        
        meal_obj = {
            "id": str(uuid.uuid4()),
            "recipe_id": selected_recipe["id"],
            "day": day_name,
            "date": date_str,
            "week_num": week_num,
            "meal_type": "Dinner",
            "title": selected_recipe["title"],
            "description": selected_recipe["description"],
            "cuisine": selected_recipe["cuisine"],
            "prep_time": selected_recipe["prep_time"],
            "cook_time": selected_recipe["cook_time"],
            "servings": servings,
            "calories": cals,
            "protein_g": prot,
            "carbs_g": crbs,
            "fat_g": fat,
            "fiber_g": fib,
            "effort_level": r_effort,
            "effort_label": f"{effort_lbl} ({selected_recipe['prep_time']} prep)",
            "macros": {
                "calories": cals,
                "protein_g": prot,
                "carbs_g": crbs,
                "fat_g": fat,
                "fiber_g": fib
            },
            "family_macros": {
                "calories": cals * servings,
                "protein_g": prot * servings,
                "carbs_g": crbs * servings,
                "fat_g": fat * servings,
                "fiber_g": fib * servings
            },
            "family_portion_guide": f"Scaled for your family of {servings}: ~{rec_protein_lbs} lbs protein, ~{rec_sides_lbs} lbs produce/sides",
            "bulk_reuse": meal_bulk_info,
            "key_protein": selected_recipe["key_protein_keywords"][0] if selected_recipe["key_protein_keywords"] else "",
            "estimated_cost": f"${meal_cost:.2f}",
            "estimated_cost_per_serving": f"${meal_cost_serv:.2f}",
            "sale_highlights": sale_highlights,
            "ingredients": meal_ingredients,
            "instructions": selected_recipe["instructions"],
            "feedback": None,
            "calendar_synced": False,
            "calendar_event_id": None,
            "is_no_meal_needed": False,
            "is_themed_routine": False,
            "is_calendar_reserved": False
        }
        meals.append(meal_obj)
        
    plan_title = f"{'Weekly' if plan_type == 'week' else 'Monthly'} Smart Meal Plan ({start_dt.strftime('%b %d')} – {end_dt.strftime('%b %d')})"
    
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "plan_type": plan_type,
        "start_date": start_dt.strftime("%Y-%m-%d"),
        "end_date": end_dt.strftime("%Y-%m-%d"),
        "title": plan_title,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dietary_pref": dietary_pref,
        "servings": servings,
        "notes": custom_notes,
        "total_meals": len(meals),
        "total_estimated_cost": f"${total_cost:.2f}",
        "total_estimated_savings": f"${total_savings:.2f}",
        "meals_data": meals
    }

# --- Smart Meal Planner Routes ---

class DayRulesSaveRequest(BaseModel):
    rules: dict

@app.get("/api/meals/rules")
def get_meal_day_rules(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    user_prefs = settings.get("meal_preferences", {})
    rules = user_prefs.get("day_rules", DEFAULT_DAY_RULES)
    return {"status": "success", "rules": rules}

@app.post("/api/meals/rules")
def save_meal_day_rules(req: DayRulesSaveRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    if "meal_preferences" not in settings:
        settings["meal_preferences"] = {}
    settings["meal_preferences"]["day_rules"] = req.rules
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "rules": req.rules}

class FamilyProfileSaveRequest(BaseModel):
    family_name: str = "Our Family"
    members: list

class SiteSuggestionCreateRequest(BaseModel):
    page: str = "General"
    title: str
    description: str
    author: str = "Wife"
    priority: str = "improvement"

@app.get("/api/meals/family_profile")
def get_family_profile_api(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    family_profile = settings.get("family_profile", DEFAULT_FAMILY_PROFILE)
    nutrition_calc = calculate_family_nutrition_needs(family_profile)
    return {"status": "success", "family_profile": family_profile, "nutrition": nutrition_calc}

@app.post("/api/meals/family_profile")
def save_family_profile_api(req: FamilyProfileSaveRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    settings = json.loads(row['settings']) if row and row['settings'] else {}
    
    profile_data = {
        "family_name": req.family_name or "Our Family",
        "total_members": len(req.members),
        "members": req.members,
        "notes": f"{len(req.members)} family members"
    }
    settings["family_profile"] = profile_data
    
    # Also default user servings in meal_preferences
    if "meal_preferences" not in settings:
        settings["meal_preferences"] = {}
    settings["meal_preferences"]["default_servings"] = len(req.members)
    
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    conn.commit()
    conn.close()
    
    nutrition_calc = calculate_family_nutrition_needs(profile_data)
    return {"status": "success", "family_profile": profile_data, "nutrition": nutrition_calc}

# --- Site Suggestions & Wife Feedback Routes ---

@app.get("/api/suggestions")
def get_site_suggestions_api(status: str = None, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    if status and status != "all":
        c.execute("SELECT id, user_id, page, title, description, author, priority, status, created_at, completed_at FROM site_suggestions WHERE user_id=? AND status=? ORDER BY created_at DESC", (user_id, status))
    else:
        c.execute("SELECT id, user_id, page, title, description, author, priority, status, created_at, completed_at FROM site_suggestions WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM site_suggestions WHERE user_id=? AND status='open'", (user_id,))
    open_count = c.fetchone()[0]
    conn.close()
    
    suggestions = []
    for r in rows:
        suggestions.append({
            "id": r["id"],
            "page": r["page"],
            "title": r["title"],
            "description": r["description"],
            "author": r["author"] or "Wife",
            "priority": r["priority"] or "improvement",
            "status": r["status"] or "open",
            "created_at": r["created_at"],
            "completed_at": r["completed_at"]
        })
    return {"status": "success", "suggestions": suggestions, "open_count": open_count}

@app.post("/api/suggestions")
def create_site_suggestion_api(req: SiteSuggestionCreateRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    sugg_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    author = req.author.strip() if req.author and req.author.strip() else "Wife"
    page = req.page.strip() if req.page and req.page.strip() else "General"
    title = req.title.strip() if req.title and req.title.strip() else "Suggestion"
    desc = req.description.strip() if req.description else ""
    priority = req.priority or "improvement"
    
    c.execute("""INSERT INTO site_suggestions 
                 (id, user_id, page, title, description, author, priority, status, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)""",
              (sugg_id, user_id, page, title, desc, author, priority, now))
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM site_suggestions WHERE user_id=? AND status='open'", (user_id,))
    open_count = c.fetchone()[0]
    conn.close()
    
    return {
        "status": "success",
        "suggestion": {
            "id": sugg_id,
            "page": page,
            "title": title,
            "description": desc,
            "author": author,
            "priority": priority,
            "status": "open",
            "created_at": now
        },
        "open_count": open_count
    }

@app.put("/api/suggestions/{sugg_id}/complete")
def complete_site_suggestion_api(sugg_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("UPDATE site_suggestions SET status='completed', completed_at=? WHERE id=? AND user_id=?", (now, sugg_id, user_id))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM site_suggestions WHERE user_id=? AND status='open'", (user_id,))
    open_count = c.fetchone()[0]
    conn.close()
    return {"status": "success", "id": sugg_id, "status": "completed", "open_count": open_count}

@app.delete("/api/suggestions/{sugg_id}")
def delete_site_suggestion_api(sugg_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM site_suggestions WHERE id=? AND user_id=?", (sugg_id, user_id))
    conn.commit()
    c.execute("SELECT COUNT(*) FROM site_suggestions WHERE user_id=? AND status='open'", (user_id,))
    open_count = c.fetchone()[0]
    conn.close()
    return {"status": "success", "id": sugg_id, "open_count": open_count}

@app.get("/api/meals/current")
def get_current_meal_plan(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, plan_type, start_date, end_date, title, created_at, updated_at, meals_data, dietary_pref, servings, notes FROM meal_plans WHERE user_id=? ORDER BY start_date DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    u_row = c.fetchone()
    settings = json.loads(u_row['settings']) if u_row and u_row['settings'] else {}
    user_prefs = settings.get("meal_preferences", {
        "liked_cuisines": [],
        "disliked_cuisines": [],
        "liked_ingredients": [],
        "disliked_ingredients": [],
        "liked_meals": [],
        "disliked_meals": []
    })
    if "day_rules" not in user_prefs:
        user_prefs["day_rules"] = DEFAULT_DAY_RULES
    
    c.execute("SELECT count(*) FROM grocery_stores WHERE user_id=?", (user_id,))
    stores_count = c.fetchone()[0]
    conn.close()
    
    if not row:
        return {"plan": None, "preferences": user_prefs, "stores_count": stores_count}
        
    plan_dict = dict(row)
    try:
        plan_dict["meals_data"] = json.loads(plan_dict["meals_data"])
    except Exception:
        plan_dict["meals_data"] = []
        
    return {"plan": plan_dict, "preferences": user_prefs, "stores_count": stores_count}

@app.get("/api/meals/plans")
def list_meal_plans(user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, plan_type, start_date, end_date, title, created_at, updated_at, dietary_pref, servings FROM meal_plans WHERE user_id=? ORDER BY start_date DESC", (user_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@app.get("/api/meals/plans/{plan_id}")
def get_meal_plan(plan_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, plan_type, start_date, end_date, title, created_at, updated_at, meals_data, dietary_pref, servings, notes FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Meal plan not found.")
    plan_dict = dict(row)
    try:
        plan_dict["meals_data"] = json.loads(plan_dict["meals_data"])
    except Exception:
        plan_dict["meals_data"] = []
    return plan_dict

@app.post("/api/meals/generate")
def create_meal_plan(req: MealPlanGenerateRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    
    c.execute("SELECT name, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
    all_stores = []
    for r in c.fetchall():
        deals = []
        if r["cached_deals"]:
            try: deals = json.loads(r["cached_deals"])
            except Exception: deals = []
        all_stores.append({"name": r["name"], "deals": deals})
        
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    u_row = c.fetchone()
    settings = json.loads(u_row['settings']) if u_row and u_row['settings'] else {}
    user_prefs = settings.get("meal_preferences", {
        "liked_cuisines": [],
        "disliked_cuisines": [],
        "liked_ingredients": [],
        "disliked_ingredients": [],
        "liked_meals": [],
        "disliked_meals": []
    })
    
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    service = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
            service = build('calendar', 'v3', credentials=creds)
        except Exception as ge:
            logger.warning(f"Google Calendar check during meal plan generation: {ge}")
    
    plan = generate_smart_meal_plan(
        user_id=user_id,
        plan_type=req.plan_type,
        dietary_pref=req.dietary_pref or "All",
        servings=req.servings or 4,
        start_date_str=req.start_date,
        custom_notes=req.custom_notes or "",
        all_stores=all_stores,
        user_prefs=user_prefs,
        conn=conn,
        service=service
    )
    
    c.execute("""
        INSERT INTO meal_plans (id, user_id, plan_type, start_date, end_date, title, created_at, updated_at, meals_data, dietary_pref, servings, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plan["id"],
        user_id,
        plan["plan_type"],
        plan["start_date"],
        plan["end_date"],
        plan["title"],
        plan["created_at"],
        plan["updated_at"],
        json.dumps(plan["meals_data"]),
        plan["dietary_pref"],
        plan["servings"],
        plan["notes"]
    ))
    conn.commit()
    conn.close()
    return {"status": "success", "plan": plan}

@app.post("/api/meals/{plan_id}/meal/{meal_id}/feedback")
def submit_meal_feedback(plan_id: str, meal_id: str, req: MealFeedbackRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT meals_data FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal plan not found.")
        
    meals = json.loads(row["meals_data"])
    target_meal = None
    for m in meals:
        if m.get("id") == meal_id:
            target_meal = m
            m["feedback"] = req.feedback
            break
            
    if not target_meal:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal not found in plan.")
        
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    u_row = c.fetchone()
    settings = json.loads(u_row['settings']) if u_row and u_row['settings'] else {}
    prefs = settings.get("meal_preferences", {
        "liked_cuisines": [],
        "disliked_cuisines": [],
        "liked_ingredients": [],
        "disliked_ingredients": [],
        "liked_meals": [],
        "disliked_meals": []
    })
    
    m_cuisine = target_meal.get("cuisine", "")
    m_title = target_meal.get("title", "")
    m_protein = target_meal.get("key_protein", "")
    
    if req.feedback == "like":
        if m_cuisine and m_cuisine not in prefs["liked_cuisines"]:
            prefs["liked_cuisines"].append(m_cuisine)
        if m_cuisine in prefs["disliked_cuisines"]:
            prefs["disliked_cuisines"].remove(m_cuisine)
        if m_protein and m_protein not in prefs["liked_ingredients"]:
            prefs["liked_ingredients"].append(m_protein)
        if m_protein in prefs["disliked_ingredients"]:
            prefs["disliked_ingredients"].remove(m_protein)
        if m_title and m_title not in prefs["liked_meals"]:
            prefs["liked_meals"].append(m_title)
        if m_title in prefs["disliked_meals"]:
            prefs["disliked_meals"].remove(m_title)
            
    elif req.feedback == "dislike":
        if m_cuisine and m_cuisine not in prefs["disliked_cuisines"]:
            prefs["disliked_cuisines"].append(m_cuisine)
        if m_cuisine in prefs["liked_cuisines"]:
            prefs["liked_cuisines"].remove(m_cuisine)
        if m_protein and m_protein not in prefs["disliked_ingredients"]:
            prefs["disliked_ingredients"].append(m_protein)
        if m_protein in prefs["liked_ingredients"]:
            prefs["liked_ingredients"].remove(m_protein)
        if m_title and m_title not in prefs["disliked_meals"]:
            prefs["disliked_meals"].append(m_title)
        if m_title in prefs["liked_meals"]:
            prefs["liked_meals"].remove(m_title)
            
    settings["meal_preferences"] = prefs
    now = datetime.now().isoformat()
    c.execute("UPDATE users SET settings=? WHERE id=?", (json.dumps(settings), user_id))
    c.execute("UPDATE meal_plans SET meals_data=?, updated_at=? WHERE id=? AND user_id=?", (json.dumps(meals), now, plan_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "feedback": req.feedback, "meal": target_meal, "preferences": prefs}

@app.post("/api/meals/{plan_id}/meal/{meal_id}/swap")
def swap_meal_recipe(plan_id: str, meal_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT meals_data, servings FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal plan not found.")
        
    meals = json.loads(row["meals_data"])
    target_idx = None
    for idx, m in enumerate(meals):
        if m.get("id") == meal_id:
            target_idx = idx
            break
            
    if target_idx is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal not found in plan.")
        
    old_meal = meals[target_idx]
    current_recipe_ids = {m.get("recipe_id") for m in meals}
    servings = int(row["servings"] or 4)
    
    c.execute("SELECT name, cached_deals FROM grocery_stores WHERE user_id=?", (user_id,))
    all_stores = []
    for r in c.fetchall():
        deals = []
        if r["cached_deals"]:
            try: deals = json.loads(r["cached_deals"])
            except Exception: deals = []
        all_stores.append({"name": r["name"], "deals": deals})
        
    c.execute("SELECT settings FROM users WHERE id=?", (user_id,))
    u_row = c.fetchone()
    settings = json.loads(u_row['settings']) if u_row and u_row['settings'] else {}
    user_prefs = settings.get("meal_preferences", {
        "disliked_cuisines": [],
        "liked_cuisines": [],
        "disliked_ingredients": [],
        "liked_ingredients": [],
        "disliked_meals": []
    })
    
    # Select alternative candidate not used in plan
    candidates = [r for r in MEAL_RECIPES_CATALOG if r["id"] not in current_recipe_ids]
    if not candidates:
        candidates = [r for r in MEAL_RECIPES_CATALOG if r["id"] != old_meal.get("recipe_id")]
    if not candidates:
        candidates = MEAL_RECIPES_CATALOG
        
    # Prefer recipes with on-sale proteins
    sale_proteins = set()
    for s in all_stores:
        for d in s.get("deals", []):
            item_name = (d.get("item") or "").lower()
            toks = normalize_item_tokens(item_name)
            cat = (d.get("category") or "").lower()
            if "meat" in cat or "seafood" in cat:
                sale_proteins.update(toks)
                
    best_candidate = candidates[0]
    for cand in candidates:
        for pk in cand["key_protein_keywords"]:
            if any(stem in pk for stem in sale_proteins):
                best_candidate = cand
                break
                
        # Match ingredients to stores
    meal_ingredients = []
    sale_highlights = []
    meal_cost = 0.0
    for base_ing in best_candidate["ingredients"]:
        ing_name = base_ing["name"]
        ing_cat = base_ing["category"]
        best_match = find_best_store_for_ingredient(ing_name, ing_cat, all_stores)
        ing_cost = 3.50
        if "strip" in ing_name.lower() or "steak" in ing_name.lower() or "salmon" in ing_name.lower() or "shrimp" in ing_name.lower():
            ing_cost = 8.50
        elif "chicken" in ing_name.lower() or "beef" in ing_name.lower() or "pork" in ing_name.lower():
            ing_cost = 5.50
        elif "produce" in ing_cat.lower():
            ing_cost = 2.00
        elif "dairy" in ing_cat.lower():
            ing_cost = 2.50
        else:
            ing_cost = 1.75
            
        if best_match["on_sale"]:
            sale_saving = round(ing_cost * 0.35, 2)
            ing_cost -= sale_saving
            sale_highlights.append({
                "item": ing_name.split("(")[0].strip(),
                "store": best_match["store"],
                "price": best_match["price"],
                "savings": f"Save ${sale_saving:.2f} at {best_match['store']}"
            })
        meal_cost += ing_cost
        meal_ingredients.append({
            "name": ing_name,
            "category": ing_cat,
            "store": best_match["store"],
            "price": best_match["price"],
            "on_sale": best_match["on_sale"],
            "image_url": best_match.get("image_url", ""),
            "savings": best_match.get("savings", "")
        })
        
    meal_cost_serv = meal_cost / max(servings, 1)
    
    new_meal = {
        "id": old_meal["id"],
        "recipe_id": best_candidate["id"],
        "day": old_meal["day"],
        "date": old_meal["date"],
        "week_num": old_meal.get("week_num", 1),
        "meal_type": "Dinner",
        "title": best_candidate["title"],
        "description": best_candidate["description"],
        "cuisine": best_candidate["cuisine"],
        "prep_time": best_candidate["prep_time"],
        "cook_time": best_candidate["cook_time"],
        "servings": servings,
        "calories": best_candidate["calories"],
        "key_protein": best_candidate["key_protein_keywords"][0] if best_candidate["key_protein_keywords"] else "",
        "estimated_cost": f"${meal_cost:.2f}",
        "estimated_cost_per_serving": f"${meal_cost_serv:.2f}",
        "sale_highlights": sale_highlights,
        "ingredients": meal_ingredients,
        "instructions": best_candidate["instructions"],
        "feedback": None,
        "calendar_synced": False,
        "calendar_event_id": None
    }
    
    meals[target_idx] = new_meal
    now = datetime.now().isoformat()
    c.execute("UPDATE meal_plans SET meals_data=?, updated_at=? WHERE id=? AND user_id=?", (json.dumps(meals), now, plan_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "meal": new_meal}

def format_meal_calendar_desc(m: dict) -> str:
    ing_lines = [f"- {ing['name']} ({ing['store']} • {ing['price']})" for ing in m.get("ingredients", [])]
    step_lines = [f"{idx+1}. {s}" for idx, s in enumerate(m.get("instructions", []))]
    
    macros = m.get("macros", {})
    prot = macros.get("protein_g", m.get("protein_g", "N/A"))
    crbs = macros.get("carbs_g", m.get("carbs_g", "N/A"))
    fat = macros.get("fat_g", m.get("fat_g", "N/A"))
    fib = macros.get("fiber_g", m.get("fiber_g", "N/A"))
    
    fam_mac = m.get("family_macros", {})
    fam_mac_str = ""
    if fam_mac:
        fam_mac_str = f"👨‍👩‍👧‍👦 Family Batch Macros (servings: {m.get('servings', 5)}): {fam_mac.get('calories', 'N/A')} kcal | {fam_mac.get('protein_g', 'N/A')}g Protein | {fam_mac.get('carbs_g', 'N/A')}g Carbs | {fam_mac.get('fat_g', 'N/A')}g Fat\n"
        
    bulk_line = ""
    if m.get("bulk_reuse", {}).get("is_bulk"):
        bulk_line = f"🔁 Bulk Buy Synergy: {m['bulk_reuse']['bulk_title']} ({m['bulk_reuse']['bulk_note']})\n"
        
    guide_line = f"🥗 Family Portion Guide: {m.get('family_portion_guide', '')}\n" if m.get('family_portion_guide') else ""
    effort_txt = m.get("effort_label", m.get("effort_level", "Standard Weeknight"))
    
    return f"""🍽️ {m['title']} ({m.get('cuisine', 'Family Dinner')})
⏱️ {effort_txt} | Prep: {m.get('prep_time', '15m')} | Cook: {m.get('cook_time', '20m')} | Servings: {m.get('servings', 5)}
💵 Est. Cost: {m.get('estimated_cost', '$0.00')} ({m.get('estimated_cost_per_serving', '$0.00')}/serving)
📊 Macros (per serving): 🔥 {m.get('calories', 0)} kcal | 🥩 {prot}g Protein | 🍞 {crbs}g Carbs | 🥑 {fat}g Fat | 🌾 {fib}g Fiber
{fam_mac_str}{guide_line}{bulk_line}
🛒 Recommended Store Ingredients:
{chr(10).join(ing_lines)}

👩‍🍳 Cooking Directions:
{chr(10).join(step_lines)}
"""

@app.post("/api/meals/{plan_id}/meal/{meal_id}/calendar")
def sync_meal_to_calendar(plan_id: str, meal_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT meals_data FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal plan not found.")
        
    meals = json.loads(row["meals_data"])
    target_meal = None
    for m in meals:
        if m.get("id") == meal_id:
            target_meal = m
            break
            
    if not target_meal:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal not found in plan.")
        
    event_date = f"{target_meal['date']}T18:30:00"
    
    # Check if Google Calendar is authorized for user
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    service = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
            service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.warning(f"Google Calendar auth error in sync_meal: {e}")

    # Deduplication: check if meal or food event is already on calendar for this date
    existing_cal_meal = find_existing_meal_or_food_on_calendar(user_id, target_meal['date'], service=service, conn=conn)
    if existing_cal_meal:
        logger.info(f"Meal already on calendar for {target_meal['date']}: '{existing_cal_meal.get('title')}'. Skipping duplicate.")
        target_meal["calendar_synced"] = True
        if existing_cal_meal.get("id"):
            target_meal["calendar_event_id"] = existing_cal_meal.get("id")
        now = datetime.now().isoformat()
        c.execute("UPDATE meal_plans SET meals_data=?, updated_at=? WHERE id=? AND user_id=?", (json.dumps(meals), now, plan_id, user_id))
        conn.commit()
        conn.close()
        return {"status": "success", "event_id": existing_cal_meal.get("id"), "synced": True, "already_existed": True, "title": existing_cal_meal.get("title")}

    event_id = str(uuid.uuid4())
    if target_meal.get("is_no_meal_needed"):
        event_title = f"👨‍👩‍👧 {target_meal['title']}"
    elif target_meal.get("is_themed_routine"):
        event_title = f"🍕 {target_meal['title']}"
    else:
        event_title = f"🍽️ Dinner: {target_meal['title']}"
    # event_date set above
    # event_title set above with routine emojis
    
    ing_lines = []
    for ing in target_meal.get("ingredients", []):
        ing_lines.append(f"- {ing['name']} ({ing['store']} • {ing['price']})")
        
    step_lines = []
    for idx, s in enumerate(target_meal.get("instructions", [])):
        step_lines.append(f"{idx+1}. {s}")
        
    event_desc = format_meal_calendar_desc(target_meal)
    first_store = target_meal["ingredients"][0]["store"] if target_meal.get("ingredients") else "Local Store"
    
    # Check if Google Calendar is authorized for user
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    status = "pending"
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
            service = build('calendar', 'v3', credentials=creds)
            push_event_to_gcal(service, event_title, event_desc, event_date, first_store, is_meal=True)
            status = "added"
        except Exception as e:
            logger.warning(f"Could not push meal to Google Calendar directly: {e}")
            status = "pending"
            
    c.execute("INSERT INTO events (id, user_id, account, title, date, description, status, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (event_id, user_id, "Smart Meal Planner", event_title, event_date, event_desc, status, first_store))
              
    target_meal["calendar_synced"] = True
    target_meal["calendar_event_id"] = event_id
    now = datetime.now().isoformat()
    c.execute("UPDATE meal_plans SET meals_data=?, updated_at=? WHERE id=? AND user_id=?", (json.dumps(meals), now, plan_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "event_id": event_id, "synced": True}

@app.post("/api/meals/{plan_id}/calendar_all")
def sync_all_meals_to_calendar(plan_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT meals_data FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal plan not found.")
        
    meals = json.loads(row["meals_data"])
    token_file = os.path.join(DATA_DIR, f"token_{user_id}.json")
    has_gcal = os.path.exists(token_file)
    service = None
    if has_gcal:
        try:
            creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
            service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.warning(f"Google Calendar auth error: {e}")
            
    synced_count = 0
    for target_meal in meals:
        if target_meal.get("calendar_synced"):
            continue
            
        existing_cal = find_existing_meal_or_food_on_calendar(user_id, target_meal['date'], service=service, conn=conn)
        if existing_cal:
            logger.info(f"Calendar check: meal '{existing_cal.get('title')}' already exists on {target_meal['date']}. Skipping duplicate.")
            target_meal["calendar_synced"] = True
            if existing_cal.get("id"):
                target_meal["calendar_event_id"] = existing_cal.get("id")
            synced_count += 1
            continue
            
        event_id = str(uuid.uuid4())
        event_date = f"{target_meal['date']}T18:30:00"
        if target_meal.get("is_no_meal_needed"):
            event_title = f"👨‍👩‍👧 {target_meal['title']}"
        elif target_meal.get("is_themed_routine"):
            event_title = f"🍕 {target_meal['title']}"
        else:
            event_title = f"🍽️ Dinner: {target_meal['title']}"
        
        ing_lines = [f"- {ing['name']} ({ing['store']} • {ing['price']})" for ing in target_meal.get("ingredients", [])]
        step_lines = [f"{idx+1}. {s}" for idx, s in enumerate(target_meal.get("instructions", []))]
        
        event_desc = format_meal_calendar_desc(target_meal)
        first_store = target_meal["ingredients"][0]["store"] if target_meal.get("ingredients") else "Local Store"
        status = "pending"
        if service:
            try:
                push_event_to_gcal(service, event_title, event_desc, event_date, first_store, is_meal=True)
                status = "added"
            except Exception:
                pass
                
        c.execute("INSERT INTO events (id, user_id, account, title, date, description, status, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (event_id, user_id, "Smart Meal Planner", event_title, event_date, event_desc, status, first_store))
                  
        target_meal["calendar_synced"] = True
        target_meal["calendar_event_id"] = event_id
        synced_count += 1
        
    now = datetime.now().isoformat()
    c.execute("UPDATE meal_plans SET meals_data=?, updated_at=? WHERE id=? AND user_id=?", (json.dumps(meals), now, plan_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "synced_count": synced_count}

@app.post("/api/meals/{plan_id}/export_grocery_list")
def export_meal_plan_to_grocery_list(plan_id: str, req: MealExportGroceryRequest, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT title, start_date, meals_data FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Meal plan not found.")
        
    meals = json.loads(row["meals_data"])
    target_meals = []
    if req.meal_ids:
        target_meals = [m for m in meals if m.get("id") in req.meal_ids]
    else:
        target_meals = meals
        
    now = datetime.now().isoformat()
    target_list_id = req.list_id
    target_title = req.list_title
    
    if target_list_id:
        c.execute("SELECT id, title FROM grocery_lists WHERE id=? AND user_id=?", (target_list_id, user_id))
        r = c.fetchone()
        if not r:
            target_list_id = None
        else:
            target_title = r["title"]
            
    if not target_list_id:
        target_list_id = str(uuid.uuid4())
        target_title = target_title or f"Meal Plan Groceries ({row['start_date']})"
        c.execute("INSERT INTO grocery_lists (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                  (target_list_id, user_id, target_title, now, now))
                  
    added_count = 0
    for m in target_meals:
        m_title = m.get("title", "Dinner")
        for ing in m.get("ingredients", []):
            item_id = str(uuid.uuid4())
            name = ing.get("name", "Ingredient")
            store = ing.get("store", "Any")
            price = ing.get("price", "")
            cat = ing.get("category", "General")
            img = ing.get("image_url", "")
            notes = f"{price} ({m_title})" if price else m_title
            if m.get("bulk_reuse", {}).get("is_bulk"):
                notes += f" • Bulk Synergy: {m['bulk_reuse']['bulk_title']}"
            
            c.execute("INSERT INTO grocery_list_items (id, list_id, user_id, item_name, store_name, price_notes, category, is_checked, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                      (item_id, target_list_id, user_id, name, store, notes, cat, img))
            added_count += 1
            
    c.execute("UPDATE grocery_lists SET updated_at=? WHERE id=? AND user_id=?", (now, target_list_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "list_id": target_list_id, "list_title": target_title, "items_count": added_count}

@app.delete("/api/meals/{plan_id}")
def delete_meal_plan(plan_id: str, user_id: str = Depends(verify_auth)):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM meal_plans WHERE id=? AND user_id=?", (plan_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

