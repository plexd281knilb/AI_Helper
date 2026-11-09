# 📖 User Guide: DomsHomeLab (d281knilb) Media Portal, Plex Hub & Libraries

Welcome to **DomsHomeLab (d281knilb)**! This comprehensive guide walks you through monitoring your Plex streams, diagnosing playback issues, testing network speeds, setting up wireless Kindle delivery, reading in-browser with Kindle Paperwhite mode, listening to audiobooks, requesting movies and TV shows, earning referral rewards, and managing your member account.

---

### 📑 Table of Contents
1. [Getting Started, Invitations & Free Trial Passes](#1-getting-started-invitations--free-trial-passes)
2. [My Plex Hub, Stream Diagnostics & Speed Tests](#2-my-plex-hub-stream-diagnostics--speed-tests)
3. [🤖 Plex & Server Master AI Support Assistant](#3-plex--server-master-ai-support-assistant)
4. [Plex Device Setup & Quality Optimization Guides](#4-plex-device-setup--quality-optimization-guides)
5. [Wireless Send-to-Kindle Setup (For E-Readers)](#5-wireless-send-to-kindle-setup-for-e-readers)
6. [Browsing & Accessing Media (Ebooks & Audiobooks)](#6-browsing--accessing-media-ebooks--audiobooks)
7. [In-Browser Kindle Paperwhite & Comic Readers](#7-in-browser-kindle-paperwhite--comic-readers)
8. [🎧 Audiobooks & Spoken Word Media](#8-audiobooks--spoken-word-media)
9. [Requesting New Books & Audiobooks (Unified Discover Hub)](#9-requesting-new-books--audiobooks-unified-discover-hub)
10. [Troubleshooting, Request Tracking & 1-Click Import](#10-troubleshooting-request-tracking--1-click-import)
11. [🎬 Native Movie & TV Show Requests (Seerr Engine & Episode Guides)](#11-native-movie--tv-show-requests-seerr-engine--episode-guides)
12. [🎨 Curation Studio Suite (Kometa, Agregarr, Maintainerr, Tagging)](#12-curation-studio-suite-kometa-agregarr-maintainerr-tagging)
13. [💳 Subscriptions, Payments & Upcoming Member Perks](#13-subscriptions-payments--upcoming-member-perks)
14. [👁️ Admin Tools: Impersonation & Approval Governance](#14-admin-tools-impersonation--approval-governance)
15. [Need Help or Technical Support?](#15-need-help-or-technical-support)

---

## 🚀 1. Getting Started, Invitations & Free Trial Passes

1. Open your web browser and navigate to the DomsHomeLab portal address (e.g. `https://home.yourdomain.com`).
2. Log in using your Username/Email & Password or click **Sign in with Plex**.
3. **New User Invitations (`/join`):**
   - DomsHomeLab is a private, invite-only community. New users can join via a direct referral invite link (e.g. `/join?ref=YOUR_CODE`) or by entering the referral code or username of an existing active member.
   - **Free Trial Pass:** New members receive a complimentary all-access trial pass with **zero payment required up front** to preview movies and TV shows in pristine 4K HDR and 1080p studio master quality on Plex.
   - **Upgrading to Full Membership:** Upgrading unlocks all premium community perks:
     - 🎬 **Unrestricted 4K HDR Direct Play:** Original studio bitrates with zero transcoding lag.
     - 🧒 **Dedicated Kids & Living Room Profiles (Coming Soon):** Child-safe managed accounts with custom PIN protection and age rating filters (currently in active development).
     - 📚 **Full Digital Book & Audiobook Library:** In-browser Kindle Paperwhite reading mode, Plex audiobook library streaming (in-browser floating player coming soon), and wireless Send-to-Kindle delivery.
     - ⚡ **Priority Server Bandwidth:** Dedicated high-priority streaming and transcode allocation.
     - 🎁 **Discord VIP & Referral Rewards (Coming Soon):** Live server downtime alerts, member chat, and upcoming referral reward discounts.
4. Once logged in, your session remains securely active for 30 days with sliding automatic renewal.

---

## 🎬 2. My Plex Hub, Stream Diagnostics & Speed Tests

### 🏷️ Build & Environment Badges
- **Beta Preview (`main` branch)**: Purple pulsing badge (`BETA • v1.3.15`).
- **Production Release (`stable` branch)**: Emerald green badge (`PROD • v1.3.15`).
- **Admin Diagnostics**: Administrators can click the badge to inspect Docker build run numbers, commit SHAs, and GitHub Actions telemetry.


Your personalized **My Plex Hub** dashboard gives you real-time insight into your active streams, server connections, watch statistics, and playback health.

### 🔴 Real-Time Active Stream Monitoring
- **Live Playback Cards:** View everything currently streaming on your account across Smart TVs, Apple TVs, streaming sticks, web browsers, and phones.
- **Playback Telemetry:** See video resolution (4K UHD, 1080p, 720p), video/audio codecs (HEVC, H.264, EAC3, TrueHD Atmos), playback progress, direct stream bitrate, and hardware NVENC acceleration.
- **Direct Play vs. Transcode Indicators:**
  - 🟢 **Direct Play / Direct Stream:** The media is streaming at original pristine quality without taxing server CPU/GPU.
  - 🟡 **Transcoding (Video/Audio/Subtitles):** The server is converting the file on-the-fly to match your player's capabilities or bandwidth limit.

### 🩺 Transcode Doctor
If a stream is transcoding, click **Transcode Doctor** on the playback card:
- **Instant Root-Cause Analysis:** Identifies why transcoding is occurring (e.g. incompatible audio codec like TrueHD 7.1/DTS, burning PGS/VOBSUB image subtitles, client maximum bitrate cap, or remote quality limit).
- **Device-Specific Fixes:** Provides tailored instructions to adjust your Plex client settings to achieve Direct Play.

### ⏹️ Terminating Stuck Playback Sessions (`Stop Stream`)
If a TV app crashed, lost Wi-Fi, or left a "ghost session" running in the background holding server bandwidth:
1. Click the **Stop Stream** (`⏹️`) button on the active playback card.
2. Confirm the prompt to safely terminate the stuck session.
3. *Security Note:* Users are strictly authorized to terminate only their own playback sessions; administrators can manage all active server streams. You can restart playback on your device anytime!

### 🌐 Connected Plex Servers Modal
Click the **Connected Servers** badge in the hub header to view:
- All healthy Plex Media Server instances linked to your ecosystem (e.g. Main Plex Server, 4K UHD Server).
- Server names, active versions, local/public IP addresses, and secure HTTPS connection statuses.

### ⏱️ Personalized Watch Time Analytics
- **Formatted Days & Hours:** Displays your total streaming duration formatted into clean days and hours (e.g. `33 days 4 hrs` rather than confusing raw hour counts).
- **Milestone Counts:** Tracks your total Movies Finished and TV Episodes Watched, synchronized automatically from your watch history.

### ⚡ In-Browser Server Speed Test
Diagnose buffering or stuttering directly from your current viewing device:
1. Click the **Speed Test** (`⚡`) button in My Plex Hub.
2. Click **Start Test** to measure real-time download bandwidth and latency directly between your browser/device and the media server.
3. Use the measured speed to select the ideal streaming quality preset on your player.

---

## 🤖 3. Plex & Server Master AI Support Assistant

Need instant help troubleshooting a playback error on your TV or streaming device? Use the built-in **Plex & Server Master AI Assistant**!

### Key Capabilities & How to Ask:
1. **Live Playback Storage & File Health Probing:**
   - Ask the bot to test any specific movie or episode before you start watching:
     - *"Test to make sure The Sandlot runs on the main Plex server"*
     - *"Can you check if Gladiator is ready to play?"*
     - *"Is Dune available with English audio?"*
   - The AI identifies the target server, locates the title in the Plex database, and executes an **active byte-range disk read test** (`Range: bytes=0-65535`) directly against physical media storage.
   - It reports physical readability, disk latency in milliseconds (e.g. `✅ Streamed 64 KB from storage in 18ms`), container format, English audio streams, and subtitle availability.
2. **Device Buffering & Playback Diagnostics:**
   - Type your question or paste the exact error message (e.g. *"not enough bandwidth for any playback of this item. can not convert to below minimum bandwidth"* or *"why is my Roku buffering on 4K?"*).
   - The AI analyzes your active stream telemetry, client player profile, and known platform bugs to provide step-by-step resolution steps tailored to your TV model.
3. **Automated Audio Language Replacement:**
   - If a movie or episode is missing English audio (e.g. Spanish-only release), tell the bot: *"The Sandlot only has Spanish audio"*.
   - The AI inspects the media streams, verifies the absence of English audio, queries connected indexers (Radarr/Sonarr) for an English replacement release, and automatically grabs a verified candidate (or confirms if your existing file already meets the highest Custom Format score).
4. **Personalized Book & Media Recommendations (`📚 Book Recommendations`):**
   - Click the **`📚 Book Recommendations`** quick-chip or ask *"What books should I read next?"*.
   - The AI analyzes your past requests, Kindle deliveries, and genre preferences to recommend tailored titles, distinguishing between books ready to read right now in `/library` and 1-click auto-grab titles in `/requests`.
5. **Admin Homelab Command Center (Administrators Only):**
   - Administrators see dedicated quick-chips (`🐳 Docker Fleet`, `🖥️ Host Hardware`, `🚨 Sharing Alerts`) to inspect Glances CPU/RAM metrics, check or restart Docker containers, and audit multi-IP household sharing alerts directly in chat.
6. **1-Click Ticket Escalation:**
   - If an issue requires administrator intervention, click **Open Ticket With This Diagnosis** to submit a support ticket pre-populated with the AI's diagnostic snapshot!

---

## 📱 4. Plex Device Setup & Quality Optimization Guides

To eliminate buffering and enjoy maximum 4K HDR and 1080p video quality, configure your Plex client apps using our built-in interactive guides:

1. Click **Setup Guides** (`📖`) in the My Plex Hub header (or visit `/guides`).
2. Select your streaming platform:
   - 🍏 **Apple TV:** Enable Direct Play, set Home & Remote Streaming to *Maximum/Original*, and enable Match Dynamic Range & Frame Rate.
   - 📺 **Roku:** Set Video Quality to *Original*, configure Audio to *Passthrough*, and enable Burn Subtitles *Automatic / Only Image Formats*.
   - 🔥 **Amazon Fire TV / Fire Stick:** Enable hardware acceleration, set Remote Streaming to *Maximum*, and set Subtitle Burn to *Automatic*.
   - 🤖 **Android TV / Google TV / Nvidia Shield:** Enable Refresh Rate Switching, set Remote Quality to *Original*, and enable Audio Passthrough (HDMI).
   - 📱 **Smart TVs (LG webOS / Samsung Tizen):** Disable *Auto Quality Adjust*, set Local and Remote Quality to *Original*, and avoid PGS subtitles if unsupported.
   - 💻 **Web Browsers & Mobile (iOS / Android):** Use the official Plex Desktop app or native mobile apps for direct codec support.
3. **Interactive In-App Feature Guide Modal:** Click the **`📖 Feature Guide`** button available across app pages to open full interactive walk-throughs for all features without leaving your current view.

---

## 📱 5. Wireless Send-to-Kindle Setup (For E-Readers)

When you first visit the Library, you will be prompted to set up Send-to-Kindle for 1-click Wireless Ebook Delivery.

### Step 1: Find your Kindle Email
1. Log into your Amazon account and go to **Account & Lists > Content & Devices**.
2. Click the **Preferences** tab at the top.
3. Scroll down and click **Personal Document Settings**.
4. Look under **Send-to-Kindle E-mail Settings** to find your e-reader's email address (usually ends in `@kindle.com`).

### Step 2: Authorize DomsHomeLab's Sender Email
Amazon requires all senders to be approved before emails can reach your Kindle:
1. Under *Personal Document Settings*, scroll to **Approved Personal Document E-mail List**.
2. Click **Add a new approved e-mail address**.
3. Add **`kindle@domshomelab.com`** (or the server sender address displayed in your Kindle Setup prompt).

### Step 3: Save & Test
- Enter your Kindle email and click **Save Email & Unlock Automatic Delivery**.
- Click **Run Pre-Flight Delivery Check** to test your configuration before sending your first book!
- **⚡ Automatic Delivery on Request:** Whenever you request an ebook in Discover, DomsHomeLab automatically emails the clean EPUB directly to your Kindle as soon as the download finishes!
- **📋 Outbound Delivery Logs & Retries:** Inspect previous Kindle email dispatches in the Kindle Delivery History panel, and retry any failed dispatches with 1 click.
- *Don't have a Kindle or want to download files manually?* Click **Skip for Now & Browse Library**. You can update this anytime by clicking the **Kindle** tab in `/library`.

---

## 📚 6. Browsing & Accessing Media (Ebooks & Audiobooks)

DomsHomeLab organizes your reading and listening collection into dedicated tabs:

### 📖 Ebooks Tab
- **Browse & Search:** Filter by library shelves, search by title or author, and sort by date or title.
- **Series Grouping:** Toggle *Group by Series* to view books neatly organized by their book series with volume numbers.
- **🔍 Show Missing Books:** Click **Show Missing Books** on any series group to discover unacquired books in that series, sorted chronologically and sequentially by volume number (`Vol 1`, `Vol 2`, `Vol 3`...) with knockoff study guides and summary publishers automatically filtered out.
- **⚡ 1-Click Auto-Grab:** In the Missing Books view, click **Auto-Grab** on any missing installment (or grab the entire series) to immediately auto-request and download it.
- **🌫️ Missing Book Cards:** Missing books display on your shelf with a grayscale poster, "MISSING" badge, and 0 MB indicator. You can click **Re-Grab Release** directly from the book card modal to search indexers anytime.
- **1-Click Kindle Send (`📧`):** Click the Kindle button on any book card to wirelessly dispatch the standardized EPUB file directly to your e-reader.
- **Format Standardization:** Non-EPUB files (MOBI, AZW3, PDF) are automatically converted to clean EPUBs via background conversion (`ebook-convert`), and redundant legacy formats are pruned to save disk space.
- **Direct Download (`⬇️`):** Click the Download button to download EPUB or PDF files directly to your phone, tablet, or computer.
- **Interactive Metadata Matcher (`BookMatchModal`):** For unlinked or manually uploaded books, click the Match button to run the interactive matcher. It scores suggestions against local database relations, Audible, iTunes, and Google Books with AI fallback, allowing 1-click field updates, volume linking, cover fetching, and disk reorganization.

---

## 📖 7. In-Browser Kindle Paperwhite & Comic Readers

DomsHomeLab includes high-performance in-browser readers for all major book and comic formats—no third-party apps required.

### 📖 Kindle Paperwhite EPUB Reader
Click **`Read`** or **`Resume (X%)`** on any EPUB book card to launch the reader:
- **Instant 0ms Reopening:** Uses browser CacheStorage (`portalarr-books-v1`) to cache downloaded books for instant offline reopening without waiting on network transfers.
- **Fast Reading Percentage & Progress Bar:** Real-time accurate percentage calculations shown directly on library cards and in the reader.
- **Estimated Reading Time:**
  - *"X mins left in chapter"*
  - *"Y hrs Z mins left in book"* (calibrated to a standard 220 WPM reading rate).
- **Tappable Kindle Status Footer:** Tap the bottom footer bar to cycle between:
  `Time Left in Book` ↔ `Time Left in Chapter` ↔ `Page in Book` ↔ `Location` ↔ `Percentage`
- **Kindle `Aa` Typography Customization:**
  - **Typefaces:** Bookerly (Kindle Serif), Ember (Kindle Sans-Serif), and System Monospace.
  - **Font Size:** Stepped adjustment from 70% to 200%.
  - **Margins:** Narrow, Normal, or Wide page gutters.
  - **Line Height:** Compact, Normal, or Relaxed line spacing.
  - **Themes:** Dark (Night Mode), Sepia (Warm Paper), or Light (Daylight).
- **Distraction-Free Reading:** Tap the center of the page to auto-hide toolbars. A discrete corner badge continues to show your active reading metric.
- **Reading Progress Persistence:** Automatically bookmarks your position and displays a **`Resume (X%)`** amber badge on library cards.

### 🦸 Comic Book Reader (`.cbr`, `.cbz`, & Folder Archives)
- **Zero-Conversion Streaming:** Streams compressed archive pages on-the-fly via WebAssembly `unrar` and `JSZip`.
- **Display Modes:** Toggle between Fit-to-Width, Fit-to-Height, and Original resolution.
- **Navigation:** Use keyboard arrow keys, spacebar, on-screen arrows, or the bottom thumbnail scrubber to quickly jump between pages.
- **Page Position Memory:** Automatically resumes at the exact page you last viewed.

### 📄 PDF Document Viewer
- Embedded inline PDF rendering with zoom controls, page jumping, and direct download capabilities.

---

## 🎧 8. Audiobooks & Spoken Word Media

DomsHomeLab organizes and streams your spoken word audiobooks across your media ecosystem:

- **Plex & Spoken Word Streaming:** Listen directly on Plex mobile apps, desktop players, and home audio devices with full resume state and track position tracking.
- **Unified Cataloging & Chapter Inspection:** Folder structures with chapter tracks (`01 Intro.mp3`, `02 Chapter 1.mp3`) or multi-disc subdirectories (`Disc 01/`, `Disc 02/`) are automatically merged into a single audiobook entry displaying total duration and consolidated size.
- **Interactive Chapter Selector:** Click **Listen & Chapters** on any audiobook card to open the Chapter Selector Modal, inspect chapters, or view file details.
- **Reorder & Edit Chapters:** Click **✏️ Reorder & Edit Chapters** in the Chapter Selector Modal to change chapter numbers or click ⬆️ / ⬇️ buttons. Click **Save** to rename track files on disk so your custom order is permanent for all users!
- **✨ AI Chapter Track Analysis:** Click **Analyze with AI** to automatically inspect raw audio tracks, infer official chapter boundaries and titles, and auto-populate metadata.
- **🎵 Persistent Floating Web Audio Player (Coming Soon):** *(Upcoming Feature — Currently in Development)* Pinned browser audio player with continuous autoplay, playback speed memory (1.0x, 1.25x, 1.5x, 2.0x), and background tab playback.

---

## 🔍 9. Requesting New Books & Audiobooks (Unified Discover Hub)

Requesting books and audiobooks is fully integrated into the unified **Discover (`/discover`)** and **Requests (`/requests`)** hub:

### Step 1: Open Discover (`/discover`)
- Navigate to the **Discover** page from the sidebar or header.
- Browse the dedicated **Popular Books**, **Trending Books**, **Trending Audiobooks**, and **"Missing from Your Series"** carousels.

### Step 2: Search & Auto-Complete
- Type any **Title**, **Author**, or **Series** in the global search bar.
- Real-time suggestions appear with cover art, release year, author name, and format badges (**`📖 Ebook`** vs **`🎧 Audiobook`**).

### Step 3: Interactive Detail View & 1-Click Request
1. Click on any book to open the comprehensive **Book Detail Modal**.
2. View synopsis, publisher, publication date, series reading order, and similar book recommendations.
3. Click **`📖 Request Ebook`** or **`🎧 Request Audiobook`**.
4. **Instant Auto-Approval:** All book requests are automatically approved and dispatched to indexers immediately.

### Step 4: Author & Series Bibliographies
- Click on any author's name to open the **Author Detail Modal** showing their full published bibliography.
- Click on any series title to open the **Series Detail Modal** displaying all installments in chronological reading order with 1-click grab buttons for missing volumes.

### Step 5: Automatic Send-to-Kindle Delivery
- When an ebook request finishes downloading, DomsHomeLab automatically sends the clean EPUB directly to your Kindle if you have configured your Kindle email address!

---

## 🛠️ 10. Troubleshooting, Request Tracking & 1-Click Import

- 🔄 **User Scan Folder:** All approved users can click **Scan Share Folder** or **Scan Audio Folder** directly on library shelves in `/library` to instantly scan folders for new files without needing admin intervention.
- 🖼️ **Fetch Cover (`🖼️`):** Click the Fetch Cover button on any library card to query iTunes HD (600x900), OpenLibrary, and Google Books to refresh low-resolution or missing covers.

### 📨 Tracking Requests in `/requests`
- Visit the **Requests** page (`/requests`) to monitor active book, audiobook, movie, and TV downloads with real-time download speed, progress bars, and ETA.
- **Statuses:** Approved → Searching → Downloading → Available / Downloaded.

### 🔍 Manual Release Search (`Search Release`)
1. On any request card in `/requests`, click **`🔍 Search Release`**.
2. DomsHomeLab queries connected torrent and Usenet/NZB indexers and opens an **Interactive Release Chooser Modal**.
3. Browse available releases showing title, size, format, protocol (Torrent vs Usenet), seeders, and age.
4. Click **Push Release** (`📥`) to dispatch that exact release to your download client.

### 🚫 Permanent Release Blocklisting
- Corrupted, password-protected, foreign-language, or mismatched releases are automatically recorded to the blocklist database (`FailedRelease`).
- Subsequent auto-searches skip these releases automatically, and they are marked with a **`🚫 Blocklisted Release`** badge in the Interactive Release Chooser.

### 📥 1-Click Download Import (`Import Download`)
- If SABnzbd or qBittorrent finished downloading a file but it hasn't appeared on your shelf yet, click **`📥 Import Download`** in `/requests`. The system will scan all completed download directories, copy the files to your shelf, auto-consolidate multi-track audiobooks, and mark the status as `Downloaded`.

### 🔄 Retrying Failed Downloads (`Auto-Retry`)
- If a request shows `Failed` or `Failed (Missing)`, click **Auto-Retry** in `/requests` to trigger an immediate automated background search using multi-tier fallback queries.

---

## 🎬 11. Native Movie & TV Show Requests (Seerr Engine & Episode Guides)

DomsHomeLab includes a built-in media discovery and request engine directly connected with TMDb, Plex, Radarr, and Sonarr!

### 🌟 Discovering Trending & Recommended Media (`/discover`)
- **Interactive Carousels:** Browse Trending Movies, Trending TV Shows, Upcoming Releases, and Popular Titles with real-time availability badges (`Available`, `Partially Available`, `Requested`, `Monitored`).
- **Live Search & Autocomplete:** Search for any movie, TV series, actor, director, or studio with instant keyboard navigation.
- **Media Detail Modals:** Click any title to view high-definition artwork, overview, runtime, genres, trailers, cast/crew directory, ratings, and recommendations.

### 📥 Requesting Movies & TV Shows
- **1-Click Movie Requests:** Click **Request** to dispatch the movie directly to Radarr. If 4K is configured and permitted on your account, toggle between standard 1080p and dedicated 4K UHD quality.
- **TV Series & Granular Season/Episode Requests:**
  - **Full Series:** Request all past, present, and future seasons with one click.
  - **Specific Seasons:** Pick and choose exact seasons using the interactive season grid.
  - **Episode-Level Monitoring:** Expand any season to view episode thumbnails, titles, air dates, and individual episode monitoring switches (`Monitored` vs `Unmonitored`).
- **Deep Episode Sync:** If a series is already partially monitored in Sonarr, requesting newly selected episodes dynamically updates Sonarr via `PUT /api/v3/episode/monitor` and immediately triggers an automatic `EpisodeSearch` command.
- **Quota Management:** Enforces user-specific weekly/daily movie and TV request quotas.

### 🔔 Live Discord & Email Notifications
- **Discord Webhook Alerts:** When a request is submitted, approved, or downloaded, rich Discord embed cards are automatically dispatched with color coding (🟡 Pending, 🟢 Approved/Available, 🔴 Declined/Failed), media poster thumbnails, format tags (`4K UHD` vs `1080p`), and requesting user details.
- **Styled HTML Email Notifications:** Administrators receive instant email updates with direct links to approve or manage requests.

---

## 🎨 12. Curation Studio Suite (Kometa, Agregarr, Maintainerr, Tagging & Zero-Lock SQLite Engine)

Administrators can curate Plex libraries natively without external scripts or extra docker containers via the **Curation Studio (`/curation`)**:

- **⚡ Direct Plex SQLite Snapshot & Delta-Sync Engine (Zero PMS Lock Architecture):** High-speed, lock-free SQLite snapshot subsystem (`plex-snapshot-engine.ts`) that creates atomic WAL snapshots of local Plex databases (`com.plexapp.plugins.library.db`) and runs multi-database queries in `<20ms` via native `node:sqlite`. Compares items against Portalarr's target state and strictly restricts HTTP mutations to genuine deltas—preventing Plex 500 errors or SQLite lockups during heavy sweeps.
- **✨ Kometa Overlays Studio:** Apply high-definition ribbons, 4K HDR badges, Dolby Vision/Atmos labels, audio codecs, and custom user overlays to movie and TV posters with live canvas previews and hardware-accelerated SVG-to-JPEG rendering *(Note: Dynamic badges on member media cards are an upcoming feature currently in admin preview)*.
- **🎬 Agregarr Hubs:** Generate dynamic trending hubs, smart collections, placeholder stubs for missing items, and discovery rows linked directly with Trakt, TMDb, MDBList, Letterboxd, MyAnimeList, and IMDb charts across multi-Plex clusters with per-endpoint `machineIdentifier` verification.
- **🧹 Maintainerr Prune:** Set disk quota rules, identify unwatched media using a 3-tier watch status engine (local `WatchHistory` `<1ms` lookup + batch session check), and safely prune media to recover storage automatically with Leaving Soon staging collections and poster countdown badges.
- **🏷️ Parental Guide & Tagging Studio:** Tag movies, shows, and parental guide labels across Plex libraries with IMDb / Common Sense Media content advisory severity ratings (`Violence`, `Sex/Nudity`, `Profanity`, `Alcohol/Drugs`, `Frightening`) to power user-level customizable shelf filters.

---

## 💳 13. Subscriptions, Payments & Upcoming Member Perks

### 📅 Flexible Membership Plans
When upgrading from your free trial pass to full membership, choose the cadence that fits you best:
- **Flexible Monthly Plan ($17.50/month):** Pay-as-you-go month-to-month access. Cancel or resume at any time with zero long-term commitment.
- **Rest-of-Year Annual Pass ($180/year — Best Value):** Derived from the $15/month base rate ($180/year). You only pay for the remaining calendar days and full months in the current year, then renew on January 1st:
  - Prorated first month: `(remaining days / total days in month) * $15`
  - Remaining months: `remaining full months * $15`
  - *Example:* Upgrading on October 10th covers 21 days in October ($10.16) + November ($15) + December ($15) = **$40.16** for the remainder of the year.

### 🎁 Member Referral Rewards (Coming Soon)
*(Upcoming Feature — Currently in Development)*
- Invite your friends to join DomsHomeLab using your personal invite link (`/join?ref=YOUR_CODE`).
- When an invited friend joins and becomes an active member:
  - **Annual Subscribers:** Earn **$15.00 off** your next annual renewal (e.g. $180 - $15 = **$165.00** with 1 referral; $180 - $30 = **$150.00** with 2 referrals; 12 referrals makes the entire upcoming year **100% FREE**).
  - **Monthly Subscribers:** Your monthly billing is delayed by **+1 full month** per friend (e.g. pushes billing start from January 1 to February 1).

### 💳 Zero-Fee P2P Payments & Automated Receipts
- **P2P Direct Methods:** Renew seamlessly via Venmo, PayPal, or Zelle with zero gateway fees.
- **Pre-Filled Memo Notes & QR Codes:** Use the interactive QR code modal on the dashboard, `/profile`, or `/join` to prefill your exact payment memo (your clean username, e.g. `dominicjuliano`) for automated IMAP reconciliation.
- **Instant Payment Receipts:** Whenever your payment is processed, DomsHomeLab automatically dispatches a branded HTML payment confirmation receipt (`payment_received`) confirming the amount received, date, new expiration date, and active perks.
- **Full Membership Activation Alerts:** Upgrading from trial to full membership dispatches a welcome email (`subscription_activated`) highlighting all unlocked features.

### 🧒 Family Sub-Profiles (Kids & Living Room TV) (Coming Soon)
*(Upcoming Feature — Currently in Development)*
- **Living Room TV Profiles:** Managed profiles configured with content safety tags to filter out explicit content for family viewing areas.
- **Kids Profiles:** Curated child-safe profiles locked strictly to G and PG-rated movies and TV animations with optional PIN protection.
- *Access Security:* Trial accounts are strictly restricted to primary server libraries; Kids and backup servers remain isolated until upgrading to full membership.

---

## 👁️ 14. Admin Mission Control: Monitoring, Scripts, Telemetry & Governance

Administrators have a unified suite of homelab management, observability, and safety tools:

### 🐳 System & Docker Fleet Monitoring Cockpit (`/admin/monitoring`)
- **Systems & Services Health:** Live reachability, round-trip latency (ms), 24h/7d/30d rolling uptime percentages, streak counters, and 10-probe latency sparklines across Plex Media Servers, Glances hosts, Tautulli, Servarr apps, and Downloaders.
- **Docker Container Fleet Manager:** Multi-engine Docker integration (Unix socket, Windows named pipe, Docker CLI, Glances containers API, and TCP 2375) with multi-core CPU heat meters (`Flame` indicators & core usage estimates), RAM gauges, host filtering, and 1-click **Restart**, **Start**, and **Stop** controls.
- **Outages & Incident Alerts:** Chronological outage log with failure causes, downtime durations, and automated Discord embeds dispatched to `#system-status`.

### 📜 Homelab Shell Automation & User Scripts (`/admin/scripts`)
- **Unraid-Style Script Engine:** Execute, schedule, and edit maintenance scripts (`bash`, `sh`, `python3`, `node`) with pre-seeded jobs (`check_all_plex_servers.sh`, `optimize_plex_databases.sh`, `backup_portalarr_db.sh`, `restart_unresponsive_containers.sh`).
- **Live Streaming Terminal Modal:** Real-time `ReadableStream` stdout/stderr execution logs with instant abort-on-close lifecycle safety and downloadable execution history.

### 📊 Stream Intelligence Hub & Multi-IP Sharing Detection (`/admin/tautulli`)
- **Native Telemetry Takeover:** Built-in `WatchHistory` engine that tracks movies and episodes directly from your Plex cluster, plus a 100% **Complete Historical Tautulli Backfill Runner**.
- **Concurrent Multi-IP Password Sharing Detection:** Automatically distinguishes household LAN streams from simultaneous streams across $\ge 2$ distinct public WAN IP addresses, flagging violations and logging security audits.
- **User Connection & Device Intelligence Modal:** Click any user to inspect their full chronological watch history, client devices, direct play vs. transcode ratios, and IP locations.

### 🏷️ Dynamic Branch, Version & Build Badge (`BuildBadge`)
- **Instant Environment Identification:** Displays a glowing **BETA (`main`)** or **PROD (`stable`)** badge in the sidebar and dashboard with active version (`v1.3.15`), short git commit SHA, and GitHub Actions build run number. Clicking opens the Build Diagnostics dialog with 1-click SHA copy and workflow links.

### 👁️ View Site As User (Impersonation)
1. Navigate to **System Settings** → **Access Control** (`/settings/access`).
2. On any user's card in the User Directory, click **`👁️ View As`**.
3. Confirm the prompt to switch your active session to that user.
4. While impersonating, a prominent sticky warning banner appears across all pages: `Viewing site as [Username] ([ROLE])`.
5. To exit and return to your Admin account, click **`Return to Admin`** on the top banner anytime.

### 🛡️ Action Approval Gates & Governance
When `requireApprovalForPlexChanges` or `requireApprovalForEmails` switches are active in System Settings:
1. Critical actions (such as user account permission adjustments, library sharing edits, or bulk notification emails) are staged in the **Admin Approval Queue (`/admin/approvals`)**.
2. Administrators can review, batch-approve, or reject staged modifications with full audit history before they are executed live on Plex or dispatched via SMTP.

---

## ❓ 15. Need Help or Technical Support?

If a stream won't play, a book download fails, or you need server assistance:
1. **Try the AI Support Bot:** Ask questions in the floating AI Assistant on My Plex Hub for instant storage diagnostics and stream fixes.
2. **Submit a Ticket:** Click the **Support** (`💬`) icon in the navigation bar to submit a ticket detailing the issue.
3. You will receive email updates as the administrator investigates and resolves your request.

*Happy Streaming, Reading & Listening!* 🎬📖🎧
