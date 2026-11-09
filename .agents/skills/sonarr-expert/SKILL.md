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
11. **Autonomous Release Grab & Optimal File Verification (`searchAndGrabSonarrReplacement`)**:
    - When diagnosing missing tracks or corrupt episodes, inspect `/api/v3/release?episodeId={id}` and compare against `/api/v3/episodefile/{episodeFileId}`.
    - If Sonarr indexer releases are rejected with `Existing file on disk has a equal or higher Custom Format score: {score}` or the quality cutoff is met, return `alreadyOptimal: true` (with `releaseTitle`, `quality`, and `existingScore`) rather than falsely claiming an autonomous grab was queued.
    - If a superior candidate release is approved, queue download via `POST /api/v3/release { guid, indexerId }`.
12. **Missing Cover & Poster Fallback**:
    - When `series.images` lacks an external `remoteUrl` (e.g. running in Docker networks where only internal container paths `/MediaCover/...` exist), always fall back to `/api/media/image?title=${encodeURIComponent(series.title)}&year=${encodeURIComponent(String(series.year || ""))}&type=show` so artwork is proxied through TMDb or iTunes rather than rendering a blank "No Cover" placeholder.


13. **Card Title & Monitored Status Badge Non-Overlap Layout**:
    - In the TV series management grid, long titles previously collided with the top-right `MONITORED` / `UNMONITORED` badge.
    - Series cards wrap titles in a flexible container (`flex-1 min-w-0 pr-2`) with `shrink-0` on status badges, ensuring titles wrap and truncate naturally without badge collision across desktop and mobile viewports.

---

## 🚨 Mandatory Task Completion Protocol (Strict SemVer)

To guarantee 100% reliability, quality control, and consistency, the following 5-step protocol MUST be executed at the end of every task or feature change before considering the work complete:

0. **Step 0: Read Skill Upfront**: Call `read_file` on the relevant `SKILL.md` before writing code.
1. **Step 1: Integration Testing**: Execute `cmd /c "npm test"` to run the verification suite (`scripts/verify-all.ts`). All test suites must pass (0 failures).
2. **Step 2: Production Build Verification**: Execute `cmd /c "npm run build"`. Ensure 100% clean compilation, zero TypeScript errors, and zero Turbopack runtime errors.
3. **Step 3: Edge Security & Cloudflare Policy Audit**: Whenever ANY page route (`src/app/**/page.tsx`) or API route (`src/app/api/**/route.ts`) is created, moved, or updated, register it in `src/lib/edge-policy-paths.ts` and inform the user.
4. **Step 4: Skills & Documentation Sync**: Review and update relevant `.agents/skills/` documents to record any new UI patterns, API contracts, formulas, or operational guidelines **BEFORE** committing.
5. **Step 5: SemVer Version Increment & Git Deployment Push**: Increment version in `package.json` according to SemVer (PATCH `+1` for fixes/polish, MINOR `+1` for features), stage all changes (`git add -A`), commit with freshly incremented semantic version prefix (`[v<version>] feat/fix(scope): message`), push strictly to `origin/main` (Beta). NEVER push to `stable` unless the user explicitly instructs.
