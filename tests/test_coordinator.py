"""Tests for the coordinator's surplus accumulation."""
import datetime as dt

import pytest
from homeassistant.core import HomeAssistant

from custom_components.bateria_virtual.coordinator import BVCoordinator
from custom_components.bateria_virtual.const import (
    CONF_BALANCE_EXPIRY_MONTHS,
    CONF_BILLING_DAY,
    CONF_CONSUMPTION,
    CONF_CONTRACTED_POWER_P1_KW,
    CONF_CONTRACTED_POWER_P2_KW,
    CONF_ELECTRICITY_TAX_PCT,
    CONF_ENERGY_PRICE_P1,
    CONF_ENERGY_PRICE_P2,
    CONF_ENERGY_PRICE_P3,
    CONF_GRID_EXPORT,
    CONF_GRID_IMPORT,
    CONF_INITIAL_BALANCE,
    CONF_PERIOD_SENSOR,
    CONF_POWER_TERM_P1_EUR_KW_DAY,
    CONF_POWER_TERM_P2_EUR_KW_DAY,
    CONF_PRODUCTION,
    CONF_SURPLUS_PRICE,
    CONF_VAT_PCT,
)

CONFIG = {
    CONF_PRODUCTION: "sensor.solar_production",
    CONF_CONSUMPTION: "sensor.home_consumption",
    CONF_GRID_IMPORT: "sensor.grid_import",
    CONF_GRID_EXPORT: "sensor.grid_export",
    CONF_PERIOD_SENSOR: "sensor.esios_pvpc",
    CONF_SURPLUS_PRICE: 0.06,
    CONF_INITIAL_BALANCE: 5.0,
    CONF_BALANCE_EXPIRY_MONTHS: 0,
    CONF_ENERGY_PRICE_P1: 0.196,
    CONF_ENERGY_PRICE_P2: 0.169,
    CONF_ENERGY_PRICE_P3: 0.089,
    CONF_CONTRACTED_POWER_P1_KW: 3.45,
    CONF_POWER_TERM_P1_EUR_KW_DAY: 0.10,
    CONF_CONTRACTED_POWER_P2_KW: 3.45,
    CONF_POWER_TERM_P2_EUR_KW_DAY: 0.02,
    CONF_ELECTRICITY_TAX_PCT: 5.11,
    CONF_VAT_PCT: 21.0,
    CONF_BILLING_DAY: 1,
}


@pytest.mark.asyncio
async def test_export_delta_increases_balance(hass: HomeAssistant):
    coord = BVCoordinator(hass, entry_id="t1", config=CONFIG)
    await coord.async_initialise()

    # First export reading just primes the baseline, no balance change.
    coord.handle_export_total(100.0)
    assert coord.state.balance == 5.0

    # +10 kWh exported -> +0.6 €
    coord.handle_export_total(110.0)
    assert round(coord.state.balance, 2) == 5.60
    assert round(coord.state.surplus_value_month, 2) == 0.60


@pytest.mark.asyncio
async def test_meter_reset_does_not_reduce_balance(hass: HomeAssistant):
    coord = BVCoordinator(hass, entry_id="t2", config=CONFIG)
    await coord.async_initialise()
    coord.handle_export_total(100.0)
    coord.handle_export_total(2.0)  # sensor reset
    assert coord.state.balance == 5.0


@pytest.mark.asyncio
async def test_settlement_accumulates_lifetime_savings(hass: HomeAssistant):
    coord = BVCoordinator(hass, entry_id="t4", config=CONFIG)
    await coord.async_initialise()
    coord.state.period_start = "2026-06-01"
    coord.state.balance = 5.0
    coord.state.import_kwh_p1 = 10.0
    assert coord.state.lifetime_savings == 0.0

    # Billing day (1) -> the bill is discounted from the balance and the
    # discount is added to the lifetime savings counter.
    discounted = coord.state.balance
    coord.run_settlement(dt.date(2026, 6, 1))

    assert coord.state.lifetime_savings > 0
    assert round(coord.state.lifetime_savings, 2) == round(
        discounted - coord.state.balance, 2
    )


@pytest.mark.asyncio
async def test_import_delta_routed_to_active_period(hass: HomeAssistant):
    coord = BVCoordinator(hass, entry_id="t3", config=CONFIG)
    await coord.async_initialise()

    coord.handle_import_total(100.0, "P1")  # primes baseline, no accumulation
    coord.handle_import_total(110.0, "P1")  # +10 kWh in P1 punta
    coord.handle_import_total(115.0, "P3")  # +5 kWh in P3 valle

    assert round(coord.state.import_kwh_p1, 3) == 10.0
    assert round(coord.state.import_kwh_p2, 3) == 0.0
    assert round(coord.state.import_kwh_p3, 3) == 5.0
