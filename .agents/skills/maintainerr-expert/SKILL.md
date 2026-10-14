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


