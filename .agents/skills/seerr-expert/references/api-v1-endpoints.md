# Seerr (Overseerr / Jellyseerr) API v1 Reference

This document details key endpoints for media requests, discovery, user management, and availability states.

Reference source:
- [seerr-api.yml](file:///c:/Users/Dom/Documents/GitHub/Other_Repos/seerr-develop/seerr-api.yml)

---

## 1. Authentication & Common Headers

All client API requests require `X-Api-Key`:
```http
X-Api-Key: your-seerr-api-key
Accept: application/json
Content-Type: application/json
```

---

## 2. Core Endpoints

### Requests
- **Get Requests**: `GET /api/v1/request?take=20&skip=0&filter=all`
- **Submit Request**:
  ```http
  POST /api/v1/request
  {
    "mediaType": "movie",
    "mediaId": 27205,
    "is4k": false,
    "serverId": 0,
    "profileId": 1,
    "rootFolder": "/movies"
  }
  ```
- **Approve Request**: `POST /api/v1/request/{id}/approve`
- **Decline Request**: `POST /api/v1/request/{id}/decline`
- **Retry Failed Request**: `POST /api/v1/request/{id}/retry`

### Discovery
- `GET /api/v1/discover/trending`
- `GET /api/v1/discover/movies/upcoming`
- `GET /api/v1/discover/tv/upcoming`
- `GET /api/v1/search?query={query}`

### Media Status
- `GET /api/v1/media/{id}`: Returns status (`UNKNOWN` = 1, `PENDING` = 2, `PROCESSING` = 3, `PARTIALLY_AVAILABLE` = 4, `AVAILABLE` = 5).
