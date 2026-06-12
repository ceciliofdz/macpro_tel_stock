import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()

def ma(series: pd.Series, length: int, ma_type: str) -> pd.Series:
    if ma_type == 'EMA':
        return series.ewm(span=length, adjust=False).mean()
    else:  # SMA
        return series.rolling(window=length).mean()

def detect_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Aplica el MACD PRO y devuelve el DataFrame con columnas:
    - macd, signal, hist
    - raw_buy, raw_sell
    - is_bullish, is_bearish (tendencia EMA200)
    - buy_signal, sell_signal (filtradas)
    """
    source = df[params['source_type']]
    
    # Cálculo del MACD
    ma_fast = ma(source, params['fast_len'], params['osc_ma_type'])
    ma_slow = ma(source, params['slow_len'], params['osc_ma_type'])
    macd = ma_fast - ma_slow
    signal = ma(macd, params['signal_len'], params['signal_ma_type'])
    hist = macd - signal
    
    df['macd'] = macd
    df['signal'] = signal
    df['hist'] = hist
    
    # Cruces del histograma con cero
    df['raw_buy'] = (hist > 0) & (hist.shift(1) <= 0)
    df['raw_sell'] = (hist < 0) & (hist.shift(1) >= 0)
    
    # --- CORRECCIÓN: filtro de tendencia usando la misma 'source' (o 'close' si se desea) ---
    # Nuevo parámetro opcional: 'trend_source_type' (por defecto 'close' para no romper compatibilidad)
    trend_source = df[params.get('trend_source_type', 'close')]
    ema200 = ma(trend_source, params['trend_len'], 'EMA')
    df['is_bullish'] = trend_source > ema200
    df['is_bearish'] = trend_source < ema200
    
    # Aplicar filtro según modo
    use_trend = params['use_trend_filter']
    filter_mode = params['trend_filter_mode']
    
    buy_filter_required = use_trend and (filter_mode in ('Ambas', 'Solo Compras'))
    sell_filter_required = use_trend and (filter_mode in ('Ambas', 'Solo Ventas'))
    
    df['buy_signal'] = df['raw_buy'] & (~buy_filter_required | df['is_bullish'])
    df['sell_signal'] = df['raw_sell'] & (~sell_filter_required | df['is_bearish'])
    
    return df

def get_last_signal(df: pd.DataFrame):
    """Retorna el último registro con señales para enviar alerta"""
    if len(df) < 2:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2]
    # Solo interesa si la señal se produjo en la última vela (evita reenvíos)
    if last['buy_signal'] and not prev['buy_signal']:
        return ('BUY', last)
    if last['sell_signal'] and not prev['sell_signal']:
        return ('SELL', last)
    return None