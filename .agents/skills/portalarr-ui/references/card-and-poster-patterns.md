# Card & Poster Design Patterns in Portalarr

Posters and cards are the primary visual building blocks across Portalarr (Discover, Library, Agregarr, Kometa, Requests, and Radarr/Sonarr views).

---

## 1. Strict 2:3 Vertical Poster Aspect Ratio

- Always enforce standard 2:3 vertical poster proportions:
  ```tsx
  <div className="relative aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-900 border border-slate-800 shadow-md transition-all duration-300 group-hover:scale-[1.02] group-hover:shadow-xl group-hover:border-slate-700">
    <img
      src={posterUrl}
      alt={title}
      className="w-full h-full object-cover"
      loading="lazy"
    />
  </div>
  ```
- **Never** use arbitrary aspect ratios (like 4:3 or landscape 16:9) for movie, TV, book, or comic posters.
- When generating or fetching Plex transcode images via `/api/media/image`, always pass `width=600&height=900`.

---

## 2. Corner Badges & Ribbon Overlays

- **Top-Right Corner**: Format & Type Badges (e.g. `🎬 MOVIE`, `📺 TV`, `📖 EBOOK`, `🎧 AUDIOBOOK`, `4K UHD`, `1080p`).
  ```tsx
  <div className="absolute top-2 right-2 z-10 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider backdrop-blur-md bg-slate-950/80 text-cyan-300 border border-cyan-500/30">
    4K UHD
  </div>
  ```
- **Book Age Rating Badges**: Standardized four-bracket pill styling:
  - `Kids`: Emerald backdrop (`bg-emerald-500/25 text-emerald-300 border-emerald-500/40`)
  - `YA (12+)`: Sky backdrop (`bg-sky-500/25 text-sky-300 border-sky-500/40`)
  - `All Ages`: Slate backdrop (`bg-slate-900/80 text-slate-300 border-slate-700/60`)
  - `18+ Mature`: Rose backdrop (`bg-rose-500/25 text-rose-300 border-rose-500/40`)
- **Top-Left Corner**: Availability Status (`✓ Available`, `⏳ Downloading`, `⌛ Pending`, `🔥 Coming Soon`).
- **Bottom Ribbon**: Dynamic Overlay ribbons (e.g. `LEAVING IN 3 DAYS`, `STREAMING ON {date}`, `4K HDR • ATMOS`).

---

## 3. Title Typography & Line Clamping

- Multi-word non-fiction book titles and long movie titles can break layout grids if heights vary.
- **Rule**: Standardize card text container heights and clamp titles:
  ```tsx
  <div className="pt-2 px-1">
    <h3 className="font-semibold text-xs sm:text-sm text-slate-100 line-clamp-2 sm:line-clamp-3 h-[36px] sm:h-[48px] leading-tight group-hover:text-amber-400 transition-colors">
      {title}
    </h3>
    <p className="text-[11px] text-slate-400 truncate mt-0.5">
      {subtitleOrAuthor}
    </p>
  </div>
  ```

---

## 4. Missing Stubs & Grayscale Immunity Cards

- When displaying unacquired installments in a series or placeholder stubs:
  ```tsx
  <div className="relative aspect-[2/3] w-full rounded-xl overflow-hidden bg-slate-950 border-2 border-dashed border-slate-700/70 grayscale opacity-60 hover:opacity-90 transition-opacity">
    <img src={coverUrl} className="w-full h-full object-cover" />
    <div className="absolute inset-0 bg-slate-950/70 flex flex-col items-center justify-center p-2 text-center">
      <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/50 bg-amber-950/40">
        Missing Stub
      </Badge>
    </div>
  </div>
  ```

---

## 5. Responsive Grid Breakpoints

Standard grid layout for media shelves and discovery pages:
```tsx
<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 3xl:grid-cols-8 gap-3 sm:gap-4 lg:gap-5">
  {items.map(item => <MediaCard key={item.id} item={item} />)}
</div>
```

---

## 6. Volume-Ordered Missing Series Cards & 1-Click Auto-Grab

- Series missing book displays render strictly ordered ascending by volume (`Vol 1`, `Vol 2`, `Vol 3`...).
- Missing cards feature clean volume badges, author attribution, and prominent **`Auto Grab`** (1-click trigger) and **`Search`** (modal chooser) action buttons.
- In *Seerr media discovery, missing series items appear in the horizontal `"Missing from Your Series"` carousel with volume tags and 1-click grab workflows.

---

## 7. Media Card Action Bar & Radix DropdownMenu Pattern

- **Zero Button Truncation Rule:** Never place 3+ text or icon buttons side-by-side in responsive card footers. In multi-column grids (where cards narrow to 150px–180px), multi-button rows squeeze buttons down to <45px, causing aggressive text truncation (`Res...`, `k...`, `f...`, `e...`) or unrecognizable mystery icons.
- **2-Tier Standard Card Footer Structure:**
  1. **Tier 1 (Hero CTA):** Full card-width button for the primary user interaction (`Resume (31%)`, `Read Book`, `Listen & Chapters`). Spans `w-full` and never wraps or truncates.
  2. **Tier 2 (Secondary Action & Radix Menu):** A primary secondary action button (`flex-1`, e.g. `Send to Kindle` or `Download`) paired with a Radix UI `DropdownMenu` trigger button (`•••` / `MoreHorizontal`).
  3. **Tier 3 (Radix DropdownMenuContent):** All auxiliary and administrative actions (`Fetch Cover`, `Match Book`, `Edit Metadata`, `Delete`, `Admin Send to User Kindle`) reside inside `DropdownMenuContent` with clear, full text labels, colored icons, and sub-menus.

```tsx
<div className="flex flex-col gap-1.5 p-2 bg-slate-950/60 border-t border-slate-800/80">
  {/* Primary Hero Action */}
  <Button
    size="sm"
    className="w-full h-8 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white truncate shadow-sm"
    onClick={handlePrimaryAction}
  >
    <BookOpen className="w-3.5 h-3.5 mr-1.5 shrink-0" />
    <span className="truncate">{resumePercent ? `Resume (${resumePercent}%)` : "Read Book"}</span>
  </Button>

  {/* Secondary Action + Overflow Dropdown */}
  <div className="flex items-center gap-1.5 w-full">
    <Button
      size="sm"
      variant="outline"
      className="flex-1 h-7 text-[11px] font-medium border-slate-700 bg-slate-900/90 hover:bg-slate-800 text-slate-200 truncate px-2"
      onClick={handleSecondaryAction}
    >
      <Send className="w-3 h-3 mr-1 shrink-0 text-amber-400" />
      <span className="truncate">Kindle</span>
    </Button>

    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          size="sm"
          variant="outline"
          className="h-7 w-7 p-0 shrink-0 border-slate-700 bg-slate-900/90 hover:bg-slate-800 text-slate-300"
          title="More actions"
        >
          <MoreHorizontal className="w-3.5 h-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48 bg-slate-900 border-slate-800 text-slate-200">
        <DropdownMenuItem onClick={handleFetchCover}>
          <Image className="w-3.5 h-3.5 mr-2 text-cyan-400" /> Fetch Cover
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleMatchBook}>
          <Sparkles className="w-3.5 h-3.5 mr-2 text-purple-400" /> Match Metadata
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-slate-800" />
        <DropdownMenuItem onClick={handleDelete} className="text-red-400 focus:text-red-300">
          <Trash2 className="w-3.5 h-3.5 mr-2" /> Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
</div>
```

- **Radix Sub-Menu Portaling Rule (`DropdownMenuSubContent`):** `DropdownMenuSubContent` MUST be wrapped in `<DropdownMenuPrimitive.Portal>`. If rendered without a Portal, the sub-menu is inserted inline into parent `DropdownMenuContent` which has `overflow: hidden`, completely clipping and hiding the expanded sub-menu from view.
- **Send-to-Kindle Full-Width Action & Zero-Truncation Layout:** In responsive multi-column book grids (e.g. 5–8 columns on desktop/laptop, or 2-column mobile), card widths narrow to ~155px–175px. Sharing Row 2 with a 3-dot dropdown trigger causes "Send to Kindle" (14 chars) to truncate to "Send to Kin..." on any standard screen. To guarantee 100% zero text truncation:
  - **Row 1**: Pair the primary reading CTA (`Read Book` / `Resume (X%)`) with the `MoreVertical` (`h-8 w-8`) dropdown trigger in a `flex items-center gap-1.5 w-full` row.
  - **Row 2**: Render `Send to Kindle` as a dedicated full-width button (`w-full h-7.5 text-xs`) with `whitespace-nowrap font-medium`, guaranteeing complete visibility across all screen sizes and column widths.

