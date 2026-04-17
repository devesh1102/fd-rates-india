"""HDFC Bank FD rate scraper.
Source: https://www.hdfc.bank.in/interest-rates
Table: Domestic / NRO / NRE Fixed Deposit Rate — < 3 Crore
Columns: Tenor Bucket | Interest Rate (per annum) | Senior Citizen Rates (per annum)
"""

import requests
from bs4 import BeautifulSoup

from ._base import HEADERS, parse_rate, tenure_to_days

BANK = "HDFC"
FULL_NAME = "HDFC Bank"
URL = "https://www.hdfc.bank.in/interest-rates"


def scrape() -> list[dict]:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rates = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 5:
            continue

        table_text = table.get_text()
        # We want the retail (< 3 Crore) table
        if "3 crore" not in table_text.lower() and "3 Crore" not in table_text:
            continue
        # Skip the bulk / non-withdrawable tables which appear after
        if "5 crore" in table_text.lower() and "24.75 crore" in table_text.lower():
            continue

        # Flatten all header rows to find rate column positions
        regular_col = None
        senior_col = None
        data_start_row = 0

        for row_idx, row in enumerate(rows):
            cells = row.find_all(["th", "td"])
            texts = [c.get_text(" ", strip=True).lower() for c in cells]

            if any("interest rate" in t for t in texts):
                for i, t in enumerate(texts):
                    if "senior" in t:
                        senior_col = i
                    elif "interest rate" in t or "rate" in t:
                        regular_col = i
                data_start_row = row_idx + 1
                break

        # Fallback: data rows have 3 cells (tenor, regular, senior)
        if regular_col is None:
            for row in rows[1:]:
                cells = row.find_all(["td"])
                if len(cells) == 3:
                    regular_col, senior_col = 1, 2
                    break

        if regular_col is None:
            continue

        for row in rows[data_start_row:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            tenure_text = cells[0].get_text(" ", strip=True)
            if not tenure_text or "tenor" in tenure_text.lower() or "period" in tenure_text.lower():
                continue

            r_idx = min(regular_col, len(cells) - 1)
            s_idx = min(senior_col, len(cells) - 1)

            regular_rate = parse_rate(cells[r_idx].get_text(strip=True))
            senior_rate = parse_rate(cells[s_idx].get_text(strip=True))

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
            break

    return rates
