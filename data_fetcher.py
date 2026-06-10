import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
import yfinance as yf

# Mantener exchange para cryptos (compatibilidad)
exchange = ccxt.binance({
    'enableRateLimit': True,
})


def retry_on_failure(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except (ccxt.NetworkError, ccxt.ExchangeError, ccxt.RateLimitExceeded) as e:
            print(f"[Reintento {attempt+1}/{max_retries}] Error: {e}. Esperando {base_delay * (2**attempt)}s...")
            time.sleep(base_delay * (2**attempt))
        except Exception as e:
            print(f"Error inesperado (no reintento): {e}")
            raise e
    raise Exception(f"Fallo después de {max_retries} reintentos.")


def get_exchange_time():
    """Retorna la hora del exchange (si aplica) o la hora UTC del sistema en ms."""
    try:
        def _fetch_time():
            return exchange.fetch_time()
        return retry_on_failure(_fetch_time)
    except Exception:
        utc_now = pd.Timestamp.utcnow()
        return int(utc_now.timestamp() * 1000)


def _timeframe_to_yf_interval(timeframe: str) -> str:
    """Convierte timeframes a intervalos válidos para yfinance."""
    tf = timeframe.strip().lower()
    mapping = {
        '1m': '1m',
        '2m': '2m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '60m': '1h',
        '1h': '1h',
        '90m': '90m',
        '2h': '1h',
        '4h': '4h',
        '1d': '1d',
        '5d': '5d',
        '1w': '1wk',
        '1wk': '1wk',
        '1mo': '1mo',
        '3mo': '3mo',
    }
    if tf in mapping:
        return mapping[tf]
    if tf.endswith('h'):
        try:
            value = int(tf[:-1])
            if value == 2:
                return '1h'
            if value == 4:
                return '4h'
        except ValueError:
            pass
    if tf.endswith('m'):
        try:
            value = int(tf[:-1])
            if value in (1, 2, 5, 15, 30):
                return f"{value}m"
            if value == 60:
                return '1h'
            if value == 90:
                return '90m'
        except ValueError:
            pass
    raise ValueError(f"Timeframe no soportado: {timeframe}")


def _is_crypto_symbol(symbol: str) -> bool:
    """Detecta si el símbolo corresponde a un par de cryptomonedas para ccxt."""
    symbol = symbol.strip()
    if '/' in symbol:
        return True
    upper = symbol.upper()
    crypto_quotes = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB', 'EUR', 'USD', 'USDC', 'TUSD']
    return any(upper.endswith(q) and len(upper) > len(q) for q in crypto_quotes)


def _normalize_crypto_symbol(symbol: str) -> str:
    """Normaliza símbolos cripto para ccxt, aceptando formatos 'BASEQUOTE' o 'BASE/QUOTE'."""
    symbol = symbol.strip()
    if '/' in symbol:
        return symbol
    upper = symbol.upper()
    crypto_quotes = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB', 'EUR', 'USD', 'USDC', 'TUSD']
    for quote in crypto_quotes:
        if upper.endswith(quote) and len(upper) > len(quote):
            base = upper[:-len(quote)]
            return f"{base}/{quote}"
    return symbol


def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
    """Retorna DataFrame con velas en UTC.

    Si `symbol` parece de exchange (contiene '/'), usa `ccxt` (cryptos).
    Si es un ticker simple (ej: AAPL), usa `yfinance` (stocks).
    """
    # Detectar si es crypto (ej: 'BTC/USDT', 'BTCUSDT') o stock (ej: 'AAPL')
    is_crypto = _is_crypto_symbol(symbol)

    if is_crypto:
        crypto_symbol = _normalize_crypto_symbol(symbol)
        def _fetch():
            ohlcv = exchange.fetch_ohlcv(crypto_symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            return df
        return retry_on_failure(_fetch)

    # --- Stock via yfinance ---
    interval = _timeframe_to_yf_interval(timeframe)
    # Pedimos un periodo suficientemente largo para cubrir `limit` velas
    # Para intradiario pedimos 120d, para diario pedimos 365d
    period = '365d' if interval == '1d' else '120d'

    try:
        tk = yf.Ticker(symbol)
        hist = tk.history(period=period, interval=interval, auto_adjust=False, actions=False)
    except Exception as e:
        raise Exception(f"Error obteniendo datos de yfinance para {symbol}: {e}")

    # Fallbacks: para intradiario yfinance a veces devuelve vacío; probar 60m o 1d
    if hist is None or hist.empty:
        if interval.endswith('m'):
            try:
                hist = tk.history(period='60d', interval='60m', auto_adjust=False, actions=False)
            except Exception:
                hist = None
    if hist is None or hist.empty:
        # Último recurso: pedir datos diarios
        try:
            hist = tk.history(period='365d', interval='1d', auto_adjust=False, actions=False)
        except Exception:
            hist = None

    if hist is None or hist.empty:
        return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])

    # Normalizar nombres de columnas
    rename_map = {}
    if 'Open' in hist.columns:
        rename_map['Open'] = 'open'
    if 'High' in hist.columns:
        rename_map['High'] = 'high'
    if 'Low' in hist.columns:
        rename_map['Low'] = 'low'
    if 'Close' in hist.columns:
        rename_map['Close'] = 'close'
    if 'Volume' in hist.columns:
        rename_map['Volume'] = 'volume'
    hist = hist.rename(columns=rename_map)

    # Asegurar timezone UTC en el índice
    try:
        if hist.index.tz is None:
            hist.index = hist.index.tz_localize('UTC')
        else:
            hist.index = hist.index.tz_convert('UTC')
    except Exception:
        # En caso raro, forzamos a UTC sin conversión
        hist.index = pd.to_datetime(hist.index).tz_localize('UTC')

    # Mantener solo las columnas necesarias y limitar filas
    df = hist[['open', 'high', 'low', 'close', 'volume']].copy()
    if limit is not None and len(df) > limit:
        df = df.tail(limit)
    df.index.name = 'timestamp'
    return df