"""
RobinhoodAdapter — Stocks + Options via robin_stocks
Credentials stored locally via robin_stocks auth (never passed through TradeMesh).
"""
from typing import List, Optional
from .base import BaseAdapter
from ..models import TradeSignal, TradeResult, Position


class RobinhoodAdapter(BaseAdapter):
    name = "robinhood"
    supports = ["stocks", "options", "crypto"]

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Credentials optional — if not passed, robin_stocks uses stored session.
        NEVER log or expose credentials. Store via robin_stocks login once, reuse token.
        """
        self._authenticated = False
        self._username = username
        self._password = password

    def _ensure_auth(self):
        if self._authenticated:
            return
        try:
            import robin_stocks.robinhood as rh
            if self._username and self._password:
                rh.login(self._username, self._password)
            else:
                # Try stored session
                rh.login()
            self._authenticated = True
        except Exception as e:
            raise ConnectionError(f"Robinhood auth failed: {e}. Run robin_stocks login first.")

    def can_trade(self, signal: TradeSignal) -> bool:
        """Can trade stocks and options on US equities"""
        # Skip crypto-only signals (better on Hyperliquid/Coinbase)
        crypto_only = {"BTC", "ETH", "SOL", "DOGE", "ADA"}
        return signal.ticker.upper() not in crypto_only

    def execute(self, signal: TradeSignal) -> TradeResult:
        try:
            self._ensure_auth()
            import robin_stocks.robinhood as rh

            ticker = signal.ticker.upper()

            # Options trade
            if signal.strike and signal.expiration:
                return self._execute_option(signal, rh, ticker)

            # Stock trade
            return self._execute_stock(signal, rh, ticker)

        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def _execute_option(self, signal: TradeSignal, rh, ticker: str) -> TradeResult:
        """Buy an options contract"""
        option_type = signal.side or ("call" if signal.direction == "bullish" else "put")
        try:
            # Get current option price
            option_data = rh.options.find_options_by_expiration_and_strike(
                ticker,
                expirationDate=signal.expiration,
                strikePrice=str(signal.strike),
                optionType=option_type
            )
            if not option_data:
                return TradeResult(success=False, venue=self.name, error=f"Option not found: {ticker} {signal.strike} {signal.expiration} {option_type}")

            option = option_data[0]
            ask = float(option.get("ask_price", 0) or 0)
            if ask <= 0:
                return TradeResult(success=False, venue=self.name, error="Invalid ask price")

            # Calculate contracts (1 contract = 100 shares)
            contracts = max(1, int(signal.amount / (ask * 100)))

            result = rh.orders.order_buy_option_limit(
                positionEffect="open",
                creditOrDebit="debit",
                price=ask,
                symbol=ticker,
                quantity=contracts,
                expirationDate=signal.expiration,
                strike=signal.strike,
                optionType=option_type,
                timeInForce="gfd"
            )

            return TradeResult(
                success=True,
                venue=self.name,
                order_id=result.get("id"),
                ticker=ticker,
                side=option_type,
                amount=ask * contracts * 100,
                price=ask,
                status=result.get("state", "pending"),
                market=f"{ticker} {option_type.upper()} ${signal.strike} {signal.expiration}",
                raw=result
            )
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def _execute_stock(self, signal: TradeSignal, rh, ticker: str) -> TradeResult:
        """Buy/sell stock shares"""
        try:
            quote = rh.stocks.get_latest_price(ticker)
            price = float(quote[0]) if quote else 0
            if price <= 0:
                return TradeResult(success=False, venue=self.name, error="Could not get price")

            shares = max(1, int(signal.amount / price))
            side = "buy" if signal.direction == "bullish" else "sell"

            if side == "buy":
                result = rh.orders.order_buy_market(ticker, shares)
            else:
                result = rh.orders.order_sell_market(ticker, shares)

            return TradeResult(
                success=True,
                venue=self.name,
                order_id=result.get("id"),
                ticker=ticker,
                side=side,
                amount=price * shares,
                price=price,
                status=result.get("state", "pending"),
                raw=result
            )
        except Exception as e:
            return TradeResult(success=False, venue=self.name, error=str(e))

    def positions(self) -> List[Position]:
        try:
            self._ensure_auth()
            import robin_stocks.robinhood as rh

            positions = []

            # Stock positions
            stock_positions = rh.account.get_open_stock_positions()
            for p in (stock_positions or []):
                ticker = rh.stocks.get_name_by_url(p.get("instrument", "")) or ""
                qty = float(p.get("quantity", 0))
                avg_price = float(p.get("average_buy_price", 0))
                cost = qty * avg_price

                latest = rh.stocks.get_latest_price(ticker)
                current_price = float(latest[0]) if latest else avg_price
                current_value = qty * current_price
                pnl = current_value - cost
                pnl_pct = (pnl / cost * 100) if cost > 0 else 0

                positions.append(Position(
                    venue=self.name,
                    ticker=ticker,
                    side="long",
                    cost_basis=cost,
                    current_value=current_value,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    status="open"
                ))

            return positions
        except Exception:
            return []

    def balance(self) -> float:
        try:
            self._ensure_auth()
            import robin_stocks.robinhood as rh
            profile = rh.profiles.load_account_profile()
            return float(profile.get("buying_power", 0))
        except Exception:
            return 0.0

    def get_history(self) -> list:
        """Export full trade history for backtesting"""
        try:
            self._ensure_auth()
            import robin_stocks.robinhood as rh
            return rh.account.get_all_transactions()
        except Exception:
            return []
