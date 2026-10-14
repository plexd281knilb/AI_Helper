# How to Update and Tweak This Skill

The `portalarr-ui` skill is designed to be a living specification. As you refine user interfaces, establish new design decisions, or adjust layout preferences for Portalarr, you can update this skill directly.

---

## 1. When to Update This Skill

Update this skill whenever:
1. **A UI component is finalized and working well**: Document the exact class names, dimensions, and structural layout as a golden standard.
2. **A layout bug or gotcha is solved**: (e.g. Radix dialog width override, `onMouseDown` on autocomplete items, line clamping long subtitles) so future coding sessions never regress.
3. **New color tokens or design variants are added**: (e.g. new ribbon templates, badge positions, or chart styles).
4. **New pages or studios are introduced**: (e.g. Wizarr onboarding portal, Uptime monitoring dashboard).

---

## 2. Directory Structure

```text
.agents/skills/portalarr-ui/
├── SKILL.md                                 # High-level overview, core rules, and quick cheat-sheet
└── references/
    ├── modal-and-dialog-patterns.md         # Dialog widths, backdrop hero layouts, trailer embeds
    ├── card-and-poster-patterns.md          # 2:3 aspect ratios, badge placement, line clamping
    ├── form-and-input-patterns.md           # Autocomplete, dirty state highlights, token inputs
    ├── theme-and-color-tokens.md            # Background shades, border colors, semantic accents
    └── updating-this-skill.md               # This maintenance guide
```

---

## 3. Step-by-Step Guide to Making Changes

### Step 1: Add or Modify Rules in `SKILL.md`
If it's a fundamental rule (e.g. "All detail modals must use responsive width prefixes `sm:max-w-4xl lg:max-w-6xl`"), add it under **Key Layout & Component Rules** in [SKILL.md](../SKILL.md).

### Step 2: Add Code Examples to Reference Files
If you are tweaking a specific pattern:
- Modals / Dialogs → [modal-and-dialog-patterns.md](./modal-and-dialog-patterns.md)
- Posters / Media Cards → [card-and-poster-patterns.md](./card-and-poster-patterns.md)
- Forms / Inputs / Autocomplete → [form-and-input-patterns.md](./form-and-input-patterns.md)
- Colors / Typography → [theme-and-color-tokens.md](./theme-and-color-tokens.md)

### Step 3: Create New Reference Files for New Features
When adding a new major section (e.g. `references/data-tables-and-lists.md` or `references/audio-player-controls.md`):
1. Create the new markdown file under `.agents/skills/portalarr-ui/references/`.
2. Link it in the **Reference Documents** list at the bottom of [SKILL.md](../SKILL.md).

---

## 4. Prompting the Agent to Update the Skill

You can tell the AI assistant at any time:
> *"I really like how the episode guide modal turned out in `src/components/seerr/media-detail-modal.tsx`. Please update the `portalarr-ui` skill to document this layout pattern for future modals."*

The assistant will read the component, extract the layout principles, and update the skill files automatically.
