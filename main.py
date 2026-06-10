import os
import csv
import threading
import time
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from data_fetcher import fetch_ohlcv
from macd_logic import detect_signals, get_last_signal
from telegram_bot import send_telegram_alert

load_dotenv()

import time
from datetime import datetime, timezone
from data_fetcher import fetch_ohlcv, get_exchange_time

# ... resto de imports ...

# En lugar de datetime.now(), usaremos datetime.utcnow() en los logs
def log_message(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}")

# Función auxiliar para obtener tiempo UTC actual en ms (respaldo)
def get_current_utc_ms():
    return int(pd.Timestamp.utcnow().timestamp() * 1000)

def timeframe_to_milliseconds(timeframe: str) -> int:
    """Convierte timeframe de Binance (ej: '1h', '15m', '4h') a milisegundos."""
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
    """
    Retorna el índice (entero) de la última fila del DataFrame cuya vela está cerrada.
    Una vela está cerrada si: timestamp + timeframe_ms <= current_time_ms.
    Si no hay ninguna, retorna None.
    """
    for idx in range(len(df)-1, -1, -1):
        candle_time_ms = int(df.index[idx].timestamp() * 1000)
        close_time_ms = candle_time_ms + timeframe_ms
        if close_time_ms <= current_time_ms:
            return idx  # índice posicional en el DataFrame
    return None

# Parámetros globales (desde .env)
PARAMS = {
    'fast_len': int(os.getenv('FAST_LEN', 12)),
    'slow_len': int(os.getenv('SLOW_LEN', 26)),
    'signal_len': int(os.getenv('SIGNAL_LEN', 9)),
    'source_type': os.getenv('SOURCE_TYPE', 'close'),
    'osc_ma_type': os.getenv('OSC_MA_TYPE', 'EMA'),
    'signal_ma_type': os.getenv('SIGNAL_MA_TYPE', 'EMA'),
    'use_trend_filter': os.getenv('USE_TREND_FILTER', 'true').lower() == 'true',
    'trend_filter_mode': os.getenv('TREND_FILTER_MODE', 'Ambas'),
    'trend_len': int(os.getenv('TREND_EMA_LEN', 200)),
}

DEFAULT_TIMEFRAME = os.getenv('TIMEFRAME', '1h')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL_MINUTES', 5))

CSV_FILE = 'tickers.csv'
SIGNALS_FILE = 'signals_history.csv'

# Para evitar múltiples alertas de una misma señal
last_alert = {}

# --------------------- Funciones del CSV ---------------------
def init_signals_file():
    """Inicializa el archivo de histórico de señales si no existe."""
    if not os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'symbol', 'signal_type', 'price', 'momento', 'tendencia'])

def save_signal(symbol, signal_type, price, momento, tendencia):
    """Guarda una señal en el histórico CSV."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    with open(SIGNALS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, symbol, signal_type, price, momento, tendencia])

def read_signals(limit=100):
    """Lee las últimas señales del histórico."""
    init_signals_file()
    signals = []
    with open(SIGNALS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            signals.append(row)
    # Retorna en orden inverso (más recientes primero) y limita
    return list(reversed(signals))[:limit]
def read_tickers():
    """Lee el CSV y devuelve lista de dicts con symbol, active, timeframe"""
    tickers = []
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'active', 'timeframe'])
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tickers.append(row)
    return tickers

def write_tickers(tickers):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'active', 'timeframe'])
        writer.writeheader()
        writer.writerows(tickers)

def add_ticker(symbol, active, timeframe):
    tickers = read_tickers()
    # evitar duplicados
    if not any(t['symbol'] == symbol for t in tickers):
        tickers.append({'symbol': symbol, 'active': active, 'timeframe': timeframe})
        write_tickers(tickers)

def update_ticker(old_symbol, new_symbol, active, timeframe):
    tickers = read_tickers()
    for t in tickers:
        if t['symbol'] == old_symbol:
            t['symbol'] = new_symbol
            t['active'] = active
            t['timeframe'] = timeframe
            break
    write_tickers(tickers)

def delete_ticker(symbol):
    tickers = read_tickers()
    tickers = [t for t in tickers if t['symbol'] != symbol]
    write_tickers(tickers)

# --------------------- Lógica de monitoreo ---------------------
# Diccionario para recordar la última vela cerrada que ya generó alerta (por símbolo)
last_alerted_candle = {}  # key: symbol, value: timestamp (ms) de la vela cerrada

def analyze_and_alert():
    global last_alerted_candle
    tickers = read_tickers()
    active_tickers = [t for t in tickers if t['active'].lower() == 'true']
    
    try:
        current_time_ms = get_exchange_time()
    except Exception:
        current_time_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
    
    for ticker in active_tickers:
        symbol = ticker['symbol']
        timeframe = ticker.get('timeframe', DEFAULT_TIMEFRAME)
        timeframe_ms = timeframe_to_milliseconds(timeframe)
        
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
            prev_row = df_subset.iloc[-2] if len(df_subset) > 1 else None
            
            buy_signal = last_row['buy_signal'] and (prev_row is None or not prev_row['buy_signal'])
            sell_signal = last_row['sell_signal'] and (prev_row is None or not prev_row['sell_signal'])
            
            if buy_signal or sell_signal:
                sig_type = 'BUY' if buy_signal else 'SELL'
                precio = last_row['close']
                momento = "ALCISTA ↑" if last_row['hist'] > 0 else "BAJISTA ↓"
                tendencia = "BULL (Up)" if last_row['is_bullish'] else "BEAR (Down)"
                
                sent = send_telegram_alert(symbol, sig_type, precio, momento, tendencia)
                save_signal(symbol, sig_type, precio, momento, tendencia)
                if not sent:
                    log_message(f"ERROR: fallo al enviar Telegram para {symbol} - Precio: {precio} (vela UTC {last_closed_ts})")
                log_message(f"Alerta {sig_type} para {symbol} - Precio: {precio} (vela UTC {last_closed_ts})")
                last_alerted_candle[symbol] = last_closed_ts
            else:
                last_alerted_candle[symbol] = last_closed_ts
                
        except Exception as e:
            log_message(f"Error crítico procesando {symbol}: {e}")
            time.sleep(0.5)
            continue
        
        time.sleep(0.5)

# --------------------- Web (Flask) ---------------------
app = Flask(__name__)

@app.route('/')
def index():
    tickers = read_tickers()
    return render_template('index.html', tickers=tickers)

@app.route('/signals')
def signals():
    signals = read_signals(limit=200)
    return render_template('signals.html', signals=signals)

@app.route('/add', methods=['POST'])
def add():
    symbol = request.form['symbol']
    active = request.form['active']
    timeframe = request.form['timeframe']
    add_ticker(symbol, active, timeframe)
    return redirect(url_for('index'))

@app.route('/edit/<path:old_symbol>', methods=['GET', 'POST'])
def edit(old_symbol):
    if request.method == 'POST':
        new_symbol = request.form['symbol']
        active = request.form['active']
        timeframe = request.form['timeframe']
        update_ticker(old_symbol, new_symbol, active, timeframe)
        return redirect(url_for('index'))
    tickers = read_tickers()
    ticker = next((t for t in tickers if t['symbol'] == old_symbol), None)
    return render_template('edit.html', ticker=ticker)

@app.route('/delete/<path:symbol>')
def delete(symbol):
    delete_ticker(symbol)
    return redirect(url_for('index'))

# --------------------- Arranque ---------------------
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=analyze_and_alert, trigger='interval', minutes=CHECK_INTERVAL)
    scheduler.start()
    print(f"Scheduler iniciado. Revisando cada {CHECK_INTERVAL} minuto(s).")
    # log_message(f"Hora UTC actual del sistema: {pd.Timestamp.utcnow()}")
    # log_message(f"Hora del exchange: {datetime.utcfromtimestamp(get_exchange_time()/1000)} UTC")
    # Ejecutar inmediatamente al inicio
    threading.Timer(5, analyze_and_alert).start()

if __name__ == '__main__':
    start_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)