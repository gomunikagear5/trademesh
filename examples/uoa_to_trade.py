"""
Example: UOA Scanner → TradeMesh → Multi-venue execution
This is the full loop we built — UOA signal fires, TradeMesh routes to best venue.
"""
from trademesh import TradeMesh
from trademesh.adapters import SimmerAdapter, RobinhoodAdapter, AlpacaAdapter
from trademesh.core import RiskManager

# ── Setup ────────────────────────────────────────────────────────────────────

tm = TradeMesh(
    risk=RiskManager(
        max_position_usd=25.0,      # max $25 per trade
        max_total_exposure_usd=150, # max $150 total at risk
        min_score=7.0               # only high-conviction signals
    )
)

# Register venues (add what you have)
tm.register(SimmerAdapter(api_key="sk_live_..."))
# tm.register(RobinhoodAdapter())          # uncomment after login
# tm.register(AlpacaAdapter("key", "secret", paper=True))  # paper trading

print(f"TradeMesh ready. Venues: {tm.venues()}")

# ── UOA Signal comes in ───────────────────────────────────────────────────────

# Simulated UOA alert:
# IBIT PUT $42.5 | Vol/OI 82x | Premium $201K | Score 8/10 → BEARISH

result = tm.trade(
    ticker="IBIT",
    direction="bearish",
    amount=20,
    score=8.0,
    venue="auto",       # TradeMesh picks best venue
    source="uoa_scanner",
    notes="Vol/OI 82x, $201K premium, score 8/10"
)

print(result)
# ✅ [simmer] no IBIT → Bitcoin Up or Down $20.00 → submitted

# ── Check P&L ────────────────────────────────────────────────────────────────

print("\nPortfolio P&L:")
pnl = tm.pnl()
print(f"  Positions: {pnl['positions']}")
print(f"  Total PnL: ${pnl['total_pnl']:.2f}")
print(f"  Win rate: {pnl['win_rate']*100:.0f}%")

# ── Manual trade ─────────────────────────────────────────────────────────────

# Force specific venue
result2 = tm.trade(
    ticker="NVDA",
    direction="bearish",
    amount=50,
    score=9.0,
    venue="robinhood",
    side="put",
    strike=800,
    expiration="2026-04-17",
    source="uoa_scanner"
)
print(result2)
