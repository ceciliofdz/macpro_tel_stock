# MACD PRO Telegram Bot

Project: MACD signal monitor with Telegram alerts and a minimal web panel.

Description
-
`MACD PRO Telegram Bot` monitors multiple symbols (tickers) applying a variant of the MACD indicator with an optional trend filter (e.g., EMA 200). When relevant crossovers are detected, the system sends notifications to a Telegram chat and provides a simple web interface to manage the list of tickers.

Key features
-
- Monitor multiple tickers listed in `tickers.csv`.
- Configurable MACD logic (`FAST_LEN`, `SLOW_LEN`, `SIGNAL_LEN`, moving average types).
- Optional trend filter (EMA 200) to reduce noise.
- Send alerts to Telegram (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- Lightweight web interface for viewing/editing tickers (templates/).

Requirements
-
- Python 3.11+ (tested on 3.11)
- `pip` and a virtual environment recommended

Quick installation
-
1. Clone the repository.
2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
.venv\Scripts\activate     # Windows (PowerShell/CMD)
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables by copying `.env.example` to `.env` and editing values.

Usage
-
- Run the monitor:

```bash
python main.py
```

- The web interface (if enabled) runs by default at `http://localhost:5000`.

Environment variables (example)
-
Create a `.env` file with at least the following keys (example values):

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=987654321
FAST_LEN=12
SLOW_LEN=26
SIGNAL_LEN=9
SOURCE_TYPE=close
OSC_MA_TYPE=EMA
SIGNAL_MA_TYPE=EMA
USE_TREND_FILTER=true
TREND_FILTER_MODE=both
TREND_EMA_LEN=200
TIMEFRAME=1h
CHECK_INTERVAL_MINUTES=5
```

`tickers.csv` format
-
The `tickers.csv` file contains the symbols to monitor. Recommended format:

```csv
symbol,active,timeframe
BTC/USDT,True,1h
ETH/USDT,True,1h
```

Relevant files
-
- `main.py` — entry point for the monitor.
- `data_fetcher.py` — fetches market data.
- `macd_logic.py` — implements MACD and alert logic.
- `telegram_bot.py` — sends messages to Telegram.
- `templates/` — minimal web views.

Testing and development
-
- For quick tests, edit `tickers.csv` and run `python main.py`.
- Check `test.py` for local examples or test scripts (if present).

Debugging and notes
-
- Ensure system clock and timezone are correct when working with timeframes.
- If you do not receive Telegram messages, verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` with `@BotFather` and `@userinfobot`.

Would you like me to:
- translate `README.md` in place (replace the Spanish file),
- include an actual `.env.example` file in the repo with these example values, or
- add a short usage example showing common commands?
