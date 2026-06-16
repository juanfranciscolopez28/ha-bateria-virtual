# Batería Virtual (Niba) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **VERSION CONTROL:** This project uses **no git managed by the assistant**. Ignore all "commit" guidance from the executing skill. Each task ends with a **Checkpoint** (run tests / verify) instead of a commit. The user versions and uploads manually.

**Goal:** A HACS-installable Home Assistant custom integration (`bateria_virtual`) that monitors a solar install and models Niba's virtual battery: accumulates surplus value, estimates the full upcoming bill, and shows the discount applied from the accumulated balance.

**Architecture:** A config-flow-driven integration. Pure calculation logic lives in `calc.py` (no HA deps, fully unit-tested). A `DataUpdateCoordinator` listens to the user's existing source entities (push), tracks export-energy deltas, and persists the virtual-battery balance via HA's `Store`. `SensorEntity` instances expose monitoring and billing values. All exposed sensors are named in **English**.

**Tech Stack:** Python 3.12+, Home Assistant 2024.12+ APIs (ConfigEntry, DataUpdateCoordinator, RestoreEntity, helpers.storage.Store), pytest + `pytest-homeassistant-custom-component`, GitHub Actions (hassfest + HACS validate).

---

## File Structure

```
ha-bateria-virtual/
  custom_components/bateria_virtual/
    __init__.py          # setup/unload of the config entry
    manifest.json        # integration metadata
    const.py             # DOMAIN, config keys, defaults
    config_flow.py       # UI config + options flow
    calc.py              # PURE functions: accumulation, bill, discount, rollover, expiry
    storage.py           # Store wrapper for persistent state
    coordinator.py       # DataUpdateCoordinator: source listening + state machine
    sensor.py            # SensorEntity definitions
    translations/
      en.json
      es.json
  tests/
    conftest.py
    test_calc.py
    test_storage.py
    test_config_flow.py
    test_coordinator.py
  dashboards/
    example.yaml
  hacs.json
  README.md
  requirements_test.txt
  .github/workflows/validate.yml
```

Reference spec: `docs/superpowers/specs/2026-06-16-bateria-virtual-design.md`.

---

### Task 1: Project scaffolding & metadata

**Files:**
- Create: `custom_components/bateria_virtual/__init__.py` (empty placeholder for now — real content in Task 7)
- Create: `custom_components/bateria_virtual/manifest.json`
- Create: `custom_components/bateria_virtual/const.py`
- Create: `hacs.json`
- Create: `requirements_test.txt`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `const.py`**

```python
"""Constants for the Bateria Virtual integration."""

DOMAIN = "bateria_virtual"
PLATFORMS = ["sensor"]

# Config entry keys — source entities
CONF_PRODUCTION = "production"
CONF_CONSUMPTION = "consumption"
CONF_GRID_IMPORT = "grid_import"
CONF_GRID_EXPORT = "grid_export"
CONF_PRICE = "price"

# Config entry keys — parameters (editable via options flow)
CONF_SURPLUS_PRICE = "surplus_price"
CONF_INITIAL_BALANCE = "initial_balance"
CONF_BALANCE_EXPIRY_MONTHS = "balance_expiry_months"
CONF_CONTRACTED_POWER_KW = "contracted_power_kw"
CONF_POWER_TERM_EUR_KW_DAY = "power_term_eur_kw_day"
CONF_ELECTRICITY_TAX_PCT = "electricity_tax_pct"
CONF_VAT_PCT = "vat_pct"
CONF_BILLING_DAY = "billing_day"

# Defaults
DEFAULT_SURPLUS_PRICE = 0.06          # €/kWh, taxes excluded
DEFAULT_BALANCE_EXPIRY_MONTHS = 0     # 0 = never expires
DEFAULT_ELECTRICITY_TAX_PCT = 5.11    # impuesto eléctrico
DEFAULT_BILLING_DAY = 1

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN  # one store per config entry, suffixed with entry_id
```

- [ ] **Step 2: Create `manifest.json`**

```json
{
  "domain": "bateria_virtual",
  "name": "Bateria Virtual",
  "version": "0.1.0",
  "documentation": "https://github.com/REPLACE_ME/ha-bateria-virtual",
  "issue_tracker": "https://github.com/REPLACE_ME/ha-bateria-virtual/issues",
  "codeowners": [],
  "config_flow": true,
  "iot_class": "calculated",
  "integration_type": "service",
  "requirements": []
}
```

- [ ] **Step 3: Create `hacs.json`**

```json
{
  "name": "Bateria Virtual",
  "render_readme": true,
  "homeassistant": "2024.12.0"
}
```

- [ ] **Step 4: Create `__init__.py` placeholder**

```python
"""The Bateria Virtual integration."""
```

- [ ] **Step 5: Create `requirements_test.txt`**

```
pytest-homeassistant-custom-component
```

- [ ] **Step 6: Create `tests/conftest.py`**

```python
"""Shared test fixtures."""
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
```

- [ ] **Step 7 — Checkpoint**

Run: `python -c "import json; json.load(open('custom_components/bateria_virtual/manifest.json')); json.load(open('hacs.json')); print('json ok')"`
Expected: `json ok`
Run: `python -c "import ast; ast.parse(open('custom_components/bateria_virtual/const.py').read()); print('const ok')"`
Expected: `const ok`

---

### Task 2: Pure calculation core (`calc.py`)

This is the heart of the integration and has **no HA dependencies**. TDD it fully.

**Files:**
- Create: `custom_components/bateria_virtual/calc.py`
- Test: `tests/test_calc.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for the pure calculation core."""
import datetime as dt

from custom_components.bateria_virtual.calc import (
    BillBreakdown,
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
        contracted_power_kw=4.6,
        power_term_eur_kw_day=0.10,
        days=30,
        electricity_tax_pct=5.11,
        vat_pct=21.0,
    )
    # energy: 100 * 0.20 = 20.0 ; power: 4.6 * 0.10 * 30 = 13.8
    # base = 33.8 ; +5.11% elec tax = 35.52718 ; +21% VAT = 42.9878878
    assert bill.energy == 20.0
    assert round(bill.power, 5) == 13.8
    assert round(bill.total, 2) == 42.99


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_calc.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` for `calc`.

- [ ] **Step 3: Implement `calc.py`**

```python
"""Pure calculation logic for the Bateria Virtual integration.

No Home Assistant imports here — everything is unit-testable in isolation.
"""
from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class BillBreakdown:
    """Estimated bill split into its components (all in €)."""

    energy: float
    power: float
    electricity_tax: float
    vat: float
    total: float


def surplus_value(delta_kwh: float, surplus_price: float) -> float:
    """Value (€) added to the virtual battery for a given export delta.

    A negative delta (meter reset on a total_increasing sensor) yields 0.
    """
    if delta_kwh <= 0:
        return 0.0
    return delta_kwh * surplus_price


def estimate_bill(
    import_kwh: float,
    avg_price: float,
    contracted_power_kw: float,
    power_term_eur_kw_day: float,
    days: int,
    electricity_tax_pct: float,
    vat_pct: float,
) -> BillBreakdown:
    """Estimate a full bill: energy + power + electricity tax + VAT/IGIC."""
    energy = import_kwh * avg_price
    power = contracted_power_kw * power_term_eur_kw_day * days
    base = energy + power
    electricity_tax = base * electricity_tax_pct / 100.0
    taxed_base = base + electricity_tax
    vat = taxed_base * vat_pct / 100.0
    total = taxed_base + vat
    return BillBreakdown(
        energy=energy,
        power=power,
        electricity_tax=electricity_tax,
        vat=vat,
        total=total,
    )


def apply_discount(balance: float, bill: float) -> tuple[float, float]:
    """Apply virtual-battery balance to a bill.

    Returns (new_balance, discount). Niba allows the bill to reach 0.
    """
    discount = min(balance, bill)
    return balance - discount, discount


def is_billing_close_day(today: dt.date, billing_day: int) -> bool:
    """True if `today` is the billing close day, clamping to month length."""
    last_day = calendar.monthrange(today.year, today.month)[1]
    effective_day = min(billing_day, last_day)
    return today.day == effective_day


def next_balance_after_expiry(
    buckets: list[tuple[int, int, float]],
    now: dt.date,
    expiry_months: int,
) -> tuple[list[tuple[int, int, float]], float]:
    """Drop balance buckets older than `expiry_months`.

    `buckets` is a list of (year, month, amount). Returns (kept_buckets, expired_total).
    expiry_months == 0 disables expiry.
    """
    if expiry_months <= 0:
        return buckets, 0.0
    cutoff_index = now.year * 12 + (now.month - 1) - expiry_months
    kept: list[tuple[int, int, float]] = []
    expired = 0.0
    for year, month, amount in buckets:
        bucket_index = year * 12 + (month - 1)
        if bucket_index <= cutoff_index:
            expired += amount
        else:
            kept.append((year, month, amount))
    return kept, expired
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_calc.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5 — Checkpoint**

Run: `pytest tests/test_calc.py -v`
Confirm all green before moving on. `calc.py` is now frozen as the contract for the coordinator.

---

### Task 3: Persistent storage wrapper (`storage.py`)

**Files:**
- Create: `custom_components/bateria_virtual/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for the persistent storage wrapper."""
import pytest

from custom_components.bateria_virtual.storage import BVState, BVStore


@pytest.mark.asyncio
async def test_store_roundtrip(hass):
    store = BVStore(hass, entry_id="abc")
    state = BVState(
        balance=12.5,
        last_export_total=100.0,
        period_start="2026-06-01",
        surplus_value_month=3.0,
        import_kwh_month=50.0,
        buckets=[[2026, 6, 3.0]],
    )
    await store.async_save(state)

    loaded = await store.async_load()
    assert loaded.balance == 12.5
    assert loaded.last_export_total == 100.0
    assert loaded.period_start == "2026-06-01"
    assert loaded.buckets == [[2026, 6, 3.0]]


@pytest.mark.asyncio
async def test_store_load_returns_none_when_empty(hass):
    store = BVStore(hass, entry_id="missing")
    assert await store.async_load() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ImportError` for `storage`.

- [ ] **Step 3: Implement `storage.py`**

```python
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
    import_kwh_month: float = 0.0
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5 — Checkpoint**

Run: `pytest tests/test_storage.py -v`
Confirm green.

---

### Task 4: Config flow & options flow (`config_flow.py` + translations)

**Files:**
- Create: `custom_components/bateria_virtual/config_flow.py`
- Create: `custom_components/bateria_virtual/translations/en.json`
- Create: `custom_components/bateria_virtual/translations/es.json`
- Test: `tests/test_config_flow.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_flow.py -v`
Expected: FAIL — config flow not registered.

- [ ] **Step 3: Implement `config_flow.py`**

```python
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


def _number(min_v: float, step: float) -> selector.NumberSelector:
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
    vol.Required(CONF_POWER_TERM_EUR_KW_DAY, default=0.10): _number(0, 0.0001),
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
                ): _number(0, 0.0001),
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
```

- [ ] **Step 4: Create `translations/en.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Bateria Virtual",
        "description": "Select your existing sensors and Niba's virtual-battery parameters.",
        "data": {
          "production": "Solar production sensor (kWh)",
          "consumption": "Home consumption sensor (kWh)",
          "grid_import": "Grid import sensor (kWh)",
          "grid_export": "Grid export / surplus sensor (kWh)",
          "price": "Current purchase price sensor (€/kWh)",
          "surplus_price": "Surplus price (€/kWh, taxes excluded)",
          "initial_balance": "Initial virtual-battery balance (€)",
          "balance_expiry_months": "Balance expiry (months, 0 = never)",
          "contracted_power_kw": "Contracted power (kW)",
          "power_term_eur_kw_day": "Power term (€/kW·day)",
          "electricity_tax_pct": "Electricity tax (%)",
          "vat_pct": "VAT / IGIC (%)",
          "billing_day": "Billing close day"
        }
      }
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Bateria Virtual parameters",
        "data": {
          "surplus_price": "Surplus price (€/kWh, taxes excluded)",
          "balance_expiry_months": "Balance expiry (months, 0 = never)",
          "contracted_power_kw": "Contracted power (kW)",
          "power_term_eur_kw_day": "Power term (€/kW·day)",
          "electricity_tax_pct": "Electricity tax (%)",
          "vat_pct": "VAT / IGIC (%)",
          "billing_day": "Billing close day"
        }
      }
    }
  }
}
```

- [ ] **Step 5: Create `translations/es.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Batería Virtual",
        "description": "Selecciona tus sensores existentes y los parámetros de la batería virtual de Niba.",
        "data": {
          "production": "Sensor de producción solar (kWh)",
          "consumption": "Sensor de consumo del hogar (kWh)",
          "grid_import": "Sensor de importación de red (kWh)",
          "grid_export": "Sensor de exportación / excedente (kWh)",
          "price": "Sensor de precio de compra actual (€/kWh)",
          "surplus_price": "Precio del excedente (€/kWh, sin impuestos)",
          "initial_balance": "Saldo inicial de la batería virtual (€)",
          "balance_expiry_months": "Caducidad del saldo (meses, 0 = nunca)",
          "contracted_power_kw": "Potencia contratada (kW)",
          "power_term_eur_kw_day": "Término de potencia (€/kW·día)",
          "electricity_tax_pct": "Impuesto eléctrico (%)",
          "vat_pct": "IVA / IGIC (%)",
          "billing_day": "Día de corte de facturación"
        }
      }
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Parámetros de Batería Virtual",
        "data": {
          "surplus_price": "Precio del excedente (€/kWh, sin impuestos)",
          "balance_expiry_months": "Caducidad del saldo (meses, 0 = nunca)",
          "contracted_power_kw": "Potencia contratada (kW)",
          "power_term_eur_kw_day": "Término de potencia (€/kW·día)",
          "electricity_tax_pct": "Impuesto eléctrico (%)",
          "vat_pct": "IVA / IGIC (%)",
          "billing_day": "Día de corte de facturación"
        }
      }
    }
  }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_config_flow.py -v`
Expected: PASS (1 passed).

- [ ] **Step 7 — Checkpoint**

Run: `pytest tests/test_config_flow.py -v`
Confirm green.

---

### Task 5: Coordinator (`coordinator.py`)

The coordinator owns the runtime state machine: it loads/initialises `BVState`, listens to the
export sensor for deltas, accumulates surplus value, computes the live bill estimate, and runs the
billing-close settlement once per day. It exposes a `data` dict consumed by the sensors.

**Files:**
- Create: `custom_components/bateria_virtual/coordinator.py`
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for the coordinator's surplus accumulation."""
import pytest
from homeassistant.core import HomeAssistant

from custom_components.bateria_virtual.coordinator import BVCoordinator
from custom_components.bateria_virtual.const import (
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
    CONF_CONTRACTED_POWER_KW: 4.6,
    CONF_POWER_TERM_EUR_KW_DAY: 0.10,
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_coordinator.py -v`
Expected: FAIL — `ImportError` for `coordinator`.

- [ ] **Step 3: Implement `coordinator.py`**

```python
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
    CONF_CONTRACTED_POWER_KW,
    CONF_ELECTRICITY_TAX_PCT,
    CONF_GRID_EXPORT,
    CONF_GRID_IMPORT,
    CONF_INITIAL_BALANCE,
    CONF_POWER_TERM_EUR_KW_DAY,
    CONF_PRICE,
    CONF_SURPLUS_PRICE,
    CONF_VAT_PCT,
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
        self.handle_import_total(total)
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

    def handle_import_total(self, total: float) -> None:
        if not hasattr(self, "_last_import_total"):
            self._last_import_total = total
            return
        delta = total - self._last_import_total
        self._last_import_total = total
        if delta > 0:
            self.state.import_kwh_month += delta

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
        self.state.import_kwh_month = 0.0
        self.state.period_start = today.isoformat()

    # --- helpers ---------------------------------------------------------

    def _add_to_current_bucket(self, value: float) -> None:
        today = dt_util.now().date()
        if self.state.buckets and self.state.buckets[-1][0] == today.year and (
            self.state.buckets[-1][1] == today.month
        ):
            self.state.buckets[-1][2] += value
        else:
            self.state.buckets.append([today.year, today.month, value])

    def _avg_price(self) -> float:
        price = _to_float(self.hass.states.get(self.config[CONF_PRICE]).state) if (
            self.hass.states.get(self.config[CONF_PRICE]) is not None
        ) else None
        return price if price is not None else 0.0

    def _days_in_period(self, today: dt.date) -> int:
        if not self.state.period_start:
            return today.day
        start = dt.date.fromisoformat(self.state.period_start)
        return max(1, (today - start).days)

    def _estimate_bill(self, today: dt.date) -> calc.BillBreakdown:
        return calc.estimate_bill(
            import_kwh=self.state.import_kwh_month,
            avg_price=self._avg_price(),
            contracted_power_kw=float(self.config[CONF_CONTRACTED_POWER_KW]),
            power_term_eur_kw_day=float(self.config[CONF_POWER_TERM_EUR_KW_DAY]),
            days=self._days_in_period(today),
            electricity_tax_pct=float(self.config[CONF_ELECTRICITY_TAX_PCT]),
            vat_pct=float(self.config[CONF_VAT_PCT]),
        )

    def current_bill(self) -> calc.BillBreakdown:
        return self._estimate_bill(dt_util.now().date())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_coordinator.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5 — Checkpoint**

Run: `pytest tests/ -v`
Expected: all prior tests still green.

---

### Task 6: Sensors (`sensor.py`)

**Files:**
- Create: `custom_components/bateria_virtual/sensor.py`

(No dedicated unit test file — sensor wiring is exercised by the entry-load smoke test in Task 7. The
calculation behind each value is already covered by `test_calc.py` / `test_coordinator.py`.)

- [ ] **Step 1: Implement `sensor.py`**

```python
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
from homeassistant.core import HomeAssistant, callback
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


_EUR = "EUR"

SENSORS: tuple[BVSensorDescription, ...] = (
    BVSensorDescription(
        key="virtual_battery_balance",
        name="Virtual battery balance",
        unit=_EUR,
        device_class=SensorDeviceClass.MONETARY,
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
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: BVCoordinator,
        entry: ConfigEntry,
        description: BVSensorDescription,
    ) -> None:
        self._coordinator = coordinator
        self._description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class

    async def async_added_to_hass(self) -> None:
        self._coordinator.add_listener(self.async_write_ha_state)

    @property
    def native_value(self) -> float:
        return self._description.value_fn(self._coordinator)
```

- [ ] **Step 2 — Checkpoint**

Run: `python -c "import ast; ast.parse(open('custom_components/bateria_virtual/sensor.py').read()); print('sensor ok')"`
Expected: `sensor ok`

---

### Task 7: Entry setup/unload (`__init__.py`) + entry-load smoke test

**Files:**
- Modify: `custom_components/bateria_virtual/__init__.py`
- Test: `tests/test_init.py` (create)

- [ ] **Step 1: Write failing smoke test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_init.py -v`
Expected: FAIL — entry setup not implemented.

- [ ] **Step 3: Implement `__init__.py`**

```python
"""The Bateria Virtual integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import BVCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = {**entry.data, **entry.options}
    coordinator = BVCoordinator(hass, entry.entry_id, config)
    await coordinator.async_initialise()
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: BVCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_init.py -v`
Expected: PASS (1 passed). The entity_id is `sensor.bateria_virtual_virtual_battery_balance`
because `_attr_has_entity_name = True` prefixes with the integration/device name.

- [ ] **Step 5 — Checkpoint**

Run: `pytest tests/ -v`
Expected: full suite green.

---

### Task 8: Example dashboard, README, CI

**Files:**
- Create: `dashboards/example.yaml`
- Create: `README.md`
- Create: `.github/workflows/validate.yml`

- [ ] **Step 1: Create `dashboards/example.yaml`**

```yaml
# Example dashboard. Paste into a new dashboard (raw config editor) and adjust
# entity_ids if yours differ. Uses only native HA cards.
title: Batería Virtual
views:
  - title: Solar & Batería Virtual
    cards:
      - type: glance
        title: Hoy
        entities:
          - entity: sensor.bateria_virtual_grid_import_month
          - entity: sensor.bateria_virtual_surplus_value_month
      - type: gauge
        name: Saldo batería virtual
        entity: sensor.bateria_virtual_virtual_battery_balance
        unit: €
        min: 0
        max: 100
      - type: entities
        title: Próxima factura (estimación)
        entities:
          - entity: sensor.bateria_virtual_estimated_bill
            name: Factura estimada
          - entity: sensor.bateria_virtual_estimated_discount
            name: Descuento batería virtual
          - entity: sensor.bateria_virtual_estimated_final_bill
            name: Factura final estimada
          - entity: sensor.bateria_virtual_projected_balance_end_of_month
            name: Saldo proyectado fin de mes
      - type: statistics-graph
        title: Saldo batería virtual (histórico)
        entities:
          - sensor.bateria_virtual_virtual_battery_balance
```

- [ ] **Step 2: Create `README.md`**

````markdown
# Batería Virtual (Niba) — Home Assistant integration

Monitors a solar install and models Niba's virtual battery: accumulates the value of your
surplus, estimates the full upcoming bill, and shows how much the accumulated balance will
discount from it.

## Features

- Surplus value accumulation at a fixed €/kWh (default 0.06, taxes excluded).
- Full bill estimate: energy + power term + electricity tax + VAT/IGIC.
- Virtual-battery balance with optional expiry, persisted across restarts.
- Estimated discount and final bill sensors. All sensors named in English.

## Installation (HACS)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo as an **Integration**.
2. Install "Bateria Virtual", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "Bateria Virtual".
4. Select your existing sensors (production, consumption, grid import, grid export, price)
   and fill in the parameters.

## Configuration parameters

| Parameter | Meaning | Default |
|-----------|---------|---------|
| Surplus price | €/kWh paid for exported energy, taxes excluded | 0.06 |
| Initial balance | Current Niba virtual-battery balance (€) | 0 |
| Balance expiry | Months before unused balance expires (0 = never) | 0 |
| Contracted power | kW contracted | — |
| Power term | €/kW·day | — |
| Electricity tax | % | 5.11 |
| VAT / IGIC | % (check your invoice) | 21 |
| Billing day | Day of month the bill closes | 1 |

## Sensors

`virtual_battery_balance`, `surplus_value_month`, `grid_import_month`, `estimated_bill`,
`estimated_discount`, `estimated_final_bill`, `projected_balance_end_of_month`.

## Example dashboard

See `dashboards/example.yaml`.

## Disclaimer

Estimates only. The balance is modelled inside HA (no Niba API); set the initial balance to
match your real Niba balance. Adjust parameters to match your tariff.
````

- [ ] **Step 3: Create `.github/workflows/validate.yml`**

```yaml
name: Validate

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration

  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements_test.txt
      - run: pytest tests/ -v
```

- [ ] **Step 4 — Checkpoint**

Run: `pytest tests/ -v`
Expected: full suite green.
Run: `python -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('dashboards/*.yaml')+glob.glob('.github/workflows/*.yml')]; print('yaml ok')"`
Expected: `yaml ok` (requires PyYAML; skip if not installed).

---

## Self-Review notes

- **Spec coverage:** config flow (§4) → Task 4; English sensors (§5) → Task 6; calc logic (§6) →
  Tasks 2 & 5; storage (§6) → Task 3; dashboard (§7) → Task 8; tests + CI (§8) → Tasks 2–8 + Task 8.
  Monitoring "today" aggregates from §5 were intentionally trimmed to `*_month` + bill sensors for the
  first version (production/consumption "today" come straight from the user's existing Solarman
  sensors and the native Energy dashboard); add per-day aggregate sensors later if wanted.
- **Type consistency:** `BVState` fields (Task 3) are used unchanged by the coordinator (Task 5) and
  sensors (Task 6). `calc.BillBreakdown.total` is the field referenced by `current_bill()` consumers.
  `BVCoordinator.handle_export_total` / `current_bill` / `add_listener` signatures match their callers.
- **No placeholders:** every code step contains full code; `REPLACE_ME` in `manifest.json`/README is an
  intentional user-supplied GitHub URL, flagged as such.
```
