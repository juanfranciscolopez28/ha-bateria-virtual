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
    import_kwh_p1: float,
    import_kwh_p2: float,
    import_kwh_p3: float,
    energy_price_p1: float,
    energy_price_p2: float,
    energy_price_p3: float,
    contracted_power_p1_kw: float,
    power_term_p1_eur_kw_day: float,
    contracted_power_p2_kw: float,
    power_term_p2_eur_kw_day: float,
    days: int,
    electricity_tax_pct: float,
    vat_pct: float,
) -> BillBreakdown:
    """Estimate a full bill: energy + power + electricity tax + VAT/IGIC.

    The energy term sums the three Spanish energy periods (P1 punta, P2 llano,
    P3 valle), each with its own imported kWh and its own €/kWh price. The power
    term sums the two contracted-power periods (P1 punta, P2 valle), each with
    its own contracted kW and its own €/kW·day price.
    """
    energy = (
        import_kwh_p1 * energy_price_p1
        + import_kwh_p2 * energy_price_p2
        + import_kwh_p3 * energy_price_p3
    )
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


def price_with_taxes(
    base_price: float, electricity_tax_pct: float, vat_pct: float
) -> float:
    """Per-kWh price with electricity tax then VAT applied, like the template:

    precio × (1 + impuesto_eléctrico/100) × (1 + IVA/100)
    """
    taxed = base_price * (1 + electricity_tax_pct / 100.0)
    return taxed * (1 + vat_pct / 100.0)


def apply_discount(balance: float, bill: float) -> tuple[float, float]:
    """Apply virtual-battery balance to a bill.

    Returns (new_balance, discount). The bill is allowed to reach 0.
    """
    discount = min(balance, bill)
    return balance - discount, discount


def is_billing_close_day(today: dt.date, billing_day: int) -> bool:
    """True if `today` is the billing close day, clamping to month length."""
    last_day = calendar.monthrange(today.year, today.month)[1]
    effective_day = min(billing_day, last_day)
    return today.day == effective_day


def next_billing_close(d: dt.date, billing_day: int) -> dt.date:
    """Smallest date on or after `d` that is a billing close day.

    `billing_day` is clamped to the length of the target month (e.g. day 31 in
    a 30-day month becomes the 30th).
    """
    last = calendar.monthrange(d.year, d.month)[1]
    effective_day = min(billing_day, last)
    if d.day <= effective_day:
        return dt.date(d.year, d.month, effective_day)
    year = d.year + (1 if d.month == 12 else 0)
    month = 1 if d.month == 12 else d.month + 1
    last_next = calendar.monthrange(year, month)[1]
    return dt.date(year, month, min(billing_day, last_next))


def days_until_billing_close(today: dt.date, billing_day: int) -> int:
    """Whole days until the next billing close (0 if today is the close day)."""
    return (next_billing_close(today, billing_day) - today).days


def cycle_total_days(period_start: dt.date, billing_day: int) -> int:
    """Total days of the billing cycle that opened on `period_start`.

    The cycle runs from `period_start` to the next billing close strictly after
    it, matching the day count used by the running bill estimate.
    """
    next_close = next_billing_close(period_start + dt.timedelta(days=1), billing_day)
    return max(1, (next_close - period_start).days)


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
