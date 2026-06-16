# Batería Virtual (Niba) — Home Assistant integration

Monitors a solar install and models Niba's virtual battery: accumulates the value of your
surplus, estimates the full upcoming bill, and shows how much the accumulated balance will
discount from it.

## Features

- Surplus value accumulation at a fixed €/kWh (default 0.06, taxes excluded).
- Full bill estimate: energy (3 periods P1/P2/P3) + power term (2 periods P1/P2) +
  electricity tax + VAT/IGIC.
- Energy split by the active period, read from a sensor's `period` attribute
  (e.g. ESIOS PVPC), each period priced at its own configurable €/kWh.
- Virtual-battery balance with optional expiry, persisted across restarts.
- Estimated discount and final bill sensors. Entity names localised (es/en).

## Installation (HACS)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo as an **Integration**.
2. Install "Bateria Virtual", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "Bateria Virtual".
4. Select your existing sensors (production, consumption, grid import, grid export, and a
   period sensor whose `period` attribute reports P1/P2/P3) and fill in the parameters.

## Configuration parameters

| Parameter | Meaning | Default |
|-----------|---------|---------|
| Period sensor | Sensor with a `period` attribute (P1/P2/P3), e.g. ESIOS PVPC | `sensor.esios_pvpc` |
| Surplus price | €/kWh paid for exported energy, taxes excluded | 0.06 |
| Initial balance | Current Niba virtual-battery balance (€) | 0 |
| Balance expiry | Months before unused balance expires (0 = never) | 0 |
| Energy price P1 / P2 / P3 | €/kWh per period (punta / llano / valle), taxes excluded | 0.196 / 0.169 / 0.089 |
| Contracted power P1 / P2 | kW contracted (punta / valle) | 3.45 / 3.45 |
| Power term P1 / P2 | €/kW·day (punta / valle) | 0.10 / 0.02 |
| Electricity tax | % | 5.11269632 |
| VAT / IGIC | % (check your invoice) | 21 |
| Billing day | Day of month the bill closes | 1 |

> Note: the two **power** periods (P1 punta / P2 valle) are distinct from the three
> **energy** periods (P1 punta / P2 llano / P3 valle) in the 2.0TD tariff.

## Sensors

`virtual_battery_balance`, `surplus_value_month`, `grid_import_month` (+ per-period
`grid_import_month_p1/p2/p3`), `current_energy_price` (€/kWh incl. taxes), `estimated_bill`,
`estimated_discount`, `estimated_final_bill`, `projected_balance_end_of_month`.

## Example dashboard

See `dashboards/example.yaml`.

## Disclaimer

Estimates only. The balance is modelled inside HA (no Niba API); set the initial balance to
match your real Niba balance. Adjust parameters to match your tariff.
