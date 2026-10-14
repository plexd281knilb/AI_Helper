---
name: agregarr-expert
description: Expert architectural and operational guide for Agregarr (collection aggregator, smart playlists, home screen hubs, placeholder stubs, filtered smart hubs, hub dismissal blacklists, and poster styling). Activate when implementing or debugging collection synchronization, list providers (Trakt/TMDb/MDBList/Letterboxd/MAL/Radarr/Sonarr), placeholder stubs, home screen hub promotion, filtered smart hubs, or Agregarr database and API models.
---

# Agregarr Expert Guide

Agregarr is an automated media collection curation and Plex home screen management platform. It aggregates media lists from multiple upstream providers (Trakt, TMDb, MDBList, Letterboxd, IMDb, MyAnimeList, Radarr, Sonarr, Overseerr, Plex Watchlist), matches items against local libraries, creates static or smart collections, promotes collections to Plex Home and Recommended screens, generates placeholder video stubs for upcoming content, deploys filtered smart hubs that exclude placeholder trailers, and dynamically applies styled artwork overlays.

Primary Reference Repositories & Modules:
- Directory: [agregarr-latest](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest)
- API Definition: [agregarr-api.yml](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/agregarr-api.yml)
- Server Entry: [index.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/index.ts)
- Portalarr Native Engine: [src/app/curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)
- Portalarr Preset Catalog: [src/lib/curation/presets.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/lib/curation/presets.ts)

---

## Core Architecture & Module Layout

```text
agregarr-latest/server/
├── api/
│   ├── plexapi.ts              # Native Plex Media Server client (hubs, collections, labels, ratings)
│   └── overseerr.ts            # Overseerr / Jellyseerr media request integration
├── entity/
│   ├── CollectionMetadata.ts   # Collection settings, visibility, sort titles, time restrictions
│   ├── PlaceholderItem.ts      # Active placeholder files, tmdbId, path, plexRatingKey
│   └── PosterTemplate.ts       # Canvas styling, typography, colors, badges
├── lib/
│   ├── collectionsSync.ts      # Main synchronization orchestrator and task state
│   ├── collections/
│   │   ├── services/           # CollectionSyncService, HubSyncService, DiscoveryService
│   │   ├── plex/               # PlexHubManager, PlexSmartCollectionManager, UnifiedOrdering
│   │   └── sources/            # Upstream list fetchers (trakt, tmdb, mdblist, letterboxd, radarr, sonarr, mal)
│   ├── placeholders/           # placeholderManager.ts, trailerDownload.ts, PlaceholderDiscovery.ts
│   └── posterGeneration.ts     # Dynamic canvas poster renderer
└── routes/
    ├── collections.ts          # CRUD endpoints for collections, sync triggers, previews
    └── collection-posters.ts   # Poster upload, template generation, downloads
```

---

## Key Workflows & Recipes

### 1. Synchronizing Collections & Hubs
Sync evaluates each active collection configuration:
1. **Fetch Upstream List**: Queries provider (e.g. `trakt.trending`, `tmdb.popular`, `mdblist.custom_url`, `radarr:monitored_missing`, `sonarr:monitored_missing`, `letterboxd`, `mal`).
2. **Resolve to Plex Media**: Matches TMDb/IMDb/TVDb IDs or normalized titles against library `Guid` or `ratingKey`.
3. **Handle Placeholders**: If `createPlaceholdersForMissing: true`, creates on-disk `.mp4`/`.disc`/`.strm` stubs for unacquired items.
4. **Update Plex Collection**: Calls `POST /library/collections` (if new) or increments items via `updateCollectionContents`.
5. **Set Order & Hub Visibility**: Calls `HubSyncService` to configure `promotedToOwnHome`, `promotedToSharedHome`, and `promotedToRecommended`.

See detailed runbook: [plex-hubs-and-sync.md](./references/plex-hubs-and-sync.md).

### 2. Filtered Smart Hubs & Placeholder Exclusion
When trailer placeholders exist in a Plex library, standard default Plex hubs ("Recently Added", "Recently Released") display trailer stubs. Agregarr and Portalarr deploy **Filtered Smart Hubs**:
- **Movies**: `?type=1&label!=trailer-placeholder&label!=Coming%20Soon-placeholder&editionTitle!=Trailer&sort=addedAt:desc`
- **TV Shows**: `?type=2&season.index!=0&label!=trailer-placeholder&label!=Coming%20Soon-placeholder&episode.title!=Trailer%20(Placeholder)&sort=addedAt:desc`
- **TV Specials & Trailer Stub Exclusion (`season.index!=0`)**: In Plex TV queries (`type=2`), TV shows whose only media files are Season 00 specials or trailer placeholders (`S00E00`) are strictly excluded by appending `&season.index!=0`. This guarantees curated TV hubs ("Recently Added TV", "Recently Released TV", "Recently Released Episodes", "Top Unwatched TV") only display genuine TV series with regular broadcast seasons (Season 1+).
- **PMS Smart Collection Immutability & Re-creation**: Plex Media Server does NOT support modifying existing smart collection queries via `PUT /library/collections/{id}/items?uri=...` (it hangs for 4 seconds and fails). When a collection's filter URI changes, Agregarr sweeps all matching collections whose `content` attribute differs from `fullUri`, cleanly deletes them from PMS (`DELETE /library/metadata/{ratingKey}`), and creates a fresh smart collection via `POST /library/collections` with `smart=1&uri=${fullUri}`.
- **Multi-User Child Collection Cleanup**: When `collectionFilterBasedOnUser=1` is set (e.g. for `top_unwatched`), Plex spawns virtual per-user collection instances. Updating or redeploying cleans up all outdated matching instances to prevent duplicate ghost collections.
- **Candidate Preview & Stub Filtering (`isPlexItemPlaceholderOrStub`)**: Filters out TV shows residing in trailer placeholder folders (`placeholders/curated_tv_shows`), files containing `.trailer.`, and series where `hasOnlySpecials: true` or `hasRegularSeasons: false`.
- **Top Unwatched (Personalized)**: Dynamic filter with `collectionFilterBasedOnUser=1` so Plex computes unwatched recommendations dynamically per logged-in user.

See detailed runbook: [filtered-smart-hubs-and-dismissal.md](./references/filtered-smart-hubs-and-dismissal.md).

### 3. Permanent Hub & Collection Dismiss / Blacklist System
To prevent deleted Plex-generated hubs (like "Top Movies by Director" or deleted smart collections) from reappearing when clicking "Import from Plex" or running automated sweeps:
- Deleted items are registered in a persistent dismissed/ignored registry (`Settings.dismissedHubs`, `MediaCollection.isIgnored: true`).
- Library collection importers match against dismissed `ratingKey`s and normalized titles and permanently skip them.
- An Ignored Hubs modal allows administrators to inspect and unignore/restore hubs on demand.

See detailed runbook: [filtered-smart-hubs-and-dismissal.md](./references/filtered-smart-hubs-and-dismissal.md).

### 4. Missing Content & Placeholder Stubs
Agregarr bridges the gap between unreleased media and Plex collections by creating physical video files:
- **Movies**: `{libraryPath}/{Title} ({Year})/{Title} ({Year}) {tmdb-{id}} {edition-Trailer}.mp4`
- **TV Shows**: `{libraryPath}/{Title} ({Year})/Season 00/S00E00.Trailer.mp4`
- **Cleanup**: When real media is ingested, the placeholder file and directory are safely purged.

See detailed runbook: [placeholders-and-stubs.md](./references/placeholders-and-stubs.md).

### 5. Label & Tagging Integration
Agregarr manages metadata labels on items:
- **Add Label**: Fetches existing `metadata.Label`, appends tag, and sends `PUT /library/metadata/{ratingKey}?label[0].tag.tag=...&label[N].tag.tag=...`.
- **Clear All Labels**: Sends `label[0].tag.tag-=`.
- **Query by Label**: `GET /library/sections/{libraryKey}/all?label={labelName}`.

### 6. Collection Edit Modal & Reset to Preset Defaults
The Collections & Hubs studio provides interactive per-collection configuration via the **Edit** action button:
- **Edit Modal (`Edit Collection: {title}`)**: Configures Plex client screen targets (Owner Home, Shared Home, Recommended), inline library display mode (`default`, `hide`, `hideItems`, `showItems`), home screen numerical ranking (#1 - #99) and sort prefix, day-of-week active scheduling, daily time windows, seasonal date ranges, excluded Plex labels, and trailer placeholder generation.
- **Reset to Defaults (`RotateCcw`)**: Locates the underlying preset from `COLLECTION_PRESETS` (via exact title, preset ID, `sourceType`/`sourceQuery`, or normalized alphanumeric match) and restores all configuration fields to their preset baseline settings (or default studio settings for custom collections).
- **Fast Non-Blocking Save & Background Sync**:
  - **Save Changes (`Save`)**: Optimistically updates the collection card in React state and closes the modal in **0ms**, displaying an immediate confirmation toast while persisting settings to SQLite asynchronously with `syncToPlex: false`. Media managers can batch multiple edits with zero lag or waiting, then push changes when ready.
  - **Save & Sync in Background (`RefreshCw`)**: Optimistically updates the card, closes the modal in **0ms**, and launches `syncCollectionToPlexAction` asynchronously in the background with card-level loading spinners and floating glassmorphic toasts.
  - **Zero-Network Collection Loading**: `getMediaCollectionsAction` resolves candidate server identifiers strictly from the local SQLite `prisma.plexServer` table in <1ms without performing upstream network round-trips to PMS, eliminating screen refresh lag.
  - **Sync All to Plex (`Zap`)**: Prominent action button positioned in the Active Collections toolbar for 1-click background synchronization of all collections in the library via `runAgregarrSyncAction`.

### 7. Inline Quick Position Editor on Collection Cards
Active collection cards feature an interactive position badge (`#<rank>`) allowing administrators to instantly reprioritize collection hubs:
- **Direct Rank Input**: Clicking the `#<rank>` badge replaces static display with an inline number input auto-selecting current position.
- **Instant Repositioning**: Enter any target position (e.g. `20` from `#1`) and press `Enter`, click the `Check` (✓) icon, or blur the input.
- **Automatic Array Reindexing & Plex Sync**: Automatically splices and shifts intervening collections, recalculates 2-digit zero-padded sort prefixes (`!01_`, `!20_`), updates local state, and fires `reorderPlexCollectionsAction` to synchronize Plex Home Screen hub ordering and SQLite database records immediately with user feedback toast.

### 8. Fast Collection Media Preview & Live Inspector (`getCollectionMediaPreviewAction`)
The Agregarr Studio provides instant media verification via the **Inspect Media** (`Eye`) action on active collections:
- **Concurrent Tri-Tier Resolution**: `evaluateCollectionMediaPreviewInternal` queries candidate media items, local Plex library media, and Servarr (Radarr/Sonarr) monitored indexes concurrently using `Promise.allSettled`:
  - **Plex Library Scan**: Prioritizes confirmed working server URLs with an item limit of 1,500 and a strict 3.5s timeout.
  - **Servarr Monitored Index**: Fast background index with a strict 3.0s timeout.
  - **Candidate List**: Capped at 2 pages and protected by a 5.0s `AbortSignal.timeout` on all raw TMDb fetches.
- **Double Safety Timeouts & Non-Blocking Client UI**:
  - **Server-Side Timeout**: Bounded by an 8.5-second `Promise.race` safety guard returning whatever items were fetched or clean error details.
  - **Client-Side Timeout**: Capped by a 9.0-second safety race in `handleInspectCollectionMedia`.
  - **Cancel & Retry UI**: Modal renders a 1-click **Cancel** button during loading, and an error state with an instant **Retry Query** button if upstream APIs fail, eliminating infinite modal freezes.

### 9. Coming Soon (Radarr & Sonarr Monitored) Ingestion Heuristics & Auto-Placeholders
Agregarr dynamically pulls upcoming monitored content directly from Radarr and Sonarr instances:
- **Expanded Candidate Evaluation Window**:
  - **Radarr Movies (`isRadarrMovieComingSoon`)**: Evaluates `monitored: true` and `hasFile: false`. Captures `status: "announced"` (for current/future year), `status: "inCinemas"`, `isAvailable: false`, future digital/physical dates within 365 days, recent releases within a 90-day grace window, and current/future year releases, while strictly filtering out dead multi-year backlogs from previous years.
  - **Sonarr Series (`isSonarrSeriesComingSoon`)**: Evaluates `monitored: true` with missing episodes (`episodeFileCount < totalEpisodeCount`). Captures `status: "upcoming"`, `status: "continuing"` active shows between seasons, future `nextAiring` dates within 365 days, and current/future year releases.
- **Plex Disk Catch-22 Resolution in Preset Previews**:
  - Unreleased missing movies/shows do not exist on disk in Plex yet before placeholders are generated.
  - `generateCollectionCandidateItemsPreviewAction` (`previewCollectionMatchingAction`) detects when Plex library matches are zero and immediately populates `sampleMatches` and `matchCount` from the Servarr candidate stream (flagged with `isPlaceholderCandidate: true`) with posters, years, and ratings.
- **Auto-Placeholders on Collection Sync**:
  - Collections with `sourceType === "radarr"` or `sourceType === "sonarr"` (or `sourceQuery === "monitored_missing"`) automatically trigger placeholder trailer generation (`generateCollectionPlaceholdersInternal`) even if `includePlaceholders` was omitted in older records, guaranteeing video stubs exist in Plex before library content mapping.
- **Smart Banner Classification**:
  - `resolveItemSmartBanner` strictly checks `isGenuinelyReleased`. Announced movies or shows between seasons without digital/physical release dates banner cleanly as `COMING SOON MONITORED` (amber-gold) rather than defaulting prematurely to `DOWNLOADING SOON`.

---

## Common Gotchas & Troubleshooting

1. **"Synced Collections & Hubs successfully: 0 rules evaluated"**:
   - Cause: The collection has no active source rules, `isActive: false`, or current date is outside `timeRestriction` start/end window.
   - Fix: Verify collection rule toggle is enabled, and check `timeRestriction.removeFromPlexWhenInactive` settings.
2. **Deleted Plex Hubs Resurrecting on Sync/Import**:
   - Cause: Plex auto-generates category/actor/director hubs, or "Import from Plex" blindly re-inserts deleted collections.
   - Fix: Always record deleted hub ratingKeys and normalized titles into `dismissedHubs` and filter them out during sync and import.
3. **Placeholder files not showing in Plex or polluting Recently Added**:
   - Cause: Plex library scanner has not refreshed the target folder, or placeholders lack `trailer-placeholder` labels.
   - Fix: Run the placeholder tagging worker (`tagAllPlaceholdersInPlexInternal`) and deploy Filtered Smart Hubs.
4. **Smart Collections Reordering Failure**:
   - Cause: Smart collections in Plex are dynamically populated by Plex search filters. Attempting to call `/move` or `/items` on a smart collection will corrupt or error out.
   - Rule: Always check `isSmartCollection(ratingKey)`. Never call incremental item moves on smart collections.
5. **Collection Deletion Latency & Server Action Timeouts**:
   - Cause: Manually fetching and untagging thousands of media items prior to deleting a collection in Plex causes 30-40s latency spikes, resulting in Next.js Server Action timeout errors (*"An unexpected response was received from the server"*).
   - Rule: Plex Media Server automatically cascades collection deletion to all items tagged with that collection in ~10ms. Always issue direct `DELETE /library/metadata/{ratingKey}` without pre-clearing tags.
6. **Hub Reordering & Visibility Timeouts**:
   - Use `PUT /hubs/sections/{sectionKey}/manage/{hubId}/move?after={afterHubId}` alongside locked `titleSort` prefixes for immediate, stable home screen positioning.
   - Concurrently dispatch visibility updates (`promotedToOwnHome`, `promotedToSharedHome`, `promotedToRecommended`) using `Promise.all` wrapped in 4s timeout guards (`AbortSignal.timeout(4000)`) to prevent single unresponsive endpoints from stalling execution.
7. **Automated Scheduler Execution, Mutex Locks & Telemetry Resilience**:
   - Agregarr curation sync runs automatically via `isScheduleDue()` in `src/lib/prisma.ts` evaluated against `agregarrSyncSchedule` (default `every_6_hours`) and `agregarrLastRunAt`.
   - Global concurrency lock `(global as any).__PORTALARR_AGREGARR_RUNNING` protects `runAgregarrSyncInternal` against simultaneous runs from background cron timers and manual admin triggers.
   - **Scheduler Mutex Ownership & Debouncing**: The background scheduler in `src/lib/prisma.ts` MUST NOT set `(global as any).__PORTALARR_AGREGARR_RUNNING = true` before calling `runAgregarrSyncInternal()`. `runAgregarrSyncInternal()` manages its own mutex lock. Setting it externally causes the function to immediately abort with "An Agregarr collection sync task is already in progress.", skip updating `agregarrLastRunAt`, and loop every 60 seconds. The scheduler updates `agregarrLastRunAt = now` immediately upon schedule trigger to debounce subsequent 60-second ticks.
   - If execution fails or Plex tokens are missing, `agregarrLastRunAt` and `agregarrLastRunStatus` are explicitly updated in `prisma.settings` (capturing error telemetry) to prevent infinite 60-second retry loops and surface error states directly in the UI.
   - Fixed daily, weekly Sunday, and monthly schedules enforce `lastRun && elapsedMs >= threshold` for catch-up, preventing fresh installations from prematurely triggering calendar-locked jobs outside their intended low-traffic maintenance window.
8. **Collection Title Truncation with Placeholders**:
   - Cause: Hardcoded `max-w-[200px]` constraints with `truncate` on collection title spans cause names like "Netflix Trending & Top Charts" to be cut off as "Netflix Trending & ..." when badges (e.g. `Placeholders: ON`, `Seasonal`, `Limit`) are enabled.
   - Rule: Let collection titles take natural width (`font-bold text-white text-xs sm:text-sm tracking-tight`) inside flex header containers so titles and status badges wrap cleanly without clipping.
9. **Custom Collection Media Type Isolation & Server ID Resilience**:
   - Custom collections created via `handleCreateCustomCollection` must dynamically inherit `type: isTvSection ? "show" : "movie"` from the active library section so TV collection queries match series models instead of movie models.
   - Server Actions (`getMediaCollectionsAction`, `deleteAllPlexCollectionsAction`, `syncSeasonalAndScheduledCollectionsInternal`) must resolve candidate server identifiers (`[serverId, resolved?.serverId, "main"]`) to ensure collections created under legacy `"main"` or discovered PMS machine identifiers are consistently retrieved and wiped without leaving orphaned records.
10. **Popular Media Native TMDb Resolution & MDBList Fallback**:
    - Cause: "Popular Movies" originally configured with `sourceType: "mdblist"` and `sourceQuery: "official/movies/popular"` returned 0 results whenever the user had not configured an external MDBList API key (or when MDBList rate limits/fails).
    - Rule: Popular movies & TV blueprints natively use `sourceType: "tmdb"` with `sourceQuery: "popular"` to query `getTmdbPopularMovies` / `getTmdbPopularTv` across multiple pages in parallel with zero external dependencies. For backward compatibility with existing databases, all MDBList resolution routines (`previewCollectionMatchingAction`, `syncCollectionToPlexAction`, `getCollectionMediaPreviewAction`, `runAgregarrSyncInternal`) automatically fall back to native TMDb popular media if MDBList returns empty.
11. **Anime & Crunchyroll Presets & Dedicated Studio Filter Chip**:
    - Agregarr equips dedicated anime presets: "Crunchyroll Trending Anime" (`sourceType: "tmdb"`, `sourceQuery: "provider:283"`, `mediaType: "both"`), "Crunchyroll Anime Series" (`sourceType: "tmdb"`, `sourceQuery: "network:1112"`), and the "🍙 Anime & Crunchyroll" category filter chip in Agregarr Studio (`agregarr-studio.tsx`).
12. **Dual Placeholder Labeling Convention (`Coming Soon-placeholder` vs `trailer-placeholder`)**:
    - Items monitored in Radarr/Sonarr receive the Plex label `Coming Soon-placeholder` with `edition: Trailer` and `DOWNLOADING SOON` or `COMING SOON MONITORED` banners.
    - General collection placeholders (e.g. Netflix Trending, Disney+, awards, studio charts) receive `trailer-placeholder` with `edition: Trailer` and `NOT REQUESTED YET` banners.
    - Filtered Smart Hubs filter out both `label!=Coming Soon-placeholder&label!=trailer-placeholder&editionTitle!=Trailer` to keep standard "Recently Added" rows clean while enabling dedicated "Coming Soon" hubs.
13. **Non-Blocking Background Preset Installation & Plex Concurrent Batch Syncing**:
    - **UI Unblocking**: When installing a curated preset (`handleInstallPreset`) or creating a custom collection (`handleCreateCustomCollection`), `saveMediaCollectionAction` persists to SQLite immediately (~15ms). The modal closes instantly (`setInspectModalOpen(false)`), allowing the user to continue browsing and installing other presets right away without waiting.
    - **Concurrent Multi-Sync Tracking**: Collections track active syncing state in `syncingCollIds: Record<string, boolean>`. Individual collection cards display spinning sync indicators, preset cards show `✓ INSTALLED` or `SYNCING TO PLEX` badges, and a floating glassmorphic toast notification alerts the user of background progress and item counts without blocking navigation.
    - **Plex Collection Single-URI Parameter Constraint & Concurrent Batching**:
      - **CRITICAL PMS HTTP CONSTRAINT**: Plex Media Server's REST API endpoint `PUT /library/collections/{collectionRatingKey}/items?uri=...` does **NOT** support duplicate parameter keys (e.g. `?uri=A&uri=B&uri=C`). PMS's HTTP request parser parses only the final `uri` parameter and drops all preceding ones, returning HTTP 200 OK while only adding a single item!
      - **Concurrent Batching Fix**: `syncPlexCollection` dispatches concurrent `Promise.all` batches of 10 items using individual `PUT .../items?uri={singleUri}` requests (with item metadata tagging fallbacks), adding 10 items in ~700ms with 100% item retention.
      - **Local Server Machine Identifier Matching & Library URI Fallback (`LPE: only library URIs are allowed right now`)**:
        - Plex Media Server REST API rejects cross-server URIs (`server://{different_machine_id}/...`) with `400 Bad Request` and logs `LPE: only library URIs are allowed right now. Failed to generate a query from uri server://...`.
        - `syncPlexCollection` dynamically resolves the exact machine identifier for each candidate base URL (`baseMachineIdMap.get(cleanBase)`), guaranteeing the URI matches the target server's local machine identifier.
        - If the server rejects the `server://` URI with 400 Bad Request, `syncPlexCollection` automatically retries with the local library URI scheme (`library:///item/%2Flibrary%2Fmetadata%2F{ratingKey}`) before falling back to direct item metadata tagging (`collection[0].tag.tag=...`), permanently preventing 400 Bad Request and LPE query failures across multi-server ecosystems.
      - **Concurrent Stale Item Purging**: `removeItemsFromPlexCollection` similarly uses concurrent `Promise.all` batches of 10 items calling `DELETE /library/collections/{collectionRatingKey}/items/{ratingKey}`.
    - **Active Scheduled Collection Item Sync Re-Triggering**:
      - In `runAgregarrSyncInternal`, active scheduled collections that already have a `ratingKey` must invoke `syncCollectionToPlexInternal` (for non-native/non-smart collections) to periodically refresh candidate item matches from upstream lists (TMDb genres/keywords, Trakt, Radarr/Sonarr) and prune stale items, rather than only updating sort promotion metadata.
14. **Genre & Keyword Discovery, Candidate Year Verification & Placeholder Exclusion**:
    - **Genre & Keyword TMDb Discover Queries**: Curation rules with `genre:<id>` (e.g. `genre:28` Action, `genre:27` Horror, `genre:10751` Family) and `keyword:<word>` (e.g. `keyword:christmas`, `keyword:halloween`, `keyword:superhero`) query TMDb Discover (`/discover/movie` and `/discover/tv`) sorted by `vote_count.desc` and popularity with high vote count minimums (`vote_count.gte=200` for genre, `100` for keyword). This prevents genre queries from falling back to generic weekly trending that returns obscure unreleased projects.
    - **Strict Release Year Verification on Title Matching**: When matching candidate items against local Plex libraries by title (when GUIDs are absent or unindexed), matching strictly enforces `Math.abs(libraryItem.year - candidate.year) <= 1` via `buildCandidateIndex` and `matchLibraryItemToCandidates` in `@/lib/curation/plex-analyzer`. This prevents legacy catalog movies (e.g. 2002 *Resident Evil*) from matching upcoming reboots/remakes (e.g. 2026 *Resident Evil*).
    - **Strict Placeholder & Trailer Stub Exclusion from Standard Collections**: Helper `isPlexItemPlaceholderOrStub` detects and excludes trailer stubs (duration < 15min, file size < 25MB, trailer editions/labels, `.portalarr-missing`, `.disc`, `.strm`) and future unreleased items (`year > currentYear`) from standard released movie and show collections unless `includePlaceholders: true` is explicitly enabled.
    - **Seasonal Active In-Season vs Out-of-Season Status Display**: UI components dynamically compute whether the current calendar date falls within the seasonal schedule window (`scheduleStartMonth/Day` to `scheduleEndMonth/Day`, correctly handling year-end rollover). Collections and presets outside their season (e.g. Summer Blockbusters in October) are styled with neutral out-of-season badges (`Out of Season (5/15 - 8/31)`) and excluded from active home screen promotion.
15. **Full Preset Catalog Audit, Franchise Mapping & Built-in Academy Award Fallback**:
    - **TMDb Franchise Universes (`franchise:mcu`, `franchise:dceu`, `franchise:starwars`)**: Rather than pointing to limited sub-collections (e.g. TMDb collection 86311 which only contains the 4 *Avengers* films), franchise presets query `franchise:<key>`. `getTmdbFranchiseMedia` queries company IDs (e.g. Marvel Studios `420`, DC Films `128064|429|9993`, Lucasfilm `1`) and universe keywords across movies and TV series across up to 3 pages in parallel, returning the complete cinematic universe filmography.
    - **Studio & Company Multi-Page Filmographies (`company:<id>`)**: `getTmdbStudioMovies` queries up to 3 pages in parallel (`maxPages = 3`), returning up to 60 titles. This prevents studios with large catalogs (e.g. Pixar `company:3` with 28+ films, Studio Ghibli `company:10342` with 25+ films) from being truncated to page 1 (20 items).
    - **Streaming Network Movie Section Originals (`network:<id>`)**: TMDb's `/discover/tv` `with_networks` endpoint only returns TV series. When a network preset (e.g. Netflix `network:213`, Disney+ `network:2739`, Apple TV+ `network:2552`, HBO `network:49`) is targeted to a Movie library section, `getTmdbNetworkOriginalMovies` transparently maps the network ID to its streaming provider equivalent and queries feature films.
    - **Built-in Academy Award Best Picture Winners Registry (`src/lib/curation/oscar-best-picture-data.ts`)**: Upstream MDBList charts (`top-oscar-best-picture`) require an external API key. To ensure 100% offline reliability, all 4 candidate resolution routines (`syncCollectionToPlexInternal`, `generateCollectionCandidateItemsPreviewAction`, `generateCollectionPlaceholdersInternal`, `getCollectionMediaPreviewAction`) fall back to `getBuiltinOscarBestPictureList()`, containing 96+ verified historical Oscar winners from *Oppenheimer* (2023) back to *Wings* (1927) with verified TMDb & IMDb IDs.
    - **Servarr Tag Query Standardization (`tag:<tagname>`)**: Tag collections use `sourceQuery: "tag:portalarr"`. Handlers verify the tag exists in Radarr (`/api/v3/tag`) and Sonarr; if the tag does not exist or has no tagged items, the candidate list defaults to empty (`[]`) rather than returning the entire media library.
16. **Trending Auto-Placeholders, Coming Soon Exclusion & Selective Placeholder Filtering**:
    - **Trending Presets Default Settings**: Presets tracking trending and anticipated media (`trending-this-week`, `netflix-trending`, `netflix-kids-trending`, `disney-trending`, `disney-kids-trending`, `crunchyroll-trending`, `trakt-anticipated-movies`, `trakt-anticipated-tv`, `tmdb-in-theatres`) default to `defaultIncludePlaceholders: true` and `defaultExcludedLabels: "Coming Soon-placeholder, coming_soon, leaving-soon"`. This ensures upcoming media automatically generates trailer stubs while excluding monitored Coming Soon items to avoid cluttering trending carousels with upcoming backlog.
    - **Coming Soon Presets Default Settings**: Servarr Coming Soon presets (`radarr-coming-soon`, `sonarr-coming-soon`) default to `defaultIncludePlaceholders: true` and `defaultExcludedLabels: "trailer-placeholder, trailers, leaving-soon"`. This keeps the hub focused strictly on items monitored for download in Radarr/Sonarr while suppressing general trending/collection trailer stubs.
    - **Selective Label & Tag Exclusion Engine (`isPlexItemExcludedByLabels` in `src/lib/curation/plex-analyzer.ts`)**:
      - Differentiates between Coming Soon stubs (`Coming Soon-placeholder`, `coming_soon`, `radarr_monitored`) and general collection trailer placeholders (`trailer-placeholder`, `trailers`, `collection`).
      - When `allowPlaceholders: true` is enabled, avoids wiping all placeholder-related tokens. If `hasComingSoonExclusion` is configured, only Coming Soon items are excluded; if `hasTrailerExclusion` is configured, only general trailer stubs are excluded.
      - In `generateCollectionPlaceholdersInternal`, checks `excludesComingSoonFromColl` to skip generating redundant trailer stubs for items already monitored in Radarr or Sonarr.
17. **Collection Update Priority Preservation & Plex Hub Ordering Integrity**:
    - **Preserve Existing Order on Updates**: Updating or re-inspecting an installed preset (`handleInspectPreset`, `handleInstallPreset`, `handleCreateCustomCollection`) preserves the collection's existing `orderIndex` and `sortPrefix` rather than appending to the bottom (`maxOrder + 1`). `saveMediaCollectionAction` resolves existing records by ID or title first and retains their priority rank.
    - **Non-Destructive Hub Promotion**: `updatePlexCollectionPromotionAndOrder` executes `PUT` visibility changes on canonical and fallback hub IDs before issuing `POST /hubs/sections/{sectionKey}/manage`. This prevents Plex Media Server from moving an already managed hub to the bottom of the home screen priority list.
    - **Sort Title Normalization & Compounding Prevention**: Sort titles strip duplicated or recursive prefix tags via `.replace(/^(![\d]+_)+/, "").trim()`, ensuring sort titles never compound into `!01_!01_Trending`.
    - **Selective Hub Reordering Synchronization**: When collection placement or contents update, `reorderPlexHubsSelective` synchronizes the home screen hub order in PMS to strictly match SQLite `orderIndex` ascending.
18. **Plex Direct HTTPS Enforcement, Private LAN IP Isolation & Robust Poster Uploads**:
    - **Strict HTTPS on `.plex.direct`**: Plex dynamic DNS domains (`*.plex.direct`) bind wildcard TLS certificates. Plain HTTP requests to `.plex.direct` ports trigger immediate TLS handshake termination (`ECONNRESET / fetch failed`). All candidate URL builders (`expandCandidateUrls` in `plex-analyzer.ts`, `addCandidate` in `plex.ts`) enforce `https://` and strictly forbid generating `http://` for `.plex.direct`.
    - **Private LAN vs. Public WAN IP Isolation (`isPrivateOrLocalIp`)**: Decoded IP addresses from `.plex.direct` are verified against private subnets (10.x, 172.16-31.x, 192.168.x, 127.0.0.1, link-local, Docker). Only verified private IPs are routed to `directLanList` / `directLanUrls`. Public WAN IPs (e.g. `162.231.214.194`) are strictly routed to `otherList` / `otherUrls` (WAN fallback), preventing local routers lacking NAT loopback/hairpinning from dropping connections.
    - **Confirmed Working Server URL Precedence**: `expandCandidateUrls` guarantees Candidate #0 is always the primary, verified server URL supplied by the caller.
    - **Portalarr-Buffered Poster Upload Strategy (`uploadPlexItemPosterFromUrl`)**: Rather than asking Plex Media Server to download external image URLs (which often fail due to PMS container DNS issues, VPN tunnels, or CDN User-Agent blocking on Unsplash/TMDb), Portalarr downloads the image buffer locally first using browser headers and streams the raw bytes via `uploadPlexItemPoster`. It locks the uploaded poster with `thumb.locked=1` and falls back to PMS `?url=` only if local buffer download fails.
19. **High-Performance Collection Sync & Batch Hub Reordering Optimization**:
    - **Direct Confirmed URL Prioritization (`urlsToTry = [serverUrl]`)**: In `syncCollectionToPlexInternal` and `syncSeasonalAndScheduledCollectionsInternal`, once `resolvePlexConnection` discovers a working connection (e.g. `http://192.168.1.66:32400`), it uses `urlsToTry = [serverUrl]` directly. Probing dozens of candidate endpoints (Docker bridges `172.18.x`, `172.19.x`, loopbacks `127.0.0.1`, `localhost`, WAN IPs) is eliminated, avoiding 15-20s timeout stalls per item.
    - **Section Collections In-Memory Caching (`cachedExistingCollections`)**: During multi-collection scheduled or seasonal syncs, `getPlexLibraryCollections` is executed once per section and cached in `sectionCollectionsCache`, preventing redundant full-library collection sweeps on every collection.
    - **Batch Home Screen Hub Reordering Deferral (`skipHubReorder`)**: Instead of triggering `reorderPlexHubsSelective` after every single collection in a batch (which previously caused 18 full hub reorder cycles across PMS), `syncCollectionToPlexInternal` accepts `skipHubReorder: true`. Home screen hub reordering is deferred and run exactly ONCE per affected library section at the end of the entire batch.
    - **Hub Initialization Short-Circuit**: In `reorderPlexHubsSelective`, candidate endpoint probing breaks immediately upon the first successful HTTP response (`if (res.ok) break;`), preventing trailing requests across unneeded fallback URLs.
    - **Universal Clipboard Helper (`copyToClipboard`)**: System and diagnostic activity streams utilize `copyToClipboard` in `src/lib/utils.ts` which uses modern `navigator.clipboard.writeText` on secure origins, and gracefully falls back to an offscreen DOM `textarea` with `document.execCommand('copy')` on non-secure LAN HTTP origins (e.g. `http://192.168.1.x:3000`).
20. **Seasonal Collection Out-of-Season Hiding, Shared Home Screen Enforcement & Schedule Synchronization**:
    - **Tri-Screen Visibility Enforcement**: Seasonal collections and scheduled hubs must consistently synchronize visibility across all three Plex screen surfaces:
      - `promotedToHome` (Server owner's Home screen, `promotedToOwnHome` in PMS API)
      - `promotedToSharedHome` (Shared friends & home members' Home screens)
      - `promotedToRecommended` (Library section Recommended screen)
    - **Shared Home Fallback Safeguard (`plex-analyzer.ts`)**:
      - In `updatePlexCollectionPromotionAndOrder`, `sharedVal` safely defaults to `options.promotedToHome` (or `"1"` if both are undefined) rather than unconditionally setting `"1"`. This prevents out-of-season collections from leaking onto shared users' home screens when callers omit `promotedToSharedHome`.
    - **Out-of-Season Automatic Demotion & Hub Hiding**:
      - `isSeasonalCollectionInSeason` and `isCollectionScheduleActive` in `curation-actions.ts` calculate calendar dates (`curMonth * 100 + curDay`) against seasonal start and end dates with year-end rollover support (e.g. Nov 20 to Jan 6 for Holiday Cheer).
      - When an active collection is out of season (e.g. Summer Blockbusters, Holiday Cheer, Thanksgiving in October), all sync and reorder operations (`syncCollectionToPlexInternal`, `runAgregarrSyncInternal`, `syncSeasonalAndScheduledCollectionsInternal`, `updateCollectionPlacementAction`, `reorderPlexCollectionsAction`) enforce `promotedToHome = false`, `promotedToSharedHome = false`, `promotedToRecommended = false`, and `collectionMode = "hide"` (when `seasonalAction === "promote_hide"` or `"create_delete"`).
      - Database records in SQLite `MediaCollection` are persisted with `false` across all three visibility fields (`promotedToHome`, `promotedToRecommended`, `promotedToSharedHome`), preventing subsequent manual, preset, or background sync sweeps from re-promoting inactive seasonal collections to Plex hubs.


