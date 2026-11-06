"""Helper utilities for timezones, IDs, and calculations."""
from datetime import datetime, time, timedelta
import random
import string
from zoneinfo import ZoneInfo
from backend.app.config import settings

IST_ZONE = ZoneInfo(settings.TIMEZONE)


def get_ist_now() -> datetime:
    """Return current datetime in Asia/Kolkata timezone."""
    return datetime.now(IST_ZONE)


def get_ist_day_bounds(target_date=None) -> tuple[datetime, datetime]:
    """Return start (00:00:00) and end (23:59:59.999999) of day for IST."""
    if target_date is None:
        target_date = get_ist_now().date()
    start = datetime.combine(target_date, time.min, tzinfo=IST_ZONE)
    end = datetime.combine(target_date, time.max, tzinfo=IST_ZONE)
    # Return naive UTC datetime equivalents for SQLite querying
    start_utc = start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    end_utc = end.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return start_utc, end_utc


def generate_transaction_id() -> str:
    """Generate a readable, unique transaction ID: TXN-YYYYMMDD-XXXX."""
    date_str = get_ist_now().strftime("%Y%m%d")
    random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TXN-{date_str}-{random_suffix}"
