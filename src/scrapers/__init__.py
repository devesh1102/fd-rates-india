"""Scraper registry — import and run all bank scrapers."""

from . import axis, bandhan, canara, hdfc, icici, idfc, indusind, kotak, sbi

SCRAPERS = {
    sbi.BANK:      (sbi.FULL_NAME,      sbi.URL,      sbi.scrape),
    hdfc.BANK:     (hdfc.FULL_NAME,     hdfc.URL,     hdfc.scrape),
    icici.BANK:    (icici.FULL_NAME,    icici.URL,    icici.scrape),
    axis.BANK:     (axis.FULL_NAME,     axis.URL,     axis.scrape),
    kotak.BANK:    (kotak.FULL_NAME,    kotak.URL,    kotak.scrape),
    canara.BANK:   (canara.FULL_NAME,   canara.URL,   canara.scrape),
    idfc.BANK:     (idfc.FULL_NAME,     idfc.URL,     idfc.scrape),
    bandhan.BANK:  (bandhan.FULL_NAME,  bandhan.URL,  bandhan.scrape),
    indusind.BANK: (indusind.FULL_NAME, indusind.URL, indusind.scrape),
}
