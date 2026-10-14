# Agregarr Placeholder & Stub Engine Reference

This document details how Agregarr and Portalarr generate, track, discover, tag, and clean placeholder media files for unreleased or missing items in Plex libraries.

Reference source files:
- [placeholderManager.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/placeholders/placeholderManager.ts)
- [PlaceholderDiscovery.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/placeholders/services/PlaceholderDiscovery.ts)
- [PlaceholderCleanup.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/placeholders/services/PlaceholderCleanup.ts)
- [trailerDownload.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/placeholders/trailerDownload.ts)
- [PlaceholderItem.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/entity/PlaceholderItem.ts)
- [curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)

---

## 1. Placeholder File Architecture

When a collection rule is configured with `createPlaceholdersForMissing: true`, placeholder video or stub files are written directly to disk within the target Plex library folder or dedicated Coming Soon share.

### Movies
- **Folder Structure**: `{libraryPath}/{SanitizedTitle} ({Year})/`
- **File Formats**:
  - `{SanitizedTitle} ({Year}) {tmdb-{tmdbId}} {edition-Trailer}.mp4`
  - `{SanitizedTitle} ({Year}) {tmdb-{tmdbId}} {edition-Trailer}.disc`
  - `{SanitizedTitle} ({Year}) {tmdb-{tmdbId}} {edition-Trailer}.strm`
- **Plex Matching Mechanism**:
  - The `{tmdb-12345}` bracket tag forces Plex's Movie Agent (Plex Movie) to instantly match the metadata against TMDb ID `12345`.
  - The `{edition-Trailer}` tag marks the file as a special edition/trailer in Plex, preventing duplicate merges with the main movie if later imported.

### TV Shows
- **Folder Structure**: `{libraryPath}/{SanitizedTitle} ({Year})/Season 00/`
- **File Format**: `S00E00.Trailer.mp4` or `{SanitizedTitle} ({Year}) - S00E00 - Trailer (Placeholder).mp4`
- **Plex Matching Mechanism**:
  - Season 00 maps to Plex Specials.
  - S00E00 is treated as a promotional trailer special episode with episode title `Trailer (Placeholder)`, preserving series and poster art while real episodes are pending download without corrupting the main season episode count.

---

## 2. Dynamic Artwork & Countdown Banner Overlays

To distinguish upcoming media from available media on client home screens:
- Portalarr generates high-definition poster artwork combined with dynamic status banners:
  - **NOT REQUESTED YET**: Unmonitored releases.
  - **COMING SOON MONITORED**: Monitored in Radarr/Sonarr, unreleased.
  - **STREAMING IN X DAYS**: Monitored with known digital release date countdown.
  - **DOWNLOADING SOON**: Monitored and released, awaiting indexer availability.
- Generated posters are composited using `sharp` / SVG and written alongside the video stub as `poster.jpg` or uploaded directly to PMS via `POST /library/metadata/{ratingKey}/posters`.

---

## 3. Placeholder Tagging Worker (`tagAllPlaceholdersInPlexInternal`)

To prevent placeholders from showing up in default "Recently Added" rows:
1. The scanner evaluates all media items in a section.
2. Identifies placeholders by:
   - File path containing `edition-trailer`, `edition-placeholder`, `s00e00`, `.disc`, `.strm`, or `/coming_soon/`
   - Content advisory records marked with `isPlaceholder: true` or `Placeholder:`
   - Matched TMDb IDs.
3. Automatically sets Plex label: `trailer-placeholder` via `PUT /library/metadata/{ratingKey}?label[0].tag.tag=trailer-placeholder`.
4. For TV shows, renames S00E00 episode title to `Trailer (Placeholder)` and locks it (`title.locked=1`).

---

## 4. Automated Real Content Replacement & Cleanup

During every collection sync, library scan, or Servarr ingestion event:
1. Portalarr checks whether real media has arrived (file size > 200MB, non-trailer filename, or Radarr/Sonarr `hasFile: true`).
2. If real media is present:
   - Purges the placeholder file (`.mp4`, `.disc`, `.strm`) and its accompanying poster/nfo files.
   - Cleans up empty placeholder folders (`purgeEmptyDirectories`).
   - Removes the placeholder advisory record from the database.
   - Triggers PMS section refresh (`POST /library/sections/{sectionKey}/refresh`).
