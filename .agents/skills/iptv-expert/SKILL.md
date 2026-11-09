---
name: iptv-expert
description: Expert architectural, API, and operational guide for Portalarr IPTV & Live TV Hub subsystem (Dispatcharr integration, M3U/EPG streams, DVR buffer reservation, live session diagnostics, Plex Home tuner privileges, Jellyfin policies, media market shelves, and channel catalog management). Activate when developing or troubleshooting live TV streams, Dispatcharr lineups, DVR recording buffers, Plex Home Live TV/DVR restrictions, Jellyfin Live TV policies, or channel requests.
---

# IPTV & Live TV Hub Expert Guide

Portalarr integrates a unified Live TV & IPTV subsystem that bridges upstream IPTV providers (M3U / Xtream Codes), Dispatcharr lineup management, Plex Media Server Live TV & DVR tuners, and Jellyfin Live TV policies. It features real-time stream telemetry, DVR recording headroom protection, localized media market carousels, and 1-click Plex Home privilege provisioning.

Primary Reference Repositories & Modules:
- IPTV Core Engine: [`src/lib/iptv/plex-jellyfin-livetv.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/lib/iptv/plex-jellyfin-livetv.ts)
- IPTV Settings & Types: [`src/lib/iptv/types.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/lib/iptv/types.ts)
- IPTV Server Actions: [`src/app/iptv-actions.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/iptv-actions.ts)
- Admin IPTV Client UI: [`src/components/iptv/admin-iptv-client.tsx`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/components/iptv/admin-iptv-client.tsx)
- User Live Channels UI: [`src/app/channels/page.tsx`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/channels/page.tsx)
- Origin Logo Proxy: [`src/app/api/iptv/logo/[id]/route.ts`](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/api/iptv/logo/[id]/route.ts)

---

## Architecture & Subsystem Layout

```text
src/
├── app/
│   ├── admin/iptv/page.tsx           # Mission control: Providers, Dispatcharr, DVR, Telemetry, Users
│   ├── channels/page.tsx             # User-facing Live TV catalog with local market & sports shelves
│   ├── iptv-actions.ts               # Server actions for providers, lineups, DVR, users, and audit
│   └── api/iptv/
│       ├── logo/[id]/route.ts        # Origin HTTPS logo caching proxy (7-day cache)
│       ├── m3u/route.ts              # Virtual M3U playlist generator
│       └── epg/route.ts              # XMLTV electronic program guide feed
├── components/iptv/
│   ├── admin-iptv-client.tsx         # Admin command center (5 tabs with glassmorphic cards)
│   ├── channels-client.tsx           # Client catalog with filter chips, search, and market switcher
│   └── channel-card.tsx              # Resilient card with logo fallback to Lucide genre icons
└── lib/iptv/
    ├── types.ts                      # Interfaces for providers, lineups, DVR, audit, and sessions
    └── plex-jellyfin-livetv.ts       # Plex Home & DVR auditor, Jellyfin policy manager, session history
```

---

## Core Capabilities & Runbooks

### 1. Dispatcharr Integration & Authentication
- **API Authentication**: Dispatcharr requires `X-API-Key: {apiKey}` in HTTP request headers. Never pass API keys in query parameters or request bodies.
- **Lineup Sync & Profiles**: Queries Dispatcharr `/api/v1/lineups` and `/api/v1/channels`. Supports filtering by user-assigned profiles.
- **Auto-Sync & Admin Manual Trigger**: Lineup sync runs automatically via `syncDispatcharrLineupAction` and provides an instant manual sync button on both admin and catalog views.

### 2. DVR Stream Buffer Reservation (`dvrBufferReservation`)
- **Tuner Headroom Protection**: Homelab IPTV providers typically have hard limits on concurrent connections (e.g. 2–5 streams). If family members watch live streams simultaneously, scheduled Plex DVR recordings fail with "No tuner available".
- **Reservation Buffer**: Configurable via `Settings.dvrBufferReservation` (default: 1 stream).
- **Zero-Buffer Mode**: Homelab administrators who do not use Plex DVR recording can dial reservation down to `0` to allocate 100% of tuner connections to active client viewers.

### 3. Origin Channel Logo Proxy (`/api/iptv/logo/[id]`)
- **Mixed Content & LAN Block Prevention**: Dispatcharr often serves channel logos over unencrypted `http://` or private LAN IPs (`192.168.x.x`). Remote HTTPS clients block these requests.
- **HTTPS Reverse Proxy**: Logo URLs are proxied through `/api/iptv/logo/[id]`, returning high-speed image bytes with 7-day browser caching:
  `Cache-Control: public, max-age=604800, stale-while-revalidate=86400`.
- **Fail-Safe Semantic Fallback**: `ChannelCard` handles `onError` events and renders Lucide genre icons (`Trophy` for Sports, `Newspaper` for News, `Tv` for Networks, `Film` for Cinema, `Baby` for Kids) to ensure cards never display broken image icons.

### 4. Dynamic Media Market Customization Shelves
- **Anchor Market Feeds**: Always anchors the primary server market (e.g. Dallas CBS/NBC/FOX/ABC/CW).
- **Client Market Switcher**: Allows members to switch to their local broadcast media market (New York, Los Angeles, Chicago, etc.) or auto-detect based on IP geolocation.
- **Specialty Showcase Shelves**: Dedicated carousels for College Football (NCAA), NFL GameDay, Major League Baseball, and 24/7 National News.

### 5. Plex Home Live TV & DVR 3-Tier Permission Model
Plex Media Server enforces three distinct radio restriction states under **Restrictions > Live TV & DVR Access**:

| Plex Web Restriction | Plex API `allowTuners` Enum | Plex API Flags | Portalarr Badge | Action Buttons |
| :--- | :--- | :--- | :--- | :--- |
| **`No Live TV and DVR access`** | `allowTuners="0"` | `allowTuners: false`<br/>`allowDvr: false` | `⚠️ Missing Live TV & DVR` (Rose) | `[Enable Live TV]` \| `[Enable DVR]` |
| **`Allow Live TV only`** | `allowTuners="1"` | `allowTuners: true`<br/>`allowDvr: false` | `Live TV Only` (Sky Blue) | `[Live TV: ON]` \| `[Enable DVR]` |
| **`Allow Live TV and DVR access`** | `allowTuners="2"` | `allowTuners: true`<br/>`allowDvr: true` | `Live TV + DVR` (Emerald) | `[Live TV: ON]` \| `[DVR: ON]` |

- **Hierarchical 1-Click Transitions**:
  - *Clicking `[Enable Live TV]`*: Sets `allowTuners=1` and `allowChannels=1`, promoting user to **"Allow Live TV only"**.
  - *Clicking `[Enable DVR]`*: Automatically sets `allowTuners=2` (and `allowDvr=1`), promoting user to **"Allow Live TV and DVR access"** (since Plex requires tuner access to manage recordings).
  - *Clicking `[DVR: ON]`*: Revokes only DVR (`allowDvr=0&allowTuners=1`), gracefully dropping the user down to **"Allow Live TV only"**.
  - *Clicking `[Live TV: ON]`*: Revokes both Live TV and DVR (`allowTuners=0&allowDvr=0`), dropping the user to **"No Live TV and DVR access"**.

### 6. Plex Home & 3-Tier Live TV / DVR Restrictions Architecture
- **Plex 3-Tier Integer Enum Standard**:
  - **Tier 1: No Live TV and DVR access** (`allowTuners="0"`, `allowDvr="0"`): Both Live TV and DVR are completely disabled for the friend/member (e.g. `krismo4`, `Zestyandstizy`). In Portalarr UI, displays clean `No Live TV / DVR` badge and `Enable Live TV` / `Enable DVR` buttons.
  - **Tier 2: Allow Live TV only** (`allowTuners="1"`, `allowDvr="0"`): User can stream live broadcasts from virtual tuners, but cannot record or schedule DVR passes. In Portalarr UI, displays sky `Live TV Only` badge and `Live TV: ON` button.
  - **Tier 3: Allow Live TV and DVR access** (`allowTuners="2"` or `allowTuners="1"` with `allowDvr="1"`): User can stream live TV and schedule individual DVR recordings (e.g. `jrj78`, `trevscar1121`). In Portalarr UI, displays emerald `Live TV + DVR` badge and `DVR: ON` button.
- **Plex Cloud XML Integer Representation**:
  - In `https://plex.tv/api/users` XML and `/api/servers/{id}/shared_servers`, Plex returns `allowTuners="2"` directly for Tier 3 members rather than outputting a distinct `allowDvr="1"` attribute. Parsers MUST check integer values (`tunersInt === 2`) to identify DVR access.
- **Multi-Server Cluster Verification**:
  - Auditing user shares must check all servers in the cluster: both cloud-discovered PMS instances and database-configured servers in `prisma.plexServer`.
  - `getPlexSharedServersList` queries `https://plex.tv/api/servers/${encodeURIComponent(srvId)}/shared_servers` across every server (`KidsPlexServer`, `MainPlexServer`, `MainPlexServerBackup`, etc.) using server-specific tokens (`srv.accessToken || adminToken`), ensuring complete coverage across all servers.
- **`allowChannels` vs `allowTuners` Separation**:
  - `allowChannels` in Plex Media Server XML/REST API refers strictly to legacy online channels/plugins (e.g. TED, Vimeo, YouTube plugins) and is enabled by default on shared servers. It MUST NEVER be used to infer or grant Live TV access.
  - Live TV privilege is strictly governed by `allowTuners`.
- **`allowTuners` vs `allowDvr` Independence & DVR Dependency**:
  - `allowTuners="1"` does NOT imply `allowDvr="1"`. A user can have Live TV without DVR access ("Allow Live TV only").
  - In Plex, DVR strictly requires Live TV: if `allowTuners` is false (Tier 1, e.g. `krismo4`), `dvrGranted` is guaranteed `false`.
  - When `allowTuners` is true (e.g. `jrj78`, `trevscar1121`), `dvrGranted` is granted if Plex API reports DVR access (`allowTuners="2"` or `allowDvr="1"`) OR if configured in Portalarr (`matchedPortalUser?.hasPlexDvrAccess`), preventing undocumented Plex XML omission from wiping out Tier 3 access down to Tier 2.
  - Enabling DVR requires both `allowTuners="2"` (or `allowTuners="1"` and `allowDvr="1"`).
  - Revoking DVR (`allowDvr="0"`) leaves `allowTuners="1"` intact.
  - Revoking Live TV (`allowTuners="0"`) automatically sets `allowDvr="0"`.
- **Live Plex API Authoritative Precedence Over SQLite**:
  - When Plex is reachable (`plexReachable === true`), the live values from `https://plex.tv/api/users` and `https://plex.tv/api/v2/home/users` (`item.allowTuners`, `item.allowDvr`, `item.isPlexHomeMember`) are authoritative. Never OR cached SQLite values (`matchedPortalUser?.hasPlexLiveTvAccess`) into live state when Plex is reachable, or user privilege revocations made in Plex Web will be ignored and perpetually re-written to SQLite.
- **Hard Limit**: Plex caps Plex Home at 15 total users (1 owner + 14 member slots). Regular Plex friends cannot tune Live TV channels unless admitted to Plex Home.
- **Inactivity Audit**: Evaluates `lastIptvWatchedAt` and `plexHomeJoinedAt` against `plexHomeInactivityDays` (default: 21 days).
- **Non-Destructive Candidate Flagging**: Inactive members are surfaced with visual warning borders (`border-amber-500/30 bg-amber-500/5`) and labeled `• Slot Rotation Candidate (Protected)`. Auto-kick is strictly `false` by default, preserving administrator control.

### 7. Jellyfin Live TV Policy Management
- **Policy Synchronization**: Audits and provisions `EnableLiveTvAccess` in Jellyfin via `POST /Users/{id}/Policy`.
- **Folder Preservation Contract**: Always fetches existing user policies first and merges changes:
  `{ ...currentPolicy, EnableLiveTvAccess: enable, EnableLiveTvManagement: false }`.
  Never sends an unmerged policy payload, which would inadvertently reset `EnabledFolders` and revoke media library access.

### 8. Live TV Access Restrictions & Admin-Only M3U / Player Policy
- **Plex & Jellyfin Exclusivity for Members**: Regular users and members stream Live TV strictly and exclusively through official Plex (`allowTuners`) and Jellyfin (`EnableLiveTvAccess`) client applications.
- **Standalone M3U & EPG Link Prohibition**: Standalone M3U playlists (`/api/iptv/m3u`), XMLTV feeds (`/api/iptv/epg`), and direct IPTV player tokens (`canAccessIptv`) are strictly restricted to administrators (`role === "ADMIN"`). Regular members must NEVER be granted standalone links or `canAccessIptv: true` in SQLite to protect upstream tuner bandwidth, avoid stream stability degradation, and prevent playlist leakages.
- **Admin Users Table Design**: The Member Live TV roster strictly manages Plex Home slots, Live TV & DVR privileges, and Jellyfin Live TV policies. Standalone player / M3U toggle buttons are excluded from member rows.

### 9. Live Stream Session Telemetry & Watch History Integration
- **Tautulli & PMS Session Scans**: Scans active streams and session history via `/status/sessions/history/all` and Tautulli `get_history`.
- **Heuristic Live Stream Detection**: Detects live broadcasts using media type (`live`, `channel`, `clip`, `iptv`), channel identifiers, and title patterns (`/world series|mlb|baseball|nfl|ncaa|football|fox|cbs|nbc|abc|espn/i`).
- **Activity Persistence**: Updates `lastIptvWatchedAt` on the User record to track genuine live TV engagement for slot rotation calculations.

### 10. Local Media Market Affiliates & AI Dispatcharr Provisioning
- **Market Detection & Local Shelves**: Detects media markets via client IP or dropdown selector (Dallas host server default, plus Philadelphia, New York, Los Angeles, Chicago, Houston, Boston, etc.).
- **Local Broadcast Affiliates Request**: When local channels for a market are missing, users can click `[Request {City} Channels]` on `/channels` or ask the AI Server Assistant.
- **AI Dispatcharr Prompt Generation (`generateMarketAiPrompt`)**:
  - Automatically compiles network callsigns (NBC, CBS, FOX, ABC, CW), regional sports networks, in-market NFL teams, and exact Dispatcharr REST API instructions (`GET /api/channels/streams/?search={term}` and `POST /api/channels/channels/from-stream/`).
  - Stored inside `IptvChannelRequest.adminNotes` (`[AI-DISPATCHARR-PROMPT]` block).
- **Automated Stream Discovery & Provisioning (`provisionMarketChannelsFromDispatcharr`)**:
  - Queries Dispatcharr unmapped upstream streams for market keywords and callsigns.
  - Automatically creates channels via `POST /api/channels/channels/from-stream/` with `{ stream_id, name }` and syncs the channel lineup without manual admin work.
- **Admin Mission Control Experience (`/admin/iptv` Tab 6)**:
  - Displays `AI Prompt Ready` badge on market requests.
  - Expandable terminal code card allows 1-click clipboard copying (`📋 Copy AI Prompt`).
  - Instant manual trigger button (`[🤖 AI Auto-Scan Dispatcharr]`) to re-scan Dispatcharr and auto-provision channels on demand.

### 11. Plex Home Setup & Login Transition Guide (`PlexHomeGuideModal`)
- **Interactive Guide Modal**: Accessible on `/channels`, `/admin/iptv` (Tab 5), and the Profile Add-ons catalog.
- **5-Step Onboarding Workflow**:
  1. **Accept Invitation Email**: Check email or visit `app.plex.tv -> Settings -> Account -> Plex Home` to accept the pending invite banner.
  2. **Fast User Switching**: On Apple TV, Roku, Fire TV, and Smart TVs, Plex displays the "Who's Watching?" profile picker. Users must click their own profile avatar to keep watch history and continue-watching private.
  3. **4-Digit Profile PIN**: Recommend setting a PIN under Plex account settings so other household members cannot enter their profile.
  4. **Pin 'Live TV & DVR'**: In the Plex sidebar, click `More`, locate the server, and select `Pin to Sidebar` on `Live TV & DVR`.
  5. **Tune & Record**: Browse electronic program guides (EPG) by genre and schedule DVR series passes.
- **Admin 1-Click Clipboard Sharing**: Admins can copy a Markdown/plain-text formatted version of the guide (`PLEX_HOME_GUIDE_TEXT`) to paste to new users in Discord or email.

### 12. Account Settings Free Add-on (`iptv_livetv`) & Jellyfin Capacity Fallback
- **Account Settings Integration**: Live TV is a first-class Free Add-on (`iptv_livetv`) in `/profile` alongside Ebooks and Audiobooks.
- **Self-Service / Admin Provisioning**:
  - When enabled: checks Plex Home capacity. If slots are available ($< 14$ non-admin members), sends Plex Home invite and provisions `allowTuners=1`.
  - If Plex Home is full ($14/14$): automatically provisions the user on Jellyfin (`POST /Users/New` if needed, `EnableLiveTvAccess: true`) without taking a Plex Home slot!
  - When disabled: revokes tuner access across Plex PMS and Jellyfin.
- **Live Catalog Access Gating**: Automatically unlocks `/channels` when `iptv_livetv` is active in `user.enabledAddons`.
- **Capacity Fallback Banner on `/channels`**: When Plex Home is at capacity, users without Live TV see an informative banner highlighting unlimited viewer slots on Jellyfin & Swiftfin with an instant 1-click activation button.
- **Admin 1-Click Provisioning on Tab 5**: In pending requests, admins can click `[⚡ Provision on Jellyfin (Unlimited Slots)]` to instantly grant access without exceeding the 14-member Plex Home ceiling.

### 13. Dispatcharr Profile Mapping, Channel Reassignment & Plex DVR Auto-Refresh
- **Profile Transparency on Channel Cards**: Channel cards render badges for each Dispatcharr profile they belong to (`Sports`, `News`, `Kids`, `Entertainment`, `Fios`, `Spectrum`, etc.).
- **Unmapped vs Assigned Channel Actions**:
  - Channels not assigned to any profile display a prominent `⚠️ Not in a Profile` badge with an `[+ Add to Profile]` action button.
  - Channels that already have an assigned profile display a clean `[Move Profile]` button with an `ArrowRightLeft` icon, allowing users and admins to easily re-categorize channels across profiles (e.g. moving regional sports channels from News or Entertainment into Sports).
- **Dedicated Unassigned Shelf**: "Featured Hubs" includes a dedicated `⚠️ Not in a Profile ({count})` pill that isolates unmapped channels so users and admins can quickly review and organize them.
- **Strict Existing-Profile Restriction**: Channels can ONLY be added or moved to existing, configured Dispatcharr profiles. Creating new profiles is strictly blocked because Plex DVR tuners only poll pre-configured virtual tuner paths and will not detect or pull new profile feeds without server reconfiguration.
- **Profile Move Engine (`moveChannelDispatcharrProfile`)**:
  - Finds the channel by ID or `xmltvId` and resolves target and source profiles.
  - Updates local SQLite database: deletes old `prisma.iptvProfileChannel` links, inserts the new link, and recalculates accurate channel counts on both source and target profiles.
  - Updates Dispatcharr upstream REST API: patches the target profile via `PATCH /api/channels/profiles/{targetProfileId}/` with the channel appended, and patches the old profile via `PATCH /api/channels/profiles/{oldProfileId}/` with the channel removed.
  - Automatically triggers `refreshPlexDvrLineupAndGuide()` across all active Plex servers.
- **Automated Plex DVR Lineup & Guide Refresh (`refreshPlexDvrLineupAndGuide`)**: Discovers active Plex DVR tuners across PMS instances (`GET /livetv/dvrs`), triggers `POST /livetv/dvrs/{key}/reloadLineup`, `POST /livetv/dvrs/{key}/refreshGuide`, and `POST /media/subscriptions/refresh` so moved or added channels immediately appear in the correct Plex Live TV & DVR lineups and EPG grids without server restarts.
- **Admin Mission Control Experience (`/admin/iptv` Tab 6)**:
  - Distinguishes new additions (`[PROFILE_ADD]`, sky badge) from profile moves (`[PROFILE_MOVE]`, purple badge).
  - Provides a 1-click `[Move in Dispatcharr & Plex]` button that executes the move action and updates request status to `ACTIVATED`.
  - Header features manual `[🔄 Refresh Plex DVR Lineup]` tool to force a cluster-wide DVR reload anytime.

### 15. Clickable Hub Navigation & Profile Curation Architecture
- **Clickable Channel Hubs Bar**: Replaces hard-locked permanent top carousels with an interactive, responsive Hubs bar (`ChannelsClient`):
  1. **📍 Local Hub ({marketName})**: Anchored by the Dallas host server (DFW) by default, customized via IP edge geolocation or dropdown selector, displaying local broadcast affiliates (NBC, CBS, FOX, ABC, CW) and regional sports directly underneath.
  2. **🏆 Sports**: Commercial-free NFL RedZone, NFL Network, and Saturday college football (SEC, Big Ten, ACC, ESPNU). Curated to genuine sports channels (~104 channels).
  3. **📰 News**: 24/7 national, financial, and international news networks (~33 channels).
  4. **🎬 Entertainment**: Premium movies, series, drama, and comedy networks (~171 channels).
  5. **👶 Kids & Family**: Educational and family networks (Disney, Nick, Cartoon Network, PBS Kids) (~20 channels).
  6. **📺 All Lineups**: Full master lineup with virtual channel numbers (~539 channels).
  7. **⚠️ Not in a Profile (Strictly Last Hub)**: Isolates channels in the master pool that need profile mapping, with 1-click `[+ Add to Profile]` buttons.
- **Dispatcharr Bulk Profile Update API**:
  - Dispatcharr treats `channels` as `readOnly` in `PATCH /api/channels/profiles/{id}/`.
  - The authoritative endpoint for assigning/unassigning channels is:
    `PATCH /api/channels/profiles/{profile_id}/channels/bulk-update/` with payload `{ channels: [ { channel_id, enabled } ] }`.
- **FCC Callsign & Zero-Padded Channel Normalization**:
  - `extractCallsign()` extracts 3–5 letter US broadcast callsigns (`(KXAS)`, `(KDFW)`, `(KTVT)`, `(WFAA)`).
  - Normalizes zero-padded channel numbers (`NBC 05` -> `NBC 5`) and strips backup tags (`[BK]`, `(BK)`, `alt`) to ensure broadcast feeds are deduplicated and merged cleanly.
- **Stale Channel SQLite Pruning**:
  - `syncDispatcharrLineup` tracks synced channel IDs and prunes non-custom `IptvChannel` records that were deleted or merged in Dispatcharr, keeping SQLite and Dispatcharr counts 100% synchronized.
- **Two-Pass Grouping**:
  1. *Stage 1: TVG-ID Match*: Groups channels by exact `tvg_id` or `effective_tvg_id` (ignoring synthetic `dispatcharr.*` placeholders).
  2. *Stage 2: Normalized Name Match*: Groups remaining channels by normalized name (`normalizeChannelNameForDedup`) stripping provider prefixes (`US|`, `USA:`, `✦●✦`), video tags (`[USA]`, `(FHD)`, `1080p`, `60fps`), and non-alphanumeric punctuation.
- **Channel Scoring Formula (`scoreCandidateChannel`)**:
  - Cable/satellite channel numbers (<1000: +100 pts, <2000: +50 pts, <10000: +20 pts).
  - Profile memberships (+30 pts per assigned profile).
  - Existing stream sources (+10 pts per upstream stream).
  - Valid channel logos (+10 pts) and EPG bindings (+10 pts).
  - Clean display names without provider artifacts (+15 pts).
  - Lower database ID preference (tie-breaker: up to +50 pts).
- **Stream Consolidation & Multi-Source Merging**:
  - Merges all distinct upstream stream IDs from duplicate channels onto the winning primary channel via `PATCH /api/channels/channels/{primaryId}/` with `{ streams: mergedStreams }`. No redundant fallback feeds or provider tuners are discarded.
  - Automatically copies missing logos or EPG data IDs from duplicate channels to the primary if the primary channel lacked them.
  - Cleans display names (`cleanChannelNameForDisplay`) on primary channels to remove provider tags (`[USA]`, `US|`).
- **Profile Remapping & Deletion**:
  - Updates all Dispatcharr profiles via `PATCH /api/channels/profiles/{id}/` by replacing duplicate channel IDs with the primary ID and deduplicating array elements.
  - Deletes redundant duplicate channel records via `DELETE /api/channels/channels/{dupId}/` (concurrent batches of 15).
  - Re-syncs local SQLite catalog (`syncDispatcharrLineup`) and removes deleted channels from `iptvProfileChannel` and `iptvChannel`.
  - Automatically triggers `refreshPlexDvrLineupAndGuide()` to reload PMS DVR lineups and refresh electronic program guides.
- **Admin Command Center UI**: Available as a dedicated action card in Tab 2 of `/admin/iptv` (`admin-iptv-client.tsx`) and backed by Server Action `cleanupDispatcharrDuplicatesAction()`.

---

## 🚨 Mandatory Task Completion Protocol (Strict SemVer)

Before completing any task or pushing to git:
0. **Step 0: Read Skill Upfront**: Call `read_file` on the relevant `SKILL.md` before writing code.
1. **Step 1: Integration Testing**: Execute `cmd /c "npm test"` (all 23 suites must pass, 0 failures).
2. **Step 2: Production Build**: Execute `cmd /c "npm run build"` (Turbopack 100% clean, 0 errors).
3. **Step 3: Edge Security & Cloudflare Policy Audit**: Register any route changes in `src/lib/edge-policy-paths.ts`.
4. **Step 4: Skills & Documentation Sync**: Update relevant `.agents/skills/` documents with new findings **BEFORE** committing.
5. **Step 5: SemVer Bump & Push**: Bump version in `package.json`, stage all changes, commit with `[v<version>]`, push strictly to `origin/main` (Beta).
