"""Timezone helpers for Lingora.

Provide a robust way to get the Brasilia timezone (America/Sao_Paulo) when the
platform tzdata is missing. Falls back to a fixed -03:00 offset when ZoneInfo is
not available or the named zone is not found.
"""

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:
    ZoneInfo = None  # type: ignore


def _get_brasilia_tz():
    if ZoneInfo is not None:
        try:
            return ZoneInfo("America/Sao_Paulo")
        except Exception:
            import logging

            logging.getLogger(__name__).debug(
                "ZoneInfo lookup failed, using fixed -03:00 offset fallback"
            )
    # Fallback to fixed -03:00 offset (Brasil standard time without DST handling)
    return timezone(timedelta(hours=-3))


def now_brasilia() -> datetime:
    """Return an aware datetime in the Brasilia timezone (best-effort).

    If the system does not provide the IANA tz database, this returns a UTC-3
    fixed-offset timezone datetime to avoid raising ZoneInfoNotFoundError.
    """
    return datetime.now(_get_brasilia_tz())
