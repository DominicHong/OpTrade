# P&L Calculation Algorithm

This document defines the profit-and-loss (P&L) calculation for spot, swap, and
option trades over a user-specified interval `[start_date, valuation_date]`
(hereafter `val_date`).

## Core principle

P&L over `[start_date, val_date]` measures the **change in mark-to-market value**
of each position over the interval:

```
interval_pnl = value(val_date) - value(start_date)
```

A trade is included whenever its position exists at `val_date`, i.e. its
`trade_date` (spot / option) or `near_value_date` (swap) is `<= val_date` —
**regardless of whether it precedes `start_date`**. When `trade_date < start_date`,
the P&L formula is adjusted so only the `[start_date, val_date]` portion is counted.

## Trade inclusion filter

| Trade type | Reference date   | Inclusion condition          |
| ---------- | ---------------- | ---------------------------- |
| Spot       | `trade_date`     | `trade_date <= val_date`     |
| Option     | `trade_date`     | `trade_date <= val_date`     |
| Swap       | `near_value_date`| `near_value_date <= val_date`|

> The lower bound `start_date` does **not** filter trades in or out. It only
> adjusts the P&L formula for trades whose position pre-dates the interval.
>
> Note: the swap reference date is `near_value_date` (the near-leg value date),
> not `trade_date`. A swap whose near leg has not yet been reached has zero P&L
> (`未起息`), so it is excluded.

---

## 1. Spot P&L

### Notation

| Symbol                | Meaning                                                              |
| --------------------- | -------------------------------------------------------------------- |
| `deal_price`          | Dealt spot rate at `trade_date`.                                     |
| `market_rate(t)`      | Market spot rate at date `t` (FX-implied curve or exchange-rate svc).|
| `notional`            | `ccy1_amount`, **signed** (positive = long/buy, negative = short/sell). |
| `adjusted_deal_price` | Cost basis used in the P&L formula.                                  |

### Adjusted deal price

| Condition                                                        | `adjusted_deal_price`           |
| ---------------------------------------------------------------- | ------------------------------- |
| Derivative spot (option exercise) **and** `expiry_date >= start_date` | `market_rate(expiry_date)` |
| `trade_date < start_date` (position pre-dates the interval)      | `market_rate(start_date)`       |
| Otherwise (normal spot, `trade_date >= start_date`)              | `deal_price`                    |

> For derivative spots created by option exercise: if the exercise happened
> **during or after** the interval (`expiry_date >= start_date`), the expiry
> spot rate is the correct basis (the position was created at that rate). If the
> exercise happened **before** the interval (`expiry_date < start_date`), the
> `market_rate(start_date)` rule applies — the position's value at `start_date`
> is the market rate on that day, not the historical exercise rate.

### Formula

```
pnl = (market_rate(val_date) - adjusted_deal_price) * notional
```

When `trade_date < start_date`, this becomes:

```
pnl = (market_rate(val_date) - market_rate(start_date)) * notional
```

### CNY conversion

```
pnl_cny = pnl * fx_rate(ccy2 -> CNY, val_date)
```

---

## 2. Swap P&L

### Notation

| Symbol       | Meaning                                          |
| ------------ | ------------------------------------------------ |
| `near_price` | Near-leg deal price.                             |
| `far_price`  | Far-leg deal price.                              |
| `near_vd`    | Near-leg value date (`near_value_date`).         |
| `far_vd`     | Far-leg value date (`far_value_date`).           |
| `notional`   | `abs(near_ccy1_amount)` (unsigned).              |
| `total_days` | `(far_vd - near_vd).days`.                       |

### Full (maturity) P&L

```
Buy/Sell  (buy ccy1 near, sell ccy1 far):  full_pnl = (far_price - near_price) * notional
Sell/Buy  (sell ccy1 near, buy ccy1 far):  full_pnl = (near_price - far_price) * notional
```

### Accrual

The swap P&L accrues **linearly** over `[near_vd, far_vd]`. The recognised P&L
at `val_date` is the portion of `full_pnl` corresponding to the overlap between
the P&L interval `[start_date, val_date]` and the accrual window `[near_vd, far_vd]`:

```
accrual_start = max(start_date, near_vd)
accrual_end   = min(val_date,   far_vd)
accrued_days  = max(0, (accrual_end - accrual_start).days)

if total_days > 0:
    pnl = full_pnl * accrued_days / total_days
else:
    pnl = full_pnl          # degenerate same-day legs
```

Clamp `pnl` to `[0, full_pnl]` when `full_pnl >= 0` (or `[full_pnl, 0]` when
`full_pnl < 0`) to guard against floating-point drift.

### Status

| Condition                      | Status         |
| ------------------------------ | -------------- |
| `val_date < near_vd`           | 未起息 (not yet effective) |
| `near_vd <= val_date < far_vd` | 存续 (active)             |
| `val_date >= far_vd`           | 到期 (matured)            |

### Special case: `near_vd < start_date`

When the near value date precedes `start_date`, the overlap formula automatically
sets `accrual_start = start_date`, so only the `[start_date, min(val_date, far_vd)]`
portion is counted. This is equivalent to:

```
pnl = full_pnl * (val_date - start_date) / (far_vd - near_vd)
```

**with an additional cap at `far_vd`**: if the swap matures before `val_date`
(`far_vd < val_date`), the numerator uses `(far_vd - start_date)` instead of
`(val_date - start_date)` so the P&L does not over-accrue past maturity.

### Return rate (annualised)

```
Buy/Sell:  return_rate = (far_price - near_price) / near_price * 365 / total_days * 100
Sell/Buy:  return_rate = (near_price - far_price) / near_price * 365 / total_days * 100
```

### CNY conversion

```
pnl_cny = pnl * fx_rate(ccy2 -> CNY, val_date)
```

---

## 3. Option P&L

### Notation

| Symbol     | Meaning                                                                  |
| ---------- | ------------------------------------------------------------------------ |
| `NPV(t)`   | QuantLib theoretical value per unit of `notional1` at date `t`, **signed by direction** (positive for long, negative for short). |
| `premium`  | Option premium per unit (in `ccy2`), paid/received at `trade_date`.     |
| `notional` | `notional1`.                                                             |

### Value function

The total mark-to-market value of an option position at date `t`:

| Condition                                    | `value(t)`                          |
| -------------------------------------------- | ----------------------------------- |
| `t < expiry_date`                            | `NPV(t) * notional`                 |
| `t >= expiry_date` **and** exercised         | `exercise_pnl` (fixed cash flow)    |
| `t >= expiry_date` **and** not exercised     | `0`                                 |

where `exercise_pnl` is the intrinsic value realised at expiry:

```
CALL:  exercise_pnl = (market_rate(expiry_date) - strike) * notional
PUT:   exercise_pnl = (strike - market_rate(expiry_date)) * notional
Short: exercise_pnl = -exercise_pnl
```

### Interval P&L

```
option_pnl = value(val_date) - value(start_date)
```

This decomposes into three lifecycle cases:

#### Case A: `trade_date < start_date` (option pre-dates the interval)

The premium was paid/received at `trade_date` (before the interval). It is
**not excluded** — it **cancels** when the interval P&L is computed as
(total P&L) minus (pre-interval P&L):

```
total P&L (trade → val)         = (NPV(val)   - premium) × notional
pre-interval P&L (trade → start)= (NPV(start) - premium) × notional
────────────────────────────────────────────────────────────────────
interval P&L (start → val)      = (NPV(val)   - NPV(start)) × notional
```

The premium appears in both the total and pre-interval P&L, so it cancels
on subtraction. Equivalently, `NPV(start_date)` **replaces** `premium` as the
cost basis — just as `market_rate(start_date)` replaces `deal_price` in the
spot algorithm.

| Sub-case                                              | `value(val_date)`          | `value(start_date)`        | Interval P&L                                              |
| ----------------------------------------------------- | -------------------------- | -------------------------- | --------------------------------------------------------- |
| `val_date < expiry` (alive at `val_date`)             | `NPV(val) * notional`      | `NPV(start) * notional`    | `(NPV(val) - NPV(start)) * notional`                     |
| `start_date < expiry <= val_date`, exercised          | `exercise_pnl`             | `NPV(start) * notional`    | `exercise_pnl - NPV(start) * notional`                   |
| `start_date < expiry <= val_date`, not exercised      | `0`                        | `NPV(start) * notional`    | `-NPV(start) * notional`                                 |
| `expiry <= start_date` (expired before interval)      | `exercise_pnl` or `0`      | `exercise_pnl` or `0`      | `0`                                                       |

> **Key insight (last row):** if the option expired before `start_date`, both
> `value(val_date)` and `value(start_date)` contain the same `exercise_pnl`, so
> they cancel and the option's interval P&L = 0. The resulting spot position
> (if exercised) carries the P&L via the **spot algorithm** with `start_date`
> adjustment (see section 1).

#### Case B: `start_date <= trade_date <= val_date` (option traded during the interval)

The original algorithm is **unchanged**:

```
Buy:  premium_pnl = (NPV(val_date) - premium) * notional
Sell: premium_pnl = (premium + NPV(val_date)) * notional      # NPV is negative for short
```

plus `exercise_pnl` if the option has expired and been exercised.

**Justification:** At `trade_date`, `NPV(trade_date) ≈ premium` (by no-arbitrage
pricing), so the net P&L at inception is ≈ 0 — the premium cancels the NPV.
Since the interval `[start_date, val_date]` contains the entire trade life, the
interval P&L equals the total P&L:

```
value(val_date) - value(trade_date) = NPV(val) * notional - NPV(trade) * notional
                                    ≈ NPV(val) * notional - premium * notional
```

which matches the original formula. The premium appears here because the trade
was initiated **within** the interval — the premium payment is part of the
interval's cash flows.

> Note: it is the **net P&L** that is 0 at `trade_date` (because `NPV ≈ premium`),
> not the NPV itself. The NPV at `trade_date` is approximately equal to the
> premium, which is generally non-zero.

### Risk metrics (Greeks & NPV)

Risk metrics always reflect the state at `val_date` and are **not** affected by
`start_date`:

- `detail.npv`   = `NPV(val_date)` — absolute mark-to-market value (for risk reporting)
- `detail.delta` = Delta at `val_date`
- `detail.gamma` = Gamma at `val_date`

The NPV used in the **P&L** calculation is the *difference*
`(NPV(val) - NPV(start))`; the NPV in **risk metrics** is the *absolute*
`NPV(val)`. These are two different uses of the same QuantLib computation.

### CNY conversion

```
npv_cny          = NPV(val_date) * notional * fx_rate(ccy2 -> CNY, val_date)
premium_pnl_cny  = premium_pnl * fx_rate(ccy2 -> CNY, val_date)
exercise_pnl_cny = exercise_pnl * fx_rate(ccy2 -> CNY, val_date)
total_pnl_cny    = total_pnl  * fx_rate(ccy2 -> CNY, val_date)
```

---

## 4. Dashboard `start_date` default

The dashboard auto-fills `start_date` with the **earliest `trade_date`** across
all option, spot, and swap trades in all portfolios:

```
start_date_default = min(
    MIN(option_trades.trade_date),
    MIN(spot_trades.trade_date),
    MIN(swap_trades.trade_date),
)
```

(Implemented in `PortfolioService._find_earliest_trade_date`; exposed via
`GET /api/v1/dashboard/defaults` as `earliest_trade_date`.)

When the user does not override `start_date`, the interval spans from the first
trade ever to `val_date`, so the `trade_date < start_date` adjustment never
triggers and all trades use their original formulas. The portfolio-analysis
page applies the same logic but scoped to the **selected** portfolios only.
