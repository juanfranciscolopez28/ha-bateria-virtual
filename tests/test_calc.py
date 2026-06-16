"""Tests for the pure calculation core."""
import datetime as dt

from custom_components.bateria_virtual.calc import (
    apply_discount,
    estimate_bill,
    is_billing_close_day,
    next_balance_after_expiry,
    surplus_value,
)


def test_surplus_value_multiplies_delta_by_price():
    assert surplus_value(delta_kwh=10.0, surplus_price=0.06) == 0.6


def test_surplus_value_negative_delta_is_clamped_to_zero():
    # A total_increasing sensor reset must never subtract from the balance.
    assert surplus_value(delta_kwh=-5.0, surplus_price=0.06) == 0.0


def test_estimate_bill_full_breakdown():
    bill = estimate_bill(
        import_kwh=100.0,
        avg_price=0.20,
        contracted_power_p1_kw=4.6,
        power_term_p1_eur_kw_day=0.10,
        contracted_power_p2_kw=0.0,
        power_term_p2_eur_kw_day=0.0,
        days=30,
        electricity_tax_pct=5.11,
        vat_pct=21.0,
    )
    # energy: 100 * 0.20 = 20.0 ; power: 4.6 * 0.10 * 30 = 13.8
    # base = 33.8 ; +5.11% elec tax = 35.52718 ; +21% VAT = 42.9878878
    assert bill.energy == 20.0
    assert round(bill.power, 5) == 13.8
    assert round(bill.total, 2) == 42.99


def test_estimate_bill_sums_both_power_periods():
    bill = estimate_bill(
        import_kwh=0.0,
        avg_price=0.0,
        contracted_power_p1_kw=4.6,
        power_term_p1_eur_kw_day=0.10,
        contracted_power_p2_kw=4.6,
        power_term_p2_eur_kw_day=0.02,
        days=30,
        electricity_tax_pct=0.0,
        vat_pct=0.0,
    )
    # power: (4.6*0.10 + 4.6*0.02) * 30 = (0.46 + 0.092) * 30 = 16.56
    assert round(bill.power, 5) == 16.56


def test_apply_discount_partial():
    new_balance, discount = apply_discount(balance=10.0, bill=42.99)
    assert discount == 10.0
    assert new_balance == 0.0


def test_apply_discount_caps_at_bill():
    new_balance, discount = apply_discount(balance=100.0, bill=42.99)
    assert discount == 42.99
    assert round(new_balance, 2) == 57.01


def test_is_billing_close_day_true_on_match():
    assert is_billing_close_day(dt.date(2026, 6, 1), billing_day=1) is True


def test_is_billing_close_day_clamps_to_month_end():
    # billing_day 31 in a 30-day month should fire on the 30th
    assert is_billing_close_day(dt.date(2026, 6, 30), billing_day=31) is True
    assert is_billing_close_day(dt.date(2026, 6, 29), billing_day=31) is False


def test_next_balance_after_expiry_drops_old_buckets():
    # buckets: list of (year, month, amount). Expiry 12 months from 'now'.
    buckets = [(2025, 1, 5.0), (2025, 6, 3.0), (2026, 5, 2.0)]
    kept, expired = next_balance_after_expiry(buckets, now=dt.date(2026, 6, 16), expiry_months=12)
    # 2025-01 is older than 12 months -> expired
    assert expired == 5.0
    assert sum(a for _, _, a in kept) == 5.0


def test_next_balance_after_expiry_disabled_when_zero():
    buckets = [(2020, 1, 5.0)]
    kept, expired = next_balance_after_expiry(buckets, now=dt.date(2026, 6, 16), expiry_months=0)
    assert expired == 0.0
    assert kept == buckets
