# Adding a New Venue to TradeMesh

TradeMesh is designed to be community-extended. Adding any trading venue = 4 methods.

## Template

```python
from trademesh.adapters.base import BaseAdapter
from trademesh.models import TradeSignal, TradeResult, Position
from typing import List

class MyVenueAdapter(BaseAdapter):
    name = "myvenue"
    supports = ["stocks", "options"]  # what asset types this venue handles

    def __init__(self, api_key: str):
        self.api_key = api_key

    def can_trade(self, signal: TradeSignal) -> bool:
        """Return True if this adapter can handle the signal"""
        return True  # or check signal.ticker, signal.direction, etc.

    def execute(self, signal: TradeSignal) -> TradeResult:
        """Execute the trade. NEVER raise — catch all exceptions."""
        try:
            # your venue's SDK/API here
            result = my_venue_sdk.place_order(...)
            return TradeResult(
                success=True,
                venue=self.name,
                order_id=result.id,
                ticker=signal.ticker,
                side=signal.side,
                amount=signal.amount,
                status="filled"
            )
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def positions(self) -> List[Position]:
        """Return all open positions"""
        raw = my_venue_sdk.get_positions()
        return [
            Position(
                venue=self.name,
                ticker=p.symbol,
                side=p.side,
                cost_basis=p.cost,
                current_value=p.value,
                pnl=p.pnl,
                pnl_pct=p.pnl_pct,
                status="open"
            )
            for p in raw
        ]

    def balance(self) -> float:
        """Return available cash (USD)"""
        return float(my_venue_sdk.get_balance())
```

## Register and use

```python
tm = TradeMesh()
tm.register(MyVenueAdapter(api_key="..."))
tm.trade(ticker="BTC", direction="bullish", amount=50, venue="myvenue")
```

## Submitting to TradeMesh

Open a PR at https://github.com/miracleuniverse/trademesh with:
- `trademesh/adapters/myvenue.py`
- Tests in `tests/test_myvenue.py`
- Entry in `trademesh/adapters/__init__.py`

We review and merge quickly. All MIT licensed.
