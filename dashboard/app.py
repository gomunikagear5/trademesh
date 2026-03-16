"""
TradeMesh Dashboard — FastAPI web UI
Run: uvicorn dashboard.app:app --host 0.0.0.0 --port 8765 --reload
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Add project root to path ──────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from trademesh import TradeMesh
from trademesh.core import RiskManager

app = FastAPI(title="TradeMesh Dashboard", version="0.1.0")

# ── Initialize TradeMesh with whatever adapters are configured ────────────────

tm = TradeMesh(
    risk=RiskManager(
        max_position_usd=float(os.environ.get("TM_MAX_POSITION", "500")),
        max_total_exposure_usd=float(os.environ.get("TM_MAX_EXPOSURE", "5000")),
        min_score=float(os.environ.get("TM_MIN_SCORE", "0")),  # dashboard allows any score
    ),
    log_path=str(ROOT / "trademesh_log.json"),
)

UNCONFIGURED = []

# Robinhood
try:
    if os.environ.get("ROBINHOOD_USERNAME") or os.environ.get("ROBINHOOD_PASSWORD"):
        from trademesh.adapters import RobinhoodAdapter
        tm.register(RobinhoodAdapter(
            username=os.environ.get("ROBINHOOD_USERNAME"),
            password=os.environ.get("ROBINHOOD_PASSWORD"),
        ))
    else:
        UNCONFIGURED.append({"name": "robinhood", "reason": "ROBINHOOD_USERNAME / ROBINHOOD_PASSWORD not set"})
except Exception as e:
    UNCONFIGURED.append({"name": "robinhood", "reason": str(e)})

# Kalshi
try:
    if os.environ.get("KALSHI_API_KEY"):
        from trademesh.adapters import KalshiAdapter
        tm.register(KalshiAdapter())
    else:
        UNCONFIGURED.append({"name": "kalshi", "reason": "KALSHI_API_KEY not set"})
except Exception as e:
    UNCONFIGURED.append({"name": "kalshi", "reason": str(e)})

# Coinbase
try:
    if os.environ.get("COINBASE_API_KEY_NAME"):
        from trademesh.adapters import CoinbaseAdapter
        tm.register(CoinbaseAdapter())
    else:
        UNCONFIGURED.append({"name": "coinbase", "reason": "COINBASE_API_KEY_NAME not set"})
except Exception as e:
    UNCONFIGURED.append({"name": "coinbase", "reason": str(e)})

# Simmer
try:
    if os.environ.get("SIMMER_API_KEY"):
        from trademesh.adapters import SimmerAdapter
        tm.register(SimmerAdapter(api_key=os.environ["SIMMER_API_KEY"]))
    else:
        UNCONFIGURED.append({"name": "simmer", "reason": "SIMMER_API_KEY not set"})
except Exception as e:
    UNCONFIGURED.append({"name": "simmer", "reason": str(e)})

# Alpaca
try:
    if os.environ.get("ALPACA_API_KEY"):
        from trademesh.adapters import AlpacaAdapter
        tm.register(AlpacaAdapter())
    else:
        UNCONFIGURED.append({"name": "alpaca", "reason": "ALPACA_API_KEY not set"})
except Exception as e:
    UNCONFIGURED.append({"name": "alpaca", "reason": str(e)})


# ── Pydantic models ───────────────────────────────────────────────────────────

class TradeRequest(BaseModel):
    ticker: str
    direction: str = "bullish"
    amount: float = 10.0
    score: float = 7.0
    venue: str = "auto"
    market_id: Optional[str] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    notes: str = ""


# ── Helper ────────────────────────────────────────────────────────────────────

def ok(data):
    return {"success": True, "data": data, "error": None}

def err(msg):
    return {"success": False, "data": None, "error": msg}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    template_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=template_path.read_text())


@app.get("/api/venues")
async def get_venues():
    venues = tm.venues()
    health = {}
    for name in venues:
        try:
            adapter = tm._adapters[name]
            health[name] = adapter.health_check()
        except Exception:
            health[name] = False
    return ok({
        "active": venues,
        "health": health,
        "unconfigured": UNCONFIGURED,
    })


@app.get("/api/status")
async def get_status():
    try:
        pnl = tm.pnl()
        venues = tm.venues()
        return ok({
            "venues": venues,
            "unconfigured": UNCONFIGURED,
            "pnl": pnl,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        return ok({
            "venues": tm.venues(),
            "unconfigured": UNCONFIGURED,
            "pnl": {"positions": 0, "total_pnl": 0, "current_value": 0, "cost_basis": 0},
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })


@app.get("/api/positions")
async def get_positions():
    try:
        positions = tm.positions()
        return ok([
            {
                "venue": p.venue,
                "ticker": p.ticker,
                "side": p.side,
                "cost_basis": round(p.cost_basis, 2),
                "current_value": round(p.current_value, 2),
                "pnl": round(p.pnl, 2),
                "pnl_pct": round(p.pnl_pct, 2),
                "status": p.status,
                "question": p.question,
                "market_id": p.market_id,
            }
            for p in positions
        ])
    except Exception as e:
        return ok([])


@app.get("/api/history")
async def get_history():
    log_path = ROOT / "trademesh_log.json"
    if not log_path.exists():
        return ok([])
    try:
        with open(log_path) as f:
            log = json.load(f)
        return ok(list(reversed(log[-100:])))  # last 100, newest first
    except Exception as e:
        return err(str(e))


@app.post("/api/trade")
async def execute_trade(req: TradeRequest):
    try:
        result = tm.trade(
            ticker=req.ticker.upper(),
            direction=req.direction,
            amount=req.amount,
            score=req.score,
            venue=req.venue,
            market_id=req.market_id,
            strike=req.strike,
            expiration=req.expiration,
            notes=req.notes,
        )
        return ok({
            "success": result.success,
            "venue": result.venue,
            "order_id": result.order_id,
            "ticker": result.ticker,
            "side": result.side,
            "amount": result.amount,
            "status": result.status,
            "market": result.market,
            "error": result.error,
            "message": str(result),
        })
    except Exception as e:
        return err(str(e))
