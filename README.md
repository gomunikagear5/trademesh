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
tm.trade(ticker="BTC", side="short", amount=100, venue="hyperliquid")
tm.trade(market_id="abc123", side="no", amount=25, venue="simmer")
```

## Supported Venues

| Venue | Type | Status |
|-------|------|--------|
| Simmer (Polymarket) | Prediction markets | ✅ Live |
| Robinhood | Stocks + Options | 🔧 Building |
| Alpaca | Stocks + Options (paper/live) | 🔧 Building |
| Hyperliquid | Crypto perps | 📋 Planned |
| Kalshi | Regulated event contracts | 📋 Planned |
| Coinbase | Crypto spot | 📋 Planned |
| Binance | Crypto spot + futures | 📋 Planned |

## Why TradeMesh?

- **Signal-agnostic** — plug in any signal source (UOA scanner, AI, manual)
- **Venue-agnostic** — your strategy works everywhere
- **Smart routing** — auto-selects best venue based on signal type, liquidity, and odds
- **Unified P&L** — one dashboard across all venues
- **Risk-first** — position limits, stop-loss, and exposure caps enforced globally

## Quick Start

```bash
pip install trademesh
```

```python
from trademesh import TradeMesh
from trademesh.adapters import SimmerAdapter, RobinhoodAdapter

tm = TradeMesh()
tm.register(SimmerAdapter(api_key="your-simmer-key"))
tm.register(RobinhoodAdapter())  # uses stored credentials

# Check what's available
tm.venues()  # ['simmer', 'robinhood']

# Trade
result = tm.trade(ticker="IBIT", direction="bearish", amount=50, venue="auto")
print(result)
# TradeResult(venue='simmer', market='Bitcoin Up or Down', side='no', amount=50, status='filled')
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
    ├── SimmerAdapter      ✅
    ├── RobinhoodAdapter   🔧
    ├── AlpacaAdapter      🔧
    ├── HyperliquidAdapter 📋
    └── KalshiAdapter      📋
```

## Contributing

TradeMesh is designed to be community-extended. Adding a new venue = implementing `BaseAdapter` (4 methods).

See `docs/adding-adapters.md` to add your venue.

## License

MIT — free for everyone.

---

Built by Miracle Universe Inc. 🌍
