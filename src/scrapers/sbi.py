"""SBI FD rate scraper.
Source: https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits
Table: Retail Domestic Term Deposits (Below Rs. 3 crore)
Columns: Tenors | Existing Public | Revised Public (latest) | Existing Senior | Revised Senior (latest)
"""

import requests
from bs4 import BeautifulSoup

from ._base import HEADERS, parse_rate, tenure_to_days

BANK = "SBI"
FULL_NAME = "State Bank of India"
URL = "https://sbi.bank.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits"


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rates = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue

        header_cells = rows[0].find_all(["th", "td"])
        header_text = " ".join(c.get_text(" ", strip=True).lower() for c in header_cells)

        # Identify the retail FD rate table by header keywords
        if "tenor" not in header_text or "senior" not in header_text:
            continue

        # Locate column indices: we want the last "public/general" column
        # and last "senior" column (i.e. the revised/latest rates)
        regular_col = None
        senior_col = None
        for i, cell in enumerate(header_cells):
            txt = cell.get_text(" ", strip=True).lower()
            if "senior" in txt:
                senior_col = i          # keep updating → last senior col = revised
            elif "public" in txt or "general" in txt:
                regular_col = i         # keep updating → last public col = revised

        if regular_col is None or senior_col is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(regular_col, senior_col):
                continue

            tenure_text = cells[0].get_text(" ", strip=True)
            if not tenure_text or tenure_text.lower().startswith("tenor"):
                continue

            regular_rate = parse_rate(cells[regular_col].get_text(strip=True))
            senior_rate = parse_rate(cells[senior_col].get_text(strip=True))

            if regular_rate is None or senior_rate is None:
                continue

            min_d, max_d = tenure_to_days(tenure_text)
            rates.append(
                {
                    "tenure_label": tenure_text,
                    "tenure_days_min": min_d,
                    "tenure_days_max": max_d,
                    "regular_rate": regular_rate,
                    "senior_rate": senior_rate,
                }
            )

        if rates:
            break  # found the primary retail table

    return rates
