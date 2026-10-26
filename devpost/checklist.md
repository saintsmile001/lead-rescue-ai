---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

## Slices

- [x] **1. Project scaffold, canonical triage engine, seeded sample data & automated test suite**
  Becomes usable: The core triage and metric engine can be run and tested mechanically via `pytest test_triage.py`, proving all rules (high-priority quotes >= 3 days, medium-priority inquiries >= 2 days, recent leads, won leads, and metric subset hierarchy).
  Why now: Proves the foundational deterministic logic and metric calculations with automated tests before adding server and UI layers, bootstrapping the repository cleanly.
  PRD ref: `prd.md > 1. Deterministic Lead Triage & Urgency Rules`, `prd.md > 2. Lead List & Seeded Sample Data`
  Spec ref: `spec.md > Canonical Lead Triage & Metrics Engine (triage.py)`, `spec.md > Automated Test Plan (test_triage.py)`
  Build: Create `requirements.txt`, `.env.example`, `.env` (holding `GEMINI_API_KEY`), `sample_data.py` (5 realistic plumbing leads), `triage.py` (canonical triage rules and metrics), and `test_triage.py`. Install dependencies and run tests.
  Verify (mechanical): Run `pytest test_triage.py` and confirm all 7 test cases pass.
  Learner check: Run `pytest` in your terminal and verify that all lead triage rules, edge cases, and metric calculations pass cleanly.
  Commit: `Initialize project and canonical lead triage engine with automated tests`

- [x] **2. Dual-mode follow-up generator with Gemini API and template fallback**
  Becomes usable: Running `generator.py` produces personalized follow-up messages for any lead in 3 tones (Friendly Check-in, Gentle Nudge, Value-Focused), both with Gemini AI (when configured) and via deterministic template fallback (when unconfigured or offline), returning `{ message, source }`.
  Why now: Proves the unique kernel (context-aware revival message generation) and validates the AI integration and template fallback safety net early.
  PRD ref: `prd.md > 3. Dual-Mode Follow-up Message Generation`
  Spec ref: `spec.md > Message Generation Engine (generator.py)`, `spec.md > External Services and Dependencies`
  Build: Implement `generator.py` with `generate_followup_message(lead, tone)` supporting both Gemini API (`GEMINI_MODEL`, `GEMINI_API_KEY`) and deterministic template fallback. Add test cases in `test_triage.py` to verify message generation in both modes across all 3 tones.
  Verify (mechanical): Run `pytest test_triage.py` asserting non-empty message generation and accurate source attribution (`"ai"` or `"fallback"`).
  Learner check: Inspect generated follow-up messages for friendly, nudge, and value-focused tones and confirm they sound natural and professional.
  Commit: `Add dual-mode follow-up message generator with Gemini integration and fallback`

- [x] **3. FastAPI server, REST endpoints, and static file delivery**
  Becomes usable: Running `python main.py` serves `GET /api/leads`, `POST /api/triage`, `POST /api/generate`, `GET /api/health`, and mounts the static web frontend root.
  Why now: Connects the triage engine and generator behind a clean, secure local REST API, ensuring the Gemini API key stays strictly on the backend.
  PRD ref: `prd.md > Screens and Layout`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > Backend API Server (FastAPI)`
  Build: Implement `main.py` with FastAPI endpoints, CORS, static directory mounting, and graceful exception handling.
  Verify (mechanical): Launch the server with Uvicorn, query `GET /api/health`, `GET /api/leads`, and `POST /api/generate` with HTTP tests, verifying 200 OK responses and proper JSON payloads.
  Learner check: Open `http://127.0.0.1:8000/api/health` in your browser and confirm server status, configured model, and API key availability.
  Commit: `Implement FastAPI backend server with REST endpoints and static mounting`

- [x] **4. Interactive split dashboard with live triage, message generation, editing & clipboard copy**
  Becomes usable: A complete end-to-end web dashboard where the operator sees summary metric cards, browses/filters leads, selects a cold lead (e.g., Marcus Vance), generates a tailored revival message with visible source badge, edits it, and copies to clipboard with "Copied!" confirmation.
  Why now: Delivers the core user journey end to end on screen, bringing the UI styling, color hierarchy, and interaction to life.
  PRD ref: `prd.md > The Core Journey`, `prd.md > Screens and Layout`, `prd.md > Look and Feel`, `prd.md > 4. Message Editing & Clipboard Copy`
  Spec ref: `spec.md > Frontend Single-Page Dashboard (HTML/CSS/JS)`, `spec.md > Look and Feel`
  Build: Create `static/index.html`, `static/style.css`, and `static/app.js` with responsive split layout, metric cards, status badges, message generator workshop, tone pills, and copy button.
  Verify (mechanical): Start server, verify HTTP 200 on all static files, and verify DOM elements and event handlers.
  Learner check: Open `http://127.0.0.1:8000`, review the dashboard layout, select Marcus Vance, generate a message, make an edit, and copy it to clipboard.
  Commit: `Build interactive split dashboard with live triage and message workshop`

- [x] **5. Manual lead creation, localStorage persistence, and sample data reset**
  Becomes usable: The operator can click "Add Lead" to open a modal, enter a new customer inquiry, and immediately see the metric counts and lead list update dynamically; edits persist across browser refreshes, and clicking "Reset Sample Data" cleanly restores the original 5 seeded leads.
  Why now: Completes the full proof-of-concept boundary and demo flow without external database complexity.
  PRD ref: `prd.md > 5. Manual Lead Creation & Lean State Management`, `prd.md > States and Boundaries`
  Spec ref: `spec.md > State & Storage Layer (localStorage + Reset Sample Data)`
  Build: Implement "Add Lead" modal in `index.html` and `app.js`, connect `localStorage` caching with fallback to `/api/leads`, and add "Reset Sample Data" action.
  Verify (mechanical): Programmatically add a lead, verify reactive triage calculation, reload page and verify persistence, trigger reset and verify seeded state restored.
  Learner check: Click "Add Lead", add a test lead, confirm it gets triaged with the right urgency tag and updates summary cards, then test "Reset Sample Data".
  Commit: `Add manual lead entry modal, localStorage persistence, and demo reset`

## Hands-on Checkpoints

- [x] Early usable behavior explored — Slice 2 (Generator & Triage verification)
- [ ] Final kick-the-tires exploration and feedback completed

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: [to be populated upon completion]
Route and stops: [to be populated upon completion]
Edit outcome: [to be populated upon completion]
Reflection: [to be populated upon completion]
Activity mode: [to be populated upon completion]

## Revisions
