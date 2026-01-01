# Screenshot Review Dashboard & Discord Confirmation System

## Overview
Add a frontend admin interface to review OCR-extracted screenshot data alongside original images, with manual editing capabilities. Also add Discord upload confirmation (reaction or message) so users know their screenshots were detected.

---

## Part 1: Discord Upload Confirmation

### Changes to `core/events/handlers/screenshot_monitor.py`

**Add instant confirmation when screenshot is detected:**

```python
async def on_message(self, message: discord.Message):
    # ... existing detection logic ...
    
    if not image_attachments:
        return
    
    # ✨ NEW: Add reaction to confirm screenshot detected
    try:
        await message.add_reaction("✅")  # Or "👍", "❤️", "📸"
    except Exception as e:
        log.warning(f"Failed to add reaction: {e}")
    
    # ... existing batch queue logic ...
```

**Configuration options** (add to `config.yaml`):
```yaml
standings_screenshots:
  confirmation_method: "reaction"  # Options: "reaction", "message", "both"
  confirmation_reaction: "✅"       # Which emoji to use
  confirmation_message: "📸 Screenshot detected! Processing in {batch_window}s..."
```

**Three confirmation modes:**
1. **Reaction** - Quick, non-intrusive (✅ thumbs up)
2. **Message** - Ephemeral reply (visible only to uploader)
3. **Both** - Reaction + ephemeral message

---

## Part 2: Frontend Review Dashboard

### New Page: `dashboard/app/admin/placements/review/page.tsx`

**Route:** `/admin/placements/review`

**Features:**
- List view of pending submissions (needs manual review)
- Side-by-side layout: Screenshot image + Extracted data table
- Player name dropdowns (with fuzzy search)
- Placement number selectors (1-8)
- Confidence indicators (🟢 High, 🟡 Medium, 🔴 Low)
- Approve/Reject/Reprocess buttons
- Batch review mode (review all lobbies in a round)

### Component Structure

```
/admin/placements/review/
├── page.tsx                    (Main review page)
├── [id]/
│   └── page.tsx               (Single submission detail view)
└── components/
    ├── SubmissionList.tsx     (Pending submissions list)
    ├── ReviewCard.tsx         (Side-by-side screenshot + data)
    ├── PlacementEditor.tsx    (Editable data table)
    ├── PlayerAutocomplete.tsx (Player search dropdown)
    └── ConfidenceIndicator.tsx (Visual confidence display)
```

---

## Part 3: Review Dashboard UI Design

### Main Review Page Layout

```tsx
┌─────────────────────────────────────────────────────────┐
│  📊 Screenshot Review Dashboard                         │
│  [Pending (12)] [Validated (45)] [Rejected (3)]        │
└─────────────────────────────────────────────────────────┘

┌──────────────────────┬──────────────────────────────────┐
│  SCREENSHOT IMAGE    │  EXTRACTED DATA                  │
│                      │                                  │
│  [Full Screenshot]   │  Round: Round 1   Lobby: 1      │
│                      │  Confidence: 🟢 92%              │
│                      │                                  │
│  [🔍 Zoom]           │  ┌─────────────────────────────┐ │
│  [💾 Download]       │  │ Place │ Player    │ Points  │ │
│                      │  │   1   │ [Player1▼]│   8    │ │
│                      │  │   2   │ [Player2▼]│   7    │ │
│                      │  │   3   │ [Player3▼]│   6    │ │
│                      │  │  ...                        │ │
│                      │  └─────────────────────────────┘ │
│                      │                                  │
│                      │  [✅ Approve] [✏️ Edit] [❌ Reject]│
└──────────────────────┴──────────────────────────────────┘
```

### Key Components

#### 1. **SubmissionList** (Left sidebar or top)
```tsx
- Filter: Status (Pending/Validated/Rejected)
- Filter: Round (Round 1, Round 2, etc.)
- Filter: Confidence (High/Medium/Low)
- Sort: By confidence, by time, by lobby
- Quick stats: "12 pending, avg confidence: 85%"
```

#### 2. **ReviewCard** (Main content)
```tsx
- LEFT: Screenshot image (zoomable, downloadable)
- RIGHT: Extracted data table
- Header: Round, Lobby, Timestamp, Uploader
- Footer: Action buttons
```

#### 3. **PlacementEditor** (Editable table)
```tsx
- 8 rows (one per placement)
- Columns: Placement | Player | Points
- Player column: Autocomplete dropdown
  - Shows registered players
  - Fuzzy search
  - Highlight confidence: 🟢 Exact, 🟡 Fuzzy, 🔴 No match
- Points auto-calculated (8/7/6/5/4/3/2/1)
- Validation indicators: ⚠️ Duplicate player, ⚠️ Missing placement
```

#### 4. **PlayerAutocomplete**
```tsx
- Combobox with search
- Shows: "PlayerName (aliases: TP1, TestPlayer)"
- Highlights matched characters
- "Add new player" option
- Recent corrections appear first
```

#### 5. **ConfidenceIndicator**
```tsx
- Visual badge: 🟢 92% High | 🟡 75% Medium | 🔴 45% Low
- Breakdown on hover:
  - Classification: 95%
  - OCR Consensus: 90%
  - Player Matching: 88%
  - Structural: 100%
```

---

## Part 4: API Enhancements

### New Endpoints

#### 1. **GET `/placements/pending-review`**
```typescript
// Returns submissions needing manual review
{
  submissions: [{
    id: 123,
    tournament_id: "tourney-001",
    round_name: "Round 1",
    lobby_number: 1,
    image_url: "https://...",
    status: "pending_review",
    overall_confidence: 0.85,
    created_at: "2025-12-27T...",
    placements: [...],
    issues: ["Low player match confidence for Player X"]
  }]
}
```

#### 2. **POST `/placements/batch-validate`**
```typescript
// Approve multiple submissions at once
{
  submission_ids: [123, 124, 125],
  approved: true
}
```

#### 3. **GET `/placements/players/search?q=Player`**
```typescript
// Search registered players for autocomplete
{
  players: [{
    id: "player-001",
    name: "PlayerName",
    aliases: ["TP1", "TestPlayer"],
    match_confidence: 0.95
  }]
}
```

---

## Part 5: Workflow Examples

### Scenario 1: High Confidence Screenshot (Auto-Validated)
```
1. User uploads screenshot to Discord
2. ✅ Bot adds reaction immediately
3. After 30s, batch processes
4. Confidence: 98% → Auto-validated ✅
5. Staff notification: "1 screenshot auto-validated"
6. Data automatically added to scoreboard
```

### Scenario 2: Medium Confidence Screenshot (Manual Review)
```
1. User uploads screenshot to Discord
2. ✅ Bot adds reaction immediately
3. After 30s, batch processes
4. Confidence: 82% → Manual review required ⚠️
5. Staff notification: "1 screenshot needs review"
6. Admin opens review dashboard
7. Admin sees side-by-side view
8. Admin corrects 1 player name
9. Admin clicks "Approve"
10. Data added to scoreboard
```

### Scenario 3: Batch Review (Multiple Lobbies)
```
1. User uploads 4 lobby screenshots
2. ✅ Bot adds reaction to all 4
3. After 30s, batch processes
4. Results: 2 auto-validated, 2 need review
5. Admin opens "Batch Review Mode"
6. Admin reviews lobbies 3 & 4 side-by-side
7. Admin approves both at once
8. All 4 lobbies added to scoreboard
```

---

## Part 6: Tech Stack & Components

### Frontend (Next.js + TypeScript)
- **UI Library:** shadcn/ui (already in use)
- **Key Components:**
  - `Combobox` - Player autocomplete
  - `Dialog` - Confirmation modals
  - `Badge` - Confidence indicators
  - `Table` - Placement data
  - `Button` - Actions
  - `Tabs` - Status filters
- **Data Fetching:** React Query or SWR (for real-time updates)
- **Image Display:** Next.js Image component with zoom library

### Backend (FastAPI)
- **New Models:** Already created (`PlacementSubmission`, `RoundPlacement`)
- **New Endpoints:** List pending, batch validate, player search
- **WebSocket (Optional):** Real-time status updates

---

## Part 7: Implementation Steps

### Phase 1: Discord Confirmation (30 min)
1. Update `screenshot_monitor.py` with reaction logic
2. Add configuration to `config.yaml`
3. Test: Upload screenshot, verify ✅ reaction

### Phase 2: API Endpoints (1 hour)
1. Create `/placements/pending-review` endpoint
2. Create `/placements/batch-validate` endpoint
3. Create `/placements/players/search` endpoint
4. Test with Postman/curl

### Phase 3: Frontend Components (3-4 hours)
1. Create `SubmissionList` component
2. Create `ReviewCard` component
3. Create `PlacementEditor` component
4. Create `PlayerAutocomplete` component
5. Create `ConfidenceIndicator` component

### Phase 4: Main Review Page (2-3 hours)
1. Create `/admin/placements/review/page.tsx`
2. Wire up data fetching
3. Implement approve/reject handlers
4. Add navigation to dashboard

### Phase 5: Testing & Polish (1-2 hours)
1. Test full workflow end-to-end
2. Add loading states
3. Add error handling
4. Polish UI/UX

**Total Estimated Time:** 7-10 hours

---

## Part 8: Configuration

### Add to `config.yaml`:
```yaml
standings_screenshots:
  enabled: true
  
  # Discord confirmation
  confirmation_method: "reaction"  # "reaction", "message", "both"
  confirmation_reaction: "✅"
  confirmation_message: "📸 Screenshot detected! Processing in {batch_window}s..."
  
  # Review dashboard
  review_page_enabled: true
  batch_review_enabled: true
  auto_validate_threshold: 0.98
  
  # ... existing config ...
```

---

## Part 9: Future Enhancements

### Optional Features (Can be added later):
1. **Keyboard Shortcuts** - `↑/↓` to navigate, `A` to approve, `R` to reject
2. **Image Annotation** - Draw boxes around extracted data
3. **OCR Reprocessing** - "Try Again" button with different settings
4. **Learning System** - Train from corrections (already in DB schema)
5. **Multi-Admin Review** - Prevent conflicts when multiple admins review
6. **Mobile Support** - Responsive design for tablet review
7. **Audit Log** - Track who approved/rejected what

---

## Summary

### What You Get:
✅ **Discord confirmation** - Users see ✅ reaction when screenshots detected  
✅ **Review dashboard** - Side-by-side screenshot + data view  
✅ **Manual editing** - Fix OCR mistakes with dropdowns  
✅ **Confidence indicators** - Visual 🟢🟡🔴 badges  
✅ **Batch approval** - Review multiple lobbies quickly  
✅ **Player autocomplete** - Fuzzy search with aliases  
✅ **Auto-validation** - High confidence → skip review  

### Files to Create:
- `dashboard/app/admin/placements/review/page.tsx`
- `dashboard/app/admin/placements/review/[id]/page.tsx`
- `dashboard/components/placements/SubmissionList.tsx`
- `dashboard/components/placements/ReviewCard.tsx`
- `dashboard/components/placements/PlacementEditor.tsx`
- `dashboard/components/placements/PlayerAutocomplete.tsx`
- `dashboard/components/placements/ConfidenceIndicator.tsx`

### Files to Modify:
- `core/events/handlers/screenshot_monitor.py` (add reaction)
- `api/routers/placements.py` (add 3 new endpoints)
- `config.yaml` (add confirmation settings)
- `dashboard/app/dashboard/page.tsx` (add "Review" tab)

Ready to implement? 🚀