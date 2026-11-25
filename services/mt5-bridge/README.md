# MT5 / XM bridge

This service must run on a Windows machine with the MetaTrader 5 desktop terminal installed and logged into the intended XM account. The phone app cannot host the Python bridge.

1. Copy `.env.example` to `.env`; set XM demo login, password, exact server, a long random BRIDGE_API_TOKEN and local DATABASE_URL.
2. Keep `TRADING_MODE=demo` and `KILL_SWITCH=true`.
3. Confirm the exact gold/forex symbol names in MT5 Market Watch and set ALLOWED_SYMBOLS.
4. Set FINNHUB_API_KEY. News protection is required by default and will refuse orders if calendar access is unavailable.
5. Run PowerShell as a normal user in this folder: `./start.ps1`.
6. Check `http://127.0.0.1:8000/health`; use the bearer token for all account, quote, journal, news and memory endpoints.

The API binds to localhost by default. Do not change the bind address or expose port 8000 to the public internet. Use a private VPN and TLS reverse proxy for remote access. Never commit `.env`.
