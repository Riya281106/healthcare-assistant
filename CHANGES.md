# Changes in this update

## How to apply
1. Unzip over your project folder (`C:\Users\RIYA\healthcare-assistant`) and choose "replace files".
2. Add to `backend\.env` (use the email you log in with):
   `ADMIN_EMAILS=your-login-email@example.com`
   (see `backend\.env.example`; nobody can re-index the knowledge base without this).
3. `cd backend` then `pip install -r requirements.txt`
   Then run `pip show groq` and replace the bare `groq` line in requirements.txt with `groq==<your version>`.
4. Restart backend and frontend. You do NOT need to log in again.

Run the tests any time:
```
cd backend
pip install pytest
python -m pytest
```

## 1. Security (auth + data isolation)
- `/api/chat`, `/api/health-records`, `/api/symptoms`, `/api/rag/stats` now require login.
- The user comes from the login token. `user_id` is no longer accepted from the browser
  (before: anyone could read/write another person's health data by changing a number).
- `/api/rag/reindex` is admin-only (`ADMIN_EMAILS`).
- The old unauthenticated `/api/chat/history` is removed (use `/api/conversations/history`).
- Messages over 2000 characters or empty are rejected; passwords over 128 characters are rejected.
- 30 chat messages/minute/user. Emergency-looking messages are never rate limited.
- Server errors no longer leak internal details to the browser.

## 2. Emergency detector (rewritten)
Files: `utils/emergency_detector.py`, `utils/red_flag_rules.py`, `utils/clinical_text.py`,
`services/agents/emergency_agent.py`, `services/agents/orchestrator.py`.
Measured on the same 43 emergency / 24 harmless test messages:
- Original: missed 23/43 real emergencies, 9/24 false alarms.
- New: 0 missed, 0 false alarms (on that list, which is not a guarantee for every phrasing).
Real bugs fixed: curly apostrophes ("can't"), "no fever but chest pain" being ignored,
"keystroke" matching "stroke", "suicidal"/"end my life" not detected, no Hindi/Hinglish.
- Emergency check now runs FIRST in the orchestrator and uses fixed text (no LLM).
- If the AI/database fails, an emergency message still gets the emergency reply.
- Replies are specific (heart, breathing, bleeding, stroke, seizure, choking, poisoning, allergy)
  and self-harm gets a supportive message with Tele-MANAS.

## 3. Speed and reliability
- `/api/chat` is a normal `def`, so one slow AI call no longer blocks other users
  (measured: 4 simultaneous 2s calls finish in 2.1s, not 8s).
- AI calls time out after 30s (one retry) instead of hanging.
- Database indexes on every per-user query, 10s lock timeout, WAL mode.
- Saving memories / health records can fail without losing the answer.

## 4. Logging and privacy
- Every request gets an id (`X-Request-ID` header + in every log line) with the user id and timing.
- Message text is never logged (only length, intent, tier, timing).
- `.gitignore` now excludes the SQLite `-wal`/`-shm` files so health data is not committed.

## Frontend
`api.js`, `App.jsx`, `HealthRecordsPage.jsx`, `SymptomTimelinePage.jsx`, `Dashboard.jsx`,
`KnowledgePage.jsx` send the token; an expired login returns you to the login screen;
"too long / too fast / unavailable" messages are shown instead of "backend not running".

## Known limits (please read)
- Not tested: the browser flow against your real database, real Groq and your real vector store.
  Tested: 116 backend tests (temporary database, AI stubbed), a real uvicorn run, frontend build.
- Frontend lint: 4 errors remain in ConversationHistoryPage, HealthSummaryPage, ProfilePage and
  RemindersPage. They exist in your original code and I did not touch those files.
- The detector is pattern matching. It checks only the current message (a bare "yes" after
  "are you having chest pain?" is not linked), and it cannot catch every phrasing.
  Add phrases in `red_flag_rules.py` and a test for each.
- The first-aid and crisis wording has NOT been reviewed by a clinician. Have a doctor review
  `emergency_agent.py` before real patients rely on it.
- Hindi/Hinglish coverage is a starting set, not complete.
- Numbers used: 112 (national emergency), 108 (ambulance, most states), 102 (pregnancy/newborn),
  Tele-MANAS 14416 / 1800-891-4416. Checked against public/government-reported sources on
  28 Oct 2026. India is merging older lines into 112 (Supreme Court order, May 2026), so recheck yearly.
- The rate limiter is per server process (fine for one `uvicorn`).
