"""IDFC First Bank FD rate scraper.

The rate page has a 2-column table (Tenor | Rate).
Senior citizen rate = Regular rate + 0.50% (per IDFC First Bank policy).
Only the "Less than INR 3 Crores" section is used.
URL: https://www.idfcfirstbank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates
"""
import requests
from bs4 import BeautifulSoup
from ._base import HEADERS, parse_rate, tenure_to_days

BANK = "IDFC"
FULL_NAME = "IDFC First Bank"
URL = "https://www.idfcfirstbank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates"
SENIOR_BONUS = 0.50


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rates = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 4:
            continue
        table_text = table.get_text().lower()
        # Must contain rate/interest data (skip T&C tables)
        if "%" not in table.get_text():
            continue
        if "crore" in table_text and "3 crore" not in table_text:
            continue  # skip bulk tables

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            tenure_text = cells[0].get_text(" ", strip=True)
            if not tenure_text or any(
                kw in tenure_text.lower() for kw in ("tenure", "tenor", "period", "bucket")
            ):
                continue
            r = parse_rate(cells[1].get_text(strip=True))
            if r is None:
                continue
            mn, mx = tenure_to_days(tenure_text)
            rates.append(
                {
                    "tenure_label": tenure_text,
                    "tenure_days_min": mn,
                    "tenure_days_max": mx,
                    "regular_rate": r,
                    "senior_rate": round(r + SENIOR_BONUS, 2),
                }
            )
        if rates:
            break
    return rates
