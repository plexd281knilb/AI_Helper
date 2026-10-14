---
name: sonarr-expert
description: Expert architectural, API, and operational guide for Sonarr (TV series collection manager, episode parser, season pack grabber, and automated file renamer). Activate when integrating with the Sonarr v3/v5 REST API, configuring Torznab indexers, handling anime absolute numbering vs standard TV series types, troubleshooting download queue ingestion, or diagnosing release parsing failures.
---

# Sonarr Expert Guide

Sonarr is a PVR and television series management application. It monitors multiple indexers and RSS feeds for new and upgraded episodes, coordinates downloads with Usenet and BitTorrent clients (SABnzbd, qBittorrent, Transmission), parses complex release naming strings, maps scene vs TVDb episode numbering, and automatically imports, renames, and organizes episodes into structured season folders.

Primary Reference Repositories & Modules:
- Directory: [Sonarr-5-develop](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Sonarr-5-develop)
- OpenAPI Specification: [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Sonarr-5-develop/src/Sonarr.Api.V5/openapi.json)
- API Controllers: [src/Sonarr.Api.V5/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Sonarr-5-develop/src/Sonarr.Api.V5)
- Core Logic: [src/NzbDrone.Core/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Sonarr-5-develop/src/NzbDrone.Core)
- Portalarr Sonarr Actions: [src/app/arr-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/arr-actions.ts)

---

## Architecture & Codebase Layout

```text
Sonarr-5-develop/
├── src/
│   ├── Sonarr.Api.V5/               # REST API v5 controllers, schemas, OpenAPI spec
│   │   ├── Series/                  # Series CRUD, seasons, lookup, bulk editors
│   │   ├── Episodes/                # Episode listing, monitoring state, file mapping
│   │   ├── EpisodeFiles/            # File records, media info, quality details
│   │   ├── Commands/                # Asynchronous task dispatcher (SeriesSearch, Scan)
│   │   ├── Queue/                   # Download client queue monitoring & manual imports
│   │   └── Parse/                   # Release title debug parsing endpoint
│   └── NzbDrone.Core/               # Core business logic and persistence
│       ├── Tv/                      # SeriesService, EpisodeService, season tracking
│       ├── Parser/                  # Parsing regexes, quality detection, season packs
│       ├── DecisionEngine/          # Qualification specs (monitored, cutoff, language)
│       └── Download/                # Download client drivers & completed download tracker
└── frontend/                        # React / TypeScript UI
```

---

## Key Workflows & Runbooks

### 1. REST API Integration (v3 / v5)
Sonarr exposes an OpenAPI-compliant HTTP API secured by `X-Api-Key`:
- **Series Search & Add**: `GET /api/v5/series/lookup?term={query}` -> `POST /api/v5/series`.
- **Monitored Missing Queries**: `GET /api/v5/series` filtered by `s.monitored && (s.statistics.episodeFileCount === 0 || s.statistics.percentOfEpisodes < 100)`.
- **Tag Collections**: `GET /api/v5/tag` -> filter series where `s.tags.includes(tagId)`.
- **Episode Management**: `GET /api/v5/episode?seriesId={id}` -> `PUT /api/v5/episode/{id}`.
- **Bulk Episode Monitoring**: `PUT /api/v3/episode/monitor` with payload `{ episodeIds: number[], monitored: boolean }` to update monitoring state for multiple episodes at once.
- **Commands**: `POST /api/v5/command` (`SeriesSearch`, `SeasonSearch`, `EpisodeSearch`, `DownloadedEpisodesScan`, `RefreshSeries`). For specific episodes: `{ name: "EpisodeSearch", episodeIds: number[] }`.

See detailed runbook: [api-v5-endpoints.md](./references/api-v5-endpoints.md).

### 2. Series Types & Release Parsing
Sonarr accommodates different television formats:
- **Standard**: Season/Episode (`S01E05`).
- **Daily**: Date-based (`2024-10-15`).
- **Anime**: Absolute episode numbering (`542`), dual-audio flags, release group brackets, CRC32 checks.
- **Scene Mapping (The XEM)**: Automatically resolves discrepancies between scene releases and TVDb metadata.

See detailed runbook: [series-parsing-and-models.md](./references/series-parsing-and-models.md).

---

## Common Gotchas & Troubleshooting

1. **Anime Episodes Failing to Match**:
   - Cause: The show was configured with `seriesType: "standard"` instead of `"anime"`, preventing Sonarr from parsing absolute episode numbers (e.g. `Show Title - 25.mkv`).
   - Fix: Update `seriesType` to `"anime"` in the series editor.
2. **Season Pack Downloads Not Importing**:
   - Cause: Season pack completed in a sub-folder that the disk scanner cannot resolve, or path mappings differ between the client and Sonarr.
   - Fix: Ensure **Remote Path Mappings** map the download path correctly, and invoke `DownloadedEpisodesScan` with the sub-folder path.
3. **Episode Left Unmonitored After Adding Series**:
   - Cause: The series was added with `addOptions.monitor` set to `"future"` or `"none"`.
   - Fix: Use `"monitor": "all"` to monitor historical seasons.
4. **4K vs 1080p Sonarr Instance Isolation**:
   - Sonarr instances should be explicitly targeted by their configured ID in settings (`seerrDefaultTvAppId` for 1080p, `seerrDefaultTv4kAppId` for 4K). Never auto-fallback to any server containing "4k" if 4K is disabled in settings.
5. **Super User Instance Access Gating**:
   - In `src/app/arr-actions.ts`, only `ADMIN` bypasses `enabledForUsers`. Super users and regular users must only see instances where `enabledForUsers: true` is explicitly checked in Edit Application, ensuring instances like `Kids Sonarr` never leak into user management views unless explicitly enabled.
6. **Queue Progress Monitoring**:
   - Query `/api/v3/queue?page=1&pageSize=1000` and match `record.seriesId` against active requests to compute exact download progress percentages (`((size - sizeleft) / size) * 100`).
7. **Reconciling Season Monitoring Completeness**:
   - When inspecting series monitoring, evaluate `episodes` list: if `monitoredEpisodeCount === totalEpisodeCount`, flag `isFullyMonitored = true`; if `0 < monitoredEpisodeCount < totalEpisodeCount`, flag `isPartiallyMonitored = true`.
8. **Series & Queue Deletion Endpoints**:
   - `deleteSonarrSeries`: `DELETE /api/v3/series/{id}?deleteFiles={deleteFiles}&addImportListExclusion={addImportListExclusion}` allows removing television shows with optional disk media cleanup.
   - `deleteSonarrQueueItem`: `DELETE /api/v3/queue/{id}?removeFromClient={removeFromClient}&blocklist={blocklist}` cancels stuck or unwanted downloads from the download client.
9. **Interactive Release Search Custom Format Scoring & Rejections**:
   - Query `/api/v3/release?seriesId={id}` or `?episodeId={id}` and prioritize candidates by `b.customFormatScore - a.customFormatScore`.
   - Render `CF: +score` badges, release age indicators (`Clock` icon), and multi-line rejection warnings while filtering out benign non-fatal notes.
10. **Background Queue Auto-Polling & Non-Intrusive UI Telemetry**:
    - When the activity/queue tab is active, trigger 5-second automatic silent refreshes of `/api/v3/queue`.
    - Render animated progress bars, formatted transferred bytes (`formatBytes(size - sizeleft)} of ${formatBytes(size)}`), and replace tab-blocking `alert()` calls with floating glassmorphic toasts.
