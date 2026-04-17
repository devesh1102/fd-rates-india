import re


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def parse_rate(text: str) -> float | None:
    """Extract float percentage from strings like '6.25%', '6.25', '7.05*'."""
    if not text:
        return None
    text = text.strip().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None


def tenure_to_days(text: str) -> tuple[int, int]:
    """
    Convert a tenure string to (min_days, max_days).
    Handles patterns from SBI, HDFC, IDFC and common bank formats.
    Returns (0, 9999) as fallback.
    """
    # Normalize dashes and stray chars
    s = text.lower().strip().replace("–", "-").replace("—", "-")

    def to_days(val: float, unit: str) -> int:
        if "day" in unit:
            return round(val)
        if "month" in unit:
            return round(val * 30)
        if "year" in unit:
            return round(val * 365)
        return round(val)

    # "X days/months/years to [less than] Y days/months/years"
    # "X days/months/years and up to Y days/months/years"
    # "X days/months/years - [less than] Y days/months/years"  (dash variant)
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(days?|months?|years?)"
        r"\s*(?:to\s*(?:less\s*than\s*)?|and\s*up\s*to\s*|-\s*(?:less\s*than\s*)?)"
        r"(\d+(?:\.\d+)?)\s*(days?|months?|years?)",
        s,
    )
    if m:
        min_d = to_days(float(m.group(1)), m.group(2))
        max_d = to_days(float(m.group(3)), m.group(4))
        if "less than" in s[m.start() : m.end() + 15]:
            max_d -= 1
        return min_d, max_d

    # "X year Y day - Z days/years"  e.g. "1 year 1 day- 370 days", "2 years 1 day - 5 years"
    m = re.search(
        r"(\d+)\s*years?\s+\d+\s*days?\s*-\s*(\d+)\s*(days?|years?)", s
    )
    if m:
        min_d = to_days(int(m.group(1)), "years") + 1
        max_d = to_days(int(m.group(2)), m.group(3))
        return min_d, max_d

    # "X - Y days/months/years"
    m = re.match(r"(\d+)\s*[-–]\s*(\d+)\s*(days?|months?|years?)", s)
    if m:
        unit = m.group(3)
        return to_days(int(m.group(1)), unit), to_days(int(m.group(2)), unit)

    # "X months 1 day [to|<=] Y months/years"  (e.g. "6 months 1 day <= 9 months")
    m = re.search(
        r"(\d+)\s*(months?|years?)\s*\d+\s*days?\s*(?:to\s*<?|<=)\s*(\d+)\s*(months?|years?)",
        s,
    )
    if m:
        min_d = to_days(int(m.group(1)), m.group(2)) + 1
        max_d = to_days(int(m.group(3)), m.group(4))
        return min_d, max_d

    # "X days <= Y months"
    m = re.match(r"(\d+)\s*(days?|months?)\s*<=\s*(\d+)\s*(months?|years?)", s)
    if m:
        return to_days(int(m.group(1)), m.group(2)), to_days(int(m.group(3)), m.group(4))

    # "X months/years to < Y months/years"
    m = re.search(r"(\d+)\s*(months?|years?)\s*to\s*<\s*(\d+)\s*(months?|years?)", s)
    if m:
        min_d = to_days(int(m.group(1)), m.group(2))
        max_d = to_days(int(m.group(3)), m.group(4)) - 1
        return min_d, max_d

    # "X months to Y months" (no qualifier)
    m = re.search(r"(\d+)\s*(months?|years?)\s*to\s*(\d+)\s*(months?|years?)", s)
    if m:
        return to_days(int(m.group(1)), m.group(2)), to_days(int(m.group(3)), m.group(4))

    # Single "X year/month/day"
    m = re.match(r"(\d+)\s*(years?|months?|days?)", s)
    if m:
        d = to_days(int(m.group(1)), m.group(2))
        return d, d

    return 0, 9999
