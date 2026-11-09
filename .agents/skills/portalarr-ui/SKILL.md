---
name: portalarr-ui
description: Comprehensive UI/UX design, component styling, layout architecture, and responsiveness guide for Portalarr. Activate when building, modifying, or refining frontend components, modals, dialogs, media cards, forms, settings panels, navigation, or dark theme styling.
---

# Portalarr UI Design & Component System Guide

This skill serves as the single source of truth for all UI/UX design patterns, component conventions, responsiveness rules, and aesthetic standards across Portalarr. Use and update this guide whenever implementing new views, tweaking existing layouts, or refining user interaction flows.

---

## 🎨 Core Design Foundations

Portalarr uses a **Modern Cinematic Dark Theme** powered by Tailwind CSS, Radix UI primitives, Lucide React icons, and custom glassmorphic styling.

### 1. Color Palette & Hierarchy
- **Canvas / App Background**: `bg-slate-950` or `bg-black` with subtle gradients (`from-slate-950 via-slate-900 to-slate-950`).
- **Primary Cards & Containers**: `bg-slate-900/90` with `border border-slate-800 backdrop-blur-md`.
- **Secondary Nested Wells / Inner Boxes**: `bg-slate-950/60` or `bg-slate-900/40` with `border border-slate-800/80`.
- **Active / Unsaved Dirty State Warning**:
  - Border: `border-2 border-amber-500/70`
  - Glow: `shadow-[0_0_20px_rgba(245,158,11,0.2)]`
- **Semantic Accents**:
  - 🟢 **Emerald (`emerald-400` / `emerald-500`)**: Success, available in library, active streaming, auto-approved.
  - 🟡 **Amber (`amber-400` / `amber-500`)**: Pending review, warnings, unsaved dirty states, monitored coming soon.
  - 🟣 **Purple / Indigo (`purple-400` / `indigo-400`)**: Poster overlays, Kometa studio, AI metadata agents, automation schedules.
  - 🔵 **Cinematic Blue / Cyan (`sky-400` / `cyan-400`)**: Live stream telemetry, Plex direct play, speed test, digital releases.
  - 🔴 **Crimson / Rose (`rose-400` / `rose-500`)**: Media Requests (Seerr/Overseerr engine), prune deletions, errors, stream terminations, declined requests.
  - 🟠 **Vibrant Orange (`orange-400` / `orange-500`)**: General setup, alert banners, server configuration.

### 2. Multi-Tab Navigation, 5-Hub Settings Architecture & Active State Contrast
- **System Settings 5-Hub Architecture (`src/app/settings/page.tsx`)**:
  Settings are consolidated into 5 high-level mission hubs, each organized with responsive sub-tab switchers, dirty-state indicators, and full backward-compatible routing:
  1. **General & Platform (`general`)**:
     - `platform`: Web & Storage Paths (Base URL, Webhook URL, Completed Downloads Directory, filesystem permissions matrix).
     - `schedules`: Schedules & Automation (Library Auto-Scan & Sync Frequency with spinning disk optimizations, and interactive System Schedules Dashboard matrix displaying all 13 background runners, real-time frequency selector dropdowns with instant persistence for configurable tasks, relative countdowns, next run timestamps, and 1-click manual triggers).
     - `announcements`: Announcements & Roadmap (Feature broadcast banner, maintenance alert, roadmap cards).
     - `logs`: Live System Logs (Real-time colored terminal log viewer, category filters, auto-refresh toggle).
  2. **Servers & Fleet (`servers`)**:
     - `fleet`: Server Fleet & Multi-Platform (Plex, Jellyfin, Emby server fleet, self-selection toggles, library discovery).
     - `plex-admin`: Master Plex & Direct Snapshots (Primary PMS URL, Admin token, direct connection tester, cache flush).
     - `plex-cluster`: Plex Cluster & Auto-Discovery (Multi-server cluster nodes, auto-discovery worker, monitored server toggles).
     - `telemetry`: Historical Watch & Host Telemetry (Watch session tracking, sharing detection thresholds, Glances host hardware endpoints).
  3. **Access & Members (`access`)**:
     - Access Control, Admin Approval Gates, User Accounts, Role Assignments, and Pending Action Reviews (`<AccessSettingsPage />`).
  4. **Integrations & Servarr (`integrations`)**:
     - `servarr`: Servarr Stack & Downloaders (Radarr, Sonarr, Lidarr, Readarr, SABnzbd, qBittorrent connection testing and API keys).
     - `requests`: Media Requests (Seerr / Jellyseerr / Overseerr synchronization, auto-approval rules, default request limits).
     - `ai`: AI Agent & Curation Keys (Google Gemini API keys, OpenAI tokens, Kometa, Agregarr, Maintainerr curation webhooks).
  5. **Communications & Alerts (`communications`)**:
     - `smtp`: Global SMTP & Kindle Delivery (Outbound mail server, SMTP credentials, TLS/SSL, Amazon Send-to-Kindle address, live test email dispatches, and Admin Recipient indicator with 1-click Change Recipient modal).
     - `broadcast`: Broadcasts, Notification Templates & Granular Outgoing Email Approval Policy (12 granular notification templates, Markdown editor, test email dispatches, distinct "To: Users" vs "To: Admin" audience badges, interactive recipient filtering, Dominic personal sender anti-spam notices, and automated policy verification on template edit/save).
     - `discord`: Discord Bot & Automation (Bot token, Guild ID, channel mappings for alerts/status/requests, role assignments).

- **Sub-Tab Switcher Pattern & URL Synchronization**:
  - Top hubs are switched via `<TabsList>` with active semantic brand tokens (`orange`, `blue`, `emerald`, `rose`, `indigo`).
  - Active sub-tabs use secondary pill buttons (`variant="default"` when active with brand glow, `variant="outline"` when inactive).
  - Dirty state tracking (`hasChanges`) highlights both the parent hub pill and the active sub-tab pill with amber warning accents (`border-amber-500/70 shadow-[0_0_15px_rgba(245,158,11,0.2)]`).
  - Navigation guards prompt confirmation if unsaved changes exist before switching tabs or leaving the page.
  - Deep-link and backward-compatible URL query routing: `/settings?tab=general&subtab=logs` or legacy parameters (`/settings?tab=logs`, `/settings?tab=monitoring`, `/settings?tab=beta`, `/settings?tab=emails`, `/settings?tab=discord`) automatically resolve to their respective parent hub and sub-tab.

- **Semantic Tab Accents**: Tabs in settings or dashboards must never rely on monochrome/desaturated `text-primary` in dark mode. Every tab must specify its distinct brand color token for its icon, hover ring/shadow, and active selection state:
  - **General & Setup**: `text-orange-400`, `hover:ring-orange-400/80`, `data-[state=active]:text-orange-400 data-[state=active]:bg-orange-500/10 data-[state=active]:border-orange-500/40`
  - **Media Servers**: `text-blue-400`, `hover:ring-blue-400/80`, `data-[state=active]:text-blue-400 data-[state=active]:bg-blue-500/10 data-[state=active]:border-blue-500/40`
  - **Access Control**: `text-emerald-400`, `hover:ring-emerald-400/80`, `data-[state=active]:text-emerald-400 data-[state=active]:bg-emerald-500/10 data-[state=active]:border-emerald-500/40`
  - **Media Requests**: `text-rose-400`, `hover:ring-rose-400/80`, `data-[state=active]:text-rose-400 data-[state=active]:bg-rose-500/10 data-[state=active]:border-rose-500/40`
  - **Broadcast & Emails**: `text-amber-400`, `hover:ring-amber-400/80`, `data-[state=active]:text-amber-400 data-[state=active]:bg-amber-500/10 data-[state=active]:border-amber-500/40`
  - **Monitoring & Apps**: `text-sky-400`, `hover:ring-sky-400/80`, `data-[state=active]:text-sky-400 data-[state=active]:bg-sky-500/10 data-[state=active]:border-sky-500/40`
  - **Beta & Announcements**: `text-purple-400`, `hover:ring-purple-400/80`, `data-[state=active]:text-purple-400 data-[state=active]:bg-purple-500/10 data-[state=active]:border-purple-500/40`
  - **Discord Community**: `text-indigo-400`, `hover:ring-indigo-400/80`, `data-[state=active]:text-indigo-400 data-[state=active]:bg-indigo-500/10 data-[state=active]:border-indigo-500/40`
  - **Live System Logs**: `text-emerald-400`, `hover:ring-emerald-400/80`, `data-[state=active]:text-emerald-400 data-[state=active]:bg-emerald-500/10 data-[state=active]:border-emerald-500/40`
- **Zero Opacity Washes on Tab Switch**: Tab switches must be instantaneous client-side state transitions. Never wrap tab content in `opacity-50` or `isPending` transitions that dim the screen on click. For URL updates, use `router.replace(url, { scroll: false })` without `startTransition`.
- **Slot Inactive/Disabled Card Styling**: Unconfigured or optional slots (e.g. 4K Arrs or Kids Arrs) must use dashed borders (`border border-dashed border-border/40`) with muted text rather than container-wide `opacity-75` washes which make the whole panel look faded and inactive.

### 3. Multi-Platform Media Servers (Plex, Jellyfin, Emby) & Library Self-Selection
- **Distinct Server Brand Tokens**:
  - **Plex**: Amber badge (`bg-amber-500/10 text-amber-400 border-amber-500/30`)
  - **Jellyfin**: Purple badge (`bg-purple-500/10 text-purple-400 border-purple-500/30`)
  - **Emby**: Emerald green badge (`bg-emerald-500/10 text-emerald-400 border-emerald-500/30`)
- **Admin Server Whitelisting & Library Scoping**:
  - In Admin Settings (`AdminMediaServersPanel`), each server exposes toggles for `Allow Full Members to Self-Select` alongside clear indicators that Trial Account access is centralized in Access Control.
  - **Server Edit & Credential Transparency**: Jellyfin and Emby server cards include a dedicated `Edit` action button opening an edit modal. Administrators can modify the server display name and connection URL. The modal securely delivers and populates the saved decrypted API key for verified admins, with an interactive Show/Hide eye toggle and 1-click clipboard copy button, while displaying an active key badge (`Saved Key Loaded`).
  - **Multi-Scheme Reverse Proxy & Jellyfin 10.9/12+ Authentication**: Backend requests (`testMediaServerConnection`, `fetchMediaServerLibraries`, `syncUserMediaServerAccess`) send modern `Authorization: MediaBrowser Token="..."`, `X-Emby-Authorization`, `X-Emby-Token`, and `X-MediaBrowser-Token` headers, alongside an automatic `?api_key=` query parameter fallback to guarantee seamless communication through reverse proxies (Nginx Proxy Manager, Cloudflare) that may strip custom headers.
  - **Centralized Trial Safe Pool Governance**: Trial member library access is governed 100% centrally in `/settings/access` under Onboarding (`defaultTrialPlexLibraries` / "Trial Safe Pool / Restricted Shelf"). Per-server trial toggles are avoided to prevent fragmented or conflicting access rules.
  - When whitelisting specific libraries, render interactive checkbox pills for each discovered virtual folder or PMS section with high-contrast text and clean allowed counts.
- **User Self-Selection & Tier Capabilities**:
  - In User Profile (`UserMediaServersManager`), render an informative Tier Capabilities Banner highlighting Full Member privileges (unlimited media server and library self-selection across Plex, Jellyfin, and Emby, book library access, uncapped requests, and household sub-accounts).
  - Enforce server-side whitelist validation: any client tampering attempting to select unauthorized servers or hidden libraries is strictly filtered out before database persistence and API policy sync.
- **Profile Page Clean Minimal Cards & Coming Soon Gating**:
  - **Household Sub-Accounts & Profiles** and **Content Safety & Family Profile** are cleanly rendered as "Coming Soon • Beta" cards while library metadata tagging and parental rating filters remain in active development.
  - **Notification Preferences (User Opt-In Second Gate)**: Full granular control over user-targeted automated email categories (`emailRequestApproved`, `emailMediaReady`, `emailSubscriptionReminders`, `emailAnnouncements`, `emailSupportTickets`, `emailReferralRewards`). Acts as an authoritative second gate: even when an email passes global server settings and the admin approval queue, if the member has opted out of that notification category, it is automatically dropped and skipped with audit logging.
  - **Kids & Audiobooks Library Access Cards**: Excluded internal backend library dumps ("Managed Family Libraries" and "Detected Audiobook Libraries") to maintain member privacy and prevent empty badge artifacts.
- **Strict Full-Member Gating for Jellyfin & Emby**:
  - Emby and Jellyfin server options and add-ons (`jellyfin_access`, `emby_access`) are **strictly restricted to Full Members** (and Super Users / Admins). Note: `emby_access`, `music_streaming`, and `priority_requests` are marked unavailable (`isAvailable: false`) and filtered from the user account add-ons catalog until real backend integrations are deployed.
  - For Trial Members (`isTrialUser`), Jellyfin and Emby switches are locked/disabled (`checked={false} disabled={true}`) with a `Full Members Only` lock badge and a prominent locked informational banner: "Jellyfin & Emby multi-platform streaming is exclusively available for Full Members. Upgrade your membership pass to unlock."
  - Backend enforcement in `updateUserMediaServersAndLibrariesAction` and `toggleFreeAddonAction` strictly blocks and strips Jellyfin/Emby selections for trial users.
- **Interactive Step-by-Step Setup Guides (`MediaServerSetupGuideModal` & `PlexSetupGuides`)**:
  - Accessible via prominent "📖 Setup Guide" buttons on each Jellyfin/Emby card in `UserMediaServersManager`, inside the Free Add-ons catalog in `profile/page.tsx`, and auto-opened whenever a Full Member toggles ON a Jellyfin or Emby server for the first time.
  - Dedicated tabs in `PlexSetupGuides` (`getPlexSetupGuides()`) for Jellyfin and Emby with platform device icons.
  - 4-step interactive checklist:
    1. **Connect to Server Address**: Copyable server URL with 1-click clipboard copy and web client launch.
    2. **Sign In with Your Account**: Copyable configured username and password instructions.
    3. **Recommended Client Apps**: Swiftfin (Apple TV & iOS), official Jellyfin/Emby on Roku Channel Store, Fire TV, Android TV, Google TV, and web browsers.
    4. **Direct Play Optimization**: Instructions to set Remote Quality / Bitrate to Maximum / Auto for 100% Direct Play.
- **Native Jellyfin & Emby Active Playback Sessions & Remote Termination**:
  - **Admin Detailed Streams Matrix & User Dashboard Parity**: Active streams playing on monitored Jellyfin and Emby instances are queried natively via `/Sessions?activeWithinSeconds=960` and integrated seamlessly into `getAdminDetailedStreamsAction` and `getUserPlexHubData`.
  - **Telemetry Normalization**: Extracts canonical playback metrics: item title, season/episode badges (S01E05), progress bar and percentages, video/audio transcoding decisions, codecs (H264, HEVC, AAC), resolution (4K, 1080p, 720p), bitrates, client devices, and IP addresses.
  - **Brand Badge Styling**: Media server badges display signature brand tokens: Jellyfin uses a purple accent (`bg-purple-500/10 text-purple-400 border-purple-500/30`) and Emby uses emerald (`bg-emerald-500/10 text-emerald-400 border-emerald-500/30`).
  - **Interactive Remote Stream Termination (`killUserStream`)**: Users can terminate their own active Jellyfin and Emby streams directly from the dashboard, and administrators can terminate any stream across the cluster via `stopMediaServerSession` (`POST /Sessions/{sessionId}/Playing/Stop`).

### 4. Button-Led User Dashboard Architecture & Role Parity (`UserLaunchpad`)
- **DRY Launchpad Pattern**: Replace lengthy, text-heavy vertical card stacks with the touch-friendly `UserLaunchpad` (`src/components/dashboard/user-launchpad.tsx`) positioned immediately below the dashboard header.
- **Role Parity Standard (Super User = Full Member + Servarr)**:
  - **Super Users do NOT have a stripped-down or disconnected dashboard**. They share the exact same rich Full Member dashboard experience (My Plex Hub, AI Assistant, Book & Audiobook Library, Server Speed Test, Plex Setup Guides, Support Tickets).
  - The ONLY architectural difference is that `isSuperUser={true}` dynamically unlocks dedicated **🎬 Radarr Movies** and **📺 Sonarr TV Shows** quick-action buttons in an expanded 8-button launchpad grid (`grid-cols-2 sm:grid-cols-4 xl:grid-cols-8`).
  - Full Members receive the streamlined 6-button launchpad grid (`grid-cols-2 sm:grid-cols-3 xl:grid-cols-6`).
- **Free Trial Accounts (`TrialDashboardView`)**:
  - Compact glowing amber countdown pill header: `⏳ Free Trial: [X] Days Remaining` with `[View Pricing]` trigger.
  - 4-button launchpad (2x2 on mobile, 4 columns on desktop):
    1. 🎬 **Request Media** (`/discover`) with live remaining quota badge (`3 Movies • 3 TV Left`).
    2. 📺 **Plex Setup Guides** (modal trigger).
    3. ⚡ **Server Speed Test** (modal trigger).
    4. 💳 **Membership Pricing** (modal trigger with prorated monthly & annual calculations).
- **Headless Modal Trigger Pattern**:
  - Components like `ServerSpeedTest`, `PlexSetupGuides`, and `SupportTicketModal` support an optional `trigger?: React.ReactNode` prop. When provided, the dialog renders the custom launchpad card as its `DialogTrigger` without duplicate state or detached trigger buttons.
- **Admin Mission Control Immunity**:
  - The Administrator view (`isAdmin === true`) remains 100% strictly untouched, preserving the single-pane `AdminSystemHealthGrid`, `AdminDetailedStreams`, hardware telemetry meters, and 8-tool quick admin bar.

### 4. Account Settings Profile Prewarming & Dashboard Servers Launchpad
- **Account Settings SWR Prewarming (`getUserProfileBootstrapAction`)**:
  - Eliminates sequential request waterfalls by executing 10+ user profile queries in parallel and storing in RAM cache (`user_profile_bootstrap:${userId}`).
  - Warm cache hits return in <50ms with zero loading spinners or delayed layout shifts.
  - Automatically prewarmed during `prewarmUserSession` on login.
- **Quick-Access Dashboard Launchpad ("Servers & Libraries")**:
  - Mounted on the user dashboard launchpad grid (`UserLaunchpad`) with blue accent branding (`text-blue-400`, `bg-blue-500/10 border-blue-500/30`) and `Access` badge.
  - Links directly to `/profile` for 1-click management of Plex/Jellyfin/Emby servers, libraries, and add-ons.
- **Dashboard Paid Through Header (`PaidThroughHeader`)**:
  - Positioned at the top of the user dashboard view (`isMember`) and as a compact pill in the System Dashboard title header.
  - Renders active plan badge (`Annual Plan` / `Monthly Plan` / `Lifetime Pass`), pulsing indicator, exact `Paid Through: [MMMM d, yyyy]`, countdown days remaining, applied account credit, and 1-click direct link to `/profile` for renewal management.
- **Discrete Invite Banner (`PlexInviteBanner`)**:
  - Positioned unobtrusively below the AI Assistant card rather than commanding top billing.
  - Designed as a sleek, low-profile card (`bg-[#121218]/60 border-border/40`) with inline copy input and collapsible guide.

### 5. Send-to-Kindle Sender Update Notice Modal (`KindleSenderUpdateModal`)
- **Sender Address Lifecycle & Gating Rule**:
  - Outbound wireless Kindle delivery emails are dispatched from `kindle@domshomelab.com`.
  - When the outbound sender address is updated, Amazon requires that recipient Kindle users explicitly add `kindle@domshomelab.com` to their Amazon **Approved Personal Document E-mail List** (under *Manage Your Content and Devices → Preferences*).
  - To prevent delivery failures or silent document drops by Amazon, an interactive update modal (`<KindleSenderUpdateModal />`) is triggered:
    - **Trigger**: Displayed when an existing user with Send-to-Kindle set up (`user.kindleEmail` contains `@` and is not `"DIRECT_DOWNLOAD"`) goes to request an ebook or missing book in a series, or dispatches an existing ebook.
    - **Isolation**: Strictly NOT shown to users who do not have Send-to-Kindle enabled or who have already acknowledged the notice (`user.kindleSenderUpdateAcknowledgedAt !== null`).
    - **User Experience**: Features a 1-click clipboard copy button for `kindle@domshomelab.com`, a direct external link to Amazon's Personal Document Settings, step-by-step instructions, and an "I've Updated My Settings" confirmation button that records acknowledgment in the database (`acknowledgeKindleSenderUpdateAction`) and immediately resumes the pending book request without requiring the user to re-click.

## 📐 Key Layout & Component Rules

### 1. Modals & Dialogs (Space Optimization, Bounded Widths & Horizontal Overflow Protection)
- **Radix Tailwind Merge Gotcha**: Base `DialogContent` contains `sm:max-w-lg`. Passing an unprefixed `max-w-6xl` gets overridden!
- **Rule**: Always pass explicit prefixed responsive classes for wide modals (Media Detail, Book & Audiobook Detail, Seerr requests, Episode Guide, Collection Builders), capping at `max-w-3xl lg:max-w-4xl` (or `max-w-4xl lg:max-w-5xl`) with `overflow-x-hidden` to prevent horizontal page spreading and off-screen button scrolling on standard desktop/laptop scaling:
  ```tsx
  className="w-[95vw] sm:w-[92vw] md:w-[90vw] max-w-3xl lg:max-w-4xl max-h-[90vh] sm:max-h-[92vh] overflow-y-auto overflow-x-hidden p-0 bg-[#0c0c12] border border-border/60 shadow-2xl rounded-2xl sm:rounded-3xl scrollbar-thin text-foreground"
  ```
- **CSS Grid `min-w-0` Child Blowout Prevention**: Because `DialogPrimitive.Content` renders as a CSS Grid, all child containers default to `min-width: auto`. Always wrap modal contents in `<div className="flex flex-col min-h-0 min-w-0 w-full overflow-x-hidden">` and add `min-w-0` to all sections. This prevents carousels with 20+ recommendations (e.g. 24 similar books) from overriding `max-width` and expanding the modal to 3,000+ pixels.
- **Primary Action Hierarchy**:
  - In all media and book request modals, always place the primary action button (`Request Ebook` / `Request Audiobook` / `Request Movie` / `Configure & Request` / `Request 4K UHD`) FIRST on the left of the action row, followed by secondary actions like "Watch Trailer" or "Close". This guarantees immediate 1-click access without requiring horizontal scrolling.
- **Similar Titles & Recommendations (Carousel vs Grid)**:
  - Inside detail modals, provide an inline horizontal scrolling carousel (`overflow-x-auto pb-2 scrollbar-thin scroll-smooth w-full min-w-0`) with left/right chevron buttons for instant browsing without layout expansion.
  - In dedicated grid tabs (Similar Titles, Cast & Crew), cap columns at `grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3` and add `min-w-0` to all card cells. Never use unconstrained 8-10 column grids (`xl:grid-cols-8 2xl:grid-cols-10`) which spread the modal out.
- **Zero Wasted Header Space**:
  - Use a compact hero backdrop layout with gradient fades (`bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent`).
  - Keep titles, badges (Year, Rating, Runtime, Status), and quick-action buttons aligned without massive empty top margins.

See detailed reference: [modal-and-dialog-patterns.md](./references/modal-and-dialog-patterns.md).

---

### 2. Media Cards & Posters (Strict 2:3 Proportions)
- **Strict Aspect Ratio**: Always enforce standard 2:3 vertical poster proportions (`aspect-[2/3]` or `h-[270px] w-[180px]`).
- **Plex Photo Transcode Dimensions**: In `/api/media/image` and PMS endpoints, pass `width=600&height=900` (never landscape `600x400` which crops portrait posters).
- **Extensive Non-Fiction Subtitles**:
  - In `BookCard`, `AudiobookCard`, and `MediaCard`, use `line-clamp-3 h-[60px] block` instead of `flex items-center` to avoid squishing long titles.
- **Grayscale Missing Stubs**:
  - Missing book or media stubs use `grayscale opacity-60 hover:opacity-90` with dashed amber/slate borders and `.portalarr-missing` immunity.

See detailed reference: [card-and-poster-patterns.md](./references/card-and-poster-patterns.md).

---

### 3. Forms, Autocomplete & Dirty State Management
- **Autocomplete Dropdowns**: Always use `onMouseDown` on dropdown suggestion items instead of `onClick` to prevent input `onBlur` from unmounting items before the click event fires.
- **Universal Unsaved Settings Protection Standard (`<UnsavedChangesPrompt />`)**:
  - All settings pages, curation studios, and administrative configuration panels enforce strict dirty tracking against baseline `initialDataRef` / `initialSettingsRef` snapshots.
  - **3-Layer Defense Contract**:
    1. **Docked Floating Save Bar**: Fixed at `bottom-6 right-6 z-50` with pulsating amber indicator, modified sections summary (`● Unsaved Settings (N)`), Discard button, and primary Save button.
    2. **In-App Navigation Interception Guard**: Intercepts link clicks (e.g. sidebar navigation, header logo, in-app redirects) using capturing `document.addEventListener("click", handleLinkClick, true)` and displays an interactive modal dialog offering `Stay on Page`, `Discard & Leave`, and `Save & Continue`.
    3. **Browser Tab Close & Reload Guard**: Listens on `window.beforeunload` whenever `hasUnsavedChanges === true` to prevent accidental tab closing or page refresh.
  - **Embedded Sub-Panel Dirty & Imperative Save/Discard Protocol**: Child panels mounted within parent settings hubs (e.g. `SeerrSettingsPanel`, `DiscordSettingsPanel`, `AdminMediaServersPanel`, `UserMediaServersManager`) accept `onDirtyChange?: (isDirty: boolean, dirtySections?: string[]) => void` and expose an imperative handle (`ref?: React.Ref<{ saveAllDirty: () => Promise<boolean>; discardAllDirty: () => void; }>`). Parent pages retain these panels in the DOM using CSS class toggling (`className={subTab === "active" ? "space-y-6" : "hidden"}`) rather than unmounting conditionally, ensuring in-progress form inputs and imperative refs remain intact across subtab switches. When the parent master floating save bar triggers "Save All Changes" or "Discard", it imperatively executes `panelRef.current.saveAllDirty()` or `panelRef.current.discardAllDirty()`, while saving single cards immediately updates baseline snapshots to clear dirty state.
  - **100% Page Coverage**:
    - **System Settings Hub (`src/app/settings/page.tsx`)**: Dirty tracking for General, Public URL, SMTP, Plex server tokens, Direct SQLite DB snapshot presets/paths, Servarr/Requests (`SeerrSettingsPanel`), Media Server Fleet (`AdminMediaServersPanel`), Discord Bot (`DiscordSettingsPanel`), Curation keys, and Roadmap/Beta text.
    - **Access Control (`src/app/settings/access/page.tsx`)**: Full `<UnsavedChangesPrompt />` tracking onboarding gates, role permissions, trial quotas, and Discord role mappings.
    - **User Profile (`src/app/settings/profile/page.tsx` & `/profile`)**: Tracks profile info, passwords, shared Plex libraries, notifications, content safety, and `UserMediaServersManager` server access and library whitelist preferences (`isMediaServersDirty`).
    - **Curation Studios (`KometaStudio`, `AgregarrStudio`, `PruneStudio`, `TaggingStudio`)**: Standardized on `<UnsavedChangesPrompt />` guaranteeing navigation modal interception and beforeunload guards across all 4 studios.
    - **Script Editor Modal (`src/components/scripts/script-editor-modal.tsx`)**: Protects script content, interpreters, schedules, and timeouts against accidental outside-click dismissals.
- **Sensitive Fields**:
  - Mask tokens and passwords by default (`type={showToken ? "text" : "password"}`).
  - Provide an inline toggle button with Lucide `<Eye />` / `<EyeOff />`.
- **Live Connection Diagnostics**:
  - Provide a dedicated `"Test"` button next to server/app URLs and API tokens with `<Loader2 className="animate-spin" />` feedback.
- **Multi-Profile Settings & Password Confirmation**:
  - Snapshot sub-profiles individually (`initialSafetyPrefsRef.current[profileId]`) so dirty state is scoped properly across primary, living room, and kid accounts.
  - Require explicit "Confirm New Password" verification inputs with eye visibility toggles to prevent typo lockouts.
  - Support `"DIRECT_DOWNLOAD"` bypass mode on Kindle integration without false email validation rejections.

See detailed reference: [form-and-input-patterns.md](./references/form-and-input-patterns.md).

---

### 4. User Authentication, Deep Link Redirection & Frictionless Login UX
- **Safe `returnTo` Deep Linking**:
  - Whenever an unauthenticated user visits a protected route (e.g. `/requests?tab=books&query=dune`, `/library`, `/tickets`, `/profile`), `src/proxy.ts` preserves the destination path and search query via `?returnTo=${encodeURIComponent(pathname + search)}`.
  - On both Password and Plex login, sanitize `returnTo` (ensure it starts with `/` and not `//` or `/\\` to prevent open redirects) and navigate directly to the intended destination instead of resetting users back to `/`.
  - If an already-authenticated user navigates to `/login?returnTo=...`, `proxy` immediately routes them to their intended destination.
- **Resilient Multi-Alias Account Matching**:
  - Match user credentials against `username`, `email`, `plexUsername`, and `plexEmail` (case-insensitively and whitespace trimmed).
  - Users auto-provisioned via Plex who do not remember their unique auto-generated local username/email can seamlessly sign in or reset passwords using their original Plex username or Plex email address.
  - When resetting passwords for Plex-provisioned accounts, Portalarr dispatches the temporary password to their verified `plexEmail` and heals placeholder `@plex.local` addresses.
- **Mobile Popup Blocker Fallback & CapsLock Detection**:
  - If a mobile browser (iOS Safari, Android Chrome) or strict desktop setting blocks the Plex login popup, render an immediate 1-click fallback button (*"Popup blocked? Tap here to authorize on Plex.tv"*) opening the authorization URL in a new tab while continuing background PIN polling.
  - Provide a 8-second grace period on `popup.closed` detection to prevent premature polling termination when users switch to password managers or 2FA authenticators.
  - Include an interactive show/hide password toggle (`Eye` / `EyeOff`) and a real-time CapsLock detection badge (*"Caps Lock is ON"*) on all password fields.

- **Semantic Subtab & Hash Navigation Standards**:
  - **Two-Tier Hub & Subtab Resolution**: When nesting sub-panels (e.g. in `src/app/settings/page.tsx` and `src/app/settings/access/page.tsx`), parent tab resolvers must never drop child subtab parameters to `""`. Inter-tab jump buttons (e.g. jumping from PMS tokens to Media Servers fleet) must call explicit subtab transition handlers (`handleSubTabChange("servers", "fleet")`) rather than generic hub changes to eliminate silent self-referential no-ops.
  - **Post-Loading DOM Hash Jump Guard**: On pages that render conditionally during data fetching (such as `/profile` or `/settings/access` displaying full-page loaders), browser-native hash jumps fail on initial mount because the target elements do not yet exist in the DOM. Always mount a `useEffect` that listens for `!loading` and triggers `document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" })`, paired with a `window.addEventListener("hashchange", ...)` listener so that deep links (`/profile#kindle`, `/profile#referral`, `/profile#billing`, `/settings/access?tab=onboarding#trial-safe-pool`) always scroll cleanly into view.

---

### 5. Responsive Media Grids
Use dynamic wrapping columns optimized across all screen breakpoints:
```tsx
className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 3xl:grid-cols-8 gap-3 sm:gap-4 lg:gap-5"
```

---

### 5. Dense Grid Dropdowns, Slider Bounding & Title Formatting
- **Badge Toggles & Slider Controls**: Never nest horizontal `sm:grid-cols-2` inside an outer multi-column card. Stack Placement dropdowns (`h-7.5 w-32 shrink-0`) and Scale Size sliders vertically with `w-full min-w-0` on range inputs inside `max-w-[150px]` flex containers to prevent dropdowns from overlapping sliders and sliders from overflowing card boundaries.
- **Collection Card Titles**: In flex header wrappers, avoid hardcoded pixel max widths (like `max-w-[200px]`) with `truncate` on titles that cause clipping when multiple status badges (like `Placeholders: ON`, `Limit: 20`, `Seasonal`) are active. Allow titles to breathe naturally (`font-bold text-white text-xs sm:text-sm tracking-tight`) alongside wrapping badges.
- **Dense Discovery & Sandbox Grids (`min-w-0` & Select Truncation)**: In multi-column discovery toolbars (e.g. Maintainerr Oldest Files Discovery & Rule Sandbox), avoid forcing `lg:grid-cols-6` without intermediate breakpoints. Use `grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3`, give every cell `min-w-0`, and add `w-full min-w-0 truncate [&>span]:truncate [&>span]:block` to `SelectTrigger` and `SelectValue` to prevent text-heavy options from expanding and overlapping neighboring dropdowns.
- **Radix UI `SelectTrigger` Width & Truncation Guard**: In `select.tsx` and all forms, `SelectTrigger` MUST enforce `w-full min-w-0` with `*:data-[slot=select-value]:truncate` so option labels never blow past column widths.
- **Studio Schedule & Automation Card Layouts**: When configuring multi-parameter studio schedules (e.g. Kometa Overlays, Agregarr, Maintainerr, Tagging) within side-by-side cards (`grid-cols-1 lg:grid-cols-2`), avoid placing 3 select controls in a single 3-column row (`sm:grid-cols-3`). Instead, give the **Schedule Frequency** dropdown full width on Row 1 to accommodate descriptive text, and place secondary sub-options (**Scope** and **Batch Size**) side-by-side in a 2-column subgrid (`grid grid-cols-1 sm:grid-cols-2 gap-2.5`) on Row 2. Ensure all grid cells and parent cards have `min-w-0`.
- **Interactive Stepped Range Sliders & Tier Cards Pattern**:
  - When configuring stepped thresholds or permissions (e.g. AI Autonomy Levels 1-3, Max Daily Interactions 1-10), pair an `<input type="range" />` track slider with direct, clickable tier preview cards.
  - Slider track styling: `w-full h-2.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer accent-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-400/50`.
  - Provide interactive text labels beneath the track with `text-[11px]` and bold color accents when active.

---

### 6. Route Aliases, Error Boundaries & Safe Date Rendering
- **Route Alias Pages**: Whenever a route alias exists (e.g. `/profile` mirroring `/settings/profile`), the wrapper `page.tsx` must explicitly include `"use client";` at the top and export a React component. Bare `export { default } from ...` across route folders breaks Next.js App Router client reference manifests in production.
- **Safe Date Formatting (`safeFormatDate`)**: Never pass unverified strings or objects directly into date-fns `format(new Date(val))` without validating `!isNaN(new Date(val).getTime())`. Invalid dates throw `RangeError: Invalid time value` which crashes the entire page into Next.js's fallback error boundary.
- **Global Error Boundaries (`error.tsx`)**: The app includes a root `src/app/error.tsx` boundary with graceful recovery buttons (`Try Again`, `Return to Dashboard`), preventing Next.js default blank crash screens.
- **Admin Exemption in Account Views**: Administrators must never display subscription plans, renewals, or expiration dates; their status must render as `Platform Administrator (Permanent Access)`.
  - Tier cards highlight with semantic ring and border glows (`ring-1 ring-emerald-500/50 bg-emerald-950/30 border-emerald-500/80` for Autonomous, `ring-amber-500/50 bg-amber-950/30 border-amber-500/80` for Assisted, `ring-sky-500/50 bg-sky-950/30 border-sky-500/80` for Advisory).
  - Clicking any tier card immediately synchronizes the range slider and dirty-state tracking without page reloads.

---

### 6. Inline Service & Server Monitoring Toggles (Selective Opt-In Pattern)
- When presenting monitorable hosts, apps, or media servers (`PlexServer`, `TautulliInstance`, `GlancesInstance`, `MediaApp`), provide a compact inline switch with state label:
  - Container: `flex items-center gap-1 bg-muted/40 px-2 py-0.5 rounded-md border border-border/40`
  - Active: Emerald text with glowing dot `<span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Monitored`
  - Paused: Slate text with muted dot `<span className="w-1.5 h-1.5 rounded-full bg-slate-500" /> Paused`
  - Behavior: Instant optimistic toggle calling dedicated server actions (`togglePlexServerMonitoringAction`, `toggleTautulliMonitoringAction`, etc.) with zero full-page reloads.
  - Plex.tv Discovered Servers: Display passive inventory from linked accounts with `+ Add & Monitor` and `+ Add (Paused)` actions, ensuring unconfigured servers are never auto-probed or marked down.

---

### 7. Multi-Resolution Responsive Layout System (Mobile, 720p, 1080p, 4K)

- **Mobile Phones (`< 640px`)**:
  - Container padding: `p-2.5 sm:p-4 md:p-6 lg:p-8 3xl:p-10`.
  - Poster grids: Standardize on `grid-cols-2 sm:grid-cols-3` so mobile displays show a clean 2-card grid without excessive vertical scrolling.
  - Action toolbars: Always wrap controls with `flex-wrap gap-2 w-full sm:w-auto`, allowing search inputs and filter selects to collapse gracefully to full width on mobile (`w-full sm:w-64` or `flex-col sm:flex-row`).
  - Dropdown & Select Truncation: Every select trigger must include `w-full min-w-0 truncate` to prevent long option text from breaking out of the viewport.
  - Slide-out Mobile Sidebar: Ensure drawer body has `flex-1 overflow-y-auto min-h-0` with touch-friendly tap targets (`min-h-[38px]`).
  - **Admin Mission Control & User Switcher Stack**: Never fix impersonation selects and "Return to Admin" buttons side-by-side with fixed `w-full` or `shrink-0`. Use `flex-col sm:flex-row items-stretch sm:items-center` so controls stack neatly at 100% width on phone screens.
  - **Telemetry Toolbars & Action Buttons**: Button bars with 3+ tools (e.g. "Stream Intelligence Hub", "Watch History & Audit", "Refresh") must use `flex-wrap gap-1.5 sm:gap-2 w-full sm:w-auto` with responsive mobile labels (`<span className="hidden sm:inline">Stream Intelligence Hub</span><span className="sm:hidden">Intelligence</span>`).
  - **Stream Telemetry & Codec Badges**: Video and audio badges containing full transcode paths (`CONVERT (TRUEHD 7.1 ➔ EAC3 Stereo)`) must include `max-w-full break-all sm:break-normal` with `min-w-0` on parent containers to prevent wide badges from spreading cards beyond the mobile viewport.
  - **Filter Bars with Search & Category Dropdowns**: Never place category dropdowns with lengthy labels alongside search inputs in an unconstrained flex row. Wrap with `flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full md:w-auto` and give inputs full width on mobile (`w-full sm:w-44` / `w-full sm:w-56`).
  - **Download Queue Rows**: Stack release title above bandwidth/ETA badges on mobile (`flex-col sm:flex-row sm:items-center items-start gap-1 sm:gap-3`) to give release titles 100% width and prevent truncated unreadable filenames.
- **720p Displays (`1280 x 720` / Compact Height Viewports)**:
  - **Vertical Height Defense**: Total browser viewport height is often under 650px. Dialogs and modals must strictly constrain height with `max-h-[85vh]` or `max-h-[88vh]` and place `overflow-y-auto` on the inner body container.
  - Sidebars: Both desktop and mobile sidebars must use `h-full min-h-0` with `flex-1 overflow-y-auto` so the footer logout button and bottom items remain accessible.
  - Dense grids: Use intermediate breakpoints (`md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5`) so items do not crowd before reaching 1080p.
- **1080p Displays (`1920 x 1080` Full HD)**:
  - Standard desktop baseline: 5 to 6 poster cards (`xl:grid-cols-5 2xl:grid-cols-6`), 2 to 3 widget cards (`lg:grid-cols-2 xl:grid-cols-3`), balanced typography and generous breathing room.
- **4K UHD & Ultrawide (`2560px` to `3840px`)**:
  - **No Stretched Monoliths**: Wrap outer content in `max-w-[2560px] mx-auto w-full min-w-0` to prevent single form inputs or text lines from spanning 3800px.
  - **Scalable Grids**: Scale grids beyond `2xl` with native Tailwind v4 `3xl:` and `4xl:` breakpoints (`3xl:grid-cols-7 4xl:grid-cols-8` or `3xl:grid-cols-8 4xl:grid-cols-10` for posters; `3xl:grid-cols-3 4xl:grid-cols-4` for dashboard cards) so cards maintain optimal 2:3 proportions and avoid giant 500px wide cards.
  - Detail Modals: Expand wide modal caps to `2xl:max-w-7xl 3xl:max-w-[1800px]` on 4K so rich media detail views utilize the expansive screen real estate.

---

### 7. Member Onboarding & Invitation Gateway (`/join`)
- **Private Server Invite Gate**: Direct visitors without a valid `?ref=` query parameter are gated at Step 0. They cannot access the onboarding flow until entering a valid referral code or active member reference (`name` or `username`).
- **Layout Header Isolation**: On `/join`, all user navigation headers (Book Library, Guides, Account Settings, System Settings) are strictly hidden via `layout-wrapper.tsx` (`!pathname.startsWith("/join")`).
- **Trial vs Full Membership Framing (Upgrade Perks)**:
  - **Free Trial**: A risk-free preview giving full access to stream movies and TV shows on Plex, 100% Direct Play Original Studio Quality (4K HDR, Dolby Vision, Dolby Atmos), all devices (Apple TV, Roku, Fire TV, Smart TVs, Phone, Web), movie & TV requests, with no payment up front.
  - **Full Membership Upgrade Perks**: Frame full membership as unlocking all the extra perks: priority bandwidth streaming, full Ebook & Audiobook Library with in-browser Kindle Paperwhite reader & Send-to-Kindle delivery, dedicated Kids & Living Room sub-account profiles with PIN safety & age ratings, 1-click book requests, and Discord community rewards. Never use negative/restrictive phrasing like "trial members do not receive". Frame the trial as the preview and upgrading as unlocking the extra perks.
- **Prorated Rest-of-Year & Monthly Option Display**:
  - Transparently display both flexible month-to-month ($15/mo) and annual prorated rest-of-year passes across Step 1 (Welcome & Perks Comparison) and Step 5 (Subscription Info & Ready to Stream).
  - Annual plans strictly derive their monthly base rate from `yearlyPrice / 12` ($180 / 12 = $15.00/mo), never an inflated standalone monthly price.
  - Formula: `proratedMonth = (daysRemaining / totalDaysInMonth) * 15`, `fullMonths = remainingFullMonths * 15`. Total amount due now = `proratedMonth + fullMonths`.
  - Pass the registered `username` into `<PaymentMethodsGrid />` to pre-fill the username in the payment memo tag and allow instant switching between Annual and Monthly cadences in the QR modal.
- **Payment Method Wording**:
  - Strictly avoid mentioning credit cards; state "No payment up front. Stream completely free during your trial." P2P payment methods (Venmo, PayPal, CashApp, Zelle) are used for future renewals.

---

### 8. Dynamic Branch, Version & Build Telemetry (`BuildBadge` & `getBuildTelemetry`)

Portalarr features an automated, real-time versioning, branch identification, and build-workflow tracking system. It enables homelab administrators to look at any dashboard and immediately differentiate **Beta preview environments (`main` branch)** from **Production release environments (`stable` branch)**:

- **Telemetry Engine (`src/lib/version.ts`)**:
  - `getBuildTelemetry()` automatically resolves: `version`, `branch` (`main` vs `stable`), `commitSha`, `commitShortSha` (first 7 characters), `buildNumber` (GitHub Actions run number), `buildTimestamp`, `channel` (`beta` | `stable` | `dev`), `isBeta`, `isStable`, `displayBadge`, `fullDisplay`, `workflowUrl`, and `dockerImageTag`.
  - Works seamlessly on both client and server components with zero network overhead.
  - Automatically baked at build time via `next.config.ts` (`NEXT_PUBLIC_PORTALARR_VERSION`, `NEXT_PUBLIC_GIT_BRANCH`, `NEXT_PUBLIC_GIT_SHA`, `NEXT_PUBLIC_BUILD_NUMBER`, `NEXT_PUBLIC_BUILD_TIMESTAMP`) and Dockerfile build arguments (`GIT_BRANCH`, `GIT_SHA`, `BUILD_NUMBER`).

- **Interactive Build Badge (`src/components/build-badge.tsx`)**:
  - **Compact Variant (`variant="compact"`)**:
    - Embedded in the top of Desktop and Mobile sidebars right next to the app brand header.
    - Beta (`main`): Glowing neon purple pill with pulsing indicator (`bg-purple-500/15 text-purple-300 border-purple-500/30`, e.g. `BETA • v1.0.0-beta.1`).
    - Prod (`stable`): Emerald pill with steady dot (`bg-emerald-500/15 text-emerald-300 border-emerald-500/30`, e.g. `PROD • v3.0.0`).
  - **Full Variant (`variant="full"`)**:
    - Embedded on the home dashboard header (`src/app/page.tsx`) immediately adjacent to the `System Dashboard` title.
    - Displays channel icon (`FlaskConical` for Beta, `ShieldCheck` for Prod), channel name, version, commit short SHA (`[2cf7cdf]`), and build run badge (`build #142`).
  - **Subtle Variant (`variant="subtle"`)**:
    - Minimalist monospace branch, build, and SHA breadcrumb rendered in sidebar footers or headers (`main • #142 • 2cf7cdf`).
  - **Interactive Build Diagnostics Dialog (`Dialog`)**:
    - Clicking any `BuildBadge` opens a glassmorphic diagnostics modal displaying: Environment Status, Active Git Branch, Full Commit SHA with 1-click clipboard copy, GitHub Actions Workflow Run number, Build Timestamp, Target Docker Image (`ghcr.io/plexd281knilb/portalarr:main` vs `:stable`), and a direct link to GitHub Actions workflow runs.

---

### 9. Consolidated Email Management & Trigger Documentation (`/settings?tab=emails`)
- **Single Authoritative Email Hub**: Outgoing email dispatches and notification master switches are strictly consolidated inside `<EmailManagement />` on Tab 3 (`/settings?tab=emails`), eliminating obsolete duplicate cards in Tab 1 ("General & Setup"). The General SMTP card provides a direct 1-click navigation button to the Email Hub.
- **Exact Trigger Event Documentation**: Every email template definition includes an explicit, user-facing `triggerEvent` field. The UI displays this with a `Zap` icon in both the template selection sidebar and a prominent callout card in the template editor header.
- **Automated Payment Receipts & Upgrade Notifications**: Incoming payments verified via automated IMAP scraping or manual attribution dispatch the `payment_received` receipt to the user and `admin_payment_received` alert to admins. Upgrades from trial or pending to full membership automatically dispatch `subscription_activated` detailing all unlocked perks.
- **Bidirectional Approval Gate Integration in Dispatch Controls (`subTab === "notifications"`)**:
  - **Governance Summary Banner**: Positioned right above the category grid, rendering the master gate toggle (`requireApprovalForEmails`), status badge (`🔒 Approval Gate Active` vs `⚡ Gate Bypassed`), 1-click presets (`⚡ Auto-Send Kindle Only`, `Stage All`, `Auto-Send All`), and a jump button directly to `/settings/access?tab=approvals`.
  - **Per-Category Approval Gate Toggles**: Every one of the 12 notification category cards features a dedicated bottom row with `FolderCheck` icon, status badge (`🔒 Staged` vs `⚡ Auto-Send`), and an inline toggle switch to control whether that notification type is held for admin review or auto-sent via SMTP.
- **Inline Template Approval Control (`subTab === "templates"`)**:
  - Directly inside the template customization editor header, an **Action Approval Gate** card allows administrators to inspect and toggle the staging requirement for the currently selected template without having to switch tabs.

---

### 9. Admin Approval Gates & Governance (`/settings/access`)
- **Strict Dual-Gate Governance**: Two independent switches in Access Settings govern automated system mutations:
  - `requireApprovalForPlexChanges` (default `true`): When enabled, NO modifications to live Plex library shares (new trial invites, user preference updates, manual library expansions, or trial/subscription expirations) are applied immediately to Plex servers. Instead, all proposed modifications are staged as `PENDING` records in the `AdminApproval` queue (`PLEX_ACCESS_GRANT` or `PLEX_ACCESS_REVOKE`).
  - `requireApprovalForEmails` (default `true`): When enabled globally, automated user-facing emails are held in `AdminApproval` (`EMAIL`) until explicitly approved, unless configured to auto-dispatch under the Granular Email Approval Policy.
- **Granular Outgoing Email Approval Policy (`emailApprovalPolicy`)**:
  - Provides template-by-template governance over every email type in the system.
  - Unconditionally accessible on `/settings/access` under the Approval Queue tab (displaying an amber informational banner if the master gate is currently inactive).
  - Individual switches allow administrators to require approval or permit immediate automatic dispatch via SMTP (e.g. unchecking `kindle_delivery` allows Send-to-Kindle book deliveries to transmit immediately without admin bottlenecking).
  - Quick action presets: `⚡ Auto-Send Kindle Only` (sets Kindle templates to auto-send while retaining approval on account/subscription emails), `Require All`, and `Auto-Send All`.
  - Filter by search and category pills (`All`, `Kindle`, `Requests`, `Auth`, `Trials`, `Payments`, `Support`, `Broadcast`).
- **Admin Pending Approval Notifications & Alerts**:
  - `notifyAdminOnPendingApproval` (default `true`): Automatically notifies administrators whenever an action (Plex access change or staged email) enters the Action Approval Queue requiring review.
  - Multi-channel notification delivery:
    - **Discord Bot / Webhook Alerts (`adminApprovalDiscordNotify`)**: Posts rich amber embeds (`0xF59E0B`) to `#system-status`, request channel, or webhook with action type, target entity, queue status, and direct link.
    - **Admin Review Emails (`adminApprovalEmailNotify`)**: Dispatches branded HTML alert emails via SMTP to all `ADMIN` and `SUPER_USER` accounts with 1-click review buttons (`bypassApproval: true`).
- **Admin Alert Immunity**: Direct alerts sent to administrators (e.g. `admin_payment_received`, new user account requests, AI bot escalation tickets) pass `bypassApproval: true` so administrators receive timely system alerts without self-blocking their own notification channels.
- **Interactive Review Queue**: Accessible on `/settings/access`, offering instant status filters (`PENDING`, `APPROVED`, `REJECTED`, `ALL`), type filters (`EMAIL`, `PLEX_ACCESS_GRANT`, `PLEX_ACCESS_REVOKE`), batch approvals (`Approve All`), batch rejections (`Reject All`), payload inspection modals, and custom rejection reason tracking.

---

### 10. Trial User Perk Framing & Access Isolation (`/settings/profile`)
- **Positive Perk Framing (Preview vs Unlocked Membership)**:
  - Trial users (`status: "TRIAL"`, `role: "USER"`) experience a clean, curated preview of core media server features.
  - Never use restrictive, punitive, or negative phrasing ("trial members do not receive..."). Instead, frame all advanced features as exciting **Full Member Perks** that unlock upon upgrading to full membership.
- **Referral Rewards & Invite Links**:
  - Trial users do NOT receive active referral codes or invite links to share. Referral rewards ("Earn 1 Free Month per converted friend") and active invite links unlock with full annual or monthly membership.
  - When `isTrial` is true, the Referral card highlights this perk with a direct 1-click button to view membership options (`#billing`).
- **Server & Section Isolation (Kids & Backup Servers Strictly Excluded)**:
  - Trial users are strictly restricted to standard primary server libraries (e.g. `MainPlexServer` movies and TV shows).
  - Kids servers (`KidsPlexServer`, sections with `Kids`) and backup servers (`MainPlexServerBackup`) are strictly filtered out on both server (`getUserAllowedPlexLibrariesAction`, `updateUserSelectedPlexLibrariesAction`, `syncUserPlexShareInternal`) and client (`isSectionAllowed`).
- **Household Sub-Accounts & Profiles**:
  - Secondary profiles (Living Room TV with severe nudity filtering, Kids account with PG ratings ceiling) are exclusive full member perks.
  - Trial users see clean perk preview blocks and "Unlocks with Full Membership" actions linking to subscription options.
- **Account Add-Ons & Features**:
  - Separated optional free add-ons: **E-Books & Reading Access** (`ebooks`, `icon: "book"`, unlocks Kindle delivery and browser reader) and **Audiobooks Plex Library Access** (`audiobooks`, `icon: "headphones"`, unlocks narrated audiobook streaming directly through Plex and updates live Plex sharing permissions).
  - Dedicated **Audiobooks Plex Library Access Card** (`#audiobooks-library`, `purple-500/30`) in Account Profile (`/settings/profile`) allowing users to opt into or out of the Audiobooks library section with automated PMS share syncing (`syncAudiobooksPlexLibraryAccessForUser`).
  - Optional add-ons display "Unlocks with Full Membership" buttons for trial users.
  - Backend actions (`toggleFreeAddonAction`, `updateUserAudiobooksLibraryAccessAction`, `createOrUpdateSubAccountAction`) strictly enforce full membership status.

---

### 11. White-Label & Domain Brand Isolation (`DomsHomeLab` & `d281knilb`)
- **Brand Identity Mandate**:
  - Homelab / Portal / Domain brand: **`DomsHomeLab`** (accessible at `home.domshomelab.com`).
  - Media server name: **`d281knilb`** (the canonical Plex server).
  - Outgoing email sender header: `"DomsHomeLab (d281knilb)" <${smtpFrom || smtpUser}>`.
- **Zero Generic Branding Leakage in User Communications**:
  - Never allow internal/generic software names (e.g. "Portalarr") to appear in outgoing email subjects, email body text, email header banners, or user-facing UI views. Users must instantly recognize the communications as coming directly from their trusted server host to prevent confusion or spam reports.
  - Email header banner: `DOMS<span style="color: #6366f1;">HOMELAB</span>` with subtitle `d281knilb Media Server & Dashboard`.
  - Email footer: `DomsHomeLab • d281knilb Media Server` with high-contrast, theme-resilient `Open Dashboard →` action button (deep indigo `#4f46e5` / `#6366f1` and pure white text for guaranteed WCAG AA legibility across dark and light modes, automatically deduplicated if already mounted inline within the email content) and `© {year} DomsHomeLab. All rights reserved.`.
- **Payment Reconciliation Memo Notes**:
  - Payment memo notes are cleanly formatted as the member's username (e.g. `johndoe`), making it simple and frictionless for members to include in transaction notes.
  - Payment scrapers retain backwards-compatible substring matching for plain usernames as well as legacy `#DOMSHOMELAB-`, `#D281KNILB-`, and `#PORTALARR-` tags.
- **Client & Device Dialogs**:
  - In Plex stream termination messages, prompt kill alerts as: `"Stream ended by user via DomsHomeLab My Plex Hub"`.

---

### 12. Admin Stream Matrix & Dual Telemetry Command Center (`admin-detailed-streams.tsx`)
- **Hardware Hosts vs Media Servers Differentiation**:
  - Homelabs frequently host multiple Plex instances (e.g. Primary Plex, Kids Plex, 4K Plex) across physical hardware machines (e.g. Unraid primary, secondary backup server).
  - Telemetry is split into a **Dual Telemetry Command Center** (`grid grid-cols-1 lg:grid-cols-2 gap-3`):
    1. **Host Hardware Telemetry (Glances)**: Renders physical hardware host nodes with live CPU & RAM percentage meters, color-coded threshold progress bars (emerald `<60%`, amber `60-80%`, rose `>80%`), and status badges (`ONLINE`, `PAUSED`, `OFFLINE`).
    2. **Streams Per Plex Server**: Renders strictly **monitored Plex servers with monitoring turned on** (`monitored !== false`), ranked descending by active playback volume (`streamCount`) and bandwidth. Unmonitored servers are strictly excluded.
- **Transcoding Power vs Audio Conversion Isolation**:
  - Transcoding power is exclusively consumed by video transcoding (`videoDecision === "transcode"`, e.g. GPU NVENC or multi-threaded CPU video rendering).
  - Audio transcoding (e.g. TrueHD or DTS to AAC/AC3/EAC3) takes negligible CPU and zero GPU power. It is classified as **Direct Stream** in Plex and is **NOT** counted as using transcoding power.
  - In cluster stats and server usage meters, `transcodeCount` strictly counts video transcoding (`videoDecision === "transcode"`). Audio-only transcoding is counted under Direct Play / Direct Stream.
  - In the session card, overall status displays an amber `TRANSCODING` badge only if video is transcoding; otherwise it displays `DIRECT STREAM` or `DIRECT PLAY`. The audio badge is cleanly styled as `CONVERT ({codec})` rather than a misleading `TRANSCODE` tag.
- **TV Show Season & Episode Formatting**:
  - For active TV episode streams, session cards display the canonical Show Title (`grandparentTitle`), a styled monospace Season & Episode pill badge (e.g. `S02E05`), and the Episode Title (`episodeTitle`), ensuring administrators instantly identify which installment is currently streaming.
- **Top Load Server Promotion**:
  - The server with the highest active playback count receives a prominent `#1 HIGHEST LOAD` badge with an animated flame icon and amber glowing border (`border-amber-500/30 bg-amber-500/[0.04]`).
- **Cluster Load Proportional Bars**:
  - Each server card displays a Direct Play vs Transcode split (`X DP / Y Transcode`), total bandwidth in Mbps, and a proportional horizontal load bar reflecting its percentage share of total cluster streams.
- **Interactive Server Filter Pills**:
  - Clicking any server in the Streams Per Plex Server list or the filter pill bar (`All Servers`, `Server 1`, `Server 2`) filters active playback sessions instantly on the client with zero network round-trips. Clear filter action resets back to cluster-wide inspection.
- **Deterministic Stream Sorting & Stationary Key Stability**:
  - Live streams across monitored servers are deterministically sorted on both backend (`getAdminDetailedStreamsAction`) and frontend (`StreamIntelligencePage` and `AdminDetailedStreams`), preventing stream cards from shuffling, flapping, or shifting positions during 5–8 second telemetry refresh cycles.
  - Primary sort options (`user_asc` [Default: User A → Z], `user_desc`, `server`, `bandwidth`, `progress`, `transcode_first`) persist across sessions via `localStorage` (`portalarr_live_activity_sort`).
  - Strict multi-tier tiebreaker chain (`primaryDiff` → `user` A-Z → `serverName` A-Z → `mediaTitle` A-Z → `sessionKey`) guarantees 100% stationary ordering across asynchronous network polling jitter.
  - Zero `Math.random()` session key fallbacks: session keys derive deterministically from `${ratingKey}_${machineIdentifier || address || user}_${serverId}`, ensuring React DOM nodes are never unnecessarily unmounted or recreated between renders.
- **Dialog Width Clamping Guard (`sm:max-w-4xl` / `sm:max-w-5xl`)**:
  - Radix `DialogContent` injects a default `sm:max-w-lg` class. Wide inspection cockpits (e.g. User Telemetry & Overlap modal, Watch History audit modal) must explicitly pass `w-[95vw] sm:w-[92vw] md:w-[90vw] max-w-5xl sm:max-w-5xl` with `min-w-0` to avoid viewport clamping on desktop and ensure side-by-side stream comparison cards fit cleanly.
- **Session Telemetry Fidelity & Household Anchoring**:
  - **User & Household Anchoring**: Active session cards display user avatars (from Plex or local profiles) alongside the **Household Anchoring Badge**: `🏡 Primary Home` (emerald, local LAN or anchored to primary living room IP), `🏡 2nd Home / Cabin` (cyan, recurring vacation property or secondary residence), `📱 Mobile Roaming` (purple, cellular/mobile roaming players), `✈️ Travel / Away` (amber, remote travel), and pulsing `🚨 Suspected Sharing` (rose, simultaneous playback across distinct public residential IPs or dual living room TVs).
  - **Connection Mode**: `⚡ Direct LAN`, `🌐 Direct WAN`, or `⚠️ Plex Relay (Throttled)`.
  - **Video & Dynamic Range**: Resolution scaling badges (`4K UHD ➔ 1080p` or original resolution), HDR badges (`✨ Dolby Vision`, `✨ HDR10`), video codecs, real-time bitrate, and hardware NVENC acceleration status with transcode speed multipliers (`⚡ 2.8x (Fast/Throttled)` vs `< 1.0x (Buffering Risk)`).
  - **Audio & Subtitle Diagnostics**: Channel and codec conversions (e.g. `TRUEHD 7.1 ➔ AAC Stereo` or `DTS-HD MA 5.1 (Direct)`), subtitle format/language (`💬 English SRT`), and prominent `🔥 Burned In` alert informing administrators when subtitle burn-in is forcing video transcoding.
  - **Timing Clock & Finish ETA**: Displays elapsed/total clock time paired with real-time calculated ETA finish time: `42:15 / 1:00:20 (70%) • Ends at 1:45 PM (-18:05 left)`.
  - In Plex OAuth flow, register client application name as `DomsHomeLab`.

---

### 13. Admin Infrastructure Health & Monitoring Cockpit (`admin-system-health-grid.tsx`)
- **Comprehensive Single-Pane Monitoring**:
  - Positioned at the very top of Admin Mission Control (`/`), aggregating all configured infrastructure services across 5 distinct categories:
    1. **Plex Media Servers** (Direct PMS status, API identity ping, latency)
    2. **Jellyfin Media Servers** (Native Jellyfin REST ping `/System/Info`, dual-URL fallback, server version, purple badge)
    3. **Emby Media Servers** (Native Emby REST ping `/System/Info`, dual-URL fallback, server version, emerald badge)
    4. **Host Hardware (Glances)** (Physical machines, CPU & RAM utilization, port 61208 status)
    5. **Stream Monitors (Tautulli)** (Active playback count, API reachability, port 8181/18181)
    6. **Servarr & Request Apps** (Radarr, Sonarr, Seerr, Ombi, Prowlarr, Bazarr, Maintainerr)
    7. **Download Clients** (SABnzbd, qBittorrent, NZBGet)
- **Visual Status Hierarchy & Pulse States**:
  - 🟢 **ONLINE**: Emerald indicator with pulse, verified reachable response, and round-trip ping latency badge (e.g. `14ms`).
  - 🔴 **OFFLINE / UNREACHABLE**: Crimson rose badge and animated beacon, surfaced prominently with promoted filter badge (`Down (X)`).
  - ⚪ **PAUSED**: Slate neutral badge indicating intentional opt-out (`monitored === false`) configured in Settings > Monitoring. No unnecessary network probing or false alarms.
- **Interactive Multi-Axis Filtering & Instant Search**:
  - Status filter pills (`All`, `Down`, `Online`, `Paused`) paired with category dropdown selector (`All Categories`, `Plex Media Servers`, `Jellyfin Media Servers`, `Emby Media Servers`, `Host Hardware`, `Stream Monitors`, `Servarr & Request Apps`, `Download Clients`) and client-side instant search input.
- **My Plex Hub Real Monitored Server Isolation (`my-plex-hub.tsx`)**:
  - In user-facing `MyPlexHub` connected servers dialogs and status counters, dummy, paused, or unmonitored Plex servers (`monitored === false`) are strictly filtered out so that only genuine, monitored Plex instances (`KidsPlexServer`, `MainPlexServerBackup`, `MainPlexServer`) are visible to members.

---

### 14. Scrollable TabsList & Device Selector Patterns (Negative Coordinate Overflow Protection)
- **Radix UI `TabsList` Default Justification**:
  - `TabsList` in `src/components/ui/tabs.tsx` defaults to `justify-center`.
  - When placing multiple tabs (e.g. 7+ device guides, indexers, or categories totaling >800px) inside a horizontal scroll container (`overflow-x-auto`), **never rely on default justification or `w-full` with `justify-center`**.
  - **The Negative Coordinates Bug**: If a centered flex container overflows horizontally, the browser centers the items and pushes the initial items into negative X coordinates (`x < 0`). Because standard LTR browsers cannot scroll into negative scroll offsets, the first item(s) (e.g., Apple TV) become permanently cut off and unreachable even when scrolling all the way to the left.
- **The Mandatory Solution**:
  - Always explicitly pass `justify-start` to `TabsList` inside horizontal scrolling containers:
    ```tsx
    <div ref={tabsRef} className="overflow-x-auto pb-2 pt-0.5 scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent scroll-smooth">
        <TabsList className="inline-flex items-center justify-start gap-1.5 p-1.5 bg-muted/20 border border-border/40 rounded-2xl min-w-full w-max h-auto">
            {items.map(item => (
                <TabsTrigger key={item.id} value={item.id} className="... shrink-0">
                    ...
                </TabsTrigger>
            ))}
        </TabsList>
    </div>
    ```
  - For wrapped lists, also specify `flex-wrap items-center justify-start` to ensure left-alignment across line breaks.
- **Chevron Scroll Controls**:
  - When tab lists exceed normal screen boundaries, provide subtle left (`ChevronLeft`) and right (`ChevronRight`) scroll buttons that programmatically execute `tabsRef.current.scrollBy({ left: -260, behavior: 'smooth' })`.

---

### 15. Layered Poster Thumbnail Containers & Graceful Image Fallbacks
- **Zero Broken Image Boxes & Mixed Content Prevention**:
  - Whenever rendering dynamic stream session posters, watch history rows, or media items in carousels and lists, never render raw un-proxied LAN URLs (`http://192.168.1.x:32400/...`) which fail in browsers over HTTPS (mixed content blocks) or on remote/VLAN devices.
  - Route all stream thumbnails through `/api/media/image` (or `formatWatchHistoryThumb`).
  - Implement the **Layered Fallback Poster Pattern**:
    ```tsx
    <div className="relative w-16 h-24 rounded-lg overflow-hidden shrink-0 bg-slate-950 border border-slate-800 flex items-center justify-center shadow-md">
        <div className="absolute inset-0 flex items-center justify-center text-slate-600">
            {mediaType === "episode" ? <Tv className="h-6 w-6" /> : <Film className="h-6 w-6" />}
        </div>
        {thumbUrl && (
            <img 
                src={thumbUrl} 
                alt={title} 
                className="w-full h-full object-cover relative z-10" 
                onError={(e) => { (e.target as HTMLElement).style.display = "none"; }}
            />
        )}
    </div>
    ```
  - The fallback icon (`Tv` or `Film`) is placed in the background layer (`absolute inset-0`).
  - If the image loads, it sits cleanly above on `z-10`.
  - If the image fails to load or 404s, `onError` sets `display: none` immediately without layout shifts, revealing the clean fallback icon underneath with zero broken image boxes.

---

### 16. Proactive Stream Quality Doctor Alert Banner (`stream-quality-doctor-banner.tsx`)
- **Proactive Main Screen Alerting**:
  - Automatically mounted at the top of the main screen (`/`) for all authenticated members directly below the header/user switcher.
  - Queries `getUserTranscodeAlertAction()` on mount; non-intrusive (returns nothing if all streams direct play).
  - Triggers if an active or recent stream (within 14 days) was downscaling/transcoding due to client default quality caps (e.g. Roku 720p auto-adjust bug, default 2-4 Mbps remote streaming limits on Apple TV, Fire TV, Android TV, Smart TVs, or web browser HEVC incompatibility).
  - Features an animated glassmorphic banner (`bg-amber-500/10 border-amber-500/30 text-amber-300`) with quick summary, "Fix in 30 Seconds" action button, and dismissible close.
  - Clicking "Fix in 30 Seconds" opens an interactive step-by-step resolution dialog tailored to the member's specific client device with 1-click clipboard copy of the guide.

---

### 17. Smart Account Sharing & Overlap Intelligence Engine (`/admin/tautulli` & `stream-tracker.ts`)
- **Household Device Anchoring (Fixed TV vs Mobile Roaming)**:
  - Living room devices (`isFixedHomeDevice`: Apple TV, Roku, Fire TV, Smart TVs, Google TV, Shield, PlayStation, Xbox) stay physically anchored to a household.
  - Mobile devices (`isMobileRoamingDevice`: iPhones, Android phones, tablets, cellular CGNAT, laptops, web browsers) roam legitimately.
  - Local LAN IP addresses (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, `localhost`) are strictly excluded from sharing suspicion.
- **Deterministic Multi-Household Overlap Detection (`analyzeUserAccountSharing`)**:
  - **Single Household (`CLEAN_SINGLE_HOME`)**: Exclusively LAN or single residential IP playback with zero remote cross-IP concurrency.
  - **Vacation / Travel (`VACATION_TRAVEL`)**: Remote IP usage span $\le 14$ days with 0 concurrent overlap with primary home base.
  - **Second Home / Cabin (`SECOND_HOME`)**: Recurring TV playback across $> 14$ days with 0 concurrent overlap at primary home base.
  - **Mobile Roaming (`MOBILE_ROAMING`)**: Roaming on cellular networks strictly on phones/laptops while fixed TVs remain anchored at home.
  - **High-Confidence Account Sharing (`HIGH_SHARING_RISK`)**: Concurrent simultaneous playback on $\ge 2$ physical living room TVs across distinct public residential IPs (`isDualTvOverlap`).
- **Telemetry Cockpit & Directory Integration**:
  - Filter pills in User Directory: `All Users`, `🚨 Suspected Sharing`, `🏡 2nd Home / Vacation`, `📱 Mobile Roaming`, `⚠️ Transcoders`.
  - Comprehensive inspection modal with 4th tab: **Sharing & Overlap Intelligence** rendering primary home IP, secondary location, device typology meter, and chronological timeline of concurrent overlap incidents with side-by-side stream comparison cards.

---

### 13. Media Request Quota Visibility & Zero-Limit Suppression Rules
- **Strict Zero-Limit Suppression**:
  - In Seerr and media request workflows, a quota limit of `0` denotes unlimited requests (e.g. Full Members or Admins).
  - Users without a quota limit (`limit === 0` or unlimited) **MUST NEVER** see any quota counter or label. Never display confusing strings like `"Quota: 999 of Unlimited"`.
  - The backend `getUserRequestQuotaAction` returns `remaining: null` when `limit === 0`.
- **Frontend Guard Pattern**:
  - In request modals (`media-detail-modal.tsx`), strictly guard quota text by:
    ```tsx
    {quotaInfo && quotaInfo.limit > 0 && quotaInfo.remaining !== null && (
        <span className="text-xs text-muted-foreground font-medium">
            Quota: <strong className="text-foreground">{quotaInfo.remaining}</strong> of {quotaInfo.limit}
        </span>
    )}
    ```
  - In trial dashboard views (`trial-dashboard-view.tsx`), wrap quota pills in `{(movieQuota.limit > 0 || tvQuota.limit > 0) && ...}` and guard each pill with `limit > 0` and `remaining ?? 0`.

---

### 14. Member Referral Crediting & Statement Discounting Patterns
- **Manual Referral Attribution & Crediting**:
  - In `/settings/access`, administrators can manually link and credit an existing member for a friend's join using the `Credit Referral` button on the user row or `+ Credit Member Referral` on the Referrals Leaderboard.
  - The modal provides select dropdowns for both the referring member and the friend who joined, with an option to immediately extend the subscription expiration date by +1 month (`extendSubscriptionExpiry: true`) or keep the date unchanged and apply the reward on the upcoming statement.
  - The modal features a live reactive statement preview card driven by `calculateUserRenewalSummary` displaying the exact annual renewal discount ($180 - $15 = $165) and the delayed monthly payment start date (e.g. pushed from Jan 1 to Feb 1).
  - **Annual vs Monthly Rate Isolation**: Free months earned off an annual plan strictly discount at the annual plan's monthly rate (`annualMonthlyRate = baseYearlyPrice / 12`, e.g. $15.00/mo for $180/yr), even when a higher flexible standalone monthly plan is configured (e.g. $17.50/mo). Standalone `monthlyRate` is preserved exclusively for the monthly alternative schedule.
- **Renewal Statement Notices**:
  - Admins can dispatch an instant `Renewal Notice` email from the user row with pre-calculated referral discounts and delayed monthly dates.
- **User Profile Subscription Card Transparency**:
  - In `/settings/profile`, approved subscribers with active referral credits see a purple `🎁 Referral Reward Applied` badge and a card detailing their discounted annual renewal ($165/yr instead of $180) or delayed monthly billing date (`delayedMonthlyStartDate`).

---

### 15. Manual Payment Recording & Calendar Alignment Patterns (`/settings?tab=payments`)
- **Manual Payment Recording Modal**:
  - In the Payments tab (`PaymentEmailManager`), administrators can manually log offline or direct payments via the `+ Record Payment` action button.
  - Features real-time member live search filtering by `name`, `username`, or `email`, currency amount input, payment date picker (defaults to today), method selection (`Venmo`, `PayPal`, `Zelle`, `Cash App`, `Cash`, `Other`), and internal notes.
  - Automatically recalculates and synchronizes the member's subscription expiration date, subscription status (`ACTIVE`), and membership tier (`STANDARD`).
- **Calendar Alignment Formula (`paymentCycleYear` & `baseTargetYear`)**:
  - When crediting annual payments ($180), late payments made on Jan 1 or Jan 2 of the new year credit that current calendar year (`baseTargetYear = payYear + 1`), aligning expiration to `Jan 1, <payYear + 1> 23:59:59.999` (e.g. paying on 1/2/2026 sets expiration to `1/1/2027`, NOT `1/1/2028`).
  - Pre-payments made on or after October 1 credit the following calendar year (e.g. paying on 12/31/2025 sets expiration to `1/1/2027`).
  - If a user is already paid through the current cycle (`existingExpiry` in 2027), re-attributing a 2026 payment does not compound or add extra years; it stays `1/1/2027`. Multi-year extensions require explicit surplus amounts (e.g. $360 for 2 years).
- **Zero Secret Backend Retention**:
  - Deleting, unmatching, or re-attributing a payment transaction to another member immediately triggers a clean sequential recalculation (`recalculateUserSubscriptionFromPayments`) for the previous user.
  - If no payments remain, the previous user's subscription cleanly expires (`status: "EXPIRED"`, `subscriptionEndsAt: null`), ensuring no ghost expiration dates or hidden credits persist.

---

### 16. Feature Guide Modals & Centralized Knowledge Base (`FeatureGuideModal` & `/guides`)
- **Interactive Contextual Guide Buttons (`FeatureGuideModal`)**:
  - Reusable modal dialog (`src/components/feature-guide-modal.tsx`) mounted via compact trigger buttons (`<FeatureGuideModal guideId="..." label="..." />`) across key feature headers:
    - AI Assistant header: `guideId="ai-assistant"`
    - Discover / Media Requests header: `guideId="movies-tv"`
    - Media Requests status view: `guideId="movies-tv"`
    - Library Books / Audiobooks / Kindle header: dynamic `guideId` switching between `ebooks`, `audiobooks`, `requests-pipeline`, and `kindle-setup`
    - My Plex Hub stream diagnostics: `guideId="stream-diagnostics"`
    - Settings Profile & Referrals card: `guideId="referral-rewards"`
    - Curation Studio shared nav bar (`CurationNavHeader`): `guideId="curation-studio"`
  - **Category Switching Inside Modal**: Users can switch between any of the 10 topics (`ai-assistant`, `movies-tv`, `ebooks`, `audiobooks`, `requests-pipeline`, `kindle-setup`, `stream-diagnostics`, `referral-rewards`, `curation-studio`, `general`) without leaving the dialog.
  - **Visual Elements**: Highlight pill tags with icons (`CheckCircle2`), numbered step cards, pro-tip callouts (`Sparkles`), important warnings (`AlertCircle`), and deep links to `/guides`.
- **Knowledge Base & Platform Guides Hub (`/guides`)**:
  - Centralized knowledge base supporting 8 master categories:
    - 📱 Streaming Devices (Plex direct play guides with left/right tab scrolling and pro-tips)
    - 🤖 AI Support & Storage Probes (active byte-range `Range: bytes=0-65535` media testing, stream diagnostics)
    - 🎬 Movies & TV Requests (Seerr requests, multi-tier fallback Prowlarr queries)
    - 📚 Ebooks & Kindle Reader (Kindle Paperwhite reader, Send-to-Kindle pre-flight checks, comics)
    - 🎧 Audiobooks & Chapters (multi-track consolidation, chapter selector, track reordering on disk)
    - 🎁 Memberships & Referrals ($15/mo referral discount calculations, payment QR, profile management)
    - 🎨 Server Curation Suite (Kometa ribbons, Agregarr hubs, Maintainerr prune rules, Tagging)
    - 📖 Full Platform Manual (`USER_GUIDE.md` Markdown viewer with instant search and inline Admin editor)
  - URL query parameter sync (`/guides?topic=ai-assistant` or `/guides?tab=devices`) with `<Suspense>` wrapper for Next.js App Router compliance.

---

### 17. Real-Time Session Expiration & Dual Cadence Reactivation (`/pending`)
- **Edge Session Expiration & Stale Cookie Trapping**:
  - `createSession` embeds ISO strings for `trialEndsAt` and `subscriptionEndsAt` directly into the signed JWT token payload.
  - `src/proxy.ts` validates `trialEndsAt` and `subscriptionEndsAt` against `Date.now()` on every incoming request. If a trial or subscription has elapsed in real time, `proxy.ts` dynamically treats `userStatus` as `"EXPIRED"` and immediately halts access, redirecting to `/pending` (or returning 403 on API calls).
  - Server components (`src/app/page.tsx`, `src/app/discover/page.tsx`, `src/app/requests/page.tsx`) and `LayoutWrapper` explicitly verify `user.status` from SQLite via `getCurrentUser()` and redirect any `EXPIRED`, `PENDING`, `REJECTED`, or `SUSPENDED` users immediately to `/pending`, completely preventing unauthorized viewing of the dashboard or requests when cookies are mid-renewal.
- **Dual Cadence Reactivation Selector (`/pending`)**:
  - When an expired or suspended user reaches `/pending`, they are presented with an interactive dual-plan selector:
    - **Annual Renewal**: Prorated rest-of-year amount due (e.g. `$39.19 for rest of 2026` @ $15/mo base), detailing exact months covered and future January 1 renewal.
    - **Flexible Monthly**: Month-to-month reactivation rate (e.g. `$15.00/mo` or prorated current month) with first-of-month renewal cadence.
  - Selecting either card immediately updates the Reactivation Amount Due, renewal breakdown text, P2P deep link pre-filled amounts (Venmo, PayPal, Cash App, Zelle), and pure-TS SVG QR code generator in `PaymentQrModal`.

---

### 18. Trial-to-Full Account Upgrade & Activation Transition Engine (`isTrial` & `membershipTier` Lifecycle)
- **Automatic Membership Tier Upgrades on Activation**:
  - Whenever an administrator grants access or activates an account (via `executePlexLibraryAccessUpdateInternal`, `setUserTrialOrSubscription`, `recalculateUserSubscriptionFromPayments`, or `markUserConverted`) using `REST_OF_YEAR`, `30_DAYS`, `1_YEAR`, `PERMANENT`, or `CUSTOM`:
    - `user.status` transitions to `"APPROVED"`.
    - `user.trialEndsAt` is cleared to `null`.
    - `user.subscriptionEndsAt` is set to the designated expiration timestamp.
    - `user.membershipTier` automatically upgrades from `"TRIAL"` (or null) to `"STANDARD"` (or preserves elevated tiers like `"TIER_2_VIP"` / `"PREMIUM_4K"`).
- **Strict `isTrial` Evaluation Pattern Across Codebase**:
  - Always enforce status check exclusion so an approved member is NEVER flagged as a trial user:
    ```tsx
    const isTrial = (user?.status === "TRIAL" || user?.membershipTier === "TRIAL") && user?.status !== "APPROVED" && user?.role !== "ADMIN";
    const isFullUser = isLoggedIn && !isAdmin && !isSuperUser && !isTrial;
    ```
  - Prevents approved accounts with active subscriptions from rendering `TrialDashboardView`, displaying 14-day trial countdowns, getting barred from secondary server libraries (kids/backup shares), or having profile features (referral links, add-ons, sub-accounts) locked behind trial gates.
- **Self-Healing in `getCurrentUser()`**:
  - If a user has `status: "APPROVED"` (or `role: "ADMIN"`) but their `membershipTier` in SQLite was still marked as `"TRIAL"`, `getCurrentUser()` automatically heals the database record to `membershipTier: "STANDARD"`, clears `trialEndsAt: null`, re-issues an updated persistent session cookie, and returns the healed user immediately.

---

### 19. Protective Curation Library Automation Guard Rails (`CurationLibraryGuardModal`)
- **Purpose & Scope**:
  - Guards against accidental manual executions, poster overwrites, collection pushes, pruning operations, or tag modifications on Plex libraries that are currently excluded/disabled from the automated curation schedule (e.g. `KidsPlexServer -> Movies` when only TV is monitored).
  - Deployed consistently across all 4 Curation Studios:
    - **Kometa Poster Overlays**: `kometa-studio.tsx` (Batch Apply Overlays, Overlay Sync, Single-Item Poster Apply)
    - **Agregarr Collections & Playlists**: `agregarr-studio.tsx` (Collection Sync, Sync Collection to Plex, Seasonal Sync, Smart Hub Deployments)
    - **Maintainerr Prune Engine**: `prune-studio.tsx` (Prune Sync, Execute Prune / Stage Leaving Soon, Sync Leaving Soon Hub)
    - **Media Tagging & Parental Guides**: `tagging-studio.tsx` (Tagging Sync, Apply Parental Tags, Clear Parental Tags, Apply Custom Tag Rules)
- **Modal Design & 3-Choice Decision Protocol**:
  - Whenever an action is triggered on an un-enabled library (`isSectionEnabled(serverId, sectionKey) === false`), execution halts and `CurationLibraryGuardModal` is displayed:
    - **Header & Scope Box**: Amber warning theme (`AlertTriangle`), server name (`HardDrive`), library name (`Folder`), section key, and prominent `⚪ Excluded from Schedule` badge.
    - **Alert Heading**: *"Hey, you don't have this library turned on or enabled!"*
    - **Option 1: Enable Library & Apply (Recommended)**: Permanently turns the library section ON in SQLite settings (`toggleCurationLibrarySectionAction`), updates the local enabled list, and immediately executes the requested action.
    - **Option 2: Force Update (One-Time Override)**: Executes the update once right now without altering the schedule settings, keeping the library safely excluded for future automated background jobs.
    - **Option 3: Cancel**: Aborts the operation immediately with zero changes made to Plex media.
- **Component**: `src/components/curation/curation-library-guard-modal.tsx`

---

### 20. Plex & Server Master AI Mission Control Modal (`AiServerAssistant`)
- **Viewport-Bounded Modal Layout (`h-[86vh] max-h-[92vh]`)**:
  - Modal container uses responsive sizing:
    ```tsx
    className="w-[98vw] sm:max-w-4xl max-h-[92vh] h-[86vh] p-0 bg-neutral-950/98 border border-neutral-800/90 shadow-2xl rounded-2xl flex flex-col overflow-hidden text-neutral-100"
    ```
  - Replaces rigid hardcoded pixel heights (`h-[780px]`) that overflowed laptop screens and caused double nested scrollbars.
  - Header, tab bar, and prompt input are fixed anchors, with the central content area constrained to `min-h-0 flex-1 overflow-y-auto scrollbar-thin` for fluid scrolling.
- **4-Tab Mission Control Navigation**:
  - `activeTab` switches seamlessly between:
    1. **`💬 Diagnostic Chat`**: Interactive conversation with the autonomous AI agent. Features collapsible live telemetry ribbon with 1-click `"Diagnose Stream"` trigger, audio track inspector cards with replacement actions, real-time media probe results, autonomous action report cards (`RADARR_SEARCH_GRAB`, `ESCALATE_ADMIN_TICKET`), multi-step animated thinking states, and categorized prompt suggestions.
    2. **`📡 Live Telemetry`**: Deep stream telemetry inspector showing real-time video/audio transcode decisions, hardware acceleration indicators (`NVENC / QSV` vs `CPU Software`), bitrate & resolution telemetry, transcode speed multipliers, transcode reason tags, detected playback issues with recommended client fixes, and chronic pattern insights.
    3. **`🩺 Server Disk & Probes`**: Server nodes matrix dynamically rendering every configured Plex media server node (e.g. `MainPlexServer`, `KidsPlexServer`, `MainPlexServerBackup`), displaying live reachability (`ONLINE` / `OPERATIONAL`), connection mode (`Local Direct` vs `Remote`), API latency, and disk streaming health.
    4. **`⚡ Quick Fixes`**: Actionable 1-click client playback resolutions (Roku "Playback Error" fix, 100% Direct Play mode, quiet center-channel audio boost, language track replacement, subtitle burn-in fix) with direct links to `PlexSetupGuides` and `FeatureGuideModal`.
- **Conversational Context & Pronoun Anaphora Resolution**:
  - Natural language pronoun resolution (`extractContextFromHistory`) seamlessly resolves anaphoric pronouns ("can you test it on the main server?", "does that play on kids?", "is it working?") to the canonical media title discussed in previous turns, preventing erroneous matches or searching Plex for filler words.
  - Conversational title corrections (e.g. "no the sandlot", "actually the sandlot") automatically inherit requested target servers and playback test intent from context.
  - Dedicated server infrastructure status handler (`isServerStatusQuery`) provides comprehensive cluster health reports ("what all servers are online?").
- **Structured Function / Tool Calling Subsystem & Admin Homelab Command Center (`ai-assistant-tools.ts`)**:
  - Implements native function declarations for Google Gemini (`v1beta` `function_declarations`) and OpenAI (`tools` + `tool_calls`) with multi-turn synthesis dispatching across 10 structured tools.
  - Standard user tools: `probe_playback_health`, `get_cluster_status`, `terminate_playback_stream` (scoped to user's streams), `inspect_media_container`, `search_and_replace_media`, `redownload_book`.
  - Admin-only homelab command center: `get_homelab_hardware_telemetry` (Glances host CPU/RAM %), `get_docker_fleet_status` (multi-engine container fleet inspection), `restart_docker_container` (safe socket/CLI/TCP container restarts), and `get_account_sharing_alerts` (multi-IP concurrent streaming audits).
  - Strict Permission Isolation: Non-admin users attempting to invoke admin tools are denied at both prompt filtering and execution dispatch levels with explicit security notices.
  - Offline Heuristic Engine Fallback: Guarantees 100% operational uptime by executing tools locally and rendering high-density markdown cards even when external LLM keys are absent or unreachable.
  - Dynamic Admin Quick Prompts: When `snapshot?.role === "ADMIN"`, the quick prompt toolbar automatically prepends `🐳 Docker Fleet`, `🖥️ Host Hardware`, and `🚨 Sharing Alerts`.
- **Integrated High-Tech Header & Identity**:
  - Features an animated glowing Bot avatar with status pulse, operational counter badge reflecting all online server nodes (`4`), and `Autonomous v3.1` live indicator badge.
  - Quick action buttons in the header provide instant access to setup guides (`PlexSetupGuides`), feature tours (`FeatureGuideModal`), and clearing session history.
- **Component**: `src/components/ai-server-assistant.tsx`

---

### 21. Guides & Platform Knowledge Base User Access Gating (`/guides` & `FeatureGuideModal`)
- **Granular Server-Side Permissions Engine (`getUserGuideAccessAction` & `calculateUserGuideAccess`)**:
  - Automatically computes exact accessible categories (`allowedCategories`) and feature topic IDs (`allowedGuideTopicIds`) based on user session role, membership tier, trial status, account type, and relational library access.
- **Strict Persona Access Rules**:
  - **Admin (`role: "ADMIN"`)**: 100% access to all 8 categories: Streaming Devices, AI Support & Probes, Movies & TV Requests, Ebooks & Kindle, Audiobooks & Chapters, Memberships & Referrals, Server Curation Suite (`curation-studio`), and Full System Manual (`manual`) with live markdown editing.
  - **Trial Members (`status: "TRIAL"` / `membershipTier: "TRIAL"`)**: Strictly barred from Ebooks, Audiobooks, Curation Studio, and Full System Manual. Header subtitle dynamically suppresses references to audiobooks and Send-to-Kindle.
  - **Regular Approved Members**: Curation Studio and Full System Manual are completely hidden. Ebooks & Kindle and Audiobooks & Chapters are evaluated dynamically against `checkLibraryAccess` across the SQLite `Library` table (checking `allowedUsers` and `restrictedUsers`).
  - **Managed Household Sub-Accounts (`accountType: "KID"` or `"LIVING_ROOM"`)**: Barred from Memberships & Referrals (`referral-rewards`), Curation Studio, and System Manual.
  - **Direct Query Parameter & Navigation Guards**: Accessing `/guides?tab=curation-studio` or `/guides?tab=manual` as a non-admin automatically sanitizes the route and falls back to `"devices"`, with defensive rendering cards blocking unauthorized content.
- **Dynamic Header Subtitle Adaptation**:
  - Automatically tailors the page description to reflect only enabled user features (e.g. omitting audiobooks and Send-to-Kindle for trial or video-only users).
- **Interactive Feature Guide Modals (`FeatureGuideModal`)**:
  - Quick Topic Switcher Bar dynamically filters its topic buttons according to `allowedGuideTopicIds`, preventing non-admin or unauthorized users from discovering or switching into administrative suite guides.
- **Components & Actions**: `src/app/guides/page.tsx`, `src/components/feature-guide-modal.tsx`, `src/app/actions.ts` (`getUserGuideAccessAction`, `calculateUserGuideAccess`).

---

### 22. Kids & Family Library Access and Administration Controls
- **User Account Settings (`/settings/profile`)**:
  - **Kids & Family Library Access Card**: Renders an opt-in toggle card allowing approved, non-trial members (or members with `FAMILY` / `VIP_ALL_ACCESS` tiers) to add the household Kids Library to their personal access list.
  - Toggling executes `updateUserKidsLibraryAccessAction(enable)` to atomically append or remove the user's username in SQLite across all libraries flagged as kids shelves (`isKidsLibrary(lib)`), automatically bootstrapping a default `"Kids' Bookshelf"` if none exists.
  - Features real-time state feedback with an emerald `ACTIVE FAMILY ACCESS` badge, managed library list chips, and an amber tier lock warning for trial users.
- **Library Management Tab (`/library` -> Manage Tab)**:
  - **Kids Shelf Visual Badges**: Automatically detects and highlights kids shelves using `isKidsLibrary(lib)` with an emerald `Baby` icon badge (`Kids Shelf`).
  - **Interactive User Badges**: Renders individual allowed usernames as removable pill badges (`bg-slate-800/80 text-slate-300`) with an inline `X` button calling `handleToggleUserAccess(lib.id, u.username)` for instant 1-click revocation.
  - **Manage Users Popover Dropdown**: Provides an admin dropdown menu on each library card that lists all system users with toggle checkmarks, allowing administrators to grant or revoke access for any user with 1 click without opening the edit dialog.
  - **Edit Library Form Allowed Users Quick Toggles**: Allows administrators to toggle between `* (All Users)` and individual specific usernames with case-insensitive checks and clean comma-separated formatting.

---

### 23. Curation Studio Responsive 4-Way Mode Switcher Tabs (`CurationNavHeader`)
- **Outer Grid Breakpoints**: `grid grid-cols-2 xl:grid-cols-4 gap-2`
  - Replaces rigid `md:flex` (which forced 4 buttons into 1 cramped row starting at 768px, truncating titles on tablets, laptops, and snapped half-screen windows).
  - **Large Screens (`xl:` $\ge 1280px$)**: Expands to 4 equal-width buttons in a single horizontal row across the top.
  - **Medium Screens / Tablets / Laptops / Split Windows (640px–1279px)**: Renders as a 2x2 grid (`grid-cols-2`), giving each button 300px–500px of width.
  - **Mobile Screens ($< 640px$)**: Renders as a 2x2 grid with an adaptive stacked internal button layout (`flex-col sm:flex-row items-center justify-center gap-1.5 sm:gap-2`).
- **Internal Button Layout Adaptation**:
  - **Top Row on Mobile / Left on Desktop**: Centered Lucide icon paired with concise studio title (`Kometa Overlays`, `Agregarr Hubs`, `Maintainerr Prune`, `Tagging Studio`).
  - **Bottom Row on Mobile / Right on Desktop**: Dedicated studio badge (`Badges`, `Collections`, `Storage`, `Parental`).
  - Eliminates duplicate icon/emoji pairings (`<Sparkles />` + `🎨`) to recover horizontal space.
  - Enforces `whitespace-nowrap font-bold text-xs` so titles never truncate or wrap awkwardly on mobile devices.
- **Component**: `src/components/curation/curation-nav-header.tsx`

---

### 24. Multi-Stage Subscription Renewal Reminders & Payment Engine Architecture
- **Payment Email Scraper Hardening (`src/lib/payment-email-scraper.ts`)**:
  - **Zero-Fee Resilience (`extractAmount`)**: Uses `matchAll` to bypass zero amounts (e.g. `Fee: $0.00 USD`) and accurately extract the actual positive payment amount (`Net: $180.00 USD`).
  - **Cash App Cashtag Isolation (`parseCashAppEmail`)**: Enforces alphabetic characters (`/[a-zA-Z]/`) in cashtag extraction, rejecting numeric amounts like `$180` from accidentally being recorded as the user's handle.
  - **Calendar Alignment & Q4 Monthly Math (`calculateAlignedExpiryDate`)**: Fixed Q4 monthly payment math so monthly payments made in October/November/December credit 1 month without leaping across calendar years. Preserves a 25-day minimum access guarantee for full monthly payments made mid-month. Returns explicit `cadence: "YEARLY" | "MONTHLY"`.
- **Multi-Stage Advance Renewal Warnings (`sendSubscriptionRenewalRemindersInternal`)**:
  - **Annual Plan Milestones ($180/yr)**: 30 days, 14 days, 7 days, 3 days, and 1 day before expiration. Includes net balance due (with earned referral credits deducted), alternative monthly breakdown ($15/mo), payment memo username, and P2P handle options.
  - **Monthly Plan Milestones ($15/mo)**: 3 days and 1 day before expiration with standard $15 rate and memo username.
  - **Cycle-Based Milestone Deduplication**: Persists `{ cycleTarget: "YYYY-MM-DD", milestones: ["30d", "14d"] }` in `User.renewalRemindersSent`. Idempotent across hourly background sweeps; automatically resets upon subscription renewal when `cycleTarget` changes.
- **UI Components & Admin Controls**:
  - **Email Management Hub (`/settings?tab=emails`)**: Notification toggle for `notifySubscriptionRenewal` in Dispatch Controls, alongside a manual "Run Renewal Sweep Now" diagnostic button with live user scan and reminder counts.
  - **Access Management (`/settings/access`)**: User status badges display `Monthly Plan (Expires ...)` or `Annual Plan (Expires ...)`, with a dedicated `Reminder Sent (MMM d)` badge. Access & Timer modal (`subModalUser`) features a 1-click Plan Cadence switcher (`updateUserSubscriptionCadenceAction`) and displays the last reminder dispatch timestamp.
  - **Profile Page (`/settings/profile`)**: Renders `"Active Monthly Subscription"` at `$15/month` for monthly members and `"Active Annual Subscription"` for yearly members.

---

### 25. Cloudflare Access & Edge Security Policy Paths
- **Single Source of Truth Module (`src/lib/edge-policy-paths.ts`)**:
  - Defines `CLOUDFLARE_BYPASS_PATHS` (public & authenticated member endpoints) and `CLOUDFLARE_ADMIN_PATHS` (administrative management and configuration endpoints).
  - Provides path matching utilities: `matchesCloudflareBypass(pathname)` and `matchesCloudflareAdmin(pathname)` supporting wildcard prefixes (`/*`).
- **Cloudflare Bypass Policy (`CLOUDFLARE_BYPASS_PATHS`)**:
  - Public onboarding, authentication & invitations: `/`, `/login`, `/join`, `/invite/*`, `/pending`.
  - Member portal & media interfaces: `/hub`, `/library*`, `/requests*`, `/guides*`, `/beta*`.
  - Authenticated member APIs: `/api/auth/*`, `/api/books/*`, `/api/cover*`, `/api/media/*`, `/api/libraries*`, `/api/requests*`, `/api/stats*`, `/api/downloads*`, `/api/speedtest*`.
  - Static assets & browser hooks: `/favicon.ico`, `/icon.png`, `/robots.txt`, `/sitemap.xml`, `/_next/*`.
- **Cloudflare Admin Policy (`CLOUDFLARE_ADMIN_PATHS`)**:
  - Admin interfaces: `/settings*`, `/admin*`, `/curation*`, `/radarr*`, `/sonarr*`.
  - Admin API endpoints: `/api/system*`, `/api/debug*`, `/api/curation*`, `/api/users*`.
- **Edge Proxy Role Enforcement (`src/proxy.ts`)**:
  - Synchronously guards administrative pages and APIs, requiring active `ADMIN` role authentication before proceeding to `/admin`, `/curation`, `/api/curation`, `/api/users`, `/api/debug`, and `/api/system`.
- **Settings Reference Component (`src/components/cloudflare-policy-card.tsx`)**:
  - Renders live path tables on `/settings` with 1-click clipboard copy for Cloudflare Zero Trust WAF rules and edge reverse proxies (Traefik, NGINX, Caddy).
- **Mandatory Route Change Rule**:
  - Whenever adding, removing, or renaming any page (`src/app/**/page.tsx`) or API route (`src/app/api/**/route.ts`), you MUST synchronously update `src/lib/edge-policy-paths.ts`, `src/proxy.ts`, `src/components/cloudflare-policy-card.tsx`, and `scripts/verify-all.ts`.

---

### 26. Kindle Delivery Failure Inbox Scanner & Rethought Book Rating Isolation
- **Amazon Delivery Failure Inbox Scanner (`src/lib/kindle-email-scanner.ts`)**:
  - Automatically resolves IMAP credentials from active `PaymentEmailSource` entries or primary SMTP credentials (`settings.smtpUser`, decrypted `settings.smtpPass`, and derived host e.g. `imap.gmail.com`).
  - Evaluates recent outgoing Kindle dispatches (`status: "DELIVERED"`) at 5-minute and 10-minute milestones post-delivery via the background scheduler loop (`src/lib/prisma.ts`).
  - Scans for Amazon Send-to-Kindle failure emails (`kindle-cs@amazon.com`, `do-not-reply@amazon.com`) checking for unapproved sender address rejections or format issues.
  - Dynamically transitions `KindleDeliveryLog.status` to `"FAILED"`, updates `errorMessage` with the exact Amazon rejection reason, records failure diagnostics, and emits system alerts.
  - **Manual UI Trigger**: Adds a **"Check Inbox for Bounces"** button to the Kindle Delivery History panel in `/library` with live toast feedback.
- **Rethought Book Rating Engine & Badge Isolation (`src/lib/books/book-rating.ts`)**:
  - **Suppressed Misleading "All Ages" Badges**: Removed the default "All Ages" badge from general fiction and adult literature. Visual shelf badges are strictly reserved for verified `Kids` (emerald), `YA (12+)` (sky), and `18+ Mature` (rose). General audience books display cleanly without misleading badges.
  - **Expanded Romance & Spicy Detection**: Added Tessa Dare and leading historical and contemporary romance authors (`julia quinn`, `lisa kleypas`, `sarah maclean`, `courtney milan`, etc.) and historical series to `KNOWN_SPICY_AUTHORS_REGEX` and `KNOWN_SPICY_SERIES_REGEX`.
  - **Romance Title Signatures (`ADULT_ROMANCE_TITLE_REGEX`)**: Evaluates classic adult romance tropes and title keywords (`surrender`, `scandal`, `scandalous`, `seduction`, `affair`, `duchess`, `duke`, `rake`, `scoundrel`, `wicked`) as `18+ Mature`.
  - **Strict Whitelist for Kids Mode**: Child accounts (`accountType === "KID"` or `section === "kids"`) operate on a strict whitelist requiring `ageRating === "Kids"` or `YA (12+)`. Unverified general fiction and uncaught adult books are strictly barred from entering a child's reading view.

---

### 27. Settings Dirty Checking & Unsaved Changes State Lifecycle
- **Never Depend on `useMemo` for Ref Snapshots (`initialDataRef`)**:
  - `useMemo` compares its dependency array by identity (`Object.is`). It DOES NOT and CANNOT track mutations to `ref.current`.
  - If a save handler updates `initialDataRef.current` without altering state references (or if the memo dependency array only contains state), `useMemo` will return the stale cached `true` value from the previous render, leaving "● Unsaved Changes" and the floating action bar permanently visible even after successful save operations.
  - **Rule**: Compute dirty checks directly as clean, lightweight boolean expressions during component render (e.g. `isPricingDirty = Boolean(initialRef.current && (...))`).
- **State & Snapshot Synchronization on Save**:
  - On successful save actions (`savePaymentAndTrialSettings`), synchronously update `initialPaymentSettingsRef.current` with the new snapshot AND call the corresponding `setState` hooks with cloned data to ensure all render cycles are completely in sync.
  - Return authoritative updated settings from Server Actions so the frontend saves match server normalizations and defaults.
- **Robust Array Equality**:
  - Compare string array settings (such as default library IDs) by sorting copies prior to index-by-index equality checks (`[...a].sort()`), preventing false-positive dirty states caused by array order permutations.
  - Always set state arrays explicitly even when loaded strings are empty (e.g., `""` &rarr; `[]`), preventing stale key retention.

---

### 28. Action Approval Gates & Governance (Strict Staging & Manual Review)
- **Email Dispatch Gating & Granular Policy (`requireApprovalForEmails` & `emailApprovalPolicy`)**:
  - 100% of outgoing emails across the entire codebase route through `sendOrQueueEmail` in `src/app/actions.ts`.
  - When `requireApprovalForEmails` is `true` (default), outgoing emails are staged in `AdminApproval` (`type: "EMAIL"`, `status: "PENDING"`) unless their specific `templateId` is configured with `emailApprovalPolicy[templateId] === false`.
  - Individual template toggling enables granular operational automation: unchecking "Require Approval" for `kindle_delivery`, `kindle_success`, or `kindle_failed` allows books to be sent instantly to Kindle readers via SMTP while keeping account and payment emails securely staged for manual review.
  - Quick action presets: `⚡ Auto-Send Kindle Only`, `Require All`, `Auto-Send All`.
  - Staged emails preserve recipient, subject, rendered HTML, templateId, and file attachments in `payload`.
  - Emails are dispatched via SMTP when approved in the queue (`approveAdminApprovalAction`) or when configured to auto-dispatch.
- **Dedicated Category-Based Outbound Sender Routing (`resolveSenderAddress`)**:
  - Dynamically routes outgoing email dispatches to category-matched sender mailboxes based on `templateId` when using a custom verified domain (e.g. `domshomelab.com`):
    - **Kindle Ebooks (`kindle@<domain>`)**: `"DomsHomeLab Kindle"` for `kindle_delivery`, `kindle_failed`, `kindle_success`.
    - **Billing & Payments (`payments@<domain>`)**: `"DomsHomeLab Billing"` for `payment_received`, `payment_underpayment`, `admin_payment_received`, `subscription_activated`, and renewal reminders.
    - **Accounts & Authentication (`accounts@<domain>`)**: `"DomsHomeLab Accounts"` for `user_approval`, `admin_new_user`, `password_reset`, `trial_welcome`, `trial_expiring_soon`, `trial_expired`, and `library_access_request`.
    - **Requests & Seerr (`requests@<domain>`)**: `"DomsHomeLab Requests"` for `media_ready`, `media_request_admin`, and all `seerr_request_*` notifications.
    - **Support Tickets (`support@<domain>`)**: `"DomsHomeLab Support"` for `ticket_update` and `ticket_error_alert`.
    - **Governance Approvals (`accounts@<domain>`)**: `"DomsHomeLab Governance"` for `admin_approval` queue alerts.
    - **General Announcements & Broadcasts (`notifications@<domain>`)**: `"DomsHomeLab"` for broadcasts and general alerts.
  - **Safe Webmail Fallback (`PUBLIC_WEBMAIL_DOMAINS`)**: When the configured SMTP sender is a public webmail domain (e.g. `@gmail.com`, `@yahoo.com`, `@outlook.com`), the exact configured sender address is strictly preserved to prevent SPF/DKIM/DMARC rejection by recipient mail providers.
  - **Email Management UI Integration**: Displays dedicated sender mailboxes (`From: <sender>`) on each template card and in the template editor header, with 1-click preview testing matching the exact routed sender.
- **Admin Real-Time Approval Notifications (`notifyAdminOnPendingApproval`)**:
  - Whenever an action or staged email enters the queue, Portalarr automatically alerts administrators via configured channels (`adminApprovalDiscordNotify` Discord embeds and `adminApprovalEmailNotify` SMTP emails).
  - Admin notification emails pass `bypassApproval: true` to prevent infinite recursion into the approval queue.
- **Live Plex Modification Gating (`requireApprovalForPlexChanges`)**:
  - All operations that grant, sync, modify, or revoke Plex server shares (`revokePlexAccessForUserInternal`, `updateUserPlexLibraries`, `setUserTrialOrSubscription`, `createOrUpdateSubAccountAction`, `registerUserWithInviteAction`, `updateUserSelectedPlexLibrariesAction`) respect `requireApprovalForPlexChanges`.
  - When active (`true`), modifications are strictly staged in `AdminApproval` (`PLEX_ACCESS_GRANT` or `PLEX_ACCESS_REVOKE`). PMS friends and library share updates are withheld until an administrator explicitly reviews and approves the staged change.
  - When turned OFF (`requireApprovalForPlexChanges === false`), operations execute directly on the target Plex Media Server instances.

---

### 29. Admin Impersonation & Dashboard Preview Switcher (`AdminUserSwitcher` & `ImpersonationBanner`)
- **Instantaneous Preloading (Zero Client Loading Spinner)**:
  - On the dashboard (`/`), `page.tsx` checks `isAdmin || isImpersonating` and fetches candidate users server-side in under 2ms (`prisma.user.findMany` selecting only `id`, `username`, `role`, `status`, `membershipTier`).
  - Passes preloaded users via `initialUsers` to `<AdminUserSwitcher />`, completely eliminating the multi-second client-side `useEffect` delay and "Loading user accounts..." spinner.
  - Standalone fallback uses `getImpersonationUserListAction()`, which is isolated from heavy relations and payment logs.
- **Adaptive Cookie Security Flag (`getAuthCookieOptions`)**:
  - Cookie setting dynamically checks request headers (`x-forwarded-proto`, `referer`, `host`) to ensure `secure: false` over unencrypted HTTP and local LAN IPs (e.g. `http://192.168.10.199:3000`).
  - This prevents modern browsers from silently dropping session cookies when accessed on home networks, eliminating "switching does not work" failures. Over HTTPS, `secure: true` is automatically preserved.
- **Persistent Preview Navigation & Direct Switching**:
  - `<AdminUserSwitcher />` remains visible on the dashboard even when impersonating a user (`isImpersonating === true`), showing active preview status with 1-click switching to any other account.
  - `<ImpersonationBanner />` includes a compact inline `<Select>` dropdown on every page, allowing admins to switch accounts directly from `/library`, `/discover`, `/requests`, etc., without returning to admin first.
  - Returning to admin cleanly clears `portalarr_impersonator_token` and reloads the current page (or `/` if on `/pending`) without redirecting to `/settings/access`.

### 30. Live System & Diagnostic Activity Stream (`SystemLogsViewer` & `SystemLogger`)
- **Full Ring Buffer Capacity (5,000 Entries)**:
  - System logs capture up to 5,000 in-memory entries with append-only JSONL disk persistence (`data/system_logs.jsonl`).
  - Both `/api/system/logs` and `getSystemLogsAction` default to returning 5,000 entries so no logs are truncated or omitted on initial load or manual refresh.
- **Dynamic Category Detection & Category Normalization (`normalizeCategory`)**:
  - Predefined categories include `ALL`, `PLEX` (📺), `TAUTULLI` (📊), `SEERR` (🍿), `SCANNER` (📚), `DOWNLOAD` (📥), `AI_AGENT` (🤖), `COVER` (🖼️), `AUTH` (🔐), `SECURITY` (🔒), `APPROVAL` (🛡️), `KINDLE` (📖), `EMAIL` (✉️), `APPS` (⚡), `DATABASE` (💾), `API` (🌐), `MONITORING` (📡), `CURATION` (🎨), and `SYSTEM` (⚙️).
  - Micro-categories and internal alias tags normalize cleanly: `BOOK_ENGINE` -> `SCANNER`, `AUTO_GRAB` -> `DOWNLOAD`, `TAGGING`/`AGREGARR`/`MAINTAINERR`/`KOMETA` -> `CURATION`, `SETTINGS` -> `SYSTEM`, and `PLEX_HUB` -> `PLEX`.
  - Dynamic category fallback (`activeCategories`) scans active logs and dynamically renders any unlisted category with its own pill, icon, badge, and live count, guaranteeing zero log omission.
- **Clean Boot & Migration Guard Rails**:
  - `ensureSchemaColumns()` in `src/lib/prisma.ts` inspects `sqlite_master` before executing `_prisma_migrations` recovery queries, eliminating repetitive SQLite Code 1 raw query errors on startup and build.
- **Multi-Field Filtering & Smart Timestamping**:
  - Search filter matches concurrently across `log.message`, `log.category`, `log.details`, and `log.level` (e.g. typing "ERROR" or "WARN").
  - Timestamps format dynamically as `HH:mm:ss` for events logged today and `MMM D HH:mm:ss` for historical entries, paired with full locale date tooltips on hover.

### 31. User Directory, Tiers, Cadence & Add-on Controls (Controlled State & Alert Suppression)
- **Radix UI `Select` Controlled State (`value` vs `defaultValue`)**:
  - In user directories and management lists where items re-render or update optimistically upon mutations, always bind `value={...}` instead of `defaultValue={...}` on `Select` components (e.g. `value={user.membershipTier || "STANDARD"}` and `value={user.role}`).
  - Using uncontrolled `defaultValue` causes the dropdown display to become desynchronized from the actual server state when the underlying user object changes.
- **100% Elimination of Tab-Blocking `alert()` Modals**:
  - Never call native browser `alert()` or `confirm()` in user management handlers (such as cadence updates, referral unlinking, access revocations, or add-on toggling).
  - Use lightweight feedback mechanisms (e.g., non-intrusive floating toasts, status badges, or modal action states) to maintain a modern, seamless application feel.
- **Strict Member Tier Concealment & Calculations**:
  - In member profile cards and subscription modals, calculate rates dynamically from `paymentSettings`:
    - Tier 1 (`STANDARD`): default $180/yr ($15/mo annual base) or $15/mo standalone.
    - Tier 2 (`TIER_2_VIP`): default $240/yr ($20/mo annual base) or $25/mo standalone (`paymentSettings.tier2YearlyPrice` & `paymentSettings.tier2MonthlyPrice`).
  - **CRITICAL:** Regular members must NEVER know whether they are Tier 1 or Tier 2. Tier 2 is for needy users who pay a higher rate for managed support, but to members they must strictly appear as `⭐ Full Member` with zero tier numbers or "Managed Support" labels. Only administrators in `/settings/access` may view or toggle Tier 1 vs Tier 2.
- **Interactive Active Add-ons Manager**:
  - Provide an inline "Active Add-ons & Profile Perks" manager in the user's Access & Timer dialog (`subModalUser`), allowing administrators to toggle available add-ons with immediate optimistic UI updates (`toggleUserAddonAdminAction`).
  - Active add-ons display on member cards with a yellow `Zap` icon badge, count, and multi-line hover tooltip detailing all active perks.

### 32. Support Ticket & AI Diagnostic Controls (Radix Confirmation Dialogs & Alert Suppression)
- **100% Elimination of Native `confirm()` and `alert()` in Ticket Management**:
  - In `/admin/tickets` and ticket moderation workflows, never invoke native window `confirm()` or `alert()`.
  - Ticket deletions are gated by a dedicated Radix UI `<Dialog>` (`deleteModalTicket`) providing explicit item context (ticket title, ID, user), a red confirmation button with loading spinner, and an inline dismissible error banner (`deleteError`) if the deletion fails.
- **AI Diagnostics & Support Auto-Escalation**:
  - Auto-generated diagnostic tickets created by the AI Assistant or client errors include comprehensive telemetry payloads (stream health, audio codecs, transcode metrics, user client info) and an `[AUTO-TICKET]` tag in the title.
  - In-app status badges distinguish ticket priorities (`HIGH`, `MEDIUM`, `LOW`) and state transitions (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`) with semantic color accents and real-time refresh.

### 33. Cloudflare Access & Edge Security Policy Paths (Strict 3-Tier Zero-Trust Matrix)
- **Single Source of Truth (`src/lib/edge-policy-paths.ts`)**:
  - All routes are centrally declared and categorized into `CLOUDFLARE_ADMIN_PATHS`, `CLOUDFLARE_SUPER_USER_PATHS`, and `CLOUDFLARE_BYPASS_PATHS`.
  - Rendered in `/settings` via `<CloudflarePolicyCard />` with 1-click clipboard actions and step-by-step Zero Trust setup instructions.
- **Strict Admin-Only Path Isolation (`CLOUDFLARE_ADMIN_PATHS`)**:
  - Covers all management and privileged surfaces: `/settings*`, `/admin*`, `/curation*`, `/api/system*`, `/api/debug*`, `/api/curation*`, `/api/users*`, and `/api/books/upload*`.
  - In `src/proxy.ts`, all admin paths reject non-admin users with 403 Forbidden for APIs, redirect non-admins on `/settings` to `/profile`, and redirect non-admins on other admin pages to `/`.
- **Media Apps for Super Users & Admins (`CLOUDFLARE_SUPER_USER_PATHS`)**:
  - Covers movie and TV show library management (`/radarr*`, `/sonarr*`).
  - Allowed for `ADMIN` and `SUPER_USER` roles in both `src/proxy.ts` and `src/app/arr-actions.ts`.
  - In Cloudflare Zero Trust, Rule 2 permits both Admin and Super User emails, or can be bypassed at the edge while strictly guarded by Portalarr session authentication.
- **Dual End-User Routing (`/profile*` & `/settings/profile*`)**:
  - End-users can manage profile settings, Kindle email, preferences, and subscription billing seamlessly at both `/profile` and `/settings/profile`.
  - In `src/proxy.ts`, `/settings/profile*` is explicitly exempted from the admin-only redirect to `/profile`, allowing direct bookmarking and navigation to `/settings/profile`.
  - In `src/lib/edge-policy-paths.ts`, `/settings/profile*` is included in `CLOUDFLARE_BYPASS_PATHS` and excluded from `matchesCloudflareAdmin()`, guaranteeing friends and family are never blocked by Cloudflare Zero Trust login walls when visiting `/settings/profile`.
  - All email notifications dispatch links with `{billingUrl}` = `/profile#billing`.
- **Strict Non-Bypassable Admin Guard (`matchesCloudflareBypass`)**:
  - `matchesCloudflareBypass()` explicitly verifies that if `matchesCloudflareAdmin(path)` is true and the path is not `/settings/profile`, the route is NEVER bypassed, guaranteeing zero leakage or path collisions.
- **Three-Rule Cloudflare Zero Trust Setup**:
  - **Rule 1 (Admin Only - High Priority)**: Action = `Allow`, Selector = `CLOUDFLARE_ADMIN_PATHS`, Include = `Emails: [your-admin-email@example.com]`. Blocks all outsiders with HTTP 403 at Cloudflare's edge before requests reach the server.
  - **Rule 2 (Super Users & Admin - Priority 2)**: Action = `Allow`, Selector = `CLOUDFLARE_SUPER_USER_PATHS` (`/radarr*`, `/sonarr*`), Include = `Emails: [your-email, superuser-emails]`.
  - **Rule 3 (Public / End-User Bypass - Lower Priority)**: Action = `Bypass`, Selector = `CLOUDFLARE_BYPASS_PATHS`, Include = `Everyone`. Allows friends and family to stream, request, and manage their account profile without Cloudflare login walls.

### 34. Real-time Telemetry & API Route Dynamic Prerender Guards
- **Strict Dynamic Route Export (`dynamic = 'force-dynamic'`, `revalidate = 0`)**:
  - Telemetry and live status endpoints (`/api/stats`, `/api/downloads`, `/api/system/logs`) must NEVER be statically prerendered at build time.
  - Next.js Turbopack App Router prerenders route handlers lacking `export const dynamic = 'force-dynamic'` as static content (`○ /api/stats 5s 1y`). During Docker image builds (e.g. GitHub Actions), local homelab addresses (`192.168.1.x`) are unreachable, resulting in static build artifacts with false-positive offline states.
  - Adding `export const dynamic = "force-dynamic";` and `export const revalidate = 0;` guarantees on-demand evaluation upon each live incoming request.
- **Cache-Control & No-Store Headers**:
  - Responses must explicitly specify `Cache-Control: no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0` to prevent edge proxies (Cloudflare) and intermediate CDNs from serving stale status snapshots.
  - Client components (`SimpleSystemHealth`, `SystemStatus`, etc.) must fetch with `{ cache: "no-store" }`.

### 35. Subscription Renewal Reminders & Access Directory Telemetry (`/settings/access`)
- **Deterministic Member Directory Next Reminder Badges**:
  - Every member card in `/settings/access` computes live reminder information (`getNextRenewalReminderInfo`) and displays responsive status badges:
    - 🟢 `Paid / Up to Date` / `Paid`: Subscription is covered through the future cycle or a confirmed payment was recorded.
    - 🟡 `Due Today (<m>d notice)`: The current milestone bracket has arrived and is due for dispatch today.
    - 🔵 `<Date> (<m>d notice)`: Next advance notice is scheduled and waiting for the target threshold.
    - ⚪ `All Reminders Sent`: All configured milestones for this cycle have been dispatched.
    - 🔴 `Expired`: Account has lapsed.
    - 🔘 `Admin` / `Trial` / `Pending`: Account not subject to standard renewal reminders.
- **Detailed Renewal Notice Metadata Row**:
  - Below member account type and cadence pills, an informative "Renewal Notice" row renders with a `BellRing` icon, displaying plan cadence, days remaining, exact next email reminder date, and dispatched milestone history badges (`60d`, `30d`, `14d`, `3d`, `1d`).
- **Dual-Zone Schedule Configuration UI (Payment & Onboarding Tab)**:
  - Two dedicated configuration areas for Annual and Monthly memberships:
    - **Annual Members Schedule (`yearlyRenewalReminderDays`, default: `60,30,14,3,1`)**: Multi-tier advance notice (e.g. 2 months, 1 month, 14 days, 3 days, 1 day before expiration).
    - **Monthly Members Schedule (`monthlyRenewalReminderDays`, default: `7,3,1`)**: Multi-tier advance notice (e.g. 7 days, 3 days, 1 day before expiration).
  - Features quick-toggle preset milestone pills, custom comma-separated inputs with real-time numeric normalization, and sequential timeline flow arrows.
- **Strict Already-Paid Payment Check Callout**:
  - Highlights the automatic payment verification engine (`isUserSubscriptionPaidForCycle`), reassuring administrators that members who already sent their payments are strictly excluded from reminder emails.

### 36. Platform Administrator Isolation from Subscriptions, Cadences & Member Tiers (`/settings/access` & `/settings/profile`)
- **Strict Exemption from Subscriptions & Cadences**:
  - Administrators (`role === "ADMIN"`) possess permanent, lifetime platform access and must NEVER have an annual plan, monthly plan, subscription expiration (`subscriptionEndsAt`), free trial (`trialEndsAt`), or member tier (`⭐ Tier 1`, `🛡️ Tier 2`) assigned or rendered.
- **Access Control Directory Styling (`/settings/access`)**:
  - **Badges**: Admin cards strictly display `🛡️ Platform Administrator` and `Permanent Access`. Annual/Monthly plan badges, next renewal reminder pills, and trial notice badges are completely hidden for admins.
  - **Payment Row**: Displays `Payment: Exempt (Platform Administrator)` instead of member transaction history.
  - **Action Buttons**: Suppresses subscription-specific action buttons (`Access & Timer`, `Credit Referral`, `Renewal Notice`) on admin cards, leaving only `Manage Libraries` and `View As` (impersonate).
  - **Bulk Exclusion**: Checkboxes for bulk subscription/trial application are hidden on admin cards, and master bulk selection (`handleSelectAllFiltered`) as well as the backend (`bulkSetUsersTrialOrSubscriptionAction`) strictly exclude admin accounts from bulk updates.
  - **Member Tier Selector**: Replaces the interactive `<Select>` tier dropdown with a static, non-selectable badge (`🛡️ Permanent Admin`) to prevent accidental tier reassignment.
- **User Profile Status (`/settings/profile`)**:
  - Under Account Access Status, admins are prominently identified with `<Badge variant="outline" className="bg-indigo-500/20 text-indigo-300 border-indigo-500/40"><ShieldCheck /> Platform Administrator (Permanent Access)</Badge>`.
- **Backend Governance & Auto-Healing**:
  - Backend mutations (`setUserTrialOrSubscription`, `updateUserMembershipTierAction`, `updateUserSubscriptionCadenceAction`, `sendSubscriptionRenewalReminderAction`) reject operations against admins with descriptive error feedback.
### 37. Payment Threshold Awareness, Installment Credits & Account Balance Cockpit (`/profile`, `/settings/profile`, `/settings/access`)
- **Member Account Credit & Partial Balance Card (`/profile` & `/settings/profile`)**:
  - Whenever a member has an unapplied credit balance (`user.accountCredit > 0`), a prominent amber glassmorphic card renders at the top of the Subscription & Prorated Billing card (`bg-amber-500/10 border-amber-500/30`):
    - Displays total available balance (`$X.XX Balance`), latest payment amount, and payment date.
    - Features a 2-card comparison breakdown:
      - **Monthly Plan**: Displays exact remaining shortfall needed to activate/extend 1 month access (`${effectiveMonthlyPrice - user.accountCredit}` remaining).
      - **Annual Discounted Plan**: Displays exact remaining shortfall needed for 1 full year of access (`${effectiveYearlyPrice - user.accountCredit}` remaining), highlighting the discounted $15/mo equivalent rate.
  - When account credit is zero and a payment was applied, renders a subtle recent payment confirmation badge (`Last Payment: $X.XX on Date via Provider (Applied)`).
- **Admin Access Control Transparency (`/settings/access`)**:
  - User rows in the directory display an amber badge `<Badge variant="outline" className="bg-amber-500/20 text-amber-300 border-amber-500/40"><DollarSign /> Credit: $X.XX</Badge>` whenever `accountCredit > 0`.
  - Also displays latest payment badge `<Badge variant="outline" className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30"><CreditCard /> Last: $X.XX</Badge>`.
  - Inside the user management modal (`subModalUser`), displays a dedicated Account Credit Balance row with full payment details.

### 38. Strict Member Tier Concealment & Bidirectional Discord Role Sync Architecture (`/settings/profile`, `/settings/access`, `discord-role-sync.ts`)
- **Strict Member Tier Concealment**:
  - Non-admin members must NEVER know or see whether they are Tier 1 or Tier 2. Tier 2 is for needy users who pay a higher rate for managed support, but to regular members they must strictly appear as "⭐ Full Member" (in the web portal) and "⭐ Member" (in Discord) with zero tier numbers or "Managed Support" labels.
  - Only administrators in `/settings/access` may view or manage Tier 1 vs Tier 2 membership levels.
- **Strict Limited Trial Discord Access & Channel Isolation**:
  - Members with `⏱️ Trial Pass` (and unlinked users with only `@everyone`) are denied `VIEW_CHANNEL` across all member categories (Guides & Self-Service, Community Chat, Requests & Media, Help & Tickets) and all non-welcome channels in Category 1.
  - Trial members strictly view `#welcome-and-rules` until they link their Portalarr member account on the web portal.
  - The `#welcome-and-rules` embed features a prominent `⏱️ Trial Pass & Account Linking (Required)` guideline explaining the restriction and directing users to **Account Settings → Profile** to link their Discord handle and automatically elevate to `⭐ Member`.
- **Zero Pricing / Tiers / Subscriptions on Discord Policy**:
  - Absolutely NO mentions of pricing ($17.50, $180), payment methods (Cash App, Venmo, PayPal, Zelle), tiers (Tier 1, Tier 2), or subscription billing anywhere on Discord channel topics or embeds.
  - Pinned embeds emphasize homelab infrastructure, 4K Direct Play setup, reading integrations (Paperwhite & Audiobooks), automated request fulfillment, and the hardware expansion roadmap.
- **Discord Community & Role Sync Card with Direct Invite Link (`/settings/profile`)**:
  - Positioned prominently below Notification & Email Preferences.
  - **Step 1: Join the Discord Server**: Features a prominent glassmorphic CTA button with `Gamepad2` and `ExternalLink` icons directing members to the permanent server invite URL (`getDiscordServerInviteUrlAction` / `paymentConfig?.discordInviteUrl`).
  - **Step 2: Link Your Discord Handle**: Allows members to self-service link their Discord account by username or numeric Snowflake ID (`linkMyDiscordAccountAction`) to unlock `⭐ Member` access immediately.
  - When linked, displays avatar, linked username, linked snowflake ID, auto-sync status, a direct **Open Discord** button, 1-click **Sync Role** (`syncMyDiscordRoleAction`), and **Unlink** (`unlinkMyDiscordAccountAction`).
- **Admin User Management Direct Discord Linking (`/settings/access`)**:
  - Inside the User Management modal (`subModalUser`), includes a dedicated **Discord Account Binding** card:
    - If unlinked: Admins can directly enter any Discord handle or Snowflake ID and link the member with 1 click (`adminLinkUserByHandleAction`).
    - If linked: Displays linked avatar, handle, Snowflake ID, 1-click **Sync Role**, and **Unlink** (`unlinkUserFromDiscordAction`).
  - Single-pane management modal (`DiscordMemberManagerModal`) with multi-axis filtering (`All`, `Unlinked`, `Linked`, `Suggested`).
  - Smart heuristic auto-matching engine (`findBestMatch`) pairing exact usernames (100%), email prefixes (95%), server nicknames (90%), full names (85%), display names (80%), and substrings (70%).
  - 1-click Auto-Match, Bulk Push to Discord (`syncAllUsersRolesToDiscordAction`), Bulk Pull to Portalarr (`syncAllDiscordRolesToPortalarrAction`), and individual user dropdown linking.

- **Request Manager Bulk Actions & Multi-Select Architecture (`request-manager.tsx`)**:
  - **Multi-Select Checkboxes**: Every request card features an isolated `Checkbox` component with `e.stopPropagation()` preventing inadvertent card expansion or dialog opening.
  - **Selected Visual State**: Selected cards display high-contrast accent outlines (`border-primary ring-1 ring-primary/40 bg-[#161626]`).
  - **Master Toolbar Controls**: Features a dynamic `Select All ({filteredRequests.length}) / Deselect All` toggle alongside a dedicated manual `Refresh` button that busts in-memory cache and loads a fresh DB snapshot.
  - **Sticky Bulk Actions Bar**: Renders a floating/docked toolbar (`sticky top-3 z-30`) with backdrop blur (`backdrop-blur-md bg-card/95 border border-border/70 shadow-2xl`):
    - Badge: `{selectedIds.size} Selected` indicator.
    - Clear: Quick "Clear" link.
    - Mass Approve: Vibrant emerald action (`CheckCheck` icon) with optimistic state updating.
    - Mass Reject: Rose outline action (`XCircle` icon) with confirmation prompt.
    - Mass Delete: Rose filled action (`Trash2` icon) executing two-way cascade permanent deletion.
  - **0ms Optimistic UI Transitions**: Mutated or deleted cards immediately disappear from the view with 0ms latency, backed by floating glassmorphic toasts for feedback.

- **Support Tickets Unified Portal & Edge Policy Bypass (`/tickets`)**:
  - **Public User Route & Cloudflare Admin Policy Bypass**: Aliased and served from `/tickets` with entry in `CLOUDFLARE_BYPASS_PATHS` (`src/lib/edge-policy-paths.ts`). This allows all standard members and trial users to access support without encountering Cloudflare Access or Admin path policies.
  - **Automatic Route Normalization**: Visiting `/admin/tickets` redirects non-admins transparently to `/tickets` via `src/proxy.ts`, while administrators retain full mission-control features.
  - **Role-Scoped Access Control**: Backend action `getTicketsDashboardAction()` scopes ticket queries by role. Standard users see strictly their own submitted tickets, open new tickets with priority tiers (`LOW`, `NORMAL`, `HIGH`, `URGENT`), and view admin comments/resolution notes. Administrators see tickets from all users, filter by status (`ALL`, `OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`), update ticket status, link to relevant user profiles or Arr apps, and delete tickets.
  - **Sidebar & Navigation Integration**: Accessible via "Support Tickets" (`LifeBuoy` icon) in both desktop and mobile sidebars for all authenticated users.

- **Stream Intelligence & Multi-Server Telemetry Hub (`/admin/tautulli` and `/admin/streams`)**:
  - **Unified Mission Control**: Single-pane stream intelligence hub aggregating live sessions, watch history, user leaderboards, and device telemetry across all monitored Plex Media Servers (`MainPlexServer`, `KidsPlexServer`, `MainPlexServerBackup`, etc.) and hardware hosts.
  - **Admin-Only Guarded Route**: Strictly placed under `/admin/tautulli` and `/admin/streams` (aliased in App Router), guarded by `payload.role === "ADMIN"` in `src/proxy.ts` and registered in `CLOUDFLARE_ADMIN_PATHS`. Non-admins visiting legacy `/tautulli` or `/streams` are bounced to `/`, while admins are automatically redirected to `/admin/tautulli`.
  - **Built-in Telemetry Takeover Mode (`nativeStreamMonitoringEnabled`)**: When enabled (default), DomsHomeLab polls all Plex servers directly and halts live queries to standalone external Tautulli containers, eliminating duplicate stream tracking and redundant polling load while preserving external instances as backfill sources.
  - **Tautulli Complete Historical Backfill Runner (`backfillTautulliHistoryAction`, `startTautulliBackfillAction`, `getTautulliBackfillStatusAction`, `stopTautulliBackfillAction`)**: 1-click historical watch log importer from external Tautulli instances into the SQLite `WatchHistory` table with 2-hour window deduplication, configurable batch limits (100–25,000 records), and 100% **Unlimited Mode** paginating all historical records across time without limits. Features asynchronous background execution, 500x optimized batch queries, parameter-safe insertion chunks, interactive cancellation, and a live progress cockpit displaying animated progress bars, live inspected vs total counts, imported vs skipped duplicates, and current page metrics.
  - **User Telemetry & Connection Intelligence Modal (`getUserDetailedTelemetryAction`)**:
    - Clicking on any member in the User Telemetry list, active sessions, or watch history logs opens a dedicated, high-density inspection dialog (`max-w-4xl`).
    - Features 3 organized sub-tabs:
      - **Watch History**: Chronological playback feed with search filter, media type badges (`Movie` / `Episode`), completion percentages, and universal poster thumbnails.
      - **All Devices**: Hardware & player directory listing client apps (e.g. Apple TV, Plex for iOS, Plex Web), device models, Direct Play vs Transcode rates, total plays, and first/last active timestamps.
      - **All IP Addresses**: Network connection directory identifying private LAN vs public WAN IP addresses, location tags, session counts, detected password sharing alerts, and associated device fingerprints.
  - **Device Quality Doctor (`diagnoseStreamSettings`)**: Proactive client-side settings evaluator detecting downscaling and quality bottlenecks:
    - *Roku Auto-Adjust 720p 4Mbps Cap*: Detects default "Auto Adjust Quality" setting forcing server transcoding.
    - *Default Remote Quality Cap (2-4 Mbps)*: Detects Apple TV, Fire TV, Android TV, and Smart TVs running factory default 720p caps.
    - *Web Browser HEVC/4K Codec Incompatibility*: Prompts users to download the native Plex Desktop App for direct playback.
    - *Subtitle Burn-in & Audio Conversion Suppression*: Detects image-based subtitle burning (PGS/VOBSUB) requiring server transcoding. For audio-only conversions (e.g. TrueHD or DTS to stereo/EAC3 with Direct Play video), suppresses doctor fix warnings (`hasIssue: false`, zero troubleshooting steps) since lightweight audio downmixing consumes negligible server resources (~0% CPU, 0% GPU) and is standard for TV/stereo speakers.
    - *Actionable Guidance*: Provides interactive step-by-step fix guides and 1-click copyable user notices ready to send via Discord or email.
  - **Sidebar Navigation**: Positioned under "Administration" (`Activity` icon, cyan/emerald accents) visible exclusively to administrators.

- **User Scripts & Automation Subsystem (`/admin/scripts` & `src/lib/scripts`)**:
  - **Single-Pane Shell Automation Mission Control**: Unraid-style user scripts dashboard for homelab maintenance, automated database vacuuming, Docker container audits, and database-driven Plex cluster health checks.
  - **Default Built-in Scripts**:
    - `check_all_plex_servers.sh`: Resilient database-driven health check and auto-restart probe for `MainPlexBackup` (port 24958) and `KidsPlexServer` (port 32400) featuring quiet hours window checks (3:00 - 6:00), SQLite binary fallback, Docker container status audits, and retry curl probes.
    - `optimize_plex_databases.sh`: Plex SQLite database optimization executing `PRAGMA optimize` and integrity checks across Plex libraries.
    - `backup_portalarr_db.sh`: Atomic SQLite database snapshot creation to `data/backups/` with timestamping and integrity verification.
    - `restart_unresponsive_containers.sh`: Automated Docker health probe identifying dead or crash-looping containers with fast recovery.
  - **Live Interactive Terminal Modal (`ScriptTerminalModal`)**:
    - Displays prominent unraid-style abort warning: `"Note that closing this window will abort the execution of this script"`.
    - Real-time line-by-line streaming via HTTP `ReadableStream` (`/api/admin/scripts/run`).
    - Smart log syntax colorizer: `[OK]` (bright emerald), `[FAIL]`/`[ERROR]` (bright rose), `[WARN]` (amber), timestamps (sky blue), headers `--- Checking ... ---` (indigo).
    - Abort lifecycle: Closing the modal window or clicking "Abort Script" terminates the running child process immediately via `AbortController` and signals.
    - Terminal tools: Auto-scroll toggle, 1-click clipboard copy, and `.log` file download.
  - **Script Editor Modal (`ScriptEditorModal`)**:
    - Manage script name, filename, description, category (`Plex & Media`, `Database`, `Docker`, `System & Backup`, `Custom`), interpreter (`bash`, `sh`, `python3`, `node`), schedule cadence, and timeout.
    - Monospace code editor with quick-insert templates for Bash, Python, and Node.js.
  - **Execution History Modal (`ScriptHistoryModal`)**:
    - Chronological log of past runs with duration, exit codes (`Exit 0`, `Failed`, `Aborted`), execution mode (interactive vs background), and full log viewer.
  - **Admin Route & Security**: Guarded under `/admin/scripts` and `/api/admin*` via `CLOUDFLARE_ADMIN_PATHS` and `src/proxy.ts`. Navigation link integrated in desktop and mobile sidebars with `Terminal` icon.

---

### 23. System & Docker Fleet Monitoring Cockpit (`/admin/monitoring` & `admin-system-health-grid.tsx`)
- **Single-Pane Homelab Cockpit**: Unified administration mission control providing full-fleet container management, real-time service reachability, rolling uptime telemetry (24h/7d/30d), and automated outage alerts.
- **Tri-Tab Layout & Semantic Accents**:
  - **Tab 1: Systems & Services (`systems`)** (`text-sky-400`, `data-[state=active]:text-sky-400 data-[state=active]:bg-sky-500/15 data-[state=active]:border-sky-500/40`):
    - Comprehensive reachability grid covering Plex Media Servers, Host Hardware (Glances), Stream Monitors (Tautulli), Servarr & Request Apps, and Download Clients.
    - Status badges (`ONLINE`, `OFFLINE`, `PAUSED`) with live ping round-trip latency (`latencyMs`).
    - Rolling Uptime Telemetry Scorecards: precise 24-hour, 7-day, and 30-day uptime percentages with current streak badges ("Up for 14d 6h" or "Down for 12m").
    - Mini Sparkline Ping History: last 10 probe indicators (emerald for responsive, crimson for failed).
  - **Tab 2: Docker Container Fleet (`containers`)** (`text-emerald-400`, `data-[state=active]:text-emerald-400 data-[state=active]:bg-emerald-500/15 data-[state=active]:border-emerald-500/40`):
    - Multi-engine Docker connectivity: direct Unix domain socket (`/var/run/docker.sock`), Windows named pipe (`//./pipe/docker_engine`), Docker CLI (`docker ps`), remote Glances container API (`/api/3/containers`), and remote Docker daemon TCP probes on port 2375.
    - **Container Application Branding**: Dynamic Lucide icons and accent tints mapped to container names and images (`Film` for Plex/Radarr, `Tv` for Sonarr, `ArrowDownCircle` for SABnzbd/qBittorrent, `FileText` for Bazarr, `Image` for Immich, `Zap` for TeslaMate, `BarChart2` for Grafana, `Cpu` for Glances, `HardDrive` for DiskSpeed).
    - **Multi-Core Linux CPU Hot Load Engine**: Automatically detects multi-core cumulative CPU reporting ($\ge 100\%$, e.g. `185.1%`), rendering animated flame icons (`Flame`), live core estimations (`~1.9 cores`), and vibrant heat gradients (`from-amber-500 via-orange-500 to-rose-500`) alongside color-coded RAM utilization.
    - **Instant Fleet Sorting**: 1-click sorting pills: `A-Z` (Default), `🔥 CPU` (Highest CPU load first), and `💾 RAM` (Highest memory consumption first).
    - **Cleaned Telemetry & Host Identification**: Replaces raw monitoring agent tags (`Up (Glances)`) with clean status (`Running`, `Stopped`) and displays physical host pills (`<Server /> Main Unraid`).
    - **Container Image & Field Normalization Resilience**: Guarantees zero `e.image.replace is not a function` exceptions. Container attributes returned from multi-host agents (Glances python lists, Docker API arrays, or missing properties) are strictly normalized via `normalizeContainerImage` and defensively cast to strings before string operations (`.replace`, `.toLowerCase`) and UI rendering.
    - 1-Click Container Actions: instant **Restart Container** (`restartDockerContainerAction`), **Start Container**, and **Stop Container** with multi-tier execution across Docker socket, CLI, and remote Docker TCP API with glassmorphic toast notifications.
  - **Tab 3: Outages & Alerts (`incidents`)** (`text-amber-400`, `data-[state=active]:text-amber-400 data-[state=active]:bg-amber-500/15 data-[state=active]:border-amber-500/40`):
    - Overall Fleet Uptime Scorecards (24h Uptime %, 7d Uptime %, active incidents count).
    - Automated Outage Notification Engine: dispatches rich Discord embeds (crimson on failure, emerald on recovery) to `#system-status` channel or custom Discord Webhook URLs.
    - Chronological incident log tracking start time, failure details, total downtime duration, and 1-click incident clearance.
- **Navigation Integration**: Desktop and mobile sidebars under Administration via `Layers` icon, with direct jump button ("Docker Fleet & Uptime") embedded in `AdminSystemHealthGrid` on the home dashboard. Ultra-wide layout container (`max-w-7xl 2xl:max-w-[1600px] 3xl:max-w-[2200px]`) ensures perfect fit across all monitor sizes.

### 14. Strict React Hook Ordering & Early Return Safety (Zero Error #310 Guard)
- **The Golden Rule**: React hooks (`useState`, `useEffect`, `useMemo`, `useCallback`, `useRef`, `useTransition`, `useId`) must **NEVER** be called conditionally or placed below an early return statement (e.g. `if (loading && !data) return <Skeleton />`).
- **Minified React Error #310**: Calling hooks after a conditional early return causes React Error #310 (*"Rendered more hooks than during the previous render"*). On the initial render, the component exits early before reaching subsequent hooks. Once data resolves and triggers a re-render, the early return is skipped and React encounters more hooks than in the prior render, crashing the application.
- **Enforcement Pattern**:
  - Always declare all state, effects, and memoized values (`useMemo`, `useCallback`) unconditionally at the very top of the component.
  - Safe fallback defaults (`data?.items || []`) must be supplied so calculations execute cleanly even when `data` is initially `null` or `undefined`.
  - Place early loading or error returns (`if (loading && !data) return ...`) strictly **after** all hook declarations, immediately before the primary JSX return.

### 15. Server Management vs Cloud Discovery Inbox Pattern & State Synchronization
- **Separation of Master Management vs Discovery Inbox**:
  - The primary server list (**Configured Servers**) serves as the single source of truth for active management controls: Default selection, live connection testing, deletion actions, and master Monitored / Paused switches.
  - The cloud auto-discovery section (**Account Discovery Inbox**) strictly serves as an onboarding queue for new, unadded servers found on the linked cloud account.
- **Deduplication & Inbox Partitioning**:
  - Cloud-discovered servers must be partitioned into `unconfiguredDiscovered` (new discoveries) and `configuredDiscovered` (already added).
  - When all account servers are already added, collapse and summarize them into a clean confirmation badge (`✓ All Plex account servers are configured & active above.`) with an optional read-only "View Details" disclosure, completely omitting duplicate interactive switches.
  - Interactive onboarding buttons (`+ Add & Monitor`, `+ Add (Paused)`) must strictly be reserved for new, unadded discoveries.
- **Bidirectional State Synchronization**:
  - Any server-level status toggles must update both `configuredServers` and `discoveredServers` state arrays simultaneously, preventing desynchronized UI switches when viewing secondary details.

### 16. Stream Telemetry, React Reconciliation Key Stability & Ghost Stream Immunity
- **Plex Session Key Collision Vulnerability**:
  - Plex Media Server assigns integer session keys starting at `"1"` or `"2"` independently on each server instance.
  - In multi-server environments (e.g. `MainPlexServer` and `KidsPlexServer`), two concurrent active streams frequently share identical `sessionKey: "1"`.
  - Binding `<Card key={session.sessionKey}>` causes catastrophic React virtual DOM reconciliation key collisions. When sort orders change, React cannot differentiate colliding elements, reuses/clones stale DOM nodes, and renders phantom or duplicate "ghost streams".
- **Globally Unique React Stream Key Contract**:
  - All streaming cards must bind a compound, globally unique key incorporating server identity, session key, user, and media:
    ```tsx
    key={session.uniqueStreamKey || `${session.serverName}_${session.sessionKey}_${session.user}_${idx}`}
    ```
  - Backend actions (`getAdminDetailedStreamsAction`, `getUserPlexHubData`) must construct `uniqueStreamKey`:
    ```ts
    const uniqueStreamKey = `plex_${srv.serverId || srv.serverName}_${rawSessionKey}_${userTitle}_${s.ratingKey || fullTitle}`.replace(/[^a-zA-Z0-9_-]/g, "_");
    ```
- **Defensive Stream Array Sanitization**:
  - When clients disconnect or when PMS reports empty XML containers, Plex can return empty session objects `{}` or lingering `state: "stopped"` items.
  - Memoized stream sorting (`useMemo`) must defensively sanitize the stream array prior to sorting:
    ```ts
    const list = filteredSessions.filter((s: any) => 
        s && (s.title || s.grandparentTitle || s.fullTitle) && s.state !== "stopped"
    );
    ```
- **Deterministic Multi-Tier Tiebreaker Chain**:
  - Stream sorting must always culminate in a stable 4-tier tiebreaker (`user` ➔ `serverName` ➔ `title` ➔ `uniqueStreamKey`) so stream cards maintain 100% position stability across background polling intervals and sorting changes without visual jitter.

---

### 38. AI Server Assistant Mission Control & Universal Floating Launcher (`AiServerAssistant` & `FloatingAiLauncher`)
- **Prominent User Mission Control Placement**:
  - Positioned prominently on the main dashboard (position #2 on user/trial/super-user views, and directly accessible in Admin Mission Control) for all accounts (Admins, Full Accounts, Super Users, and Trial Users).
  - Styled with glowing purple/cyan linear gradient borders (`from-purple-500/20 via-primary/10 to-transparent`), a pulse status badge (`24/7 AI Diagnostic Engine Active`), and instant 1-click quick-chips (`⚡ Buffering`, `🔊 Quiet Dialogue`, `💬 Subtitles`, `📺 Unlock 4K/1080p`, `🎬 Missing Media`, `🟢 Server Health`, and `📚 Book Recommendations`).
  - Automatically loads the user's active streaming session telemetry into the diagnostic prompt for zero-click context awareness.
- **Personalized Book & Media Recommendations Engine (`ai-book-recommendations.ts` & `recommend_books_and_media`)**:
  - Aggregates user taste from previous `MediaRequest` and `BookRequest` records, Kindle deliveries (`KindleDeliveryLog`), and content preferences (`UserContentPreference`).
  - Detects favorite authors, universe affinities across 8 major genres, and cross-references existing disk catalog (`Book`) vs unacquired comparable works.
  - Generates actionable recommendation cards distinguishing between server-available books (`inLibrary: true`, linking directly to `/library` for Read Now or 1-Click Send-to-Kindle) and unacquired recommendations (`inLibrary: false`, linking to `/requests` for 1-Click Auto-Grab).
  - Supported across both LLM tool calling (Gemini `recommend_books_and_media`, OpenAI tools) and the zero-dependency heuristic engine fallback (`resolvePlexMasterHeuristic`).
- **Universal Floating Launcher & Event Bus**:
  - Rendered globally via `<FloatingAiLauncher />` in `LayoutWrapper` at `fixed bottom-4 right-4 z-40` for all authenticated members.
  - Supports programmatic triggers via `openAiAssistant(initialQuery?: string)` custom DOM events (`window.dispatchEvent(new CustomEvent("open-ai-assistant", ...))`) and query params (`?openAssistant=true`).
- **Support Ticket Triage Redirection & Diagnostic Hand-off**:
  - Mounts a prominent callout banner at the top of `/tickets` (*"Fix Playback or Media Issues in 30 Seconds"*) prompting members to test with the AI Assistant before creating manual support tickets.
  - Clicking *"Open Support Ticket With This Diagnosis"* in any chat bubble closes the assistant, navigates to `/tickets?prefill=...`, automatically opens the ticket submission dialog, and pre-populates the complete AI diagnosis into the issue description without clipboard copy.

---

### 39. Dual-Tier Prewarming Engine & High-Speed SWR RAM Caching (`src/lib/prewarm.ts`)
- **Dual-Tier Prewarming Architecture**:
  - **Global System Prewarm (`prewarmGlobalSystem`)**: Prewarms Discovery TMDb carousels (RAM + disk), Plex library availability GUID index, system landing reachability stats, active streams matrix, and Docker container fleet telemetry. Executed automatically on server boot, every 30 minutes in background cron (`src/lib/prisma.ts`), and on-demand via the 1-click **"⚡ Prewarm Caches"** button in `admin-system-health-grid.tsx`.
  - **Personalized User Prewarm (`prewarmUserSession`)**: Prewarms individual user request quotas (`user_quota:${userId}`), AI Server Assistant diagnostic snapshots (`user_diag_snapshot:${userKey}`), proactive Stream Quality Doctor alerts (`user_transcode_alert:${userKey}`), book library access permission (`user_lib_access:${userId}`), and personal Plex Hub stats (`user_plex_hub:${userKey}`).
- **Asynchronous Non-Blocking Lifecycle**:
  - Triggered automatically the instant a member logs in (`login()` in `auth-actions.ts`) and on initial client layout mount (`LayoutWrapper`).
  - Debounced per user session to run at most once every 3 minutes, completely eliminating redundant overhead.
  - Backed by an in-memory SWR cache (`getUserCache`, `setUserCache`, `clearUserCache`) with fine-grained TTLs (10s for landing stats, 15s for Docker fleet, 60s for user stream hubs, 3m for request quotas and library access).

---

### 40. Dynamic Residential ISP Subnet Matching & Remote Household Anchoring
- **Subnet Matching Heuristics (`isSameSubnetOrIp`)**:
  - Distinguishes residential ISP DHCP rotation by matching IPv4 `/24` subnets (first 3 octets, e.g. `73.18.20.15` and `73.18.20.210`) and IPv6 `/64` routing prefixes.
- **Remote Living Room TV Cold-Start Anchoring**:
  - When remote users without an established `primaryHomeIp` stream on a fixed living room TV (Apple TV, Roku, Fire TV, Smart TVs, Android TV) with zero concurrent multi-IP overlap, the system recognizes the stream as `🏡 Primary Home` ("Remote Home TV (IP)") rather than defaulting to `✈️ Travel / Away`.

---

### 41. Live Activity Transcode Telemetry, Resolution Downscaling & Power/Buffer Cockpit
- **Target Resolution Resolution (`resolveResolution`)**:
  - In Plex Media Server `/status/sessions`, `TranscodeSession` supplies target dimensions via `height` (e.g. 1080, 720, 480) and `width` (e.g. 1920, 1280) rather than a string `videoResolution` attribute.
  - `resolveResolution` evaluates both pixel dimensions (including cinemascope aspect ratios like 1920x800 for 1080p, 1280x534 for 720p) and standard string formats (`4k`, `1080`, `720`, `480`), ensuring downscaled streams accurately reflect their target resolution instead of falling back to source resolution.
- **Visual Downscaling & HDR Tone-Mapping Indicators**:
  - **Resolution Conversion**: When downscaling (`sourceResolution !== streamResolution`), render an amber glowing badge: `📉 4K UHD ➔ 1080p` or `📉 4K UHD ➔ 720p`.
  - **HDR Tone-Mapping**: When an HDR or Dolby Vision stream is transcoded down to SDR, render `✨ HDR10 ➔ SDR Tone Mapped` or `✨ Dolby Vision ➔ SDR Tone Mapped`.
- **Hardware Acceleration & Power Consumption Badges**:
  - **GPU Hardware Accelerated (`isHw`)**: Renders cyan badge with `<Zap className="h-2.5 w-2.5" />`: `{hwEngine} ({dec} ➔ {enc}) • Low Power` (e.g. `Nvidia NVENC (nvenc ➔ nvenc) • Low Power` or `Intel QuickSync • Low Power`).
  - **CPU Software Transcode**: Renders rose badge with `<Flame className="h-2.5 w-2.5" />`: `CPU Software • High Power` (signaling heavy CPU core saturation).
- **Multi-Edition & Transcode Media Selection**:
  - When a movie or episode has multiple files on disk (e.g. a 4K UHD file and a 1080p file), Plex creates a dedicated transcode `Media` entry with `selected: true` and active streams under `Part[0].Stream`.
  - Never naively read `s.Media[0]`. Always find the media marked `selected: true` or with `Part[0].selected`.
  - The active video stream's `displayTitle` (e.g. `"1080p (HEVC Main)"` or `"4K HDR10+ (HEVC Main 10)"`) is Plex's canonical indicator of the actual source resolution and codec, preventing false 4K reporting when a 1080p edition is played.
- **Transcode Speed, Throttle & Buffer Ahead Metrics**:
  - **Speed Multiplier**: Renders emerald badge `⚡ 2.8x speed (Real-Time OK)` when speed $\ge 1.0x$, or pulsing rose badge `⚡ 0.8x speed (Slow)` when $< 1.0x$ and unthrottled.
  - **Throttle Power Saving State (0.0x Speed is Healthy)**: When Plex pauses the transcoder because playback buffer is satisfied, Plex sets `throttled: true` and speed drops to `0.0x`. This is 100% HEALTHY (CPU/GPU at 0% idle power saving, never a red error!). Renders healthy emerald badge `⚡ 0.0x speed (Throttled • Power Saving)`.
  - **Buffer Ahead Duration**: Displays buffer lead time calculated from `maxOffsetAvailable - viewOffset` (e.g. `(+2m 00s buffer ahead)`).

---

### 42. Stream Intelligence Time Range Filtering, Aggregation Engine & User Directory Sorting
- **Single-Source-of-Truth Time Range Selector Bar**:
  - Positioned prominently above Metric Summary Cards with responsive layout (`flex-col md:flex-row`).
  - Supports preset filter pills: `All Time`, `Last 30 Days` (`30d`), `Last 60 Days` (`60d`), `Last 90 Days` (`90d`), and `Custom Range...` (`custom`).
  - When `Custom Range...` is active, displays native start date and end date inputs (`type="date"`) with timezone-safe start-of-day (`00:00:00.000`) and end-of-day (`23:59:59.999`) clamping, paired with an "Apply" button.
  - Active time range badge updates on Metric Summary Cards (Direct Play Rate and Hours Streamed) so administrators always have unambiguous visual context of the active time window.
- **Full Database SQLite SQL Aggregations (Zero Truncation)**:
  - Metric summary cards, user directory metrics, and library analytics must NEVER truncate records using arbitrary `take: 2000` or `take: 3000` limits.
  - Aggregations are calculated dynamically in SQLite via `COUNT(*)`, `SUM(durationMs)`, `SUM(directPlay)`, `SUM(transcode)`, and `SUM(sharingAlerts)`, completing in $< 500$ms even on databases with $> 28,000$ historical sessions.
- **User Directory Multi-Metric Sorting**:
  - Administrators can sort users on-the-fly via a dedicated sort dropdown:
    - **Most Plays** (`plays_desc`, default)
    - **Most Watch Hours** (`hours_desc`)
    - **Highest Transcode %** (`transcode_desc`)
    - **Most Sharing Alerts** (`alerts_desc`)
    - **Alphabetical (A-Z)** (`name_asc`)
  - Backed by zero-latency client-side `useMemo` sorting and server-side ordering.
- **User Telemetry Modal Range Toggling**:
  - When inspecting a user in the User Telemetry modal, administrators can toggle between the active page date range (e.g. `Last 30 Days`) and `All Time` right in the modal header to instantly compare recent streaming habits against all-time totals.
  - All numbers formatted with `toLocaleString()` for professional presentation.

---

### 43. Member Roadmap & Feature Announcements: User-Facing Beta Framing vs Admin Concealment
- **User-Facing Roadmap Rule**:
  - The public member Roadmap (`roadmap.md`, `getRoadmapText()`) is viewed by all authenticated members across DomsHomeLab.
  - **Strict Admin Feature Concealment**: Never include internal administrative tools, security heuristics, or surveillance engines in the member-facing Roadmap (e.g. cluster Tautulli telemetry, concurrent multi-IP monitoring, household fraud heuristics, Docker fleet management).
  - **Active Beta Notice**: Frame all newly released platform capabilities with an active beta notice inviting members to test features and report feedback or issues directly to Dominic / the administrator.
  - **Core Member Focus Areas**:
    - **What's New**: Unified 1-click media requests (movies, TV, ebooks, audiobooks), AI Server Assistant support bot, in-browser Kindle reader, 1-click Send-to-Kindle, floating audiobook player, Live Streams Doctor & Transcode diagnostics, personalized invite links, family sub-profiles (Kids & Living Room TV), custom library selection, and Radarr/Sonarr power user tools.
    - **Coming Soon**: 4K HDR badges, "Leaving Soon" collections and countdown ribbons, smart hubs and custom media tagging, member referral rewards, 1-click subtitle search, personal year-in-review, and real-time server status indicators.

---

### 44. Universal Mobile Viewport Optimization & Layout Container Architecture
- **Single Top-Level Main Layout Wrapper (`layout-wrapper.tsx`)**:
  - The root layout already encapsulates all page content inside:
    ```tsx
    <main className="flex-1 overflow-y-auto p-2.5 sm:p-4 md:p-6 lg:p-8 3xl:p-10 w-full min-w-0">
    ```
  - **Zero Duplicate Nested Padding Rule**: Subpages (`src/app/**/page.tsx`) must NEVER wrap themselves in redundant `min-h-screen`, `bg-background`, nested `<main>` tags, or duplicate `p-4 sm:p-6` padding. Doing so strips mobile viewports (< 640px) of 30–50px of precious horizontal space and introduces HTML accessibility violations (multiple `<main>` elements).
  - **Standard Subpage Root Container**:
    ```tsx
    <div className="flex-1 max-w-7xl 2xl:max-w-[1600px] 3xl:max-w-[2200px] 4xl:max-w-[2560px] mx-auto w-full min-w-0 space-y-4 sm:space-y-6 animate-in fade-in duration-500">
    ```
- **Mobile Action Stacking & Responsive Controls**:
  - Header control bars, search inputs, instance selectors, and filters must adapt cleanly on small screens:
    - Use `flex-col sm:flex-row gap-2 sm:gap-3` on control rows.
    - Full width on mobile: `w-full sm:w-auto` or `w-full sm:w-48`.
    - Stackable buttons: `flex-1 sm:flex-initial justify-center` so touch targets are large and easy to tap.
  - Multi-button card actions (such as in Admin Scripts or Arr queues) must use `flex-wrap items-center justify-between gap-2` with `flex-1 min-w-[120px]` on primary action buttons so they never truncate or overflow outside the card boundaries.
- **Universal Mobile Modal Sizing**:
  - All modals, sheets, and dialogs must specify `w-[95vw]` to prevent clipping on 360px–420px mobile screens:
    ```tsx
    <DialogContent className="w-[95vw] sm:max-w-2xl max-h-[90vh] overflow-y-auto overflow-x-hidden p-4 sm:p-6">
    ```
  - Form footers in dialogs must use `flex-col-reverse sm:flex-row gap-2 sm:gap-0` with `w-full sm:w-auto` for action buttons.

---

### 46. Sidebar & Header Navigation Architecture (`SidebarNavContent`)
- **DRY Desktop & Mobile Parity**:
  - The navigation structure is unified in `SidebarNavContent` (`src/components/sidebar.tsx`) to prevent code duplication between Desktop (`<aside>`) and Mobile (`<Sheet>`).
- **Header Structure & Typography**:
  - App title: `DomsHomeLab` formatted with `whitespace-nowrap font-bold shrink-0 text-foreground` ensuring zero truncation across mobile and desktop scaling.
  - Vertical lockup: Compact `<BuildBadge variant="compact" isAdmin={isAdmin} />` mounted directly below the title.
- **Admin-Only Build Telemetry Gating**:
  - Passing `isAdmin={isAdmin}` strictly gates the interactive build modal, commit SHA copying, and workflow links to Administrators.
  - Non-admin users see a static indicator (`cursor-default select-none`) with no modal mounted in the DOM.
- **Vibrant Signature App Colors**:
  - All icons and active highlights preserve recognizable brand accents:
    - Plex: Amber (`text-amber-400`)
    - Sonarr: Sky (`text-sky-400`)
    - Radarr: Yellow (`text-yellow-400`)
    - Tautulli: Flame Orange (`text-orange-400`)
    - Glances: Purple (`text-purple-400`)
    - Docker Fleet: Cyan (`text-cyan-400`)
    - User Scripts: Emerald (`text-emerald-400`)
    - Tickets: Rose (`text-rose-400`)
- **AI Assistant Hero Card**:
  - Full-width hero container with dual-tier typography, glowing bot icon, and live pulse status badge (`24/7 AI Diagnostic Engine Active`).
- **Top-Level Curation Studios Section**:
  - Rendered as first-class, unindented `NavItem` elements with zero accordion dropdowns and pixel-perfect alignment across Desktop and Mobile sidebars.
- **System Settings & Live System Logs Navigation**:
  - Rendered as dedicated, full-width NavItem components with Live System Logs positioned directly below System Settings jumping to /settings?tab=logs.

---

### 46. Multi-Platform Media Server Auto-Provisioning & Streaming Password Architecture
- **Plex OAuth vs Jellyfin/Emby Password Reality**:
  - DomsHomeLab members authenticate via Plex OAuth and have no local passwords stored in Portalarr.
  - Jellyfin and Emby accounts created via `POST /Users/New` initialize with a **BLANK (no password)** default state.
  - Setup Guide Step 2 clearly explains this: members sign into Jellyfin client apps with their portal username and **leave the password field blank**.
- **Instant Auto-Provisioning on Modal Mount**:
  - Opening the setup guide modal (`MediaServerSetupGuideModal`) immediately invokes `ensureUserMediaServerProvisionedAction(serverId)` in the background.
  - If the user does not yet exist on Jellyfin/Emby, Portalarr automatically provisions the user, configures library access policies, and saves `jellyfinUserId` / `embyUserId` in `prisma.user`.
- **Dedicated Streaming Password Manager**:
  - Inside Step 2 of the setup guide, users can optionally set a dedicated streaming password (min 4 characters) directly within Portalarr via `setUserMediaServerPasswordAction`.
  - Portalarr pushes the new password to the Jellyfin API (`POST /Users/{id}/Password`) using admin API credentials, without requiring members to access the Jellyfin web client settings.
- **Reverse Proxy Header Stripping & Dual-Mode Auth Fallback**:
  - Reverse proxies (like Nginx Proxy Manager and Cloudflare) frequently strip non-standard HTTP request headers like `X-Emby-Token` or `Authorization`.
  - `mediaServerFetch` implements automatic query parameter fallback: if header authentication returns HTTP 401 or network errors, it retries transparently with `?api_key=${apiKey}` appended to the URL.
- **Two-URL Dual-Routing Architecture (Public Client URL + Internal LAN Fallback URL)**:
  - **Public Client URL (`url`)**: The public reverse proxy address (e.g. `https://jellyfin.domshomelab.com`) presented to members in the Setup Guide and used by remote player apps, as well as pinged by Portalarr to monitor external reachability.
  - **Internal LAN Fallback URL (`internalUrl`)**: The direct local network address (e.g. `http://192.168.1.87:8096`) used by Portalarr for high-speed backend API operations (user provisioning, password updates, library scans, and Quick Connect authorization) to completely bypass reverse proxy header stripping, SSL overhead, and NAT loopback.
  - **Resilient Fallback**: `resilientMediaServerFetch` automatically tries the internal LAN URL first if available, and transparently falls back to the public URL.
- **Native Quick Connect TV & Device Pairing (`authorizeMediaServerQuickConnectAction`)**:
  - Embedded in Step 2 of `MediaServerSetupGuideModal`: allows members to enter the 6-character Quick Connect code displayed on smart TVs, Apple TV (Swiftfin), Android TV, Roku, or Fire TV.
  - Portalarr calls `POST /QuickConnect/Authorize?Code={code}&UserId={userId}` using admin credentials and resilient internal LAN routing, immediately logging the TV into the member's account with zero remote typing.
  - Includes a direct fallback button opening the Jellyfin Web Quick Connect page (`${resolvedUrl}/web/index.html#!/quickconnect.html`).

---
Before completing any task, execute:
1. `cmd /c "npm test"`: Full 18+ suite verification (`scripts/verify-all.ts`), 0 failures.
2. `cmd /c "npm run build"`: Next.js production build, 0 TS errors, 100% clean.
3. Skills & Documentation Sync: Update `.agents/skills/` and `.md` files with architectural learnings.
4. SemVer Version Increment & Git Deployment Push: Increment version in `package.json` according to SemVer (PATCH `+1` for fixes/polish, MINOR `+1` for features), commit with freshly incremented `[v<version>]` prefix, push strictly to `origin/main` (Beta). NEVER push to `stable` unless the user explicitly instructs.

---

### 45. Unified Payment Pricing, Prorated Billing & Referral Discount Alignment
- **Standard Pricing Fallbacks**:
  - **Tier 1 (Standard)**: `$180.00/year` (averaging `$15.00/mo` for annual Rest-of-Year proration and referral reward credits) and `$17.50/month` for the standalone Monthly Plan.
  - **Tier 2 (VIP / Managed Support)**: `$240.00/year` (averaging `$20.00/mo` for annual proration and referral reward credits) and `$25.00/month` for the standalone Monthly Plan.
  - Never fall back to `$15` for standalone monthly plan displays in `PaymentMethodsGrid`, `PaymentQrModal`, `TrialDashboardView`, `/join`, `/pending`, or `/profile`; always use `config?.monthlyPrice ?? 17.50`.
- **Consistent Prorated Quotes & Payment Prefilling**:
  - For active Trial accounts on `/` and `/profile`, always pass `trialEndDate: user?.trialEndsAt` to `calculateProratedBilling` so both views display identical prorated Rest-of-Year and Rest-of-Month dollar amounts.
  - For expired/suspended accounts reactivating on `/pending`, pass `trialDays: 0` to `calculateProratedBilling` so proration begins immediately from today rather than 14 days in the future.
  - On `/profile#billing`, pass the user's net effective amount due (accounting for trial proration, converted referral discounts, and `user.accountCredit`) into `<PaymentMethodsGrid amount={...} cadence={...} />`.
- **Threshold Engine & Scraper Reconciliation (`evaluatePaymentThreshold`)**:
  - Automatically honors active referral discounts (`effectiveYearlyTarget = yearlyPrice - referralDiscount`), Rest-of-Year prorated annual quotes (within `$1.00` tolerance), and first-month prorated standalone monthly quotes (within `$0.50` tolerance) as full subscription fulfillments.

---

### 46. Dispatched Email Audit Log Architecture (`/settings/access?tab=sent-emails`, `SentEmailAuditLog`, `SentEmailLog`)
- **6-Tab Access Control Navigation**:
  - The Access Control directory (`src/app/settings/access/page.tsx`) features 6 dedicated tabs organized in a balanced `grid-cols-2 sm:grid-cols-3 lg:grid-cols-6` layout:
    1. **User Directory**: Member directory, roles, and live Plex library shares.
    2. **Referrals & Leaderboard**: Ambassador referral ranks, rewards, and credits.
    3. **Payment & Onboarding**: Trial safe pool, automated proration, and pricing tiers.
    4. **Email Scraper**: IMAP/Gmail automated payment scraping and ledger reconciliation.
    5. **Approval Queue**: Staged live PMS modifications and staged user-facing emails.
    6. **Sent Emails (`sent-emails`)**: Complete outbound email audit log displaying dispatch modes, delivery status, and full message previews.
- **Automatic vs Approved & Sent Distinction (`SentEmailLog`)**:
  - **Sent Automatically (`sendMode: "AUTOMATIC"`)**: Displays a purple/indigo badge (`bg-purple-500/15 text-purple-400 border-purple-500/40`) with `Bot` icon indicating messages triggered autonomously by background system workflows (welcome emails, automated renewal notices, system alerts, test emails via `sendTestEmailAction`, template preview tests, and scheduled digests).
  - **Approved & Sent (`sendMode: "APPROVED_AND_SENT"`)**: Displays an emerald badge (`bg-emerald-500/15 text-emerald-400 border-emerald-500/40`) with `ShieldCheck` icon indicating messages that were staged in the Action Approval Queue and vetted by an administrator prior to live SMTP transmission. Displays approver identity (`Approved by "Admin"`) and exact approval timestamp.
  - **Comprehensive Outbound Logging**: 100% of outbound platform email paths (automated workflows, approved queue dispatches, test connection checks via Resend or Custom SMTP, template previews, and admin approval notifications) record directly to `SentEmailLog` to ensure the audit log is never falsely empty.
- **Audit Metrics & Telemetry Grid**:
  - **Total Dispatched**: Platform-wide outbound email volume with `Mail` icon in sky blue (`text-sky-400`).
  - **Sent Automatically**: Count of autonomous notifications in purple (`text-purple-400`).
  - **Approved & Sent**: Count of vetted dispatches in emerald (`text-emerald-400`).
  - **Delivery Failures**: Count of SMTP rejections or network errors in rose (`text-rose-400`).
- **Inspection Modal & Operator Controls**:
  - **Rendered Message Preview**: Sandboxed HTML view displaying the exact layout, styles, and branding received by the recipient.
  - **Plaintext View & Audit Metadata**: Displays raw plain text body, log IDs, SMTP errors, and template identifiers.
  - **1-Click Resend (`resendSentEmailAction`)**: Allows administrators to re-dispatch any previous message directly to the recipient via SMTP with immediate visual feedback.
  - **Clean Pruning**: Supports individual log deletion and platform-wide audit log clearing.

---

### 41. Universal Floating Suggest Fix Launcher & Decoupled SMTP Settings Architecture
- **Floating Suggest Fix Launcher (`FloatingSuggestFixLauncher` & `SuggestFixModal`)**:
  - Mounted globally in `src/components/layout-wrapper.tsx` at `fixed bottom-16 right-4 sm:bottom-20 sm:right-6 z-40` for all authenticated members (positioned just above the AI Assistant pill).
  - Explicit canonical label: **`Suggest Fix`** with `Wrench` icon (`text-amber-200`) and glowing purple/indigo pill gradient (`from-amber-600 via-purple-600 to-indigo-600`).
  - Dismissible with `X` button and programmatically operable via `window.dispatchEvent(new CustomEvent("open-suggest-fix"))`.
- **Decoupled SMTP & Resend Settings Architecture (`src/app/settings/page.tsx`)**:
  - Resend credentials (`resendApiKey`, `resendFrom`) and Custom SMTP credentials (`customSmtpHost`, `customSmtpPort`, `customSmtpUser`, `customSmtpPass`, `customSmtpFrom`) are completely isolated in separate database columns and UI form states.
  - **Active Outbound Email Engine Selector Bar**: Administrators can toggle which outbound engine is active using dedicated selector buttons: `Resend (Domain: @domshomelab.com)` with purple styling and `Custom SMTP (Gmail / Outlook / SES)` with sky-blue styling, each displaying real-time `[ ACTIVE ]` vs `[ Standby ]` indicators.
  - **Panel Status Badges & Quick Set-Active Controls**: Each provider panel features an `Active Engine` emerald pulse badge or a direct 1-click `Set Active` action button.
  - **Provider-Aware Test Connection (`sendTestEmailAction(emailProviderMode)`)**: When an administrator clicks `Test Connection (Resend)` or `Test Connection (Custom SMTP)`, the action tests the explicitly chosen provider mode rather than whatever was previously saved in the generic SMTP fields. Resend tests route strictly through `smtp.resend.com:465` with `notifications@domshomelab.com`, while Custom SMTP routes through the configured custom host/credentials.
  - Switching between provider tabs never mutates or overwrites the other provider's credentials, preventing API keys and passwords from overwriting each other.
  - Active provider mode synchronizes outbound SMTP parameters while leaving both credential sets permanently preserved.

### 42. Outbound Kindle Sender Update Notice & Ebooks Request Tab Banner (`KindleSenderNoticePopup`, `KindleSenderUpdateBanner`, `KindleSenderUpdateModal`)
- **Targeted Trigger Architecture (`KindleSenderUpdateBanner`)**:
  - Rendered on the Ebooks request tab in Media Requests (`src/components/seerr/discover-hub.tsx` when `activeTab === "ebooks"`) and Book Library (`src/app/library/page.tsx`).
  - For existing Kindle users whose accounts require the outbound sender update (`user.kindleSenderUpdateAcknowledgedAt === null`), automatically displays the action-required update banner and modal.
  - Confirming writes `user.kindleSenderUpdateAcknowledgedAt = new Date()` via `acknowledgeKindleSenderUpdateAction()`, permanently dismissing it.
- **Clickable Amazon Settings Link**:
  - Displays `https://www.amazon.com/hz/mycd/myx#/home/settings/payment` as an active, clickable link (`target="_blank" rel="noopener noreferrer"`) in modal descriptions, step-by-step instructions, and tab banners.

### 43. Send-to-Kindle First-Time Setup Guide & Onboarding Architecture (`KindleSetupGuideModal`, `KindleSenderUpdateBanner`)
- **Automatic Setup Detection**:
  - Whenever a member without Send-to-Kindle configured (`!user.kindleEmail` or `user.kindleEmail === "DIRECT_DOWNLOAD"`) accesses the **Ebooks requests tab** in Media Requests (`/requests?tab=ebooks` or `/discover?tab=ebooks`), the **Book Library** (`/library`), or clicks **Request Ebook** on any book card (`book-detail-modal.tsx`), the system guides them through complete setup.
- **Interactive 3-Step Setup Wizard (`KindleSetupGuideModal`)**:
  1. **Step 1: Find Kindle Email**: Direct clickable link to Amazon Personal Document Settings (`https://www.amazon.com/hz/mycd/myx#/home/settings/payment`) to find their `@kindle.com` address.
  2. **Step 2: Authorize Homelab Sender**: Shows `kindle@domshomelab.com` with 1-click clipboard copy (`copied ? "Copied!" : "Copy Email"`).
  3. **Step 3: Direct In-Modal Save**: Inline input with real-time `@kindle.com` validation and a 1-click **"Save & Activate Kindle"** button calling `updateCurrentUserKindleEmail(cleanEmail)` to immediately activate wireless delivery without leaving the page.
- **Full Viewport Responsive Modals & Footers**:
  - Base `DialogContent` standardizes `max-h-[92vh] overflow-y-auto scrollbar-thin` to ensure no modal clips vertically in landscape orientation or on small mobile devices.
  - Dialog footers strictly follow `flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2.5` with `w-full sm:w-auto shrink-0 whitespace-nowrap` on action buttons to prevent text wrapping or truncation on narrow screens (<375px).

### 44. End-User Plain-English Terminology Standards (Zero Jargon Policy)
To ensure Portalarr remains approachable for non-technical family members, trial accounts, and casual users, user-facing views must strictly adhere to plain-English replacements:
- **Build & Branch Telemetry (`BuildBadge`)**: Non-admins seeing `variant="full"` are shown `Beta Preview • v<version>` or `Production • v<version>`. Git branch names (`(main)`, `(stable)`), commit short hashes (`[90fb926]`), and workflow run badges are strictly restricted to administrators.
- **Streaming Quality vs Direct Play**:
  - Replace "100% Direct Play" with **"Original Quality (Zero Buffering)"** or **"Maximum Quality"**. Plex device apps label their setting "Maximum / Original Quality", so users cannot find a setting called "Direct Play".
  - Replace "4K Remux Ready" with **"Maximum 4K HDR Quality"**.
  - Replace "1080p High Bitrate Ready" with **"Crisp 1080p Full HD"**.
- **Server Processing vs Transcode Doctor**:
  - Transcode Doctor modal is presented to members as **"Stream Quality & Playback Diagnostics"**.
  - Server transcode decisions are presented as **"Original Quality (Direct Play)"**, **"Optimized via Hardware Acceleration"**, or **"Server Transcoding Active"** under a clean **"Server Processing"** header.
- **AI Assistant Labels**:
  - Live Telemetry tab ➔ **"Live Stream Stats"**.
  - Server Disk & Probes tab ➔ **"Server Health Check"**.
  - NVENC HW badge ➔ **"GPU Accelerated"**.
  - Video/Audio Codec ➔ **"Video Format"** / **"Audio Format"**.
  - Synthetic probes / byte-range reads ➔ **"Live diagnostic tests measuring drive read performance and streaming health"**.
- **Daemon & Backend App Names**:
  - In media requests and detail modals, avoid surfacing raw *Arr names ("Sonarr", "Radarr", "Prowlarr", "Tautulli"). Use **"Movie Manager"**, **"TV Manager"**, **"Stream Monitor"**, and **"Online Catalogs / Release Sources"**.
  - Button text: "Re-Search Movie in Radarr" ➔ **"Re-Search Releases"**.
- **System Email Notices & Templates**:
  - Replace raw protocol names: "SMTP server rejected the delivery" ➔ **"Amazon's email service rejected the delivery"**.
  - Replace Usenet/torrent indexer terms: "when indexers or sources become available" ➔ **"when new releases or sources become available"**.
  - Replace homelab terms: "transcoding allocation" ➔ **"high-priority dedicated streaming allocation for smooth playback anywhere"**.
  - Standardize streaming terminology: "Direct Play" ➔ **"Original Studio Quality"** / **"Original Quality"**.
  - Diagnostic references: "Stream Quality Doctor" ➔ **"Stream Diagnostics & Device Setup Guides"**.

### 45. User Media Server & Library Access Verification Standards (Zero False-Positive Permissions)
To prevent confusing false positives on user settings and profile pages:
- **Audiobooks Plex Library Access Gating (`getUserAudiobooksLibraryAccessAction`)**:
  - Must strictly verify whether the user actually has the Plex Audiobooks library granted via active live Plex share (`livePlexShareKeys`) or explicit local library access.
  - The presence of the `audiobooks` add-on in `enabledAddons` alone must NEVER cause "Plex Library Granted" or the toggle switch to report true if Plex has not actually granted the library.
  - Local web bookshelf libraries (`prisma.library`) with wildcard `allowedUsers: "*"` must NEVER cause "Plex Library Granted" or switch check to report true.
- **Multi-Platform Media Servers & Libraries (`getUserMediaServersAndLibrariesAction`)**:
  - Automatically queries live Plex friend shares (`getUserPlexSharedLibraries`) to match per-server shares so all active servers (e.g. Main Server, Kids Server) and their exact shared sections properly evaluate to `isSelected: true`, completely eliminating single-server alphabetical fallback bugs.
  - Secondary media platforms (Jellyfin and Emby) must never default to `isServerSelected: true` or have libraries checked for users who have not opted in, been granted explicit access (`allowedServerKeys`), or been provisioned on the remote server (`jellyfinUserId` / `embyUserId`).
  - When a server is unselected/disabled, its individual libraries must evaluate to `isSelected: false` with zero selections returned in `selectedMediaLibraryKeys`.
  - On update (`updateUserMediaServersAndLibrariesAction`), preserves per-server machine identifiers (`${srvMachineId}:${secId}`) when dispatching to `syncUserPlexShareInternal` to ensure multi-server shares are never overwritten or collapsed onto a single server.

---

As the Portalarr frontend evolves or new design decisions are finalized:
1. **Adding a New UI Rule**: Add the rule to the relevant section above or under `references/`.
2. **Tweaking Component Defaults**: Update the corresponding reference file in `references/`.
3. **Documenting New Pages or Studios**: Create a new reference file in `references/` and link it here.

Detailed guide on updating: [updating-this-skill.md](./references/updating-this-skill.md).

---

## 📚 Reference Documents

- [Modal & Dialog Patterns](./references/modal-and-dialog-patterns.md)
- [Card & Poster Patterns](./references/card-and-poster-patterns.md)
- [Form & Input Patterns](./references/form-and-input-patterns.md)
- [Theme & Color Tokens](./references/theme-and-color-tokens.md)
- [Updating This Skill](./references/updating-this-skill.md)
### 46. "What's New in DomsHomeLab" Role-Based Gating & Zero-Jargon Protocol
- **Source of Truth (`roadmap.md`)**:
  - Maintained with clean, approachable, plain-English release highlights and coming soon items.
  - Features designated for administrators must be marked with `(Admin)` so they are programmatically excluded for all non-admins.
  - Features designated for super users must be marked with `(Super Users)` so they are excluded for standard users and trial accounts.
  - Zero raw jargon: strictly replace "Direct Play" with "Original Quality (Zero Buffering)", "Quality Doctor" with "Stream Diagnostics", "playback telemetry" with "stream health stats", and avoid daemon/tool names ("Radarr", "Sonarr", "Dispatcharr").
- **Dynamic Role Filtering (`filterRoadmapByRole` in `src/components/whats-new-modal.tsx`)**:
  - **Administrator View (`role === "ADMIN"`)**: Full visibility into all features, administrative auditing tools, and operational roadmaps.
  - **Super User View (`role === "SUPER_USER"`)**: Excludes any administrative items, action approval queues, or outbound audit logs, but retains power-user queue and release management.
  - **Standard User View (`role === "USER"`)**: Retains full member perks (Ebooks & Audiobooks subsystem with reading/Kindle features, multi-platform media servers, family sub-profiles, poster curation badges, and Live TV preview) while excluding admin tools and super user management.
  - **Trial Account View (`role === "TRIAL"`)**: Excludes full-member exclusive features (Ebooks & Audiobooks subsystem including indented child items, multi-platform media servers, family profiles, poster curation badges, and Live TV) and smoothly adapts Unified Media Requests to `(Movies & TV Shows)`.
  - **Automatic Jargon Sanitation Pass**: Automatically translates any residual technical jargon ("Direct Play", "Quality Doctor", "playback telemetry", "homelab streaming", "Dispatcharr") into clean, friendly plain English.
  - **Mandatory Pre-Push Audit**: Verified automatically in Suite 22 of `scripts/verify-all.ts` across all 4 role views before every deployment push.

### 47. Guide Surfaces & Coming Soon Alignment Standard
- **Zero Misrepresentation Policy**: All user-facing documentation surfaces (`USER_GUIDE.md`, `user_guide_ebooks.md`, `src/app/guides/page.tsx`, `src/components/feature-guide-modal.tsx`, `src/app/join/page.tsx`, `src/lib/discord/discord-bot.ts`, `src/lib/email-templates.ts`) must strictly mirror the roadmap's Coming Soon status for upcoming platform features (e.g. Member Referral Rewards, Family Sub-Profiles, Persistent Floating Web Audio Player, Enhanced Curation & Poster Badges).
- **Mandatory (Coming Soon) Tagging**: Upcoming features must always be labeled with `(Coming Soon)` or `*(Upcoming Feature — Currently in Development)*`, ensuring members and visitors are never misled into believing an in-development feature is already operational.

### 48. Cloudflare Zero Trust Strict Admin Path Isolation
- **Admin-Only Blocking Architecture**: Cloudflare Zero Trust blocks access strictly to designated Admin-Only paths (`/settings*`, `/admin*`, `/curation*`, `/tautulli*`, `/streams*`, `/api/admin*`, `/api/system*`, `/api/debug*`, `/api/curation*`, `/api/users*`, `/api/books/upload*`). All other paths are open at the edge and handled by Portalarr's native JWT session management.
- **Strict Prohibition of User/Super User Features Under Admin Prefixes**: No user-facing or super-user-facing page, button, link, or API fetch may ever target an admin-only path.
- **Canonical `/profile` Route**: User profile, server selection, and password management reside strictly at `/profile`. Any legacy hits to `/settings/profile` are automatically redirected to `/profile` on the server. Non-admins must never fetch `/api/users` on `/library` or any other view.


### 49. Dual Roadmap Architecture: User-Facing Roadmap vs Developer Backlog
- **Separation of Concerns**:
  - **User-Facing Roadmap (`roadmap.md`)**: Publicly accessible and tailored across 4 role views (`USER`, `TRIAL`, `SUPER_USER`, `ADMIN`). Formatted in approachable, plain English zero-jargon language highlighting platform capabilities, media features, and new enhancements.
  - **Developer Maintenance Backlog (`docs/DEV_ROADMAP.md`)**: Strictly restricted to Administrators. Contains technical maintenance tasks, background scheduler mutexes, edge policies, Docker socket optimizations, API sync pipelines, and database migrations.
- **UI Interaction & Gating**:
  - `WhatsNewModal` (`src/components/whats-new-modal.tsx`) provides an integrated dual-tab switcher (`🚀 User Roadmap` vs `🛠️ Developer Roadmap`) mounted strictly for verified Administrators (`userRole === "ADMIN"`).
  - Dedicated `[🛠️ Dev Roadmap]` button (`DevRoadmapModal`) is mounted on the Home Dashboard (`src/app/page.tsx`) header lockup and inside `AdminDetailedStreams` (`src/components/admin-detailed-streams.tsx`).
  - **Settings Management**: In `/settings?tab=announcements`, administrators can edit, preview, and save both `roadmap.md` and `docs/DEV_ROADMAP.md` via a dual-tab Markdown editor with dirty state tracking.
  - **Container Packaging**: `Dockerfile` copies `/app/docs` to the runtime container so developer maintenance logs persist in Docker homelab deployments.


### 50. Live TV & Channel Lineup UI Architecture
- **Origin Channel Logo Proxy (`/api/iptv/logo/[id]`)**: To prevent Mixed Content (`http://` on `https://`) blocks and unroutable private LAN IP (`192.168.x.x`) failures on remote client devices, channel logos from Dispatcharr are proxied through Portalarr's HTTPS origin with 7-day browser caching (`Cache-Control: public, max-age=604800, stale-while-revalidate=86400`).
- **Fail-Safe Card Logo Fallback**: `ChannelCard` components dynamically sanitize raw upstream URLs to the proxy path, handle `onError` via component state, and render a semantic Lucide genre icon (e.g. `Trophy`, `Tv`, `Newspaper`, `Baby`, `Film`) if the image fails or is unavailable, preventing blank or broken cards.
- **Dynamic Media Market Customization Shelves**: Displays sticky anchor feeds for the host server market (Dallas CBS/NBC/FOX/ABC/CW) alongside a client-selected or IP-detected local media market shelf, college sports (NCAA), and NFL showcase carousels.
- **DVR Stream Reservation Controls**: Dedicated stream headroom reservation prevents concurrent client live TV viewers from starving scheduled Plex DVR tuner recordings, configurable by homelab administrators down to 0 if DVR recording is not utilized.


### 51. Member Live TV Access & Platforms Management UI (`admin-iptv-client.tsx`)
- **Plex 3-Tier Restriction Badge Lockup**:
  - `Live TV + DVR` (Emerald `bg-emerald-500/20 text-emerald-300`): Displayed when user has both live channel and DVR privileges (`Allow Live TV and DVR access` in Plex).
  - `Live TV Only` (Sky Blue `bg-sky-500/20 text-sky-300`): Displayed when user has channel tuning without DVR recording privileges (`Allow Live TV only` in Plex).
  - `⚠️ Missing Live TV & DVR` (Rose `bg-rose-500/20 text-rose-300`): Displayed when user lacks tuner and DVR access (`No Live TV and DVR access` in Plex).
- **Hierarchical Action Buttons**:
  - `[Live TV: ON]` / `[Enable Live TV]`: Toggles live stream privileges. Revoking Live TV automatically revokes DVR privileges.
  - `[DVR: ON]` / `[Enable DVR]`: Toggles DVR recording privileges. Granting DVR automatically ensures live tuner privileges are active.
  - `[Free Slot]`: Ghost button demoting the user to a regular Plex friend to free up one of the 14 shared Plex Home slots.
- **Card Status Outlines**: Cards are outlined with `border-rose-500/40 bg-rose-500/5` when a Plex Home member lacks live privileges, and `border-amber-500/30 bg-amber-500/5` when identified as an inactive rotation candidate.


### 52. Secondary & Linked Notification Inboxes (`/profile`)
- **Multi-Inbox Notification Architecture**:
  - Homelab members frequently request that their spouse, partner, or family member receive specific notifications (e.g. billing receipts or media request approvals) without sharing account passwords.
  - In `/profile` under **Secondary & Linked Inboxes**, members can link additional notification emails stored in `prisma.linkedNotificationEmail`.
  - **Granular Category Routing**: Each linked inbox has independent category toggles (`BILLING`, `REQUESTS`, `MAINTENANCE`).
  - **User-Level Notification Preference Second Gate**: User-level notification settings in `user.emailPreferences` act as an absolute second gate. If the account owner opts out of a category (e.g. Media Available alerts), dispatches to both the primary inbox and any linked inboxes for that category are strictly suppressed.


### 53. User Directory Sorting & Account Age (`/settings?tab=access`)
- **Multi-Column Directory Sorting**:
  - In the User Management panel (`/settings?tab=access`), administrators can sort members by `lastLogin` (active vs inactive), account creation date, username, role, or storage footprint.
  - Dynamic `lastLogin` tracking in `createSession()` updates automatically on password sign-in, Plex SSO, and active site visits.
  - Active vs Inactive indicators display relative age (`Joined: MMM d, yyyy • Last Login: 4d ago` vs `Never`).


### 54. First-Time Send-to-Kindle Setup Guide & Amazon Approved Sender Notice
- **Amazon Approved Personal Document List Protection**:
  - Amazon Kindle devices reject `.epub` deliveries from unapproved sender addresses with a silent delivery failure.
  - Portalarr dispatches ebooks from `books@domshomelab.com`.
  - **Auto-Popup Sender Notice Modal**: On the eBooks request tab and book library shelf, a setup guide pops up for first-time visitors with a 1-click link to their Amazon Personal Document Settings (`amazon.com/myk`), guiding them to add `books@domshomelab.com` to their Approved Personal Document E-mail List.
  - **Persistent Dismissal**: Once acknowledged, dismissal is stored in `localStorage` (`kindleSenderNoticeDismissed`) so members are not repeatedly interrupted.


---

## 🚨 Mandatory Task Completion Protocol (Strict SemVer)

To guarantee 100% reliability, quality control, and consistency, the following 5-step protocol MUST be executed at the end of every task or feature change before considering the work complete:

0. **Step 0: Read Skill Upfront**: Call `read_file` on the relevant `SKILL.md` before writing code.
1. **Step 1: Integration Testing**: Execute `cmd /c "npm test"` to run the verification suite (`scripts/verify-all.ts`). All test suites must pass (0 failures).
2. **Step 2: Production Build Verification**: Execute `cmd /c "npm run build"`. Ensure 100% clean compilation, zero TypeScript errors, and zero Turbopack runtime errors.
3. **Step 3: Edge Security & Cloudflare Policy Audit**: Whenever ANY page route (`src/app/**/page.tsx`) or API route (`src/app/api/**/route.ts`) is created, moved, or updated, register it in `src/lib/edge-policy-paths.ts` and inform the user.
4. **Step 4: Skills & Documentation Sync**: Review and update relevant `.agents/skills/` documents to record any new UI patterns, API contracts, formulas, or operational guidelines **BEFORE** committing.
5. **Step 5: SemVer Version Increment & Git Deployment Push**: Increment version in `package.json` according to SemVer (PATCH `+1` for fixes/polish, MINOR `+1` for features), stage all changes (`git add -A`), commit with freshly incremented semantic version prefix (`[v<version>] feat/fix(scope): message`), push strictly to `origin/main` (Beta). NEVER push to `stable` unless the user explicitly instructs.
