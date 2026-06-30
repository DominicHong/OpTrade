"""
Spot trade column mapping: ComStar Chinese Excel headers → SpotTrade model fields.

The ComStar spot FX export uses Chinese column headers (48 columns).
This module provides the canonical mapping for the spot import pipeline.
Follows the same pattern as column_mapping.py.
"""

# Mapping from Chinese Excel header to SpotTrade model attribute name
CSV_TO_SPOT_FIELD: dict[str, str] = {
    # Identifiers
    "成交编号": "trade_id",

    # Portfolio
    "投组": "portfolio_name",

    # Trade details
    "货币对": "ccy_pair",
    "交易方向": "direction",
    "买卖方式": "direction",
    "交易事件类型": "event_type",

    # Pricing
    "成交价": "deal_price",
    "客户价": "deal_price",
    "成交价/客户价": "deal_price",

    # Amounts
    "货币1金额": "ccy1_amount",
    "货币2金额": "ccy2_amount",

    # Counterparty
    "对手方": "counterparty_name",

    # Dates
    "交易日": "trade_date",
    "起息日": "settlement_date",
    "创建时间": "created_timestamp",

    # Status & meta
    "来源": "source",
    "交易场所": "venue",
}

# Required fields for spot trade import
SPOT_REQUIRED_FIELDS: list[str] = [
    "trade_id",
    "ccy_pair",
]

# Chinese headers that strongly identify a spot trade file.
# Used to detect when a user accidentally uploads an options file as spot.
SPOT_SIGNATURE_HEADERS: list[str] = [
    "成交价",
    "客户价",
    "成交价/客户价",
    "起息日",
]

# Fields that require date parsing (Chinese date formats → date)
SPOT_DATE_FIELDS: set[str] = {
    "trade_date",
    "settlement_date",
}

# Fields that require datetime parsing
SPOT_DATETIME_FIELDS: set[str] = {
    "created_timestamp",
}

# Fields that require float parsing (string with commas → float)
SPOT_FLOAT_FIELDS: set[str] = {
    "deal_price",
    "ccy1_amount",
    "ccy2_amount",
}

# No boolean fields for spot trades
SPOT_BOOL_FIELDS: set[str] = set()
