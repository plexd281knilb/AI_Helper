---
name: kometa-expert
description: Expert architectural and configuration guide for Kometa (formerly Plex Meta Manager) and Portalarr Poster Studio. Activate when creating, debugging, or optimizing media metadata, automated image overlays (4K HDR badges, Dolby Vision/Atmos ribbons, rating badges, audio/video specs), collection builders, playlist rules, schedule settings, or Kometa YAML configurations.
---

# Kometa & Poster Studio Expert Guide

Kometa (formerly Plex Meta Manager) and Portalarr's Native Poster Studio automate Plex media metadata management and artwork enhancement. They build dynamic collections and smart playlists, apply graphical poster and backdrop overlays (resolution, HDR, audio codec, streaming source, network, IMDb/TMDb/Rotten Tomatoes ratings, awards ribbons), and standardize media library styling.

Primary Reference Repositories & Modules:
- Directory: [Kometa-master](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master)
- Entry Point: [kometa.py](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/kometa.py)
- Modules: [modules/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/modules)
- Default Overlays & Templates: [defaults/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/defaults)
- Portalarr Poster Engine: [src/app/api/curation/badges/route.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/api/curation/badges/route.ts)
- Portalarr Media Image API: [src/app/api/media/image/route.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/api/media/image/route.ts)

---

## Architecture & Module Directory

```text
Kometa-master/modules/
├── builder.py       # Core collection, playlist, and smart builder resolver
├── overlay.py       # Overlay coordinate math, variables, special text, dimensions
├── overlays.py      # Image loading, PIL composite pipeline, original asset preservation
├── meta.py          # Metadata mass updating (titles, locked fields, genres, labels)
├── plex.py          # Plex Media Server client, collections, hub visibility, poster uploads
├── operations.py    # Library sweeps, genre mapping, label purging, asset directory linking
└── config.py        # YAML configuration loader and environmental parameter parser
```

---

## Core Capabilities & Runbooks

### 1. Dynamic Poster & Backdrop Overlays
Kometa and Portalarr generate 1000x1500 (2:3 portrait) or 1920x1080 (16:9 landscape) layered artwork:
- **Ribbon & Awards**: Oscars, Golden Globes, Emmy award badges.
- **Resolution & Media Flags**: 4K UHD, HDR, HDR10+, Dolby Vision, IMAX Enhanced, audio codec (TrueHD, Atmos, DTS-HD).
- **Ratings & Dynamic Badges**: Real-time IMDb, Rotten Tomatoes (Certified Fresh / Popcorn), TMDb ratings.
- **Suppression & Queues**: Weights and group rules prevent overlapping badges.
- **Multi-Position Rendering**: Supports `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center-top`, `center-bottom`.

See detailed runbook: [overlay-engine.md](./references/overlay-engine.md).

### 2. Collection & Smart Playlist Builders
Builds collections from over 20+ list providers:
- **TMDb, IMDb, Trakt, Letterboxd, MDBList**: Auto-populated based on trends, awards, actors, directors, or user lists.
- **Filtering Pipeline**: Exclude or include by genre, year, rating, country, audio codec, and release dates.
- **Sync Modes**: `sync` (strict parity, removing unlisted items) vs `append` (keep manual additions).

See detailed runbook: [collection-builders.md](./references/collection-builders.md).

### 3. Dual Automation Schedules & Background Engine
Portalarr separates overlay generation into two distinct, decoupled automated schedules:
- **Fast Incremental Scan (`overlayIncrementalSchedule`)**: High-frequency scan (e.g. `every_hour`, `every_3_hours`) targeting newly added and upgraded media across enabled libraries.
- **Deep Library Recheck (`overlayRecheckSchedule`)**: Comprehensive maintenance sweep (e.g. `daily_4am`, `weekly_sun`) verifying existing badge hashes, updating dynamic countdown/ribbon dates, and processing all catalog items.
- **Universal Scheduler (`isScheduleDue`)**: Evaluates interval schedules with a 5-minute variance buffer (e.g. 55m for 1h), and checks daily fixed-time schedules against `now.getHours() === targetHour && (!lastRun || lastRun.toDateString() !== now.toDateString()) && elapsed >= 12h`.

---

## Common Gotchas & Troubleshooting

1. **Poster Aspect Ratio & Transcoder Cropping**:
   - Cause: Requesting landscape dimensions (e.g. `600x400`) from Plex `/photo/:/transcode` forces PMS to center-crop portrait posters.
   - Solution: Always request standard 2:3 vertical poster proportions (`width=600&height=900&minSize=1`).
2. **Scheduler Looping on Missing Tokens**:
   - Cause: If Plex tokens or settings are missing, returning early without updating `overlayIncrementalLastRunAt` / `overlayRecheckLastRunAt` causes the 60-second background ticker to retry indefinitely every minute.
   - Solution: Always persist `lastRunAt: new Date()` to SQLite even on early exits or unconfigured server tokens.
3. **Decoupled In-Flight Mutexes**:
   - Incremental and deep recheck runners must use dedicated in-flight locks (`__PORTALARR_OVERLAY_INC_RUNNING`, `__PORTALARR_OVERLAY_RECHECK_RUNNING`) rather than a shared global sync lock, ensuring long-running deep sweeps do not block quick incremental checks or library scans.
4. **Overlay Degradation / Quality Loss**:
   - Cause: Re-applying overlays on top of already overlaid posters causes blur and artifacting.
   - Solution: Always preserve clean original source posters in an asset cache or pristine storage before compositing overlays.
5. **Plex Client Caching Glitches**:
   - Cause: Plex Web and mobile clients aggressively cache posters in local cache storage.
   - Fix: Force a cache busting parameter or update PMS `thumb` timestamp upon uploading new artwork.
6. **Weight & Group Collision**:
   - Cause: Multiple overlays render on the same corner without a common `group` or `queue`.
   - Rule: Overlays that share screen coordinates must define a `group` with distinctive `weight` values.
7. **Badge Toggles & Slider Layout**:
   - Cause: Nesting `sm:grid-cols-2` inside multi-column simulator cards squeezes columns to ~120px, causing the Position Select dropdown to overlap the Size slider and forcing the slider out of the card bounds.
   - Rule: Always stack Placement dropdowns (`h-7.5 w-32 shrink-0`) and Scale Size sliders vertically with `w-full min-w-0` on range inputs within a bounded `max-w-[150px]` container.
8. **Cross-Library & Cross-Server Rule Hijacking**:
   - Cause: Falling back to `findFirst({ orderBy: { updatedAt: "desc" } })` when looking up overlay rules causes an unconfigured library to hijack the ID and configuration of whatever library was most recently edited. Saving then inadvertently overwrites the previous library's rule.
   - Rule: Overlay rules must strictly resolve to `(serverId, sectionKey)` or `(serverId, sectionKey: null)` server-default. If saving a rule with a mismatched server or section, always create a new rule rather than updating the mismatched existing rule ID.
9. **Revert Button Granularity (Section vs Server)**:
   - Cause: A single global "Revert All" button wipes out original artwork across all libraries on the Plex server, even when an admin only wanted to revert a test in a single section.
   - Rule: Always provide section-scoped reverts (`revertLibraryOverlaysAction(serverId, sectionKey)`) querying the specific section's rating keys, while offering a clear confirmation dialog for server-wide reverts.
10. **Custom Badge ID Scoping**:
    - Cause: Unrestricted custom badge retrieval overlays all active badges globally onto every library regardless of the library's rule configuration.
    - Rule: Check and filter against `rule.customBadgeIds` in `applyOverlaysToLibraryInternal` so only badges explicitly enabled for that rule are processed.
11. **TV Episode 16:9 Thumbnail Distortion**:
    - Cause: Applying 2:3 portrait overlays (1000x1500) to Plex TV episode items (`type === "episode"`) forces center-cropping into vertical portraits, ruining 16:9 episode screenshots.
    - Rule: Guard against `item.type === "episode"` in `backupAndApplyOverlay` and single-item overlay actions.
12. **Orphan Artwork Backup Reclamation**:
    - Cause: Media items removed or upgraded in Plex leave orphaned `.jpg` backups and SQLite rows in `mediaArtBackup` in `data/art_backups`.
    - Rule: Provide `pruneOrphanArtworkBackupsAction` to reconcile active PMS rating keys against backup records, unlinking orphaned physical `.jpg` files and reclaiming disk storage.
13. **Dual Automation Schedules, Mutual Exclusion & Scheduler Precision**:
    - **Dual Schedules**: Fast Incremental Scan (`overlayIncrementalSchedule`, default `every_hour`) scans only unbadged/upgraded items, while Deep Library Recheck (`overlayRecheckSchedule`, default `daily_4am`) inspects the entire library.
    - **Mutual Exclusion**: Background runners in `src/lib/prisma.ts` and actions in `src/app/curation-actions.ts` enforce that `__PORTALARR_OVERLAY_INC_RUNNING` and `__PORTALARR_OVERLAY_RECHECK_RUNNING` mutually exclude each other, preventing two overlay jobs from reading and writing the same poster art simultaneously.
    - **Scheduler Mutex Ownership & Debouncing**: The background scheduler in `src/lib/prisma.ts` MUST NOT set global running flags before calling `runOverlayIncrementalSyncInternal()` or `runOverlayRecheckSyncInternal()`. The internal functions manage their own mutex flags. Prematurely setting flags in `prisma.ts` causes the invoked functions to immediately abort with "An overlay scan task is already in progress.", skip updating `overlayIncrementalLastRunAt`, and loop every 60 seconds. The scheduler updates `overlayIncrementalLastRunAt = now` immediately upon schedule trigger to debounce subsequent 60-second ticks.
    - **Error Recovery**: Catch blocks in `runOverlayIncrementalSyncInternal` and `runOverlayRecheckSyncInternal` update `LastRunAt` to prevent the 60-second background ticker from re-triggering repeatedly on transient errors.
    - **Catch-up Guard**: Fixed daily (`daily_4am`), weekly Sunday, and monthly schedules enforce `lastRun && elapsedMs >= threshold` for catch-up, preventing fresh installations from prematurely triggering deep rechecks during peak hours.
14. **Collection & Poster Studio Candidate Indexing and Placeholder Guards**:
    - **Trailer & Stub Immunity**: When Kometa Studio or Poster Studio evaluates collections or batches media, trailer stubs, placeholder files (`.portalarr-missing`, `edition-trailer`, duration < 15 min, size < 25MB), and future unreleased items (`year > currentYear`) are isolated via `isPlexItemPlaceholderOrStub` in `@/lib/curation/plex-analyzer`.
    - **Year-Aware Candidate Title Matching**: When matching candidate items to library media by title, matching strictly checks `Math.abs(libraryItem.year - candidate.year) <= 1` via `matchLibraryItemToCandidates` to prevent vintage releases from cross-matching unreleased remakes/reboots.
15. **IMDb Top 150 vs Top 250 Waterfall Ribbon Differentiation & Vector Corner Banner Resolution**:
    - **Stock Asset Collision**: Kometa's stock asset repository contains `ribbon/yellow/imdb.png` which has the text 'IMDb TOP 250' permanently pre-rendered into the graphic. There is no stock `imdb150.png` asset in Kometa.
    - **Strict Top 150 Isolation**: `resolveStockRibbonPath` excludes `150` from matching `assetName = "imdb"`, mapping `imdb_top_150` to `blank-${color}.png` (`blank-yellow.png`) instead.
    - **Dynamic Vector Banner Rendering**: In `applyOverlaysToPoster`, when `winningRibbonName` is `imdb_top_150` (or `winningRibbonText` contains `150` or custom tier text is specified), the overlay engine routes to `generateBannerSvg` with `winningTheme` (`amber-gold`) and `winningRibbonText` (`IMDb TOP 150`), producing crisp vector text and correct corner rotation rather than stamping the stock `imdb.png` Top 250 graphic.
    - **Simulator Parity**: In `kometa-studio.tsx`, `isTop150` is evaluated before `isTop250` so that `cleanText.includes("150")` produces the `- TOP 150 -` sub-label on amber gold ribbons rather than `- ALL-TIME BEST -`.

