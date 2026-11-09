# 📖 DomsHomeLab (d281knilb) Ebooks & Audiobooks User Guide

Welcome to the comprehensive user guide for **DomsHomeLab's (d281knilb) Ebooks and Audiobooks** ecosystem! This document explains all features available in the library, in-browser readers, Send-to-Kindle delivery, audio chapter management, media requests, series tracking, and indexer integration.

---

### 📑 Table of Contents
1. [Getting Started & Navigation](#1-getting-started--navigation)
2. [Ebook & Comic In-Browser Reading](#2-ebook--comic-in-browser-reading)
3. [Send-to-Kindle Wireless Delivery & Failure Diagnostics](#3-send-to-kindle-wireless-delivery--failure-diagnostics)
4. [Audiobooks & Plex Streaming](#4-audiobooks--plex-streaming)
5. [Chapter Management & Track Reordering on Disk](#5-chapter-management--track-reordering-on-disk)
6. [Discovering & Requesting Books (The Unified Hub)](#6-discovering--requesting-books-the-unified-hub)
7. [Series Tracking, Missing Books & 1-Click Auto-Grab](#7-series-tracking-missing-books--1-click-auto-grab)
8. [Interactive Ingest & Unlinked Series Matcher](#8-interactive-ingest--unlinked-series-matcher)
9. [Request Tracking, Release Selection & 1-Click Import](#9-request-tracking-release-selection--1-click-import)
10. [AI Metadata Agent, Cover Artwork Engine & Personalized Book Recommendations](#10-ai-metadata-agent-cover-artwork-engine--personalized-book-recommendations)
11. [Frequently Asked Questions (FAQ)](#11-frequently-asked-questions-faq)

---

## 🚀 1. Getting Started & Navigation

DomsHomeLab offers dedicated views for your digital reading and listening collection:
- **📖 Ebooks Shelf (`/library`):** Browse clean, standardized EPUB, PDF, and comic files across public and user-restricted shelves with series grouping and quick filters.
- **🎧 Audiobooks Shelf (`/library`):** Browse single-file and multi-track audiobooks with duration stats, cover art, chapter track listings, and Plex library streaming.
- **🔍 Media Discovery Hub (`/discover`):** Unified discovery center for trending books, popular audiobooks, author bibliographies, and missing series installments with 1-click request buttons.
- **📨 Request Manager (`/requests`):** Track all active book and audiobook grabs with real-time download progress, release selection, retry tools, and completed download imports alongside movies and TV shows.
- **⚙️ Kindle Settings Tab (`/library`):** Configure your Send-to-Kindle email, enable automatic delivery on download completion, run pre-flight diagnostics, and view outbound delivery transaction logs.
- **📚 Manage Shelves Tab (`/library` - Admins):** Create and manage custom public or user-restricted library shelves with granular user access rules.
- **❓ Help & Guide Tab (`/library`):** This in-app guide, keeping you up-to-date with all the latest features.

> 💡 **Full Membership Perk:** The digital Ebook & Audiobook Library is an exclusive perk of Full Membership. While free trial passes provide full movie and TV streaming on Plex, upgrading to full membership unlocks our complete digital book library, wireless Send-to-Kindle delivery, Plex audiobook streaming, and 1-click book requests!

---

## 📱 2. Ebook & Comic In-Browser Reading

DomsHomeLab includes high-performance in-browser readers for all major book and comic formats—no third-party apps required.

### 📖 Kindle-Style EPUB Reader
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

## 📧 3. Send-to-Kindle Wireless Delivery & Failure Diagnostics

Send books wirelessly to your Kindle e-reader in seconds with end-to-end delivery tracking, automated diagnostics, and automatic request dispatch:

### ⚡ Automatic Delivery upon Request Completion
- When you request an ebook in **`/discover`** or **`/requests`**, DomsHomeLab automatically checks if you have configured a Kindle email address.
- As soon as the download finishes and is organized into your library, **the book is automatically emailed directly to your Kindle**! No manual clicking required.

### 📱 EPUB-Only Amazon Delivery Standard
- Amazon officially discontinued `.mobi` and `.azw` file delivery for Send-to-Kindle.
- DomsHomeLab automatically verifies and standardizes all ebook files to clean **EPUB format** (<50MB, valid EPUB ZIP magic bytes, sanitized ASCII filename) so files deliver flawlessly every time.

### Step 1: Find your Kindle Email
- On Amazon, go to *Account & Lists* > *Content & Devices* > *Preferences* > *Personal Document Settings*.
- Copy your Kindle email address (ends in `@kindle.com`).

### Step 2: Authorize DomsHomeLab's Sender Email
- Under *Approved Personal Document E-mail List*, click *Add a new approved e-mail address*.
- Add your server's SMTP sender address (displayed in the Kindle Setup tab).

### Step 3: 1-Click Manual Dispatch
- Click the **`📧 Send to Kindle`** icon on any book card in `/library` to dispatch the book immediately.

### 🩺 Kindle Pre-Flight Diagnostics Check
- Navigate to the **Kindle Settings** tab in `/library` and click **`Run Pre-Flight Delivery Check`**.
- The system runs live checks across your SMTP configuration, sender address authorization, Kindle email syntax, and ebook storage limits.

### 📋 Outbound Delivery History & Error Tracker
- All outbound deliveries are logged in the **Kindle Delivery History** panel with timestamps, recipient emails, file formats, and file sizes.
- **Status Indicators:**
  - 🟢 **`DELIVERED`**: The file was accepted by the SMTP mail relay and dispatched to Amazon.
  - 🔴 **`DELIVERY FAILED`**: Displays the exact failure cause (e.g. unwhitelisted sender, file size over 50MB, or network timeout) along with actionable troubleshooting tips.
- **1-Click Retry (`RotateCcw`):** Click **`Retry Delivery`** on any failed log entry to re-attempt sending once the issue has been resolved.

---

## 🎧 4. Audiobooks & Plex Streaming

DomsHomeLab provides full audiobook support across Plex and your connected players:

- **Plex Audiobook Streaming:** Stream audiobooks with chapter memory and progress tracking on any device using the Plex app, Plexamp, or Prologue.
- **Multi-Disc & Multi-Track Auto-Consolidation:** Folder structures with chapter tracks (`01 Intro.mp3`, `02 Chapter 1.mp3`) or multi-disc subdirectories (`Disc 01/`, `Disc 02/`) are automatically merged into a single audiobook card displaying total duration and consolidated size.
- **Interactive Chapter Inspection:** Click **Listen & Chapters** on any audiobook card to view chapter lists, track lengths, and file details.
- **🎵 Persistent Floating Web Audio Player (Coming Soon):** *(Upcoming Feature — Currently in Development)* Pinned browser audio player with continuous autoplay, playback speed memory (1.0x, 1.25x, 1.5x, 2.0x), and background tab playback.

---

## 🎼 5. Chapter Management & Track Reordering on Disk

Need to correct chapter numbers or track ordering?

1. Click **`Listen & Chapters`** on any audiobook card to open the Chapter Selector Modal.
2. Click **`✏️ Reorder & Edit Chapters`**.
3. Use the **`⬆️ Up`** / **`⬇️ Down`** buttons or type custom chapter numbers to rearrange tracks.
4. Click **`Save Order`**. DomsHomeLab physically renames and synchronizes track files on disk (`reorderAudiobookChapters`) so the new order is permanent for all users across the server!
5. **✨ AI Chapter Track Analysis:** Click **`Analyze with AI`** to have the AI agent automatically inspect raw track names, infer official chapter splits, and populate canonical chapter titles.

---

## 🔍 6. Discovering & Requesting Books (The Unified Hub)

Requesting books and audiobooks is fully integrated into the unified **Discover (`/discover`)** and **Requests (`/requests`)** experience:

### 🌟 Discover Hub (`/discover`)
- **Popular & Trending Carousels:** Browse trending books and audiobooks alongside movies and TV shows, with high-definition artwork, author credits, and genre tags.
- **"Missing from Your Series" Carousel:** Automatically scans your existing book library and highlights the next unacquired installments in series you already follow!
- **Global Search with Autocomplete:** Type any book title, author, or series name into the search bar. Real-time autocomplete queries Audible, iTunes, OpenLibrary, and Google Books simultaneously with format badges (**`📖 Ebook`** vs **`🎧 Audiobook`**).

### 📖 Interactive Book Detail Modal
Click any book in Discover or search results to open the comprehensive detail view:
- **Synopsis & Metadata:** Read the full publisher synopsis, view publication year, page count, and series volume numbers.
- **Author & Series Links:** Click the author's name to view their complete bibliography, or click the series title to view all installments in chronological reading order.
- **Similar Books Carousel:** Browse algorithmically recommended similar books directly inside the modal with 1-click exploration.
- **1-Click Request Buttons:** Prominent **`📖 Request Ebook`** and **`🎧 Request Audiobook`** buttons dispatch the request instantly.
- **Auto-Approval:** All book requests are automatically approved and dispatched to background download indexers immediately.

### 👤 Author & Series Catalogs
- **Author Detail Modal (`AuthorDetailModal`):** Browse the author's complete catalog of published books, audiobooks, and series.
- **Series Detail Modal (`SeriesDetailModal`):** See every volume in the series numbered sequentially (`Vol 1`, `Vol 2`, `Vol 3`...) with instant 1-click grab buttons for missing installments.

### 🏷️ Tier 1 Request-First Metadata Binding
- When you submit a request, its canonical metadata (`title`, `author`, `series`, `volumeNumber`, `coverUrl`) is locked in the SQLite database relations (`Author` and `BookSeries`).
- When the file downloads, DomsHomeLab binds the downloaded media directly to these relations, ensuring clean on-disk organization (`Author / Series / Title`) without messy guessing or folder misidentification.

### 🔄 Non-EPUB to EPUB Standardized Conversion
- When downloads complete, non-EPUB files (MOBI, AZW3, PDF) are automatically converted into standardized, clean EPUB format via background conversion engines (`ebook-convert`).
- Redundant legacy files (`.mobi`, `.azw3`) are safely cleaned up from disk once the EPUB version is verified, keeping your storage optimized and 100% Kindle-compatible.

---

## 📚 7. Series Tracking, Missing Books & 1-Click Auto-Grab

DomsHomeLab tracks book series and helps you complete your collections:

- **Group by Series:** Check the *Group by Series* toggle on any library shelf in `/library` to organize books sequentially by series name and volume number.
- **📡 Auto-Monitor Series:** Click the **`Monitor Series` (`Zap`)** button on any series card. Background schedulers automatically check book registries for new installments and queue downloads as soon as they become available.
- **🔍 Show Missing Books:** Click *Show Missing Books* on any series card to automatically scan iTunes, OpenLibrary, and Google Books for unacquired installments. Results are sorted strictly by volume (`Vol 1`, `Vol 2`, `Vol 3`...) with knockoff study guides, summary publishers, and foreign translations filtered out.
- **⚡ 1-Click Auto-Grab:** Click **`Auto-Grab`** on individual missing installments (or **`Grab All Missing`**) to automatically search indexers and download them. Discovered missing books also appear in the Discover hub's *"Missing from Your Series"* carousel.
- **Missing Book Stubs:** Missing books appear on your shelf as grayscale cards with a `MISSING` badge and `.portalarr-missing` immunity markers. When the real file is downloaded, the stub is automatically replaced.

---

## 🧩 8. Interactive Ingest & Unlinked Series Matcher

Have unlinked files or manually uploaded books?
- **Interactive Matcher (`BookMatchModal`):** Radarr/Sonarr-style interactive matcher that non-destructively inspects file metadata and presents candidate suggestions with confidence scoring.
- **Multi-Source Registries:** Pulls suggestions from the local database relations (`Author`/`BookSeries`), OpenLibrary, Audible, Google Books, and AI agent fallback.
- **Customization:** Allows manual field overrides, volume linking, high-definition cover selection, optional disk restructuring (`renameBookFileOnDisk`), and automatic request state reconciliation (`Downloaded` / `AVAILABLE`).

---

## ⚙️ 9. Request Tracking, Release Selection & 1-Click Import

All active and historical media requests (Ebooks, Audiobooks, Movies, TV) are tracked in the unified **Requests Manager (`/requests`)**:

### Pipeline Status Lifecycle
- ⏳ **Approved:** Request is auto-approved and queued for background processing.
- 🔍 **Searching:** Multi-tier search engine is querying connected Prowlarr indexers for the best quality release.
- 📥 **Downloading:** Download active in SABnzbd or qBittorrent with real-time download progress and ETA.
- ✅ **Downloaded / Available:** Download complete! The book is organized into your library shelf and automatically delivered to your Kindle (if configured).
- ❌ **Failed:** If a grab fails, actionable retry and release search buttons are displayed.

### Interactive Release Chooser
- If an automatic grab picks the wrong release or you want to choose a specific release group, click **`🔍 Search Release`** on any request card in `/requests`.
- Filter and review all available indexer releases with file size, protocol (Torrent vs Usenet), seeders, age, and format tags.
- Click **`Grab` (`📥`)** to dispatch that exact release to your download client.

### 🚫 Permanent Release Blocklisting
- Corrupted, password-protected, foreign-language, or mismatched releases are automatically recorded to the blocklist database (`FailedRelease`).
- Subsequent auto-searches skip these releases automatically, and they are marked with a **`🚫 Blocklisted Release`** badge in the Interactive Release Chooser.

### 📥 1-Click Download Import (`Import Download`)
- If a download completes in SABnzbd/qBittorrent but wasn't automatically organized, click **`📥 Import Download`** in `/requests`.
- DomsHomeLab scans completed download folders, matches the media, moves it into your library, and updates the database record to `Downloaded`.

---

## 🤖 10. AI Metadata Agent, Cover Artwork Engine & Personalized Book Recommendations

- **3-Tier Cover Artwork Engine & Universal SVG Proxy (`/api/cover`):** Automatically queries iTunes HD (600x900), OpenLibrary, and Google Books, backed by a dynamic SVG cover generator (`/api/cover`) so every book and audiobook renders a crisp cover without broken image icons. Click the **`🖼️ Fetch Cover`** button on any card to refresh missing or low-res covers.
- **AI Metadata Agent:** Powered by Gemini, Claude, OpenAI, Ollama, Groq, or DeepSeek. Click **`🤖 Run AI Metadata Agent`** on any card to extract official title, author, series name, volume numbers, and high-resolution artwork from noisy file names.
- **📚 Personalized AI Book Recommendations (`recommend_books_and_media`):** Open the **AI Server Assistant** on your dashboard or click the **`📚 Book Recommendations`** quick-chip! The AI inspects your personal `BookRequest` history, `KindleDeliveryLog` dispatches, and favorite authors/genres to recommend tailored next reads—clearly distinguishing titles already on the shelf (`✅ ON SERVER` at `/library`) from 1-click auto-grab recommendations (`📥 REQUESTABLE` at `/requests`).

---

## ❓ 11. Frequently Asked Questions (FAQ)

**Q: Where do I go to request new books or audiobooks?**  
A: Head to the **Discover** tab (`/discover`). You can browse popular books and audiobooks or search by title, author, or series name. Click on any title to open the detail view and click **`Request Ebook`** or **`Request Audiobook`**. All requests are auto-approved instantly!

**Q: Will requested ebooks automatically send to my Kindle?**  
A: Yes! Once you have saved your Kindle email address in the **Kindle Settings** tab in `/library`, any ebook you request will be automatically dispatched to your Kindle as soon as the download finishes.

**Q: Why does Send-to-Kindle only support EPUB files?**  
A: Amazon officially deprecated MOBI and AZW file delivery via Send-to-Kindle. DomsHomeLab automatically standardizes non-EPUB files (MOBI, AZW3, PDF) into clean, valid EPUBs so they deliver wirelessly and display properly on your Kindle e-reader.

**Q: Can I read EPUB files offline?**  
A: Yes. Once an EPUB is opened in DomsHomeLab's reader, it is cached in your browser's persistent CacheStorage (`portalarr-books-v1`). You can resume reading even if you temporarily lose your internet or server connection.

**Q: Why did my Kindle email delivery fail?**  
A: Go to the **Kindle Settings** tab in `/library` and inspect the **Kindle Delivery History** log. Common reasons:
1. Your server's sending email is not on your Amazon Approved Personal Document E-mail List.
2. The file size exceeds Amazon's 50MB limit.
3. The recipient email was not an `@kindle.com` address.
After correcting the issue, click **`Retry Delivery`** to resend immediately.

**Q: How do I scan for newly added files in my shared folders?**  
A: Click **`Scan Share Folder`** (for Ebooks) or **`Scan Audio Folder`** (for Audiobooks) at the top of any library shelf in `/library` to trigger an instant background scan.
