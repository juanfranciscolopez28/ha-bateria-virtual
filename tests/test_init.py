"""Smoke test: a config entry sets up and creates sensors."""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bateria_virtual.const import DOMAIN
from tests.test_coordinator import CONFIG


@pytest.mark.asyncio
async def test_entry_setup_creates_balance_sensor(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=CONFIG)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.bateria_virtual_virtual_battery_balance")
    assert state is not None
    assert float(state.state) == 5.0
