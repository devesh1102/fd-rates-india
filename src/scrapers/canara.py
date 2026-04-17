"""Canara Bank FD rate scraper.
Source: https://www.canarabank.bank.in/pages/deposit-interest-rates
Table: Term Deposits < Rs.3 Crore (Callable) — Domestic
Columns: Tenure | Rate GP | Yield GP | Rate SC | Yield SC | (Non-callable cols...)
We want col[0]=Tenure, col[1]=Rate General Public, col[3]=Rate Senior Citizen
"""

import requests
from bs4 import BeautifulSoup
from ._base import HEADERS, parse_rate, tenure_to_days

BANK = "CANARA"
FULL_NAME = "Canara Bank"
URL = "https://www.canarabank.bank.in/pages/deposit-interest-rates"


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rates = []
    for table in soup.find_all("table"):
        table_text = table.get_text()
        # Target the retail callable (<3Cr) domestic term deposit table
        if "General Public" not in table_text and "general public" not in table_text.lower():
            continue
        if "Senior Citizen" not in table_text:
            continue
        # Skip bulk-deposit tables
        if "10 Crore" in table_text or "25 Crore" in table_text:
            continue

        rows = table.find_all("tr")
        if len(rows) < 4:
            continue

        # Find the sub-header row that has "Rate of Interest" cells to confirm col layout
        # Layout (after flattening colspan): Tenure | RateGP | YieldGP | RateSC | YieldSC | ...
        # We use fixed positions: col 0 = tenure, col 1 = regular rate, col 3 = senior rate
        REGULAR_COL, SENIOR_COL = 1, 3

        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue

            tenure_text = cells[0].get_text(" ", strip=True).strip("*").strip()
            if not tenure_text or any(
                kw in tenure_text.lower()
                for kw in ["tenor", "term deposit", "general", "senior", "rate", "annualised", "na"]
            ):
                continue

            r = parse_rate(cells[REGULAR_COL].get_text(strip=True))
            s = parse_rate(cells[SENIOR_COL].get_text(strip=True))
            if r is None or s is None:
                continue

            mn, mx = tenure_to_days(tenure_text)
            rates.append({
                "tenure_label": tenure_text,
                "tenure_days_min": mn,
                "tenure_days_max": mx,
                "regular_rate": r,
                "senior_rate": s,
            })

        if rates:
            break

    return rates
