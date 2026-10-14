# Filtered Smart Hubs & Hub Dismissal Blacklist Reference

This document explains the technical implementation of **Filtered Smart Hubs** (which exclude placeholder trailers from default Plex rows) and the **Permanent Hub & Collection Dismiss / Blacklist System** (which prevents deleted auto-generated hubs from resurfacing).

---

## 1. Filtered Smart Hubs Architecture

### The Problem
When unreleased media trailers (`edition-Trailer`, `s00e00`, `.disc`, `.strm`) are imported into Plex to populate "Coming Soon" hubs, default Plex rows (such as "Recently Added Movies" or "Recently Released TV") immediately display those trailer stubs, confusing users who expect playable full movies/episodes.

### The Solution: Dynamic Plex Smart Collections
By deploying Plex Smart Collections that explicitly filter out placeholder criteria, we replace or augment default Plex hubs with clean, trailer-free hubs.

### Filter Queries by Subtype & Default Titles

1. **Recently Added Movies (`recently_added` - Movies)**:
   - Default Title: `Recently Added Movies (Curated)`
   - Filter URI: `?type=1&label!=trailer-placeholder&editionTitle!=Trailer&sort=addedAt:desc`
   - Excludes items with Plex label `trailer-placeholder` or edition `Trailer`.

2. **Recently Added TV (`recently_added` - TV Shows)**:
   - Default Title: `Recently Added TV (Curated)`
   - Filter URI: `?type=2&sort=addedAt:desc&season.index!=0&episode.title!=Trailer%20(Placeholder)&label!=trailer-placeholder&label!=Coming%20Soon-placeholder`
   - Excludes shows whose episodes are marked with `Trailer (Placeholder)` and uses `season.index!=0` to strictly exclude series that only have Season 00 specials/trailers.

3. **Recently Released Movies (`recently_released` - Movies)**:
   - Default Title: `Recently Released Movies (Curated)`
   - Filter URI: `?type=1&sort=originallyAvailableAt:desc&label!=trailer-placeholder&label!=Coming%20Soon-placeholder&editionTitle!=Trailer`
   - Orders by premiere/theatrical release date while excluding placeholder trailers.

4. **Recently Released TV / Episodes (`recently_released` / `recently_released_episodes` - TV)**:
   - Default Title: `Recently Released Episodes (Curated)` (or `Recently Released TV (Curated)`)
   - Filter URI: `?type=2&sort=episode.addedAt:desc&season.index!=0&episode.title!=Trailer%20(Placeholder)&label!=trailer-placeholder&label!=Coming%20Soon-placeholder`
   - Includes `season.index!=0` to guarantee that trailer-only stubs are excluded from latest episodes.

5. **Top Unwatched (Personalized per User) (`top_unwatched`)**:
   - Default Title: `Top Unwatched Movies (Curated)` (Movies) / `Top Unwatched TV (Curated)` (TV)
   - Filter URI: `?type=1&sort=originallyAvailableAt:desc&unwatched=1&and=1&label!=trailer-placeholder&label!=Coming%20Soon-placeholder&editionTitle!=Trailer` (Movies) or `?type=2&sort=originallyAvailableAt:desc&season.index!=0&show.unwatchedLeaves=1&and=1&episode.title!=Trailer%20(Placeholder)&label!=trailer-placeholder&label!=Coming%20Soon-placeholder` (TV)
   - User Personalization API:
     ```http
     PUT /library/metadata/{ratingKey}/prefs?collectionFilterBasedOnUser=1
     ```
     This instructs PMS to evaluate the `unwatched=1` filter per individual logged-in user rather than globally across the server owner.

### PMS Smart Collection Immutability & Re-creation
Plex Media Server does not support modifying the query URI of an existing smart collection via `PUT /library/collections/{id}/items?uri=...`. When updating smart queries:
1. Sweep all existing matching collections on the server.
2. If `content` matches `fullUri`, keep it.
3. If `content` differs or if duplicates exist, delete them via `DELETE /library/metadata/{ratingKey}`.
4. Deploy the new smart collection via `POST /library/collections` with `smart=1&uri=${encodeURIComponent(fullUri)}`.

---

## 2. Permanent Hub & Collection Dismiss / Blacklist Engine

### The Problem
When an administrator deletes an auto-generated Plex hub (such as *"Top Movies by Vicky Jenson"*, *"Action Movies from the 90s"*, or an old smart collection) from their dashboard, subsequent actions like clicking **"Import from Plex"** or running background library syncs detect the collection on PMS and blindly re-import it into the database.

### The Solution: Persistent Dismissal Blacklist
1. **Schema Registry**:
   - `Settings.dismissedHubs`: Stores a JSON array of dismissed hub records:
     ```typescript
     interface DismissedHubEntry {
         ratingKey: string;
         title: string;
         normalizedTitle: string;
         serverId?: string;
         sectionKey?: string;
         dismissedAt: string;
     }
     ```
   - `MediaCollection.isIgnored`: Boolean flag marking database records as ignored.

2. **Deletion Workflow (`deleteMediaCollectionAction`)**:
   - When a collection or hub is deleted in the UI:
     - Register the hub's `ratingKey`, `title`, and normalized lowercase title into `Settings.dismissedHubs`.
     - Update the database record with `isIgnored: true`.
     - If the user selects "Delete from Plex", PMS collection endpoint is also invoked (`DELETE /library/collections/{ratingKey}`).

3. **Plex Import Guard (`importPlexLibraryCollectionsAction`)**:
   - Before importing collections from PMS:
     - Fetch the current `dismissedHubs` set.
     - For each PMS collection:
       - If `dismissedSet.has(c.ratingKey)` or `dismissedSet.has(c.title.toLowerCase().trim())`, **skip it unconditionally**.
     - Only valid, non-dismissed collections are imported into the active database.

4. **Ignored Hubs Management**:
   - Admins can open the **"Ignored Hubs"** modal in Agregarr Studio.
   - Any hub can be restored via `unignoreMediaCollectionAction(ratingKeyOrTitle, serverId, sectionKey)`, removing it from the blacklist and resetting `isIgnored: false`.
