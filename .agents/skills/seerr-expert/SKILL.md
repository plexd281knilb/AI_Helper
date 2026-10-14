---
name: seerr-expert
description: Expert architectural, API, and operational guide for Seerr (Overseerr / Jellyseerr media request management, discovery carousels, user quotas, auto-approval rules, Radarr/Sonarr dispatch, and Plex/Jellyfin availability synchronization). Activate when integrating with the Seerr/Overseerr REST API, managing media requests, configuring user permissions, or troubleshooting Servarr dispatch workflows.
---

# Seerr Expert Guide

Seerr (Overseerr / Jellyseerr) is an open-source media discovery and request management platform for Plex, Jellyfin, and Emby ecosystems. It allows users to browse trending, popular, and upcoming movies/shows via TMDb, submit requests, and automatically coordinates approvals, user quotas, and dispatching to Radarr and Sonarr download managers.

Primary Reference Repositories & Modules:
- Directory: [seerr-develop](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop)
- OpenAPI Specification: [seerr-api.yml](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/seerr-api.yml)
- Server Source: [server/](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/server)
- Entity Definitions: [server/entity/](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/server/entity)
- API Routes: [server/routes/](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/server/routes)
- Portalarr Native Request Engine: [src/app/actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/actions.ts)

---

## Architecture & Codebase Layout

```text
seerr-develop/
├── server/
│   ├── api/                         # Upstream clients (TMDb, TVDb, Radarr, Sonarr, Plex, Jellyfin)
│   ├── entity/                      # TypeORM entities (MediaRequest, Media, User, OverrideRule, Watchlist)
│   ├── routes/                      # REST API routes (request, media, discover, movie, tv, search)
│   ├── subscriber/                  # MediaRequestSubscriber (dispatches approved requests to Radarr/Sonarr)
│   ├── lib/
│   │   ├── availabilitySync.ts      # Periodic background sync matching Plex/Jellyfin library files
│   │   ├── permissions.ts           # Integer bitflag permission evaluator
│   │   ├── downloadtracker.ts       # Active download queue listener
│   │   └── notifications/           # Multi-channel notification engine (Discord, Slack, Pushbullet, Email)
│   └── datasource.ts                # SQLite / Postgres persistence config
└── src/                             # Next.js / React frontend
```

---

## Core Capabilities & Runbooks

### 1. REST API & Request Lifecycle
Seerr provides full request lifecycle management authenticated via `X-Api-Key`:
- **Submit Request**: `POST /api/v1/request` (checks permissions, user quotas, duplicate requests, and blocklists).
- **Approve / Decline / Retry**: `POST /api/v1/request/{id}/approve`, `POST /api/v1/request/{id}/decline`, `POST /api/v1/request/{id}/retry`.
- **Permissions Bitmask**: Granular permissions (`REQUEST`, `AUTO_APPROVE`, `REQUEST_4K`, `MANAGE_REQUESTS`, `ADMIN`).

See detailed runbook: [api-v1-endpoints.md](./references/api-v1-endpoints.md).

### 2. Servarr Dispatch & Override Rules
When requests are approved:
- **`MediaRequestSubscriber`**: Dispatches movie payload to Radarr or series payload to Sonarr.
- **`OverrideRule`**: Dynamically assigns custom quality profiles, root paths, or tags based on language (e.g. Japanese anime -> `/data/anime`), genres, or keywords.
- **`AvailabilitySync`**: Periodic scanner checks Plex/Jellyfin libraries to flip media to `AVAILABLE` and notifies the requester.

### 3. Granular TV Episode Monitoring & Deep Arr Inspection
Portalarr's native Seerr engine features deep per-episode monitoring synchronization:
- **Episode Mapping**: Queries `/api/v3/episode?seriesId={id}` on target Sonarr instances to construct a per-episode map (`s{season}e{episode}`) tracking monitored and on-disk file availability for both 1080p and 4K instances.
- **Season Status Reconciliation**: Compares `monitoredEpisodeCount` against `totalEpisodeCount` to flag seasons as `isFullyMonitored`, `isPartiallyMonitored`, or `Unmonitored`.
- **Targeted Episode Grabs**: Allows users to select individual unmonitored episodes or unmonitored seasons, dispatching `/api/v3/episode/monitor` and triggering `EpisodeSearch` commands without redundant series re-imports.

### 4. Multi-Channel Notification Engine (Discord Webhooks & HTML Emails)
- **Discord Webhook Cards**: Dispatches embed cards for `PENDING`, `AUTO_APPROVED`, `APPROVED`, `DECLINED`, `AVAILABLE`, and `FAILED` events. Embeds feature poster artwork, format badges (🎬 MOVIE vs 📺 TV SERIES, 4K UHD vs 1080p), requester username, season counts, and direct action links.
- **Rich HTML Emails**: Sends branded HTML emails via SMTP for admin approval alerts and user status updates, using dynamic public host resolution (`getAppUrl()`).

### 5. Automated Background Queue & Availability Reconciliation
- **Unauthenticated Internal Runner (`syncMediaRequestsQueueAndAvailabilityInternal`)**:
  - Called every 2 minutes by the background scheduler in `src/lib/prisma.ts`.
  - Reconciles active requests (`PROCESSING`, `APPROVED`, `PENDING`) against the Plex library GUID index.
  - Queries `/api/v3/queue?page=1&pageSize=1000` on enabled Radarr and Sonarr instances to compute exact download progress percentages:
    $$\text{progress} = \max\left(1, \min\left(99, \text{round}\left(\frac{\text{size} - \text{sizeleft}}{\text{size}} \times 100\right)\right)\right)$$
  - Updates requests to `AVAILABLE` with `100%` progress when media is detected on PMS.

### 6. Kids Profile Isolation & Filtered Media Discovery
- **Safe Content Enforcements**: Kids searches and carousels pass `include_adult=false`, enforce TMDb certification ratings (`G`, `PG`, `TV-Y`, `TV-Y7`, `TV-G`, `TV-PG`), and filter out adult keywords.
- **Isolated Library Matching**: Kids views verify library availability strictly against kids-specific Plex libraries rather than unrestricted main adult libraries.
- **Book Age & Maturity Rating Engine (`inferBookRating`)**:
  - Deterministically evaluates publisher taxonomy (Google Books `volumeInfo.maturityRating` & `volumeInfo.categories` BISAC headings, Open Library `doc.subject`, Audible genres, and iTunes media tags).
  - Assigns standardized age brackets: `"Kids"` (emerald), `"YA (12+)"` (sky), `"All Ages"` (slate), and `"18+ Mature"` (rose).
  - Flags mature indicators (`"MATURE"` vs `"NOT_MATURE"`) from explicit publisher labels and adult/erotica keywords.
  - **Kids Mode Filtering & Request Guard**: Whenever in Kids section mode (`section === "kids"`) or logged in under a child profile (`accountType === "KID"`), mature titles (`isMature === true` or `"18+ Mature"`) are completely omitted from trending ebooks/audiobooks, search results, missing series carousels, and `/library` shelf browsing. Attempting to submit a mature book request in Kids mode or under a kid profile is blocked at both client and server action levels (`submitBookOrAudiobookRequestAction`).
  - **Kids Request Mandatory Admin Approval Gating**: All book and audiobook requests targeted for kids (identified via kids mode, child account profile, `ageRating === "Kids"`, target kids library evaluated via `isKidsLibrary`, or inferred age rating) are strictly saved with `status: "Pending"` (`BookRequest`) and `"PENDING"` (`MediaRequest`). They are barred from immediate auto-approval and auto-downloading until an administrator explicitly reviews and approves them via `approveBookRequestAction`. The periodic background scheduler (`src/lib/prisma.ts`) actively skips pending kids requests during auto-approval sweeps.
  - **Badge Display**: Color-coded age rating badges are rendered across discovery cards (`BookCard`), media details (`BookDetailModal`), and library shelf cards (`renderBookCard` and `renderAudiobookCard`).

### 7. Unified Multi-Media Pipeline (Movies, TV, Ebooks & Audiobooks)
Portalarr's native Seerr engine unifies all media types into a single mission control request registry (`/requests` and `/discover`):
- **Cross-Format MediaRequest Model**: Supports `mediaType: "movie" | "tv" | "book" | "audiobook" | "ebook"`.
- **Nullable `tmdbId` for Books & Audiobooks**: Non-TMDB media identifiers use `openLibraryId`, `googleBooksId`, `asin`, `bookAuthor`, `bookSeries`, and `bookVolume`, with `tmdbId` explicitly nullable (`Int?`).
- **Missing from Your Series Discovery**: Discovered unacquired installments from the user's book and audiobook series automatically surface in the *Seerr discovery feed as high-priority suggestions.
- **Bi-Directional Request Mirroring**: `syncMediaRequestsQueueAndAvailabilityInternal` periodically reconciles legacy `BookRequest` records into `MediaRequest`, synchronizing download progress and availability states.

### 8. US-First Domestic Priority & Typo-Tolerant Search Engine
- **Search Relevance & Typo Problem**: TMDb's default keyword searches return results primarily by raw token match and fail completely on misspellings (e.g. `oppenhiemer`, `gladiater`, `stranger thngs`, `breaking bag`, `interstelar` return 0 results). Obscure, low-vote international releases also frequently displace iconic US blockbusters.
- **US Domestic & English Priority Algorithm** (`src/lib/curation/tmdb.ts`):
  Each search candidate is evaluated and sorted by a weighted score prioritizing US domestic releases:
  - **US Domestic Boost (+300 pts)**: Awarded when `originCountry.includes("US")` or when `originalLanguage === "en"` with no foreign origin country.
  - **English Language Boost (+200 pts)**: Awarded when `originalLanguage === "en"`.
  - **US Certification Boost (+50 pts)**: Awarded for standard US MPAA/TV ratings (`G`, `PG`, `PG-13`, `R`, `NC-17`, `TV-14`, `TV-MA`).
  - **Foreign Obscurity Penalty (-300 pts)**: Heavily suppresses non-English, non-US releases with low vote counts (<1,000 votes) to prevent obscure foreign titles from polluting US user searches.
- **Typo Tolerance & Spell-Correction Engine**:
  - **Dual-Query Search**: In parallel with the raw query, `getSpellingSuggestion` executes a fast US-biased spellcheck. If a typo is detected (e.g. `oppenhiemer` -> `oppenheimer`, `gladiater` -> `gladiator`), TMDb queries both queries in parallel across `/search/multi`, `/search/movie`, and `/search/tv`.
  - **Levenshtein Fuzzy Matching**: Calculates string similarity ratios (`stringSimilarityRatio`). Typo matches (similarity $\ge 0.80$–$0.90$) receive $+600$ to $+850$ match points, ensuring the intended blockbuster surfaces at #1 even if misspelled.
  - **Unified Books Fallback**: `searchBooksUnified` automatically falls back to `getSpellingSuggestion` when raw book/author searches yield 0 results.

### 9. Unified Branding & Mobile Search Input Responsiveness
- **Standardized Naming**: All navigation bars, breadcrumbs, page titles, and sidebars standardize on **"Media Requests"** (retiring fragmented labels like "Discovery & Requests").
- **Responsive Search Input Sizing**: On mobile screens, search inputs without flex width wrappers collapse to illegibly small widths. Always style request search inputs with `w-full max-w-full sm:w-[320px] md:w-[420px]` within `flex-wrap gap-2` toolbars.

### 10. High-Performance Multi-Tier Caching & Instant Tab Switching Engine
To achieve sub-second page loads and eliminate blank-screen flashing on tab changes:
- **Server-Side In-Memory Discovery Caches**:
  - `discoverHomeCache`: Stores curated hero spotlights and category sections per section mode (`main` vs `kids`) with a 5-minute TTL. Availability checks run dynamically against SQLite/Arr in ~5ms.
  - `discoverMediaCache`: Caches paginated category grids (`trending`, `popular`, `upcoming`, `top_rated`) keyed by `${category}:${mediaType}:${page}:${isKids}` with a 5-minute TTL. Primes `popular:movie:1` and `popular:tv:1` during `getDiscoverHomeAction` so default grid tabs execute in 0ms directly from RAM.
  - `mediaSearchCache` & `booksSearchCache`: Caches full-text search results for 5 minutes, preventing redundant upstream API calls when users re-search or navigate back.
  - `mediaDetailsCache`: Caches TMDb full movie/TV metadata for 10 minutes. Deep Arr and recommendations availability run concurrently via `Promise.all([checkMediaAvailability, batchCheckMediaAvailability])`.
  - `certificationCache`: In-memory cache for US content certifications with a 24-hour TTL in `src/lib/curation/tmdb.ts`, eliminating repetitive HTTP requests to TMDb release dates/content ratings.
  - `cachedApiKey`: In-memory cache for TMDb API key with a 5-minute TTL to prevent redundant SQLite queries on high-throughput media operations.
  - `inFlightPlexPromise` & `inFlightArrPromise`: In-flight Promise deduplication in `getPlexLibraryGuidIndex` and `getArrIndex` ensures that concurrent requests share the exact same background indexing run, preventing duplicate full Plex/Radarr/Sonarr sweeps.
  - `CACHE_TTL_MS` & `ARR_CACHE_TTL_MS`: Extended cache retention of 15 minutes for Plex GUID index and Arr monitoring index with AbortSignal timeouts (8s–10s) on individual server sockets.
  - `trendingEbooksCache` & `trendingAudiobooksCache`: Caches OpenLibrary, Google Books, and Audible trending works with a 15-minute TTL in `src/lib/books/book-service.ts`.
  - `missingSeriesCandidatesCache`: Caches discovered series volumes with a 30-minute TTL in `findMissingBooksInSeries`, eliminating up to 15 sequential external API calls during library scans and home loads.
  - `reconcileBookRequestsWithMediaRequests`: Throttled to a 30-second interval (`Date.now() - lastReconcileTime < 30_000`) so repeated request listing queries execute immediately without running SQLite PRAGMA table audits or 300-row updates, with a `force = true` bypass for manual syncs and new request submissions.
- **Client-Side Stale-While-Revalidate Tab Caching (`tabCacheRef`) & Background Pre-Warming**:
  - `DiscoverHub` maintains an in-memory ref caching previously visited tabs (`discover`, `movies`, `tv`, `ebooks`, `audiobooks`).
  - Background Tab Pre-warming: Silently pre-loads `movie:popular:1` and `tv:popular:1` tabs into `tabCacheRef.current.grid` 80ms after Browse loads, making the very first click on "Movies" or "TV Shows" 100% instant (0ms, zero spinner).
  - Race Condition Guards: Tracks `activeTabRef` to ensure that fast switching between "Movies" and "TV Shows" never allows older in-flight promises to overwrite the active tab's grid items.
  - Switching between tabs instantly displays cached data with `0ms` latency (zero loading spinner, zero screen flicker), then revalidates in the background if older than 2 minutes.
  - Search debounce is optimized to `350ms` for fluid responsiveness. Searches on `movies` and `tv` tabs strictly query TMDb media without firing redundant book APIs, while `ebooks` and `audiobooks` tabs strictly query book registries.
- **Request Manager Module-Level Cache**:
  - `RequestManager` initializes from `cachedRequests` to render previous request listings instantly when switching between Discover and Requests tabs.
  - `filteredRequests` and status `counts` are memoized via `useMemo` for lag-free typing in large request catalogs.
- **Verification & Soak Testing Timing Tolerances**:
  - When verifying primed in-memory cache pre-warming (such as Test 50 in `scripts/verify-all.ts`), server action execution includes local availability evaluations (`batchCheckMediaAvailability`) iterating over media items.
  - Uncached TMDb network calls require 1,500ms–3,500ms; primed cache execution completes in ~10–130ms depending on background CPU load and GC sweeps. Timing assertions enforce a sub-second threshold (`< 250ms`) rather than micro-benchmarks (`< 60ms`) to guarantee 100% soak test reliability under heavy system stress without masking uncached network calls.

---

## Common Gotchas & Troubleshooting

1. **Request Stuck in "Approved" Without Reaching Radarr/Sonarr**:
   - Cause: Radarr/Sonarr server settings misconfigured (invalid API key, unreachable hostname), or no default server was flagged.
   - Fix: Check `MediaRequest.status`. If `FAILED`, inspect server connection settings, ensure port and URL base match, and click `/retry`.
2. **Trailer Placeholders Falsely Flagged as "In Library"**:
   - Cause: Agregarr placeholder video stubs matching the TMDb/IMDb ID of an upcoming movie exist in Plex.
   - Fix: Availability indexer (`getPlexLibraryGuidIndex`) must explicitly exclude items tagged with `trailer-placeholder` label or `editionTitle === "Trailer"`.
3. **Duplicate Request Error (HTTP 409)**:
   - Cause: Another user already submitted a request for this TMDb ID or season.
   - Fix: Seerr blocks duplicate requests. The UI attaches multiple users to the existing `Media` record instead.
4. **4K vs Standard Media Isolation & Strict Gating**:
   - 4K Radarr and Sonarr instances must strictly resolve only when explicitly configured in settings (`seerrDefaultMovie4kAppId` / `seerrDefaultTv4kAppId` !== `"none"`).
   - When 4K is set to "Disabled / Don't Use", always fallback cleanly to standard 1080p and gate UI 4K checkboxes behind `canRequest4k = Boolean(quotaData?.canRequest4k && arrDetails?.isConfigured4k)`.
5. **Trial Account Quota Sliding Window**:
   - Quotas for trial accounts are calculated over the user's active trial window defined in Access Control, rather than an arbitrary rolling window.
6. **Radix Dialog `sm:max-w-lg` Tailwind Specificity**:
   - Radix `DialogContent` includes `sm:max-w-lg` in base classes. Passing an unprefixed `max-w-6xl` fails to override `sm:max-w-lg` during `tailwind-merge`.
   - Pass explicit prefixed responsive classes (`sm:max-w-4xl md:max-w-5xl lg:max-w-6xl xl:max-w-7xl 2xl:max-w-[1500px] w-[96vw] sm:w-[94vw] md:w-[92vw] lg:w-[90vw] xl:w-[86vw] 2xl:w-[82vw]`) to render wide, spacious modals for TV series episode guides and cast grids.
7. **SQLite `PRAGMA table_info` BigInt Gotcha on Table Rebuilds**:
   - In Prisma with SQLite, `prisma.$queryRawUnsafe("PRAGMA table_info(...)")` returns column integer metadata (`notnull`, `pk`) as JavaScript `BigInt` (e.g. `1n`). Strict equality `col.notnull === 1` returns `false`, causing table constraint migrations (like relaxing `tmdbId` to nullable) to be skipped. Always check `Number(col.notnull) === 1 || col.notnull == 1` and execute `DROP TABLE IF EXISTS "Table_migrating";` before staging new tables.
8. **App Router Deep-Link Tab Desync & Hydration Alignment**:
   - For pages embedding multi-tab discover/request hubs (`/discover`), server page components (`page.tsx`) must resolve `searchParams: Promise<{ tab?: string; section?: string }>` and pass down `initialTab` and `initialSection` wrapped within `<Suspense>`. Client components must consume `useSearchParams()` and reflect state back to the URL with `window.history.replaceState` or `router.replace`.
9. **Online Book Registry (OpenLibrary, Audible, Google Books) Resilience**:
   - OpenLibrary searches MUST pass lightweight field projections (`&fields=key,title,author_name,cover_i,first_publish_year`) and a valid application `User-Agent` (`Portalarr/3.0 ...`) to avoid Cloudflare/undici connection drops and rate limits.
   - Batch lookups (such as series discovery) must run concurrently via `Promise.allSettled` and use bounded `AbortController` timeouts to guarantee sub-second page responses.
10. **Redundant Schema Columns Audits on Fast Polling**:
   - Calling `ensureSchemaColumns()` on high-frequency routes (like requests or availability sync) triggers expensive SQLite metadata queries. Throttle background reconciliation passes (`reconcileBookRequestsWithMediaRequests`) to $\ge 30$ seconds to keep request browsing sub-second.
11. **Book Age & Maturity Rating Engine & Romance Guards (`inferBookRating`)**:
   - Evaluates multi-source publisher metadata (Google Books `maturityRating` & BISAC `categories`, OpenLibrary `subjects`, Audible `category_ladders`, iTunes `primaryGenreName`) and assigns standardized ratings: `"Kids"`, `"YA (12+)"`, `"All Ages"`, or `"18+ Mature"`.
   - **Known Spicy Authors & Series Registry**: Integrates curated regular expressions (`KNOWN_SPICY_AUTHORS_REGEX` and `KNOWN_SPICY_SERIES_REGEX`) covering over 60 spicy romance and dark fiction authors (e.g., Elsie Silver, Colleen Hoover, Ana Huang, Penelope Douglas, Ali Hazelwood, Tessa Bailey, Lauren Asher, Lucy Score, Meghan Quinn, H.D. Carlton, Shantel Tessier, Sylvia Day, E.L. James, Sarah J. Maas, Rebecca Yarros) and series (*Gold Rush Ranch*, *Chestnut Springs*, *Twisted*, *Kings of Sin*, *Dreamland Billionaires*, *Cat and Mouse Duet*, *ACOTAR*, *Fourth Wing*). These authors/series are strictly evaluated as `"18+ Mature"` with `maturityRating: "MATURE"` and `isMature: true`.
   - **Adult Romance Tropes & Category Guards**: Steamy tropes (`steamy`, `spicy`, `high heat`, `spice level`, `open door`, `dirty talk`, `cowboy romance`, `western romance`, `ranch romance`, `billionaire romance`, `mafia romance`, `reverse harem`, `enemies to lovers`, `forced proximity`, `grumpy sunshine`) guarantee an `"18+ Mature"` rating. Mainstream romance categories without explicit children or YA classifications default to `"18+ Mature"`, preventing spicy novels from ever defaulting to `"All Ages"`.
   - **Multi-Layer Kids Isolation & Auto-Repair**: Books rated `"18+ Mature"` or `maturityRating === "MATURE"` are completely hidden from Kids mode (`section === "kids"`) and child profiles (`accountType === "KID"`), and mature request submissions from children are actively rejected. Existing database items with stale `"All Ages"` ratings are dynamically re-evaluated and healed upon retrieval in `getBooks` and during library scans in `scanLibraryInternal`.
12. **Mass / Bulk Action Operations & Anti-Resurrection Cascade Synchronization**:
   - **The Resurrection Bug & Root Cause**: When book/audiobook requests were submitted, rows were created in both `prisma.bookRequest` and `prisma.mediaRequest`. Deleting a request via the web UI previously only deleted the `MediaRequest` row, leaving `BookRequest` intact. When hitting refresh or when the background runner ran `reconcileBookRequestsWithMediaRequests()`, it found the orphan `BookRequest`, saw no corresponding `MediaRequest`, and automatically recreated the `MediaRequest` row.
   - **Two-Way Cascade Deletion Contract**:
     - `deleteMediaRequestAction(requestId)` & `bulkDeleteMediaRequestsAction(requestIds)`: When deleting book/audiobook requests, queries and permanently deletes matching `prisma.bookRequest` records (matching `cleanTitle`, `cleanAuthor`, `requestedBy`, and `mediaType`). When deleting 4K media items, cascades deletion to companion 1080p child requests (`isDual1080pChild: true`, `parent4kRequestId`) and vice-versa.
     - `deleteBookRequest(id)` in `src/app/actions.ts`: Reciprocally cascades deletion to matching `prisma.mediaRequest` records.
     - Guarantees permanent deletion so refreshing the page, changing tabs, or triggering background sync sweeps NEVER resurrects deleted requests.
   - **Bulk Actions Architecture**:
     - `bulkApproveMediaRequestsAction(requestIds: string[])`: Bulk approves requests in one operation, dispatches to Radarr/Sonarr/Book downloaders, synchronizes linked `BookRequest.status` to `"Approved"`, and triggers webhooks.
     - `bulkDeclineMediaRequestsAction(requestIds: string[], reason?: string)`: Sets `MediaRequest.status = "DECLINED"`, synchronizes matching `BookRequest.status = "Rejected"`, and enforces Anti-Reversion so `reconcileBookRequestsWithMediaRequests()` preserves the decline state without reverting back to `"PENDING"`.
     - `bulkDeleteMediaRequestsAction(requestIds: string[])`: Executes mass two-way cascade deletion across target IDs.
   - **Safe Revalidation**: Wraps Next.js route cache revalidation in `safeRevalidatePath` to prevent `Invariant: static generation store missing in revalidatePath` crashes in test runners and cron workers.


13. **Dual-Tier Persistent Media Caching & Pre-Warming Engine (`src/lib/seerr/media-cache.ts`)**:
    - **Dual-Tier Cache Architecture**: Pairs ultra-fast RAM Tier 1 (`Map`) with persistent filesystem JSON Tier 2 (`data/cache/tmdb/`), mirroring Overseerr's snappy instantaneous page responses even across cold server reboots. `setMediaCache` writes to RAM and awaits `writeDiskCache` to guarantee atomic persistence on disk before resolving.
    - **Stale-While-Revalidate (SWR) Engine**: Automatically delivers stale data immediately in <5ms while refreshing upstream TMDb/TVDb APIs asynchronously in background threads.
    - **In-Flight Stampede Deduplication**: Coalesces identical concurrent upstream requests into a single promise, completely eliminating redundant network calls.
    - **Automated Pre-Warming Runner**: `prewarmDiscoverCachesInternal` triggers 10 seconds post-boot and every 30 minutes in `src/lib/prisma.ts` to pre-populate trending, popular, upcoming, and kids media categories.
    - **Persistent Cache Pruning**: `pruneExpiredDiskMediaCache` automatically purges disk cache files older than 7 days, maintaining clean disk usage.

14. **Audiobook Poster Resolution, Corrupted URL Auto-Healing & Explicit Content Suppression**:
    - **Poster Resolution & `?lib=` Sanitization**: Removed legacy bug where missing covers generated `?lib=${libraryId}` values in `BookRequest.coverUrl` and `MediaRequest.posterPath`. Added proactive high-definition cover resolution in `submitBookOrAudiobookRequestAction` querying `fetchBookCover(title, author, mediaType)`.
    - **Automatic Poster Healing**: `reconcileBookRequestsWithMediaRequests` detects missing or `?lib=` corrupted poster paths and auto-heals them from linked `BookRequest.coverUrl` or multi-source lookups.
    - **Comprehensive Mature Registry (`KNOWN_SPICY_AUTHORS_REGEX`, `KNOWN_SPICY_SERIES_REGEX`, `MATURE_KEYWORDS_REGEX`, `isExplicitSexOrErotica`)**:
      - **Sex Manuals & Sexual Non-Fiction**: Anne Hooper, Alex Comfort (*The Joy of Sex*), Tracey Cox (*Supersex*, *Hot Sex*), Ian Kerner (*She Comes First*, *He Comes Next*), Emily Nagoski (*Come as You Are*), Mantak Chia (*The Multi-Orgasmic Man*), Lou Paget, Betty Dodson (*Sex for One*), Dossie Easton & Janet Hardy (*The Ethical Slut*), Esther Perel (*Mating in Captivity*), Paul Joannides (*Guide to Getting It On*), Christopher Ryan (*Sex at Dawn*), Vatsyayana (*Kama Sutra*), Kalyana Malla (*Ananga Ranga*), Sheikh Nefzawi (*The Perfumed Garden*).
      - **Classic & Literary Erotica**: Marquis de Sade (*120 Days of Sodom*, *Justine*), Leopold von Sacher-Masoch (*Venus in Furs*), Pauline Réage / Anne Desclos (*Story of O*), Anaïs Nin (*Delta of Venus*, *Little Birds*), Henry Miller (*Tropic of Cancer*, *Sexus*), John Cleland (*Fanny Hill*), Georges Bataille, Catherine Millet, Giacomo Casanova, Nicholson Baker, Alina Reyes, Virginie Despentes.
      - **Viral Dark Romance, Mafia & Taboo**: H.D. Carlton (*Haunting Adeline*), Shantel Tessier (*The Ritual*, *L.O.R.D.S.*), Penelope Douglas (*Corrupt*, *Punk 57*, *Credence*), Rina Kent (*God of Malice*, *Legacy of Gods*), RuNyx (*The Predator*, *Dark Verse*), Brynne Weaver (*Butcher & Blackbird*), Emily McIntire (*Hooked*, *Never After*), Harley Laroux (*Her Soul to Take*), Sam Mariano, Kitty Thomas, K.G. Reuss, Somme Sketcher, Michelle Heard, Neva Altaj, Sophie Lark, Cora Reilly, Danielle Lori, J.T. Geissinger, Jagger Cole, Eva Winners, Nicole Fox, Tracy Lorraine, Callie Rose, Tate James, Caroline Peckham & Susanne Valenti (*Zodiac Academy*), C.M. Stunich, Amo Jones, Pepper Winters, Pam Godwin, Penelope Sky, Jade West.
      - **High-Heat Erotic Romance & Smut**: Sierra Simone (*Priest*), Katee Robert (*Neon Gods*, *Dark Olympus*), Nikki Sloane (*The Pool Boy*, *The Architect*), Tiffany Reisz (*The Siren*), Tara Sue Me (*The Submissive*), Beth Kery, R.K. Lilley, J. Kenner, Meredith Wild, C.D. Reiss, Shayla Black, Cherise Sinclair (*Masters of the Shadowlands*), Lexi Blake, Lora Leigh, Joey W. Hill, Robin Schone, Zane, Megan Hart, Alexa Riley, Jessa Kane, Lucy Darling, Fiona Davenport, Jordan Silver, Ella Goode.
      - **Monster Smut, Romantasy & Paranormal**: Ruby Dixon (*Ice Planet Barbarians*), C.M. Nascosta (*Morning Glory Milking Farm*), Kathryn Moon (*A Lady of Rooksgrave Manor*), Lillian Lark, Finley Fenn (*Orc Sworn*), Zoey Draven (*Horde Kings*), Colette Rhodes, Kimberly Lemming, Mallory Dunlin, Heather Guerre, Suzanne Wright, Christine Feehan, J.R. Ward (*Black Dagger Brotherhood*), Kresley Cole, Gena Showalter, Nalini Singh, Laurell K. Hamilton (*Anita Blake*), Sherrilyn Kenyon, Lara Adrian, Donna Grant, Larissa Ione, Tiffany Roberts, Lily Mayne, C.S. Pacat, Alessandra Hazard, Raven Kennedy (*The Plated Prisoner*), Sarah J. Maas (*ACOTAR*, *Crescent City*), Rebecca Yarros (*Fourth Wing*), Jennifer L. Armentrout (*Blood and Ash*), Carissa Broadbent.
      - **Explicit Sexual Acts, Tropes & Library Taxonomy**: Cunnilingus, fellatio, blowjob, handjob, anal/oral sex, deepthroat, pegging, rimming, creampie, ejaculation, squirting, cumming, moresome, threesome, gangbang, orgy, swingers, cuckold, hotwife, dub-con, non-con, consensual non-consent, somnophilia, primal play, omegaverse, knotting, breeding/praise kink, degradation, chastity, shibari, sex instruction, human sexuality, sexual behavior, BISAC `FICTION / Erotica` (`FIC005000`), `FICTION / Romance / Erotic` (`FIC027010`), `FICTION / Romance / Dark Romance` (`FIC027560`).
    - **Standardized Maturity Evaluation (`inferBookRating`)**: Evaluates all explicit sex guides, adult manuals, dark romance, and erotica strictly as `18+ Mature` with `maturityRating: "MATURE"`.
    - **Maturity Badge Streamlining**: Suppresses redundant "All Ages" badges from media cards in `BookCard`, reserving visible badges strictly for `Kids`, `YA (12+)`, and `18+ Mature`.
