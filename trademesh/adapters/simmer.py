"""
SimmerAdapter — Polymarket prediction markets via Simmer SDK
"""
from typing import List
from .base import BaseAdapter
from ..models import TradeSignal, TradeResult, Position


class SimmerAdapter(BaseAdapter):
    name = "simmer"
    supports = ["prediction", "crypto_direction", "macro_direction"]

    def __init__(self, api_key: str, live: bool = True):
        self.api_key = api_key
        self.live = live
        self._client = None

    @property
    def client(self):
        if not self._client:
            from simmer_sdk import SimmerClient
            self._client = SimmerClient(api_key=self.api_key, live=self.live)
        return self._client

    # Tickers we can bridge to Polymarket prediction markets
    CRYPTO_BRIDGE = {
        "BTC": ["bitcoin", "btc"],
        "ETH": ["ethereum", "eth"],
        "SOL": ["solana", "sol"],
        "IBIT": ["bitcoin", "btc"],
        "ETHA": ["ethereum", "eth"],
        "BTCO": ["bitcoin", "btc"],
        "QETH": ["ethereum", "eth"],
        "COIN": ["bitcoin", "btc", "crypto"],
    }

    def can_trade(self, signal: TradeSignal) -> bool:
        """Can trade if ticker maps to a crypto prediction market"""
        ticker = signal.ticker.upper()
        # Direct market_id trade
        if signal.market_id:
            return True
        # Bridge trade
        return ticker in self.CRYPTO_BRIDGE

    def execute(self, signal: TradeSignal) -> TradeResult:
        try:
            # Direct market trade
            if signal.market_id:
                return self._execute_direct(signal)
            # Bridge: find best matching market
            return self._execute_bridge(signal)
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def _execute_direct(self, signal: TradeSignal) -> TradeResult:
        """Execute directly on a known market_id"""
        side = signal.side or ("yes" if signal.direction == "bullish" else "no")
        try:
            result = self.client.trade(
                market_id=signal.market_id,
                side=side,
                amount=signal.amount,
                action="buy"
            )
            return TradeResult(
                success=True,
                venue=self.name,
                order_id=getattr(result, "order_id", None),
                ticker=signal.ticker,
                side=side,
                amount=signal.amount,
                status=getattr(result, "order_status", "submitted"),
                market=signal.question,
                raw=vars(result) if hasattr(result, "__dict__") else None
            )
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def _execute_bridge(self, signal: TradeSignal) -> TradeResult:
        """Find best Polymarket market matching signal direction and execute"""
        ticker = signal.ticker.upper()
        keywords = self.CRYPTO_BRIDGE.get(ticker, [ticker.lower()])

        markets = self.client.get_markets(status="active", limit=50)

        # Find matching markets
        candidates = []
        for m in markets:
            q = (m.question or "").lower()
            prob = getattr(m, "current_probability", None)
            if prob is None:
                continue
            if not any(k in q for k in keywords):
                continue

            # Score by edge
            if signal.direction == "bearish" and prob < 0.48:
                edge = 0.50 - prob
                candidates.append((edge, m, "no"))
            elif signal.direction == "bullish" and prob > 0.52:
                edge = prob - 0.50
                candidates.append((edge, m, "yes"))

        if not candidates:
            return TradeResult(
                success=False,
                venue=self.name,
                ticker=signal.ticker,
                error=f"No {signal.direction} markets found for {ticker}"
            )

        # Pick best edge
        candidates.sort(key=lambda x: x[0], reverse=True)
        edge, best_market, side = candidates[0]

        try:
            result = self.client.trade(
                market_id=best_market.id,
                side=side,
                amount=signal.amount,
                action="buy"
            )
            return TradeResult(
                success=True,
                venue=self.name,
                order_id=getattr(result, "order_id", None),
                ticker=signal.ticker,
                side=side,
                amount=signal.amount,
                status=getattr(result, "order_status", "submitted"),
                market=best_market.question,
                raw=vars(result) if hasattr(result, "__dict__") else None
            )
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def positions(self) -> List[Position]:
        try:
            raw = self.client.get_positions()
            positions = []
            for p in raw:
                cost = p.cost_basis or 0
                val = p.current_value or 0
                pnl = p.pnl or 0
                pnl_pct = ((val - cost) / cost * 100) if cost > 0 else 0
                positions.append(Position(
                    venue=self.name,
                    ticker=getattr(p, "ticker", ""),
                    side="yes" if (p.shares_yes or 0) > 0 else "no",
                    cost_basis=cost,
                    current_value=val,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    status=getattr(p, "status", "open"),
                    question=getattr(p, "question", None),
                    market_id=getattr(p, "market_id", None),
                    raw=vars(p) if hasattr(p, "__dict__") else None
                ))
            return positions
        except Exception:
            return []

    def balance(self) -> float:
        try:
            return float(self.client.get_balance())
        except Exception:
            return 0.0
