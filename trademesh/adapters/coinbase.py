"""
CoinbaseAdapter — Crypto spot trading via Coinbase Advanced Trade API v3

Required env vars (or pass to constructor):
    COINBASE_API_KEY_NAME  — CDP API key name (format: "organizations/{org_id}/apiKeys/{key_id}")
    COINBASE_PRIVATE_KEY   — Ed25519 private key PEM string

Docs: https://docs.cdp.coinbase.com/advanced-trade/docs/welcome
"""
import os
import time
import uuid
from typing import List, Optional

from .base import BaseAdapter
from ..models import TradeSignal, TradeResult, Position

COINBASE_BASE_URL = "https://api.coinbase.com/api/v3/brokerage"

# Map signal tickers → Coinbase product IDs
TICKER_MAP = {
    "BTC": "BTC-USDC",
    "ETH": "ETH-USDC",
    "SOL": "SOL-USDC",
    "XRP": "XRP-USDC",
    "DOGE": "DOGE-USDC",
    "ADA": "ADA-USDC",
    "AVAX": "AVAX-USDC",
    "MATIC": "MATIC-USDC",
    "LINK": "LINK-USDC",
    "DOT": "DOT-USDC",
    "UNI": "UNI-USDC",
    "ATOM": "ATOM-USDC",
    "LTC": "LTC-USDC",
    "BCH": "BCH-USDC",
    # ETF bridging for direction signals
    "IBIT": "BTC-USDC",
    "ETHA": "ETH-USDC",
    "BTCO": "BTC-USDC",
    "FBTC": "BTC-USDC",
}


class CoinbaseAdapter(BaseAdapter):
    name = "coinbase"
    supports = ["crypto", "crypto_direction"]

    def __init__(
        self,
        api_key_name: Optional[str] = None,
        private_key: Optional[str] = None,
    ):
        """
        Args:
            api_key_name: CDP API key name. Falls back to COINBASE_API_KEY_NAME env var.
            private_key: Ed25519 private key PEM string. Falls back to COINBASE_PRIVATE_KEY env var.
        """
        self._api_key_name = api_key_name or os.environ.get("COINBASE_API_KEY_NAME", "")
        self._private_key_pem = private_key or os.environ.get("COINBASE_PRIVATE_KEY", "")

    def _validate_creds(self):
        if not self._api_key_name or not self._private_key_pem:
            raise ValueError(
                "Coinbase credentials required. Set COINBASE_API_KEY_NAME and COINBASE_PRIVATE_KEY."
            )

    def _make_jwt(self, method: str, path: str) -> str:
        """Generate a signed JWT for Coinbase CDP API authentication (Ed25519)."""
        try:
            import jwt as pyjwt
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
        except ImportError:
            raise ImportError(
                "CoinbaseAdapter requires 'PyJWT' and 'cryptography': pip install PyJWT cryptography"
            )

        pem = self._private_key_pem
        if isinstance(pem, str):
            pem = pem.encode()

        private_key = load_pem_private_key(pem, password=None)
        now = int(time.time())

        payload = {
            "sub": self._api_key_name,
            "iss": "cdp",
            "nbf": now,
            "exp": now + 120,
            "uri": f"{method} api.coinbase.com{path}",
        }
        token = pyjwt.encode(
            payload,
            private_key,
            algorithm="EdDSA",
            headers={"kid": self._api_key_name, "nonce": str(uuid.uuid4()).replace("-", "")},
        )
        return token

    def _headers(self, method: str, path: str) -> dict:
        token = self._make_jwt(method, path)
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        import requests
        self._validate_creds()
        url = COINBASE_BASE_URL + path
        resp = requests.get(url, headers=self._headers("GET", f"/api/v3/brokerage{path}"), params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        import requests
        self._validate_creds()
        url = COINBASE_BASE_URL + path
        resp = requests.post(url, headers=self._headers("POST", f"/api/v3/brokerage{path}"), json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _resolve_product(self, ticker: str) -> Optional[str]:
        """Resolve signal ticker to a Coinbase product ID."""
        ticker = ticker.upper()
        return TICKER_MAP.get(ticker) or (f"{ticker}-USDC" if len(ticker) <= 6 else None)

    def can_trade(self, signal: TradeSignal) -> bool:
        """Trade crypto tickers that map to Coinbase products."""
        return self._resolve_product(signal.ticker.upper()) is not None

    def execute(self, signal: TradeSignal) -> TradeResult:
        try:
            product_id = self._resolve_product(signal.ticker.upper())
            if not product_id:
                return TradeResult(
                    success=False, venue=self.name, ticker=signal.ticker,
                    error=f"No Coinbase product mapping for ticker: {signal.ticker}"
                )

            side = "BUY" if signal.direction == "bullish" else "SELL"
            client_order_id = str(uuid.uuid4())

            body = {
                "client_order_id": client_order_id,
                "product_id": product_id,
                "side": side,
                "order_configuration": {
                    "market_market_ioc": {
                        "quote_size": str(round(signal.amount, 2))  # USD amount
                    }
                },
            }

            data = self._post("/orders", body)
            order = data.get("success_response", data.get("order_configuration", {}))
            success = data.get("success", False)
            error_resp = data.get("error_response", {})

            if not success:
                return TradeResult(
                    success=False,
                    venue=self.name,
                    ticker=signal.ticker,
                    error=error_resp.get("message", "Order failed"),
                    raw=data,
                )

            return TradeResult(
                success=True,
                venue=self.name,
                order_id=order.get("order_id") or client_order_id,
                ticker=product_id,
                side=side.lower(),
                amount=signal.amount,
                status=order.get("status", "pending"),
                market=product_id,
                raw=data,
            )

        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def positions(self) -> List[Position]:
        """Return non-zero crypto holdings as positions."""
        try:
            data = self._get("/accounts")
            accounts = data.get("accounts", [])
            positions = []
            for acct in accounts:
                currency = acct.get("currency", "")
                if currency in ("USD", "USDC", "USDT"):
                    continue  # skip cash
                avail = float(acct.get("available_balance", {}).get("value", 0) or 0)
                hold = float(acct.get("hold", {}).get("value", 0) or 0)
                total = avail + hold
                if total <= 0:
                    continue
                positions.append(Position(
                    venue=self.name,
                    ticker=currency,
                    side="long",
                    cost_basis=0.0,     # Coinbase accounts API doesn't return cost basis
                    current_value=total,
                    pnl=0.0,
                    pnl_pct=0.0,
                    status="open",
                    raw=acct,
                ))
            return positions
        except Exception:
            return []

    def balance(self) -> float:
        """Return available USD/USDC balance."""
        try:
            data = self._get("/accounts")
            accounts = data.get("accounts", [])
            total = 0.0
            for acct in accounts:
                currency = acct.get("currency", "")
                if currency in ("USD", "USDC"):
                    val = float(acct.get("available_balance", {}).get("value", 0) or 0)
                    total += val
            return total
        except Exception:
            return 0.0
