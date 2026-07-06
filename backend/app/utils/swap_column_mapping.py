"""
Swap trade column mapping: ComStar Chinese Excel headers → SwapTrade model fields.

The ComStar FX Swap export uses Chinese column headers (67 columns).
This module provides the canonical mapping for the swap import pipeline.
Follows the same pattern as spot_column_mapping.py.
"""

# Mapping from Chinese Excel header to SwapTrade model attribute name
CSV_TO_SWAP_FIELD: dict[str, str] = {
    # Identifiers
    "成交编号": "trade_id",
    "原始交易系统编号": "source_trade_id",
    "复核编号": "review_id",
    # Portfolio
    "投组": "portfolio_name",
    # Trade details
    "货币对": "ccy_pair",
    "交易方向": "direction",
    "交易事件类型": "event_type",
    "掉期类型": "swap_type",
    "价差": "spread",
    "期限": "tenor",
    # Counterparty
    "对手方": "counterparty_name",
    "本方交易员": "our_trader",
    # Spot reference
    "即期起息日": "spot_value_date",
    "即期汇率": "spot_rate",
    # Near leg (近端)
    "近端起息日": "near_value_date",
    "近端期限": "near_tenor",
    "近端掉期点": "near_swap_points",
    "近端成交价": "near_deal_price",
    "近端交易货币": "near_trade_ccy",
    "近端货币1金额": "near_ccy1_amount",
    "近端货币2金额": "near_ccy2_amount",
    "近端交割状态": "near_settlement_status",
    # Far leg (远端)
    "远端起息日": "far_value_date",
    "远端期限": "far_tenor",
    "远端掉期点": "far_swap_points",
    "远端成交价": "far_deal_price",
    "远端交易货币": "far_trade_ccy",
    "远端货币1金额": "far_ccy1_amount",
    "远端货币2金额": "far_ccy2_amount",
    "远端交割状态": "far_settlement_status",
    # Dates
    "交易日": "trade_date",
    "交易时间": "trade_time",
    "自然日": "natural_date",
    # Status & meta
    "备注": "comments",
    "来源": "source",
    "交易场所": "venue",
    "清算机构": "clearing_org",
    "清算方式": "clearing_method",
    "创建时间": "created_timestamp",
}

# Required fields for swap trade import
SWAP_REQUIRED_FIELDS: list[str] = [
    "trade_id",
    "ccy_pair",
    "direction",
    "near_deal_price",
    "far_deal_price",
    "near_value_date",
    "far_value_date",
]

# Chinese headers that strongly identify a swap trade file.
# Used to detect when a user accidentally uploads an option/spot file as swap.
SWAP_SIGNATURE_HEADERS: list[str] = [
    "近端成交价",
    "远端成交价",
    "近端起息日",
    "远端起息日",
    "掉期类型",
]

# Fields that require date parsing (Chinese date formats → date)
SWAP_DATE_FIELDS: set[str] = {
    "trade_date",
    "natural_date",
    "spot_value_date",
    "near_value_date",
    "far_value_date",
}

# Fields that require datetime parsing
SWAP_DATETIME_FIELDS: set[str] = {
    "created_timestamp",
}

# Fields that require float parsing (string with commas → float)
SWAP_FLOAT_FIELDS: set[str] = {
    "spread",
    "spot_rate",
    "near_swap_points",
    "near_deal_price",
    "near_ccy1_amount",
    "near_ccy2_amount",
    "far_swap_points",
    "far_deal_price",
    "far_ccy1_amount",
    "far_ccy2_amount",
}

# No boolean fields for swap trades
SWAP_BOOL_FIELDS: set[str] = set()
