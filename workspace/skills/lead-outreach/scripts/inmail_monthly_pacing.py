"""InMail pacing: spread remaining credits across remaining weekdays in the month.

Uses only the standard library. Intended for lead-outreach workflows: read credits from
Sales Navigator, then cap today's sends with ``plan.sends_budget_today``.

Example::

    from inmail_monthly_pacing import inmail_pacing_plan

    plan = inmail_pacing_plan(credits_remaining=42)
    print(plan.working_days_remaining, plan.sends_budget_today)
"""

from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator


def _last_day_of_month(d: date) -> date:
    _, last = calendar.monthrange(d.year, d.month)
    return date(d.year, d.month, last)


def _dates_inclusive(start: date, end: date) -> Iterator[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def is_working_day(d: date) -> bool:
    """Monday–Friday (Saturday=5, Sunday=6 are excluded)."""
    return d.weekday() < 5


def working_days_remaining_in_month(reference: date | None = None) -> int:
    """Count weekdays from ``reference`` through the last calendar day of that month (inclusive).

    If ``reference`` is a weekend, only dates from that day onward count; weekend days
    themselves are not included in the count.
    """
    ref = reference if reference is not None else date.today()
    end = _last_day_of_month(ref)
    return sum(1 for d in _dates_inclusive(ref, end) if is_working_day(d))


def working_days_in_month(reference: date | None = None) -> int:
    """Count weekdays in the full calendar month of ``reference``."""
    ref = reference if reference is not None else date.today()
    start = date(ref.year, ref.month, 1)
    end = _last_day_of_month(ref)
    return sum(1 for d in _dates_inclusive(start, end) if is_working_day(d))


@dataclass(frozen=True)
class InMailPacingPlan:
    reference_date: date
    credits_remaining: int
    working_days_remaining: int
    """Weekdays from ``reference_date`` through month end (inclusive)."""

    sends_budget_today: int
    """Integer division ``credits_remaining // working_days_remaining`` (0 if no days left)."""

    credits_if_even_split: float
    """``credits_remaining / working_days_remaining`` for display; 0 if no days left."""


def inmail_pacing_plan(
    credits_remaining: int,
    reference: date | None = None,
    *,
    min_one_when_credits: bool = False,
) -> InMailPacingPlan:
    """Compute how many InMails to target **today** using remaining month weekdays only.

    **Rolling plan:** Re-run with fresh ``credits_remaining`` each session so the daily
    budget adapts as the month progresses.

    :param credits_remaining: InMail credits left (non-negative).
    :param reference: "Today" for remaining-days calculation; defaults to ``date.today()``.
    :param min_one_when_credits: If True and credits > 0 but floor division yields 0,
        return ``sends_budget_today == 1`` (may exhaust credits before month-end).
    """
    ref = reference if reference is not None else date.today()
    n = working_days_remaining_in_month(ref)
    if credits_remaining < 0:
        raise ValueError("credits_remaining must be >= 0")
    if n <= 0:
        return InMailPacingPlan(
            reference_date=ref,
            credits_remaining=credits_remaining,
            working_days_remaining=0,
            sends_budget_today=0,
            credits_if_even_split=0.0,
        )
    split = credits_remaining / n
    budget = credits_remaining // n
    if min_one_when_credits and credits_remaining > 0 and budget == 0:
        budget = 1
    return InMailPacingPlan(
        reference_date=ref,
        credits_remaining=credits_remaining,
        working_days_remaining=n,
        sends_budget_today=budget,
        credits_if_even_split=split,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute InMail sends budget from credits and remaining weekdays this month."
    )
    parser.add_argument(
        "--credits",
        type=int,
        required=True,
        help="Remaining InMail credits (integer).",
    )
    parser.add_argument(
        "--date",
        dest="ref_date",
        metavar="YYYY-MM-DD",
        default=None,
        help="Reference date (default: today).",
    )
    parser.add_argument(
        "--min-one",
        action="store_true",
        help="If credits>0 but floor split is 0, use 1 send for today.",
    )
    args = parser.parse_args()
    ref = date.fromisoformat(args.ref_date) if args.ref_date else None
    plan = inmail_pacing_plan(args.credits, ref, min_one_when_credits=args.min_one)
    print(f"reference_date={plan.reference_date.isoformat()}")
    print(f"credits_remaining={plan.credits_remaining}")
    print(f"working_days_remaining_in_month={plan.working_days_remaining}")
    print(f"credits_per_remaining_working_day≈{plan.credits_if_even_split:.4f}")
    print(f"sends_budget_today={plan.sends_budget_today}")


if __name__ == "__main__":
    main()
