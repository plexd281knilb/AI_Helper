# Sonarr Series Models & Release Parsing Reference

This document details Sonarr series resource properties, series types, and release title regex parsing rules.

Reference source:
- [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Sonarr-5-develop/src/Sonarr.Api.V5/openapi.json)

---

## 1. Series Types

- `standard`: Standard season and episode numbering (e.g. `S01E05`).
- `daily`: Broadcast daily releases identified by air date (e.g. `2024.10.15`).
- `anime`: Absolute episode numbering (e.g. `[SubsPlease] Show Title - 05 [1080p].mkv`).

---

## 2. Monitored Missing Statistics

To detect series with missing episodes:
```typescript
const isMissing = series.monitored && (
  series.statistics?.episodeFileCount === 0 ||
  series.statistics?.percentOfEpisodes < 100
);
```

---

## 3. Placeholder TV Episodes (S00E00)

When creating Coming Soon placeholder stubs for TV series:
- Create folder: `{libraryPath}/{SeriesTitle} ({Year})/Season 00/`
- Create file: `S00E00.Trailer.mp4`
- Set Plex episode title to `Trailer (Placeholder)` to ensure TV series counts and season listings remain clean.
