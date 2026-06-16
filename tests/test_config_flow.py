"""Tests for the config flow."""
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.bateria_virtual.const import (
    CONF_GRID_EXPORT,
    CONF_GRID_IMPORT,
    CONF_PRICE,
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
        CONF_PRICE: "sensor.current_price",
        CONF_SURPLUS_PRICE: 0.06,
        "initial_balance": 0.0,
        "balance_expiry_months": 0,
        "contracted_power_kw": 4.6,
        "power_term_eur_kw_day": 0.10,
        "electricity_tax_pct": 5.11,
        CONF_VAT_PCT: 21.0,
        "billing_day": 1,
    }
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SURPLUS_PRICE] == 0.06
