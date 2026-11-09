---
name: maintainerr-expert
description: Expert architectural and operational guide for Maintainerr and Portalarr Prune Engine (media library pruning, rule engine, "Leaving Soon" staging, Servarr unmonitoring/deletion, poster countdown overlays, and storage reclamation). Activate when designing or troubleshooting retention rules, complex boolean conditions, Leaving Soon grace periods, poster countdown banners, or Radarr/Sonarr file cleanup.
---

# Maintainerr & Prune Engine Expert Guide

Maintainerr and Portalarr's Storage Prune Engine automate disk space reclamation and media lifecycle management. They monitor Plex, Jellyfin, and Emby servers alongside Radarr, Sonarr, Tautulli, and Overseerr to identify low-engagement or surplus media based on custom nested rule sets, stage candidate files into "Leaving Soon" collections with dynamic countdown artwork, and execute automated prune actions.

Primary Reference Repositories & Modules:
- Directory: [Maintainerr-development](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development)
- Architecture Overview: [ARCHITECTURE.md](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development/ARCHITECTURE.md)
- Server Source: [apps/server/src/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development/apps/server/src)
- Portalarr Prune Actions: [src/app/curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)
- Portalarr Leaving Soon API: [src/app/api/curation/leaving-soon/route.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/api/curation/leaving-soon/route.ts)

---

## Monorepo Architecture

```text
Maintainerr-development/
├── apps/
│   ├── server/                      # NestJS backend (API, cron jobs, DB, integrations)
│   │   └── src/modules/
│   │       ├── rules/               # Rule evaluation engine, operators, entity repositories
│   │       ├── collections/         # "Leaving Soon" collection handlers & staging lifecycle
│   │       ├── actions/             # Radarr/Sonarr deletion, unmonitoring, leftover cleanup
│   │       ├── overlays/            # node-canvas / sharp countdown poster rendering
│   │       └── api/media-server/    # Server-agnostic adapters (Plex, Jellyfin, Emby)
│   └── ui/                          # Vite + React + TanStack Query + TailwindCSS UI
└── packages/
    └── contracts/                   # Shared types, Zod schemas, rule & action enums
```

---

## Core Capabilities & Runbooks

### 1. Complex Boolean Rule Engine
Evaluates hierarchical rules combining conditions from Plex, Radarr, Sonarr, Seerr, and Tautulli:
- **Condition Operators**: `BIGGER`, `SMALLER`, `EQUALS`, `CONTAINS`, `BEFORE`, `AFTER`, `IN_LAST`, `IN_NEXT`.
- **User Scoping**: Evaluates watch history per specific user (`viewCountByUser`, `watchTimeByUser`) or globally.
- **Disk Triggers**: Triggers cleanups when free disk space falls below a specified gigabyte threshold (`diskspace_remaining_gb`).

See detailed runbook: [rules-and-operators.md](./references/rules-and-operators.md).

### 2. "Leaving Soon" Staging, Banners & Prune Actions
Provides a safe grace period before permanent deletion:
- **Staging Collection**: Creates a visible Plex/Jellyfin collection highlighting expiring items.
- **Dynamic Poster Overlays**: Renders "Leaving in X Days" or target deletion dates onto posters using `sharp` / canvas.
- **Prune Execution**: Executes configured `ServarrAction` (Delete file, Unmonitor, Remove series if empty, Downgrade profile).
- **Client Sweeper**: Deletes associated torrents/NZBs from qBittorrent/Transmission/SABnzbd, clears Seerr requests, and cleans empty folders without `EACCES` file locks.

See detailed runbook: [leaving-soon-and-actions.md](./references/leaving-soon-and-actions.md).

---

## Common Gotchas & Troubleshooting

1. **"Leaving Soon" Banner Not Showing Text**:
   - Cause: The text variable (`field: 'daysLeft'` or `field: 'date'`) evaluates against `TemplateRenderContext`. If `deleteAfterDays` is 0, null, or outside safe bounds (`DELETE_AFTER_MAX_DAYS = 36500`), `deleteDate` becomes `null`, rendering an empty background pill.
   - Fix: Ensure the collection rule defines a positive integer for `deleteAfterDays` (e.g. `14`), and verify date arithmetic produces a valid timestamp.
2. **Accidental Mass Deletion Protection**:
   - Always provide dry-run / candidate preview modes before executing disk prune actions.
3. **File Lock Collisions (`EACCES`)**:
   - When deleting media that is actively seeding or downloading, delegate torrent/NZB deletion to the client API first before attempting filesystem unlinks.
4. **Oldest Files Discovery & Rule Sandbox Grid Overlaps**:
   - Cause: Using `lg:grid-cols-6` without intermediate breakpoints or `min-w-0` on container cards causes text-heavy `<SelectValue>` text (e.g. `⚡ Dual-Lane Cascade (Never Watched → Oldest Watched)`) to expand beyond column widths and overlap adjacent dropdowns.
   - Rule: Use `grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3`, ensure all cells have `min-w-0`, and add `w-full min-w-0 truncate [&>span]:truncate [&>span]:block` to all `SelectTrigger` and `SelectValue` elements.
5. **"Date Added" Pre-dating Server Setup (Preserved Release Timestamps & Plex addedAt Behavior)**:
   - Cause: Plex Media Server's `addedAt` timestamp frequently derives from physical file creation dates (`mtime` / `ctime`) preserved by torrent downloaders, Usenet NZB clients, or archive extractions (e.g. 2012, 2016, 2018). When Plex scans these files, it inserts the release file's original timestamp into `metadata_items.added_at`, making newly downloaded legacy content appear as though it was added years before the server existed. Furthermore, TV show seasons often inherit the show's or earliest episode's date.
   - Solution: The Prune Engine extracts both `addedAt` and `updatedAt` (when the file/metadata was last touched/refreshed on the current server), renders `• Mod: {updatedDateStr}` in the telemetry grid, and provides the **'Oldest Modified on Disk'** sort strategy (`sortBy: 'oldest_modified'`) to evaluate media against the actual timeframe it has resided on the current server.
6. **Watch Revocation Loop on Oldest Watched (Lane 1)**:
   - Cause: Checking `currentViewCount > 0` without verifying playback recency caused items staged under Lane 1 (Oldest Watched) to unflag themselves immediately upon staging, creating an endless flapping loop.
   - Fix: Require `lastViewedAt >= (flaggedAt - 86400000)` so that only plays occurring during the active grace period rescue media items.
7. **Sonarr TV Season Pruning Nuking Whole Series**:
   - Cause: Truncating `- Season X` to the base show title and calling `DELETE /api/v3/series/{id}?deleteFiles=true` deleted the entire series and all seasons from Sonarr instead of just the expired season.
   - Fix: Inspect for season numbering; when present, query `/api/v3/episode?seriesId={id}&seasonNumber={seasonNum}`, delete the individual episode files via `/api/v3/episodefile/{id}`, unmonitor the season's episodes and season model, and never delete the parent series entity.
8. **Automated Scheduler Execution, Baseline Parity & Mutex Locks**:
   - In `prune-studio.tsx`, initialize `baselineSettings.curationSyncSchedule` with `settingsRes.pruneSyncSchedule || settingsRes.curationSyncSchedule || "daily_6am"` so that the dedicated prune schedule matches initial state and does not trigger false unsaved changes flags (`isScheduleDirty`).
   - Concurrency lock `(global as any).__PORTALARR_PRUNE_RUNNING` prevents background evaluations from colliding with manual admin triggers.
   - In `runMaintainerrSyncInternal`, `catch (e: any)` updates `pruneLastRunAt: new Date()` and `pruneLastRunStatus` with error telemetry to prevent 60-second crash loops and surface errors in the UI.
   - **Unraid Plex Container Maintenance Blackout (5:00 AM – 5:30 AM)**: Unraid runs database integrity checks and restarts Plex containers daily from 5:00 AM to 5:30 AM. Maintainerr's recommended schedule is `daily_6am` (6:00 AM). The universal helper `isPlexMaintenanceWindow(now)` strictly blocks all scheduled and manual Maintainerr pruning runs during 5:00:00 AM – 5:29:59 AM. Existing legacy schedules set to `daily_5am` automatically defer to 5:30:00 AM after maintenance concludes.
9. **Rule-Based Retention vs. Capacity-Triggered Pruning (`pruneTriggerMode`)**:
   - In standard Maintainerr, media lifecycle rules (such as unwatched media older than 90 days) run on schedule to stage items into 'Leaving Soon' with grace periods, independent of disk pressure.
   - Portalarr supports two evaluation trigger modes configured via `Settings.pruneTriggerMode`:
     1. `"always"` (Rule-Based Retention, standard default): Every scheduled run (`runMaintainerrSyncInternal`) and manual trigger (`runMaintainerrSyncAction`) evaluates enabled libraries against aging and watch rules, staging expiring media into the Leaving Soon Plex collection with dynamic countdown overlays.
     2. `"capacity"` (Capacity-Triggered): Candidate evaluation runs only when the selected Glances storage array reaches or exceeds the Warning threshold (e.g. ≥ 85% used). If Glances disk monitoring reports 0 disks or is unconfigured, it gracefully falls back to rule-based evaluation to prevent silent suppression.
   - Manual admin actions (`runMaintainerrSyncAction` or `forceEvaluate: true`) always evaluate candidate media regardless of disk headroom.
   - `syncLeavingSoonCollectionHubInternal` returns `evaluatedCount` and `newlyStagedCount`, enabling `runMaintainerrSyncInternal` to aggregate and report accurate `totalEvaluated` counts in execution logs and telemetry.
10. **File Size Tracking & Recoverable Storage Telemetry**:
   - `MediaContentAdvisory.fileSizeGb` persists the exact media file size (in gigabytes) for each item staged to Leaving Soon across auto-staging (`syncLeavingSoonCollectionHubInternal`), manual flagging (`markItemLeavingSoonAction`), and sandbox staging (`executePruneAction`).
   - Staged item retrieval (`getLeavingSoonItemsAction`) automatically enriches and backfills legacy or missing sizes on the fly via `getPlexSingleItemMetadata(serverUrl, token, ratingKey)` in parallel batches of 10 and commits them to SQLite.
   - Active Staged Media Items card in `prune-studio.tsx` calculates cumulative recoverable storage (`💾 X.X GB / TB Recoverable`), provides individual item file size badges (`💾 X.X GB`), explicit space savings annotations (`Saves X.X GB • Reason: ...`), and server badges (`KidsPlexServer`, `Main Server`) for immediate server isolation.
11. **Global vs. Single-Library Evaluation & Multi-Server Filter Pills**:
   - `prune-studio.tsx` provides clear separation between global and scoped evaluations:
     - `Run Global Prune Evaluation (All Servers)`: Calls `runMaintainerrSyncAction()` without target server or section arguments, running a cluster-wide sweep across all enabled libraries on all registered Plex instances.
     - `Evaluate Library #{selectedSectionKey}`: Calls `runMaintainerrSyncAction(selectedServerId, selectedSectionKey)` to evaluate strictly the single selected library section on the currently active server.
   - Staged media retrieval (`loadLeavingSoonItems`) retrieves items cluster-wide by default, allowing the Active Staged Media Items card to render interactive server filter pills (`All Servers (X)`, `KidsPlexServer (Y)`, `Main Server (Z)`) with per-server counts and reactive total recoverable space calculation.
12. **Bulk Staged Removal & Multi-Select Operations**:
   - The **Active Staged Media Items** card in `prune-studio.tsx` equips administrators with granular and mass lifecycle actions:
     - **Multi-Select Checkboxes**: Every staged row has an interactive toggle checkbox (`Square` / `CheckSquare`) keyed by `${serverId}:${ratingKey}` to prevent cross-server collision.
     - **Select All / Deselect All**: Master toggle button in the card header dynamically selects or deselects all currently displayed or filtered media items.
     - **Bulk Action Toolbar**: Automatically appears when one or more items are selected, displaying the selected count and aggregate recoverable space (e.g. `12 Selected • 💾 48.2 GB Recoverable`).
     - **Bulk Cancel Removal (`bulkUnmarkItemsLeavingSoonAction`)**: Unstages selected items from SQLite in batch (`isLeavingSoon: false`), restores backed-up original poster artwork in Plex, and syncs the Leaving Soon collection hub once per affected server.
     - **Bulk Permanent Delete (`executePruneAction(..., { forceLiveDelete: true })`)**: Immediately deletes selected files from disk, removes them from Plex, and unmonitors them in Servarr without waiting for the grace period.
     - **Cancel All Removal (`clearAllLeavingSoonFlagsAction`)**: 1-click header action allowing administrators to unstage and restore original artwork across an entire server or the entire multi-server cluster with confirmation safeguards.
13. **Target Reclamation Headroom Quota Capping (`pruneTargetHeadroomGb`) & Seamless Auto-Save**:
   - **Universal Quota Enforcement**: Regardless of whether evaluation is triggered by schedule, capacity threshold, or manual admin action, `syncLeavingSoonCollectionHubInternal` strictly respects `Settings.pruneTargetHeadroomGb` (e.g. 300 GB). It calculates currently staged storage on the target server and only auto-stages candidate items until `accumulatedGb >= targetHeadroomGb`, preventing massive over-staging beyond the configured headroom buffer.
   - **Intelligent Headroom Satisfaction**: If existing staged items in Leaving Soon already satisfy or exceed the target headroom, additional candidates are suppressed with informative logging (`Target reclamation headroom of X GB already satisfied by Y staged items. No additional items needed.`).
   - **Seamless Sync Auto-Save**: In `prune-studio.tsx`, triggering prune evaluation (`executeRunPruneSync`) automatically flushes and saves any dirty settings (thresholds, target headroom, selected Glances disk, schedules) to SQLite via `handleSaveAllDirty()` before the sync action executes.
14. **Poster Artwork Restoration & Multi-Candidate Failover Resilience**:
   - **Automatic Image Magic Byte Detection**: Plex Media Server's `/library/metadata/{ratingKey}/posters` endpoint strictly validates binary image formats against the HTTP `Content-Type` header and returns `400 Bad Request` if a PNG or WebP buffer is uploaded with `image/jpeg`. `uploadPlexItemPoster` inspects the initial buffer magic bytes (`89 50 4E 47` for PNG, `FF D8 FF` for JPEG, `52 49 46 46` ... `57 45 42 50` for WebP, and `47 49 46 38` for GIF) and sets the exact MIME header automatically.
   - **Candidate URL Failover & Augmentation**: Calling `restoreItemOriginalArtwork` passes `urlsToTry = [resolved.serverUrl, ...(resolved.allCandidateUrls || []).filter(u => u !== resolved.serverUrl)]`. If an HTTPS `.plex.direct` domain fails due to local DNS rebind protection or TLS handshake timeouts, the request immediately fails over to the direct LAN IP (`http://192.168.1.X:32400`). If a single string URL is passed, `restoreItemOriginalArtwork` automatically augments candidates using `resolveWorkingPlexServerConnection(serverId)`.
   - **Artwork Fallback & Transparent Diagnostics**: If the local backup file on disk is missing, `restoreItemOriginalArtwork` attempts to retrieve original artwork from `backup.originalArtUrl`. If all candidate endpoints fail, `uploadPlexItemPoster` surfaces the exact HTTP status codes and server endpoints (e.g. `HTTP 404 Not Found` or `HTTP 400 Bad Request`) in the warning log instead of swallowing error context.
15. **Plex Server Crash Prevention, Stream Exclusion & SWR Memory Caching Architecture**:
   - **Plex Sections 10-Minute SWR Cache (`plexServerSectionsCache`)**: `getPlexServerSections` and `getPlexServerLibrarySections` in `src/lib/plex.ts` cache section lists for 10 minutes, eliminating parallel PMS queries whenever navigating between studio tabs or evaluating multi-server rules.
   - **Plex Library Media Items 3-Minute SWR Cache (`plexMediaItemsCache`)**: In `src/lib/curation/plex-analyzer.ts`, media items are cached in memory for 3 minutes, eliminating redundant PMS full-library scans across candidate evaluations.
   - **Cross-Server Activity 5-Minute Cache (`crossServerActivityCache`)**: `buildCrossServerPlaybackIndex` caches cluster-wide unified playback metadata in memory.
   - **Show Seasons 10-Minute Cache (`plexShowSeasonsCache`)**: `getPlexShowSeasons` caches season metadata and play counts.
   - **N+1 Season Explosion Elimination**: Skips querying `/children` for shows that have 0 views and are younger than `unwatchedMinAgeDays`, reducing HTTP requests by 80%+ on large TV libraries.
   - **Mandatory Stream Exclusion (`includeStreams: false`)**: Maintainerr candidate evaluations strictly omit stream and codec tracks, preventing PMS SQLite from performing heavy table joins across 2,500–5,000 items.
   - **Global Curation Mutex Lock (`isAnyCurationTaskRunning()`)**: In `schedule-helper.ts` and `prisma.ts`, background curation jobs across Kometa, Agregarr, Maintainerr, and Tagging are strictly serialized so only one task can query PMS at a time.
   - **Mutation & Poster Upload Pacing**: Staggered pauses (100ms–120ms) prevent SQLite write locks during poster and tag updates.
16. **Direct Plex SQLite Database Snapshot & Cross-Query CTE Engine (`plex-snapshot-engine.ts`)**:
   - **PMS Crash Prevention**: Repetitive HTTP calls to Plex Media Server during prune sweeps (`/library/sections/{id}/all`, `/library/metadata/{ratingKey}`, `/status/sessions/history/all`) cause severe SQLite write locks, 4-second timeouts, and frequent PMS container crashes on large homelabs (especially with multi-server clusters).
   - **Hot Snapshot Architecture**: Emulates the proven Unraid `plex_prune_hourly.sh` architecture. Portalarr creates atomic read-only hot snapshots of PMS SQLite databases (`com.plexapp.plugins.library.db`) via `sqlite3 "$src" ".backup '$dst'"` with fallback to file copy + WAL checkpointing (`PRAGMA wal_checkpoint(TRUNCATE)` via `node:sqlite`).
   - **Multi-Server CTE Cross-Query (`evaluatePruneCandidatesFromSnapshotsUnified`)**: Portalarr attaches secondary Plex databases (`ATTACH DATABASE '$kidsPath' AS kids`, `ATTACH DATABASE '$backupPath' AS backup`) and executes a single unified SQL Common Table Expression (CTE) query in <20ms across all servers. It computes `active_dt` (most recent of `viewed_at`, `added_at`, `created_at`) across all 3 servers simultaneously, resolving candidates with zero Plex HTTP overhead.
   - **Ghost Skip & Fallback**: Automatically filters out already-deleted records or local stub entries (`local:` guid prefix). Falls back seamlessly to HTTP querying when a server has no `databasePath` configured.
   - **Delta-Syncing & Direct File Size Calculation**: Directly queries file sizes and stream attributes from snapshot tables (`media_items`, `media_parts`) without sending individual `/library/metadata/{ratingKey}` HTTP requests, populating `fileSizeGb` and candidate criteria instantaneously.
17. **Multi-Tier Leaving Soon Watch Status Engine & PMS Overload Protection (`recheckLeavingSoonWatchActivityInternal`)**:
   - Replaces legacy sequential `/library/metadata/{ratingKey}` loops that caused heavy Plex SQLite locks, 4-second timeouts, and server crashes during prune sync with an ultra-efficient 3-tier architecture:
     - **Tier 1 (Instant Indexed Cache)**: Executes an instantaneous `<1ms` indexed lookup against local SQLite `WatchHistory` (resolving watched items with ZERO Plex network calls).
     - **Tier 2 (Batch History Query)**: Performs a single batch session history query (`/status/sessions/history/all?sort=viewedAt:desc&X-Plex-Container-Start=0&X-Plex-Container-Size=500`) fetching up to 500 recent sessions in ONE request with multi-level episode `parentRatingKey` and series `grandparentRatingKey` mapping.
     - **Tier 3 (Throttled Circuit-Breaker Fallback)**: Provides a throttled circuit-breaker fallback for any remaining items capped at 10 items with 100ms pauses between calls that aborts immediately upon 2 consecutive errors.
     - **Debounce Guard**: Protected by a 60-second per-server in-memory debounce guard (`lastWatchCheckByServer`) to eliminate redundant runs from rapid callers.
18. **Multi-Server Leaving Soon Collection Sync & Candidate Machine Identifier Matching**:
   - In multi-server clusters (`KidsPlexServer`, `MainPlexServerBackup`, `MainPlexServer`), `syncLeavingSoonCollectionHubInternal` guarantees zero cross-server URI collisions or PMS 400 Bad Request errors.
   - **Candidate Endpoint Resolution (`resolveWorkingPlexServerConnection`)**: Strictly purges candidates failing `/identity` probes with mismatched `machineIdentifier` attributes from `allCandidateUrls`, preventing secondary servers from adopting the primary server's LAN IP (`192.168.1.87`).
   - **Local Server Machine Identifier Matching**: In `syncPlexCollection`, dynamically resolves and binds the local machine identifier for each candidate base URL (`baseMachineIdMap.get(cleanBase)`), ensuring `server://{machineIdentifier}/com.plexapp.plugins.library/library/metadata/{ratingKey}` strictly matches the receiving server's local database.
   - **Resilient Fallback**: Automatically falls back to `library:///item/%2Flibrary%2Fmetadata/{ratingKey}` upon any HTTP 400 rejection followed by direct item metadata tagging (`collection[0].tag.tag=...`), achieving 100% Leaving Soon collection sync reliability with zero PMS log errors.




19. **Strict Server Isolation Guard & Automated Watch Rescue (`SERVER-ISOLATION-GUARD`)**:
    - **Strict Server Isolation Guard**: When pruning or rechecking items for a specific server (e.g. `KidsPlexServer`), `SERVER-ISOLATION-GUARD` verifies that the target server exists and is active. If not found, it strictly blocks falling back to other Plex servers (`⚠️ [SERVER-ISOLATION-GUARD] Requested Plex server not found. Strictly blocked fallback to other servers to prevent unintended cross-server modifications`), permanently preventing accidental deletions on unintended servers.
    - **Dynamic Watch Activity Rescue**: In `recheckLeavingSoonWatchActivityInternal`, if active playback is detected across Tautulli, PMS sessions, or local SQLite `WatchHistory`, the item is automatically unstaged (`🎉 Unflagged items from Leaving Soon due to detected watch activity`), original poster artwork is restored in PMS, and the Leaving Soon collection hub is synchronized immediately.

---

## 🚨 Mandatory Task Completion Protocol (Strict SemVer)

To guarantee 100% reliability, quality control, and consistency, the following 5-step protocol MUST be executed at the end of every task or feature change before considering the work complete:

0. **Step 0: Read Skill Upfront**: Call `read_file` on the relevant `SKILL.md` before writing code.
1. **Step 1: Integration Testing**: Execute `cmd /c "npm test"` to run the verification suite (`scripts/verify-all.ts`). All test suites must pass (0 failures).
2. **Step 2: Production Build Verification**: Execute `cmd /c "npm run build"`. Ensure 100% clean compilation, zero TypeScript errors, and zero Turbopack runtime errors.
3. **Step 3: Edge Security & Cloudflare Policy Audit**: Whenever ANY page route (`src/app/**/page.tsx`) or API route (`src/app/api/**/route.ts`) is created, moved, or updated, register it in `src/lib/edge-policy-paths.ts` and inform the user.
4. **Step 4: Skills & Documentation Sync**: Review and update relevant `.agents/skills/` documents to record any new UI patterns, API contracts, formulas, or operational guidelines **BEFORE** committing.
5. **Step 5: SemVer Version Increment & Git Deployment Push**: Increment version in `package.json` according to SemVer (PATCH `+1` for fixes/polish, MINOR `+1` for features), stage all changes (`git add -A`), commit with freshly incremented semantic version prefix (`[v<version>] feat/fix(scope): message`), push strictly to `origin/main` (Beta). NEVER push to `stable` unless the user explicitly instructs.
