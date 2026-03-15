"""
TradeMesh Core — Signal Router + Risk Manager + Position Tracker
"""
import json
import os
from typing import List, Optional, Dict
from datetime import datetime
from .models import TradeSignal, TradeResult, Position
from .adapters.base import BaseAdapter


class RiskManager:
    """Global risk rules enforced across all venues"""

    def __init__(self,
                 max_position_usd: float = 50.0,
                 max_total_exposure_usd: float = 200.0,
                 stop_loss_pct: float = 0.20,
                 min_score: float = 6.0):
        self.max_position_usd = max_position_usd
        self.max_total_exposure_usd = max_total_exposure_usd
        self.stop_loss_pct = stop_loss_pct
        self.min_score = min_score

    def check(self, signal: TradeSignal, current_exposure: float) -> tuple[bool, str]:
        """Returns (approved, reason)"""
        if signal.score < self.min_score:
            return False, f"Signal score {signal.score} below minimum {self.min_score}"
        if signal.amount > self.max_position_usd:
            signal.amount = self.max_position_usd  # cap, don't reject
        if current_exposure + signal.amount > self.max_total_exposure_usd:
            return False, f"Would exceed max exposure ${self.max_total_exposure_usd}"
        return True, "approved"


class TradeMesh:
    """
    Universal execution layer. Register adapters, fire signals.
    """

    # Signal type → preferred venue order
    ROUTING_RULES = {
        "prediction": ["simmer", "kalshi"],
        "crypto_direction": ["simmer", "hyperliquid", "coinbase"],
        "stocks": ["robinhood", "alpaca"],
        "options": ["robinhood", "alpaca"],
        "crypto": ["hyperliquid", "coinbase", "robinhood"],
    }

    # Ticker → signal type mapping
    TICKER_TYPES = {
        "IBIT": "crypto_direction",
        "ETHA": "crypto_direction",
        "BTCO": "crypto_direction",
        "QETH": "crypto_direction",
        "COIN": "crypto_direction",
        "BTC": "crypto",
        "ETH": "crypto",
        "SOL": "crypto",
        "SPY": "options",
        "QQQ": "options",
    }

    def __init__(self,
                 risk: Optional[RiskManager] = None,
                 log_path: str = "trademesh_log.json"):
        self._adapters: Dict[str, BaseAdapter] = {}
        self.risk = risk or RiskManager()
        self.log_path = log_path
        self._trade_log: List[dict] = []
        self._load_log()

    def register(self, adapter: BaseAdapter) -> "TradeMesh":
        """Register a venue adapter. Chainable."""
        self._adapters[adapter.name] = adapter
        print(f"✅ TradeMesh: registered {adapter.name}")
        return self

    def venues(self) -> List[str]:
        return list(self._adapters.keys())

    def trade(self,
              ticker: str,
              direction: str = "bullish",
              amount: float = 10.0,
              score: float = 7.0,
              venue: str = "auto",
              **kwargs) -> TradeResult:
        """
        Main entry point. Creates a signal and routes it.

        Args:
            ticker: Asset ticker ("IBIT", "NVDA", "BTC")
            direction: "bullish" or "bearish"
            amount: USD amount to risk
            score: Signal confidence 0-10
            venue: "auto" or specific adapter name
            **kwargs: Extra fields for TradeSignal (strike, expiration, market_id, etc.)
        """
        signal = TradeSignal(
            ticker=ticker.upper(),
            direction=direction,
            amount=amount,
            score=score,
            venue=venue,
            **kwargs
        )
        return self.execute(signal)

    def execute(self, signal: TradeSignal) -> TradeResult:
        """Execute a TradeSignal through the appropriate adapter"""

        # Risk check
        current_exposure = self._current_exposure()
        approved, reason = self.risk.check(signal, current_exposure)
        if not approved:
            result = TradeResult(
                success=False,
                venue="risk_manager",
                ticker=signal.ticker,
                error=f"Risk rejected: {reason}"
            )
            self._log(signal, result)
            return result

        # Find adapter
        adapter = self._route(signal)
        if not adapter:
            result = TradeResult(
                success=False,
                venue="router",
                ticker=signal.ticker,
                error=f"No adapter available for {signal.ticker} (venue={signal.venue}, registered={self.venues()})"
            )
            self._log(signal, result)
            return result

        # Execute
        result = adapter.execute(signal)
        self._log(signal, result)
        return result

    def positions(self, venue: Optional[str] = None) -> List[Position]:
        """Get all positions, optionally filtered by venue"""
        all_positions = []
        for name, adapter in self._adapters.items():
            if venue and name != venue:
                continue
            all_positions.extend(adapter.positions())
        return all_positions

    def pnl(self) -> dict:
        """Get unified P&L summary across all venues"""
        positions = self.positions()
        total_cost = sum(p.cost_basis for p in positions)
        total_value = sum(p.current_value for p in positions)
        total_pnl = sum(p.pnl for p in positions)
        wins = sum(1 for p in positions if p.is_winner)
        losses = len(positions) - wins
        win_rate = wins / len(positions) if positions else 0

        return {
            "positions": len(positions),
            "cost_basis": round(total_cost, 2),
            "current_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 3),
            "by_venue": {
                name: {
                    "pnl": round(sum(p.pnl for p in positions if p.venue == name), 2),
                    "positions": len([p for p in positions if p.venue == name])
                }
                for name in self.venues()
            }
        }

    def health(self) -> dict:
        """Check all adapters"""
        return {name: adapter.health_check() for name, adapter in self._adapters.items()}

    # ── Internal ─────────────────────────────────────────────────────────────

    def _route(self, signal: TradeSignal) -> Optional[BaseAdapter]:
        """Pick the best adapter for this signal"""
        # Explicit venue
        if signal.venue != "auto":
            return self._adapters.get(signal.venue)

        # Ticker-based routing
        signal_type = self.TICKER_TYPES.get(signal.ticker.upper(), "stocks")
        preferred = self.ROUTING_RULES.get(signal_type, [])

        for venue_name in preferred:
            adapter = self._adapters.get(venue_name)
            if adapter and adapter.can_trade(signal):
                return adapter

        # Fallback: first adapter that can trade it
        for adapter in self._adapters.values():
            if adapter.can_trade(signal):
                return adapter

        return None

    def _current_exposure(self) -> float:
        """Total current cost basis across all venues"""
        return sum(p.cost_basis for p in self.positions())

    def _log(self, signal: TradeSignal, result: TradeResult):
        """Persist trade log for performance tracking"""
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "ticker": signal.ticker,
            "direction": signal.direction,
            "amount": signal.amount,
            "score": signal.score,
            "source": signal.source,
            "venue": result.venue,
            "success": result.success,
            "status": result.status,
            "pnl": None,  # filled on close
            "error": result.error,
        }
        self._trade_log.append(entry)
        self._save_log()

    def _load_log(self):
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path) as f:
                    self._trade_log = json.load(f)
            except Exception:
                self._trade_log = []

    def _save_log(self):
        try:
            with open(self.log_path, "w") as f:
                json.dump(self._trade_log, f, indent=2)
        except Exception:
            pass
