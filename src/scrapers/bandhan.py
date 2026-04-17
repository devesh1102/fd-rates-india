"""Bandhan Bank FD rate scraper.
URL: https://bandhan.bank.in/fixed-deposit

The rate chart is a standard 3-column HTML table:
  Tenure | Regular Rate (General Public) | Senior Citizen Rate
"""
import requests
from bs4 import BeautifulSoup
from ._base import HEADERS, parse_rate, tenure_to_days

BANK = "BANDHAN"
FULL_NAME = "Bandhan Bank"
URL = "https://bandhan.bank.in/fixed-deposit"


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
        # Need at least one rate and tenure-like content
        if "%" not in table.get_text():
            continue
        if "days" not in table_text and "year" not in table_text and "month" not in table_text:
            continue
        # Skip NRE/NRO/bulk tables
        if any(kw in table_text for kw in ("nre", "nro", "5 crore", "25 crore")):
            continue

        # Determine column indices from header
        header_rows = [r for r in rows if r.find(["th"])]
        regular_col, senior_col = 1, 2
        if header_rows:
            hdrs = header_rows[0].find_all(["th", "td"])
            for i, cell in enumerate(hdrs):
                t = cell.get_text(" ", strip=True).lower()
                if "senior" in t:
                    senior_col = i
                elif "general" in t or "public" in t or "regular" in t or (
                    "rate" in t and "senior" not in t
                ):
                    regular_col = i

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            tenure_text = cells[0].get_text(" ", strip=True)
            if not tenure_text or any(
                kw in tenure_text.lower() for kw in ("tenure", "tenor", "period", "maturity")
            ):
                continue
            r = parse_rate(cells[min(regular_col, len(cells) - 1)].get_text(strip=True))
            s_idx = min(senior_col, len(cells) - 1)
            s = parse_rate(cells[s_idx].get_text(strip=True))
            if r is None:
                continue
            if s is None:
                s = r
            mn, mx = tenure_to_days(tenure_text)
            rates.append(
                {
                    "tenure_label": tenure_text,
                    "tenure_days_min": mn,
                    "tenure_days_max": mx,
                    "regular_rate": r,
                    "senior_rate": s,
                }
            )
        if rates:
            break
    return rates
