"""Kotak Mahindra Bank FD rate scraper.

Uses Playwright (headless Chromium) to render the JS-heavy page.
Table 0 structure (21 rows):
  row 0: Title (colspan)
  row 1: Regular | Senior Citizen*
  row 2: Sub-headers with amount slabs
  rows 3+: Tenure | Regular<3Cr | Regular>3Cr | Senior<3Cr | Senior>3Cr
  We use col[0]=Tenure, col[1]=Regular<3Cr, col[3]=Senior<3Cr
URL: https://www.kotak.bank.in/en/personal-banking/deposits/fixed-deposit/fixed-deposit-interest-rate.html
"""
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from ._base import parse_rate, tenure_to_days

BANK = "KOTAK"
FULL_NAME = "Kotak Mahindra Bank"
URL = "https://www.kotak.bank.in/en/personal-banking/deposits/fixed-deposit/fixed-deposit-interest-rate.html"


def scrape() -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(6000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")

    rates = []
    for table in tables:
        txt = table.get_text().lower()
        if "senior" not in txt or "%" not in table.get_text():
            continue
        # Skip non-callable / penalty tables
        if any(kw in txt for kw in ("premature withdrawal not allowed", "penalty")):
            continue

        rows = table.find_all("tr")
        if len(rows) < 5:
            continue

        # Data starts after 3 header rows (title, regular/senior, amount slabs)
        for row in rows[3:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            tenure_text = cells[0].get_text(" ", strip=True)
            if not tenure_text or any(
                kw in tenure_text.lower() for kw in ("tenure", "maturity", "period", "rate")
            ):
                continue
            r = parse_rate(cells[1].get_text(strip=True))
            s = parse_rate(cells[3].get_text(strip=True))
            if r is None:
                continue
            if s is None:
                s = r
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
