# Sonarr REST API v5 Reference

This document details key Sonarr v5 API endpoints, query syntax, series model properties, and background command triggers.

Reference source:
- [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Sonarr-5-develop/src/Sonarr.Api.V5/openapi.json)

---

## 1. Authentication & Common Headers

All requests require the `X-Api-Key` header:
```http
X-Api-Key: your-sonarr-api-key
Accept: application/json
Content-Type: application/json
```

---

## 2. Core Endpoints

### Series
- **Get All Series**: `GET /api/v5/series`
- **Lookup Series**: `GET /api/v5/series/lookup?term={term}`
- **Lookup by TVDb ID**: `GET /api/v5/series/lookup?term=tvdb:{id}`
- **Add Series**:
  ```http
  POST /api/v5/series
  {
    "title": "Breaking Bad",
    "tvdbId": 81189,
    "qualityProfileId": 1,
    "rootFolderPath": "/tv",
    "monitored": true,
    "seriesType": "standard",
    "seasonFolder": true,
    "addOptions": {
      "monitor": "all",
      "searchForMissingEpisodes": true
    }
  }
  ```
- **Delete Series**: `DELETE /api/v5/series/{id}?deleteFiles=true&addImportExclusion=false`

### Episodes
- **Get Episodes**: `GET /api/v5/episode?seriesId={id}`
- **Monitor / Unmonitor Episode**:
  ```http
  PUT /api/v5/episode/{id}
  {
    "monitored": false
  }
  ```

### Commands
- `POST /api/v5/command` with `{ "name": "SeriesSearch", "seriesId": 1 }`
- `POST /api/v5/command` with `{ "name": "SeasonSearch", "seriesId": 1, "seasonNumber": 1 }`
- `POST /api/v5/command` with `{ "name": "DownloadedEpisodesScan", "path": "/downloads/completed/ShowFolder" }`
- `POST /api/v5/command` with `{ "name": "RefreshSeries", "seriesId": 1 }`
