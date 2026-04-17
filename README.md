# 🏦 FD Rates India

A live Fixed Deposit (FD) interest rate tracker for **9 major Indian banks**, with comparisons for both **Regular** and **Senior Citizen** customers across all tenures.

## 🌐 Live App

👉 **[https://fdrates-app.wittysky-9b56846b.eastus.azurecontainerapps.io](https://fdrates-app.wittysky-9b56846b.eastus.azurecontainerapps.io)**

> First load may take ~30 seconds (cold start). Fetch rates from the **📥 Fetch Rates** page to populate data.

---

## 🏦 Supported Banks

| Bank | Method |
|------|--------|
| State Bank of India (SBI) | HTML scraper |
| HDFC Bank | HTML scraper |
| ICICI Bank | JSON API |
| Canara Bank | HTML scraper |
| IndusInd Bank | HTML scraper |
| IDFC First Bank | HTML scraper |
| Bandhan Bank | HTML scraper |
| Kotak Mahindra Bank | Playwright (headless) |
| Axis Bank | PDF parser |

---

## 📸 Features

- **📥 Fetch Rates** — Scrape live rates from all 9 official bank websites
- **📊 Bank Explorer** — Browse rates per bank with source link, charts, and tenure breakdown
- **🏆 Best Rates** — Find the best rate for a specific tenure or across all tenures
- **📈 Compare Banks** — Side-by-side heatmap, line charts, and peak rate comparison

---

## 🚀 Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/Devesh1102/fd-rates-india.git
cd fd-rates-india
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Start the app
```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🐳 Run with Docker

```bash
docker build -t fdrates-app .
docker run -p 8501:8501 fdrates-app
```

---

## 🗂️ Project Structure

```
getfdRates/
├── app.py                  # Streamlit UI (4 pages)
├── main.py                 # CLI entry point
├── requirements.txt
├── Dockerfile
├── data/
│   └── fd_rates.db         # SQLite database (auto-created)
└── src/
    ├── database.py         # SQLite layer
    ├── display.py          # Rich terminal display
    └── scrapers/
        ├── _base.py        # Shared utilities
        ├── sbi.py
        ├── hdfc.py
        ├── icici.py
        ├── canara.py
        ├── indusind.py
        ├── idfc.py
        ├── bandhan.py
        ├── kotak.py
        └── axis.py
```

---

## 🛠️ CLI Usage

```bash
# Fetch rates for all banks
python main.py fetch

# Fetch a specific bank
python main.py fetch --bank sbi

# Show rates for a bank
python main.py show --bank hdfc

# Best rates for a tenure
python main.py best --tenure "1 year"

# Compare banks
python main.py compare
```

---

## ☁️ Azure Deployment

Deployed on **Azure Container Apps** (`rg-fdrates`, `eastus`).

To redeploy after changes:
```powershell
az containerapp up --name fdrates-app --resource-group rg-fdrates --source .
```

---

## 📦 Tech Stack

- **Python 3.11**
- **Streamlit** — Web UI
- **Plotly** — Charts
- **requests + BeautifulSoup4** — HTML scraping
- **Playwright** — JS-rendered pages (Kotak)
- **pdfplumber** — PDF parsing (Axis)
- **SQLite** — Local data storage
- **Rich** — Terminal output
