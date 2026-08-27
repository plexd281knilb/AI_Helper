# AGENTS.md — Developer & AI Agent Guide

This document provides a comprehensive overview of the **AI Helper** codebase, its architectural design, data flows, database schemas, and guidelines for AI agents and developers working on this repository.

---

## 1. Project Overview

**AI Helper** is a self-hosted, multi-user web application designed to automatically scan incoming emails via IMAP, detect calendar events and deadlines using Large Language Models (Google Gemini or OpenAI), present extracted events in a clean dashboard, and synchronize them directly with Google Calendar.

It is built with **FastAPI** (Python 3.11) on the backend and a responsive, vanilla JavaScript/HTML5/CSS3 Single Page Application (SPA) on the frontend, containerized for easy deployment on Docker / Unraid.

---

## 2. Directory Structure

```
.
├── app.py                 # Core backend: FastAPI app, DB initialization, API routes, IMAP fetching, AI parsing, and Google OAuth
├── static/
│   └── index.html         # Complete frontend SPA (Dashboard, History, Settings, Users, Logs)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Python 3.11 slim container image
├── docker-compose.yml     # Container definition and volume mapping (`./data:/app/data`)
├── README.md              # High-level project README
├── AGENTS.md              # Architectural and development guide for AI agents
└── data/                  # Persistent data directory (auto-created at runtime)
    ├── app.db             # SQLite database storing users, accounts, events, and email history
    ├── app.log            # Rotating application logs (1MB max)
    ├── client_secret.json # Uploaded Google OAuth credentials
    └── token_<user_id>.json # Stored Google Calendar OAuth tokens per user
```

---

## 3. Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) with [Uvicorn](https://www.uvicorn.org/)
- **Database**: SQLite3 (managed in `data/app.db`)
- **Email Fetching**: [imap-tools](https://github.com/ikvk/imap_tools) (IMAP protocol)
- **AI Providers**:
  - Google Gemini (`google-generativeai`)
  - OpenAI (`openai`)
- **Calendar Integration**: Google Calendar API v3 (`google-api-python-client`, `google-auth-oauthlib`)
- **Frontend**: Vanilla JS (ES6+), HTML5, CSS3 with dark mode theme (embedded in `static/index.html`)
- **Containerization**: Docker & Docker Compose

---

## 4. Database Schema (`data/app.db`)

All tables are initialized and automatically migrated on startup in `init_db()` (`app.py`):

### `users`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Unique user UUID |
| `username` | TEXT UNIQUE | Login username |
| `password_hash` | TEXT | SHA-256 password hash |
| `settings` | TEXT (JSON) | JSON object containing AI provider, keys, models, custom instructions, public URL, and OAuth state |

### `sessions`
| Column | Type | Description |
|---|---|---|
| `token` | TEXT PRIMARY KEY | 64-character hex session token |
| `user_id` | TEXT | Associated user UUID |
| `expires` | REAL | Timestamp for session expiration |

### `email_accounts`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Account UUID |
| `user_id` | TEXT | Foreign key referencing `users.id` |
| `email_user` | TEXT | IMAP email address |
| `email_pass` | TEXT | IMAP App Password |
| `email_host` | TEXT | IMAP server host (e.g. `imap.gmail.com`) |

### `events`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Event UUID |
| `user_id` | TEXT | User UUID |
| `account` | TEXT | Email account that received the message |
| `title` | TEXT | Event title |
| `date` | TEXT | ISO 8601 event start date/time |
| `description` | TEXT | Detailed notes / event context |
| `location` | TEXT | Physical address, room, or location |
| `status` | TEXT | `'pending'`, `'added'`, or `'dismissed'` |

### `processed_emails_v2`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT | Email UID from IMAP server |
| `user_id` | TEXT | User UUID |
| `account` | TEXT | Email address that received the email |
| `subject` | TEXT | Email subject line |
| `date` | TEXT | Email date (ISO 8601 format) |
| `body` | TEXT | Full plain text / HTML body of the email |
| `sender` | TEXT | Sender email/name (`From:` header) |
| `reason` | TEXT | AI decision explanation and sync outcome |
| `status` | TEXT | `'added'` or `'no_event'` |
| **PRIMARY KEY** | `(id, user_id, account)` | Prevents duplicate processing per account per user |

---

## 5. Core Processing & Architecture

### 1. Authentication
- Cookie-based authentication using `session_token`.
- Verified in FastAPI route dependencies via `verify_auth(request)`.

### 2. Email Ingestion (`process_user_emails`)
- Loops through all configured `email_accounts` for a user.
- Connects via IMAP (`MailBox.login`).
- Fetches messages from the past 7 days (`AND(date_gte=...)`, limit 20 per account).
- Checks `processed_emails_v2` to skip already-analyzed emails.

### 3. AI Extraction & Reasoning (`extract_event`)
- Formulates a structured prompt including custom user instructions (if configured).
- Requests a JSON response with:
  - `events`: Array of objects (`title`, `date`, `description`, `location`).
  - `reason`: Explanation of why events were extracted or why the email was skipped (e.g. newsletter, past event, custom grade filter, receipt).
- Fallback parsers handle raw JSON, markdown-wrapped JSON (```` ```json ````), legacy arrays, or `NO_EVENT`.
- Automatically enforces Gemini rate limits (4.1s sleep per request for free-tier compatibility).

### 4. Calendar Sync
- When events are detected, they are inserted into the `events` table with status `'pending'`.
- If Google Calendar is connected (`token_<user_id>.json` exists), events are immediately auto-synced to Google Calendar and updated to status `'added'`.
- If not connected, users can manually sync or click manual add links on the Dashboard.

### 5. Email Processing History
- Stores complete email content (`body`), sender, subject, date, AI reason, and status in `processed_emails_v2`.
- The History tab in `static/index.html` provides:
  - Interactive click-to-expand card view with full email body and formatted headers.
  - Clear AI decision boxes explaining why events were or were not added to the calendar.
  - Live search across subjects, senders, reasons, and email bodies.
  - Category filters: **All**, **Events Added**, and **No Events**.
  - Single and bulk deletion of memory items (to allow re-processing if needed).

### 6. Background Worker
- An `asyncio` task (`scheduled_email_fetch`) triggers hourly background scans across all configured users and accounts.

---

## 6. API Route Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/auth/status` | Check authentication & first-time setup status | No |
| `POST` | `/api/auth/login` | Log in user | No |
| `POST` | `/api/auth/register` | Register new user | No |
| `POST` | `/api/auth/logout` | Log out user and clear cookie | No |
| `GET` | `/api/users` | List all users | Yes |
| `POST` | `/api/users` | Create a user | Yes |
| `PUT` | `/api/users/{id}` | Update username/password | Yes |
| `DELETE` | `/api/users/{id}` | Delete user and all associated data | Yes |
| `GET` | `/api/settings` | Read user settings and connected accounts | Yes |
| `POST` | `/api/settings/ai` | Save AI configuration & custom prompt | Yes |
| `POST` | `/api/accounts` | Add or update an IMAP account | Yes |
| `DELETE` | `/api/accounts/{id}` | Delete an IMAP account | Yes |
| `GET` | `/api/events` | Fetch active calendar events (pending & added) | Yes |
| `POST` | `/api/events/{id}/sync` | Manually sync event to Google Calendar | Yes |
| `DELETE` | `/api/events/{id}` | Dismiss an event | Yes |
| `POST` | `/api/events/bulk_dismiss`| Bulk dismiss events | Yes |
| `GET` | `/api/fetch_emails` | Trigger manual email fetching & AI parsing | Yes |
| `GET` | `/api/history` | Retrieve up to 100 processed email records | Yes |
| `DELETE` | `/api/history/{account}/{uid}` | Remove specific email from memory | Yes |
| `POST` | `/api/history/bulk_delete` | Bulk remove emails from memory | Yes |
| `DELETE` | `/api/settings/reset_history` | Wipe all email processing memory | Yes |
| `GET` | `/api/auth/google/url` | Generate Google OAuth authorization URL | Yes |
| `GET` | `/api/auth/google/callback` | Google OAuth callback handler | No |
| `POST` | `/api/upload_client_secret` | Upload Google OAuth `client_secret.json` | Yes |
| `POST` | `/api/models` | List available models from Gemini or OpenAI | Yes |
| `GET` | `/api/logs` | View recent application logs (tail 1MB) | Yes |

---

## 7. Guidelines for AI Agents Working on this Codebase

1. **Database Changes**:
   - Always update `init_db()` in `app.py` using `ALTER TABLE ... ADD COLUMN` inside `try...except sqlite3.OperationalError:` blocks to preserve existing databases without requiring destructive rebuilds.
2. **Frontend UI Architecture**:
   - The UI is self-contained within `static/index.html`. Do not introduce heavy frontend build tooling (e.g. Webpack, Vite, React) unless explicitly requested.
   - Maintain dark theme CSS variables (`--bg-color`, `--card-bg`, `--accent`, `--border-color`).
   - Always sanitize/escape dynamic user content using `escapeHtml()` before rendering into the DOM to prevent XSS vulnerabilities.
3. **AI Provider Compatibility**:
   - Ensure prompts and JSON parsers work reliably with both Google Gemini and OpenAI models.
   - Preserve rate limit safeguards (e.g. delay between requests for Gemini free tier).
4. **Data Privacy & Secrets**:
   - Never hardcode or commit API keys, passwords, or credentials into the repository.
   - Keep user-specific OAuth credentials and session tokens isolated in the `data/` volume.
5. **Testing Changes**:
   - Compile Python code (`python -m py_compile app.py`) after making edits.
   - Verify that new or modified endpoints return valid JSON structures compatible with `static/index.html`.
