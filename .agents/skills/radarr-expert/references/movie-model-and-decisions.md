# Radarr Movie Model & Decision Engine Reference

This document details the Radarr movie resource model, release date fields, quality profile structures, and custom format evaluation.

Reference source:
- [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Radarr-develop/src/Radarr.Api.V3/openapi.json)

---

## 1. Key Movie Model Properties

- `id`: Internal Radarr database ID.
- `title`, `cleanTitle`, `sortTitle`.
- `tmdbId`, `imdbId`.
- `monitored`: Boolean indicating if automatic RSS/search is active.
- `hasFile`: Boolean indicating if movie file exists on disk.
- `isAvailable`: Boolean indicating if movie has passed minimum availability.
- **Release Dates**:
  - `inCinemas`: Theatrical premiere date ISO string.
  - `digitalRelease`: Digital streaming release date ISO string.
  - `physicalRelease`: Blu-ray/DVD release date ISO string.
- `tags`: Array of integer tag IDs assigned to this movie.
- `movieFile`: File details (size, quality, mediaInfo, path).

---

## 2. Release Scoring & Custom Formats

Custom Formats allow assigning positive or negative point scores to releases:
- **HDR Specs**: HDR10 (+500), Dolby Vision (+800), HDR10+ (+400).
- **Audio Specs**: TrueHD Atmos (+600), DTS-HD MA (+400).
- **Release Groups / Sources**: Preferred P2P/Internal groups (+200), Remux (+1000).
- **Cutoffs**: When a grabbed release reaches the `cutoffScore`, Radarr stops automated upgrade searches.
