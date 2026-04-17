"""Rich terminal display helpers."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def _rate_style(rate: float | None) -> str:
    if rate is None:
        return "dim"
    if rate >= 8.0:
        return "bold bright_green"
    if rate >= 7.5:
        return "bright_green"
    if rate >= 7.0:
        return "green"
    if rate >= 6.5:
        return "yellow"
    if rate >= 6.0:
        return "orange3"
    return "white"


def _fmt(rate: float | None) -> str:
    return f"{rate:.2f}%" if rate is not None else "—"


def show_bank_table(bank: str, full_name: str, rates: list[dict], last_updated: str = "") -> None:
    title = f"[bold cyan]{bank}[/] — {full_name}"
    if last_updated:
        title += f"  [dim](updated {last_updated})[/]"

    table = Table(
        title=title,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold blue",
        min_width=60,
    )
    table.add_column("Tenure", style="bold", min_width=28)
    table.add_column("Regular (%)", justify="center", min_width=14)
    table.add_column("Senior Citizen (%)", justify="center", min_width=18)

    for r in rates:
        reg = r.get("regular_rate")
        sen = r.get("senior_rate")
        table.add_row(
            r["tenure_label"],
            Text(_fmt(reg), style=_rate_style(reg)),
            Text(_fmt(sen), style=_rate_style(sen)),
        )

    console.print(table)


def show_all_summary(all_rates: list[dict]) -> None:
    """Show one row per bank with their peak regular and senior rates."""
    # Group by bank
    from collections import defaultdict
    by_bank: dict[str, list] = defaultdict(list)
    for r in all_rates:
        by_bank[r["bank"]].append(r)

    table = Table(
        title="[bold cyan]All Banks — FD Rate Summary[/]",
        box=box.ROUNDED,
        header_style="bold blue",
        min_width=70,
    )
    table.add_column("Bank", style="bold", min_width=20)
    table.add_column("Full Name", min_width=22)
    table.add_column("Peak Regular (%)", justify="center", min_width=16)
    table.add_column("Peak Senior (%)", justify="center", min_width=15)
    table.add_column("Records", justify="center")

    for bank, rows in sorted(by_bank.items()):
        full_name = rows[0].get("full_name", bank)
        peak_reg = max((r["regular_rate"] for r in rows if r.get("regular_rate")), default=None)
        peak_sen = max((r["senior_rate"] for r in rows if r.get("senior_rate")), default=None)
        table.add_row(
            bank,
            full_name,
            Text(_fmt(peak_reg), style=_rate_style(peak_reg)),
            Text(_fmt(peak_sen), style=_rate_style(peak_sen)),
            str(len(rows)),
        )

    console.print(table)


def show_comparison(tenure_label: str, results: list[dict], citizen_type: str = "both") -> None:
    """Side-by-side comparison of all banks for a given tenure."""
    table = Table(
        title=f"[bold cyan]FD Rate Comparison — {tenure_label}[/]",
        box=box.ROUNDED,
        header_style="bold blue",
        min_width=72,
    )
    table.add_column("Rank", justify="center", min_width=6)
    table.add_column("Bank", style="bold", min_width=12)
    table.add_column("Full Name", min_width=22)
    table.add_column("Tenure Bucket", min_width=18)

    if citizen_type in ("regular", "both"):
        table.add_column("Regular (%)", justify="center", min_width=12)
    if citizen_type in ("senior", "both"):
        table.add_column("Senior (%)", justify="center", min_width=11)

    sort_key = "senior_rate" if citizen_type == "senior" else "regular_rate"
    sorted_results = sorted(results, key=lambda x: x.get(sort_key) or 0, reverse=True)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, r in enumerate(sorted_results, 1):
        reg = r.get("regular_rate")
        sen = r.get("senior_rate")
        row_vals = [
            medals.get(i, str(i)),
            r["bank"],
            r.get("full_name", ""),
            r.get("tenure_label", ""),
        ]
        if citizen_type in ("regular", "both"):
            row_vals.append(Text(_fmt(reg), style=_rate_style(reg)))
        if citizen_type in ("senior", "both"):
            row_vals.append(Text(_fmt(sen), style=_rate_style(sen)))
        table.add_row(*row_vals)

    console.print(table)


def show_best_rates(results: list[dict], tenure_approx: str, citizen_type: str, top_n: int = 5) -> None:
    label = "Senior Citizens" if citizen_type == "senior" else "Regular Citizens"
    table = Table(
        title=f"[bold cyan]🏆 Best FD Rates — ~{tenure_approx} ({label})[/]",
        box=box.ROUNDED,
        header_style="bold blue",
        min_width=68,
    )
    table.add_column("Rank", justify="center", min_width=6)
    table.add_column("Bank", style="bold", min_width=12)
    table.add_column("Full Name", min_width=22)
    table.add_column("Tenure Bucket", min_width=20)
    table.add_column("Rate (%)", justify="center", min_width=10)

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, r in enumerate(results[:top_n], 1):
        rate = r.get("rate")
        table.add_row(
            medals.get(i, str(i)),
            r["bank"],
            r.get("full_name", ""),
            r.get("tenure_label", ""),
            Text(_fmt(rate), style=_rate_style(rate)),
        )

    console.print(table)


def print_banner() -> None:
    console.print(
        Panel(
            "[bold cyan]🏦 Indian Bank FD Rates Fetcher[/]\n"
            "[dim]Scrapes live rates from official bank websites[/]",
            expand=False,
        )
    )
