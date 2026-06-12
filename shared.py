import os
import csv
from datetime import datetime, timezone

# Archivos CSV
CSV_FILE = 'tickers.csv'
SIGNALS_FILE = 'signals_history.csv'

# --------------------- Tickers ---------------------
def init_tickers_file():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['symbol', 'active', 'timeframe'])

def read_tickers():
    init_tickers_file()
    tickers = []
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

# --------------------- Señales ---------------------
def init_signals_file():
    if not os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'symbol', 'signal_type', 'price', 'momento', 'tendencia'])

def save_signal(symbol, signal_type, price, momento, tendencia):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    with open(SIGNALS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, symbol, signal_type, price, momento, tendencia])

def read_signals(limit=100, include_id=True):
    init_signals_file()
    signals = []
    with open(SIGNALS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if include_id:
                row['id'] = idx
            signals.append(row)
    reversed_signals = list(reversed(signals))
    if limit:
        reversed_signals = reversed_signals[:limit]
    return reversed_signals

def get_all_signals_with_id():
    init_signals_file()
    signals = []
    with open(SIGNALS_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            row['id'] = idx
            signals.append(row)
    return signals

def delete_signal(signal_id):
    signals = get_all_signals_with_id()
    new_signals = [s for s in signals if s['id'] != signal_id]
    with open(SIGNALS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'symbol', 'signal_type', 'price', 'momento', 'tendencia'])
        writer.writeheader()
        for s in new_signals:
            s_copy = {k: v for k, v in s.items() if k != 'id'}
            writer.writerow(s_copy)
    return True

def delete_all_signals():
    with open(SIGNALS_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'signal_type', 'price', 'momento', 'tendencia'])
    return True