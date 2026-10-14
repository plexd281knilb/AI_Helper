# Kometa & Poster Studio Overlay Engine Reference

This document details the coordinate math, composite pipeline, asset caching, and badge overlay generation used by Kometa and Portalarr's native Poster Studio.

Reference source files:
- [overlay.py](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/modules/overlay.py)
- [overlays.py](file:///C:/Users/Dom/Documents/GitHub/Other_Repos/Kometa-master/Kometa-master/modules/overlays.py)
- [src/app/api/curation/badges/route.ts](file:///C:/Users/Dom/Documents/GitHub/portalarr/src/app/api/curation/badges/route.ts)

---

## 1. Canvas Dimensions & Aspect Ratio Standards

- **Standard Poster (Portrait)**:
  - Width: `1000px`, Height: `1500px` (or `600px` x `900px` for fast streaming web view).
  - Strict 2:3 vertical aspect ratio (`aspect-[2/3]`).
- **Standard Backdrop (Landscape)**:
  - Width: `1920px`, Height: `1080px` (16:9).

---

## 2. Overlay Types & Badges

### Resolution & Video Standard Flags
- `4K UHD`, `1080p FHD`, `720p HD`
- `HDR10`, `HDR10+`, `Dolby Vision` (DV / DV+HDR)
- `IMAX Enhanced`

### Audio Specs
- `Dolby Atmos`, `Dolby TrueHD`, `DTS:X`, `DTS-HD MA`, `FLAC`

### Dynamic Ratings & Ribbons
- `IMDb Score` (e.g. `⭐ 8.4`)
- `Rotten Tomatoes Critic` (Fresh / Certified Fresh / Rotten %)
- `Rotten Tomatoes Audience` (Popcorn %)
- `TMDb User Score`

---

## 3. Positioning & Coordinate Math

Badges can be placed in 6 standard positions:
- `top-left`: `(x: offset_x, y: offset_y)`
- `top-right`: `(x: width - badge_w - offset_x, y: offset_y)`
- `bottom-left`: `(x: offset_x, y: height - badge_h - offset_y)`
- `bottom-right`: `(x: width - badge_w - offset_x, y: height - badge_h - offset_y)`
- `center-top`: `(x: (width - badge_w)/2, y: offset_y)`
- `center-bottom`: `(x: (width - badge_w)/2, y: height - badge_h - offset_y)`

### Collision Handling & Group Queues
When multiple badges share a corner (e.g. 4K badge + Dolby Vision badge):
- Set `queue: <name>` with `addon_offset`. Badges are automatically stacked vertically or horizontally based on their defined weight and priority.
