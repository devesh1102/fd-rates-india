"""Axis Bank FD rate scraper.

Strategy:
  1. Use requests to fetch the Axis page and find the current PDF link.
  2. If not in plain HTML, fall back to Playwright.
  3. Download the PDF and parse page-0 raw text with regex.

PDF text format (page 0):
  "7 – 14 days   3.00   3.50   3.50   4.00"
  Columns: Tenure | General<3Cr | General3-5Cr | Senior<3Cr | Senior3-5Cr
  We use col[0]=Tenure, col[1]=Regular, col[3]=Senior.
"""
import io
import re

import pdfplumber
import requests
from bs4 import BeautifulSoup

from ._base import HEADERS, tenure_to_days

BANK = "AXIS"
FULL_NAME = "Axis Bank"
URL = "https://www.axisbank.com/deposits/fixed-deposits/fd-interest-rates"
_BASE = "https://www.axis.bank.in"

# Regex: tenure text (may include digits, spaces, dashes) then 4 float values
_ROW_RE = re.compile(
    r"^(.+?)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$"
)


def _find_pdf_url() -> str | None:
    """Find the current domestic FD PDF URL from the Axis page."""
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "domestic-fixed-deposits" in href and ".pdf" in href and "plus" not in href:
                return (_BASE + href) if href.startswith("/") else href
    except Exception:
        pass

    # Fallback: Playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch(headless=True)
            pg = br.new_page()
            pg.goto(URL, timeout=30000, wait_until="networkidle")
            pg.wait_for_timeout(5000)
            html = pg.content()
            br.close()
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "domestic-fixed-deposits" in href and ".pdf" in href and "plus" not in href:
                return (_BASE + href) if href.startswith("/") else href
    except Exception:
        pass
    return None


def _parse_pdf(pdf_bytes: bytes) -> list[dict]:
    rates = []
    seen: set[str] = set()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # Page 0: Less-than-3Cr domestic deposits
        text = pdf.pages[0].extract_text() or ""
        for line in text.splitlines():
            line = line.strip()
            m = _ROW_RE.match(line)
            if not m:
                continue
            tenure_text = m.group(1).strip()
            # Skip header/footer lines
            if any(kw in tenure_text.lower() for kw in
                   ("maturity", "period", "tenure", "interest", "rate", "general", "senior", "crore")):
                continue
            # Must look like a real tenure (contains day/month/year or digits)
            if not re.search(r"\d", tenure_text):
                continue
            if tenure_text in seen:
                continue
            seen.add(tenure_text)
            try:
                regular = float(m.group(2))
                senior = float(m.group(4))
            except ValueError:
                continue
            if regular < 1.0 or senior < 1.0:
                continue
            mn, mx = tenure_to_days(tenure_text)
            rates.append({
                "tenure_label": tenure_text,
                "tenure_days_min": mn,
                "tenure_days_max": mx,
                "regular_rate": regular,
                "senior_rate": senior,
            })
    return rates


def scrape() -> list[dict]:
    pdf_url = _find_pdf_url()
    if not pdf_url:
        raise RuntimeError("Could not find Axis Bank domestic FD PDF URL.")
    resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return _parse_pdf(resp.content)
