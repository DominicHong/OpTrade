"""
Column mapping: Chinese CSV header names → Trade model field names.

The COMSTAR FX Options export uses Chinese column headers.
This module provides the canonical mapping for the import pipeline.
"""

# Mapping from Chinese CSV header to Trade model attribute name
CSV_TO_OPTION_TRADE_FIELD: dict[str, str] = {
    # Identifiers
    "成交编号": "trade_id",
    "原始交易系统编号": "source_trade_id",
    "复核编号": "review_id",
    "Leg": "leg",
    # Portfolio & Strategy
    "选择导入": "is_selected",
    "分配状态": "allocation_status",
    "期权类型": "option_type",
    "策略编号": "strategy_id",
    "策略成交编号": "strategy_trade_id",
    "投组": "portfolio_name",
    "交易事件类型": "event_type",
    "交易目的": "trade_purpose",
    "交易性质": "trade_nature",
    # Option Specs
    "货币对": "ccy_pair",
    "货币1金额": "notional1",
    "货币2金额": "notional2",
    "交易货币": "trade_currency",
    "交易方向": "direction",
    "交易类型": "trade_type",
    "执行价": "strike",
    # Dates
    "交易日": "trade_date",
    "交易时间": "trade_time",
    "自然日": "natural_date",
    "期权费支付日": "premium_payment_date",
    "期限": "tenor",
    "行权日": "expiry_date",
    "时区": "timezone",
    "行权截止时间": "expiry_cutoff_time",
    "交割日": "delivery_date",
    "观测起始日": "observation_start_date",
    "观测结束日": "observation_end_date",
    "平均价格计算起始日": "averaging_start_date",
    "平均价格计算结束日": "averaging_end_date",
    # Premium
    "期权费类型": "premium_type",
    "期权费率": "premium_rate",
    "期权费金额": "premium_amount",
    "期权费货币": "premium_currency",
    "成本期权费率": "cost_premium_rate",
    "成本期权费金额": "cost_premium_amount",
    # Market Data
    "即期汇率": "spot_rate",
    "波动率": "volatility",
    "波动率标的": "volatility_reference",
    # Counterparty & Venue
    "操作人": "operator",
    "本方": "our_side",
    "本方交易员": "our_trader",
    "对手方": "counterparty_name",
    "交易场所": "venue",
    "清算机构": "clearing_org",
    "清算方式": "clearing_method",
    "经纪人": "broker",
    "来源": "source",
    # Barrier
    "障碍类型": "barrier_type",
    "障碍方向": "barrier_direction",
    "障碍线": "barrier_level",
    # Asian
    "亚式期权子类型": "asian_sub_type",
    "平均计算方法": "averaging_method",
    "频率": "averaging_frequency",
    "平均价格舍入方式": "averaging_rounding_method",
    "平均价格小数位数": "averaging_decimal_places",
    "参考假日": "reference_holiday",
    # Return
    "回报金额": "return_amount",
    "回报货币": "return_currency",
    # Exercise
    "行权状态": "exercise_status",
    "行权方法": "exercise_method",
    "行权交易员": "exercise_trader",
    "行权时间": "exercise_time",
    "行权衍生交易的成交编号": "exercise_derivative_trade_id",
    "行权衍生交易的交易编号": "exercise_derivative_transaction_id",
    "行权衍生的交易品种": "exercise_derivative_product",
    # Delivery
    "交割类型": "delivery_type",
    "交割货币": "delivery_currency",
    "交割参考汇率": "delivery_reference_rate",
    "交割轧差汇率": "delivery_netting_rate",
    # Status
    "生效状态": "effective_status",
    # Delta Exchange
    "Delta Exchange交易成交编号": "delta_exchange_trade_id",
    "Delta Exchange交易编号": "delta_exchange_transaction_id",
    "Delta Exchange交易产品类型": "delta_exchange_product_type",
    # Flags
    "是否关联方交易": "is_related_party_trade",
    "是否到期自动行权": "is_auto_exercise",
    "是否有原始交易": "has_original_trade",
    # Comments
    "备注": "comments",
    "事件备注": "event_comments",
    "操作事件": "operation_event",
    # Client
    "客户利润": "client_profit",
    # Timestamp
    "创建时间": "created_timestamp",
}

# Fields that are required (must have a value or the row is flagged as error)
REQUIRED_FIELDS: list[str] = [
    "trade_id",
    "option_type",
    "trade_type",
    "direction",
    "ccy_pair",
    "expiry_date",
    "notional1",
    "strike",
]

# Fields that require date parsing
DATE_FIELDS: set[str] = {
    "trade_date",
    "natural_date",
    "expiry_date",
    "delivery_date",
    "premium_payment_date",
    "observation_start_date",
    "observation_end_date",
    "averaging_start_date",
    "averaging_end_date",
}

# Fields that require datetime parsing
DATETIME_FIELDS: set[str] = {
    "created_timestamp",
}

# Fields that require float parsing
FLOAT_FIELDS: set[str] = {
    "strike",
    "notional1",
    "notional2",
    "spot_rate",
    "volatility",
    "premium_rate",
    "premium_amount",
    "cost_premium_rate",
    "cost_premium_amount",
    "barrier_level",
    "return_amount",
    "delivery_reference_rate",
    "delivery_netting_rate",
    "client_profit",
}

# Fields that require boolean parsing
BOOL_FIELDS: set[str] = {
    "is_selected",
    "is_related_party_trade",
    "is_auto_exercise",
    "has_original_trade",
}
