# CFETS FX Option Premium Calculation

Using `ccy1 / ccy2` as the example currency pair.

## Premium Rules

- `premium_type` must be either `Pips` or `%`.
- `premium_currency` must be either `ccy1` or `ccy2`.

| `premium_type` | `premium_currency` | Formula |
|---|---|---|
| `Pips` | `ccy2` | `premium_amount = premium_rate * notional1 / 10000` |
| `Pips` | `ccy1` | `premium_amount = premium_rate * notional2 / 10000` |
| `%` | `ccy2` | `premium_amount = premium_rate * notional2 / 100` |
| `%` | `ccy1` | `premium_amount = premium_rate * notional1 / 100` |

## Notes

- `notional1` is the amount of `ccy1`.
- `notional2` is the amount of `ccy2`.
- `premium_rate` is expressed in the unit of `premium_type` (pips or percent).
- `premium_amount` is the absolute premium value in `premium_currency`.
