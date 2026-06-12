import os
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import fcntl
import sys

from data_fetcher import fetch_ohlcv, _is_crypto_symbol, get_exchange_time
from macd_logic import detect_signals
from telegram_bot import send_telegram_alert
from shared import read_tickers, save_signal, CSV_FILE, SIGNALS_FILE

load_dotenv()

# --------------------- Parámetros desde .env ---------------------
PARAMS = {
    'fast_len': int(os.getenv('FAST_LEN', 12)),
    'slow_len': int(os.getenv('SLOW_LEN', 26)),
    'signal_len': int(os.getenv('SIGNAL_LEN', 9)),
    'source_type': os.getenv('SOURCE_TYPE', 'close'),
    'trend_source_type': os.getenv('TREND_SOURCE_TYPE', 'close'),
    'osc_ma_type': os.getenv('OSC_MA_TYPE', 'EMA'),
    'signal_ma_type': os.getenv('SIGNAL_MA_TYPE', 'EMA'),
    'use_trend_filter': os.getenv('USE_TREND_FILTER', 'true').lower() == 'true',
    'trend_filter_mode': os.getenv('TREND_FILTER_MODE', 'Ambas'),
    'trend_len': int(os.getenv('TREND_EMA_LEN', 200)),
}

DEFAULT_TIMEFRAME = os.getenv('TIMEFRAME', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL_MINUTES', 5))

# --------------------- Funciones auxiliares ---------------------

def lock_instance():
    try:
        with open('/tmp/macdpro-monitor.lock', 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("Ya existe una instancia del monitor ejecutándose.")
        sys.exit(1)

def log_message(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}")

def is_wall_street_open():
    try:
        import pytz
        eastern = pytz.timezone('US/Eastern')
        now = datetime.now(eastern)
    except ImportError:
        utc_now = datetime.now(timezone.utc)
        est_offset = timedelta(hours=-5)
        now = utc_now + est_offset
        now = now.replace(tzinfo=timezone.utc)
    
    weekday = now.weekday()
    if weekday >= 5:
        return False
    
    pre_market = now.replace(hour=8, minute=30, second=0, microsecond=0)
    post_market = now.replace(hour=17, minute=0, second=0, microsecond=0)
    return pre_market <= now <= post_market

def timeframe_to_milliseconds(timeframe: str) -> int:
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    if unit == 'm':
        return value * 60 * 1000
    elif unit == 'h':
        return value * 60 * 60 * 1000
    elif unit == 'd':
        return value * 24 * 60 * 60 * 1000
    else:
        raise ValueError(f"Timeframe no soportado: {timeframe}")

def get_last_closed_candle(df: pd.DataFrame, timeframe_ms: int, current_time_ms: int):
    for idx in range(len(df)-1, -1, -1):
        candle_time_ms = int(df.index[idx].timestamp() * 1000)
        close_time_ms = candle_time_ms + timeframe_ms
        if close_time_ms <= current_time_ms:
            return idx
    return None

# --------------------- Lógica de monitoreo ---------------------
last_alerted_candle = {}  # symbol -> timestamp_ms de la última vela alertada

def analyze_and_alert():
    global last_alerted_candle
    
    tickers = read_tickers()
    active_tickers = [t for t in tickers if t['active'].lower() == 'true']
    
    if not active_tickers:
        log_message("No hay tickers activos para monitorear.")
        return
    
    try:
        current_time_ms = get_exchange_time()
    except Exception:
        current_time_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
    
    for ticker in active_tickers:
        symbol = ticker['symbol']
        timeframe = ticker.get('timeframe', DEFAULT_TIMEFRAME)
        timeframe_ms = timeframe_to_milliseconds(timeframe)
        
        # Saltar acciones fuera de horario Wall Street
        if not _is_crypto_symbol(symbol):
            if not is_wall_street_open():
                log_message(f"Fuera de horario Wall Street, saltando {symbol}")
                continue
        
        try:
            df = fetch_ohlcv(symbol, timeframe, limit=300)
            if df.empty:
                continue
            
            last_closed_idx = get_last_closed_candle(df, timeframe_ms, current_time_ms)
            if last_closed_idx is None:
                continue
            
            last_closed_ts = int(df.index[last_closed_idx].timestamp() * 1000)
            if symbol in last_alerted_candle and last_alerted_candle[symbol] >= last_closed_ts:
                continue
            
            df_subset = df.iloc[:last_closed_idx+1].copy()
            df_subset = detect_signals(df_subset, PARAMS)
            
            last_row = df_subset.iloc[-1]
            buy_signal = last_row['buy_signal']
            sell_signal = last_row['sell_signal']
            
            if buy_signal or sell_signal:
                sig_type = 'BUY' if buy_signal else 'SELL'
                precio = last_row['close']
                momento = "ALCISTA ↑" if last_row['hist'] > 0 else "BAJISTA ↓"
                tendencia = "BULL (Up)" if last_row['is_bullish'] else "BEAR (Down)"
                
                sent = send_telegram_alert(symbol, sig_type, precio, momento, tendencia)
                save_signal(symbol, sig_type, precio, momento, tendencia)
                if sent:
                    log_message(f"✅ Alerta {sig_type} para {symbol} - Precio: {precio} (vela UTC {last_closed_ts})")
                else:
                    log_message(f"❌ Fallo Telegram para {symbol} - Precio: {precio}")
                last_alerted_candle[symbol] = last_closed_ts
            else:
                last_alerted_candle[symbol] = last_closed_ts
                
        except Exception as e:
            log_message(f"Error procesando {symbol}: {e}")
            time.sleep(0.5)
            continue
        
        time.sleep(0.5)  # pequeño delay entre tickers

# --------------------- Scheduler ---------------------
def start_monitor():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=analyze_and_alert, trigger='interval', minutes=CHECK_INTERVAL)
    scheduler.start()
    log_message(f"Monitor iniciado. Revisando cada {CHECK_INTERVAL} minuto(s).")
    # Ejecutar una vez al inicio (opcional)
    analyze_and_alert()

if __name__ == '__main__':
    lock_instance()
    start_monitor()
    # Mantener el script vivo
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log_message("Monitor detenido por el usuario.")