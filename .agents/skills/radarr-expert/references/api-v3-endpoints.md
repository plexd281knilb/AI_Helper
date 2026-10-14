# Radarr REST API v3 Reference

This document details key Radarr v3 API endpoints, query syntax, movie model properties, and background command triggers.

Reference source:
- [openapi.json](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Radarr-develop/src/Radarr.Api.V3/openapi.json)

---

## 1. Authentication & Common Headers

All requests require the `X-Api-Key` header:
```http
X-Api-Key: your-radarr-api-key
Accept: application/json
Content-Type: application/json
```

---

## 2. Core Endpoints

### Movies
- **Get All Movies**: `GET /api/v3/movie`
- **Lookup Movie**: `GET /api/v3/movie/lookup?term={term}`
- **Lookup by TMDb ID**: `GET /api/v3/movie/lookup/tmdb?tmdbId={id}`
- **Add Movie**:
  ```http
  POST /api/v3/movie
  {
    "title": "Inception",
    "year": 2010,
    "tmdbId": 27205,
    "qualityProfileId": 1,
    "rootFolderPath": "/movies",
    "monitored": true,
    "minimumAvailability": "released",
    "addOptions": {
      "searchForMovie": true
    }
  }
  ```
- **Delete Movie**: `DELETE /api/v3/movie/{id}?deleteFiles=true&addImportExclusion=false`

### Tags
- **Get Tags**: `GET /api/v3/tag`
- **Create Tag**: `POST /api/v3/tag` with `{ "label": "4k" }`

### Commands
- `POST /api/v3/command` with `{ "name": "MoviesSearch", "movieIds": [1, 2] }`
- `POST /api/v3/command` with `{ "name": "DownloadedMoviesScan", "path": "/downloads/completed/MovieName" }`
- `POST /api/v3/command` with `{ "name": "RefreshMovie", "movieId": 1 }`
