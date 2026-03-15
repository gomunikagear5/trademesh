"""
AlpacaAdapter — Stocks + Options via Alpaca API
Supports paper trading (safe testing) and live trading.
Get keys at: https://alpaca.markets
"""
from typing import List, Optional
from .base import BaseAdapter
from ..models import TradeSignal, TradeResult, Position


class AlpacaAdapter(BaseAdapter):
    name = "alpaca"
    supports = ["stocks", "options"]

    PAPER_URL = "https://paper-api.alpaca.markets"
    LIVE_URL = "https://api.alpaca.markets"

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        """
        paper=True (default) uses paper trading — safe for testing.
        paper=False uses live account — real money.
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self.base_url = self.PAPER_URL if paper else self.LIVE_URL
        self._client = None

    @property
    def client(self):
        if not self._client:
            try:
                import alpaca_trade_api as tradeapi
                self._client = tradeapi.REST(
                    self.api_key,
                    self.secret_key,
                    self.base_url
                )
            except ImportError:
                raise ImportError("Install alpaca: pip install alpaca-trade-api")
        return self._client

    def can_trade(self, signal: TradeSignal) -> bool:
        crypto_only = {"BTC", "ETH", "SOL", "DOGE"}
        return signal.ticker.upper() not in crypto_only

    def execute(self, signal: TradeSignal) -> TradeResult:
        try:
            ticker = signal.ticker.upper()
            side = "buy" if signal.direction == "bullish" else "sell"

            # Get current price
            latest = self.client.get_latest_trade(ticker)
            price = float(latest.price)
            qty = max(1, int(signal.amount / price))

            order = self.client.submit_order(
                symbol=ticker,
                qty=qty,
                side=side,
                type="market",
                time_in_force="day"
            )

            return TradeResult(
                success=True,
                venue=self.name + ("-paper" if self.paper else "-live"),
                order_id=order.id,
                ticker=ticker,
                side=side,
                amount=price * qty,
                price=price,
                status=order.status,
                raw=vars(order)
            )
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def positions(self) -> List[Position]:
        try:
            raw_positions = self.client.list_positions()
            positions = []
            for p in raw_positions:
                positions.append(Position(
                    venue=self.name,
                    ticker=p.symbol,
                    side="long" if float(p.qty) > 0 else "short",
                    cost_basis=float(p.cost_basis),
                    current_value=float(p.market_value),
                    pnl=float(p.unrealized_pl),
                    pnl_pct=float(p.unrealized_plpc) * 100,
                    status="open"
                ))
            return positions
        except Exception:
            return []

    def balance(self) -> float:
        try:
            account = self.client.get_account()
            return float(account.buying_power)
        except Exception:
            return 0.0
