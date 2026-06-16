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
