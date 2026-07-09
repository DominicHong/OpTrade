from datetime import date, datetime, timezone


def parse_chinese_date(value: str) -> date | None:
    """Parse a date string, handling Chinese date formats like '2026-06-08'."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    # Try ISO formats
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def parse_chinese_datetime(value: str) -> datetime | None:
    """Parse a datetime string like '2026-06-08 15:26:47'."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    # Try date-only
    d = parse_chinese_date(value)
    if d is not None:
        return datetime(d.year, d.month, d.day)
    return None


def parse_float(value: str) -> float | None:
    """Parse a numeric string to float, returning None for empty/invalid."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip().replace(",", "")
    if not value:
        return None
    try:
        return float(value)
    except (ValueError, OverflowError):
        return None


def parse_bool_chinese(value: str) -> bool | None:
    """Parse a Chinese boolean string like 'true'/'false' or '是'/'否'."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in ("true", "yes", "y", "1", "是"):
        return True
    if value in ("false", "no", "n", "0", "否"):
        return False
    return None


def utc_now() -> datetime:
    """Return the current UTC datetime (use as a ``Field`` default_factory)."""
    return datetime.now(timezone.utc)
