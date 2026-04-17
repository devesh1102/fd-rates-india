"""IndusInd Bank FD rate scraper.

Table: Tenure | Rate | Annualized Yield | Senior Rate | Senior Yield  (5 cols)
We use col[0]=Tenure, col[1]=Regular Rate, col[3]=Senior Rate.
URL: https://www.indusind.bank.in/in/en/personal/fixed-deposit-interest-rate.html
"""
import requests
from bs4 import BeautifulSoup
from ._base import HEADERS, parse_rate, tenure_to_days

BANK = "INDUSIND"
FULL_NAME = "IndusInd Bank"
URL = "https://www.indusind.bank.in/in/en/personal/fixed-deposit-interest-rate.html"


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
        if "senior" not in table_text:
            continue
        if "days" not in table_text and "year" not in table_text:
            continue
        # Skip bulk tables only (not NRE/NRO mentions in title)
        if any(kw in table_text for kw in ("5 crore", "25 crore", "above 3 crore")):
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            tenure_text = cells[0].get_text(" ", strip=True)
            if not tenure_text or any(
                kw in tenure_text.lower() for kw in ("tenure", "period", "tenor")
            ):
                continue
            r = parse_rate(cells[1].get_text(strip=True))
            s = parse_rate(cells[3].get_text(strip=True))
            if r is None:
                continue
            if s is None:
                s = r  # some rows may be empty for senior
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
