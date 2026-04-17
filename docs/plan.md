# Indian Bank FD Rates Fetcher — Project Plan

## Problem
Fetch Fixed Deposit (FD) interest rates from all major Indian banks for:
- Multiple tenures (7 days → 10 years)
- Both regular citizens and senior citizens
- Keep data fresh and queryable

## Approach
**Scraper + Agent architecture:**
- Scrape aggregator sites (BankBazaar / Paisabazaar) for structured rate tables
- Normalize and store in SQLite
- Expose a tool-calling agent as the query/reasoning layer

---

## Architecture

```
User Query
    ↓
Agent (LLM) ←→ Tools
                ├── scrape_bank_rates(bank)
                ├── compare_rates(tenure, citizen_type)
                ├── get_best_rate(tenure, citizen_type)
                └── refresh_cache()
    ↓
SQLite Cache (rates DB)
    ↑
Scraper (requests + BeautifulSoup / Playwright)
    ↑
BankBazaar / Paisabazaar / Bank websites
```

---

## Banks to Cover
1. SBI (State Bank of India)
2. IDFC First Bank
3. Canara Bank
4. ICICI Bank
5. HDFC Bank
6. Bandhan Bank
7. Kotak Mahindra Bank
8. Axis Bank
9. IndusInd Bank

---

## Data Model
```json
{
  "bank": "SBI",
  "tenure_label": "1 year",
  "tenure_days": 365,
  "regular_rate": 6.80,
  "senior_rate": 7.30,
  "source_url": "https://...",
  "last_updated": "2026-04-17"
}
```

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Scraping | Python, requests, BeautifulSoup, Playwright (fallback) |
| Storage | SQLite |
| Agent | OpenAI / Gemini function-calling |
| CLI | Python argparse or Typer |
| (Optional) API | FastAPI |

---

## Phases

### Phase 1 — Scraper
- [ ] Project scaffold (folder structure, venv, requirements.txt)
- [ ] Scraper for BankBazaar aggregator page (SBI first as pilot)
- [ ] Tenure normalizer (map "12 months", "1Y", "365 days" → canonical)
- [ ] Extend scraper to all target banks
- [ ] SQLite schema + insert/upsert logic
- [ ] Scheduler / refresh script (daily/weekly)

### Phase 2 — Agent Layer
- [ ] Define tool schemas (scrape, compare, best_rate, refresh)
- [ ] Implement tool functions backed by SQLite
- [ ] Wire up LLM (OpenAI/Gemini) with tool-calling
- [ ] Natural language query interface (CLI)
- [ ] Rate change diff & alert summary

### Phase 3 — Polish (Optional)
- [ ] FastAPI REST endpoints
- [ ] Simple web UI or rich CLI table output
- [ ] Export to CSV / JSON

---

## Notes
- No free public bank FD API exists; scraping is the primary source
- Aggregator sites (BankBazaar, Paisabazaar) are preferred over scraping 20+ individual bank sites
- Respect robots.txt and ToS; cache aggressively to minimize requests
- Tenure normalization is critical — banks label tenures inconsistently
