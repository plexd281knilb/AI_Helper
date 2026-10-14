# Kometa Collection & Smart Playlist Builders Reference

This document details how Kometa and Portalarr construct dynamic media collections and playlists from upstream list providers, Plex metadata filters, and smart query builders.

Reference source files:
- [builder.py](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/modules/builder.py)
- [plex.py](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/modules/plex.py)
- [kometaconfig.yml](file:///C:/Users/Dom/Documents/GitHub/portalarr/kometaconfig.yml)

---

## 1. List Providers & Builders

### TMDb Builders
- `tmdb_popular`, `tmdb_top_rated`, `tmdb_now_playing`, `tmdb_upcoming`
- `tmdb_collection`: Target franchise by collection ID (e.g. Marvel Cinematic Universe `86311`).
- `tmdb_company`: Filter by production company ID (e.g. Pixar `3`).
- `tmdb_network`: Filter TV by network ID (e.g. HBO `49`, Netflix `213`).

### Trakt Builders
- `trakt_trending`, `trakt_popular`, `trakt_watched`, `trakt_collected`, `trakt_anticipated`
- `trakt_list`: Custom user lists (e.g. IMDb Top 250 mirrors, Criterion Collection).

### Letterboxd & IMDb Builders
- `letterboxd_list`: Top 250 narrative features, Oscar winners, genre rankings.
- `imdb_list`: IMDb Top 250, IMDb Popular, Most Voted.

### Radarr / Sonarr Servarr Builders
- Monitored Missing: `monitored_missing` for unacquired items.
- Tag Collections: `tag:<tagName>` for specific server tags (e.g. `tag:4k`, `tag:anime`).

---

## 2. Filtering Pipeline & Smart Rule Syntax

Collections support inclusive and exclusive filters:
```yaml
collections:
  "Top 90s Action Movies":
    tmdb_discover:
      with_genres: 28
      primary_release_date.gte: "1990-01-01"
      primary_release_date.lte: "1999-12-31"
      sort_by: vote_average.desc
      vote_count.gte: 1000
    filters:
      rating.gte: 7.0
      original_language: en
    sync_mode: sync
```

---

## 3. Sync Modes & Content Management

- `sync_mode: sync`: Strict parity. Any item in Plex collection that is no longer in the builder source list will be removed.
- `sync_mode: append`: Additive only. Preserves manual Plex user additions.
- `collection_order`: `release`, `alpha`, or `custom` (preserves ranking order from list provider).
