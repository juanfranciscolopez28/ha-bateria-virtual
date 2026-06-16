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
DEFAULT_CONTRACTED_POWER_P1_KW = 3.45  # kW, punta
DEFAULT_CONTRACTED_POWER_P2_KW = 3.45  # kW, valle
DEFAULT_POWER_TERM_P1_EUR_KW_DAY = 0.10  # €/kW·día, punta
DEFAULT_POWER_TERM_P2_EUR_KW_DAY = 0.02  # €/kW·día, valle
DEFAULT_ELECTRICITY_TAX_PCT = 5.11    # impuesto eléctrico
DEFAULT_BILLING_DAY = 1

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN  # one store per config entry, suffixed with entry_id
