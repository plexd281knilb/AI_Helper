---
name: plex-api-expert
description: Expert architectural and API specification guide for Plex Media Server (PMS REST API, token authentication, library sections, metadata schemas, tag/label manipulation, custom collection hubs, photo transcoding, and stream session diagnostics). Activate when integrating with Plex, calling Plex endpoints, diagnosing playback sessions, managing collections and labels, or referencing openapi.json.
---

# Plex Media Server (PMS) API Expert Guide

Plex Media Server (PMS) provides an extensive HTTP REST API for media cataloging, metadata extraction, user management, library scanning, stream transcoding, home screen hub recommendations, and playback session telemetry.

Primary Reference Files & OpenAPI:
- OpenAPI 3.1 Specification: [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/openapi.json)
- Portalarr Plex Engine: [src/app/actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/actions.ts)
- Portalarr Curation Actions: [src/app/curation-actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/curation-actions.ts)

---

## API Architecture & Key Concepts

- **Authentication**: Token-based via `X-Plex-Token` HTTP header or `?X-Plex-Token=` query parameter.
- **Client Identification**: Mandatory `X-Plex-Client-Identifier` and `X-Plex-Product` headers.
- **Data Formats**: PMS defaults to XML; clients should explicitly supply `Accept: application/json` for JSON payloads.
- **Relative Path Resolution**: PMS API responses return relative `key` attributes that resolve against `/library/sections/` or root endpoints.
- **Multi-Server Candidate URLs Resolution**: To maintain 100% reliable connectivity across LAN, remote direct, and Plex Relay, clients should resolve all candidate URLs via `https://plex.tv/api/v2/resources` and test reachability with fastest-path failover.
- **Type Identifiers**:
  - `1`: `movie`
  - `2`: `show`
  - `3`: `season`
  - `4`: `episode`
  - `8`: `artist`
  - `9`: `album`
  - `10`: `track`
  - `15`: `playlist`
  - `18`: `collection`

---

## Core Capabilities & Runbooks

### 1. Server Endpoints & Telemetry
- **Identity & Capabilities**: `GET /identity`, `GET /myplex/account`.
- **Sections & Items**: `GET /library/sections`, `GET /library/sections/{id}/all`.
- **Stream Telemetry**: `GET /status/sessions`, `DELETE /status/sessions/{id}?reason=...`.
- **Image Transcoder**: `GET /photo/:/transcode?width=600&height=900&url=...`.

See detailed runbook: [pms-endpoints-reference.md](./references/pms-endpoints-reference.md).

### 2. Tags, Collections & Home Screen Hubs
- **Tag / Label Updates**: `PUT /library/metadata/{ratingKey}?label[0].tag.tag=...`.
- **Clear Labels**: `PUT /library/metadata/{ratingKey}?label[0].tag.tag-=`.
- **Collections**: `POST /library/collections`, batch add via `POST /library/collections/{id}/items?uri=server://...`.
- **Smart Collections**: `POST /library/collections?type={type}&title={title}&smart=1&uri={filterUri}`.
- **Personalized Recommendations**: `PUT /library/metadata/{ratingKey}/prefs?collectionFilterBasedOnUser=1`.
- **Hub Visibility**: Initialize via `POST /hubs/sections/{id}/manage?metadataItemId={id}`, then toggle `promotedToOwnHome`, `promotedToSharedHome`, `promotedToRecommended`.

See detailed runbook: [tags-collections-and-hubs.md](./references/tags-collections-and-hubs.md).

---

## Common Gotchas & Best Practices

1. **Tag Clearing Syntax**:
   - Omitting `label[0].tag.tag-=` when clearing all labels will leave existing tags intact in PMS. Always send `label[0].tag.tag-=` when emptying tag arrays.
2. **Locking Custom Metadata**:
   - Any manual edit made via `PUT /library/metadata/{ratingKey}` should include `<fieldName>.locked=1` (e.g. `title.locked=1`, `titleSort.locked=1`). Otherwise, the next automated library metadata refresh will overwrite the modification with agent data.
3. **Smart vs Static Collections**:
   - Never call `/move` or item manipulation endpoints on a collection created with `smart=1`. Smart collections are dynamically populated by Plex search filters.
4. **Portrait Poster Dimensions**:
   - Always request 2:3 vertical poster proportions (`width=600&height=900`) on `/photo/:/transcode` to prevent PMS from cropping portrait artwork to landscape dimensions.
5. **Session Stream Termination Fallback**:
   - When terminating active playback streams, verify user alias permissions and fall back from Tautulli to Direct PMS `DELETE /status/sessions/{sessionId}` if Tautulli is unavailable.
6. **Fast Collection Deletion via PMS Cascade**:
   - Deleting a collection via `DELETE /library/metadata/{ratingKey}` automatically unlinks all media items in Plex in ~10ms. Avoid pre-fetching and untagging items individually, as this triggers severe latency and Server Action timeouts.
7. **Hub Reordering & Visibility Timeouts**:
   - Use `PUT /hubs/sections/{sectionKey}/manage/{hubId}/move?after={afterHubId}` combined with locked `titleSort` prefixes to reorder hubs. Dispatch hub visibility updates concurrently (`Promise.all`) using 4s timeout guards (`AbortSignal.timeout(4000)`) to ensure Server Action resilience.
8. **Large Section Responses & Next.js Data Cache Limit**:
   - Large library endpoints (`/library/sections/{id}/all?includeGuids=1`) frequently exceed Next.js 2MB data cache limit (`WARN: items over 2MB can not be cached`). Direct server calls must bypass Next.js automatic fetch caching by supplying `{ cache: 'no-store' }`.
9. **Identifying Trailer Placeholders vs Real Media**:
   - Agregarr trailer placeholders share identical `Guid` (TMDb / IMDb) values with real movies. Distinguish them by checking `editionTitle === "Trailer"` or searching `metadata.Label` for `trailer-placeholder`. Availability indexes must exclude placeholders so upcoming movies are not falsely marked as "In Library".
10. **Strict Friend & Share Matching Integrity**:
    - When mapping local users to Plex friends/shares via `/api/users` or `https://plex.tv/api/v2/friends`, NEVER use partial substring containment (e.g. `ta.includes(sa)` or `sa.startsWith(ta)`). Partial substring matching causes disastrous cross-user share collisions (e.g. `userprimary` falsely matching `primary` or `mjprimary`). Strictly compare exact numeric Plex user IDs, exact emails, exact usernames, normalized alphanumeric characters (`username.replace(/[^a-z0-9]/gi, '')`), or exact email prefix identifiers (`email.split('@')[0]`).
11. **Connection Reachability & Byte-Range Playback Probing**:
    - When searching items or probing media across multiple PMS servers/candidate URLs, avoid sequential hanging on unresponsive URLs. Probe connection responsiveness with a fast 1,500ms `/identity` check first.
    - To verify disk read health without downloading complete multi-gigabyte media parts, execute an active HTTP Range probe (`Range: bytes=0-65535`) against the part URL (`part.key`). A 206 Partial Content or 200 OK confirms physical storage availability and responsive disk I/O.
12. **Tagging Studio & Content Advisory Labels**:
    - **Label Destination vs Genre Destination**: Plex labels applied via `PUT /library/metadata/{ratingKey}?label[0].tag.tag=...&label.locked=1` integrate directly into Plex Home user sharing restrictions, allowing administrators to restrict Kids and Teen profiles from sensitive content (e.g. `IMDb: Nudity [Severe]`).
    - **Dual Endpoint Updating**: Always dispatch tag updates to both `PUT /library/metadata/{ratingKey}` and `PUT /library/sections/{sectionKey}/all?type={typeId}&id={ratingKey}` to maintain 100% compatibility across legacy and modern PMS versions.
    - **Pre-Filtering to Avoid Excessive HTTP Calls**: When clearing tags or applying custom rules across thousands of media items, inspect known stream/section tags (`item.labels`, `item.genres`, `item.collections`) before initiating individual `GET /library/metadata/{ratingKey}` requests. Items that already lack the tag should be skipped immediately to maintain sub-second execution speeds.
    - **Collection Untagging and Container Deletion**: When clearing custom collection tags from a library, untagging the items should be accompanied by `deletePlexCollection` to cleanly remove the collection container entity from PMS.
13. **Unraid Daily 5:00 AM – 5:30 AM Plex Container Maintenance Blackout**:
    - **Blackout Protocol (`isPlexMaintenanceWindow`)**: Unraid executes scheduled database integrity checks and restarts Plex containers daily from 5:00 AM to 5:30 AM. No background runner, automated scheduled task, or direct PMS polling (`getPlexActiveSessions`, `getPlexServerLibrarySections`, `runOverlayIncrementalSyncInternal`, `runOverlayRecheckSyncInternal`, `runAgregarrSyncInternal`, `runMaintainerrSyncInternal`, `runParentalTagsSyncInternal`, `syncPlexFriendsInternal`, `syncMediaRequestsQueueAndAvailabilityInternal`, `getPlexLibraryGuidIndex`) is permitted to hit Plex Media Server during 5:00:00 AM – 5:29:59 AM.
    - All schedules due at or during 5:00 AM automatically defer to 5:30:00 AM once the container restart concludes. Maintainerr's recommended default is `daily_6am`.
14. **Direct Poster Buffer Uploads & MIME Magic Byte Requirements**:
    - PMS `/library/metadata/{ratingKey}/posters` rejects binary uploads with `400 Bad Request` if the `Content-Type` header disagrees with the binary image structure.
    - Always determine the image format from magic bytes (`image/png` for `89 50 4E 47`, `image/jpeg` for `FF D8 FF`, `image/webp` for `RIFF...WEBP`) rather than defaulting strictly to `image/jpeg`.
    - Always lock the uploaded poster (`PUT /library/metadata/{ratingKey}?thumb.locked=1`) to prevent PMS scheduled maintenance from overwriting custom or restored artwork.
    - Use multi-candidate URL failover (`expandCandidateUrls`) to ensure direct LAN IP fallback (`http://192.168.1.X:32400`) if `.plex.direct` endpoints time out or encounter DNS rebind blocks.
15. **Native Stream Intelligence, Watch History & Multi-IP Password Sharing Detection**:
    - **Native Watch History Engine (`stream-tracker.ts`)**: Portalarr records active playback sessions directly from PMS `/status/sessions` without requiring external Tautulli. Records progress percentage (dynamically calculated from `viewOffset` / `duration` if omitted by PMS), duration, completed status (`progress >= 90%`), video/audio decisions, transcode HW acceleration, client platform/device, and remote IP addresses.
    - **Password Sharing & Multi-IP Detection Heuristics (`analyzeActiveSessionsForSharing`)**: Detects simultaneous streaming sessions per user. Private/LAN IPs (`192.168.x.x`, `10.x.x.x`, `172.16-31.x.x`, `localhost`) are recognized as same-household playback and do NOT trigger sharing alerts. Multi-IP sharing is strictly flagged when a user streams concurrently from 2 or more distinct public IP addresses (indicating disparate households), recording `isSharingAlert: true`, incrementing `user.sharingAlertCount`, and alerting admins in real time on the Stream Matrix dashboard.
16. **Network Fetch Resilience & Next.js Streaming Pipeline Protection**:
    - **Never wrap operational PMS/Tautulli queries in `next: { revalidate: N }`**: In Next.js App Router Turbopack, wrapping dynamic server component or server action calls with Next.js data cache interceptors causes unreachable servers, dead Docker IP candidates, or aborted signals to throw unhandled `TypeError: fetch failed` during response piping, which crashes the stream with `Error: failed to pipe response`.
    - **Enforce `cache: "no-store"` & explicit `AbortSignal.timeout(...)`**: Always supply `{ cache: "no-store" }` and explicit timeout signals (e.g. `AbortSignal.timeout(5000)`) wrapped in `try/catch` blocks returning fallback structures (`null` or empty arrays) so failing endpoints fail gracefully without ever interrupting Next.js response piping.
17. **Local Machine Identifier URI Matching & Library URI Fallback (`LPE: only library URIs are allowed right now`)**:
    - **Plex Collection Single-Item URI Constraint**: Adding items to collections via `PUT /library/collections/{id}/items?uri=...` requires the URI to point to the local server's internal database (`server://{machineIdentifier}/com.plexapp.plugins.library/library/metadata/{ratingKey}`). If `{machineIdentifier}` does not match the receiving server, or if a cross-server URI is sent, PMS rejects it with `400 Bad Request` and logs `LPE: only library URIs are allowed right now. Failed to generate a query from uri server://...`.
    - **Strict Candidate Isolation**: In multi-server environments, `resolveWorkingPlexServerConnection` strictly purges candidate URLs returning mismatched `machineIdentifier` values so candidate lists never leak cross-server URLs. `syncPlexCollection` resolves `machineIdentifier` per candidate base URL (`baseMachineIdMap`), retries with `library:///item/%2Flibrary%2Fmetadata/{ratingKey}` upon HTTP 400 rejection, and falls back to item metadata tagging (`collection[0].tag.tag=...`) to ensure 100% item retention without PMS log errors.





