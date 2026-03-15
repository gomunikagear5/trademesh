"""
TradeMesh — Universal trading execution layer
One interface. Any venue.
"""

from .core import TradeMesh
from .models import TradeSignal, TradeResult, Position

__version__ = "0.1.0"
__all__ = ["TradeMesh", "TradeSignal", "TradeResult", "Position"]
