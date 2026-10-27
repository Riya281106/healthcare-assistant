import sqlite3
import os
import json
# ==================================================
# DATABASE PATH
# ==================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

DATABASE_NAME = os.path.join(
    BASE_DIR,
    "healthcare.db"
)


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    connection.row_factory = sqlite3.Row

    return connection


# ==================================================
# INITIALIZE DATABASE
# ==================================================

def init_db():

    connection = get_connection()

    cursor = connection.cursor()


    # ----------------------------------------------
    # USERS
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ----------------------------------------------
    # USERS - PROFILE COLUMNS (added for Profile Management module)
    # ----------------------------------------------
    profile_columns = {
        "age": "INTEGER",
        "gender": "TEXT",
        "date_of_birth": "TEXT",
        "phone": "TEXT",
        "blood_group": "TEXT",
        "height_cm": "REAL",
        "weight_kg": "REAL",
        "allergies": "TEXT",
        "chronic_conditions": "TEXT",
        "emergency_contact_name": "TEXT",
        "emergency_contact_phone": "TEXT",
    }
    for column_name, column_type in profile_columns.items():
        try:
            cursor.execute(
                f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
            )
        except sqlite3.OperationalError:
            # Column already exists - safe to ignore
            pass


    # ----------------------------------------------
    # CHAT MESSAGES
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT NOT NULL,

            role TEXT NOT NULL,

            message TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


    # ----------------------------------------------
    # HEALTH RECORDS
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS health_records (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT NOT NULL,

            record_type TEXT NOT NULL,

            record_content TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ----------------------------------------------
    # HEALTH RECORDS - SYMPTOM TRACKER COLUMNS
    # (added for Symptom Tracker / Health Journal module)
    # ----------------------------------------------
    health_record_columns = {
        "symptom_name": "TEXT",
        "severity": "TEXT",
        "duration_text": "TEXT",
    }
    for column_name, column_type in health_record_columns.items():
        try:
            cursor.execute(
                f"ALTER TABLE health_records ADD COLUMN {column_name} {column_type}"
            )
        except sqlite3.OperationalError:
            # Column already exists - safe to ignore
            pass


    # ----------------------------------------------
    # REMINDERS
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT NOT NULL,

            reminder_text TEXT NOT NULL,

            reminder_time TEXT,

            frequency TEXT DEFAULT 'once',

            status TEXT DEFAULT 'active',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


    # ----------------------------------------------
    # REMINDERS - NOTIFICATION COLUMNS (added for due-time notifications)
    # ----------------------------------------------

    reminder_notification_columns = {
        "due_at": "TIMESTAMP",
        "last_notified_at": "TIMESTAMP",
    }

    for column_name, column_type in reminder_notification_columns.items():
        try:
            cursor.execute(
                f"ALTER TABLE reminders ADD COLUMN {column_name} {column_type}"
            )
        except sqlite3.OperationalError:
            pass


    # ----------------------------------------------
    # HOSPITALS
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hospitals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            city TEXT NOT NULL,

            area TEXT,

            address TEXT,

            phone TEXT,

            emergency_available TEXT DEFAULT 'no'
        )
        """
    )


    # ----------------------------------------------
    # LONG TERM USER MEMORY
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_memories (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT NOT NULL,

            memory_type TEXT NOT NULL,

            memory_content TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


    # ----------------------------------------------
    # CONVERSATION SUMMARIES (Auto Summary feature)
    # ----------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_summaries (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id TEXT NOT NULL UNIQUE,

            overall_summary TEXT,

            main_concerns TEXT,

            symptoms TEXT,

            medicines TEXT,

            health_observations TEXT,

            urgency_level TEXT,

            recommended_actions TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


    connection.commit()

    connection.close()


# ==================================================
# HOSPITALS -- SEED DATA
# ==================================================
# Local fallback dataset used only when GOOGLE_PLACES_API_KEY is not
# configured (see app/services/integrations/google_places.py). Real,
# independently verified hospitals/clinics with published phone
# numbers, so the Hospital Agent has something usable out of the box
# instead of an empty table. This is NOT a substitute for live data --
# phone numbers and hours can change -- but it beats returning nothing.

HOSPITAL_SEED_DATA = [
    # ---------------- Mumbai: Andheri (East & West) ----------------
    {
        "name": "Holy Spirit Hospital",
        "city": "Mumbai",
        "area": "Andheri East",
        "address": "Mahakali Caves Road, Sher-e-Punjab Colony, Andheri East, Mumbai 400093",
        "phone": "022-4247 8888 (OPD appointments: 7045517269)",
        "emergency_available": "yes",
    },
    {
        "name": "Kokilaben Dhirubhai Ambani Hospital",
        "city": "Mumbai",
        "area": "Andheri West",
        "address": "Rao Saheb Achutrao Patwardhan Marg, Four Bungalows, Andheri West, Mumbai 400053",
        "phone": "022-3069 6969 (appointments); Emergency: 022-3091 9191; Toll-free: 1800-3000-3333",
        "emergency_available": "yes",
    },
    {
        "name": "Seven Hills Hospital",
        "city": "Mumbai",
        "area": "Andheri East",
        "address": "Marol Maroshi Road, Andheri East, Mumbai 400059",
        "phone": "022-6767 6766",
        "emergency_available": "yes",
    },
    {
        "name": "CritiCare Hospital",
        "city": "Mumbai",
        "area": "Andheri East",
        "address": "Teli Gali, Andheri East, Mumbai 400069",
        "phone": "022-6231 6666",
        "emergency_available": "yes",
    },
    {
        "name": "BSES MG Hospital",
        "city": "Mumbai",
        "area": "Andheri West",
        "address": "S.V. Road, opposite Andheri railway station, Andheri West, Mumbai 400058",
        "phone": "022-6970 707",
        "emergency_available": "no",
    },
    # ---------------- Mumbai: other areas ----------------
    {
        "name": "Lilavati Hospital & Research Centre",
        "city": "Mumbai",
        "area": "Bandra",
        "address": "A-791, Bandra Reclamation, Bandra West, Mumbai 400050",
        "phone": "022-2675 1000",
        "emergency_available": "yes",
    },
    {
        "name": "Holy Family Hospital",
        "city": "Mumbai",
        "area": "Bandra",
        "address": "St. Andrew's Road, Bandra West, Mumbai 400050",
        "phone": "022-3061 0555",
        "emergency_available": "yes",
    },
    {
        "name": "P.D. Hinduja National Hospital & Medical Research Centre",
        "city": "Mumbai",
        "area": "Mahim",
        "address": "Veer Savarkar Marg, Mahim, Mumbai 400016",
        "phone": "022-2445 1515",
        "emergency_available": "yes",
    },
    {
        "name": "Dr. Balabhai Nanavati Hospital",
        "city": "Mumbai",
        "area": "Vile Parle",
        "address": "S.V. Road, Vile Parle West, Mumbai 400056",
        "phone": "022-2626 7500",
        "emergency_available": "yes",
    },
    {
        "name": "Breach Candy Hospital Trust",
        "city": "Mumbai",
        "area": "Breach Candy",
        "address": "60-A, Bhulabhai Desai Road, Mumbai 400026",
        "phone": "022-2367 7788",
        "emergency_available": "yes",
    },
    {
        "name": "Jaslok Hospital & Research Centre",
        "city": "Mumbai",
        "area": "Pedder Road",
        "address": "15, Dr. G. Deshmukh Marg, Pedder Road, Mumbai 400026",
        "phone": "022-6657 3333",
        "emergency_available": "yes",
    },
    {
        "name": "Bombay Hospital & Medical Research Centre",
        "city": "Mumbai",
        "area": "Marine Lines",
        "address": "12, New Marine Lines, Mumbai 400020",
        "phone": "022-2206 7676",
        "emergency_available": "yes",
    },
    {
        "name": "Kapadia Multispeciality Hospital",
        "city": "Mumbai",
        "area": "Goregaon",
        "address": "M.G. Road, Goregaon West, Mumbai 400062",
        "phone": "022-2879 7400",
        "emergency_available": "no",
    },
    # ---------------- Pune ----------------
    {
        "name": "Ruby Hall Clinic",
        "city": "Pune",
        "area": "Sassoon Road",
        "address": "40, Sassoon Road, Pune 411001",
        "phone": "020-6699 9999",
        "emergency_available": "yes",
    },
]


def seed_hospitals():
    """
    Inserts the local hospital fallback dataset if the `hospitals`
    table is currently empty. Safe to call on every startup -- it
    is a no-op once the table has any rows, so it never duplicates
    data or clobbers anything an admin has added manually.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM hospitals")
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        connection.close()
        return existing_count

    for hospital in HOSPITAL_SEED_DATA:
        cursor.execute(
            """
            INSERT INTO hospitals (
                name, city, area, address, phone, emergency_available
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                hospital["name"],
                hospital["city"],
                hospital["area"],
                hospital["address"],
                hospital["phone"],
                hospital["emergency_available"],
            ),
        )

    connection.commit()
    connection.close()

    return len(HOSPITAL_SEED_DATA)


# ==================================================
# USERS
# ==================================================

def create_user(
    name: str,
    email: str,
    password_hash: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO users (
            name,
            email,
            password
        )

        VALUES (?, ?, ?)
        """,
        (
            name,
            email.lower(),
            password_hash
        )
    )


    user_id = cursor.lastrowid

    connection.commit()


    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )


    user = cursor.fetchone()

    connection.close()

    return dict(user)


def get_user_by_email(email: str):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            password AS password_hash,
            created_at
        FROM users
        WHERE email = ?
        """,
        (email.lower(),)
    )


    user = cursor.fetchone()

    connection.close()


    if user:

        return dict(user)

    return None


def get_user_by_id(user_id: int):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            name,
            email,
            password AS password_hash,
            created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )


    user = cursor.fetchone()

    connection.close()


    if user:

        return dict(user)

    return None


# ==================================================
# CHAT MESSAGES
# ==================================================

def save_message(
    user_id: str,
    role: str,
    message: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO chat_messages (
            user_id,
            role,
            message
        )

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            role,
            message
        )
    )


    connection.commit()

    connection.close()


def get_recent_messages(
    user_id: str,
    limit: int = 5
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            role,
            message,
            created_at

        FROM chat_messages

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )


    rows = cursor.fetchall()

    connection.close()

    messages = []

    for row in reversed(rows):

        messages.append({
            "role": row["role"],
            "message": row["message"],
            "created_at": row["created_at"]
        })

    return messages


def delete_user_messages(user_id: str):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM chat_messages WHERE user_id = ?",
        (user_id,)
    )

    deleted_count = cursor.rowcount

    connection.commit()

    connection.close()

    return deleted_count


# ==================================================
# HEALTH RECORDS
# ==================================================

def save_health_record(
    user_id: str,
    record_type: str,
    record_content: str,
    symptom_name: str = None,
    severity: str = None,
    duration_text: str = None
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO health_records (
            user_id,
            record_type,
            record_content,
            symptom_name,
            severity,
            duration_text
        )

        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            record_type,
            record_content,
            symptom_name,
            severity,
            duration_text
        )
    )


    connection.commit()

    connection.close()
def update_health_record_fields(record_id, symptom_name, severity, duration_text):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE health_records
        SET symptom_name = ?,
            severity = ?,
            duration_text = ?
        WHERE id = ?
        """,
        (symptom_name, severity, duration_text, record_id)
    )

    conn.commit()
    conn.close()


def get_null_symptom_records():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, record_content
        FROM health_records
        WHERE symptom_name IS NULL
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows

def get_health_records(
    user_id: str,
    limit: int = 50
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            record_type,
            record_content,
            created_at

        FROM health_records

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# ==================================================
# SYMPTOM HISTORY (Symptom Tracker / Health Journal)
# ==================================================

def get_symptom_history(
    user_id: str,
    limit: int = 100
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            record_type,
            symptom_name,
            severity,
            duration_text,
            record_content,
            created_at

        FROM health_records

        WHERE
            user_id = ?
            AND record_type IN ('SYMPTOM', 'URGENT', 'SELF_CARE')

        ORDER BY created_at ASC, id ASC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# ==================================================
# LONG TERM MEMORY
# ==================================================

def save_user_memory(
    user_id: str,
    memory_type: str,
    memory_content: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO user_memories (
            user_id,
            memory_type,
            memory_content
        )

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            memory_type,
            memory_content
        )
    )


    memory_id = cursor.lastrowid

    connection.commit()


    cursor.execute(
        """
        SELECT
            id,
            user_id,
            memory_type,
            memory_content,
            created_at

        FROM user_memories

        WHERE id = ?
        """,
        (memory_id,)
    )


    memory = cursor.fetchone()

    connection.close()


    return dict(memory)


def get_user_memories(
    user_id: str,
    limit: int = 50
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            memory_type,
            memory_content,
            created_at

        FROM user_memories

        WHERE user_id = ?

        ORDER BY id DESC

        LIMIT ?
        """,
        (
            user_id,
            limit
        )
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


def find_duplicate_memory(
    user_id: str,
    memory_type: str,
    memory_content: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT
            id,
            memory_type,
            memory_content,
            created_at

        FROM user_memories

        WHERE
            user_id = ?
            AND memory_type = ?
            AND LOWER(memory_content) = LOWER(?)

        LIMIT 1
        """,
        (
            user_id,
            memory_type,
            memory_content
        )
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)

    return None


# ==================================================
# REMINDERS
# ==================================================

def save_reminder(
    user_id: str,
    reminder_text: str,
    reminder_time: str = None,
    frequency: str = "once"
):

    from app.utils.reminder_time_parser import compute_due_at

    due_at = compute_due_at(reminder_time)

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO reminders (
            user_id,
            reminder_text,
            reminder_time,
            frequency,
            status,
            due_at
        )

        VALUES (?, ?, ?, ?, 'active', ?)
        """,
        (
            user_id,
            reminder_text,
            reminder_time,
            frequency,
            due_at
        )
    )


    reminder_id = cursor.lastrowid

    connection.commit()


    cursor.execute(
        """
        SELECT *
        FROM reminders
        WHERE id = ?
        """,
        (reminder_id,)
    )


    reminder = cursor.fetchone()

    connection.close()


    return dict(reminder)


def get_user_reminders(user_id: str):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *

        FROM reminders

        WHERE
            user_id = ?
            AND status = 'active'

        ORDER BY id DESC
        """,
        (user_id,)
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


def get_due_reminders(user_id: str):

    from app.utils.reminder_time_parser import reschedule_next_due
    from datetime import datetime

    connection = get_connection()

    cursor = connection.cursor()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        SELECT *

        FROM reminders

        WHERE
            user_id = ?
            AND status = 'active'
            AND due_at IS NOT NULL
            AND due_at <= ?

        ORDER BY due_at ASC
        """,
        (user_id, now_str)
    )

    rows = cursor.fetchall()

    due_reminders = [dict(row) for row in rows]

    for reminder in due_reminders:

        if reminder["frequency"] == "daily":

            next_due_at = reschedule_next_due(reminder["due_at"])

            cursor.execute(
                "UPDATE reminders SET due_at = ?, last_notified_at = ? WHERE id = ?",
                (next_due_at, now_str, reminder["id"])
            )

        else:

            cursor.execute(
                "UPDATE reminders SET status = 'completed', last_notified_at = ? WHERE id = ?",
                (now_str, reminder["id"])
            )

    connection.commit()

    connection.close()

    return due_reminders


def find_duplicate_reminder(
    user_id: str,
    reminder_text: str,
    reminder_time: str,
    frequency: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *

        FROM reminders

        WHERE
            user_id = ?
            AND LOWER(reminder_text) = LOWER(?)
            AND COALESCE(reminder_time, '') =
                COALESCE(?, '')
            AND frequency = ?
            AND status = 'active'

        LIMIT 1
        """,
        (
            user_id,
            reminder_text,
            reminder_time,
            frequency
        )
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)

    return None


def find_matching_reminder(
    user_id: str,
    reminder_text: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *

        FROM reminders

        WHERE
            user_id = ?
            AND status = 'active'
            AND LOWER(reminder_text)
                LIKE '%' || LOWER(?) || '%'

        ORDER BY id DESC

        LIMIT 1
        """,
        (
            user_id,
            reminder_text
        )
    )


    row = cursor.fetchone()

    connection.close()


    if row:

        return dict(row)

    return None


def deactivate_reminder(
    reminder_id: int
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        UPDATE reminders

        SET status = 'cancelled'

        WHERE id = ?
        """,
        (reminder_id,)
    )


    connection.commit()

    connection.close()


# ==================================================
# HOSPITAL SEARCH
# ==================================================

def search_hospitals(
    city: str = None,
    area: str = None,
    emergency_only: bool = False,
    limit: int = 10
):

    connection = get_connection()

    cursor = connection.cursor()


    query = """
        SELECT
            id,
            name,
            city,
            area,
            address,
            phone,
            emergency_available

        FROM hospitals

        WHERE 1 = 1
    """

    parameters = []


    if city:

        query += """
            AND LOWER(city) = LOWER(?)
        """

        parameters.append(city)


    if area:

        # LIKE match, not exact: a seeded row's area is often more
        # specific than what the user said (e.g. "Andheri East" vs.
        # the user just saying "Andheri"), so an exact match would
        # miss real rows. This matches either direction.
        query += """
            AND LOWER(area) LIKE '%' || LOWER(?) || '%'
        """

        parameters.append(area)


    if emergency_only:

        query += """
            AND LOWER(emergency_available) = 'yes'
        """


    query += """
        ORDER BY name
        LIMIT ?
    """

    parameters.append(limit)


    cursor.execute(
        query,
        parameters
    )


    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]


# ==================================================
# USER PROFILE
# ==================================================

def get_user_profile(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, email, age, gender, date_of_birth, phone,
               blood_group, height_cm, weight_kg, allergies,
               chronic_conditions, emergency_contact_name,
               emergency_contact_phone, created_at
        FROM users
        WHERE id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)


def update_user_profile(user_id, profile_data):

    allowed_fields = {
        "name", "age", "gender", "date_of_birth", "phone",
        "blood_group", "height_cm", "weight_kg", "allergies",
        "chronic_conditions", "emergency_contact_name",
        "emergency_contact_phone",
    }

    fields_to_update = {
        key: value
        for key, value in profile_data.items()
        if key in allowed_fields
    }

    if not fields_to_update:
        return False

    set_clause = ", ".join(
        f"{field} = ?" for field in fields_to_update
    )
    values = list(fields_to_update.values())
    values.append(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        f"UPDATE users SET {set_clause} WHERE id = ?",
        values
    )

    connection.commit()
    connection.close()

    return True
# ==================================================
# CONVERSATION SUMMARY (Auto Summary feature)
# ==================================================

def get_conversation_summary(user_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            overall_summary,
            main_concerns,
            symptoms,
            medicines,
            health_observations,
            urgency_level,
            recommended_actions,
            created_at,
            updated_at
        FROM conversation_summaries
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    summary = dict(row)

    # Decode the JSON-encoded list fields back into Python lists
    for field in ("main_concerns", "symptoms", "medicines", "health_observations", "recommended_actions"):
        raw_value = summary.get(field)
        summary[field] = json.loads(raw_value) if raw_value else []

    return summary


def upsert_conversation_summary(
    user_id: str,
    overall_summary: str,
    main_concerns: list,
    symptoms: list,
    medicines: list,
    health_observations: list,
    urgency_level: str,
    recommended_actions: list
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO conversation_summaries (
            user_id,
            overall_summary,
            main_concerns,
            symptoms,
            medicines,
            health_observations,
            urgency_level,
            recommended_actions,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

        ON CONFLICT(user_id) DO UPDATE SET
            overall_summary = excluded.overall_summary,
            main_concerns = excluded.main_concerns,
            symptoms = excluded.symptoms,
            medicines = excluded.medicines,
            health_observations = excluded.health_observations,
            urgency_level = excluded.urgency_level,
            recommended_actions = excluded.recommended_actions,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            user_id,
            overall_summary,
            json.dumps(main_concerns),
            json.dumps(symptoms),
            json.dumps(medicines),
            json.dumps(health_observations),
            urgency_level,
            json.dumps(recommended_actions)
        )
    )

    connection.commit()
    connection.close()

    return get_conversation_summary(user_id)