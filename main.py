"""
FD Rates CLI — fetch and compare Fixed Deposit rates from major Indian banks.

Commands:
  fetch [BANK ...]   Scrape rates (all banks by default)
  show  [BANK]       Display rate table for one or all banks
  best  TENURE       Show bank with best rate for a tenure
  compare TENURE     Compare all banks for a tenure

Examples:
  python main.py fetch
  python main.py fetch SBI HDFC
  python main.py show SBI
  python main.py show
  python main.py best "1 year" --type senior
  python main.py compare "1 year"
"""

import argparse
import sys
from src.database import init_db, upsert_rates, get_rates, get_all_banks, get_best_rates, has_data
from src.scrapers import SCRAPERS
from src.display import (
    print_banner,
    show_bank_table,
    show_all_summary,
    show_comparison,
    show_best_rates,
)
from rich.console import Console

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_banks(keys: list[str]) -> list[str]:
    """Validate and return upper-cased bank keys, or all keys if empty."""
    all_keys = list(SCRAPERS.keys())
    if not keys:
        return all_keys
    resolved = []
    for k in keys:
        ku = k.upper()
        if ku not in SCRAPERS:
            console.print(f"[bold red]Unknown bank: {k}[/]  Valid: {', '.join(all_keys)}")
            sys.exit(1)
        resolved.append(ku)
    return resolved


def _tenure_to_days_approx(tenure: str) -> int:
    """Very rough conversion of user-supplied tenure to days for lookup."""
    import re
    s = tenure.lower().strip()
    m = re.search(r"(\d+)\s*(day|week|month|year)", s)
    if not m:
        return 365
    val, unit = int(m.group(1)), m.group(2)
    if "day" in unit:
        return val
    if "week" in unit:
        return val * 7
    if "month" in unit:
        return val * 30
    return val * 365


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_fetch(args):
    banks = _resolve_banks(args.bank)
    total_rows = 0
    skipped = []

    for key in banks:
        full_name, url, scrape_fn = SCRAPERS[key]
        console.print(f"  [cyan]Fetching[/] [bold]{full_name}[/] …", end=" ")
        try:
            rows = scrape_fn()
            if not rows:
                console.print("[yellow]0 rows[/] (empty result)")
                skipped.append(key)
                continue
            saved = upsert_rates(key, full_name, rows, url)
            console.print(f"[green]{saved} rows saved[/]")
            total_rows += saved
        except NotImplementedError as e:
            console.print(f"[yellow]SKIP[/] — {e}")
            skipped.append(key)
        except Exception as e:
            console.print(f"[red]FAILED[/] — {e}")
            skipped.append(key)

    console.print()
    console.print(f"[bold green]Done.[/] {total_rows} rows saved across "
                  f"{len(banks) - len(skipped)} banks.")
    if skipped:
        console.print(f"[dim]Skipped: {', '.join(skipped)}[/]")


def cmd_show(args):
    bank_records = get_all_banks()
    if not bank_records:
        console.print("[yellow]No data in database. Run: python main.py fetch[/]")
        return

    present_keys = {r["bank"] for r in bank_records}

    if args.bank:
        key = args.bank.upper()
        if key not in SCRAPERS:
            console.print(f"[red]Unknown bank: {args.bank}[/]")
            sys.exit(1)
        if key not in present_keys:
            console.print(f"[yellow]{key} not in database. Run: python main.py fetch {key}[/]")
            return
        rates = get_rates(key)
        last_upd = rates[0].get("last_updated", "") if rates else ""
        show_bank_table(key, SCRAPERS[key][0], rates, last_upd)
    else:
        all_rates = get_rates()
        show_all_summary(all_rates)


def cmd_best(args):
    if not has_data():
        console.print("[yellow]No data in database. Run: python main.py fetch[/]")
        return
    days = _tenure_to_days_approx(args.tenure)
    citizen_type = args.type.lower()
    if citizen_type not in ("regular", "senior", "both"):
        console.print("[red]--type must be one of: regular, senior, both[/]")
        sys.exit(1)

    types_to_show = ["regular", "senior"] if citizen_type == "both" else [citizen_type]
    for ct in types_to_show:
        results = get_best_rates(days, ct)
        if not results:
            console.print(f"[yellow]No rates found for ~{args.tenure} ({ct})[/]")
        else:
            show_best_rates(results, args.tenure, ct, top_n=args.top)


def cmd_compare(args):
    if not has_data():
        console.print("[yellow]No data in database. Run: python main.py fetch[/]")
        return
    days = _tenure_to_days_approx(args.tenure)
    citizen_type = args.type.lower()
    if citizen_type not in ("regular", "senior", "both"):
        console.print("[red]--type must be one of: regular, senior, both[/]")
        sys.exit(1)

    results = get_best_rates(days, "regular")
    if not results:
        console.print(f"[yellow]No rates found for ~{args.tenure}[/]")
        return
    show_comparison(args.tenure, results, citizen_type)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Indian Bank FD Rate Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Scrape rates from bank websites")
    p_fetch.add_argument(
        "bank", nargs="*", metavar="BANK",
        help="Banks to fetch (default: all). E.g. SBI HDFC CANARA"
    )

    # show
    p_show = sub.add_parser("show", help="Display rate table(s)")
    p_show.add_argument(
        "bank", nargs="?", metavar="BANK",
        help="Bank to show (default: all banks summary)"
    )

    # best
    p_best = sub.add_parser("best", help="Show bank with best rate for a tenure")
    p_best.add_argument("tenure", help='Tenure, e.g. "1 year", "6 months", "2 years"')
    p_best.add_argument(
        "--type", default="both", choices=["regular", "senior", "both"],
        help="Citizen type (default: both)"
    )
    p_best.add_argument(
        "--top", type=int, default=5, metavar="N",
        help="Show top N banks (default: 5)"
    )

    # compare
    p_compare = sub.add_parser("compare", help="Compare all banks for a tenure")
    p_compare.add_argument("tenure", help='Tenure, e.g. "1 year", "6 months"')
    p_compare.add_argument(
        "--type", default="both", choices=["regular", "senior", "both"],
        help="Citizen type (default: both)"
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    print_banner()

    if not args.command:
        parser.print_help()
        return

    init_db()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "best":
        cmd_best(args)
    elif args.command == "compare":
        cmd_compare(args)


if __name__ == "__main__":
    main()

