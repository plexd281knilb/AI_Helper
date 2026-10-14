# Modal & Dialog Design Patterns in Portalarr

Modals and dialogs are critical throughout Portalarr for media details, requests, season/episode guides, stream diagnosis, collection creation, and system configuration.

---

## 1. Width Specificity & Radix Dialog Overrides

Radix UI's default `DialogContent` includes `sm:max-w-lg`. If you simply add `max-w-6xl` to `className`, `tailwind-merge` will prioritize `sm:max-w-lg` at screen widths $\ge 640\text{px}$, causing the modal to render cramped and narrow!

### Standard Wide Modal Specification
For wide media and book modals (such as `MediaDetailModal`, `BookDetailModal`, `EpisodeGuideModal`, `CollectionBuilderModal`, `SettingsModal`):
```tsx
<DialogContent
  className="w-[95vw] sm:w-[92vw] md:w-[90vw] max-w-3xl lg:max-w-4xl max-h-[90vh] sm:max-h-[92vh] overflow-y-auto overflow-x-hidden p-0 bg-[#0c0c12] border border-border/60 shadow-2xl rounded-2xl sm:rounded-3xl scrollbar-thin text-foreground focus:outline-none"
>
```

> [!CRITICAL]
> **CSS Grid `min-w-0` Intrinsic Width Blowout**: Radix UI's `DialogPrimitive.Content` renders as a CSS Grid (`grid w-full ...`). In CSS Grid, children default to `min-width: auto`. If an inner section contains a horizontal scrolling carousel with 20+ items (e.g. "Similar Books & Recommendations" with 24 items), the intrinsic width calculation overrides `max-width`, causing the entire modal to expand horizontally to 3,000+ pixels!
> **Mandatory Fix**:
> 1. Always place a root wrapper with `<div className="flex flex-col min-h-0 min-w-0 w-full overflow-x-hidden">` directly inside `DialogContent`.
> 2. Ensure all inner wrappers and carousels include `min-w-0 w-full`.
> 3. Provide left/right chevron buttons for smooth horizontal carousel scrolling.
> 4. In the action button row, place the primary Request action (`Request Ebook` / `Request Audiobook` / `Request Movie`) **FIRST on the left**, so users never have to search or scroll horizontally to find the button.

### Standard Medium Modal Specification
For confirmation dialogs, quick actions, single-item edits, or auth prompts:
```tsx
<DialogContent
  className="sm:max-w-lg md:max-w-xl w-[94vw] sm:w-[90vw] max-h-[90vh] overflow-y-auto p-5 bg-slate-950 border border-slate-800 shadow-2xl rounded-xl"
>
```

---

## 2. Space Optimization & Zero Wasted Top Space

When users click on a poster or open media details, they expect to see key metadata, trailer access, and primary action buttons immediately without excessive scrolling.

### Header Architecture:
1. **Hero Backdrop Banner**:
   - 16:9 or cinematic ratio backdrop container (`h-48 sm:h-64 md:h-72 lg:h-80 w-full relative overflow-hidden`).
   - Image layer with soft zoom/fade: `<img src={backdropUrl} className="w-full h-full object-cover object-top opacity-35" />`.
   - Bottom gradient fade: `bg-gradient-to-t from-slate-950 via-slate-950/70 to-transparent`.
2. **Foreground Header Overlap**:
   - Poster thumbnail on the left (`w-28 sm:w-36 md:w-40 lg:w-44 aspect-[2/3] rounded-2xl shadow-2xl border border-white/10 shrink-0`).
   - Information stack on the right:
     - Title (`text-xl sm:text-2xl md:text-3xl font-bold text-white tracking-tight`).
     - Tagline (`text-xs sm:text-sm text-slate-400 italic`).
     - Pill badges row: Release Year, Content Rating (PG-13 / R / TV-MA), Runtime / Episodes, TMDB Score (`⭐ 8.2`).
     - Action Bar: Primary Request button (`📥 Request Movie` / `Configure & Request`), Monitored status badge, followed by secondary actions (`▶️ Watch Trailer`). Primary action must ALWAYS be first on the left.

---

## 3. Tabbed Content Containers

For detail modals that have multiple sub-sections (e.g. Details, Seasons/Episodes, Cast & Crew, Similar Titles):
- Use sticky tab headers with active underline indicators:
  ```tsx
  <div className="flex items-center gap-2 border-b border-slate-800 px-6 pt-2 sticky top-0 bg-slate-950/95 backdrop-blur-md z-10">
    <button className={activeTab === 'details' ? 'border-b-2 border-amber-400 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}>
      Details
    </button>
  </div>
  ```
- Keep season selectors and episode drilldown lists spacious with clear download status indicators (1080p FHD, 4K UHD, Monitored, Unmonitored).

---

## 4. Trailer Embeds & Media Playback

- Modal trailer player should embed responsive YouTube `<iframe>` players with `aspect-video` and standard autoplay settings:
  ```tsx
  <div className="relative w-full aspect-video rounded-xl overflow-hidden border border-slate-800 bg-black">
    <iframe
      src={`https://www.youtube-nocookie.com/embed/${trailerKey}?autoplay=1&rel=0`}
      title="Trailer"
      className="w-full h-full"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowFullScreen
    />
  </div>
  ```

---

## 5. Radarr/Sonarr-Style Interactive Match & Ingest Modals

For loose file ingestion, unlinked series metadata matching, and interactive release verification (`BookMatchModal`):
- **Candidate Suggestion Cards**:
  - Render detected candidate cards with tier confidence badges (`emerald` for High SQLite/Exact match, `amber` for Medium registry search, `purple` for AI analysis).
  - Include 2:3 vertical poster thumbnails, canonical title, author, series name, volume number, and a direct `✓ Select` action.
- **Side-by-Side File Inspection Telemetry**:
  - Show raw disk file path, parsed base title, file type, file size, and current relational link status (`Unlinked` vs `Linked to Series`).
- **Interactive Search Bar**:
  - Provide an inline search bar with format filter buttons (`📚 Ebook` vs `🎧 Audiobook`) querying online registries (OpenLibrary, Audible, Google Books) on demand.
- **Manual Overrides & Safety Toggles**:
  - Editable form inputs for Title, Author, Series Name, Volume Number, and Cover URL.
  - Safe disk restructuring checkbox (`"Organize on disk into Author / [Series Vol] Title"`) defaulting to checked only when confident.
