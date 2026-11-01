# Final update (31 Oct 2026)

## How to apply
1. Unzip over `C:\Users\RIYA\healthcare-assistant` and choose "replace files".
2. Add to `backend\.env` (see `backend\.env.example`): `DATA_ENCRYPTION_KEY`, `DEMO_PARTNER_ENABLED=1`.
3. `cd backend`, then `pip install -r requirements.txt` (python-jose is now 3.5.0).
4. `cd backend`, then `python -m pytest` (expected: 351 passed) and `python eval_safety.py`.
5. Restart backend and frontend. Existing users stay logged in.
6. You are on branch `fixes/critical`. Commit, push, open a pull request and merge it into the default branch so GitHub shows this version.

## What changed
* Emergency detector: new rules (self-harm phrasings, overdose counts, vomiting blood, snake bite, drowning, newborn fever, pregnancy bleeding, stroke and cardiac phrasings); a normal dose ("took 2 tablets of paracetamol") no longer fires; three new first-aid texts. `tests/safety_cases.py` + `eval_safety.py` measure it.
* Hospital search: Maharashtra only; up to 10 results; nearest-first ranking with contact details preferred; general hospitals fill remaining places and are labelled; directions link; "find phone" link when no number; 10-minute cache; wider radius steps.
* Appointment requests: new `appointment_flow.py` (offer, 5 questions, validation, summary, confirmation, list, cancel), demo partner hospital, encrypted details, audit events.
* Agent transparency: replies carry a short "How I handled this" trace and tap-to-answer quick replies.
* Security: login/sign-up rate limits, equal-time login errors, emergency rate limit, security headers, no-store caching, CORS from `.env`, no re-raise of internal errors, last-resort emergency reply, patched python-jose, delete-my-data endpoint, memory/health extraction moved off the reply path.
* Frontend: Call / Directions / Find phone / Select-and-book buttons, quick replies, appointment card, trace panel, erase-my-data and appointments in the side panel.

## Not done / still needed
* Not run against the live OpenStreetMap servers from here (tests stub them). Run `python osm_check.py` and one real search before the viva.
* Not run against real Groq.
* The appointment form is English only. Hindi and Marathi texts need a native speaker; first-aid wording needs a doctor.
* Admin email takeover: registration still does not verify email ownership. Register your admin account first.
* `agentic_orchestrator.py` is still unused and not importable; delete it or leave it.
