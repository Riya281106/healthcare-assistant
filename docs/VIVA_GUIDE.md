# Viva and implementation review: demo script and answers

## 0. Before you go in (10 minutes)

1. `backend/.env` has `DEMO_PARTNER_ENABLED=1`, `DATA_ENCRYPTION_KEY=...` and your Groq key.
2. Start backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`).
3. **Test the free map search once with internet on** (`python osm_check.py`). If it is slow or down in the room, the app still works: it says search is unavailable and offers the DEMO hospital.
4. Register a fresh demo user (e.g. demo@example.com) so the chat history is clean.
5. Run `python -m pytest` and `python eval_safety.py` once so you have the numbers on screen.

## 1. Live demo (about 5 minutes)

| You type | What the audience sees | Say this |
|---|---|---|
| `I have eye pain and want to see a doctor` | One red-flag question first | "Safety check runs first; it never jumps to hospitals if the pain is sudden or severe." |
| `no` | Asks PIN or area | "It asks for the location only when needed." |
| `400093` (or `Andheri East, Mumbai`) | Up to 10 places, each with Call, Directions, Find phone, Select and book | "Maharashtra only, free OpenStreetMap data, nearest first. Where a phone is missing it says so and links the Google Maps listing." |
| `110001` | Refuses: Maharashtra only | "Scope is enforced by PIN prefix and by the geocoder's state." |
| Tap **Select and book** on any hospital | Details + directions + "Do you want me to prepare an appointment request?" | "It never says booked." |
| `yes` then answer the 5 questions | One question at a time, Step n of 5 | "Bad input is re-asked, nothing is saved yet." |
| `yes` on the summary | Reference number, status REQUESTED, what to say on the phone | "Hospitals have no public booking API, so this is honest: a request plus a call script." |
| Repeat choosing **DEMO Partner Hospital** | Status CONFIRMED (demo hospital) | "A sandbox partner that shows the full confirmed flow. It is labelled everywhere." |
| `my appointments`, then `cancel appointment HA-XXXXXX`, `yes` | List, then cancel after a yes | "Every write asks for confirmation. Only the owner can see or cancel." |
| `I have chest pain` (mid-form is fine) | Instant fixed emergency reply, 112 | "No AI is involved in emergencies, and it works even if the AI is down." |
| Side panel: **Erase all my data** | Confirmation, then everything removed | "Privacy by design." |

Show the **How I handled this** line under a reply when asked "where is the agent?".

## 2. Numbers you can quote (and how to say them)

* `python eval_safety.py`: 52 of 52 real emergencies detected, 0 of 30 harmless messages flagged **on the fixed list in `tests/safety_cases.py`**. Say "on my test list", not "100% accurate".
* The original detector missed 23 of 43 emergencies on an earlier list; the review found more gaps (self-harm phrased as "i dont wanna live", "swallowed 15 sleeping pills", snake bite, vomiting blood, newborn fever) and they are now covered by tests.
* 355 automated tests pass (LLM and map servers stubbed).

## 3. Likely questions

**Is it really agentic? It looks like rules.**
It is a controlled agent by design: goal-directed, tool-using, stateful across turns, multi-step, with confirmation before any action. An LLM decides nothing safety-critical or any write, on purpose: in healthcare an unpredictable agent loop is a risk, not a feature. LLM agents write the information and self-care answers.

**Why can't it book directly?**
Indian hospitals expose no public booking API (partnerships such as Practo or ABDM are needed). So it prepares a request, gives a call script and directions, and tracks status. The labelled demo hospital shows what a connected partner would return.

**Why Maharashtra only?**
So every result can be checked against a known area. The limit is enforced two ways: PIN prefix (400 to 445 except Goa's 403) and the geocoder's state and bounding box.

**What does "best hospital" mean?**
Nearest first, places that list a phone slightly preferred, specialty matches before general hospitals. There is no reliable public quality data, so it does not claim "best".

**Where does the hospital data come from, and is it reliable?**
OpenStreetMap through Nominatim and Overpass (free, no card). Community-edited, so phone and address are often missing; the app says "not listed". You can add hand-verified clinics in `backend/app/data/local_facilities.csv`.

**How is it secured?** See the README list. Be ready to say what is NOT done: no email verification, per-process rate limits, only appointment details encrypted, no clinician review, no penetration test.

**What are the failure modes?**
Detector is pattern matching (checks one message, can miss unusual phrasing or false-alarm on odd ones). Map servers can be down (it says so). LLM can be wrong (it is told to use retrieved sources and to refer to a doctor; sources are shown).

**What would you do next?**
Clinician review of the first-aid text; native-speaker review of Hindi and Marathi; real partner APIs; email verification; whole-database encryption; Postgres; multi-turn emergency context ("yes" after "are you having chest pain?").

## 4. Add real, verified hospitals (recommended before the viva)

For the 8 to 10 hospitals near your college or home, open the hospital's own website, copy its phone number and booking page, and add a row to `backend/app/data/local_facilities.csv`. The app shows exactly what you write, first, with your `verified_on` date. Do not copy numbers from memory. The file already contains 52 Maharashtra hospitals from a union's panel list, labelled "not checked with the hospital"; promote the ones you check by filling `verified_on` and clearing `source_note`.
