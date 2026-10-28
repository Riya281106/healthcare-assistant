# Update: multilingual care navigation, hospital discovery, booking help

## How to apply
1. Unzip over `C:\Users\RIYA\healthcare-assistant` and choose "replace files".
2. Add to `backend\.env`:  `GOOGLE_PLACES_API_KEY=<your key>`  (Google Cloud -> enable "Places API").
   Without it, hospital search says it is not set up. It never shows made-up hospitals.
3. No new Python packages. Restart backend and frontend (`npm run dev`).
4. Tests: `cd backend` then `python -m pytest` (expected: 160 passed).

## What was found in the existing code (Phase 1-2)
- Working: FastAPI + SQLite, auth, emergency detector, risk tiers, RAG (ChromaDB), reminders, records, memory.
- BUG: the emergency detector did NOT flag "I suddenly lost vision in one eye" (fixed, see below).
- `agents/agentic_orchestrator.py` is not used by `/api/chat` and cannot even be imported
  (it needs `generate_with_tools`, which does not exist). Left untouched.
- Hospital agent: fixed city list only, no PIN support, local table empty, no booking links.
- Each LLM agent forced "reply in the language of the message", so a language selector or
  "explain in Marathi" could not work. Now the selected language wins.
- GitHub default branch is `master`; your pushes go to `main`.

## What changed
| Area | Files |
|---|---|
| Eye emergencies (sudden vision loss, chemical, object, Hindi/Hinglish/Marathi) | `utils/red_flag_rules.py`, `utils/emergency_detector.py`, `agents/emergency_agent.py` |
| Language detect / switch / selector (en, hi, mr, Hinglish; other Indian scripts detected) | `utils/language.py`, `llm/service.py`, `llm/client.py`, 7 agent prompts |
| Emergency replies in Hindi / Marathi / Hinglish (fixed text, no LLM) | `utils/messages.py`, `agents/emergency_agent.py` |
| Care navigator (red-flag question -> PIN/area -> up to 5 results -> booking) | `agents/care_navigator.py`, `facilities/specialty.py` |
| Real booking-link lookup on the hospital's own website (SSRF-guarded) | `facilities/booking_finder.py` |
| Search failure vs zero results | `integrations/google_places.py` (`search_places_checked`) |
| Saved PIN / language / last results, view + delete | `session_context.py`, `core/database.py` (table `session_state`), `main.py` |
| Plain text, no `**` / `##` | `utils/text_format.py`, `orchestrator.py` |
| UI: language selector, location box, facility cards, booking button | `frontend/src/ChatExtras.jsx`, `App.jsx`, `api.js`, `App.css` |
| Tests A-L + unit tests (44 new) | `tests/test_care_navigation.py` |

## Test results (Phase 10)
Backend: 160 passed (116 existing + 44 new). Frontend: production build succeeds, 0 lint errors in changed files.

| Test | Result | What it proves |
|---|---|---|
| A Hinglish eye pain | pass (stubbed LLM) | detected as Hinglish; model told to reply in Hinglish |
| B Switch to Marathi | pass (stubbed LLM) | switch works, history passed, choice persists |
| C Hypertension | pass (stubbed retrieval) | only really retrieved sources are returned |
| D Not in knowledge base | pass (stubbed retrieval) | no sources, no context presented as evidence |
| E Sudden vision loss | pass | emergency in en/hi/mr/Hinglish; no search, no LLM |
| F Eye pain + find hospitals | pass | red-flag question first, then asks PIN |
| G PIN results | pass (stubbed Places) | max 5, nothing invented, missing fields labelled |
| H Booking | pass (stubbed Places/websites) | verified link, external provider flagged, phone fallback |
| I Saved location | pass | PIN reused, only saved when user says they live there |
| J Concise / plain text | partly | Markdown removed; brevity depends on the real model |
| K Tool failure | pass | clear message, no fabricated results; failure != zero results |
| L "I booked it" | pass | never confirms a booking |

## NOT tested / still needed (be honest about this)
- Never run against real Groq or real Google Places. Test A-D wording quality and real result
  accuracy need a manual run with your keys.
- Booking-link finder reads the hospital homepage only. Many hospital sites load booking with
  JavaScript, so "not verified" will be common. That is the honest result, not a bug.
- Hindi and Marathi texts were written by an AI and need review by a native speaker.
  Emergency / first-aid wording needs review by a doctor. Non-English emergency replies are
  shorter than the English ones (general instructions, plus an eye-specific line).
- Hindi vs Marathi for very short Devanagari messages can be mis-detected; the selector fixes it.
- Red-flag question is answered by simple yes/no patterns, not understanding.
- Rule-based emergency detector can false-alarm (e.g. "I suddenly lost my phone, can't see it").
- Not built: agentic LLM tool loop wiring, reminders from booking, real appointment APIs,
  hospital verification beyond Google listing data, chat-history display of facility cards after reload.
- Facility data is Google Maps listing data. Phone/timing may be outdated; the reply says so.
- Rate limit and state are per server process / SQLite file.

## Fixes after the first live run (28 Oct 2026)
- Test D: retrieval stub now covers lazily imported agents; knowledge-base cutoff lowered to 1.0 (`RAG_DISTANCE_CUTOFF`);
  non-English questions are translated to English before the knowledge-base search. Re-run `python calibrate.py` to tune.
- After a failed/unconfigured hospital search the flow no longer stays "waiting for a location" (it used to hand
  "book hospital 2" to the old agent). A booking request or new search is no longer swallowed while waiting for a location.
- "andheri east mumbai 400093" keeps both the place and the PIN.
- The Google Maps suggestion in failure messages is always an English query.
- Language choice is shown in the selector after "reply in Marathi"; choosing Auto by hand clears the saved choice.
- Backend tests: 169 passed.
