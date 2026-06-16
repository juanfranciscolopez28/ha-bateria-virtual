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
