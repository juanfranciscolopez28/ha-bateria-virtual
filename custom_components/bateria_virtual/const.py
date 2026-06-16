"""Constants for the Bateria Virtual integration."""

DOMAIN = "bateria_virtual"
PLATFORMS = ["sensor"]

# Config entry keys — source entities
CONF_PRODUCTION = "production"
CONF_CONSUMPTION = "consumption"
CONF_GRID_IMPORT = "grid_import"
CONF_GRID_EXPORT = "grid_export"
# Sensor whose `period` attribute reports the active energy period ("P1"/"P2"/"P3").
CONF_PERIOD_SENSOR = "period_sensor"

# Energy periods (3, Spanish 2.0TD): P1 punta, P2 llano, P3 valle. NOTE: these are
# distinct from the 2 *power* periods below (power P1/P2 ≠ energy P1/P2/P3).
PERIOD_P1 = "P1"
PERIOD_P2 = "P2"
PERIOD_P3 = "P3"
ENERGY_PERIODS = (PERIOD_P1, PERIOD_P2, PERIOD_P3)
PERIOD_ATTRIBUTE = "period"

# Config entry keys — parameters (editable via options flow)
CONF_SURPLUS_PRICE = "surplus_price"
CONF_INITIAL_BALANCE = "initial_balance"
CONF_BALANCE_EXPIRY_MONTHS = "balance_expiry_months"
# Energy price per period (€/kWh, taxes excluded).
CONF_ENERGY_PRICE_P1 = "energy_price_p1"
CONF_ENERGY_PRICE_P2 = "energy_price_p2"
CONF_ENERGY_PRICE_P3 = "energy_price_p3"
# Two contracted-power periods (Spanish 2.0TD / 3.0TD): P1 (punta) and P2 (valle).
CONF_CONTRACTED_POWER_P1_KW = "contracted_power_p1_kw"
CONF_CONTRACTED_POWER_P2_KW = "contracted_power_p2_kw"
CONF_POWER_TERM_P1_EUR_KW_DAY = "power_term_p1_eur_kw_day"
CONF_POWER_TERM_P2_EUR_KW_DAY = "power_term_p2_eur_kw_day"
CONF_ELECTRICITY_TAX_PCT = "electricity_tax_pct"
CONF_VAT_PCT = "vat_pct"
CONF_BILLING_DAY = "billing_day"

# Defaults
DEFAULT_SURPLUS_PRICE = 0.06          # €/kWh, taxes excluded
DEFAULT_BALANCE_EXPIRY_MONTHS = 0     # 0 = never expires
DEFAULT_ENERGY_PRICE_P1 = 0.196       # €/kWh, punta
DEFAULT_ENERGY_PRICE_P2 = 0.169       # €/kWh, llano
DEFAULT_ENERGY_PRICE_P3 = 0.089       # €/kWh, valle
DEFAULT_PERIOD_SENSOR = "sensor.esios_pvpc"
DEFAULT_CONTRACTED_POWER_P1_KW = 3.45  # kW, punta
DEFAULT_CONTRACTED_POWER_P2_KW = 3.45  # kW, valle
DEFAULT_POWER_TERM_P1_EUR_KW_DAY = 0.10  # €/kW·día, punta
DEFAULT_POWER_TERM_P2_EUR_KW_DAY = 0.02  # €/kW·día, valle
DEFAULT_ELECTRICITY_TAX_PCT = 5.11269632  # impuesto eléctrico
DEFAULT_BILLING_DAY = 1

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN  # one store per config entry, suffixed with entry_id
