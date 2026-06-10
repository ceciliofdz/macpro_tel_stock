import ccxt
import pandas as pd
from datetime import datetime

def probar_conexion_binance(symbol="BTC/USDT", timeframe="1h", limit=100):
    """
    Función de prueba para verificar la conexión y descarga de datos desde Binance.
    """
    try:
        # 1. Crear la instancia del exchange
        exchange = ccxt.binance({
            'enableRateLimit': True,  # Muy importante para respetar los límites de la API
        })
        print(f"✅ Conectado a Binance. Versión de la API: {exchange.version}")

        # 2. Probar la carga de mercados (para ver si todo funciona)
        print("\n⏳ Cargando mercados...")
        exchange.load_markets()
        print(f"✅ Mercados cargados. Símbolo '{symbol}' encontrado.")

        # 3. Descargar datos OHLCV (velas)
        print(f"\n⏳ Descargando las últimas {limit} velas de {symbol} en timeframe {timeframe}...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        if not ohlcv:
            print("❌ Error: No se recibieron datos.")
            return None

        # 4. Convertir a DataFrame de Pandas para un análisis fácil
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # 5. Mostrar información y validación de los datos
        print(f"\n✅ Datos descargados correctamente. Total de velas: {len(df)}")
        print(f"\n📊 Primeras 5 velas (más recientes):")
        print(df.head())
        print(f"\n📊 Últimas 5 velas (más antiguas):")
        print(df.tail())

        # Validaciones básicas
        print("\n--- Validación de datos ---")
        print(f"- Precio de cierre más reciente: {df['close'].iloc[-1]:.2f} USD")
        print(f"- Precio máximo en el período: {df['high'].max():.2f} USD")
        print(f"- Precio mínimo en el período: {df['low'].min():.2f} USD")
        print(f"- Volumen total en el período: {df['volume'].sum():.2f}")

        # Verificar si hay valores nulos
        if df.isnull().sum().sum() == 0:
            print("- ✅ No hay valores nulos en los datos.")
        else:
            print("- ❌ Se encontraron valores nulos. Revisa los datos.")

        return df

    except ccxt.NetworkError as e:
        print(f"❌ Error de red al conectar con Binance: {e}")
    except ccxt.ExchangeError as e:
        print(f"❌ Error del exchange: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

    return None

# --- Ejecutar la prueba ---
if __name__ == "__main__":
    # Cambia estos parámetros si quieres probar otro símbolo o timeframe
    df_btc = probar_conexion_binance(symbol="BTC/USDT", timeframe="1h")
    if df_btc is not None:
        print("\n🎉 Conexión exitosa. Todo funciona correctamente.")