# 0xLongitude

**Does knowing *where* crypto capital comes from help predict whether a Bitcoin move will hold?**

0xLongitude is a pre-registered quantitative research study. It tested whether regional capital flows (US, Europe, Korea/Japan, Binance, offshore exchanges), regional price premiums and derivatives positioning can tell a sustainable BTC move from one that is about to reverse.

**Short answer: no.** None of the signals tested adds information beyond a simple base rate. The study documents why, and publishes every negative result, with the code to reproduce it.

> Research notes in `docs/` are written in Spanish. This README summarises them in English.

---

## Key findings

| # | Finding | Evidence |
|---|---|---|
| 1 | **The "Coinbase premium" is mostly the price of USDT.** Measured the usual way (Coinbase BTC-USD vs Binance BTC-USDT), it moves 99.5 % in line with USDT/USD (daily correlation 0.995; 0.968 hourly). Once Binance is converted to real dollars, the premium is a few basis points of microstructure noise. Its biggest spikes were stablecoin crises (LUNA, FTX, USDC/SVB), not US demand. | `docs/02_HALLAZGOS.md` H-01 |
| 2 | **The kimchi premium is a real regional signal, but it does not predict BTC returns.** Mean +1.89 %, peak +10.99 % (19 Mar 2024). 12 tests (level, 1-day change, 3-day change, 30-day z-score × 1–3 day horizons): none significant (min block-bootstrap p = 0.098). | H-02, H-03 |
| 3 | **A global model does not beat the base rate.** Price, volatility, spot taker imbalance, funding, open interest and premiums: no improvement in log loss over a constant model, out of sample. | H-04 |
| 4 | **Spot/derivatives divergence does not predict reversals.** Moves without spot support but with rising leverage: reversal 28.3 % vs 25.6 % (diff. +2.7 pp, 95 % CI −9.9 to +14.8). | H-05 |
| 5 | **Regional on-chain flows add no information.** Net flows of stablecoins and ETH/WBTC by region (Dune, Ethereum) on top of the global model: no improvement for continuation, reversal or fragility. | H-08 |
| 6 | **"Asia" barely exists in on-chain stablecoin flows on Ethereum.** Korean and Japanese exchanges received USD 0.44 bn of external USDT/USDC deposits on Ethereum between Nov 2021 and Dec 2024, vs USD 887 bn for US exchanges. On-chain "regional" narratives about Asia rest on very thin data. | H-08 |

### Headline result (walk-forward 2023–2024, 360 out-of-sample events)

Improvement in log loss from adding the four pre-registered regional variables to the global model (positive = regional helps):

| Target | Improvement | 95 % CI (block bootstrap) | Quarters improved |
|---|---|---|---|
| A · Continuation | −0.0024 | [−0.0110, +0.0061] | 3 / 8 |
| B · Reversal | −0.0001 | [−0.0054, +0.0049] | 3 / 8 |
| C · Fragility | −0.0042 | [−0.0200, +0.0067] | 5 / 8 |

Robust to block sizes of 5–30 days and to using the previous day's flows. Under the pre-registered rule the hypothesis cannot succeed, so **the locked 2025–2026 test set was never opened**.

---

## Method

The study was designed so it could fail cheaply and could not be tuned after the fact.

- **Pre-registration before data.** Hypothesis, targets, variables, splits and kill criterion were fixed before any on-chain flow was downloaded (`docs/05_PREREGISTRO_H1.md`). Every later change is logged and classified (clarification / sensitivity / new hypothesis / pre-data design change) in `docs/06_AUDITORIA_METODOLOGICA_H1.md`.
  SHA-256 of the frozen pre-registration: `26315767b52423c18eefa928bb91d1e3323d872042604d066f20b5584080905e`.
- **Events and targets.** A "move" is a day with |return| > 0.5σ (σ = previous 30 days). Each move is labelled with volatility-scaled triple barriers over the next 72 hours (hourly highs and lows): **continuation**, **reversal** or **neutral**, plus **fragility** (max adverse excursion > 1.5σ√3). 519 events in 2022–2024.
- **Baselines.** A constant model (base rate) and a global model (price, volatility, Binance spot taker imbalance, funding, open-interest change, futures taker ratio, Coinbase and kimchi premiums).
- **Validation.** Quarterly walk-forward (2023-Q1 to 2024-Q4) with a 3-day embargo, L2 logistic regression with regularisation chosen inside each fold, block-bootstrap confidence intervals. Test period 2025-01 to 2026-06 locked in code.
- **Point-in-time data.** FX rates used only after publication, volatility from past days only, USDT/USD gaps not interpolated beyond 2 hours.
- **Power checks.** Synthetic tests plant a regional signal of ~1 standard deviation and confirm the pipeline detects it in 8/8 quarters, and that pure noise produces no false positive (`tests/test_sinteticos.py`, 7/7 passing).
- **Flow cleaning.** Exchange-internal moves, ETH staking deposits and transfers to other labelled exchanges are separated from external (client) flows. Coinbase Prime (institutional custody, incl. ETFs) is kept out of the US retail bucket.

### Regions

An exchange is assigned to a region by the **fiat currency its users deposit**, not its legal seat:
US (Coinbase, Kraken, Gemini, Robinhood, Binance US) · EU (Bitstamp, Bitvavo, Bitpanda) · ASIA (Upbit, Bithumb, bitFlyer, Coincheck) · BINANCE · OFFSHORE (OKX, Bybit, Bitget, HTX, KuCoin, Bitfinex). Offshore exchanges are **not** counted as Asia: their user base cannot be proven from chain data.

---

## Data

| Source | Data | Period |
|---|---|---|
| Coinbase, Binance, Upbit public APIs | Hourly BTC candles, USDT/USD, taker volume | 2022–2026 (42,030 hours) |
| ECB (via Frankfurter) | USD/KRW, USD/JPY | 2022–2026 |
| Binance futures, data.binance.vision | Funding, open interest, long/short and taker ratios | 2022–2026 |
| DefiLlama | USDT and USDC supply | 2022–2026 |
| Dune Analytics (`cex.addresses`, `cex.flows`) | Daily exchange flows by region, Ethereum | 2021-11 to 2024-12 |

Raw and processed data are not included in the repository: they are regenerated by the scripts. Dune data requires your own Dune account and API key.

---

## Reproduce

```bash
pip install -r requirements.txt          # requests, pandas, numpy

python src/descargar_primas.py           # prices and regional premiums
python src/descargar_contexto.py         # funding, open interest, stablecoin supply
python src/etiquetas_eventos.py          # events and barrier labels
python src/modelo_h1.py                  # global baseline (walk-forward)

# On-chain flows (needs a Dune API key; asked on first run and stored in .env)
#   run queries/01L_flujos_h1_desarrollo.sql in Dune, then:
python src/descargar_dune.py <query_id> data/raw/dune/01_flujos_diarios_region.csv
python src/flujos_dune.py                # regional variables
python src/modelo_h1.py                  # H1: global vs global + regional
python src/modelo_h1.py --retardo-flujos 1   # sensitivity: previous-day flows

python src/modelo_h2.py                  # H2: spot/derivatives divergence
python tests/test_sinteticos.py          # synthetic power and false-positive tests
```

The logistic regression is implemented in plain NumPy (`src/logistica_np.py`, validated against scikit-learn to < 1e-6).

---

## Repository map

```
docs/      research notes (Spanish): plan, entity mapping, findings, pre-registrations, audit log
queries/   Dune SQL
src/       data download, labelling, models
tests/     synthetic power / false-positive tests
results/   text outputs of every run
```

## Limitations

- Only Ethereum flows; Bitcoin-native and Tron exchange labels in Dune are too sparse for US and Asian exchanges.
- Exchange labels in Dune are today's labels applied to the past; some look-ahead cannot be ruled out.
- Cross-exchange transfers through unlabelled deposit addresses are only approximated.
- 86.5 % of events overlap within 72 hours: the effective sample is smaller than 519.
- A null result means no *useful-sized* effect was found with this design, not that no effect exists.

## What this is not

Not investment advice and not a trading signal. A negative result, documented so that others do not have to repeat it.

---

Author: **Ivan Alonso**
