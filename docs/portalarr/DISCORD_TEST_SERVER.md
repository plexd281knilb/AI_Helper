# 🧪 DomsHomeLab Test Discord Server Architecture & Parity Blueprint

> **Environment**: Test & Sandbox Discord Server  
> **Server Name**: `Test Plex Server`  
> **Guild ID**: `1559231517325135892`  
> **Portalarr Target Version**: `v1.1.0`  
> **Active Member Count**: 2 (Gemini_CLI_Connector Bot + Admin)  
> **Live Production Counterpart**: `Plex Group` (`553667067363196941`)

---

## 1. Executive Summary & Purpose

The **Test Plex Server** serves as the isolated staging environment for all DomsHomeLab Discord bot automations, permission isolation tests, pinned embed formatting, and community engagement experiments before rolling them out to the 20+ active household members on the live production server (`Plex Group`).

Using this environment prevents notification spam, avoids broken embeds, and guarantees that role synchronization, channel permissions, and automated system alerts function with 100% reliability.

---

## 2. Role Hierarchy & Provisioning Matrix

Roles provisioned by `syncDiscordServerAction` in accordance with `DISCORD_ROLES_BLUEPRINT`:

| Position | Role Name | Role ID | Color | Permissions | Purpose & Scope |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **8** | `Gemini_CLI_Connector` | `1559235023700500600` | Default (`#000000`) | Administrator (`0x8`) | Integrated Discord Bot application execution & channel management |
| **7** | `👑 Admin` | `1559236186810224753` | Amber (`#F59E0B`) | Elevated Member | Platform administrators, homelab operators, full system access |
| **6** | `🛡️ Moderator` | `1559236188303523970` | Indigo (`#06B6D4`) | Moderation | Community ticket helpers, requests triage |
| **5** | `⭐ Member` | `1559236190140629234` | Emerald (`#10B981`) | Standard Member | Approved active Plex streamers, media requests, community chat |
| **4** | `⏱️ Trial Pass` | `1559236190908055552` | Blue (`#3B82F6`) | Isolated Read | 48-Hour evaluation accounts (restricted to `#welcome-and-rules`) |
| **3** | `🧒 Kids Account` | `1559236191847452684` | Pink (`#EC4899`) | Child Profile | Managed household child profile (filtered requests, kids library) |
| **2** | `📺 Living Room Device`| `1559236192589971516` | Violet (`#6366F1`) | Device Profile | Shared household Apple TV / Nvidia Shield account |
| **1** | `⏳ Pending Approval` | `1559236193797931170` | Gray (`#9CA3AF`) | Read Only | Users awaiting administrator verification & onboarding |
| **0** | `@everyone` | `1559231517325135892` | Default (`#000000`) | View Only Rules | Default role. Blocked from chatting until account is linked |

---

## 3. Complete Channel & Category Architecture Map

All channels in the Test Server are organized strictly under 7 functional categories aligned with the canonical blueprint:

### 📌 Category 1: WELCOME & INFO (`1559236195433578551`)
*Public read-only landing zone for onboarding, device invites, and platform policies.*

| Channel Name | Channel ID | Type | Read / Write | Pinned Embed Key | Description & Topic |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `#welcome-and-rules` | `1559236196901847060` | Text | Read-only | `welcome_rules` | Community etiquette, zero-pricing rules, account linking |
| `#announcements` | `1562546144289095821` | Text | Read-only | — | Official platform updates, maintenance notices, outages |
| `#membership-info` | `1559236207605452842` | Text | Read-only | `membership_info` | Household features, request privileges, guidelines |
| `#links-and-webhooks` | `1559236216182800518` | Text | Read-only | `links_webhooks` | Portalarr Web Portal, Seerr, Tautulli, and external links |
| `#roadmap-and-updates`| `1559236222105297046` | Text | Read-only | `roadmap_updates` | Storage upgrades, 4K transcode nodes, platform roadmap |
| `#plex-invites` | `1559236239729889351` | Text | Read-only | `plex_invites` | How to accept Plex invites and connect new client devices |
| `#maintenance` | `1559236247359324200` | Text | Read-only | `maintenance_schedule` | Daily 5:00 AM – 5:30 AM reboot and maintenance schedule |

### 📖 Category 2: GUIDES & SELF-SERVICE (`1559236252228648970`)
*Technical troubleshooting, Direct Play optimization, and reading device setup.*

| Channel Name | Channel ID | Type | Read / Write | Pinned Embed Key | Description & Topic |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `#plex-setup-guides` | `1559236253944123494` | Text | Read-only | `plex_setup_guides` | Direct Play configuration for Apple TV, Roku, Shield, LG/Samsung |
| `#transcode-doctor` | `1559236259283734688` | Text | Read-only | `transcode_doctor` | Buffering diagnosis, 30-second fix, audio transcode issues |
| `#kindle-and-audiobooks` | `1559236264832667698` | Text | Read-only | `kindle_audiobooks` | Send-to-Kindle approved senders guide, web reader instructions |

### 💬 Category 3: COMMUNITY CHAT (`1559236270956355615`)
*Interactive discussion channels for verified Members and Admins.*

| Channel Name | Channel ID | Type | Read / Write | Pinned Embed Key | Description & Topic |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `#general-chat` | `1559236272294338631` | Text | Member Chat | — | Homelab banter, casual community chat, and updates |
| `#movie-and-tv-talk` | `1559236273368080394` | Text | Member Chat | — | Spoiler-free movie/show discussions and recommendations |
| `#book-nook` | `1559236274769100912` | Text | Member Chat | — | Reading club, audiobook discoveries, author recommendations |
| `#polls-and-feedback` | `1559236276060815482` | Text | Member Chat | — | Community voting for upcoming 4K remasters & library polls |

### 🎬 Category 4: REQUESTS & MEDIA (`1559236276761133086`)
*Real-time media notifications, requests feed, and retention warnings.*

| Channel Name | Channel ID | Type | Read / Write | Pinned Embed Key | Description & Topic |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `#media-requests` | `1559236277889671218` | Text | Read-only Feed | — | Automated Overseerr/Seerr media request status updates |
| `#recently-added` | `1559236278791442472` | Text | Read-only Feed | — | Newly ingested movies, episodes, audiobooks, and books |
| `#leaving-soon` | `1559236280028504094` | Text | Read-only Feed | — | Maintainerr pruning warnings: 14-day watch grace period |

### 🆘 Category 5: HELP & TICKETS (`1559236284961132686`)
*Live health telemetry, outage alerts, and user support channels.*

| Channel Name | Channel ID | Type | Read / Write | Pinned Embed Key | Description & Topic |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `#support-tickets` | `1559236286638981140` | Text | Member Chat | `support_guide` | Open tickets, report playback issues or website page bugs |
| `#server-uptime` | `1559236291894182042` | Text | Read-only | `system_status` | **Live Status Cockpit**: Host health, reachability, outage alerts |

### 🤖 Category 6: BOT & AUTOMATION (`1559236297673941053`)
*Admin-only technical audit logs, automation triggers, and container diagnostics.*

| Channel Name | Channel ID | Type | Read / Write | Description & Topic |
| :--- | :---: | :---: | :---: | :--- |
| `#main-server-feed` | `1559236300454887485` | Text | Admin Only | Radarr/Sonarr grab alerts and import logs for Main Plex |
| `#kid-server-feed` | `1559236302178877522` | Text | Admin Only | Radarr/Sonarr grab alerts and import logs for Kids Plex |
| `#host-health-glances`| `1559236305500774561` | Text | Admin Only | CPU spikes, RAM capacity warnings, disk temperature alerts |
| `#deletion-audit` | `1559236308524732498` | Text | Admin Only | Maintainerr cleanup logs, disk space reclaimed summaries |
| `#bot-commands` | `1559236309787091075` | Text | Admin Only | Diagnostic bot slash commands, manual sync triggers |
| `#domshomelab-logs` | `1559236311494295602` | Text | Admin Only | Automated sync logs, request dispatch audit, and alert telemetry |

### 🔒 Category 7: STAFF & VAULT (`1559236312207327283`)
*Strictly private administrator lounge and storage ledger.*

| Channel Name | Channel ID | Type | Read / Write | Description & Topic |
| :--- | :---: | :---: | :---: | :--- |
| `#staff-lounge` | `1559236313658695760` | Text | Admin Only | Private operator discussions, user management, and security notes |

### ✅ Clean Channel Topology
*All 4 orphaned default channels generated by Discord have been deleted:*
- Deleted: `#general` (`1559231517773799477`) & default `Text Channels` category
- Deleted: `#General` voice (`1559231517773799478`) & default `Voice Channels` category
- Current Channel Count: 26 active channels organized strictly under the 7 canonical categories.

---

## 4. Website-to-Discord Parity Audit & Strategic Recommendations

To ensure the Discord server seamlessly reflects all active features of the **DomsHomeLab (`v1.1.0`) Web Portal**, the following strategic enhancements should be tested and validated here before rolling them out to the production server:

### 1. 24/7 AI Server Assistant Integration (`#transcode-doctor` & `#support-tickets`)
- **Website Capability**: Portalarr features an autonomous AI Server Assistant accessible 24/7 with zero waiting time. It diagnoses buffering, quiet dialogue, forced subtitle burns, 4K unlocks, and provides personalized book/movie recommendations.
- **Discord Action**:
  - Update the pinned embed in `#transcode-doctor` with a prominent section:  
    > **🤖 Need Instant Diagnosis?** Open the **24/7 AI Assistant** directly on your [DomsHomeLab Dashboard](https://domshomelab.org). It runs live stream telemetry on your active session to pinpoint bandwidth constraints, transcode audio throttles, and client container mismatches in under 5 seconds!

### 2. "Suggest a Fix / Report Page Issue" Feature (`#support-tickets` & `#polls-and-feedback`)
- **Website Capability**: Every website page now features a floating **"Suggest a Fix"** action button available to all authenticated Members. It automatically captures route parameters, device telemetry, and DOM context.
- **Discord Action**:
  - In `#support-tickets`, instruct members that if they encounter a visual glitch, missing metadata, or broken link on the web portal, using the **"Suggest a Fix"** button on the page routes the diagnostic ticket directly to the administrator's dashboard with zero back-and-forth questioning required.

### 3. My Plex Hub & Stream Quality Doctor (`#plex-setup-guides`)
- **Website Capability**: The `/profile` (My Plex Hub) page offers an integrated speed test measuring real HTTPS throughput from PMS directly to the user's browser, along with device-specific Direct Play checklists.
- **Discord Action**:
  - Update `#plex-setup-guides` to link members to their personal **My Plex Hub** dashboard to test their connection speed directly against the server, verifying if they have the 25+ Mbps throughput needed for uncompressed 4K HDR playback.

### 4. Digital Bookshelf, Comic Reader & Send-to-Kindle (`#kindle-and-audiobooks` & `#book-nook`)
- **Website Capability**: The platform features a full-featured ePub web reader, integrated audiobook player, and 1-click **Send-to-Kindle** with automatic Amazon approved sender verification and delivery tracking.
- **Discord Action**:
  - Update the pinned guide in `#kindle-and-audiobooks` with step-by-step instructions:
    1. Add `kindle@domshomelab.com` to your Amazon Approved Personal Document E-mail List.
    2. Enter your `@kindle.com` address in [Account Settings → Profile](https://domshomelab.org/profile).
    3. Click **Send to Kindle** on any book in the library for instantaneous Wi-Fi sync.

### 5. Maintainerr Retention Radar & 14-Day Grace Period (`#leaving-soon`)
- **Website Capability**: The Leaving Soon engine flags low-demand media items to protect NVMe/ZFS pool capacity. When any household member streams a flagged item on Plex, the watch activity is immediately detected, clearing the deletion flag and resetting retention for 180 days.
- **Discord Action**:
  - Highlight in `#leaving-soon`:  
    > **💡 Want to save a title from deletion?** Simply press play on Plex! Watching any flagged movie or episode for 5 minutes automatically removes it from the pruning queue.

### 6. Dynamic System Status & Outage Cockpit (`#server-uptime`)
- **Website Capability**: Portalarr has dual-branch build telemetry (`main` Beta vs `stable` Production), live Docker fleet probing, and a scheduled daily maintenance window from 5:00 AM – 5:30 AM.
- **Discord Action**:
  - The live status embed in `#server-uptime` automatically displays hardware vitals, active streams, container statuses, and maintenance alerts. The automated webhook/bot outage dispatcher immediately alerts this channel if PMS or Seerr becomes unreachable.

### 7. Strict Privacy & Zero Commercial Terms Enforcement
- **Website Capability**: DomsHomeLab operates strictly under private homelab sharing guidelines with zero public pricing, subscription marketing, or payment tier advertising.
- **Discord Action**:
  - Ensure `#welcome-and-rules` and `#membership-info` never use words like "cost", "subscription fee", or "tier pricing". Only refer to "Household Sharing", "Member Access", and "Direct Play Onboarding".

---

## 5. Test Server Execution Checklist

- [x] Verify bot credentials and Discord Guild ID (`1559231517325135892`) in database.
- [x] Run `updateDiscordStatusEmbedAction()` to confirm `#server-uptime` live cockpit renders cleanly.
- [x] Post test messages via `postDiscordTestMessageAction()`.
- [x] Verify channel permission overwrites: `@everyone` cannot send messages in read-only guide channels.
- [x] Delete orphaned default channels (`#general`, `#General` voice, `Text Channels`, and `Voice Channels`).
- [x] Provision `#announcements` (`1562546144289095821`) under `📌 1. WELCOME & INFO`.
- [x] Stage and synchronize upgraded parity embeds in `#transcode-doctor`, `#support-tickets`, `#plex-setup-guides`, `#kindle-and-audiobooks`, and `#leaving-soon`.
- [x] Verify live status embed in `#server-uptime` (`1559236291894182042`) updated in-place with real-time telemetry.
