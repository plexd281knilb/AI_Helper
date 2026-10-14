# Seerr Servarr Dispatch & Availability Sync Reference

This document details how approved media requests are routed to Radarr/Sonarr instances, how override rules apply, and how library availability is reconciled against media servers.

Reference source:
- [server/subscriber/MediaRequestSubscriber.ts](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/server/subscriber)
- [server/lib/availabilitySync.ts](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/server/lib/availabilitySync.ts)

---

## 1. Servarr Dispatch Pipeline

1. **Request Approval**:
   - `MediaRequestSubscriber` listens for request status changes to `APPROVED`.
2. **Server & Profile Selection**:
   - Selects the target Radarr/Sonarr instance based on `is4k` flag or explicit `serverId`.
   - Resolves `qualityProfileId` and `rootFolderPath`.
3. **Override Rules**:
   - Matches media attributes (genres, spoken language, origin country) against `OverrideRule` records.
   - Example: Spoken language `ja` (Japanese anime) automatically reroutes to Anime Radarr/Sonarr server with `/data/anime` root folder.
4. **API Invocation**:
   - Calls `POST /api/v3/movie` (Radarr) or `POST /api/v3/series` (Sonarr) with `addOptions.searchForMovie: true` / `searchForMissingEpisodes: true`.
   - Updates `MediaRequest.status` to `COMPLETED` (dispatched) or `FAILED` (error logged).

---

## 2. Media Availability Sync

- **Periodic Scanner**:
  - Scans Plex or Jellyfin library sections matching TMDb/TVDb/IMDb GUIDs.
  - When media files are discovered:
    - Sets `Media.status` to `AVAILABLE` (5) or `PARTIALLY_AVAILABLE` (4 for partial TV seasons).
    - Triggers notifications to the original requester (Email, Discord, Pushbullet) that their media is ready to stream.
