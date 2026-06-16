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
        import_kwh_p1=50.0,
        import_kwh_p2=20.0,
        import_kwh_p3=10.0,
        buckets=[[2026, 6, 3.0]],
    )
    await store.async_save(state)

    loaded = await store.async_load()
    assert loaded.balance == 12.5
    assert loaded.last_export_total == 100.0
    assert loaded.period_start == "2026-06-01"
    assert loaded.import_kwh_p1 == 50.0
    assert loaded.import_kwh_p2 == 20.0
    assert loaded.import_kwh_p3 == 10.0
    assert loaded.buckets == [[2026, 6, 3.0]]


@pytest.mark.asyncio
async def test_store_load_returns_none_when_empty(hass):
    store = BVStore(hass, entry_id="missing")
    assert await store.async_load() is None
