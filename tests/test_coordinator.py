"""Tests for the coordinator's surplus accumulation."""
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
    CONF_GRID_EXPORT,
    CONF_GRID_IMPORT,
    CONF_INITIAL_BALANCE,
    CONF_POWER_TERM_P1_EUR_KW_DAY,
    CONF_POWER_TERM_P2_EUR_KW_DAY,
    CONF_PRICE,
    CONF_PRODUCTION,
    CONF_SURPLUS_PRICE,
    CONF_VAT_PCT,
)

CONFIG = {
    CONF_PRODUCTION: "sensor.solar_production",
    CONF_CONSUMPTION: "sensor.home_consumption",
    CONF_GRID_IMPORT: "sensor.grid_import",
    CONF_GRID_EXPORT: "sensor.grid_export",
    CONF_PRICE: "sensor.current_price",
    CONF_SURPLUS_PRICE: 0.06,
    CONF_INITIAL_BALANCE: 5.0,
    CONF_BALANCE_EXPIRY_MONTHS: 0,
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
