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

---

# Portfolio Greeks

## Trade-Level Greeks (Per-Unit)

Computed by QuantLib (`AnalyticEuropeanEngine`) for **1 unit of `notional1`**.

| Greek | Meaning | Unit |
|---|---|---|
| **Delta** | $\Delta = \frac{\partial V}{\partial S}$. Change in option value for a 1-unit change in spot. | `ccy2` / `1 ccy1` |
| **Gamma** | $\Gamma = \frac{\partial^2 V}{\partial S^2}$. Change in Delta for a 1-unit change in spot. | `ccy2` / `(1 ccy1)^2` |
| **NPV** | Theoretical option premium (present value). Positive for long, negative for short. | `ccy2` / `1 ccy1` |

> Example: NPV = `0.1` for USD/CNY means each USD of notional is worth `0.1 CNY`.

## Aggregated Greeks (Weighted, in 万)

Portfolio-level totals are **notional-weighted sums**, then scaled to **万** .

```
Weighted Delta = Σ (delta_i × notional1_i)
Weighted Gamma = Σ (gamma_i × notional1_i)
Weighted NPV   = Σ (npv_i   × notional1_i)
```

## Relationship

- **Trade-level** = per-unit sensitivity / price.
- **Aggregated** = trade-level value × `notional1`, summed across the portfolio.

Sign convention: Long = positive, Short = negative (signs are flipped in code for short positions).
