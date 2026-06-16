# Batería Virtual — Home Assistant integration

Monitors a solar install and models a **virtual battery** (the surplus-compensation scheme
offered by several Spanish retailers): it accumulates the value of your surplus, estimates
the full upcoming bill, and shows how much the accumulated balance will discount from it.
It is retailer-agnostic — configure the surplus price, tariff and expiry to match yours.

## Features

- Surplus value accumulation at a fixed €/kWh (default 0.06, taxes excluded).
- Full bill estimate: energy (3 periods P1/P2/P3) + power term (2 periods P1/P2) +
  electricity tax + VAT/IGIC.
- Energy split by the active period, read from a sensor's `period` attribute
  (e.g. ESIOS PVPC), each period priced at its own configurable €/kWh.
- Virtual-battery balance with optional expiry, persisted across restarts.
- Estimated discount and final bill sensors. Entity names localised (es/en).
- Lifetime savings, balance coverage (in months) and days-until-billing-close sensors.
- Key monetary/energy sensors kept in long-term statistics (see the Sensors table).

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
| Initial balance | Current virtual-battery balance with your retailer (€) | 0 |
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

All entities belong to the single "Bateria Virtual" device. The **LTS** column marks the
sensors that declare a `state_class` and are therefore kept in Home Assistant's **long-term
statistics** (visible in the *Statistics* graph, the Energy dashboard, and months/years of
history); the rest only keep short-term state history, which the recorder purges (default 10
days).

### How the bill is calculated

Several sensors derive from the same bill estimate. Given the kWh imported in each energy
period so far this cycle, the configured prices, and the days elapsed:

```
energy        = kWh_P1·price_P1 + kWh_P2·price_P2 + kWh_P3·price_P3
power         = (kW_P1·term_P1 + kW_P2·term_P2) · days_elapsed
base          = energy + power
electricity_tax = base · (electricity_tax_% / 100)        # e.g. 5.11 %
taxed_base    = base + electricity_tax
VAT           = taxed_base · (VAT_% / 100)                # 21 %, or IGIC in the Canaries
bill.total    = taxed_base + VAT
```

- The **energy** term grows in real time: every positive delta of the grid-import meter is
  added to the bucket of the currently active period (P1/P2/P3), read from the period
  sensor's `period` attribute.
- The **power** term is `days_elapsed` since the cycle opened (today excluded) times the
  fixed daily power cost — it only steps up once per day.
- Counters reset and the balance is discounted on the **billing day**.

### Reference

| Sensor (entity key) | Unit | LTS | What it is / how it's calculated |
|---------------------|------|:---:|----------------------------------|
| `virtual_battery_balance` | € | ✅ | Current virtual-battery balance. Starts at *Initial balance*; **+** surplus value on every export delta; **−** the discounted bill on the billing day; **−** any buckets that pass the expiry window. |
| `surplus_value_month` | € | — | Surplus accrued **this billing cycle**: `Σ (export_delta_kWh · surplus_price)`. Resets to 0 on the billing day. |
| `grid_import_month` | kWh | ✅ | Total energy imported from the grid this cycle = `kWh_P1 + kWh_P2 + kWh_P3`. Resets on the billing day. |
| `grid_import_month_p1` | kWh | ✅ | Energy imported this cycle while the active period was **P1 (punta)**. |
| `grid_import_month_p2` | kWh | ✅ | Energy imported this cycle while the active period was **P2 (llano)**. |
| `grid_import_month_p3` | kWh | ✅ | Energy imported this cycle while the active period was **P3 (valle)**. |
| `current_energy_price` | €/kWh | — | Price of the **currently active** period including taxes: `price · (1 + electricity_tax%/100) · (1 + VAT%/100)`. |
| `estimated_bill` | € | — | The running bill `bill.total` (see formula above): cost accrued so far this cycle, taxes included, **before** the battery discount. |
| `estimated_discount` | € | — | How much of the running bill the balance would cover right now: `min(balance, bill.total)`. |
| `estimated_final_bill` | € | ✅ | What you'd pay after the discount: `max(0, bill.total − balance)`. |
| `projected_balance_end_of_month` | € | — | Balance left over if the bill were settled now: `max(0, balance − bill.total)`. |
| `lifetime_savings` | € | ✅ | Total amount the virtual battery has **ever** discounted from bills. Increases by each billing day's discount and never resets. |
| `balance_coverage_months` | months | ✅ | How many monthly bills the balance could cover: `balance / monthly_estimate`, where `monthly_estimate` scales the running bill to the full cycle (full-cycle power + linear energy projection). |
| `days_until_billing_close` | d | ✅ | Whole days remaining until the next billing close (0 on the billing day itself), clamped to the month length. |

## Example dashboard

- `dashboards/example.yaml` — basic panel using only native HA cards.
- `dashboards/example-advanced.yaml` — richer panel in **per-view** format. Requires
  these HACS → Frontend cards: **ApexCharts Card**, **Bubble Card**, **Mushroom**,
  **button-card**. Paste it into a view's YAML editor (*Editar dashboard → vista → ⋮ →
  Editar en YAML*), replacing the view's contents.

## Disclaimer

Estimates only. The balance is modelled inside HA (no retailer API); set the initial balance
to match your real virtual-battery balance. Adjust parameters to match your tariff.
