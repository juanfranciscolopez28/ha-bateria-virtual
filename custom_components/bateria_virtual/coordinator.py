"""Runtime coordinator for a Bateria Virtual config entry."""
from __future__ import annotations

import datetime as dt
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from . import calc
from .const import (
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
    CONF_INITIAL_BALANCE,
    CONF_PERIOD_SENSOR,
    CONF_POWER_TERM_P1_EUR_KW_DAY,
    CONF_POWER_TERM_P2_EUR_KW_DAY,
    CONF_SURPLUS_PRICE,
    CONF_VAT_PCT,
    ENERGY_PERIODS,
    PERIOD_ATTRIBUTE,
    PERIOD_P1,
)
from .storage import BVState, BVStore

_LOGGER = logging.getLogger(__name__)


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BVCoordinator:
    """Owns the persistent state and reacts to source-sensor changes."""

    def __init__(self, hass: HomeAssistant, entry_id: str, config: dict) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.config = config
        self._store = BVStore(hass, entry_id)
        self.state: BVState = BVState()
        self._unsub: list = []
        self._listeners: list = []  # sensor update callbacks
        self._last_import_total: float | None = None
        self._last_period: str = PERIOD_P1  # fallback when sensor unavailable

    async def async_initialise(self) -> None:
        """Load persisted state or seed it from the configured initial balance."""
        loaded = await self._store.async_load()
        if loaded is not None:
            self.state = loaded
            return
        today = dt_util.now().date()
        self.state = BVState(
            balance=float(self.config[CONF_INITIAL_BALANCE]),
            period_start=today.replace(day=1).isoformat(),
            buckets=[],
        )
        await self._store.async_save(self.state)

    async def async_start(self) -> None:
        """Attach listeners to source entities and the daily settlement timer."""
        export_entity = self.config[CONF_GRID_EXPORT]
        self._unsub.append(
            async_track_state_change_event(
                self.hass, [export_entity], self._on_export_event
            )
        )
        import_entity = self.config[CONF_GRID_IMPORT]
        self._unsub.append(
            async_track_state_change_event(
                self.hass, [import_entity], self._on_import_event
            )
        )
        # Run the billing settlement once a day at 00:05.
        self._unsub.append(
            async_track_time_change(
                self.hass, self._on_daily_tick, hour=0, minute=5, second=0
            )
        )

    async def async_stop(self) -> None:
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()

    # --- listener registration for sensors -------------------------------

    @callback
    def add_listener(self, update_cb) -> None:
        self._listeners.append(update_cb)

    @callback
    def _notify(self) -> None:
        for cb in self._listeners:
            cb()

    # --- event handlers --------------------------------------------------

    @callback
    def _on_export_event(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        total = _to_float(new_state.state)
        if total is None:
            return
        self.handle_export_total(total)
        self.hass.async_create_task(self._store.async_save(self.state))
        self._notify()

    @callback
    def _on_import_event(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        total = _to_float(new_state.state)
        if total is None:
            return
        self.handle_import_total(total, self._current_period())
        self.hass.async_create_task(self._store.async_save(self.state))
        self._notify()

    async def _on_daily_tick(self, now: dt.datetime) -> None:
        self.run_settlement(now.date())
        await self._store.async_save(self.state)
        self._notify()

    # --- pure-ish state transitions (unit-tested) ------------------------

    def handle_export_total(self, total: float) -> None:
        """Update balance from a new export total. First reading primes baseline."""
        if self.state.last_export_total is None:
            self.state.last_export_total = total
            return
        delta = total - self.state.last_export_total
        self.state.last_export_total = total
        value = calc.surplus_value(delta, float(self.config[CONF_SURPLUS_PRICE]))
        if value <= 0:
            return
        self.state.balance += value
        self.state.surplus_value_month += value
        self._add_to_current_bucket(value)

    def handle_import_total(self, total: float, period: str) -> None:
        """Accumulate an import delta into the bucket of the active energy period."""
        if self._last_import_total is None:
            self._last_import_total = total
            return
        delta = total - self._last_import_total
        self._last_import_total = total
        if delta <= 0:
            return
        if period == "P2":
            self.state.import_kwh_p2 += delta
        elif period == "P3":
            self.state.import_kwh_p3 += delta
        else:  # P1 / unknown -> treat as punta
            self.state.import_kwh_p1 += delta

    def run_settlement(self, today: dt.date) -> None:
        """Expire old buckets, and on billing day apply the estimated bill."""
        kept, expired = calc.next_balance_after_expiry(
            [tuple(b) for b in self.state.buckets],
            now=today,
            expiry_months=int(self.config[CONF_BALANCE_EXPIRY_MONTHS]),
        )
        if expired > 0:
            self.state.balance = max(0.0, self.state.balance - expired)
            self.state.buckets = [list(b) for b in kept]

        if not calc.is_billing_close_day(today, int(self.config[CONF_BILLING_DAY])):
            return

        bill = self._estimate_bill(today)
        new_balance, _ = calc.apply_discount(self.state.balance, bill.total)
        self.state.balance = new_balance
        # Reset monthly counters for the new period.
        self.state.surplus_value_month = 0.0
        self.state.import_kwh_p1 = 0.0
        self.state.import_kwh_p2 = 0.0
        self.state.import_kwh_p3 = 0.0
        self.state.period_start = today.isoformat()

    # --- helpers ---------------------------------------------------------

    def _add_to_current_bucket(self, value: float) -> None:
        today = dt_util.now().date()
        if (
            self.state.buckets
            and self.state.buckets[-1][0] == today.year
            and self.state.buckets[-1][1] == today.month
        ):
            self.state.buckets[-1][2] += value
        else:
            self.state.buckets.append([today.year, today.month, value])

    def _current_period(self) -> str:
        """Active energy period from the period sensor's attribute.

        Falls back to the last known period (P1 initially) when unavailable.
        """
        sensor = self.config.get(CONF_PERIOD_SENSOR)
        if sensor:
            state = self.hass.states.get(sensor)
            if state is not None:
                period = state.attributes.get(PERIOD_ATTRIBUTE)
                if period in ENERGY_PERIODS:
                    self._last_period = period
                    return period
        return self._last_period

    def _energy_price(self, period: str) -> float:
        """Configured €/kWh (taxes excluded) for an energy period."""
        key = {
            "P1": CONF_ENERGY_PRICE_P1,
            "P2": CONF_ENERGY_PRICE_P2,
            "P3": CONF_ENERGY_PRICE_P3,
        }[period]
        return float(self.config[key])

    def current_energy_price_with_taxes(self) -> float:
        """Current €/kWh including electricity tax and VAT (matches the template)."""
        return calc.price_with_taxes(
            self._energy_price(self._current_period()),
            float(self.config[CONF_ELECTRICITY_TAX_PCT]),
            float(self.config[CONF_VAT_PCT]),
        )

    def _days_in_period(self, today: dt.date) -> int:
        if not self.state.period_start:
            return today.day
        start = dt.date.fromisoformat(self.state.period_start)
        return max(1, (today - start).days)

    def _estimate_bill(self, today: dt.date) -> calc.BillBreakdown:
        return calc.estimate_bill(
            import_kwh_p1=self.state.import_kwh_p1,
            import_kwh_p2=self.state.import_kwh_p2,
            import_kwh_p3=self.state.import_kwh_p3,
            energy_price_p1=float(self.config[CONF_ENERGY_PRICE_P1]),
            energy_price_p2=float(self.config[CONF_ENERGY_PRICE_P2]),
            energy_price_p3=float(self.config[CONF_ENERGY_PRICE_P3]),
            contracted_power_p1_kw=float(self.config[CONF_CONTRACTED_POWER_P1_KW]),
            power_term_p1_eur_kw_day=float(self.config[CONF_POWER_TERM_P1_EUR_KW_DAY]),
            contracted_power_p2_kw=float(self.config[CONF_CONTRACTED_POWER_P2_KW]),
            power_term_p2_eur_kw_day=float(self.config[CONF_POWER_TERM_P2_EUR_KW_DAY]),
            days=self._days_in_period(today),
            electricity_tax_pct=float(self.config[CONF_ELECTRICITY_TAX_PCT]),
            vat_pct=float(self.config[CONF_VAT_PCT]),
        )

    def current_bill(self) -> calc.BillBreakdown:
        return self._estimate_bill(dt_util.now().date())
