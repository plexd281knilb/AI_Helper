# Form & Input Design Patterns in Portalarr

Settings, access control, media request forms, curation filters, and integration setups follow structured form patterns to ensure clarity, immediate validation feedback, and data safety.

---

## 1. Autocomplete & Dropdown Lists (`onMouseDown`)

When building suggestion dropdowns (e.g. Title/Author autocomplete, Plex server chooser, TMDb quick-search):
- **CRITICAL**: Use `onMouseDown` instead of `onClick` on dropdown suggestion items!
- **Why**: When an `<input />` has an `onBlur` handler that closes the dropdown, a user's click triggers `onBlur` on the input *before* the `onClick` event fires on the list item, causing the suggestion item to unmount prematurely. `onMouseDown` fires *before* `onBlur`, ensuring the item selection registers reliably every time.

```tsx
<div
  key={item.id}
  onMouseDown={(e) => {
    e.preventDefault(); // Prevents input blur
    handleSelectItem(item);
  }}
  className="px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 hover:text-amber-400 cursor-pointer flex items-center justify-between transition-colors"
>
  <span>{item.title}</span>
</div>
```

---

## 2. Dirty State Warnings & Unified `UnsavedChangesPrompt` System

To prevent users from losing unpersisted settings changes when navigating across tabs or pages, all settings and configuration surfaces in Portalarr adhere to a standardized unsaved changes alert system:

1. **Dirty Detection**: Compare current component states against an `initialDataRef` snapshot taken on page load and updated upon successful saves.
2. **Visual Card Highlight**:
   ```tsx
   <Card className={`transition-all duration-300 ${isDirty ? 'border-2 border-amber-500/70 shadow-[0_0_20px_rgba(245,158,11,0.2)]' : 'border-border/50'}`}>
   ```
3. **Card Header Badge**:
   ```tsx
   {isDirty && (
       <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/30 font-medium ml-2 animate-in fade-in">
           ● Unsaved Changes
       </Badge>
   )}
   ```
4. **Tab Switch & In-App Navigation Interception**:
   - Tab triggers display a pulsing amber dot: `{isTabDirty && <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse ml-1 shrink-0" />}`.
   - If switching tabs while dirty, intercept with confirmation before switching.
5. **Unified `<UnsavedChangesPrompt />` Component**:
   Located at `@/components/ui/unsaved-changes-prompt`.
   - **Floating Docked Save Bar**: Fixed at `bottom-6 right-6 z-50` with an animated amber ping, list of modified sections, "Discard" button, and "Save All Changes" button.
   - **Browser Navigation Guard**: Registers `beforeunload` listener while dirty to prevent accidental page refresh or tab close.
   - **Link Click Interception**: Intercepts in-app `<a>` navigation, displaying a modal dialog with 3 options:
     - "Stay on Page" (dismisses dialog)
     - "Discard & Leave" (discards changes and navigates to target)
     - "Save & Continue" (saves changes, updates snapshot, and navigates to target)
   ```tsx
   <UnsavedChangesPrompt
       hasUnsavedChanges={hasUnsavedChanges}
       unsavedSections={unsavedSections}
       onSave={handleSaveAllDirty}
       onDiscard={handleDiscardAll}
       isSaving={saving}
   />
   ```

### ⚠️ Critical Gotcha: Never Wrap Mutable Ref Comparisons in `useMemo`
- **The Bug**: Wrapping dirty checks like `const isDirty = useMemo(() => JSON.stringify(data) !== JSON.stringify(initialRef.current), [data])` fails to reset on save. When the save action updates `initialRef.current = clonedData` without changing the `data` state reference, React's `useMemo` dependencies have not changed, returning the stale cached `true` value. The card stays permanently locked in an amber glow (`● Unsaved Changes`).
- **The Fix**: Evaluate dirty states as **direct booleans** during render (`const isDirty = Boolean(...)`) or ensure state references are updated/cloned.
- **Array Equality**: For multiselect or checkbox arrays (e.g., library selections, channels), compare sorted elements (`[...a].sort().join(',') === [...b].sort().join(',')`) so order differences do not trigger false dirty states.

---

## 3. Prorated Subscription Billing Display & Math

When displaying live prorated billing calculations (e.g. on `/settings/access`, `/pending`, and onboarding):
- **Annual Plan Proration**:
  - Derived strictly from the yearly price divided by 12 (`annualMonthlyRate = yearlyRate / 12`).
  - Daily rate: `dailyRate = annualMonthlyRate / daysInMonth`.
  - Amount due now covers remaining days in the trial-end month plus all remaining full months in the calendar year.
- **Standalone Monthly Plan**:
  - Displays `standaloneMonthlyRate` (e.g. `$17.50/mo`, independent of annual proration).
  - Daily rate: `monthlyDailyRate = standaloneMonthlyRate / daysInMonth`.
  - Amount due now: `standaloneMonthlyRate * (daysRemaining / daysInMonth)`.
  - Day range labels must NEVER prefix day numbers with a dollar sign (e.g. `(15–31)`, not `($15–31)`).
  - All preview badges, daily rates, and renewal labels for the monthly plan MUST use `standaloneMonthlyRate` and `monthlyDailyRate`, reserving `annualMonthlyRate` and `dailyRate` strictly for the annual plan.

---

## 4. Sensitive Tokens & Password Visibility

- Mask tokens by default (`type="password"`).
- Provide an inline visibility toggle with Lucide `<Eye />` / `<EyeOff />`.
- Use a mono font for tokens, hashes, and URLs (`font-mono text-xs`).

```tsx
<div className="relative">
  <Input
    type={showToken ? "text" : "password"}
    value={token}
    onChange={(e) => setToken(e.target.value)}
    className="bg-slate-950 border-slate-700 pr-10 font-mono text-xs text-slate-200"
  />
  <button
    type="button"
    onClick={() => setShowToken(!showToken)}
    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
  >
    {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
  </button>
</div>
```

---

## 5. Live Connection Diagnostic Buttons ("Test")

All third-party integration fields (Plex, Tautulli, Glances, Radarr, Sonarr, Prowlarr, SABnzbd, qBittorrent, SMTP, IMAP) must feature a live `"Test"` button that calls the backend diagnostic server action with immediate feedback badges (🟢 Connected vs 🔴 Connection Failed with detailed error text).

---

## 6. Standard Input Sizing & Styling

- **Standard Inputs**: `h-9 text-xs sm:text-sm bg-slate-950 border-slate-700 text-slate-100 rounded-lg placeholder:text-slate-500 focus:border-amber-400 focus:ring-1 focus:ring-amber-400`.
- **Compact Inputs / Select Triggers**: `h-8 text-xs bg-slate-900 border-slate-700 text-slate-200 rounded-md`.
- **Field Labels**: `text-xs font-semibold text-slate-300 flex items-center gap-1.5`.
- **Help / Description Text**: `text-[11px] sm:text-xs text-slate-400 leading-relaxed`.

---

## 7. Radix `SelectTrigger` Width & Truncation Guard

In Radix UI Select components:
- `SelectTrigger` MUST default to `w-full min-w-0` and enforce `*:data-[slot=select-value]:truncate` so that long option texts (e.g. `"🌙 Daily at 4:00 AM (Recommended for Deep Overlays)"`) truncate gracefully with ellipsis (`...`) instead of expanding and overflowing into neighboring columns.
- The chevron icon should have `shrink-0` to avoid being squished by long truncated text:
  ```tsx
  <SelectTrigger className="w-full min-w-0 bg-slate-900 border-slate-700 text-xs h-8 text-slate-200 truncate">
    <SelectValue placeholder="Select Option" />
  </SelectTrigger>
  ```

---

## 8. Studio Schedule & Multi-Parameter Automation Layouts

When designing side-by-side automation cards (`grid-cols-1 lg:grid-cols-2`):
- Avoid forcing 3 dropdowns side-by-side in a 3-column row (`sm:grid-cols-3`), as each column receives only ~140px-160px.
- **2-Row Stacking Pattern**:
  - **Row 1 (Full width / `sm:col-span-2`)**: Primary Schedule Frequency dropdown (gives ample breathing room for descriptive frequency labels).
  - **Row 2 (`grid grid-cols-1 sm:grid-cols-2 gap-2.5`)**: Secondary parameters side-by-side (e.g. Recheck Scope & Batch Size).
- Ensure all grid columns and wrapper containers specify `min-w-0` to prevent CSS Grid blowouts.

---

## 9. Account Settings, Sub-Account Profile Safety & Password Confirmation

- **Password Changes with Confirmation**: Always provide a "Confirm New Password" field alongside the "New Password" field to prevent accidental typo lockouts. Both fields (plus the current password field) should feature inline `<Eye />` / `<EyeOff />` visibility toggles, standard `min-length` checks, and client-side mismatch alerts before dispatching to backend server actions.
- **Multi-Profile Dirty State Tracking**: When an account settings page allows switching between active sub-profiles (e.g. Primary Account, Living Room TV Profile, Kid Profile), track initial snapshots per profile ID (`initialSafetyPrefsRef.current[profileId]`). This ensures editing a sub-profile's content safety switches (e.g. `requireApproval`, `allowMatureContent`, strictness levels) marks the form dirty, enables the floating save prompt, and allows discarding or persisting without mutating or dropping other profiles.
- **Kindle Direct Download Bypass Mode**: When users lack an `@kindle.com` email address, allow activating a `"DIRECT_DOWNLOAD"` bypass mode. In bypass mode, the email input is disabled/hidden, the dirty tracker evaluates bypass state against the initial snapshot rather than stale input text, and the submit button enables only when an actual change is detected.
- **Section-Level Library Comparison**: When comparing user Plex library selections against initial state, evaluate selected status at the library item / section level rather than comparing raw strings or unnormalized IDs, preventing false dirty states caused by variations in composite ID formats (`"serverId:sectionId"` vs `"sectionId"`).

