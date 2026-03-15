"""
KalshiAdapter — Regulated US event/prediction markets via Kalshi Trade API v2

Required env vars (or pass to constructor):
    KALSHI_API_KEY      — your Kalshi API key ID
    KALSHI_PRIVATE_KEY  — RSA private key (PEM string, or set KALSHI_PRIVATE_KEY_PATH for file path)

Docs: https://trading-api.readme.io/reference/
"""
import os
import time
import uuid
from typing import List, Optional

from .base import BaseAdapter
from ..models import TradeSignal, TradeResult, Position

KALSHI_BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"
KALSHI_DEMO_URL = "https://demo-api.kalshi.co/trade-api/v2"


class KalshiAdapter(BaseAdapter):
    name = "kalshi"
    supports = ["prediction", "event", "macro_direction", "politics", "weather"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        demo: bool = False,
    ):
        """
        Args:
            api_key: Kalshi API key ID. Falls back to KALSHI_API_KEY env var.
            private_key: RSA private key PEM string. Falls back to KALSHI_PRIVATE_KEY env var.
            private_key_path: Path to PEM file. Falls back to KALSHI_PRIVATE_KEY_PATH env var.
            demo: Use Kalshi demo environment (default: False = live).
        """
        self._api_key = api_key or os.environ.get("KALSHI_API_KEY", "")
        self._private_key_pem = private_key or os.environ.get("KALSHI_PRIVATE_KEY", "")
        self._private_key_path = private_key_path or os.environ.get("KALSHI_PRIVATE_KEY_PATH", "")
        self._base_url = KALSHI_DEMO_URL if demo else KALSHI_BASE_URL
        self._session = None
        self._private_key_obj = None

    def _load_private_key(self):
        """Load RSA private key from PEM string or file."""
        if self._private_key_obj:
            return self._private_key_obj
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
        except ImportError:
            raise ImportError(
                "KalshiAdapter requires 'cryptography': pip install cryptography"
            )

        pem = self._private_key_pem
        if not pem and self._private_key_path:
            with open(self._private_key_path, "rb") as f:
                pem = f.read().decode()

        if not pem:
            raise ValueError(
                "Kalshi private key required. Set KALSHI_PRIVATE_KEY or KALSHI_PRIVATE_KEY_PATH."
            )

        if isinstance(pem, str):
            pem = pem.encode()

        self._private_key_obj = load_pem_private_key(pem, password=None)
        return self._private_key_obj

    def _make_jwt(self, method: str, path: str) -> str:
        """Generate a signed JWT for Kalshi API authentication (RSA-PS256)."""
        try:
            import jwt as pyjwt
        except ImportError:
            raise ImportError("KalshiAdapter requires 'PyJWT': pip install PyJWT cryptography")

        private_key = self._load_private_key()
        now = int(time.time())
        payload = {
            "sub": self._api_key,
            "iat": now,
            "exp": now + 30,
            "jti": str(uuid.uuid4()),
            "method": method.upper(),
            "path": path,
        }
        token = pyjwt.encode(payload, private_key, algorithm="PS256")
        return token

    def _session_headers(self, method: str, path: str) -> dict:
        token = self._make_jwt(method, path)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        import requests
        if not self._api_key:
            raise ValueError("KALSHI_API_KEY is not set.")
        url = self._base_url + path
        headers = self._session_headers("GET", path)
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        import requests
        if not self._api_key:
            raise ValueError("KALSHI_API_KEY is not set.")
        url = self._base_url + path
        headers = self._session_headers("POST", path)
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def can_trade(self, signal: TradeSignal) -> bool:
        """Trade if market_id is set, or ticker maps to a known Kalshi event category."""
        if signal.market_id:
            return True
        # Kalshi shines for macro/political/event markets — not individual equities
        KALSHI_CATEGORIES = {
            "FED", "CPI", "GDP", "NFP", "NASDAQ", "SPX", "BTC", "ETH",
            "RECESSION", "ELECTION", "RATE", "INFLATION"
        }
        return signal.ticker.upper() in KALSHI_CATEGORIES

    def execute(self, signal: TradeSignal) -> TradeResult:
        try:
            market_id = signal.market_id
            if not market_id:
                # Try to find best matching active market
                market_id = self._find_market(signal)
            if not market_id:
                return TradeResult(
                    success=False, venue=self.name, ticker=signal.ticker,
                    error=f"No Kalshi market found for {signal.ticker}. Set signal.market_id."
                )
            return self._place_order(signal, market_id)
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def _find_market(self, signal: TradeSignal) -> Optional[str]:
        """Search active markets for the best match to the signal."""
        try:
            keyword = signal.ticker.lower()
            data = self._get("/markets", params={"status": "open", "limit": 100})
            markets = data.get("markets", [])
            for m in markets:
                title = (m.get("title") or m.get("question") or "").lower()
                if keyword in title:
                    # Simple edge check on yes_bid
                    yes_bid = m.get("yes_bid", 50) / 100.0
                    if signal.direction == "bullish" and yes_bid > 0.52:
                        return m.get("ticker")
                    elif signal.direction == "bearish" and yes_bid < 0.48:
                        return m.get("ticker")
        except Exception:
            pass
        return None

    def _place_order(self, signal: TradeSignal, market_ticker: str) -> TradeResult:
        side = "yes" if signal.direction == "bullish" else "no"

        # Kalshi orders use cents (1 = $0.01), amount in USD
        amount_cents = int(signal.amount * 100)

        body = {
            "ticker": market_ticker,
            "action": "buy",
            "type": "market",
            "side": side,
            "count": max(1, amount_cents // 100),  # # of contracts at ~$1 each
            "client_order_id": str(uuid.uuid4()),
        }

        data = self._post("/portfolio/orders", body)
        order = data.get("order", {})

        return TradeResult(
            success=True,
            venue=self.name,
            order_id=order.get("order_id"),
            ticker=market_ticker,
            side=side,
            amount=signal.amount,
            status=order.get("status", "pending"),
            market=order.get("ticker"),
            raw=order,
        )

    def positions(self) -> List[Position]:
        try:
            data = self._get("/portfolio/positions")
            raw_positions = data.get("market_positions", [])
            result = []
            for p in raw_positions:
                ticker = p.get("ticker", "")
                yes_count = p.get("position", 0)
                side = "yes" if yes_count >= 0 else "no"
                # Cost/value approximated from available fields
                cost = abs(p.get("market_exposure", 0)) / 100.0
                value = abs(p.get("resting_orders_count", 0)) / 100.0
                result.append(Position(
                    venue=self.name,
                    ticker=ticker,
                    side=side,
                    cost_basis=cost,
                    current_value=value,
                    pnl=value - cost,
                    pnl_pct=((value - cost) / cost * 100) if cost > 0 else 0.0,
                    status="open",
                    market_id=ticker,
                    raw=p,
                ))
            return result
        except Exception:
            return []

    def balance(self) -> float:
        try:
            data = self._get("/portfolio/balance")
            # balance is in cents
            return data.get("balance", 0) / 100.0
        except Exception:
            return 0.0
