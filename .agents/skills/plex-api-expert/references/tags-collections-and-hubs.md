# Plex Tags, Collections & Home Screen Hubs Reference

This document details the exact HTTP requests and URL parameter syntax for managing Plex labels, creating static and smart collections, ordering items, and controlling Home / Recommended screen hubs.

Reference source files:
- [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/openapi.json)
- [curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)

---

## 1. Label & Metadata Management

### Appending Labels to an Item
```http
PUT /library/metadata/{ratingKey}?label[0].tag.tag={label1}&label[1].tag.tag={label2}&X-Plex-Token={token}
```

### Clearing All Labels from an Item
```http
PUT /library/metadata/{ratingKey}?label[0].tag.tag-=&X-Plex-Token={token}
```
*Crucial*: The `-=` suffix is mandatory for clearing array attributes in PMS.

### Locking Metadata Fields
```http
PUT /library/metadata/{ratingKey}?title.value={CleanTitle}&title.locked=1&titleSort.value={SortPrefix}&titleSort.locked=1&X-Plex-Token={token}
```

---

## 2. Collections (Static vs Smart)

### Create Static Collection
```http
POST /library/collections?type={1|2}&title={Title}&smart=0&sectionId={sectionKey}&X-Plex-Token={token}
```

### Add Items to Static Collection
```http
POST /library/collections/{collectionRatingKey}/items?uri=server://{machineId}/com.plexapp.plugins.library/library/metadata/{commaSeparatedKeys}&X-Plex-Token={token}
```

### Create Smart Collection with Filter URI
```http
POST /library/collections?type={1|2}&title={Title}&smart=1&uri={EncodedFilterUri}&sectionId={sectionKey}&X-Plex-Token={token}
```

### Update Existing Smart Collection Filter URI
```http
PUT /library/collections/{collectionRatingKey}/items?uri={EncodedFilterUri}&X-Plex-Token={token}
```

### Enable User-Personalized Recommendations on Smart Collections
```http
PUT /library/metadata/{collectionRatingKey}/prefs?collectionFilterBasedOnUser=1&X-Plex-Token={token}
```

### Delete Collection (Instant Cascade)
```http
DELETE /library/metadata/{collectionRatingKey}?X-Plex-Token={token}
```
*Note*: Plex Media Server automatically cascades collection deletion to all member items and removes the collection tag across the entire library in ~10ms. Manual untagging loops across thousands of items are unnecessary and cause severe latency.

---

## 3. Home Screen & Recommended Hub Management

### Initialize Hub
```http
POST /hubs/sections/{sectionKey}/manage?metadataItemId={collectionRatingKey}&X-Plex-Token={token}
```

### Configure Hub Promotion
Hub identifier syntax: `custom.collection.{sectionKey}.{collectionRatingKey}`
```http
PUT /hubs/sections/{sectionKey}/manage/custom.collection.{sectionKey}.{collectionRatingKey}?promotedToRecommended={1|0}&promotedToOwnHome={1|0}&promotedToSharedHome={1|0}&X-Plex-Token={token}
```
- `promotedToRecommended=1`: Shown in library Recommended view.
- `promotedToOwnHome=1`: Shown on Server Owner Home screen.
- `promotedToSharedHome=1`: Shown on Friends & Managed Users Home screens.

### Reorder / Move Hub
```http
PUT /hubs/sections/{sectionKey}/manage/{hubIdentifier}/move?after={afterHubIdentifier}&X-Plex-Token={token}
```
- `hubIdentifier`: Hub ID to move (e.g. `custom.collection.1.12345` or native hub ID `movie.recentlyadded.1`).
- `after`: Hub ID after which this hub should be positioned. Pass empty/omit to move to the very top.
- *Best Practice*: Combine sequential `/move` calls with setting locked `titleSort` prefixes (e.g. `01 - Featured`, `02 - Trending`) on underlying collections to ensure persistent ordering across Plex Web and TV client refreshes.

### Concurrency & Timeout Protection
When synchronizing hub visibility and ordering across multiple collections:
- Dispatch individual Plex API hub visibility calls concurrently with `Promise.all`.
- Wrap requests in a 4-second timeout (`AbortSignal.timeout(4000)`) to prevent single unresponsive endpoints or transient network stalls from blocking Next.js Server Actions.

