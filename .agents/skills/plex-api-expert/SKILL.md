---
name: plex-api-expert
description: Expert architectural and API specification guide for Plex Media Server (PMS REST API, token authentication, library sections, metadata schemas, tag/label manipulation, custom collection hubs, photo transcoding, and stream session diagnostics). Activate when integrating with Plex, calling Plex endpoints, diagnosing playback sessions, managing collections and labels, or referencing openapi.json.
---

# Plex Media Server (PMS) API Expert Guide

Plex Media Server (PMS) provides an extensive HTTP REST API for media cataloging, metadata extraction, user management, library scanning, stream transcoding, home screen hub recommendations, and playback session telemetry.

Primary Reference Files & OpenAPI:
- OpenAPI 3.1 Specification: [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/openapi.json)
- Portalarr Plex Engine: [src/app/actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/actions.ts)
- Portalarr Curation Actions: [src/app/curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)

---

## API Architecture & Key Concepts

- **Authentication**: Token-based via `X-Plex-Token` HTTP header or `?X-Plex-Token=` query parameter.
- **Client Identification**: Mandatory `X-Plex-Client-Identifier` and `X-Plex-Product` headers.
- **Data Formats**: PMS defaults to XML; clients should explicitly supply `Accept: application/json` for JSON payloads.
- **Relative Path Resolution**: PMS API responses return relative `key` attributes that resolve against `/library/sections/` or root endpoints.
- **Multi-Server Candidate URLs Resolution**: To maintain 100% reliable connectivity across LAN, remote direct, and Plex Relay, clients should resolve all candidate URLs via `https://plex.tv/api/v2/resources` and test reachability with fastest-path failover.
- **Type Identifiers**:
  - `1`: `movie`
  - `2`: `show`
  - `3`: `season`
  - `4`: `episode`
  - `8`: `artist`
  - `9`: `album`
  - `10`: `track`
  - `15`: `playlist`
  - `18`: `collection`

---

## Core Capabilities & Runbooks

### 1. Server Endpoints & Telemetry
- **Identity & Capabilities**: `GET /identity`, `GET /myplex/account`.
- **Sections & Items**: `GET /library/sections`, `GET /library/sections/{id}/all`.
- **Stream Telemetry**: `GET /status/sessions`, `DELETE /status/sessions/{id}?reason=...`.
- **Image Transcoder**: `GET /photo/:/transcode?width=600&height=900&url=...`.

See detailed runbook: [pms-endpoints-reference.md](./references/pms-endpoints-reference.md).

### 2. Tags, Collections & Home Screen Hubs
- **Tag / Label Updates**: `PUT /library/metadata/{ratingKey}?label[0].tag.tag=...`.
- **Clear Labels**: `PUT /library/metadata/{ratingKey}?label[0].tag.tag-=`.
- **Collections**: `POST /library/collections`, batch add via `POST /library/collections/{id}/items?uri=server://...`.
- **Smart Collections**: `POST /library/collections?type={type}&title={title}&smart=1&uri={filterUri}`.
- **Personalized Recommendations**: `PUT /library/metadata/{ratingKey}/prefs?collectionFilterBasedOnUser=1`.
- **Hub Visibility**: Initialize via `POST /hubs/sections/{id}/manage?metadataItemId={id}`, then toggle `promotedToOwnHome`, `promotedToSharedHome`, `promotedToRecommended`.

See detailed runbook: [tags-collections-and-hubs.md](./references/tags-collections-and-hubs.md).

---

## Common Gotchas & Best Practices

1. **Tag Clearing Syntax**:
   - Omitting `label[0].tag.tag-=` when clearing all labels will leave existing tags intact in PMS. Always send `label[0].tag.tag-=` when emptying tag arrays.
2. **Locking Custom Metadata**:
   - Any manual edit made via `PUT /library/metadata/{ratingKey}` should include `<fieldName>.locked=1` (e.g. `title.locked=1`, `titleSort.locked=1`). Otherwise, the next automated library metadata refresh will overwrite the modification with agent data.
3. **Smart vs Static Collections**:
   - Never call `/move` or item manipulation endpoints on a collection created with `smart=1`. Smart collections are dynamically populated by Plex search filters.
4. **Portrait Poster Dimensions**:
   - Always request 2:3 vertical poster proportions (`width=600&height=900`) on `/photo/:/transcode` to prevent PMS from cropping portrait artwork to landscape dimensions.
5. **Session Stream Termination Fallback**:
   - When terminating active playback streams, verify user alias permissions and fall back from Tautulli to Direct PMS `DELETE /status/sessions/{sessionId}` if Tautulli is unavailable.
6. **Fast Collection Deletion via PMS Cascade**:
   - Deleting a collection via `DELETE /library/metadata/{ratingKey}` automatically unlinks all media items in Plex in ~10ms. Avoid pre-fetching and untagging items individually, as this triggers severe latency and Server Action timeouts.
7. **Hub Reordering & Visibility Timeouts**:
   - Use `PUT /hubs/sections/{sectionKey}/manage/{hubId}/move?after={afterHubId}` combined with locked `titleSort` prefixes to reorder hubs. Dispatch hub visibility updates concurrently (`Promise.all`) using 4s timeout guards (`AbortSignal.timeout(4000)`) to ensure Server Action resilience.
8. **Large Section Responses & Next.js Data Cache Limit**:
   - Large library endpoints (`/library/sections/{id}/all?includeGuids=1`) frequently exceed Next.js 2MB data cache limit (`WARN: items over 2MB can not be cached`). Direct server calls must bypass Next.js automatic fetch caching by supplying `{ cache: 'no-store' }`.
9. **Identifying Trailer Placeholders vs Real Media**:
   - Agregarr trailer placeholders share identical `Guid` (TMDb / IMDb) values with real movies. Distinguish them by checking `editionTitle === "Trailer"` or searching `metadata.Label` for `trailer-placeholder`. Availability indexes must exclude placeholders so upcoming movies are not falsely marked as "In Library".
10. **Strict Friend & Share Matching Integrity**:
    - When mapping local users to Plex friends/shares via `/api/users` or `https://plex.tv/api/v2/friends`, NEVER use partial substring containment (e.g. `ta.includes(sa)` or `sa.startsWith(ta)`). Partial substring matching causes disastrous cross-user share collisions (e.g. `userprimary` falsely matching `primary` or `mjprimary`). Strictly compare exact numeric Plex user IDs, exact emails, exact usernames, normalized alphanumeric characters (`username.replace(/[^a-z0-9]/gi, '')`), or exact email prefix identifiers (`email.split('@')[0]`).
11. **Connection Reachability & Byte-Range Playback Probing**:
    - When searching items or probing media across multiple PMS servers/candidate URLs, avoid sequential hanging on unresponsive URLs. Probe connection responsiveness with a fast 1,500ms `/identity` check first.
    - To verify disk read health without downloading complete multi-gigabyte media parts, execute an active HTTP Range probe (`Range: bytes=0-65535`) against the part URL (`part.key`). A 206 Partial Content or 200 OK confirms physical storage availability and responsive disk I/O.
12. **Tagging Studio & Content Advisory Labels**:
    - **Label Destination vs Genre Destination**: Plex labels applied via `PUT /library/metadata/{ratingKey}?label[0].tag.tag=...&label.locked=1` integrate directly into Plex Home user sharing restrictions, allowing administrators to restrict Kids and Teen profiles from sensitive content (e.g. `IMDb: Nudity [Severe]`).
    - **Dual Endpoint Updating**: Always dispatch tag updates to both `PUT /library/metadata/{ratingKey}` and `PUT /library/sections/{sectionKey}/all?type={typeId}&id={ratingKey}` to maintain 100% compatibility across legacy and modern PMS versions.
    - **Pre-Filtering to Avoid Excessive HTTP Calls**: When clearing tags or applying custom rules across thousands of media items, inspect known stream/section tags (`item.labels`, `item.genres`, `item.collections`) before initiating individual `GET /library/metadata/{ratingKey}` requests. Items that already lack the tag should be skipped immediately to maintain sub-second execution speeds.
    - **Collection Untagging and Container Deletion**: When clearing custom collection tags from a library, untagging the items should be accompanied by `deletePlexCollection` to cleanly remove the collection container entity from PMS.
13. **Unraid Daily 5:00 AM – 5:30 AM Plex Container Maintenance Blackout**:
    - **Blackout Protocol (`isPlexMaintenanceWindow`)**: Unraid executes scheduled database integrity checks and restarts Plex containers daily from 5:00 AM to 5:30 AM. No background runner, automated scheduled task, or direct PMS polling (`getPlexActiveSessions`, `getPlexServerLibrarySections`, `runOverlayIncrementalSyncInternal`, `runOverlayRecheckSyncInternal`, `runAgregarrSyncInternal`, `runMaintainerrSyncInternal`, `runParentalTagsSyncInternal`, `syncPlexFriendsInternal`, `syncMediaRequestsQueueAndAvailabilityInternal`, `getPlexLibraryGuidIndex`) is permitted to hit Plex Media Server during 5:00:00 AM – 5:29:59 AM.
    - All schedules due at or during 5:00 AM automatically defer to 5:30:00 AM once the container restart concludes. Maintainerr's recommended default is `daily_6am`.
14. **Direct Poster Buffer Uploads & MIME Magic Byte Requirements**:
    - PMS `/library/metadata/{ratingKey}/posters` rejects binary uploads with `400 Bad Request` if the `Content-Type` header disagrees with the binary image structure.
    - Always determine the image format from magic bytes (`image/png` for `89 50 4E 47`, `image/jpeg` for `FF D8 FF`, `image/webp` for `RIFF...WEBP`) rather than defaulting strictly to `image/jpeg`.
    - Always lock the uploaded poster (`PUT /library/metadata/{ratingKey}?thumb.locked=1`) to prevent PMS scheduled maintenance from overwriting custom or restored artwork.
    - Use multi-candidate URL failover (`expandCandidateUrls`) to ensure direct LAN IP fallback (`http://192.168.1.X:32400`) if `.plex.direct` endpoints time out or encounter DNS rebind blocks.
15. **Native Stream Intelligence, Watch History & Multi-IP Password Sharing Detection**:
    - **Native Watch History Engine (`stream-tracker.ts`)**: Portalarr records active playback sessions directly from PMS `/status/sessions` without requiring external Tautulli. Records progress percentage (dynamically calculated from `viewOffset` / `duration` if omitted by PMS), duration, completed status (`progress >= 90%`), video/audio decisions, transcode HW acceleration, client platform/device, and remote IP addresses.
    - **Dynamic Date Range Filtering (`parseDateRange`)**: Stream intelligence and telemetry views support scoped historical analysis across `All Time`, `Last 30 Days` (`30d`), `Last 60 Days` (`60d`), `Last 90 Days` (`90d`), and `Custom Range` (`custom`). In `stream-tracker.ts`, `buildWatchHistoryConditions` dynamically injects parameterized SQL date clauses (`watchedAt >= ? AND watchedAt <= ?`) into raw SQLite queries.
    - **Full SQLite Database Aggregation Engine (Zero Truncation)**: Metric summary cards, user directory metrics, and library analytics compute true, un-truncated totals using fast raw SQLite aggregations (`COUNT(*)`, `SUM(durationMs)`, `SUM(directPlay)`, `SUM(transcode)`, `SUM(sharingAlerts)`). Eliminates legacy `take: 2000` / `take: 3000` truncations and resolves exact metrics ($< 500$ms on 28k+ records).
    - **User Playback Directory Sorting & Modal Range Toggle**: Administrators can sort users on-the-fly by plays, streaming hours, transcode rate, sharing alerts, or name. In the User Telemetry modal, administrators can seamlessly toggle between the active page date range and All Time to compare recent versus lifetime streaming habits.
    - **Password Sharing & Multi-IP Detection Heuristics (`analyzeActiveSessionsForSharing`)**: Detects simultaneous streaming sessions per user. Private/LAN IPs (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, `localhost`) are recognized as same-household playback and do NOT trigger sharing alerts. Multi-IP sharing is strictly flagged when a user streams concurrently from 2 or more distinct public IP addresses (indicating disparate households), recording `isSharingAlert: true`, incrementing `user.sharingAlertCount`, and alerting admins in real time on the Stream Matrix dashboard.
16. **Network Fetch Resilience & Next.js Streaming Pipeline Protection**:
    - **Never wrap operational PMS/Tautulli queries in `next: { revalidate: N }`**: In Next.js App Router Turbopack, wrapping dynamic server component or server action calls with Next.js data cache interceptors causes unreachable servers, dead Docker IP candidates, or aborted signals to throw unhandled `TypeError: fetch failed` during response piping, which crashes the stream with `Error: failed to pipe response`.
    - **Enforce `cache: "no-store"` & explicit `AbortSignal.timeout(...)`**: Always supply `{ cache: "no-store" }` and explicit timeout signals (e.g. `AbortSignal.timeout(5000)`) wrapped in `try/catch` blocks returning fallback structures (`null` or empty arrays) so failing endpoints fail gracefully without ever interrupting Next.js response piping.
17. **Local Machine Identifier URI Matching & Library URI Fallback (`LPE: only library URIs are allowed right now`)**:
    - **Plex Collection Single-Item URI Constraint**: Adding items to collections via `PUT /library/collections/{id}/items?uri=...` requires the URI to point to the local server's internal database (`server://{machineIdentifier}/com.plexapp.plugins.library/library/metadata/{ratingKey}`). If `{machineIdentifier}` does not match the receiving server, or if a cross-server URI is sent, PMS rejects it with `400 Bad Request` and logs `LPE: only library URIs are allowed right now. Failed to generate a query from uri server://...`.
    - **Strict Candidate Isolation**: In multi-server environments, `resolveWorkingPlexServerConnection` strictly purges candidate URLs returning mismatched `machineIdentifier` values so candidate lists never leak cross-server URLs. `syncPlexCollection` resolves `machineIdentifier` per candidate base URL (`baseMachineIdMap`), retries with `library:///item/%2Flibrary%2Fmetadata/{ratingKey}` upon HTTP 400 rejection, and falls back to item metadata tagging (`collection[0].tag.tag=...`) to ensure 100% item retention without PMS log errors.
18. **Multi-Library Candidate Probing & Self-Healing Stale Metadata Refreshes (`inspectMediaStreams`)**:
    - When inspecting media across libraries (e.g. 4K TV vs Standard TV sections) or multiple Plex Media Servers, never select the first search match naively. Stale or deleted files in one library can cause false 404 errors even when a playable file exists in another library.
    - Actively probe candidate items via byte-range requests (`probePlexPartStreaming` requesting `Range: bytes=0-65535`). If a candidate returns `HTTP 200` or `HTTP 206`, select it as the active stream.
    - If a candidate returns `HTTP 404`, trigger a non-blocking background metadata refresh (`PUT /library/metadata/{ratingKey}/refresh`) so Plex prunes the stale reference automatically, and continue searching remaining candidate items.
19. **PMS Transcode Session Target Resolution & Power Telemetry Extraction (`TranscodeSession` Attributes)**:
    - **Target Resolution Dimension Fallback**: In Plex Media Server `/status/sessions`, `TranscodeSession` provides target resolution via pixel `height` (e.g. 1080, 720, 480) and `width` (e.g. 1920, 1280) rather than a string `videoResolution` property. Naively querying `ts.videoResolution` causes target resolution to fall back to the source resolution (`s.Media[0].videoResolution` = 4k), concealing downscaled transcoding. `resolveResolution` maps height and width (handling cinemascope aspect ratios like 1920x800 for 1080p, 1280x534 for 720p) to clean display strings (`4K UHD`, `1080p`, `720p`, `480p`).
    - **HDR-to-SDR Tone Mapping Detection (`isToneMapping`)**: When source video contains HDR, HDR10, or Dolby Vision metadata and is transcoding video to SDR, or when `ts.transcodeHwToneMapping` is set, flag tone-mapping active so the UI displays `✨ HDR10 ➔ SDR Tone Mapped`.
    - **Multi-Edition & Transcode Media Selection (`s.Media` Array)**: When a library title has multiple files on disk (e.g. 4K UHD and 1080p), Plex creates a dedicated transcode `Media` item marked `selected: true` with active streams inside `Part[0].Stream`. Naively indexing `s.Media[0]` yields the wrong file. The active video stream's `displayTitle` (e.g. `"1080p (HEVC Main)"`) is PMS's canonical indicator of the actual source resolution and codec being fed into the transcoder.
    - **Transcode Speed & Buffer Throttle (`speed` & `throttled`)**: `speed` represents the transcode speed multiplier relative to real-time playback ($\ge 1.0x$ is healthy; $< 1.0x$ indicates buffering risk when unthrottled). When `throttled: true` (or when lead buffer is $\ge 10s$), Plex intentionally pauses transcoding because the playback buffer is satisfied, dropping CPU/GPU power draw to 0% idle and transcode speed to `0.0x`. This state is classified as healthy (`transcodeSpeedHealthy: true`) and rendered with an emerald badge `⚡ 0.0x speed (Throttled • Power Saving)`, never as a red error. The lead buffer duration is calculated via `maxOffsetAvailable - viewOffset`.
20. **Direct SQLite Snapshot & Delta-Sync Engine (`plex-snapshot-engine.ts`)**:
    - **Plex Crash Prevention via Hot Snapshots**: High-frequency HTTP polling and bulk library sweeps (parental tags, Kometa overlays, smart collections, and prune candidate evaluations) overload PMS's internal SQLite database, triggering database locks and daemon crashes. Portalarr decouples operational analysis from the live PMS process by taking detached local SQLite snapshots.
    - **Hot Backup Fallback Strategy**:
      1. Attempts atomic `sqlite3 "$src" ".backup '$dst'"` via shell.
      2. If shell `sqlite3` is unavailable, executes hot file copy (`.db`, `.db-wal`) and performs WAL checkpoint truncation (`PRAGMA wal_checkpoint(TRUNCATE)`) using native Node 22+ `node:sqlite` (`DatabaseSync`), with fallback to `sqlite3` CLI. Container runs on `node:22-bookworm-slim` with both `sqlite3` and native `node:sqlite`.
    - **Tag Audit Delta-Sync**: `getSnapshotLibraryTagsAudit(dbPath, sectionKey)` extracts all existing tags, genres, and collections indexed by `ratingKey` in <5ms. During parental tagging sweeps (`applyParentalTagsToLibrary`), items whose target tags match the snapshot are skipped with zero HTTP GET or PUT calls. If changes are needed, target tags are updated via paced PUT requests without redundant metadata GET fetches.
    - **Direct Media Items & Stream Badges**: `getSnapshotLibraryMediaItems(dbPath, sectionKey)` queries media parts, video/audio codecs, bitrates, resolutions, and stream attributes directly from SQLite tables (`metadata_items`, `media_items`, `media_parts`, `media_streams`), completely eliminating heavy `/all?includeStreams=1` HTTP queries.
    - **Safe Multi-Server Cross-Server Views**: Using `ATTACH DATABASE`, secondary server databases are cross-queried in <20ms for watch history synchronization without hitting secondary server HTTP APIs.
21. **Multi-Tier Leaving Soon Watch Status Engine & PMS Overload Protection (`recheckLeavingSoonWatchActivityInternal`)**:
    - **PMS Lock Avoidance on Watch Verification**: Validating whether staged or expiring items have been watched by users typically creates severe PMS CPU and SQLite bottlenecks when looping over `/library/metadata/{ratingKey}` endpoints.
    - **Tiered Verification Architecture**:
      - **Tier 1 (Instant Local Cache)**: Instantaneous `<1ms` lookup against local SQLite `WatchHistory` resolving watched status with ZERO network calls to PMS.
      - **Tier 2 (Batch History Inspection)**: Single batch query against `/status/sessions/history/all?sort=viewedAt:desc&X-Plex-Container-Start=0&X-Plex-Container-Size=500` fetching up to 500 recent sessions with episode `parentRatingKey` and series `grandparentRatingKey` mapping in 1 HTTP call.
      - **Tier 3 (Throttled Circuit-Breaker Fallback)**: Capped at 10 items with 100ms pauses between calls, immediately aborting upon 2 consecutive errors.
    - **In-Memory Debounce**: Protected by a 60-second per-server in-memory debounce guard (`lastWatchCheckByServer`) to suppress redundant invocations from rapid callers.






22. **My Plex Hub Watch Statistics & Session Resolution Architecture**:
    - **User Identity Matching**: Expands `userAliases` to include `username`, `email`, `name`, `plexUsername`, and `plexEmail` queried from `prisma.user`, matching against active Plex sessions and Tautulli user tables.
    - **Multi-Server Token Decryption Fallback**: Decrypts server-specific tokens in `prisma.plexServer` (`dbPlexServers`) if `settings.mainPlexToken` is unset, ensuring `getPlexOwnerUser` and friend lookups always succeed.
    - **Tautulli User Matching & Python Falsy `0` Fix**: Implements two-pass user matching (alias match first, then admin fallback). Avoids Python `user_id = 0` falsy drops by resolving to `user=${username}` for Plex server owner accounts.
    - **Direct Plex Media Server History Scan**: Accumulates watch time (ms) and counts across all discovered PMS instances without loop-scoped cutoff bugs.
    - **Local SQLite `WatchHistory` Fallback**: If Tautulli is offline or unconfigured, queries Prisma `WatchHistory` using exact and lowercased alias arrays (avoiding SQLite `mode: "insensitive"` crashes) to accurately aggregate watch hours, movies finished, and episodes watched.

24. **Plex Home Live TV & DVR Privilege Auditor & Policy Management (`plex-jellyfin-livetv.ts`)**:
    - **15-User Plex Home Limit**: Plex caps Plex Home at 15 users (1 admin owner + 14 member slots). Only Plex Home members can be granted Live TV / DVR tuner access (`allowTuners="1" | "2"`, `allowChannels="1"`). Regular Plex friends cannot access Live TV tuners unless admitted into the Plex Home.
    - **The 3 Plex Restrictions Radio States & Cloud API Integer Enum**:
      - In Plex Media Server under **Restrictions > Live TV & DVR Access**, Plex enforces three distinct states represented as an **integer enum** in `allowTuners`:
        1. `No Live TV and DVR access` (`allowTuners="0"`, `allowDvr="0"`): User has neither live tuner nor recording privileges (e.g. `krismo4`, `Zestyandstizy`).
        2. `Allow Live TV only` (`allowTuners="1"`, `allowDvr="0"`): User can stream live channels, but cannot view scheduled recordings or schedule DVR recordings.
        3. `Allow Live TV and DVR access` (`allowTuners="2"` or `allowTuners="1"` with `allowDvr="1"`): User can both stream live channels and schedule/manage their own recordings (e.g. `jrj78`, `trevscar1121`).
      - Crucially, in `https://plex.tv/api/users` XML, Plex outputs `allowTuners="2"` for members with Live TV and DVR access rather than a separate `allowDvr="1"` tag. Parsers MUST check `tunersInt === 2` to recognize Tier 3 status.
    - **Multi-Server Shared Server Verification**:
      - All discovered Plex Media Servers (cloud resources and database records in `prisma.plexServer`) must be queried when auditing shares and privileges.
      - `getPlexSharedServersList` queries `https://plex.tv/api/servers/${encodeURIComponent(srvId)}/shared_servers` across every server in the cluster (`KidsPlexServer`, `MainPlexServer`, `MainPlexServerBackup`, etc.) using server-specific tokens (`srv.accessToken || adminToken`), ensuring no server in the cluster is skipped.
    - **Plex Home Discovery & Decoupled Audit**: Inspects `GET https://plex.tv/api/users` (XML) and `GET https://plex.tv/api/v2/home/users` (JSON). Audits `allowTuners` and `allowDvr` independently without assuming that tuner access automatically implies DVR access. When `allowTuners` is true (e.g. `jrj78`, `trevscar1121`), `dvrGranted` is preserved from `item.allowDvr || matchedPortalUser?.hasPlexDvrAccess`, guaranteeing members with "Allow Live TV and DVR access" in Plex Web correctly render as Tier 3 (`Live TV + DVR`). If `allowTuners` is false (e.g. `krismo4`), `dvrGranted` is strictly false (Tier 1).
    - **`allowChannels` vs `allowTuners` Separation**: `allowChannels` on PMS shared servers refers to legacy online plugins/channels (e.g. YouTube, Vimeo) and is enabled by default. It MUST NOT be used to grant Live TV. Live TV is strictly governed by `allowTuners`.
    - **Live Plex API Authoritative Precedence**: When Plex is reachable (`plexReachable === true`), the live values from Plex API are authoritative. Never OR cached SQLite values (`matchedPortalUser?.hasPlexLiveTvAccess`) into live state, which would prevent Plex restrictions from syncing down when revoked in Plex Web.
    - **Hierarchical Privilege Transitions**:
      - *Grant Live TV*: Calls `/api/friends/{uid}?allowTuners=1` and updates server shares; sets `hasPlexLiveTvAccess: true` while preserving existing DVR state.
      - *Revoke Live TV*: Revokes both tuner and DVR access (`allowTuners=0`, `allowDvr=0`), dropping the user to `No Live TV and DVR access`.
      - *Grant DVR*: Automatically enables tuners if disabled (`allowDvr=1&allowTuners=2`), upgrading the user to `Allow Live TV and DVR access`.
      - *Revoke DVR*: Revokes only DVR (`allowDvr=0&allowTuners=1`), gracefully dropping the user down to `Allow Live TV only`.
    - **Inactivity Rotation Engine**: Evaluates `lastIptvWatchedAt` and `plexHomeJoinedAt` against `plexHomeInactivityDays` (default: 21 days). Strictly non-destructive: `plexHomeAutoKickEnabled` is strictly `false` by default, surfacing candidates for admin review without kicking anyone out unexpectedly.
    - **Jellyfin Live TV Policy Management**: Audits and controls `EnableLiveTvAccess` in Jellyfin via `POST /Users/{id}/Policy`. Always reads existing policies first and merges changes (`{ ...currentPolicy, EnableLiveTvAccess: true, EnableLiveTvManagement: false }`) to preserve library folder access permissions (`EnabledFolders`).

25. **Multi-Server Token Decryption Fallback, Debounced Probing & Quiet Logging**:
    - **Token Decryption Fallback**: `resolveActivePlexAdminToken` inspects `prisma.settings.mainPlexToken` and decrypts server-specific tokens in `prisma.plexServer` (`dbPlexServers`), ensuring owner account discovery and friends lookups always succeed even if the primary cloud token is unconfigured.
    - **Debounced Probes & Quiet Logging**: Plex connection resolutions enforce 3.5s timeouts per probe and debounce network probes across repetitive callers, silencing spammy `connect ECONNREFUSED` or timeout warnings in development and testing.
    - **Tautulli Python Falsy `0` Fix**: In `getUserPlexHubData`, resolving Tautulli user history uses `user=${username}` for Plex server owner accounts to prevent Python `user_id = 0` falsy drops from blanking watch statistics.
    - **Direct PMS Session History Scan**: Accumulates watch hours across discovered PMS instances via `/status/sessions/history/all?sort=viewedAt:desc` without loop-scoped cutoff bugs.
    - **Local SQLite `WatchHistory` Fallback**: If Tautulli is offline, queries Prisma `WatchHistory` using exact and lowercased alias arrays (avoiding SQLite `mode: "insensitive"` crashes) to accurately aggregate watch hours, movies finished, and episodes watched.

26. **Strict Plex Authentication & Admin Immunity Safeguards (`handlePlexCallback`)**:
    - **Arbitrary Plex Resources Privilege Escalation Elimination**: Never query arbitrary Plex account resources (`/api/v2/resources`) to infer administrative privileges. Owning an arbitrary personal Plex Media Server (e.g. on a laptop, desktop, or test machine) MUST NEVER grant homelab administrator status or overwrite `settings.mainPlexToken`.
    - **Immutable User Roles During Plex Login**: Existing user roles in `prisma.user` are strictly immutable during Plex login. Login callbacks must never alter `user.role` (`updateData.role` is strictly prohibited).
    - **Auto-Provisioned User Defaults**: All auto-provisioned new users created via Plex login are strictly assigned `role: "USER"`, except during initial system setup when 0 administrators exist in the database.
    - **Plex Admin Token Protection**: Global `settings.mainPlexToken` can only be updated/refreshed by verified existing `ADMIN` users who own a configured homelab server in `prisma.plexServer` or match the existing token owner identity. Regular users can never touch or overwrite `mainPlexToken`.

---

## 🚨 Mandatory Task Completion Protocol (Strict SemVer)

To guarantee 100% reliability, quality control, and consistency, the following 5-step protocol MUST be executed at the end of every task or feature change before considering the work complete:

0. **Step 0: Read Skill Upfront**: Call `read_file` on the relevant `SKILL.md` before writing code.
1. **Step 1: Integration Testing**: Execute `cmd /c "npm test"` to run the verification suite (`scripts/verify-all.ts`). All test suites must pass (0 failures).
2. **Step 2: Production Build Verification**: Execute `cmd /c "npm run build"`. Ensure 100% clean compilation, zero TypeScript errors, and zero Turbopack runtime errors.
3. **Step 3: Edge Security & Cloudflare Policy Audit**: Whenever ANY page route (`src/app/**/page.tsx`) or API route (`src/app/api/**/route.ts`) is created, moved, or updated, register it in `src/lib/edge-policy-paths.ts` and inform the user.
4. **Step 4: Skills & Documentation Sync**: Review and update relevant `.agents/skills/` documents to record any new UI patterns, API contracts, formulas, or operational guidelines **BEFORE** committing.
5. **Step 5: SemVer Version Increment & Git Deployment Push**: Increment version in `package.json` according to SemVer (PATCH `+1` for fixes/polish, MINOR `+1` for features), stage all changes (`git add -A`), commit with freshly incremented semantic version prefix (`[v<version>] feat/fix(scope): message`), push strictly to `origin/main` (Beta). NEVER push to `stable` unless the user explicitly instructs.
