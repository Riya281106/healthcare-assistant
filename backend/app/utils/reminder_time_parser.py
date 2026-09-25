import re
from datetime import datetime, timedelta


TIME_PATTERN = re.compile(
    r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?',
    re.IGNORECASE
)


def compute_due_at(reminder_time):
    """
    Parses a loosely-formatted time string into the next upcoming
    datetime it refers to (today if that time hasn't passed yet,
    otherwise tomorrow). Returns None if it can't be parsed -
    callers should treat that as "no schedulable due time",
    not as an error.
    """

    if not reminder_time:
        return None

    match = TIME_PATTERN.search(reminder_time.strip())

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3)

    if meridiem:
        meridiem = meridiem.upper()

        if meridiem == "PM" and hour != 12:
            hour += 12

        if meridiem == "AM" and hour == 12:
            hour = 0

    if hour > 23 or minute > 59:
        return None

    now = datetime.now()

    candidate = now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate.strftime("%Y-%m-%d %H:%M:%S")


def reschedule_next_due(current_due_at_str):
    """
    Given a due_at that just fired for a 'daily' reminder,
    returns the same clock time on the next day.
    """

    current_due_at = datetime.strptime(
        current_due_at_str,
        "%Y-%m-%d %H:%M:%S"
    )

    next_due_at = current_due_at + timedelta(days=1)

    return next_due_at.strftime("%Y-%m-%d %H:%M:%S")