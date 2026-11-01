# Agentic Healthcare Assistant (Maharashtra)

A chat assistant that gives general health information, spots emergencies, helps you find a
nearby hospital or clinic **in Maharashtra**, and prepares an appointment **request**.
Built with FastAPI + SQLite + ChromaDB (backend) and React + Vite (frontend).

> **It is an information tool, not a doctor.** It cannot diagnose, prescribe or examine you.
> For an emergency call **112** (ambulance **108** in most states). For emotional distress call
> Tele-MANAS **14416** or **1800-891-4416**.

## What it does

| Area | What happens |
|---|---|
| Safety first | Every message goes through a rule-based emergency detector before anything else. Emergencies get a fixed, specific reply (no AI involved) in English, Hindi, Marathi and Hinglish. |
| Triage | Messages are sorted into emergency / urgent / self-care / information, and the reply says which. |
| Hospital finder | Asks a red-flag question, then your PIN or area (Maharashtra only), then lists **up to 10** places ranked nearest-first, each with phone, address, directions and a "find phone" link when no number is listed. Free OpenStreetMap data; nothing is invented. |
| Appointment request | You pick a number, say yes, answer 5 short questions (name, phone, age, date/time, reason), review a summary, and confirm. It is saved as a **request** with a reference number. |
| Honest about booking | Hospitals have no public booking API, so a real hospital's request says "REQUESTED: not confirmed" and tells you to call. Only the labelled **DEMO partner hospital** confirms instantly. |
| Memory and records | Remembers facts you state, builds a symptom timeline, reminders, health summary. |
| Privacy controls | View or delete saved location data; **erase all my data** (optionally the account too). |

## Why it counts as "agentic"

It is a **controlled agent**: it has a goal (get the person to the right care), keeps state across turns, chooses between tools, plans a multi-step task, and asks for confirmation before it acts.

* **Tools:** emergency detector, specialty detector, geocoder + facility search, booking-link finder, appointment tools, reminders, retrieval over the knowledge base.
* **State:** a per-user step machine (screening, location, results, offer, form, summary) stored in the database.
* **Safety rule:** an LLM never decides an emergency and never writes data. Writes happen only after the person says YES on the summary.
* **Transparency:** each reply can show "How I handled this" (the steps taken).

## Run it

```powershell
cd backend
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env   then edit .env
uvicorn app.main:app --reload

# second terminal
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Tests: `cd backend; pip install pytest; python -m pytest`.
Safety numbers: `python eval_safety.py`.

## Security (what is actually implemented)

* Login with bcrypt-hashed passwords and signed tokens (python-jose 3.5.0, patched).
* Login rate limit (8 tries / 5 min per account and address), sign-up limit, identical error for unknown email vs wrong password.
* Every health, appointment and chat route requires login; the user comes from the token, never from the request.
* Appointment name, phone and reason are **encrypted in the database** (Fernet / AES + HMAC).
* Security headers, `Cache-Control: no-store` on API responses, CORS limited to listed origins, no cookies.
* Message text is never written to logs; every request has an id.
* Server-side request guard (SSRF) when looking for a hospital's booking page.
* Emergency messages have their own higher rate limit; the safety check cannot be the thing that fails.
* Delete-my-data endpoint and button.

## Known limits (please read)

* The emergency detector is pattern matching. It is measured on a fixed list (`tests/safety_cases.py`), not on every possible phrasing. It checks one message at a time.
* First-aid and crisis wording has **not** been reviewed by a doctor. Hindi and Marathi texts have not been reviewed by native speakers. The appointment form is in English only.
* OpenStreetMap data for India is community-edited: many places have no phone or address. "Best" here means nearest with contact details preferred, not a clinical quality ranking.
* The free map servers can be slow or down; the app says so instead of guessing.
* A request to a real hospital is not a confirmed appointment.
* SQLite and the rate limiters are per process: fine for one server, not for a large deployment.
* Data is not yet encrypted as a whole (only appointment details are).
