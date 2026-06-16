"""Sensor entities for Bateria Virtual."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BVCoordinator


@dataclass(frozen=True, kw_only=True)
class BVSensorDescription:
    """Describes one derived sensor."""

    key: str
    name: str
    unit: str
    device_class: SensorDeviceClass | None
    value_fn: Callable[[BVCoordinator], float]
    state_class: SensorStateClass | None = None


_EUR = "EUR"

SENSORS: tuple[BVSensorDescription, ...] = (
    BVSensorDescription(
        key="virtual_battery_balance",
        name="Virtual battery balance",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: round(c.state.balance, 2),
    ),
    BVSensorDescription(
        key="surplus_value_month",
        name="Surplus value this month",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda c: round(c.state.surplus_value_month, 2),
    ),
    BVSensorDescription(
        key="grid_import_month",
        name="Grid import this month",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda c: round(c.state.import_kwh_month, 3),
    ),
    BVSensorDescription(
        key="estimated_bill",
        name="Estimated bill",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda c: round(c.current_bill().total, 2),
    ),
    BVSensorDescription(
        key="estimated_discount",
        name="Estimated discount",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda c: round(min(c.state.balance, c.current_bill().total), 2),
    ),
    BVSensorDescription(
        key="estimated_final_bill",
        name="Estimated final bill",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda c: round(
            max(0.0, c.current_bill().total - c.state.balance), 2
        ),
    ),
    BVSensorDescription(
        key="projected_balance_end_of_month",
        name="Projected balance end of month",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
        value_fn=lambda c: round(
            max(0.0, c.state.balance - c.current_bill().total), 2
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BVCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BVSensor(coordinator, entry, description) for description in SENSORS
    )


class BVSensor(SensorEntity):
    """A single derived Bateria Virtual sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BVCoordinator,
        entry: ConfigEntry,
        description: BVSensorDescription,
    ) -> None:
        self._coordinator = coordinator
        self._description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Bateria Virtual",
            manufacturer="Niba",
        )

    async def async_added_to_hass(self) -> None:
        self._coordinator.add_listener(self.async_write_ha_state)

    @property
    def native_value(self) -> float:
        return self._description.value_fn(self._coordinator)
