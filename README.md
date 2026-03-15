# TradeMesh 🔌

**One interface. Any trading venue.**

TradeMesh is a universal execution layer for algorithmic traders. Connect to any trading platform through a single, consistent API — then route signals automatically to the best venue.

```python
from trademesh import TradeMesh

tm = TradeMesh()

# Auto-route to best venue
tm.trade(ticker="IBIT", direction="bearish", amount=50)

# Or target specific venues
tm.trade(ticker="NVDA", side="put", strike=800, exp="2026-04-17", venue="robinhood")
tm.trade(ticker="BTC", direction="bullish", amount=100, venue="coinbase")
tm.trade(ticker="FED", direction="bearish", amount=25, venue="kalshi")
tm.trade(market_id="abc123", side="no", amount=25, venue="simmer")
```

## ⚡ Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/gomunikagear5/trademesh/main/install.sh | bash
```

Or with pip:

```bash
pip install git+https://github.com/gomunikagear5/trademesh.git
```

## Supported Venues

| Venue | Type | Status |
|-------|------|--------|
| Robinhood | Stocks + Options | ✅ Live |
| Kalshi | Regulated event contracts | ✅ Live |
| Coinbase | Crypto spot | ✅ Live |
| Simmer (Polymarket) | Prediction markets | ✅ Live |
| Alpaca | Stocks + Options (paper/live) | ✅ Live |
| Hyperliquid | Crypto perps | 📋 Planned |
| Interactive Brokers | Stocks/Options/Futures | 📋 Planned |
| dYdX | Decentralized crypto perps | 📋 Planned |
| Binance | Crypto spot + futures | 📋 Planned |

## Why TradeMesh?

- **Signal-agnostic** — plug in any signal source (UOA scanner, AI, manual)
- **Venue-agnostic** — your strategy works everywhere
- **Smart routing** — auto-selects best venue based on signal type, liquidity, and odds
- **Unified P&L** — one dashboard across all venues
- **Risk-first** — position limits, stop-loss, and exposure caps enforced globally

## Quick Start

```python
from trademesh import TradeMesh
from trademesh.adapters import RobinhoodAdapter, KalshiAdapter, CoinbaseAdapter

tm = TradeMesh()
tm.register(RobinhoodAdapter())   # uses ROBINHOOD_USERNAME / ROBINHOOD_PASSWORD
tm.register(KalshiAdapter())      # uses KALSHI_API_KEY / KALSHI_PRIVATE_KEY_PATH
tm.register(CoinbaseAdapter())    # uses COINBASE_API_KEY_NAME / COINBASE_PRIVATE_KEY

# Check what's available
tm.venues()  # ['robinhood', 'kalshi', 'coinbase']

# Trade — TradeMesh auto-routes to the best adapter
tm.trade(ticker="TSLA", direction="bearish", amount=200)  # → Robinhood
tm.trade(ticker="BTC",  direction="bullish", amount=100)  # → Coinbase
tm.trade(ticker="FED",  direction="bearish", amount=25)   # → Kalshi
```

## Adapter Setup

### 🟢 Robinhood (Stocks + Options)

```bash
export ROBINHOOD_USERNAME="your@email.com"
export ROBINHOOD_PASSWORD="yourpassword"
```

```python
from trademesh.adapters import RobinhoodAdapter
adapter = RobinhoodAdapter()
# Or: RobinhoodAdapter(username="...", password="...")
```

### 🔵 Kalshi (Regulated Event Markets)

```bash
export KALSHI_API_KEY="your-api-key-id"
export KALSHI_PRIVATE_KEY_PATH="/path/to/private.pem"
# Or: export KALSHI_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
```

```python
from trademesh.adapters import KalshiAdapter
adapter = KalshiAdapter()
# Use demo=True for Kalshi's sandbox environment
```

### 🟠 Coinbase (Crypto Spot)

```bash
export COINBASE_API_KEY_NAME="organizations/{org_id}/apiKeys/{key_id}"
export COINBASE_PRIVATE_KEY="-----BEGIN EC PRIVATE KEY-----\n..."
```

```python
from trademesh.adapters import CoinbaseAdapter
adapter = CoinbaseAdapter()
# Supports BTC, ETH, SOL, XRP, DOGE, ADA, and more
```

### 🟣 Simmer / Polymarket

```python
from trademesh.adapters import SimmerAdapter
adapter = SimmerAdapter(api_key="your-simmer-key")
```

## Architecture

```
TradeMesh
├── Core Engine
│   ├── Signal Router      — picks best venue per signal type
│   ├── Risk Manager       — global position limits + stop-loss
│   ├── Position Tracker   — unified P&L across all venues
│   └── Performance Logger — feeds backtest + optimization
└── Adapters (pluggable)
    ├── BaseAdapter        — interface all venues implement
    ├── RobinhoodAdapter   ✅
    ├── KalshiAdapter      ✅
    ├── CoinbaseAdapter    ✅
    ├── SimmerAdapter      ✅
    ├── AlpacaAdapter      ✅
    └── HyperliquidAdapter 📋
```

## Contributing

TradeMesh is designed to be community-extended. Adding a new venue = implementing `BaseAdapter` (4 methods).

See `docs/adding-adapters.md` to add your venue.

## License

MIT — free for everyone.

---

Built by Miracle Universe Inc. 🌍
