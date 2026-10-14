# Maintainerr Rules & Operators Reference

This document details the rule definition schema, comparison operators, and data sources supported by the Maintainerr and Portalarr rule engine.

Reference source files:
- [apps/server/src/modules/rules/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development/apps/server/src/modules/rules)
- [packages/contracts/src/rules/](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Maintainerr-development/Maintainerr-development/packages/contracts/src/rules)

---

## 1. Rule Structure

Rules are structured as trees of boolean groups containing individual condition specs:

```json
{
  "name": "Unwatched Movies Over 1 Year Old",
  "mediaType": "movie",
  "action": "delete",
  "deleteAfterDays": 14,
  "conditionGroup": {
    "operator": "AND",
    "conditions": [
      {
        "source": "plex",
        "property": "viewCount",
        "operator": "EQUALS",
        "value": 0
      },
      {
        "source": "radarr",
        "property": "added",
        "operator": "BEFORE",
        "value": "365d"
      }
    ]
  }
}
```

---

## 2. Comparison Operators

| Operator | Type | Description |
| :--- | :--- | :--- |
| `EQUALS` | Primitive | Exact value match |
| `NOT_EQUALS` | Primitive | Value negation |
| `CONTAINS` | String | Substring search |
| `BIGGER` | Numeric | Greater than (`>`) |
| `SMALLER` | Numeric | Less than (`<`) |
| `BEFORE` | Date / Time | Timestamp occurred before target date |
| `AFTER` | Date / Time | Timestamp occurred after target date |
| `IN_LAST` | Time Window | Event occurred within the last X days/hours |
| `IN_NEXT` | Time Window | Upcoming event occurring in the next X days |

---

## 3. Supported Data Sources

- **Plex**: `viewCount`, `lastViewedAt`, `addedAt`, `rating`, `userWatchCount`, `resolution`.
- **Radarr**: `monitored`, `hasFile`, `sizeOnDisk`, `qualityProfileId`, `tags`, `added`.
- **Sonarr**: `monitored`, `episodeCount`, `sizeOnDisk`, `percentOfEpisodes`, `tags`.
- **Overseerr / Seerr**: `requestedBy`, `requestDate`, `is4k`.
- **Tautulli**: `playCount`, `totalDurationWatched`, `lastStreamedUser`.
- **Storage**: `diskspace_remaining_gb`, `mountPoint`.
