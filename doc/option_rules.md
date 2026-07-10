# CFETS FX Option Premium Calculation 
Using `ccy1 / ccy2` as the example currency pair. 
## Premium Rules 
- `premium_type` must be either `Pips` or `%`. 
- `premium_currency` must be either `ccy1` or `ccy2`. 

| `premium_type` | `premium_currency` | Formula                                             |
| -------------- | ------------------ | --------------------------------------------------- |
| `Pips`         | `ccy2`             | `premium_amount = premium_rate * notional1 / 10000` |
| `Pips`         | `ccy1`             | `premium_amount = premium_rate * notional2 / 10000` |
| `%`            | `ccy2`             | `premium_amount = premium_rate * notional2 / 100`   |
| `%`            | `ccy1`             | `premium_amount = premium_rate * notional1 / 100`   |

## Notes 
- `notional1` is the amount of `ccy1`. 
- `notional2` is the amount of `ccy2`. 
- `premium_rate` is expressed in the unit of `premium_type` (pips or percent). 
- `premium_amount` is the absolute premium value in `premium_currency`. 

--- 

# Portfolio Greeks 

## Trade-Level Greeks (Per-Unit) 
Computed by QuantLib (`AnalyticEuropeanEngine`) for **1 unit of `notional1`**. 

| Greek     | Meaning                                                                                       | Unit                  |
| --------- | --------------------------------------------------------------------------------------------- | --------------------- |
| **Delta** | $\Delta = \frac{\partial V}{\partial S}$. Change in option value for a 1-unit change in spot. | `ccy2` / `1 ccy1`     |
| **Gamma** | $\Gamma = \frac{\partial^2 V}{\partial S^2}$. Change in Delta for a 1-unit change in spot.    | `ccy2` / `(1 ccy1)^2` |
| **Theta** | $\Theta = \frac{\partial V}{\partial t}$. Change in option value per day (time decay).        | `ccy2` / `1 ccy1` / `1 day` |
| **Vega**  | $\nu = \frac{\partial V}{\partial \sigma}$. Change in option value for a 1% change in volatility. | `ccy2` / `1 ccy1` / `1% vol` |
| **NPV**   | Theoretical option premium (present value). Positive for long, negative for short.            | `ccy2` / `1 ccy1`     |

> Example: NPV = `0.1` for USD/CNY means each USD of notional is worth `0.1 CNY`. 

## Gamma in QuantLib vs Gamma in Bloomberg 
Gamma in QuantLib is the change of delta for 1-unit change in spot. 
Gamma in Bloomberg is the change of delta for 1% change in spot. 

$$
Gamma_{quantlib} = \frac{Gamma_{bloomberg} \cdot 100}{spot}
$$

## Theta Algorithm 
QuantLib's `AnalyticEuropeanEngine` natively returns theta **per year** 
($\Theta = -\frac{\partial V}{\partial T}$, where $T$ is in years). The system 
converts it to **per day** for display:

1. **Per-year → per-day**: `theta = option.thetaPerDay()`, i.e. $\Theta_{\text{day}} = \Theta_{\text{year}} / 365$ (Actual/365Fixed day-count convention).
2. **Short position sign flip**: for `Sell` (Short), `theta = -theta`, so that a long position's time decay (typically negative) becomes a short position's time gain (positive), consistent with the Long = positive / Short = negative sign convention.
3. **Rounding**: the per-day theta is rounded to 6 decimals at the trade level (`greeks_service.py`).

> Note: QuantLib's theta sign follows the convention $\Theta = -\partial V / \partial T$ 
> (positive theta means value increases as time passes toward expiry). Some 
> platforms use the opposite sign ($\Theta = \partial V / \partial t$ where 
> $t$ increases backward); always check the convention before comparing.

## Vega Algorithm 
QuantLib's `AnalyticEuropeanEngine` natively returns vega **per 1.0 (100%) 
change in volatility** ($\nu = \frac{\partial V}{\partial \sigma}$, where 
$\sigma$ is expressed as a decimal). Since volatilities are quoted and 
managed in percent, the system converts it to **per 1% change**:

1. **Per-1.0 → per-1%**: `vega = option.vega() / 100.0`, i.e. $\nu_{\text{1\%}} = \nu_{\text{1.0}} / 100$. This makes the displayed Vega the value change when implied vol moves by 1 percentage point (e.g. from 15% to 16%).
2. **Short position sign flip**: for `Sell` (Short), `vega = -vega`, consistent with the Long = positive / Short = negative sign convention.
3. **Rounding**: vega is rounded to 6 decimals at the trade level (`greeks_service.py`).

## Aggregated Greeks (Weighted, in 万) 
Portfolio-level totals are **notional-weighted sums**, then scaled to **万**. 
```

Weighted Delta = Σ (delta_i × notional1_i)

Weighted Gamma = Σ (gamma_i × notional1_i)

Weighted Theta = Σ (theta_i × notional1_i)

Weighted Vega  = Σ (vega_i  × notional1_i)

Weighted NPV   = Σ (npv_i   × notional1_i)

```
## Relationship

- **Trade-level** = per-unit sensitivity / price.

- **Aggregated** = trade-level value × `notional1`, summed across the portfolio. 

Sign convention: Long = positive, Short = negative (signs are flipped in code for short positions).