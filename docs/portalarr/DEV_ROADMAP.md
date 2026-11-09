# 🛠️ Developer Roadmap & Maintenance Backlog

This document tracks prioritized backend fixes, scheduler alignment, and maintenance tasks scheduled for upcoming development sessions.

---

## 🎯 High-Priority Fixes (Scheduled for Next Session)

### 🔄 1. Self-Collision in Background Scheduler (Curation / Overlays)

**Status:** Completed (Fixed in v1.3.81)  
**Impact:** Automated runs execute smoothly on schedule without internal self-collision.  
**Target Files:**
- [`src/lib/prisma.ts`](file:///C:/Users/kyraj/Documents/Github/portalarr/src/lib/prisma.ts#L2321) (lines 2321, 2350, 2379, 2408)
- [`src/app/curation-actions.ts`](file:///C:/Users/kyraj/Documents/Github/portalarr/src/app/curation-actions.ts#L7483)

#### Observed Behavior
Every ~55 minutes, the system logs record:
```text
[CURATION] [WARN] Incremental overlay scan: | An overlay scan task is already in progress.
[CURATION] [WARN] Collection sync: | An Agregarr collection sync task is already in progress.
```

#### Root Cause Analysis
In `src/lib/prisma.ts` at line 2321, the background timer sets:
```typescript
(global as any).__PORTALARR_OVERLAY_INC_RUNNING = true;
```
immediately before calling `runOverlayIncrementalSyncInternal()`.

However, `runOverlayIncrementalSyncInternal()` in `src/app/curation-actions.ts` at line 7483 performs its own internal mutex guard check:
```typescript
if ((global as any).__PORTALARR_OVERLAY_INC_RUNNING) {
    logger.addLog("WARN", "CURATION", "Incremental overlay scan: | An overlay scan task is already in progress.");
    return { success: false, message: "An overlay scan task is already in progress." };
}
```
Because the caller already flipped the flag to `true`, the function immediately detects itself as "already running" and aborts before executing. The same pattern repeats for the Agregarr collection sync timer at line 2350 (`__PORTALARR_COLLECTION_SYNC_RUNNING`).

#### Resolution Implemented
Removed the premature `(global as any).__PORTALARR_... = true` assignments inside the timer callbacks in `src/lib/prisma.ts`. The outer lock is held by `setCurationTaskRunning`, allowing the invoked internal functions (`runOverlayIncrementalSyncInternal`, etc.) to cleanly control their own mutex acquisition and release in their `try ... finally` blocks.

---

### 🌐 2. Plex Server Isolation In-Flight Connection Resolution Debouncing

**Status:** Completed (Fixed in v1.3.81)  
**Impact:** Bursts of duplicate connection resolution logs eliminated; parallel queries share in-flight pings.  
**Target Files:**
- [`src/lib/plex.ts`](file:///C:/Users/kyraj/Documents/Github/portalarr/src/lib/plex.ts#L1169) (`resolveWorkingPlexServerConnection`)

#### Observed Behavior
Burst of 15–20 identical logs in under 160ms on dashboard load:
```text
[PLEX] [INFO] [SERVER-ISOLATION] Resolved verified working connection for Plex server "Main Server" (ab32d8af...): http://192.168.1.87:32400
[PLEX] [INFO] [SERVER-ISOLATION] Resolved verified working connection for Plex server "Kids Server" (8cc01505...): http://192.168.1.66:32400
[PLEX] [INFO] [SERVER-ISOLATION] Resolved verified working connection for Plex server "Backup Server" (d268f4ed...): http://192.168.1.66:24958
```

#### Root Cause Analysis
When 7 components or poster endpoints (`/api/media/image`) fire in parallel on initial page load, all 7 execute `resolveWorkingPlexServerConnection` within the same ~30ms before the first network probe finishes and populates `resolvedServerCache`. All 7 probes succeed and each independently writes an `INFO` entry to the persistent system log.

#### Planned Fix
1. Add in-flight Promise memoization:
   ```typescript
   const inFlightConnections = new Map<string, Promise<ResolvedPlexConnection | null>>();
   ```
   If a probe for `cacheKey` is already in flight, subsequent callers await that existing Promise instead of launching concurrent probes.
2. Throttled Logging: Only dispatch `logger.addLog("INFO", "PLEX", ...)` if the resolved URL has changed or on initial server discovery, suppressing duplicate logs for the same connection.

---

### 📚 3. Audiobook Storage Path Mount Audit

**Status:** Diagnostics  
**Target Files:**
- `src/lib/curation/audiobook-scanner.ts`
- Docker Volume Mounts / Disk Paths

#### Observed Behavior
```text
[AUDIOBOOKS] [WARN] Wipe protection triggered: Scanner found 0 files on disk for path "/Kyrabooks/audiobooks"
```

#### Planned Action
Verify host-to-container mount paths in `docker-compose.yml` to confirm that the `/Kyrabooks/audiobooks` directory is properly mounted into the Portalarr container and accessible.

---

### 📬 4. Secondary & Linked Notification Inboxes (Family & Alternate Email Routing)

**Status:** Completed (Shipped in v1.4.0)  
**Priority:** High  
**Target Subsystems & Files:**
- `prisma/schema.prisma` (`UserLinkedEmail` model + relation in `User`)
- `src/app/actions.ts` (`sendEmailAction`, `getLinkedEmailsAction`, `addLinkedEmailAction`, `updateLinkedEmailRoutingAction`, `deleteLinkedEmailAction`)
- `src/app/profile/page.tsx` (`/profile` & `/settings/profile` notification management card)
- `src/app/payment-actions.ts` (subscription renewal reminder multi-dispatch)
- `src/components/sent-email-audit-log.tsx` (audit logging with recipient tag)

#### 1. Problem Statement & Real-World Use Cases
- **Plex Login Email Decoupling:** Many users registered on Plex with burner, placeholder, or unmonitored email addresses (e.g. `plexuser99@gmail.com`). They need critical server announcements and maintenance alerts forwarded to their actual daily inbox.
- **Spouse / Household Billing Sharing:** A subscriber wants their spouse or partner to receive subscription renewal reminder notices (so whoever handles the household budget sees the upcoming bill) without sharing personal Portalarr account passwords.
- **Media Fulfillment Sharing:** A family member who frequently requests media wants email notifications when requested movies/shows finish downloading, while another family member only cares about platform downtime announcements.
- **Granular Opt-In Matrix:** Each linked email address must have independent checkboxes for every email category, preventing inbox spam for recipients who only want specific notifications.

#### 2. Data Model Design (`prisma/schema.prisma`)
```prisma
model UserLinkedEmail {
  id                           String   @id @default(cuid())
  userId                       String
  user                         User     @relation("UserLinkedEmails", fields: [userId], references: [id], onDelete: Cascade)
  email                        String
  label                        String?  // e.g. "Spouse (Sarah)", "Work Inbox", "Partner"
  isVerified                   Boolean  @default(true) // Auto-verified for active subscribers
  
  // Granular Delivery Category Toggles
  receiveSubscriptionReminders Boolean  @default(true)  // Invoices, payment receipts, renewal notices
  receiveAnnouncements         Boolean  @default(true)  // Server maintenance & downtime alerts
  receiveMediaReady            Boolean  @default(false) // Media downloaded & ready to stream
  receiveRequestApproved       Boolean  @default(false) // Requests approved by admin
  receiveNewContent            Boolean  @default(false) // Weekly library digests & recommendations
  receiveSupportTickets        Boolean  @default(false) // Support ticket replies & resolutions

  createdAt                    DateTime @default(now())
  updatedAt                    DateTime @updatedAt

  @@unique([userId, email])
  @@index([userId])
}
```

#### 3. Dispatch Engine Integration (`sendEmailAction`)
- When an email event triggers (e.g. `subscription_renewal_reminder` or `broadcast_announcement`), the engine resolves the target `user` record.
- If the user has linked emails with that category enabled (`linked.receiveSubscriptionReminders === true`), the engine dispatches a tailored copy to each linked recipient with:
  - Personal salutation: `Hi [Label or Name],`
  - Contextual delivery disclaimer: `"You received this notification because [User] added this email address for [Category] alerts on DomsHomeLab."`
  - Safe 1-click unsubscribe token link: allows the secondary recipient to opt out of future emails without affecting the primary user's account.

#### 4. Frontend UX / UI in Account Settings (`/profile`)
- Mount a new section in `/profile`: **"📬 Additional Notification Inboxes & Family Routing"**.
- Displays each linked email with its custom label (e.g. `sarah@gmail.com • Sarah (Spouse)`).
- Category badges showing active routing (e.g. `[💳 Renewals] [🎬 Media Ready] [📢 Announcements]`).
- Interactive modal to adjust checkboxes per category or delete linked inboxes.
- "Add Alternate Email" button with instant email format validation and duplicate prevention.

