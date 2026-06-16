"""Tests for the config flow."""
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bateria_virtual.const import (
    CONF_BALANCE_EXPIRY_MONTHS,
    CONF_BILLING_DAY,
    CONF_CONTRACTED_POWER_P1_KW,
    CONF_CONTRACTED_POWER_P2_KW,
    CONF_ELECTRICITY_TAX_PCT,
    CONF_ENERGY_PRICE_P1,
    CONF_ENERGY_PRICE_P2,
    CONF_ENERGY_PRICE_P3,
    CONF_GRID_EXPORT,
    CONF_GRID_IMPORT,
    CONF_PERIOD_SENSOR,
    CONF_POWER_TERM_P1_EUR_KW_DAY,
    CONF_POWER_TERM_P2_EUR_KW_DAY,
    CONF_SURPLUS_PRICE,
    CONF_VAT_PCT,
    DOMAIN,
)


async def test_user_flow_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = {
        "production": "sensor.solar_production",
        "consumption": "sensor.home_consumption",
        CONF_GRID_IMPORT: "sensor.grid_import",
        CONF_GRID_EXPORT: "sensor.grid_export",
        CONF_PERIOD_SENSOR: "sensor.esios_pvpc",
        CONF_SURPLUS_PRICE: 0.06,
        "initial_balance": 0.0,
        "balance_expiry_months": 0,
        CONF_ENERGY_PRICE_P1: 0.196,
        CONF_ENERGY_PRICE_P2: 0.169,
        CONF_ENERGY_PRICE_P3: 0.089,
        CONF_CONTRACTED_POWER_P1_KW: 3.45,
        CONF_POWER_TERM_P1_EUR_KW_DAY: 0.10,
        CONF_CONTRACTED_POWER_P2_KW: 3.45,
        CONF_POWER_TERM_P2_EUR_KW_DAY: 0.02,
        "electricity_tax_pct": 5.11,
        CONF_VAT_PCT: 21.0,
        "billing_day": 1,
    }
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SURPLUS_PRICE] == 0.06


async def test_options_flow_updates_parameters(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "production": "sensor.solar_production",
            "consumption": "sensor.home_consumption",
            CONF_GRID_IMPORT: "sensor.grid_import",
            CONF_GRID_EXPORT: "sensor.grid_export",
            CONF_PERIOD_SENSOR: "sensor.esios_pvpc",
            CONF_SURPLUS_PRICE: 0.06,
            "initial_balance": 0.0,
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
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SURPLUS_PRICE: 0.07,
            CONF_BALANCE_EXPIRY_MONTHS: 24,
            CONF_ENERGY_PRICE_P1: 0.20,
            CONF_ENERGY_PRICE_P2: 0.17,
            CONF_ENERGY_PRICE_P3: 0.09,
            CONF_CONTRACTED_POWER_P1_KW: 5.75,
            CONF_POWER_TERM_P1_EUR_KW_DAY: 0.12,
            CONF_CONTRACTED_POWER_P2_KW: 5.75,
            CONF_POWER_TERM_P2_EUR_KW_DAY: 0.04,
            CONF_ELECTRICITY_TAX_PCT: 5.11,
            CONF_VAT_PCT: 7.0,
            CONF_BILLING_DAY: 15,
        },
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SURPLUS_PRICE] == 0.07
    assert entry.options[CONF_VAT_PCT] == 7.0
