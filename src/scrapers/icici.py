"""ICICI Bank FD rate scraper.

Reads from ICICI's internal JSON endpoint (no Playwright needed).
JSON structure: interestData[0] = "Popular FD Rates" tab (<3Cr, with premature withdrawal)
  c1 = General rate, c2 = Senior Citizen rate
URL: https://www.icicibank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates
"""
import requests
from ._base import HEADERS, tenure_to_days

BANK = "ICICI"
FULL_NAME = "ICICI Bank"
URL = "https://www.icicibank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates"
_JSON_URL = "https://www.icicibank.com/content/dam/icicibank-revamp/deposits/fixed-deposits/json/fd-interest-rate.json"


def scrape() -> list[dict]:
    resp = requests.get(_JSON_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    # interestData[0] = Popular/main tab: c1 = General <3Cr, c2 = Senior <3Cr
    rows = data.get("interestData", [[]])[0]

    rates = []
    for row in rows:
        tenure_text = row.get("tenure", "").strip()
        regular = row.get("c1")
        senior = row.get("c2")
        if not tenure_text or regular is None or senior is None:
            continue
        # Skip if values look like penalty/multiplier (< 2 is not a valid rate)
        if float(regular) < 2.0 or float(senior) < 2.0:
            continue
        mn, mx = tenure_to_days(tenure_text)
        rates.append({
            "tenure_label": tenure_text,
            "tenure_days_min": mn,
            "tenure_days_max": mx,
            "regular_rate": float(regular),
            "senior_rate": float(senior),
        })
    return rates
