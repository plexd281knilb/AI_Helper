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

### `grocery_stores`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Store UUID |
| `user_id` | TEXT | Foreign key referencing `users.id` |
| `name` | TEXT | Store name (e.g. HEB, Kroger, Tom Thumb, Costco, Sprouts, Whole Foods, Walmart) |
| `ad_url` | TEXT | Weekly ad or circular URL |
| `notes` | TEXT | Custom store notes or location details |
| `last_scanned` | TEXT | ISO timestamp of last successful circular scan |
| `cached_deals` | TEXT (JSON) | Cached JSON array of extracted weekly deals |

### `grocery_lists`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Grocery list UUID |
| `user_id` | TEXT | Foreign key referencing `users.id` |
| `title` | TEXT | List title (e.g. "Weekly Essentials", "Costco Run") |
| `created_at` | TEXT | ISO timestamp of creation |
| `updated_at` | TEXT | ISO timestamp of last update |

### `grocery_list_items`
| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Item UUID |
| `list_id` | TEXT | Foreign key referencing `grocery_lists.id` |
| `user_id` | TEXT | Foreign key referencing `users.id` |
| `item_name` | TEXT | Item name and quantity |
| `store_name` | TEXT | Designated store (e.g. "HEB", "Costco", "Any") |
| `price_notes` | TEXT | Price or deal notes (e.g. "$4.99/lb sale", "Digital coupon") |
| `category` | TEXT | Item category (Produce, Meat & Seafood, Dairy, etc.) |
| `is_checked` | INTEGER | `0` = pending, `1` = checked/bought |

---

## 5. Core Processing & Architecture

### 1. Authentication
- Cookie-based authentication using `session_token`.
- Verified in FastAPI route dependencies via `verify_auth(request)`.

### 2. Email Ingestion (`process_user_emails`)
- Loops through all configured `email_accounts` for a user.
- Connects via IMAP (`MailBox.login`).
- Reads user-configured `lookback_days` (default 7 days) and `email_fetch_limit` (default 20 per account).
- Fetches messages (`AND(date_gte=...)`, reverse order).
- Checks `processed_emails_v2` to skip already-analyzed emails.
- Persists `last_scan_time` in user settings upon scan completion.

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

### 6. Background Worker & Job Scheduling (`scheduled_email_fetch`)
- An `asyncio` background task polls every 30 seconds to check if any user is due for an automated email scan.
- Each user can customize:
  - **Auto-Fetch Frequency**: Every 15m, 30m, 1h (default), 2h, 4h, 8h, 12h, 24h, custom minutes, or disabled (manual only).
  - **Lookback Window**: Past 1, 3, 7 (default), 14, or 30 days.
  - **Batch Limit**: Max 10, 20 (default), 50, or 100 emails per account per run.
- Real-time status badge and next-run countdown display in the Settings tab.

### 7. Local Deals & Smart Grocery Lists (`/api/groceries/*`)
- **Store Ads & Circulars**: Users can configure local store ad URLs (HEB, Kroger, Tom Thumb, Costco, Sprouts, Whole Foods, Walmart, etc.).
- **AI Ad Scraping**: Scrapes web circulars using clean HTML text extraction and parses structured deals by category.
- **Price Query & Deal Comparison**: Natural language prompt query allows users to ask for best prices, ingredient comparisons, and budget recommendations across stores.
- **Interactive Grocery Lists**: Create custom lists, group items by category or store, check off bought items, clear checked items, copy markdown/plain text lists to clipboard, and 1-click add deals directly to any list.
- **AI Meal-Prep List Generator**: Generates full recipe-based grocery lists with assigned stores and estimated pricing based on user dietary or meal planning prompts.

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
| `POST` | `/api/events/bulk_sync` | Bulk sync multiple events to Google Calendar | Yes |
| `DELETE` | `/api/events/{id}` | Dismiss an event | Yes |
| `POST` | `/api/events/bulk_dismiss`| Bulk dismiss events | Yes |
| `GET` | `/api/fetch_emails` | Trigger manual email fetching & AI parsing | Yes |
| `GET` | `/api/history` | Retrieve up to 100 processed email records | Yes |
| `DELETE` | `/api/history/{account}/{uid}` | Remove specific email from memory | Yes |
| `POST` | `/api/history/bulk_delete` | Bulk remove emails from memory | Yes |
| `DELETE` | `/api/settings/reset_history` | Wipe all email processing memory | Yes |
| `GET` | `/api/auth/google/url` | Generate Google OAuth authorization URL | Yes |
| `GET` | `/api/auth/google/callback` | Google OAuth callback handler | No |
| `DELETE` | `/api/auth/google/token` | Disconnect Google Calendar OAuth token | Yes |
| `POST` | `/api/upload_client_secret` | Upload Google OAuth `client_secret.json` | Yes |
| `POST` | `/api/models` | List available models from Gemini or OpenAI | Yes |
| `GET` | `/api/logs` | View recent application logs (tail 1MB) | Yes |
| `GET` | `/api/groceries/stores` | List all configured grocery stores and ads | Yes |
| `POST` | `/api/groceries/stores` | Add or update a grocery store | Yes |
| `DELETE` | `/api/groceries/stores/{id}` | Delete a grocery store | Yes |
| `POST` | `/api/groceries/stores/{id}/scan` | Scan store circular URL with AI | Yes |
| `POST` | `/api/groceries/stores/scan_all` | Scan all store circular URLs with AI | Yes |
| `POST` | `/api/groceries/query_deals` | AI price comparison and deals query | Yes |
| `GET` | `/api/groceries/lists` | List all grocery lists for user | Yes |
| `POST` | `/api/groceries/lists` | Create or update a grocery list | Yes |
| `DELETE` | `/api/groceries/lists/{id}` | Delete a grocery list and its items | Yes |
| `GET` | `/api/groceries/lists/{id}/items` | List items in a grocery list | Yes |
| `POST` | `/api/groceries/lists/{id}/items` | Add single item to grocery list | Yes |
| `POST` | `/api/groceries/lists/{id}/batch_items` | Batch add multiple items to grocery list | Yes |
| `PUT` | `/api/groceries/items/{id}` | Update grocery item (check off, edit) | Yes |
| `DELETE` | `/api/groceries/items/{id}` | Delete item from grocery list | Yes |
| `POST` | `/api/groceries/lists/{id}/clear_checked` | Remove all checked items from a list | Yes |
| `POST` | `/api/groceries/ai_generate_list` | Generate meal-prep grocery list with AI | Yes |

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
