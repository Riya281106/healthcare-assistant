import sqlite3
import os


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


    connection.commit()

    connection.close()


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


# ==================================================
# HEALTH RECORDS
# ==================================================

def save_health_record(
    user_id: str,
    record_type: str,
    record_content: str
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO health_records (
            user_id,
            record_type,
            record_content
        )

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            record_type,
            record_content
        )
    )


    connection.commit()

    connection.close()


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

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO reminders (
            user_id,
            reminder_text,
            reminder_time,
            frequency,
            status
        )

        VALUES (?, ?, ?, ?, 'active')
        """,
        (
            user_id,
            reminder_text,
            reminder_time,
            frequency
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

        query += """
            AND LOWER(area) = LOWER(?)
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