# Dashboard and Interface Module

## 1. What this module is responsible for

The frontend is not just a visual shell. It is the operational command surface of the product.

Its responsibilities are:

- loading live detections from the backend
- preserving operator selection during polling
- letting the user navigate between panels
- rendering MPAs, detections, scan points, and sweep contacts
- showing evidence and AI explanations without leaving the map
- presenting the product story through the landing page

The main code center is:

- `frontend/src/App.tsx`

Supporting feature files are:

- `frontend/src/components/MapView.tsx`
- `frontend/src/components/EvidenceCard.tsx`
- `frontend/src/components/RiskTable.tsx`
- `frontend/src/components/DailyBriefing.tsx`
- `frontend/src/components/PatrolBoard.tsx`
- `frontend/src/components/AskOceanGuard.tsx`
- `frontend/src/components/LandingPage.tsx`

## 2. The two major frontend surfaces

The app is split into two top-level pages:

- `landing`
- `dashboard`

This state lives in `App.tsx` as:

- `type Page = "landing" | "dashboard"`

### Landing page

Purpose:

- tell the problem story
- explain the system
- give a visually strong demo entry

Key behaviors:

- full-screen hero
- cinematic storytelling
- live ticker strip
- CTA into dashboard
- CTA into demo path

This is a presentation layer, not an operational one.

### Dashboard

Purpose:

- make live detections reviewable and actionable

Key sections:

- header and top navigation
- toolbar and KPI bands
- full-screen map
- left information panels
- right evidence/scan/assistant panels
- footer and responsible-AI notice

## 3. How the dashboard state is designed

The dashboard uses a single coordinating component (`App.tsx`) to manage shared operational state.

This is a deliberate design choice.

Instead of pushing all state down into many unrelated components, the app keeps the important operator context centralized:

- current page
- active dashboard tab
- loaded events
- selected event
- loading and error states
- currently open left panel
- currently open right panel
- point scan state
- area sweep state

This makes cross-panel coordination easier.

For example:

- if the user selects a detection, the Evidence Card should take precedence
- if the user starts a point scan, assistant/evidence should step aside
- if the user starts an area sweep, the sweep result should own the right panel

That orchestration is much easier when the state is held in one place.

## 4. The most important frontend pattern: precedence-based overlays

The dashboard UI is built around overlay precedence.

The right side of the app can show multiple concepts, but only one should dominate at a time.

Current precedence in `App.tsx` is:

1. sweep result
2. scan result
3. assistant
4. evidence card

This solves an important UX problem:

Without precedence, the operator could end up with stacked panels fighting for the same space.

With precedence:

- the current task becomes visually obvious
- the user is less likely to get lost

## 5. How live loading works in the dashboard

The dashboard polls the backend every 30 seconds.

That behavior lives in `App.tsx`.

The logic is:

1. initial load starts
2. `fetchRiskEvents()` is called
3. results are stored in `events`
4. if the currently selected event still exists, keep it selected
5. otherwise choose a sensible default "hero" event
6. repeat every 30 seconds

This is a strong operational pattern because it avoids two bad UX outcomes:

### Bad outcome 1: full reset every poll

If polling replaced all UI state blindly, the officer would lose context every 30 seconds.

### Bad outcome 2: stale context forever

If the selection were never reconciled with the new dataset, the UI could keep referencing a detection that no longer exists.

The current design avoids both.

## 6. How the default highlighted event is chosen

The helper `pickHeroEvent()` is a small but important product decision.

It chooses the strongest candidate for demo and initial focus based on signal quality, not fixed IDs.

Priority order:

1. dark vessel inside an MPA
2. any vessel inside an MPA
3. CRITICAL event
4. HIGH event
5. highest score overall

Why this matters:

- IDs change in live data
- static demo assumptions break
- the product should still open on a compelling event

This is a subtle example of making the demo robust against real live data.

## 7. Map behavior

The map layer lives in `MapView.tsx`.

Key responsibilities:

- render base map
- render risk markers
- render selected state
- render MPA polygons
- accept point-scan clicks
- track viewport bounds
- render sweep rectangle
- render sweep contacts

### Why `MapView` is kept focused

`MapView` does not try to become the whole dashboard.

It does map things only.

That separation is good because:

- map concerns stay local
- non-map panel logic stays in `App.tsx`
- requests to the backend can still be orchestrated centrally

## 8. The MPA map strategy

The frontend does not load all MPAs at once.

Instead:

- `MapView` watches the viewport
- it sends the current bbox to the backend
- the backend returns only intersecting MPAs

Why this is good:

- avoids sending the global WDPA dataset to the browser
- keeps rendering manageable
- makes the app usable on real hardware

## 9. Evidence Card design

`EvidenceCard.tsx` is one of the most important UI files in the whole repo.

It assembles multiple backend features into one review surface:

- event metadata
- SAR image chip
- MPA proximity context
- AIS status
- AI narration
- YOLO confirmation
- review action buttons

This is where the product shifts from "interesting map" to "decision-support tool."

### Why the Evidence Card matters so much

An operator should not have to manually stitch together:

- the map point
- the radar chip
- the explanation
- the review action

The card turns all of that into a single case file.

## 10. Landing page design philosophy

The landing page is not just a generic SaaS hero.

It is intentionally narrative-driven.

It tries to:

- establish the ocean blind-spot problem
- explain the system in steps
- create visual authority
- feel like an operational intelligence product, not a dashboard template

This is why the landing implementation includes:

- hero animation/video
- HUD overlays
- blind-spot visuals
- evidence card mockups
- system stage storytelling

The frontend design is part of the product positioning, not just decoration.

## 11. Mobile responsiveness

The desktop dashboard is the main operational layout.

Mobile support was added later through a responsive shell strategy.

Key changes:

- compact header on smaller screens
- horizontally scrollable top controls
- KPI grid instead of wide KPI row
- bottom-sheet style panels instead of large left/right floating side rails
- card-based detection list on mobile instead of dense table

This keeps the desktop experience intact while still making mobile workable.

That is the right strategy for a dashboard product:

- do not weaken desktop just to force full symmetry
- add a mobile-appropriate interaction model instead

## 12. Frontend technology choices and why they fit

### React

Used for:

- stateful coordination
- conditional rendering
- component composition

Why it fits:

- the dashboard has many interacting panels and states
- the landing page has many animated sections

### Framer Motion

Used for:

- panel transitions
- staged section entrances
- subtle operational motion

Why it fits:

- the product wants motion with meaning, not only CSS hover effects

### Leaflet / React Leaflet

Used for:

- world map
- markers
- polygons
- viewport math

Why it fits:

- mature mapping primitives
- fast enough for this use case
- good custom marker flexibility

### Tailwind

Used for:

- rapid UI iteration
- explicit visual control
- responsive utility classes

Why it fits:

- the project evolved quickly
- custom visual language matters more than abstract design tokens alone

## 13. If you want to modify this module

### Change panel behavior

Start with:

- `frontend/src/App.tsx`

### Change map interactions

Start with:

- `frontend/src/components/MapView.tsx`

### Change detection review experience

Start with:

- `frontend/src/components/EvidenceCard.tsx`
- `frontend/src/components/RiskTable.tsx`

### Change storytelling / pitch experience

Start with:

- `frontend/src/components/LandingPage.tsx`
- `frontend/src/components/landing/*`

## 14. Bottom line

The frontend is not a passive renderer.

It is the operational conductor that:

- keeps live state coherent
- coordinates feature precedence
- turns backend data into reviewable evidence
- makes the product understandable to both officers and demo audiences
