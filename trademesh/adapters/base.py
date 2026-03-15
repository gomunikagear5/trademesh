"""
BaseAdapter — interface every venue adapter must implement.
To add a new venue: subclass BaseAdapter and implement all 4 methods.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import TradeSignal, TradeResult, Position


class BaseAdapter(ABC):
    """
    Implement this to add any trading venue to TradeMesh.

    Example:
        class MyBrokerAdapter(BaseAdapter):
            name = "mybroker"
            supports = ["stocks", "options"]

            def can_trade(self, signal): ...
            def execute(self, signal): ...
            def positions(self): ...
            def balance(self): ...
    """

    # Override in subclass
    name: str = "base"
    supports: List[str] = []  # e.g. ["stocks", "options", "crypto", "prediction"]

    @abstractmethod
    def can_trade(self, signal: TradeSignal) -> bool:
        """
        Return True if this adapter can handle the given signal.
        Used by the Signal Router for auto-venue selection.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, signal: TradeSignal) -> TradeResult:
        """
        Execute a trade for the given signal.
        Must return a TradeResult (success or failure).
        Should NEVER raise — catch all exceptions and return TradeResult(success=False).
        """
        raise NotImplementedError

    @abstractmethod
    def positions(self) -> List[Position]:
        """
        Return all current open positions on this venue.
        """
        raise NotImplementedError

    @abstractmethod
    def balance(self) -> float:
        """
        Return available cash balance (USD) on this venue.
        """
        raise NotImplementedError

    def health_check(self) -> bool:
        """
        Optional: verify API connectivity. Returns True if healthy.
        """
        try:
            self.balance()
            return True
        except Exception:
            return False

    def __repr__(self):
        return f"<{self.__class__.__name__} venue={self.name}>"
