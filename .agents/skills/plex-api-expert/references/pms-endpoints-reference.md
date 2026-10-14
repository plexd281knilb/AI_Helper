# Plex Media Server (PMS) Endpoints Reference

This document details key PMS REST API endpoints, query parameters, telemetry, and photo transcoding options.

Reference source:
- [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/openapi.json)
- [actions.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/actions.ts)

---

## 1. Authentication & System Endpoints

- **Server Identity**:
  ```http
  GET /identity
  Headers: X-Plex-Token: {token}, Accept: application/json
  ```
  Returns `MediaContainer.machineIdentifier` and `version`.

- **Library Sections**:
  ```http
  GET /library/sections
  ```
  Returns array of library sections with `key`, `type` (`movie`, `show`), `title`, and `agent`.

- **Library Media Items**:
  ```http
  GET /library/sections/{sectionKey}/all?type={1|2}&includeGuids=1&includeAdvanced=1
  ```
  Returns metadata including TMDb/IMDb/TVDb GUIDs, file paths, editions, labels, and stream specs.

---

## 2. Active Playback Sessions & Stream Control

- **Active Sessions Telemetry**:
  ```http
  GET /status/sessions
  ```
  Provides live stream details: video/audio codecs, transcode decision (direct play vs transcode), transcode speed, bitrate, user username/email, and player title.

- **Kill Stream**:
  ```http
  DELETE /status/sessions/{sessionId}?reason={EncodedMessage}
  ```
  Immediately terminates the specified playback session on the client device.

---

## 3. Photo Transcoder (Artwork Optimization)

```http
GET /photo/:/transcode?width=600&height=900&minSize=1&upscale=1&url={EncodedArtworkPath}&X-Plex-Token={token}
```
- Requesting `width=600&height=900` preserves 2:3 vertical poster proportions.
- Passing `url` pointing to local metadata or remote HTTPS images fetches cached, hardware-accelerated WebP/JPEG thumbnails.
