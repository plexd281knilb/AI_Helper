# Theme & Color Tokens Reference in Portalarr

Portalarr adheres to an ultra-dark cinematic aesthetic designed for high contrast and seamless viewing on OLED displays and dark room setups.

---

## 1. Backgrounds & Surfaces

| Token / Class | Usage |
| :--- | :--- |
| `bg-slate-950` / `bg-black` | Main page body, dialog backgrounds, dropdown menu background |
| `bg-slate-900/90` | Primary cards, sidebars, modal headers, floating navigation bars |
| `bg-slate-950/60` | Secondary nested inner boxes, code blocks, parameter sections |
| `bg-slate-900/40` | Tertiary wells, table row hover states, disabled button backgrounds |
| `backdrop-blur-md` | Glassmorphic overlay containers, sticky headers, bottom floating bars |

---

## 2. Borders & Dividers

| Token / Class | Usage |
| :--- | :--- |
| `border-slate-800` | Standard card borders, dialog borders, divider lines |
| `border-slate-700/60` | Interactive input borders, hoverable poster card borders |
| `border-slate-800/80` | Inner well borders, sub-card section dividers |
| `border-amber-500/70` | Unsaved dirty state warning border |
| `border-emerald-500/40` | Active enabled service badge, success state outline |

---

## 3. Semantic Accents & Badges

| Accent Color | Primary Class | Semantic Meaning |
| :--- | :--- | :--- |
| **Amber / Gold** | `text-amber-400 bg-amber-950/40 border-amber-500/30` | Pending approvals, warnings, unsaved states, Coming Soon Monitored |
| **Emerald / Green** | `text-emerald-400 bg-emerald-950/40 border-emerald-500/30` | In Library, Available, Downloaded, Approved, Direct Play |
| **Purple / Violet** | `text-purple-400 bg-purple-950/40 border-purple-500/30` | Poster Studio, Overlays, AI metadata agents, Kometa rules |
| **Indigo / Blue** | `text-indigo-400 bg-indigo-950/40 border-indigo-500/30` | Agregarr curation, Collections, TV Series, Deep Recheck |
| **Cyan / Sky** | `text-cyan-400 bg-cyan-950/40 border-cyan-500/30` | 4K UHD badges, stream telemetry, speed test, digital releases |
| **Crimson / Rose** | `text-rose-400 bg-rose-950/40 border-rose-500/30` | Prune deletions, Leaving Soon, stream termination, rejected |

---

## 4. Typography Hierarchy

| Level | Tailwind Classes | Usage |
| :--- | :--- | :--- |
| **Page Title** | `text-2xl sm:text-3xl font-extrabold text-white tracking-tight` | Main page headers (`/library`, `/settings`) |
| **Card Title** | `text-base sm:text-lg font-bold text-white` | Section card headers |
| **Body Primary** | `text-xs sm:text-sm text-slate-200 leading-relaxed` | Descriptions, labels, table rows |
| **Body Secondary** | `text-[11px] sm:text-xs text-slate-400` | Subtitles, help captions, timestamps |
| **Badge / Label** | `text-[10px] font-bold uppercase tracking-wider` | Corner chips, format tags, statuses |
| **Monospace** | `font-mono text-xs text-slate-300` | IDs, tokens, paths, bitrates, hashes |
