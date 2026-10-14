# 🗺️ AI Helper — Strategic Engineering Roadmap

This document outlines the evolutionary roadmap for **AI Helper**, cataloging recent v2.5 architectural breakthroughs and charting our upcoming multi-phase engineering milestones to expand email intelligence, multimodal vision OCR, autonomous grocery execution, multi-calendar integrations, and household automation.

---

### ✨ What's New in v2.5

- **🏰 Portalarr-Inspired Responsive Navigation Shell:** Modern responsive navigation architecture with role-aware separation between **Main Workspace** (`Dashboard`, `Email History`, `Deals & Groceries`) and **Administration** (`Access Control & Users`, `System Settings`, `Live Diagnostic Logs`), featuring glowing badge indicators, slide-out mobile drawer, and quick-action fetch controls.
- **🛡️ Enterprise PBKDF2 Password Security & Role-Based Access Control (RBAC):** Salted PBKDF2-HMAC-SHA256 password hashing (100,000 iterations) with transparent backward-compatible auto-upgrades for legacy SHA-256 accounts, auto-expiring session garbage collection, and strict administrator path verification (`verify_admin`).
- **⚡ Fault-Isolated Multi-Account IMAP Engine:** Resilient email ingestion across multiple IMAP accounts with per-account error isolation, permissive SSL handshake negotiation for portal/school announcement digests, and zero database connection leaks.
- **🚀 High-Performance SQLite Composite Indexing:** Sub-millisecond queries on large multi-user databases with automated composite indexes across events, accounts, processing memory, and circular deals.
- **🛒 Stemmed Cross-Store Deal Comparison & Exact Cent Pricing:** Plural noun stemming (`stem_word`) and accurate cents-to-dollars price normalization (`parse_numeric_price`) allowing exact cross-store bargain matching across 25+ nationwide supermarket chains.
- **🥩 USDA Beef Grade Quality Isolation:** Dedicated beef grade detection (`prime`, `choice`, `select`, `wagyu`, `angus`) preventing misleading price comparisons across quality tiers.
- **🩺 Container Health Monitoring:** Standardized `/health` and `/api/health` endpoints with lightweight Python urllib healthchecks in `docker-compose.yml`.

---

### 🚀 Upcoming Phased Roadmap

#### Phase 1: Zero-Latency Communication & Cloud OAuth2 Ingestion
- **🔐 Native Google & Microsoft 365 OAuth2 Email Ingestion:**
  - Transition beyond App Passwords with native OAuth2 authorization flows for Gmail, Google Workspace, Outlook.com, and Microsoft 365.
  - Granular scopes (`https://www.googleapis.com/auth/gmail.readonly`) keeping user credentials completely private and avoiding 2FA app-password generation hurdles.
- **⚡ Real-Time Push Ingestion via Cloud Webhooks & Pub/Sub:**
  - Direct integration with Google Cloud Pub/Sub and Microsoft Graph Webhooks.
  - Eliminates polling delays: incoming event invitations, school notices, and flights trigger immediate instant extraction within 1–2 seconds of arrival.
- **📬 Unified Multi-Account Inbox & Activity Feed:**
  - Single-pane view aggregating incoming emails, AI parsing outcomes, and status across all connected inboxes with sender filtering and custom regex routing rules.

#### Phase 2: Multimodal Document Intelligence & Vision OCR
- **📸 Visual Circular & Paper Receipt OCR (Gemini Vision / GPT-4o):**
  - Direct photo uploads of physical printed supermarket circulars, coupon mailers, and paper cash register receipts.
  - Automatically transcribes deal pricing, dates, and item weights directly into the grocery database and price history trends.
- **✈️ Travel Itinerary & Reservation Extraction:**
  - Deep entity extraction for airline boarding passes, Amtrak train bookings, car rentals, and Airbnb/hotel confirmations.
  - Automatically captures check-in/check-out times, gate numbers, confirmation codes, and maps locations directly into calendar events.
- **📄 PDF Attachment Ticket & Bill Parser:**
  - Automatic extraction and parsing of attached PDF documents (e.g., concert tickets, doctor appointment confirmations, school newsletters, utility bills).
  - Automatically attaches the original PDF or excerpt to the synchronized calendar event notes.
- **🏫 Portal & League Scrapers (TeamSnap, ParentSquare, SportsEngine):**
  - Direct headless scrapers for youth sports schedules, school board announcement feeds, and municipal recreation calendars.

#### Phase 3: Autonomous Household & Grocery Agent
- **🛒 1-Click Cart Export & Auto-Fill (Walmart / Instacart / Kroger API):**
  - Transform your AI grocery list into real merchant carts in one click.
  - Deep-link and dispatch items directly into Walmart Cart, Instacart, or Kroger Digital Carts with matching product SKUs and quantities.
- **✂️ Digital Coupon Auto-Clipper & Reward Loyalty Optimizer:**
  - Automatically match grocery list items against active digital coupons (HEB Digital Coupons, Kroger Best Customer coupons, Target Circle offers).
  - Highlight net out-of-pocket prices after digital coupons and loyalty card discounts.
- **🔔 Price Drop, BOGO & Deal Alerts:**
  - User-configurable price triggers (e.g., "Alert me when Prime Ribeye drops below $10.99/lb" or "Alert me when Strawberries are 2 for $4").
  - Instant push notifications, Discord webhooks, or Telegram alerts when target deals are published.
- **🥫 Smart Pantry & Depletion Predictor:**
  - Track household staple consumption based on grocery purchase frequency.
  - Predictive reminders: "You bought Olive Oil 6 weeks ago and usually finish a bottle in 7 weeks. Add to list?"
  - Expiration date tracking for perishables (milk, chicken, fresh produce) to reduce household food waste.

#### Phase 4: Multi-Calendar & Smart Home Ecosystem
- **🍏 Apple iCloud & Microsoft Outlook 365 Two-Way Calendar Sync:**
  - Expand beyond Google Calendar with direct CalDAV / iCloud Calendar and Outlook Calendar API two-way synchronization.
  - Support for custom calendar selection (e.g. route School events to "Kids Calendar", Flights to "Travel Calendar", and Bills to "Family Finance").
- **🏡 Home Assistant Lovelace Card & Sensor Integration:**
  - Native Home Assistant integration via MQTT or custom integration component.
  - Live sensor entities: `sensor.ai_helper_upcoming_events`, `sensor.ai_helper_grocery_deals`, `sensor.ai_helper_weekly_savings`.
  - Custom Lovelace card for smart kitchen touchscreen displays showing tonight's meal plan and ingredients to buy.
- **🔄 Event Conflict & Travel Buffer Detection:**
  - Detect overlapping meetings or events with zero transit buffer between different physical locations.
  - Proactively alert the user: "Warning: Event at 2:00 PM is 15 miles away from your 1:30 PM appointment."

#### Phase 5: Mobile PWA, Voice & Offline Companion
- **📱 Installable Progressive Web App (PWA):**
  - Web App Manifest and Service Worker providing an app-like experience on iOS and Android home screens without an app store download.
  - Fast offline cache for viewing grocery lists and calendar events in basement supermarkets with zero cellular reception.
- **🛒 In-Store Shopping Mode:**
  - Department-sorted, high-contrast, one-thumb checkoff interface designed for one-handed operation while pushing a shopping cart.
  - Aisle ordering optimization based on typical store layout (Produce -> Meat -> Bakery -> Dairy -> Frozen).
- **📷 Barcode Scanner & Instant Price Comparison:**
  - Use smartphone camera to scan product UPC barcodes in-store.
  - Instantly reveals whether the product is cheaper at competitor supermarkets nearby.
- **🎙️ Voice Assistant Integration (Siri, Google Assistant, Alexa):**
  - Voice shortcuts: "Hey Siri, add avocados to my AI Helper grocery list."
  - Conversational query: "What deals are running on tri-tip this week?"

#### Phase 6: Multi-Tenant Enterprise & Privacy Sandbox
- **👥 Granular Multi-Tenant Role-Based Access Control:**
  - Expanded permissions matrix: `ADMIN`, `FAMILY_MEMBER`, `KIDS_PROFILE`, and `VIEW_ONLY_GUEST`.
  - Child-safe content filtering and individual calendar isolation.
- **🔑 Enterprise SSO & Identity Provider Integration:**
  - Support for OpenID Connect (OIDC) and SAML 2.0 (Authelia, Authentik, Keycloak, Cloudflare Access).
- **🔒 Zero-Knowledge Hardware & Vault Encryption:**
  - AES-256-GCM encryption for stored IMAP passwords, OAuth refresh tokens, and AI API keys with user-supplied master passphrase or TPM/hardware key.
