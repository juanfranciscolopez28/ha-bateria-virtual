"""Persistent state for a Bateria Virtual config entry."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


@dataclass
class BVState:
    """Persisted state of the virtual battery for one config entry."""

    balance: float = 0.0
    last_export_total: float | None = None
    period_start: str | None = None  # ISO date of current billing period start
    surplus_value_month: float = 0.0
    # Imported kWh this month, split by energy period (P1 punta / P2 llano / P3 valle).
    import_kwh_p1: float = 0.0
    import_kwh_p2: float = 0.0
    import_kwh_p3: float = 0.0
    buckets: list = field(default_factory=list)  # list of [year, month, amount]


class BVStore:
    """Thin wrapper over HA Store, one file per config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry_id}")

    async def async_load(self) -> BVState | None:
        data = await self._store.async_load()
        if data is None:
            return None
        return BVState(**data)

    async def async_save(self, state: BVState) -> None:
        await self._store.async_save(asdict(state))
