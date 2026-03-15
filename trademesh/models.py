"""
TradeMesh data models — shared across all adapters
"""
from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime


@dataclass
class TradeSignal:
    """
    Normalized signal that can be routed to any venue.
    Created by signal sources (UOA scanner, AI, manual).
    """
    ticker: str                          # e.g. "IBIT", "NVDA", "BTC"
    direction: Literal["bullish", "bearish", "neutral"]
    amount: float                        # USD amount to risk
    score: float = 5.0                   # signal confidence 0-10
    venue: str = "auto"                  # "auto" or specific venue name

    # Options-specific (optional)
    side: Optional[str] = None           # "call" / "put" / "yes" / "no"
    strike: Optional[float] = None
    expiration: Optional[str] = None     # "YYYY-MM-DD"

    # Prediction market-specific (optional)
    market_id: Optional[str] = None
    question: Optional[str] = None

    # Metadata
    source: str = "manual"              # "uoa_scanner", "manual", "ai", etc.
    created_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""


@dataclass
class TradeResult:
    """
    Result of a trade execution, normalized across all venues.
    """
    success: bool
    venue: str
    order_id: Optional[str] = None
    ticker: Optional[str] = None
    side: Optional[str] = None
    amount: float = 0.0
    price: Optional[float] = None
    status: str = "unknown"             # "filled", "pending", "rejected", "error"
    market: Optional[str] = None       # human-readable market description
    error: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)
    raw: Optional[dict] = None         # raw venue response for debugging

    def __str__(self):
        if self.success:
            return f"✅ [{self.venue}] {self.side} {self.ticker or self.market} ${self.amount:.2f} → {self.status}"
        return f"❌ [{self.venue}] FAILED: {self.error}"


@dataclass
class Position:
    """
    A live or closed position, normalized across venues.
    """
    venue: str
    ticker: str
    side: str
    cost_basis: float
    current_value: float
    pnl: float
    pnl_pct: float
    status: str                         # "open", "closed"
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    market_id: Optional[str] = None
    question: Optional[str] = None
    raw: Optional[dict] = None

    @property
    def is_winner(self) -> bool:
        return self.pnl > 0
