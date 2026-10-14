# Agregarr Plex Collection & Home Hub Sync Reference

This document details how Agregarr and Portalarr create collections, synchronize media items, set sort orders, and promote custom collections to Plex Home and Recommended screens.

Reference source files:
- [HubSyncService.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/collections/plex/HubSyncService.ts)
- [PlexSmartCollectionManager.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/collections/plex/PlexSmartCollectionManager.ts)
- [plexapi.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/api/plexapi.ts)
- [UnifiedOrderingService.ts](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/agregarr-latest/agregarr-latest/server/lib/collections/plex/UnifiedOrderingService.ts)
- [curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)

---

## 1. Creating Collections in Plex

Collections in Plex can be either **Static (Manual)** or **Smart (Filter-based)**.

### Static / Manual Collections
```http
POST /library/collections?type={1|2}&title={EncodedTitle}&smart=0&sectionId={libraryKey}
```
- `type`: `1` for Movie libraries, `2` for TV Show libraries.
- `smart=0`: Creates a standard collection that can hold an arbitrary list of rating keys.
- Response contains `MediaContainer.Metadata[0].ratingKey` which is stored as `collectionRatingKey`.

### Smart Collections
```http
POST /library/collections?type={1|2}&title={EncodedTitle}&smart=1&uri={EncodedFilterUri}&sectionId={libraryKey}
```
- `uri`: The underlying Plex query filter URI (e.g. `server://{machineId}/com.plexapp.plugins.library/library/sections/{libraryKey}/all?genre=12&sort=rating:desc`).

---

## 2. Incremental Collection Item Synchronization

Instead of deleting and recreating collections (which resets user customizations and posters), collections are synchronized incrementally:

1. **Query Current Contents**:
   ```http
   GET /library/collections/{collectionRatingKey}/children
   ```
   Collects existing item `ratingKey`s into a set.

2. **Compute Diff**:
   - `toAdd`: Desired items not currently in collection.
   - `toRemove`: Current items not in desired list.

3. **Batch Removal**:
   ```http
   DELETE /library/collections/{collectionRatingKey}/items/{itemRatingKey}
   ```

4. **Batch Addition**:
   ```http
   POST /library/collections/{collectionRatingKey}/items?uri=server://{machineId}/com.plexapp.plugins.library/library/metadata/{commaSeparatedRatingKeys}
   ```

5. **Sorting & Arranging**:
   Set collection preference for sort mode:
   ```http
   PUT /library/collections/{collectionRatingKey}/prefs?collectionSort={0|1|2}
   ```
   - `0`: Release Date (`release`)
   - `1`: Alphabetical (`alpha`)
   - `2`: Custom Order (`custom`) — preserves custom move order!

   When `custom` is selected, items are ordered using:
   ```http
   PUT /library/collections/{collectionRatingKey}/items/{itemToMove}/move?after={afterItemRatingKey}
   ```
   (For the first item at index 0, the `?after` parameter is omitted).

---

## 3. Home Screen & Recommended Hub Promotion

Plex exposes custom collections on user home screens via its Hub Management endpoints.

### Step 1: Initialize the Hub in Plex
```http
POST /hubs/sections/{librarySectionId}/manage?metadataItemId={collectionRatingKey}
```

### Step 2: Hub Identifier Convention
Custom collection hubs follow the strict identifier schema:
```text
custom.collection.{librarySectionId}.{collectionRatingKey}
```

### Step 3: Set Visibility Flags
```http
PUT /hubs/sections/{librarySectionId}/manage/{hubIdentifier}?promotedToRecommended={1|0}&promotedToOwnHome={1|0}&promotedToSharedHome={1|0}
```
- `promotedToRecommended`: Appears on the library's **Recommended** tab.
- `promotedToOwnHome`: Appears on the **Server Owner's Home Screen**.
- `promotedToSharedHome`: Appears on **Managed & Friend Users' Home Screens**.

---

## 4. Sort Ordering, Hub Moving & Priority Prefixes

To control the vertical positioning of custom collection hubs on the Plex Home screen:

### Visual Hub Reordering (Drag & Drop)
Plex natively supports reordering home screen hubs via the `/move` API:
```http
PUT /hubs/sections/{librarySectionId}/manage/{hubIdentifier}/move?after={afterHubIdentifier}
```
- For the first item at the top of Home, omit the `?after` query parameter.
- `hubIdentifier`: `custom.collection.{librarySectionId}.{collectionRatingKey}` (for custom collections) or `hub:movie.recentlyadded.1` (for built-in hubs).

### Sort Title Prefixes & Metadata Locking
- Agregarr and Portalarr apply sort title prefixes to the collection's `titleSort` attribute:
  - `!00_Recent` (displays at the very top of Home)
  - `!01_Released`
  - `!02_Unwatched`
  - `!03_Theatres`
  - `!04_Dynamic`
- API Call:
  ```http
  PUT /library/metadata/{collectionRatingKey}?type=18&id={collectionRatingKey}&titleSort.value={sortTitle}&titleSort.locked=1
  ```

### Concurrency & Server Action Timeout Prevention
- When reordering 10–20 hubs, execute database updates and visibility updates concurrently using `Promise.all` with a 4-second timeout per network call.
- Avoid slow serialized waterfalls or spraying 10+ candidate URLs to prevent Next.js Server Action timeouts (`An unexpected response was received from the server`).

---

## 5. Fast Collection Deletion & Cascade

When deleting a collection from Plex:
- **Direct API Call**:
  ```http
  DELETE /library/metadata/{collectionRatingKey}
  ```
- **Internal PMS Cascade**: Plex Media Server automatically removes the collection tag from all associated media items internally in milliseconds.
- **Rule**: Never download or sweep thousands of library items to untag them individually. Use direct `DELETE` with early exit on success.
