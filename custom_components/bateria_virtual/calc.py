"""Pure calculation logic for the Bateria Virtual integration.

No Home Assistant imports here — everything is unit-testable in isolation.
"""
from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class BillBreakdown:
    """Estimated bill split into its components (all in €)."""

    energy: float
    power: float
    electricity_tax: float
    vat: float
    total: float


def surplus_value(delta_kwh: float, surplus_price: float) -> float:
    """Value (€) added to the virtual battery for a given export delta.

    A negative delta (meter reset on a total_increasing sensor) yields 0.
    """
    if delta_kwh <= 0:
        return 0.0
    return delta_kwh * surplus_price


def estimate_bill(
    import_kwh: float,
    avg_price: float,
    contracted_power_p1_kw: float,
    power_term_p1_eur_kw_day: float,
    contracted_power_p2_kw: float,
    power_term_p2_eur_kw_day: float,
    days: int,
    electricity_tax_pct: float,
    vat_pct: float,
) -> BillBreakdown:
    """Estimate a full bill: energy + power + electricity tax + VAT/IGIC.

    The power term sums the two Spanish contracted-power periods (P1 punta and
    P2 valle), each with its own contracted kW and its own €/kW·day price.
    """
    energy = import_kwh * avg_price
    power = (
        contracted_power_p1_kw * power_term_p1_eur_kw_day
        + contracted_power_p2_kw * power_term_p2_eur_kw_day
    ) * days
    base = energy + power
    electricity_tax = base * electricity_tax_pct / 100.0
    taxed_base = base + electricity_tax
    vat = taxed_base * vat_pct / 100.0
    total = taxed_base + vat
    return BillBreakdown(
        energy=energy,
        power=power,
        electricity_tax=electricity_tax,
        vat=vat,
        total=total,
    )


def apply_discount(balance: float, bill: float) -> tuple[float, float]:
    """Apply virtual-battery balance to a bill.

    Returns (new_balance, discount). Niba allows the bill to reach 0.
    """
    discount = min(balance, bill)
    return balance - discount, discount


def is_billing_close_day(today: dt.date, billing_day: int) -> bool:
    """True if `today` is the billing close day, clamping to month length."""
    last_day = calendar.monthrange(today.year, today.month)[1]
    effective_day = min(billing_day, last_day)
    return today.day == effective_day


def next_balance_after_expiry(
    buckets: list[tuple[int, int, float]],
    now: dt.date,
    expiry_months: int,
) -> tuple[list[tuple[int, int, float]], float]:
    """Drop balance buckets older than `expiry_months`.

    `buckets` is a list of (year, month, amount). Returns (kept_buckets, expired_total).
    expiry_months == 0 disables expiry.
    """
    if expiry_months <= 0:
        return buckets, 0.0
    cutoff_index = now.year * 12 + (now.month - 1) - expiry_months
    kept: list[tuple[int, int, float]] = []
    expired = 0.0
    for year, month, amount in buckets:
        bucket_index = year * 12 + (month - 1)
        if bucket_index < cutoff_index:
            expired += amount
        else:
            kept.append((year, month, amount))
    return kept, expired
