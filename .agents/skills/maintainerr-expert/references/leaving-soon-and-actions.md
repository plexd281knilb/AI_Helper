# Maintainerr "Leaving Soon" Staging, Banners & Actions Reference

This document details the lifecycle of staged media items, countdown banner overlays, and prune actions across Plex, Radarr, Sonarr, and download clients.

Reference source files:
- [apps/server/src/modules/collections/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development/apps/server/src/modules/collections)
- [apps/server/src/modules/actions/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development/apps/server/src/modules/actions)
- [src/app/curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)

---

## 1. "Leaving Soon" Staging Workflow

1. **Rule Evaluation**: Candidates are identified based on inactivity, watch status, age, or disk thresholds.
2. **Staging**:
   - Items are tagged with Plex label `leaving-soon`.
   - Items are added to a dedicated Plex collection: `⚠️ Leaving Soon`.
   - The collection is promoted to the Plex Home screen to alert household members and friends.
3. **Grace Period**:
   - A configurable timer (e.g. 7 days, 14 days, 30 days) begins counting down.
   - If a user watches the media item during this grace period, the rule resets and the item is un-staged.

---

## 2. Dynamic Countdown Banner Overlays

To visually alert users browsing library posters:
- Maintainerr and Portalarr render dynamic countdown banners at the bottom or top of candidate posters:
  - `LEAVING IN 7 DAYS`
  - `EXPIRING OCT 15`
  - `LOW DISK SPACE CLEANUP`
- Banners are composited using `sharp` / SVG and uploaded to PMS via `POST /library/metadata/{ratingKey}/posters`.

---

## 3. Autonomous Watch Activity Revocation (Self-Healing) & Multi-Tier Engine

When household users browse the `⚠️ Leaving Soon` collection on the Plex Home screen, playback activity rescues staged items:
- **Revocation Condition**: `recheckLeavingSoonWatchActivityInternal` verifies if staged items were watched during the grace period (`lastViewedAt >= (flaggedAt - 24 hours)`).
- **Multi-Tier Batch Engine (Plex Overload Protection)**: Rather than bombarding Plex with sequential `/library/metadata/{ratingKey}` queries that exhaust PMS HTTP worker threads and trigger timeout cascades:
  1. **Tier 1 (Local SQLite `WatchHistory`)**: Instantaneous `<1ms` indexed lookup against local playback records. Unflags items with ZERO Plex PMS network calls.
  2. **Tier 2 (Single PMS Batch Session History)**: Fetches up to 500 recent sessions in ONE single request via `/status/sessions/history/all?sort=viewedAt:desc&X-Plex-Container-Start=0&X-Plex-Container-Size=500`. Resolves movies, season `parentRatingKey`, and series `grandparentRatingKey` in bulk.
  3. **Tier 3 (Throttled Circuit-Breaker Fallback)**: For any remaining unverified items, caps individual metadata checks to at most 10 items with a 100ms throttle between calls. Immediately aborts if 2 consecutive timeouts or errors occur to preserve Plex stability.
- **60-Second In-Memory Debounce**: `lastWatchCheckByServer` prevents rapid back-to-back runs (e.g. from concurrent sync tasks) from querying the same Plex server within 60 seconds unless explicitly forced via admin action.
- **Lane 1 Retention Integrity**: Items staged under Lane 1 (Oldest Watched) already have `viewCount > 0` and legacy `lastViewedAt` timestamps from months ago. Checking strictly against the staging window prevents false-positive revocation loops where Lane 1 items unflag themselves immediately upon staging.
- **Artwork Vault Restoration**: When an item is rescued by watch activity, its original un-badged poster is automatically restored from the local artwork vault (`restoreItemOriginalArtwork`), ensuring no permanent visual artifacts remain on library posters.

---

## 4. Prune Actions & Safe Disk Deletion

When the grace period expires without activity:
1. **Radarr Prune**:
   - Calls `DELETE /api/v3/movie/{id}?deleteFiles=true&addImportExclusion=false`.
2. **Sonarr TV Season Pruning Safety**:
   - For season-level items (`- Season X` or `(Season X)`): Queries `/api/v3/episode?seriesId={id}&seasonNumber={seasonNum}`, deletes the individual episode files via `DELETE /api/v3/episodefile/{episodeFileId}`, unmonitors the episodes via `/api/v3/episode/monitor`, and unmonitors the season in the series model. **NEVER deletes the root series entity**.
   - For entire series items (no season specified): Calls `DELETE /api/v3/series/{id}?deleteFiles=true&addImportExclusion=false`.
3. **Scheduled Sync Optimization**:
   - `runMaintainerrSyncInternal` hoists watch activity rechecks and expired item reclamation to run once per server pass rather than repeating N times inside the library section loop.
   - `syncLeavingSoonCollectionHubInternal` isolates items by `sectionKey`, preventing cross-library section rating key leakage into foreign collection hubs.
4. **Glances Storage Array Mount Detection**:
   - Heuristically prioritizes storage array mounts (`/mnt/user`, `/media`, `/data`, `/storage`, `pool`, `tank`) when `selectedGlancesDiskId` is unset, preventing accidental fallback to container root (`/`).
5. **Download Client Purge**:
   - Instructs qBittorrent, SABnzbd, or Transmission to delete associated torrents and NZBs to prevent re-downloads.
6. **Filesystem Cleanup**:
   - Removes empty parent folders (`purgeEmptyDirectories`).
   - Cleans up associated `.nfo`, `.srt`, and subtitle files.
