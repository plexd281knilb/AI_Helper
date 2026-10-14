---
name: discord-expert
description: Expert architectural, permission, and operational guide for Portalarr Discord Bot integration, channel/role blueprints, trial isolation, zero-pricing policies, embed formatting standards, and web account linking. Activate when managing Discord bot configurations, creating or updating Discord embeds, configuring channel permissions, implementing account linking workflows, or synchronizing Discord member roles.
---

# Discord Bot & Community Integration Expert Guide

Portalarr integrates with Discord via a lightweight, native REST API bot engine (`discordFetch`) that provisions an automated community server, synchronizes member roles with web accounts, broadcasts infrastructure health and request telemetry, and publishes interactive guides.

---

## 🚨 Strict Public Policies & Core Rules

### 1. Absolute Zero-Pricing & Zero-Tier Concealment Policy
- **Never reveal Tier 1 vs Tier 2:** Tier 2 members are higher-paying accounts who receive managed support because they need more hands-on assistance. Publicly, both tiers are identical and unified under the single **`⭐ Member`** role in Discord.
- **No commercial or pricing terms in Discord:**
  - Prohibited strings: `$15`, `$17.50`, `$180`, `$240`, `Cash App`, `Venmo`, `Zelle`, `Billing Ledger`, `Tier 1`, `Tier 2`, `Subscription Fee`, `Invoice`.
  - Embeds and channel topics must strictly discuss platform features, technical setup, automated requests, library guides, and community discussions.

### 2. Strict Trial Isolation & Gating Protocol
- **Default Permissions:**
  - `@everyone` and `⏱️ Trial Pass` are denied `VIEW_CHANNEL` across all categories and channels **except `#welcome-and-rules`**.
  - Trial members entering the Discord server only see `#welcome-and-rules`.
  - They are instructed to log in to the Portalarr Web Portal (`home.domshomelab.com`) and link their Discord handle in **Account Settings → Profile**.
- **Role Elevation:**
  - Once linked, the user's role is automatically evaluated in Portalarr and updated to **`⭐ Member`** via the Discord REST API.
  - Elevating to `⭐ Member` instantly unlocks Category 2 (Guides), Category 3 (Community Chat), Category 4 (Requests & Media), and Category 5 (Help & Tickets).

### 3. Media Retention & Leaving Soon Policy
- Unwatched items staged in Maintainerr Leaving Soon grace periods are kept in the library solely by **active playback**.
- **No manual administrator exemptions:** Users must simply start streaming/watching the title to reset retention. Do not instruct users to open tickets asking for exemptions.

---

## Architecture & REST Engine

Portalarr communicates with Discord using native HTTPS fetch queries without heavy gateway dependencies:

- **Endpoint Client:** `discordFetch<T>(endpoint, options, botToken)` in [`src/lib/discord/discord-bot.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/lib/discord/discord-bot.ts).
- **Rate Limit Resilience:** Automatically respects Discord HTTP 429 rate limits using exponential backoff (`retry_after` + 150ms buffer, up to 5 attempts).
- **Credentials Storage:** Bot token is encrypted using AES-256-GCM in the `SystemSetting` table under key `DISCORD_BOT_CONFIG`.
- **In-Place Embed Updating:** Pinned embeds are updated in-place via `PATCH /channels/{channelId}/messages/{messageId}` to prevent duplicate message spamming during sync operations.

---

## Discord Server Blueprint

### Categories & Channel Topology

```text
📁 📌 1. WELCOME & INFO (Gated: Trial only sees welcome-and-rules)
  ├── 💬 #welcome-and-rules      [All Read-Only] Pinned: welcome_rules embed
  ├── 📢 #announcements          [Member Read-Only] Announcement channel
  ├── 💬 #membership-info        [Member Read-Only] Pinned: platform_features embed
  ├── 💬 #links-and-webhooks     [Member Read-Only] Pinned: links_webhooks embed (Quick Links)
  ├── 💬 #roadmap-and-updates    [Member Read-Only] Pinned: roadmap_updates embed
  ├── 💬 #plex-invites           [Member Read-Only] Pinned: plex_invites embed
  └── 💬 #maintenance            [Member Read-Only] Pinned: maintenance_window embed (5:00-5:30 AM)

📁 📖 2. GUIDES & SELF-SERVICE (Member-Only)
  ├── 💬 #plex-setup-guides      [Member Read-Only] Pinned: plex_guides embed (30-sec Direct Play)
  ├── 💬 #transcode-doctor       [Member Read-Only] Pinned: transcode_doctor embed
  └── 💬 #kindle-and-audiobooks  [Member Read-Only] Pinned: kindle_reading embed (Ebooks & Audiobooks)

📁 💬 3. COMMUNITY CHAT (Member-Only, Interactive)
  ├── 💬 #general-chat           [Member Chat] Homelab & general banter
  ├── 💬 #movie-and-tv-talk      [Member Chat] Spoiler-tagged discussions
  ├── 💬 #book-nook              [Member Chat] Reading & audiobooks recommendations
  └── 💬 #polls-and-feedback     [Member Chat] Library addition polls

📁 🎬 4. REQUESTS & MEDIA (Member-Only)
  ├── 💬 #media-requests         [Member Read-Only] Live Seerr request stream
  ├── 💬 #recently-added         [Member Read-Only] Plex/Tautulli new release webhooks
  └── 💬 #leaving-soon           [Member Read-Only] Pinned: leaving_soon embed

📁 🆘 5. HELP & TICKETS (Member-Only)
  ├── 💬 #support-tickets        [Member Interactive] Pinned: support_guide embed
  ├── 💬 #request-help           [Member Interactive] Media request assistance
  └── 💬 #server-uptime          [Member Read-Only] Live 60-second status cockpit
```

### Discord Roles Hierarchy

| Role Name | Color | Hoist | Purpose |
| :--- | :--- | :--- | :--- |
| **`👑 Platform Admin`** | `#EF4444` (Red) | Yes | Full server management and administrative oversight |
| **`⭐ Member`** | `#10B981` (Emerald) | Yes | Unified role for all active members (both Tier 1 and Tier 2) |
| **`⏱️ Trial Pass`** | `#3B82F6` (Blue) | No | Gated role restricted strictly to `#welcome-and-rules` |

---

## Embed Formatting Standards

All Discord embeds generated via `generateDiscordEmbed(key, customData)` in [`src/lib/discord/discord-bot.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/lib/discord/discord-bot.ts) must adhere to these canonical formats:

### 1. Plex Device Setup Guide (`plex_guides`)
```json
{
  "title": "📱 Plex Device Setup: Enable Direct Play in 30 Seconds",
  "description": "Plex default settings often limit video quality to 720p 2 Mbps over the internet. Follow these steps on your device once to ensure Crystal Clear 4K/1080p Original Quality without server buffering.",
  "color": 16096779,
  "fields": [
    {
      "name": "📺 Apple TV 4K",
      "value": "Open Plex Settings → Video\nSet Home Streaming & Remote Streaming to Maximum\nTurn Match Content (Dynamic Range & Frame Rate) ON"
    },
    {
      "name": "📺 Roku Players & Roku TVs",
      "value": "Open Plex Settings → Video\nSet Local Quality & Remote Quality to Original\nIn Playback Options, ensure Direct Play is set to Force or Auto"
    },
    {
      "name": "📺 Amazon Fire TV & Android TV / Google TV",
      "value": "Open Plex Settings → Video\nSet Video Quality to Maximum\nScroll to Subtitles → Set Burn Subtitles to Only Image Formats"
    },
    {
      "name": "📺 Samsung Tizen & LG webOS Smart TVs",
      "value": "Open Plex Settings → Video\nSet Local Quality & Remote Quality to Original\nEnable Direct Stream and Direct Play checkboxes"
    },
    {
      "name": "📱 iPhone, iPad & Android Mobile",
      "value": "Open Plex Settings → Quality\nSet Remote Streaming to Maximum\nIn Advanced → Turn Use Old Video Player OFF"
    },
    {
      "name": "💻 Windows / macOS / Linux PC",
      "value": "⚡ Pro Tip: Never use web browser tabs (Chrome/Safari) for 4K or HDR! Download the free official Plex Desktop App for native hardware decoding and Dolby Atmos pass-through."
    }
  ],
  "footer": { "text": "DomsHomeLab • Device Setup Guides" }
}
```

### 2. Welcome & Community Rules (`welcome_rules`)
- **Header:** `🚀 Welcome to DomsHomeLab & Portalarr Mission Control`
- **Fields:**
  1. `⏱️ Trial Pass & Account Linking (Required)`: Explains trial restrictions and provides linking instructions in `/settings/profile`.
  2. `📌 1. Quality & Direct Play First`: Guidance on setting client quality to Maximum / Original.
  3. `📥 2. Automated Media Requests`: Portalarr web portal automated grabbing.
  4. `🩺 3. Transcode Doctor Diagnostics`: Device fix instructions linking to `<#1558230275950125261>`.
  5. `💬 4. Spoiler Etiquette & Chat`: Use `||spoiler||` tags for new releases.
- **Rule Exclusions:** Do NOT include household integrity or account sharing rules.

### 3. Leaving Soon Radar (`leaving_soon`)
- **Header:** `⏳ Leaving Soon: Storage Headroom & Media Retention`
- **Fields:**
  1. `🛡️ 14-Day Grace Period`: Items marked with badges and featured on Plex Home Screen.
  2. `🍿 Want to Keep Something?`:
     `Simply start watching the title before the countdown finishes to keep it in the library! Active playback automatically resets retention and keeps the media active.`

### 4. Official Links Directory (`links_webhooks`)
- **Header:** `🔗 Official Homelab Links & Fast Access`
- **Fields:** Portalarr Web Portal (`https://home.domshomelab.com`), Plex Web (`https://app.plex.tv`), Seerr media requests, in-browser Speed Test.

### 5. Scheduled Maintenance Window (`maintenance_window`)
- **Header:** `🛠️ Scheduled Server Maintenance: Daily 5:00 AM – 5:30 AM`
- **Fields:** Schedule details, Unraid reboot & DB sweep explanation, stream disconnection expectation (resumes at 5:30 AM), 24/7 uptime note.

### 6. Support Ticket Submission Guide (`support_guide`)
- **Header:** `🆘 Support & Assistance: How to Report an Issue`
- **Fields:** Issue reporting template (device model, title, timestamp, error/buffering details), Transcode Doctor self-service check before opening a ticket.

---

## Web Account Linking & Verification Workflows

### 1. Member Self-Service Linking (`/settings/profile`)
1. User navigates to **Account Settings → Profile → Discord Community & Role Sync**.
2. If not yet in the Discord server, user clicks **"Join Discord Community"** (`https://discord.gg/KNvUSmPtD3`).
3. User enters their Discord handle or username (e.g. `username` or `username#1234`).
4. System invokes `linkMyDiscordAccountAction(query)` in [`src/app/discord-actions.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/discord-actions.ts).
5. The bot queries the guild member list via `GET /guilds/{guildId}/members/search?query=...`, resolves the user's Discord ID, saves `discordId`, `discordUsername`, and `discordAvatar` to the `User` record, and immediately grants the `⭐ Member` role in Discord.

### 2. Administrator Manual Linking (`/settings/access`)
1. In the User Management list, administrator clicks **Manage** on any user card to open `subModalUser`.
2. Under **Discord Account Binding**, admin enters the member's Discord handle and clicks **"Link Discord Account"**.
3. System invokes `adminLinkUserByHandleAction(userId, query)`.
4. The bot matches the Discord member, updates the database, provisions the proper role, and displays the user's avatar and snowflake ID.

---

## User Activity & Login Tracking (`lastLogin`)

- **Database Column:** `User.lastLogin DateTime?` in SQLite schema.
- **Tracking Mechanism:** Recorded automatically in `createSession()` in [`src/app/auth-actions.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/auth-actions.ts) whenever a user logs in with password credentials, signs in via Plex SSO, or switches household sub-profiles.
- **Cookie Lifetime:** Sessions use 30-day persistent JWT cookies (`THIRTY_DAYS_SEC = 2592000`). If a user keeps a browser open without re-authenticating, `lastLogin` preserves their actual last authentication timestamp.
- **UI Exposure:**
  - **User Card:** Prominently displays `Joined: MMM d, yyyy • Last Login: MMM d, yyyy` (or `Never` if not yet logged in).
  - **User Modal (`subModalUser`):** Shows exact timestamp `Last Login: MMM d, yyyy h:mm a` alongside status and cadence info.

---

## Test Suite Isolation & Notification Suppression

To ensure test suites (`npm test` / `verify-all.ts`) never post messages, dispatch webhooks, or ping users in live Discord channels:

1. **Environment Variables:** `scripts/verify-all.ts` unconditionally initializes:
   - `process.env.PORTALARR_TEST = "true"`
   - `process.env.NODE_ENV = "test"`
   - `process.env.DISABLE_DISCORD_NOTIFICATIONS = "true"`
2. **REST API & Webhook Guards:**
   - `discordFetch`: Returns mocked HTTP 200 `{ ok: true, status: 200, data: {} }` during test runs, preventing external network traffic to Discord API endpoints.
   - `postDiscordMessage`: Returns `{ success: true, messageId: "mock-test-message-id" }` during test runs.
   - `sendSeerrDiscordWebhook`: Silently returns `{ success: true }` without dispatching webhooks or bot messages if `PORTALARR_TEST` is set or if the request title/requester contains `"test"`.
   - `sendSeerrEmailNotification`: Silently returns `{ success: true }` during test runs.
3. **Auto-Download Decoupling:** `dispatchBookOrAudiobookRequest` skips background `autoDownloadBookRequest` loops in test runs to prevent async race conditions during bulk approval/decline verification.
4. **Test Discord Guild:** When testing bot features in staging, administrators can bind dedicated test servers (e.g., Guild ID `1559231517325135892`) in Settings → Discord. Ensure the bot application is invited with Administrator permissions (`permissions=8&scope=bot%20applications.commands`).
