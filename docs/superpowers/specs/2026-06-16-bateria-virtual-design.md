# Diseño — Integración Home Assistant "Batería Virtual" (Niba)

**Fecha:** 2026-06-16
**Proyecto:** `~/IdeaProjects/ha-bateria-virtual`
**Tipo:** Integración custom de Home Assistant instalable vía HACS
**Dominio de la integración:** `bateria_virtual`

> Nota de versionado: este proyecto **no usa git gestionado por el asistente**. El usuario lo sube a GitHub manualmente.

## 1. Objetivo

Monitorizar una instalación solar (inversor INVT 6x integrado vía Solarman en HA) y modelar la
**batería virtual** de la comercializadora **Niba**: acumular el valor económico de los excedentes,
estimar la próxima factura completa y mostrar cuánto se descontará de ella usando el saldo acumulado.

Todos los sensores expuestos por la integración tendrán **nombre y entity_id en inglés**.

## 2. Contexto del usuario (reglas de negocio confirmadas)

- Comercializadora: **Niba**.
- Batería virtual: descuenta **peajes e impuestos**, puede llegar a **factura 0**, **sin cuota mensual**.
- Caducidad del saldo: **desconocida** → se trata como "sin caducidad" pero **configurable** (meses; 0 = sin caducidad).
- Excedente valorado a **precio fijo €/kWh** (valor exacto configurable).
- Sensores ya existentes en HA: producción solar, consumo del hogar, import/export de red, precio PVPC,
  y **ayudantes que calculan el precio real del kWh** (PVPC + precios de contrato).
- Proyección de factura deseada: **completa** = energía variable + término de potencia fijo + impuesto eléctrico + IVA/IGIC.

## 3. Decisión de arquitectura

Integración custom en Python (no addon de Supervisor, no paquete YAML, no tarjeta custom).
La parte con estado (saldo de la batería virtual) se calcula con el **Enfoque A**:

> La integración escucha el sensor de **export/excedente** (kWh, `total_increasing`), calcula el delta
> de cada actualización y suma `delta × precio_fijo` al saldo. Persiste saldo y último total visto con
> el `Store` de HA. Robusto ante reinicios; no depende de recalcular desde cero.

Descartado el Enfoque B (recalcular el saldo entero en cada actualización): frágil ante reinicios y
cambios de configuración, difícil de cuadrar con el saldo real de Niba.

## 4. Configuración (config flow — todo desde la UI)

**Selección de entidades existentes** (entity selectors):
- `production` — producción solar (sensor de energía kWh, `total_increasing`)
- `consumption` — consumo del hogar (kWh)
- `grid_import` — energía importada de red (kWh)
- `grid_export` — energía exportada/excedente (kWh) — **obligatorio** para la BV
- `price` — sensor de precio actual de compra €/kWh (el ayudante del usuario)

**Parámetros numéricos:**
- `surplus_price` — precio fijo del excedente (€/kWh) — **por defecto 0,06** (sin impuestos)
- `initial_balance` — saldo inicial de la batería virtual (€)
- `balance_expiry_months` — caducidad del saldo en meses (0 = sin caducidad; por defecto 0)
- `contracted_power_kw` — potencia contratada (kW) — admite punta/valle si difieren
- `power_term_eur_kw_day` — término de potencia (€/kW·día)
- `electricity_tax_pct` — impuesto eléctrico % (por defecto 5,11)
- `vat_pct` — IVA/IGIC % (configurable, **sin default fijo**; el usuario lo verifica en su factura — 21 % IVA península, o IGIC 0/3/7 % en Canarias)
- `billing_day` — día de corte de facturación (mensual)

Los parámetros editables tras la instalación van en un **options flow**.

## 5. Sensores expuestos (nombres en inglés)

**Monitorización (agregados a partir de los totales existentes):**
- `sensor.bv_production_today`, `sensor.bv_production_month` (kWh)
- `sensor.bv_consumption_today`, `sensor.bv_consumption_month` (kWh)
- `sensor.bv_surplus_today`, `sensor.bv_surplus_month` (kWh)
- `sensor.bv_grid_import_today`, `sensor.bv_grid_import_month` (kWh)
- `sensor.bv_self_consumption_pct` (%)
- `sensor.bv_current_price` (€/kWh) — reflejo del precio actual

**Batería virtual y factura:**
- `sensor.bv_virtual_battery_balance` (€) — **núcleo**, persistente (Enfoque A)
- `sensor.bv_surplus_value_month` (€) — valor de excedentes acumulado en el periodo
- `sensor.bv_estimated_bill` (€) — energía + potencia fija + impuesto eléctrico + IVA/IGIC
- `sensor.bv_estimated_discount` (€) = `min(balance, estimated_bill)`
- `sensor.bv_estimated_final_bill` (€) = `estimated_bill − estimated_discount`
- `sensor.bv_projected_balance_end_of_month` (€)

Clases de dispositivo y `state_class` adecuados (energy/monetary; `total`/`measurement`) para que sean
compatibles con el **Energy dashboard nativo** y con estadísticas a largo plazo.

## 6. Lógica de cálculo

- **`calc.py`** — módulo de funciones puras (sin dependencias de HA), fácil de testear:
  - acumulación de excedente: `surplus_value += delta_kwh * surplus_price`
  - estimación de factura: energía variable (kWh import × precio) + potencia (`contracted_power_kw × power_term_eur_kw_day × días`) + impuesto eléctrico + IVA/IGIC
  - aplicación de descuento: `discount = min(balance, bill)`, `balance -= discount`
  - rollover de periodo (cierre en `billing_day`) y caducidad de saldo
- **`coordinator.py`** — `DataUpdateCoordinator` que escucha cambios de las entidades fuente (push vía
  `async_track_state_change_event`). Mantiene deltas y dispara el asentamiento al cierre de periodo.
- **`storage.py`** — wrapper de `homeassistant.helpers.storage.Store` para persistir: saldo, último total
  de export visto, inicio del periodo actual, acumulados del mes.

## 7. Dashboard de ejemplo

`dashboards/example.yaml` con tarjetas nativas de HA: producción/consumo/excedente (hoy y mes),
precio actual, saldo de batería virtual, y bloque de proyección (factura estimada / descuento / factura final).
Pensado para copiar y ajustar; compatible con el Energy dashboard nativo.

## 8. Calidad y empaquetado

- Estructura del repo:
  ```
  ha-bateria-virtual/
    custom_components/bateria_virtual/
      __init__.py  manifest.json  config_flow.py  const.py
      coordinator.py  sensor.py  calc.py  storage.py
      translations/{en,es}.json
    hacs.json
    README.md
    dashboards/example.yaml
    tests/
    .github/workflows/   (hassfest + HACS validate)
  ```
- Tests con `pytest-homeassistant-custom-component`: cobertura de `calc.py` (acumulación, estimación de
  factura, descuento, rollover, caducidad) y del config/options flow.
- Workflows de GitHub: `hassfest` y validación HACS.
- Traducciones es/en; README con instrucciones de instalación vía HACS y configuración.

## 9. Fuera de alcance (YAGNI)

- Tarjeta Lovelace custom (frontend) — se usan tarjetas nativas.
- Integración directa con la API/web de Niba para leer el saldo real (no hay API pública conocida);
  el saldo se modela en HA. El saldo inicial se introduce manualmente.
- Soporte multi-comercializadora genérico; el modelo se ajusta a las reglas de Niba (parametrizable).
