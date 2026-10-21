"""The one place the app asks what time it is, so tests can freeze it.

Always call these through the module (``clock.now()``), never ``from .clock import now``.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from ..config import settings


def now() -> datetime:
    return datetime.now(timezone.utc)


def tz() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def today() -> date:
    return now().astimezone(tz()).date()


def start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=tz())


def end_of_day(day: date) -> datetime:
    """Exclusive upper bound: midnight at the start of the next day, in APP_TIMEZONE."""
    return start_of_day(day + timedelta(days=1))


def local_date(moment: datetime) -> date:
    return moment.astimezone(tz()).date()
