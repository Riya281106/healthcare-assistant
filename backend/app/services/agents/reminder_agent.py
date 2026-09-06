import re

from app.core.database import (
    save_reminder,
    get_user_reminders,
    deactivate_reminder,
    find_duplicate_reminder,
    find_matching_reminder
)


# ==================================================
# EXTRACT REMINDER DETAILS
# ==================================================

def extract_reminder_details(message: str):

    message_lower = message.lower()


    # ------------------------------------------
    # FREQUENCY
    # ------------------------------------------

    frequency = "once"

    if "every day" in message_lower or "daily" in message_lower:

        frequency = "daily"

    elif "every week" in message_lower or "weekly" in message_lower:

        frequency = "weekly"


    # ------------------------------------------
    # TIME EXTRACTION
    # ------------------------------------------

    time_match = re.search(
        r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))',
        message_lower
    )

    reminder_time = None

    if time_match:

        reminder_time = time_match.group(1).upper()


    # ------------------------------------------
    # REMINDER TEXT
    # ------------------------------------------

    reminder_text = message


    # Remove reminder phrases

    patterns = [

        r"remind me to",

        r"reminder to"

    ]

    for pattern in patterns:

        reminder_text = re.sub(
            pattern,
            "",
            reminder_text,
            flags=re.IGNORECASE
        )


    # Remove frequency phrases

    reminder_text = re.sub(
        r'\bevery day\b',
        '',
        reminder_text,
        flags=re.IGNORECASE
    )

    reminder_text = re.sub(
        r'\bdaily\b',
        '',
        reminder_text,
        flags=re.IGNORECASE
    )

    reminder_text = re.sub(
        r'\bevery week\b',
        '',
        reminder_text,
        flags=re.IGNORECASE
    )

    reminder_text = re.sub(
        r'\bweekly\b',
        '',
        reminder_text,
        flags=re.IGNORECASE
    )


    # Remove time phrase

    reminder_text = re.sub(
        r'\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b',
        '',
        reminder_text,
        flags=re.IGNORECASE
    )


    # Clean spaces and punctuation

    reminder_text = re.sub(
        r'\s+',
        ' ',
        reminder_text
    )

    reminder_text = reminder_text.strip(
        " .,!? "
    )


    return {

        "reminder_text": reminder_text,

        "reminder_time": reminder_time,

        "frequency": frequency

    }


# ==================================================
# EXTRACT CANCELLATION TEXT
# ==================================================

def extract_cancel_reminder_text(message: str):

    text = message.lower()


    patterns = [

        r"cancel my reminder to",

        r"cancel reminder to",

        r"delete my reminder to",

        r"remove my reminder to",

        r"cancel my reminder",

        r"cancel reminder"

    ]


    for pattern in patterns:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )


    text = text.strip(
        " .,!? "
    )


    return text


# ==================================================
# REMINDER AGENT
# ==================================================

def run_reminder_agent(

    user_id: str,

    message: str,

    history: list = None,

    memories: list = None

):

    history = history or []

    memories = memories or []

    message_lower = message.lower()


    # ==================================================
    # CANCEL REMINDER
    # ==================================================

    if (

        "cancel reminder" in message_lower

        or "cancel my reminder" in message_lower

        or "delete reminder" in message_lower

        or "remove reminder" in message_lower

    ):

        reminder_text = extract_cancel_reminder_text(
            message
        )


        reminder = find_matching_reminder(

            user_id=user_id,

            reminder_text=reminder_text

        )


        if not reminder:

            return {

                "message": (
                    "I could not find an active reminder "
                    "matching that description."
                ),

                "urgency_tier": "self_care",

                "agent": "REMINDER_AGENT",

                "rag_used": False

            }


        deactivate_reminder(
            reminder["id"]
        )


        time_text = (

            reminder["reminder_time"]

            if reminder["reminder_time"]

            else "Not specified"

        )


        return {

            "message": (
                "Your reminder has been cancelled successfully.\n\n"
                f"Reminder: {reminder['reminder_text']}\n"
                f"Time: {time_text}\n"
                f"Frequency: {reminder['frequency']}"
            ),

            "urgency_tier": "self_care",

            "agent": "REMINDER_AGENT",

            "rag_used": False

        }


    # ==================================================
    # SHOW REMINDERS
    # ==================================================

    if (

        "show reminders" in message_lower

        or "my reminders" in message_lower

        or "list reminders" in message_lower

        or "show my reminders" in message_lower

    ):

        reminders = get_user_reminders(
            user_id
        )


        if not reminders:

            return {

                "message": (
                    "You currently have no active reminders."
                ),

                "urgency_tier": "self_care",

                "agent": "REMINDER_AGENT",

                "rag_used": False

            }


        response = "Here are your active reminders:\n\n"


        for reminder in reminders:


            time_text = (

                reminder["reminder_time"]

                if reminder["reminder_time"]

                else "Not specified"

            )


            response += (

                f"• {reminder['reminder_text']}\n"

                f"  Time: {time_text}\n"

                f"  Frequency: {reminder['frequency']}\n\n"

            )


        return {

            "message": response,

            "urgency_tier": "self_care",

            "agent": "REMINDER_AGENT",

            "rag_used": False

        }


    # ==================================================
    # CREATE REMINDER
    # ==================================================

    details = extract_reminder_details(
        message
    )


    # ==================================================
    # CHECK DUPLICATE
    # ==================================================

    duplicate = find_duplicate_reminder(

        user_id=user_id,

        reminder_text=details["reminder_text"],

        reminder_time=details["reminder_time"],

        frequency=details["frequency"]

    )


    if duplicate:


        time_text = (

            duplicate["reminder_time"]

            if duplicate["reminder_time"]

            else "Not specified"

        )


        return {

            "message": (

                "You already have an active reminder "
                "with the same details.\n\n"

                f"Reminder: {duplicate['reminder_text']}\n"

                f"Time: {time_text}\n"

                f"Frequency: {duplicate['frequency']}"

            ),

            "urgency_tier": "self_care",

            "agent": "REMINDER_AGENT",

            "rag_used": False

        }


    # ==================================================
    # SAVE NEW REMINDER
    # ==================================================

    reminder = save_reminder(

        user_id=user_id,

        reminder_text=details["reminder_text"],

        reminder_time=details["reminder_time"],

        frequency=details["frequency"]

    )


    time_text = (

        reminder["reminder_time"]

        if reminder["reminder_time"]

        else "Not specified"

    )


    response = (

        "Your reminder has been saved successfully.\n\n"

        f"Reminder: {reminder['reminder_text']}\n"

        f"Time: {time_text}\n"

        f"Frequency: {reminder['frequency']}"

    )


    return {

        "message": response,

        "urgency_tier": "self_care",

        "agent": "REMINDER_AGENT",

        "rag_used": False

    }