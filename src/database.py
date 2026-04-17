import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "fd_rates.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fd_rates (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                bank            TEXT    NOT NULL,
                full_name       TEXT,
                tenure_label    TEXT    NOT NULL,
                tenure_days_min INTEGER NOT NULL,
                tenure_days_max INTEGER NOT NULL,
                regular_rate    REAL,
                senior_rate     REAL,
                source_url      TEXT,
                last_updated    TEXT    DEFAULT CURRENT_DATE,
                UNIQUE(bank, tenure_label)
            )
        """)
        conn.commit()


def upsert_rates(bank: str, full_name: str, rates: list[dict], source_url: str) -> int:
    today = date.today().isoformat()
    records = [
        {
            "bank": bank,
            "full_name": full_name,
            "tenure_label": r["tenure_label"],
            "tenure_days_min": r["tenure_days_min"],
            "tenure_days_max": r["tenure_days_max"],
            "regular_rate": r["regular_rate"],
            "senior_rate": r["senior_rate"],
            "source_url": source_url,
            "last_updated": today,
        }
        for r in rates
    ]
    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO fd_rates
                (bank, full_name, tenure_label, tenure_days_min, tenure_days_max,
                 regular_rate, senior_rate, source_url, last_updated)
            VALUES
                (:bank, :full_name, :tenure_label, :tenure_days_min, :tenure_days_max,
                 :regular_rate, :senior_rate, :source_url, :last_updated)
            ON CONFLICT(bank, tenure_label) DO UPDATE SET
                tenure_days_min = excluded.tenure_days_min,
                tenure_days_max = excluded.tenure_days_max,
                regular_rate    = excluded.regular_rate,
                senior_rate     = excluded.senior_rate,
                last_updated    = excluded.last_updated
            """,
            records,
        )
        conn.commit()
    return len(records)


def get_rates(bank: str | None = None) -> list[dict]:
    with _conn() as conn:
        if bank:
            rows = conn.execute(
                "SELECT * FROM fd_rates WHERE UPPER(bank) = UPPER(?) ORDER BY tenure_days_min",
                (bank,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM fd_rates ORDER BY bank, tenure_days_min"
            ).fetchall()
    return [dict(r) for r in rows]


def get_all_banks() -> list[str]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT bank, full_name FROM fd_rates ORDER BY bank"
        ).fetchall()
    return [dict(r) for r in rows]


def get_best_rates(tenure_days: int, citizen_type: str = "regular") -> list[dict]:
    rate_col = "senior_rate" if citizen_type == "senior" else "regular_rate"
    with _conn() as conn:
        rows = conn.execute(
            f"""
            SELECT bank, full_name, tenure_label,
                   {rate_col} AS rate, regular_rate, senior_rate,
                   tenure_days_min, tenure_days_max
            FROM fd_rates
            WHERE tenure_days_min <= ? AND tenure_days_max >= ?
              AND {rate_col} IS NOT NULL
            ORDER BY {rate_col} DESC
            """,
            (tenure_days, tenure_days),
        ).fetchall()
    return [dict(r) for r in rows]


def has_data() -> bool:
    with _conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM fd_rates").fetchone()[0]
    return count > 0
