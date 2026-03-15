#!/usr/bin/env bash
# TradeMesh Installer
# Usage: curl -sSL https://raw.githubusercontent.com/gomunikagear5/trademesh/main/install.sh | bash

set -e

REPO="https://github.com/gomunikagear5/trademesh"
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}🔌 TradeMesh Installer${RESET}"
echo -e "   Universal trading execution layer"
echo "   $REPO"
echo ""

# ── Check Python ───────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌  Python 3 not found. Install Python 3.8+ and retry."
  echo "    https://www.python.org/downloads/"
  exit 1
fi

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYMAJ=$(python3 -c "import sys; print(sys.version_info.major)")
PYMIN=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYMAJ" -lt 3 ] || { [ "$PYMAJ" -eq 3 ] && [ "$PYMIN" -lt 8 ]; }; then
  echo "❌  Python 3.8+ required (found $PYVER). Please upgrade."
  exit 1
fi

echo -e "✅  Python $PYVER detected"

# ── Check pip ─────────────────────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null 2>&1; then
  echo "❌  pip not found. Install pip and retry."
  exit 1
fi

PIP="pip3"
if ! command -v pip3 &>/dev/null; then
  PIP="python3 -m pip"
fi

# ── Install TradeMesh ─────────────────────────────────────────────────────────
echo ""
echo -e "📦  Installing TradeMesh from GitHub..."
$PIP install --quiet --upgrade "git+${REPO}.git"

# ── Install adapter deps ──────────────────────────────────────────────────────
echo -e "📦  Installing adapter dependencies..."
$PIP install --quiet --upgrade requests PyJWT cryptography

echo ""
echo -e "${GREEN}${BOLD}✅  TradeMesh installed successfully!${RESET}"
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  Quick Start — Connect your broker in 3 lines${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

echo -e "${CYAN}${BOLD}🟢  Robinhood (Stocks + Options)${RESET}"
echo -e "${YELLOW}    # Set env vars: ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD${RESET}"
cat << 'EOF'
    from trademesh import TradeMesh
    from trademesh.adapters import RobinhoodAdapter

    tm = TradeMesh()
    tm.register(RobinhoodAdapter())
    tm.trade(ticker="AAPL", direction="bullish", amount=50)
EOF
echo ""

echo -e "${CYAN}${BOLD}🔵  Kalshi (Regulated Event Markets)${RESET}"
echo -e "${YELLOW}    # Set env vars: KALSHI_API_KEY, KALSHI_PRIVATE_KEY (or KALSHI_PRIVATE_KEY_PATH)${RESET}"
cat << 'EOF'
    from trademesh import TradeMesh
    from trademesh.adapters import KalshiAdapter

    tm = TradeMesh()
    tm.register(KalshiAdapter())
    tm.trade(ticker="FED", direction="bullish", amount=25)
EOF
echo ""

echo -e "${CYAN}${BOLD}🟠  Coinbase (Crypto)${RESET}"
echo -e "${YELLOW}    # Set env vars: COINBASE_API_KEY_NAME, COINBASE_PRIVATE_KEY${RESET}"
cat << 'EOF'
    from trademesh import TradeMesh
    from trademesh.adapters import CoinbaseAdapter

    tm = TradeMesh()
    tm.register(CoinbaseAdapter())
    tm.trade(ticker="BTC", direction="bullish", amount=100)
EOF
echo ""

echo -e "${CYAN}${BOLD}🔌  All adapters at once${RESET}"
cat << 'EOF'
    from trademesh import TradeMesh
    from trademesh.adapters import RobinhoodAdapter, KalshiAdapter, CoinbaseAdapter

    tm = TradeMesh()
    tm.register(RobinhoodAdapter())
    tm.register(KalshiAdapter())
    tm.register(CoinbaseAdapter())

    # TradeMesh auto-routes to the best adapter for each signal
    tm.trade(ticker="TSLA", direction="bearish", amount=200)
    tm.trade(ticker="BTC", direction="bullish", amount=50)
    tm.trade(ticker="FED", direction="bearish", amount=25)
EOF
echo ""

echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  📚  Full docs + adapter guide: ${REPO}"
echo -e "  ⭐  Star us on GitHub if TradeMesh saves you time!"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
