"""Config and options flow for Bateria Virtual."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BALANCE_EXPIRY_MONTHS,
    CONF_BILLING_DAY,
    CONF_CONSUMPTION,
    CONF_CONTRACTED_POWER_KW,
    CONF_ELECTRICITY_TAX_PCT,
    CONF_GRID_EXPORT,
    CONF_GRID_IMPORT,
    CONF_INITIAL_BALANCE,
    CONF_POWER_TERM_EUR_KW_DAY,
    CONF_PRICE,
    CONF_PRODUCTION,
    CONF_SURPLUS_PRICE,
    CONF_VAT_PCT,
    DEFAULT_BALANCE_EXPIRY_MONTHS,
    DEFAULT_BILLING_DAY,
    DEFAULT_ELECTRICITY_TAX_PCT,
    DEFAULT_SURPLUS_PRICE,
    DOMAIN,
)

_SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)


def _number(min_v: float, step: float | str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_v, step=step, mode=selector.NumberSelectorMode.BOX
        )
    )


# Parameters editable in both the initial flow and the options flow.
_PARAM_SCHEMA = {
    vol.Required(CONF_SURPLUS_PRICE, default=DEFAULT_SURPLUS_PRICE): _number(0, 0.001),
    vol.Required(CONF_INITIAL_BALANCE, default=0.0): _number(0, 0.01),
    vol.Required(
        CONF_BALANCE_EXPIRY_MONTHS, default=DEFAULT_BALANCE_EXPIRY_MONTHS
    ): _number(0, 1),
    vol.Required(CONF_CONTRACTED_POWER_KW, default=4.6): _number(0, 0.1),
    vol.Required(CONF_POWER_TERM_EUR_KW_DAY, default=0.10): _number(0, "any"),
    vol.Required(
        CONF_ELECTRICITY_TAX_PCT, default=DEFAULT_ELECTRICITY_TAX_PCT
    ): _number(0, 0.01),
    vol.Required(CONF_VAT_PCT, default=21.0): _number(0, 0.1),
    vol.Required(CONF_BILLING_DAY, default=DEFAULT_BILLING_DAY): _number(1, 1),
}


class BVConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ):
        if user_input is not None:
            return self.async_create_entry(title="Bateria Virtual", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_PRODUCTION): _SENSOR_SELECTOR,
                vol.Required(CONF_CONSUMPTION): _SENSOR_SELECTOR,
                vol.Required(CONF_GRID_IMPORT): _SENSOR_SELECTOR,
                vol.Required(CONF_GRID_EXPORT): _SENSOR_SELECTOR,
                vol.Required(CONF_PRICE): _SENSOR_SELECTOR,
                **_PARAM_SCHEMA,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BVOptionsFlow(config_entry)


class BVOptionsFlow(OptionsFlow):
    """Edit numeric parameters after install."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SURPLUS_PRICE,
                    default=current.get(CONF_SURPLUS_PRICE, DEFAULT_SURPLUS_PRICE),
                ): _number(0, 0.001),
                vol.Required(
                    CONF_BALANCE_EXPIRY_MONTHS,
                    default=current.get(
                        CONF_BALANCE_EXPIRY_MONTHS, DEFAULT_BALANCE_EXPIRY_MONTHS
                    ),
                ): _number(0, 1),
                vol.Required(
                    CONF_CONTRACTED_POWER_KW,
                    default=current.get(CONF_CONTRACTED_POWER_KW, 4.6),
                ): _number(0, 0.1),
                vol.Required(
                    CONF_POWER_TERM_EUR_KW_DAY,
                    default=current.get(CONF_POWER_TERM_EUR_KW_DAY, 0.10),
                ): _number(0, "any"),
                vol.Required(
                    CONF_ELECTRICITY_TAX_PCT,
                    default=current.get(
                        CONF_ELECTRICITY_TAX_PCT, DEFAULT_ELECTRICITY_TAX_PCT
                    ),
                ): _number(0, 0.01),
                vol.Required(
                    CONF_VAT_PCT, default=current.get(CONF_VAT_PCT, 21.0)
                ): _number(0, 0.1),
                vol.Required(
                    CONF_BILLING_DAY,
                    default=current.get(CONF_BILLING_DAY, DEFAULT_BILLING_DAY),
                ): _number(1, 1),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
